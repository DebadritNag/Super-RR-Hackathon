"""Stage 3: pressure feature distributions and candidate populations (EXPLORATORY).

Reads the exploratory pre-delivery state (the official DB is only snapshot-checked, read-only).
Writes data/reports/pressure_distribution_report.md/.json and table exp_pressure_signals in the
exploratory store. No cutoff is chosen and no player is ranked. Exit 1 if official data changed or
the independent spot check disagrees.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics import pressure_distributions as pdist  # noqa: E402
from app.analytics import pressure_features as pf  # noqa: E402
from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.pressure_distribution_report import render_report  # noqa: E402
from app.analytics.reporting import provenance, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services import pressure_service as ps  # noqa: E402

STATUS = {"status": "EXPLORATORY_NOT_VALIDATED", "official_ranking": False,
          "not_for_publication": True}  # fmt: skip
SIGNAL_COLS = [
    "match_id", "innings_number", "innings_ball_num", "wbin", "par_runs_lomo", "par_deviation_lomo",
    "par_runs_prior", "par_deviation_prior", "exp_remaining", "exp_cell_level_used",
    "shrinkage_floor_hit", "req_to_exp", "proj_total_gap_lomo", "bowl_signal_B",
    "rank_bat_pressure_rel", "bowl_rel_A", "rank_bowl_rel_B", "bowl_B_early_flag",
]  # fmt: skip


def prepare(store: Path, with_flag: bool = True):
    """Load state, add populations, signals and relative views (shared with Stage 4)."""
    rules = pf.load_rules()
    df = pf.add_populations(pf.load_state(store)).reset_index(drop=True)
    if with_flag:
        df["state_wicket_flag_disagreement"] = _flag(store, "state_wicket_flag_disagreement").values
    df, meta = pf.add_signals(df, rules)
    df = pf.add_relative(df, rules)
    return rules, df, meta


def _flag(store: Path, col: str) -> pd.Series:
    con = duckdb.connect(str(store), read_only=True)
    try:
        return (
            con.execute(
                f"SELECT coalesce({col}, false) FROM exp_pre_delivery_state "
                "ORDER BY match_id, innings_number, innings_ball_num"
            )
            .df()
            .iloc[:, 0]
            .astype(bool)
        )
    finally:
        con.close()


def population_block(df: pd.DataFrame) -> dict:
    def cnt(m):
        r = df[m]
        return {"rows": int(m.sum()), "matches": int(r["match_id"].nunique()),
                "innings": int(r["inn_key"].nunique())}  # fmt: skip

    reg = df["innings_number"].isin([1, 2]) & df["competition_type"].isin(pf.SCOPE)
    sets = {
        "all state rows": cnt(pd.Series(True, index=df.index)),
        "regulation in-scope (innings 1/2, IPL/T20I)": cnt(reg),
        "base population (no DLS-excluded rows)": cnt(df["base_pop"]),
        "innings-1 primary population": cnt(df["inn1_pop"]),
        "chase primary population": cnt(df["chase_pop"]),
    }
    by = []
    for ctx, col in (("chase", "chase_pop"), ("inn1", "inn1_pop")):
        for comp in pf.SCOPE:
            by.append({"comp": comp, "ctx": ctx, **cnt(df[col] & (df["competition_type"] == comp))})
    chase = df["chase_flag"].fillna(False).astype(bool)
    base = df["base_pop"]
    ex = {
        "innings 3/4 (restricted, RULE_INNINGS_3_4)": int((~df["innings_number"].isin([1, 2])).sum()),
        "OTHER_T20 (format out of scope)": int((df["competition_type"] == "OTHER_T20").sum()),
        "DLS-excluded primary rows (regulation in-scope)": int(
            (reg & df["dls_exclude_primary"].fillna(False)).sum()),
        "chase rows with target_basis_unverified (in base)": int(
            (base & chase & df["target_basis_unverified"].fillna(False)).sum()),
        "chase rows with Req <= 0 (in base)": int(
            (base & chase & df["req_nonpositive_flag"].fillna(False)).sum()),
        "chase rows with RRR NULL (in base)": int((base & chase & df["rrr"].isna()).sum()),
    }  # fmt: skip
    wd = int((base & df["state_wicket_flag_disagreement"]).sum())
    return {"sets": sets, "by_comp_ctx": by, "exclusions": ex, "wicket_disagreement_rows": wd}


def threshold_grid(specs: list[dict]) -> list[dict]:
    t: dict[tuple, dict] = {}
    for s in specs:
        if s["family"] == "a" and s["view"] == "abs" and s["role"] == "batter":
            t.setdefault((s["ctx"], s["comp"], s["signal"]), {})[str(s["q"])] = s["threshold"]
    return [{"ctx": k[0], "comp": k[1], "signal": k[2], "thr": v} for k, v in sorted(t.items())]


def opportunity_distribution(df: pd.DataFrame, specs, flags) -> list[dict]:
    out = []
    wanted = [("chase", "rrr", "abs"), ("inn1", "neg_par_dev", "abs"),
              ("chase", "bowl_signal_B_all", "abs"), ("inn1", "bowl_signal_B_all", "abs")]  # fmt: skip
    for s in specs:
        if s["family"] != "a" or (s["ctx"], s["signal"], s["view"]) not in wanted:
            continue
        if s["q"] not in (0.75, 0.9):
            continue
        pc = pdist.player_counts(df, flags[s["id"]], s["role"])
        keep = pc["measure"].to_numpy() > 0
        m = pc["measure"].to_numpy()[keep]
        if len(m) == 0:
            continue
        ne = pc["n_eff_kish"].to_numpy()[keep]
        mt = pc["matches"].to_numpy()[keep]
        out.append({"id": s["id"], "role": s["role"], "players": int(len(m)),
                    "p10": float(np.percentile(m, 10)), "p25": float(np.percentile(m, 25)),
                    "p50": float(np.percentile(m, 50)), "p75": float(np.percentile(m, 75)),
                    "p90": float(np.percentile(m, 90)), "max": float(m.max()),
                    "neff_p50": float(np.percentile(ne, 50)), "neff_p90": float(np.percentile(ne, 90)),
                    "matches_p50": float(np.percentile(mt, 50))})  # fmt: skip
    return out


def spot_check(store: Path, effects: list[dict]) -> dict:
    """Independent SQL re-implementation of one candidate (IPL chase RRR at q = 0.9)."""
    cid = "a|chase|IPL|batter|rrr|abs|0.9"
    eng = next(e for e in effects if e["id"] == cid)
    base = (
        "regulation_pressure_eligible AND NOT format_out_of_scope AND NOT dls_exclude_primary "
        "AND innings_number IN (1, 2) AND competition_type = 'IPL' AND chase_flag "
        "AND NOT target_basis_unverified AND NOT req_nonpositive_flag AND rrr IS NOT NULL"
    )
    con = duckdb.connect(str(store), read_only=True)
    try:
        thr = con.execute(
            f"SELECT quantile_cont(rrr, 0.9) FROM exp_pre_delivery_state WHERE {base}"
        ).fetchone()[0]
        flagged = f"{base} AND rrr >= {float(thr)!r}"
        balls, matches, innings = con.execute(
            "SELECT sum(den_counts_as_ball_faced), count(DISTINCT match_id), "
            "count(DISTINCT (match_id, innings_number)) "
            f"FROM exp_pre_delivery_state WHERE {flagged} AND striker_id IS NOT NULL"
        ).fetchone()
        ge = con.execute(
            "SELECT count(*) FROM (SELECT striker_id FROM exp_pre_delivery_state "
            f"WHERE {flagged} AND striker_id IS NOT NULL GROUP BY striker_id "
            f"HAVING sum(den_counts_as_ball_faced) >= {eng['floors']['floor2']})"
        ).fetchone()[0]
    finally:
        con.close()
    pairs = {
        "threshold": (eng["threshold"], float(thr)),
        "pressure balls faced": (eng["pressure_unit_rows"], int(balls)),
        "matches": (eng["matches"], int(matches)),
        "innings": (eng["innings"], int(innings)),
        "batters with >= floor 2 balls": (eng["players_ge_floor2"], int(ge)),
    }
    checks = {}
    for k, (a, b) in pairs.items():
        ok = abs(a - b) < 1e-9 if isinstance(a, float) else a == b
        checks[k] = {"engine": a, "sql": b, "match": bool(ok)}
    return {
        "candidate": cid,
        "checks": checks,
        "all_match": all(v["match"] for v in checks.values()),
    }


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--store", type=Path, default=ps.EXPLORATORY_DB)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s, args.db)
    rules, df, meta = prepare(args.store)
    specs, flags = pf.build_candidates(df, rules)
    effects = pdist.candidate_effects(df, specs, flags)
    breaks = pdist.break_candidates(df, rules)
    all_effects = effects + pdist.break_effects(df, breaks)

    chase = df["chase_pop"]
    wb = meta["wickets_bins"]
    wb["min_cell_innings"] = int(pf.param(rules, "min_cell_innings"))
    kp = meta["exp_k_by_parent"]
    wrem = {w: {"chase": int((chase & (df["wickets_remaining"] == w)).sum()),
                "inn1": int((df["inn1_pop"] & (df["wickets_remaining"] == w)).sum())}
            for w in range(1, 11)}  # fmt: skip
    res = {
        **STATUS,
        "provenance": {**provenance(None, None, seed=None), "state_table": ps.STATE_TABLE,
                       "state_rows": int(len(df)), "rules_config": "pressure_rules_v1.json"},
        "populations": population_block(df),
        "wickets_bins": wb,
        "par_meta": meta["par"],
        "source_innings_n": meta["source_innings_n"],
        "exp_levels": {k: int(v) for k, v in df["exp_cell_level_used"].value_counts().items()},
        "shrinkage_floor_hit_rows": int(df["shrinkage_floor_hit"].sum()),
        "floor_hit_parents": int(sum(1 for v in kp.values() if v["shrinkage_floor_hit"])),
        "parents": len(kp),
        "exp_k_by_parent": kp,
        "distributions": pdist.signal_distributions(df),
        "rrr_cap": pdist.rrr_cap_report(df),
        "rrr_hist": pdist.histogram(df.loc[chase, "rrr"].to_numpy(float),
                                    [0, 4, 6, 8, 10, 12, 15, 20, 30, 60, 1e9]),
        "phase_table": pdist.balls_remaining_table(df),
        "wrem_hist": wrem,
        "req_by_balls": pdist.runs_required_by_balls(df),
        "cell_counts": pdist.cell_innings_counts(df),
        "season_counts": pdist.season_counts(df),
        "zero_inflation_share": float(pf.param(rules, "zero_inflation_share")),
        "grid": list(pf.param(rules, "quantile_grid")),
        "threshold_grid": threshold_grid(specs),
        "break_tol": float(pf.param(rules, "break_reproducibility_tol")),
        "breaks": breaks,
        "n_candidates": len(all_effects),
        "n_family": {k: sum(1 for e in all_effects if e["family"] == k) for k in "abc"},
        "effects": all_effects,
        "opportunity_dist": opportunity_distribution(df, specs, flags),
        "min_prior_innings": int(pf.param(rules, "min_prior_innings")),
        "prior_vs_lomo": pdist.prior_vs_lomo(df, rules),
        "spot_check": spot_check(args.store, effects),
    }  # fmt: skip
    out = args.reports_dir
    write_json_deterministic(out / "pressure_distribution_report.json", res)
    write_text(out / "pressure_distribution_report.md", render_report(res))
    sig = df[[c for c in SIGNAL_COLS if c in df.columns]].copy()
    con = duckdb.connect(str(args.store))
    try:
        con.register("sig_df", sig)
        con.execute("CREATE OR REPLACE TABLE exp_pressure_signals AS SELECT *, "
                    "'pre_delivery_state_v1' AS state_version, "
                    "'EXPLORATORY_NOT_VALIDATED' AS status FROM sig_df")  # fmt: skip
    finally:
        con.close()
    diff = assert_unchanged(before, snapshot_from_settings(s, args.db))
    print(
        f"candidates={len(all_effects)} spot_check_all_match={res['spot_check']['all_match']} "
        f"official_unchanged={not diff}"
    )
    return 0 if (not diff and res["spot_check"]["all_match"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
