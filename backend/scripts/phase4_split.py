"""Phase 4 Chunk 1: temporal split manifest, strictly prior par coverage, phase documentation.

Reads the exploratory state (read-only), writes p4_ tables to the exploratory store, JSON/Markdown
outputs to data/reports, and verifies that the official database and CSVs are unchanged.
No outcome-based evaluation is performed here (counts use dates and pre-delivery state only,
plus the par source innings, which come from matches strictly earlier than the rows they serve).
Exit 1 if official data changed.
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

from app.analytics import pressure_features as pf  # noqa: E402
from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import md_table, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.phase4 import par as p4par  # noqa: E402
from app.phase4 import phases as p4ph  # noqa: E402
from app.phase4.config import file_sha256, load_split_config  # noqa: E402
from app.phase4.constants import PAR_FLAG, PERIODS, REPORTS_DIR, SCOPE, SPLIT_CONFIG  # noqa: E402
from app.phase4.data import load_state_with_period  # noqa: E402
from app.phase4.split import Split, assign_matches, check_split_integrity  # noqa: E402
from app.phase4.store import write_p4_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

MARKER = "<!-- CHUNK1_GENERATED -->"


def same_date_groups(matches: pd.DataFrame) -> dict:
    out = {}
    for comp, g in matches.groupby("competition_type"):
        sizes = g.groupby("match_date").size()
        multi = sizes[sizes > 1]
        out[comp] = {"dates": int(len(multi)), "matches": int(multi.sum())}
    return out


def pressure_state_counts(df: pd.DataFrame, cfg: dict, q: float = 0.90) -> tuple[list, list]:
    """State-only counts: chase rows with rrr >= TRAIN-only lower quantile, per format."""
    d = pf.add_populations(df)
    chase = d[d["chase_pop"]]
    rows, cells = [], []
    thr = {}
    for comp in SCOPE:
        train = chase[(chase["competition_type"] == comp) & (chase["period"] == "TRAIN")]
        thr[comp] = pf.lower_quantile(train["rrr"].to_numpy(), q)
    k = int(cfg["meaningful_split"]["player_level_ball_threshold_for_counting"])
    for comp in SCOPE:
        press = chase[(chase["competition_type"] == comp) & (chase["rrr"] >= thr[comp])]
        for period in PERIODS:
            p = press[press["period"] == period]
            rows.append(
                {
                    "format": comp,
                    "period": period,
                    "rrr_threshold_train_only": thr[comp],
                    "pressure_deliveries": int(len(p)),
                    "distinct_matches": int(p["match_id"].nunique()),
                }
            )
            for role, col in (("batter", "striker_id"), ("bowler", "bowler_id")):
                counts = p.groupby(col).size()
                cells.append(
                    {
                        "cell": f"{comp} {role}",
                        "period": period,
                        "players": int(len(counts)),
                        "p50_balls": float(counts.median()) if len(counts) else None,
                        "p90_balls": float(counts.quantile(0.9)) if len(counts) else None,
                        "players_ge_24": int((counts >= 24).sum()),
                        "players_ge_36": int((counts >= 36).sum()),
                        "players_ge_60": int((counts >= 60).sum()),
                        "players_ge_count_threshold": int((counts >= k).sum()),
                    }
                )
    return rows, cells


def verdicts(rows: list, cells: list, cfg: dict) -> list:
    m = cfg["meaningful_split"]
    out = []
    for r in rows:
        ok = (
            r["pressure_deliveries"] >= m["min_pressure_deliveries_per_period"]
            and r["distinct_matches"] >= m["min_distinct_matches_per_period"]
        )
        out.append(
            {
                "level": "population",
                "format": r["format"],
                "period": r["period"],
                "supported": bool(ok),
                "label": "SUPPORTED" if ok else "LIMITED",
            }
        )
    need = m["min_players_for_player_level_test"]
    for c in cells:
        ok = c["players_ge_count_threshold"] >= need
        out.append(
            {
                "level": "player",
                "format": c["cell"],
                "period": c["period"],
                "players_with_enough_balls": c["players_ge_count_threshold"],
                "supported": bool(ok),
                "label": "SUPPORTED" if ok else "INSUFFICIENT_FOR_PLAYER_LEVEL_TEST",
            }
        )
    return out


def compare_with_existing_prior(df: pd.DataFrame, par: pd.DataFrame, store) -> dict:
    con = duckdb.connect(str(store), read_only=True)
    try:
        old = con.execute(
            "SELECT match_id, innings_number, innings_ball_num, par_runs_prior "
            "FROM exp_pressure_signals ORDER BY match_id, innings_number, innings_ball_num"
        ).df()
    finally:
        con.close()
    keys = ["match_id", "innings_number", "innings_ball_num"]
    new = df[keys].copy()
    new["par_new"] = par["par_runs_prior"].to_numpy()
    mg = old.merge(new, on=keys, how="outer", indicator=True)
    both = mg[mg["_merge"] == "both"]
    a, b = both["par_runs_prior"].to_numpy(float), both["par_new"].to_numpy(float)
    same_null = bool((np.isnan(a) == np.isnan(b)).all())
    ok = ~np.isnan(a) & ~np.isnan(b)
    return {
        "rows_compared": int(len(both)),
        "rows_only_in_one_table": int((mg["_merge"] != "both").sum()),
        "null_pattern_identical": same_null,
        "max_abs_difference_where_both_present": float(np.abs(a[ok] - b[ok]).max())
        if ok.any()
        else 0.0,
    }


def render_generated(m: dict) -> str:
    L = [MARKER, "", "## 11. Verified counts from the Chunk 1 code (generated, do not edit)", ""]
    L.append("Generated by `scripts/phase4_split.py` from dates, pre-delivery state and par source")
    L.append("innings only. No pressure outcome (runs, wickets, residuals) was evaluated.")
    L.append("These counts use the final population rules and supersede the approximate state-only")
    L.append("counts in section 3 (small differences come from the exact population definition).\n")
    L.append(f"Split config SHA-256: `{m['split_config_sha256']}`.\n")
    L.append("### 11.1 Matches by format and period\n")
    mp = m["matches_by_format_period"]
    L.append(
        md_table(
            ["format", "period", "matches", "first date", "last date"],
            [[r["competition_type"], r["period"], r["matches"], r["first"], r["last"]] for r in mp],
        )
    )
    L.append("### 11.2 Integrity checks\n")
    L.append(md_table(["check", "result"], [[k, v] for k, v in m["integrity"].items()]))
    L.append("### 11.3 State-only pressure counts (TRAIN-only rrr q0.90 per format)\n")
    L.append(
        md_table(
            ["format", "period", "rrr threshold", "pressure deliveries", "distinct matches"],
            [
                [
                    r["format"],
                    r["period"],
                    round(r["rrr_threshold_train_only"], 2),
                    r["pressure_deliveries"],
                    r["distinct_matches"],
                ]
                for r in m["pressure_state_counts"]
            ],
        )  # fmt: skip
    )
    L.append("### 11.4 Meaningful-split verdicts\n")
    L.append(
        md_table(
            ["level", "cell", "period", "players >= 36 balls", "verdict"],
            [
                [
                    v["level"],
                    v["format"],
                    v["period"],
                    v.get("players_with_enough_balls"),
                    v["label"],
                ]
                for v in m["verdicts"]
            ],
        )
    )
    pc = m["par_coverage"]
    L.append("### 11.5 Strictly prior par: rows without enough prior history\n")
    L.append(
        md_table(
            ["format", "period", "innings-1 rows", "unavailable rows", "innings", "last date"],
            [
                [
                    r["competition_type"],
                    r["period"],
                    r["innings1_rows"],
                    r["rows_unavailable"],
                    r["innings_unavailable"],
                    r["last_unavailable_date"],
                ]
                for r in pc["rows"]
            ],
        )  # fmt: skip
    )
    L.append(
        f"Equivalence with the existing `par_runs_prior`: {m['par_equivalence']}. "
        f"Sensitivity (min prior innings -> unavailable innings-1 rows): {m['par_sensitivity']}.\n"
    )
    return "\n".join(L) + "\n"


def update_plan_doc(path: Path, generated: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if MARKER in text:
        text = text.split(MARKER)[0].rstrip() + "\n\n"
    else:
        text = text.rstrip() + "\n\n"
    write_text(path, text + generated)


def phase_markdown(ph: dict) -> str:
    rep = ph["shortened"]
    L = ["# Phase 4: innings phase boundaries and shortened innings", ""]
    L.append("Status: `EXPERIMENTAL_NOT_VALIDATED`. Generated by `scripts/phase4_split.py`.\n")
    L.append("Rule (unchanged `app/analytics/phase_engine.py`): powerplay if `B < floor(3L/10)`, ")
    L.append(
        "death if `B >= ceil(3L/4)`, middle otherwise. `B` = legal balls before the delivery, "
    )
    L.append(
        "`L` = innings limit in balls. Phase is ball-based, so for `L < 120` the boundaries fall"
    )
    L.append(" inside overs.\n")
    L.append(
        md_table(
            [
                "L",
                "powerplay_end",
                "death_start",
                "pp balls",
                "middle",
                "death",
                "innings",
                "deliveries",
            ],
            [
                [
                    r["limit"],
                    r["powerplay_end_ball"],
                    r["death_start_ball"],
                    r["powerplay_balls"],
                    r["middle_balls"],
                    r["death_balls"],
                    r["innings"],
                    r["deliveries"],
                ]
                for r in rep["by_limit"]
            ],
        )  # fmt: skip
    )
    L.append(
        f"Innings 1 and 2: {rep['regulation_innings_total']} innings; "
        f"{rep['shortened_innings']} shortened (limit not 120) in {rep['shortened_matches']} "
        f"matches covering {rep['shortened_deliveries']} deliveries. "
        f"Limit constant within every innings: {rep['limit_constant_within_every_innings']}.\n"
    )
    L.append(f"By innings number: {rep['shortened_innings_by_innings_number']}. ")
    L.append(f"By limit source: {rep.get('shortened_innings_by_limit_source')}. ")
    L.append(f"By format and period: {rep.get('shortened_innings_by_period')}.\n")
    L.append("## Reconciliation of the earlier '48 shortened innings' wording\n")
    src = rep.get("shortened_innings_by_limit_source", {})
    L.append(
        f"The data contain {rep['shortened_innings']} shortened regulation innings. "
        f"`pressure_rules_v1.json` mentions 48 in a sensitivity note. The count by limit source is "
        f"{src}: 48 innings have the limit in the revised-overs field and the remainder carry the "
        "first-innings limit to the second innings without verification. The note's 48 therefore "
        "undercounts by the carried innings; the sensitivity 'exclude shortened innings' must use "
        f"all {rep['shortened_innings']}, which is what `dls_exclude_primary` already does. "
        "The config file is left unchanged (no code reads the note).\n"
    )
    L.append("## No-future-information checks\n")
    L.append(md_table(["check", "result"], [[k, v] for k, v in ph["label_checks"].items()]))
    L.append("## Revision timing (honest caveat)\n")
    L.append(md_table(["item", "value"], [[k, v] for k, v in ph["revision_timing"].items()]))
    L.append("The announcement time of a revision is not in the data, so a label for a ball ")
    L.append("bowled before the announcement may use a limit known only later. All such innings ")
    L.append("are excluded from primary scoring.\n")
    L.append("## DLS exclusions (masks, never deletes; resources never imputed)\n")
    L.append(md_table(["item", "value"], [[k, v] for k, v in ph["dls"].items()]))
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--no-write-store", action="store_true")
    args = ap.parse_args(argv)

    before = snapshot_from_settings(s)
    cfg = load_split_config()
    split = Split.from_config(cfg)
    df = load_state_with_period(split, args.store, ("limit_source", "phase_rule"))

    matches = assign_matches(df, split)
    mp = (
        matches.groupby(["competition_type", "period"])["match_date"]
        .agg(matches="size", first="min", last="max")
        .reset_index()
    )
    mp["first"] = mp["first"].dt.date.astype(str)
    mp["last"] = mp["last"].dt.date.astype(str)
    integrity = check_split_integrity(df, split)
    integrity["matches_total"] = int(len(matches))
    integrity["delivery_rows_total"] = int(len(df))
    integrity["same_date_groups"] = same_date_groups(matches)

    rows, cells = pressure_state_counts(df, cfg)
    ver = verdicts(rows, cells, cfg)

    min_prior = int(cfg["par"]["min_prior_innings"])
    par = p4par.strictly_prior_par(df, min_prior=min_prior)
    cover = p4par.par_coverage(df, par)
    equiv = compare_with_existing_prior(df, par, args.store)
    sens = {}
    for mpi in [min_prior, *cfg["par"]["min_prior_innings_sensitivity"]]:
        alt = p4par.strictly_prior_par(df, min_prior=int(mpi))
        sens[str(mpi)] = int(alt[PAR_FLAG].sum())

    deliv = (
        df.groupby(["competition_type", "period", "innings_number"])
        .size()
        .rename("rows")
        .reset_index()
    )
    deliv = deliv[deliv["innings_number"].isin([1, 2])]

    ph = {
        "shortened": p4ph.shortened_report(df),
        "label_checks": p4ph.check_phase_labels(df),
        "revision_timing": p4ph.revision_timing_summary(df),
        "dls": p4ph.dls_exclusion_summary(df),
    }

    manifest = {
        "status": "EXPERIMENTAL_NOT_VALIDATED",
        "official_ranking": False,
        "split_version": cfg["config_version"],
        "split_config_sha256": file_sha256(SPLIT_CONFIG),
        "seed": cfg["seed"],
        "boundaries": cfg["periods"],
        "matches_by_format_period": mp.to_dict(orient="records"),
        "deliveries_by_format_period_innings": deliv.to_dict(orient="records"),
        "integrity": integrity,
        "pressure_state_counts": rows,
        "player_pressure_ball_distribution": cells,
        "verdicts": ver,
        "par_coverage": cover,
        "par_equivalence": equiv,
        "par_sensitivity": sens,
        "par_min_prior_innings": min_prior,
        "rolling_origins": cfg["rolling_origins"],
        "phases": ph,
    }
    args.reports.mkdir(parents=True, exist_ok=True)
    write_json_deterministic(args.reports / "phase4_split_manifest.json", manifest)
    write_text(args.reports / "phase4_phase_boundaries.md", phase_markdown(ph))
    update_plan_doc(args.reports / "phase4_temporal_validation_plan.md", render_generated(manifest))

    if not args.no_write_store:
        mt = matches.copy()
        mt["split_version"] = cfg["config_version"]
        write_p4_table(mt, "p4_match_period", args.store)
        pt = df[["match_id", "innings_number", "innings_ball_num", "period"]].copy()
        pt = pt[par["par_applicable"].to_numpy()].reset_index(drop=True)
        pr = par[par["par_applicable"]].reset_index(drop=True)
        pt["par_runs_prior"] = pr["par_runs_prior"]
        pt["prior_innings_n"] = pr["par_prior_innings_n"]
        pt[PAR_FLAG] = pr[PAR_FLAG]
        pt["status"] = "EXPERIMENTAL_NOT_VALIDATED"
        write_p4_table(pt, "p4_par_prior", args.store)
        pb = pd.DataFrame(ph["shortened"]["by_limit"]).rename(columns={"limit": "innings_limit"})
        pb["status"] = "EXPERIMENTAL_NOT_VALIDATED"
        write_p4_table(pb, "p4_phase_boundaries", args.store)

    after = snapshot_from_settings(s)
    diff = assert_unchanged(before, after)
    write_json_deterministic(
        args.reports / "phase4_chunk1_preservation.json",
        {"official_data_unchanged": not diff, "differences": diff},
    )
    print(
        f"matches={len(matches)} rows={len(df)} par_unavailable_rows={cover['total_rows_unavailable']}"
    )
    print("official data unchanged:", not diff)
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
