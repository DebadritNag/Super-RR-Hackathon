"""Stage 4: context-adjusted baselines and actual-versus-expected (EXPLORATORY, no ranking).

Builds separate batter and bowler hierarchical empirical-Bayes baselines from the exploratory
pre-delivery state, checks calibration, leave-player-out and leave-match-out variants, shrinkage
(shrink_to_parent, tau2 floor, floor hits) and a seeded bootstrap by match. Writes
data/reports/baseline_methodology_v1.md and baseline_exploration.json. Exit 1 if official data
changed or the calibration identity fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics import baseline_engine as be  # noqa: E402
from app.analytics import pressure_features as pf  # noqa: E402
from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.pressure_distributions import FLOORS  # noqa: E402
from app.analytics.reporting import md_table, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services import pressure_service as ps  # noqa: E402
from scripts.run_pressure_distributions import prepare  # noqa: E402

STATUS = {"status": "EXPLORATORY_NOT_VALIDATED", "official_ranking": False,
          "not_for_publication": True}  # fmt: skip
DIAG = [("chase", "rrr", 0.75), ("chase", "rrr", 0.9), ("inn1", "neg_par_dev", 0.75),
        ("inn1", "neg_par_dev", 0.9)]  # fmt: skip


def union_flag(df, flags, ctx, signal, q, role="batter"):
    sig = signal if role == "batter" else "bowl_signal_B_all"
    out = np.zeros(len(df), dtype=bool)
    for comp in pf.SCOPE:
        out |= flags[f"a|{ctx}|{comp}|{role}|{sig}|abs|{q}"]
    return out


def player_block(d, resid, mask, role, n_boot, seed, floor2):
    ps_ = be.player_match_stats(d, resid, mask)
    boot = be.bootstrap_by_match(ps_, n_boot, seed)
    n = boot["n"]
    ok = n >= floor2
    width = (boot["hi"] - boot["lo"])[ok]
    excl0 = ((boot["lo"] > 0) | (boot["hi"] < 0))[ok]
    inside = ((boot["shrunk"] >= boot["lo"]) & (boot["shrunk"] <= boot["hi"]))[ok]
    # shrink-target sensitivity on the same per-format player sets
    key = ps_["comp"] + "|" + ps_["player_id"].astype(str)
    agg = ps_.assign(k=key).groupby("k").agg(n=("n", "sum"), s=("s", "sum"), s2=("s2", "sum"))
    sh_p = be.shrink_players(agg["n"].to_numpy(), agg["s"].to_numpy(), agg["s2"].to_numpy())
    sh_0 = be.shrink_players(agg["n"].to_numpy(), agg["s"].to_numpy(), agg["s2"].to_numpy(), "zero")
    okp = agg["n"].to_numpy() >= floor2
    return {
        "role": role, "pressure_rows": int(mask.sum()),
        "pressure_sample_mean_residual": float(resid[mask].mean()),
        "players_any": int(len(n)), "players_ge_floor2": int(ok.sum()), "floor2": floor2,
        "median_n_ge_floor2": float(np.median(n[ok])) if ok.any() else None,
        "median_shrunk_ge_floor2": float(np.nanmedian(boot["shrunk"][ok])) if ok.any() else None,
        "median_ci_width_ge_floor2": float(np.nanmedian(width)) if ok.any() else None,
        "share_ci_excludes_zero_ge_floor2": float(excl0.mean()) if ok.any() else None,
        "share_point_inside_ci_ge_floor2": float(inside.mean()) if ok.any() else None,
        "median_matches_ge_floor2": float(np.median(boot["matches"][ok])) if ok.any() else None,
        "eb_k": float(sh_p["k"]), "n_boot": n_boot, "seed": seed,
        "median_abs_shift_target_zero_vs_pooled_all": float(np.nanmedian(np.abs(sh_p["shrunk"] - sh_0["shrunk"]))),
        "median_abs_shift_target_zero_vs_pooled_ge_floor2": float(np.nanmedian(np.abs(sh_p["shrunk"] - sh_0["shrunk"])[okp])) if okp.any() else None,
        "technical_sample": [
            {"player": str(boot["players"][i]), "n": float(n[i]), "matches": int(boot["matches"][i]),
             "shrunk_residual": float(boot["shrunk"][i]), "ci95": [float(boot["lo"][i]), float(boot["hi"][i])],
             "label": "TECHNICAL_SAMPLE_NOT_A_RANKING"}
            for i in np.where(ok)[0][:10]
        ],
    }  # fmt: skip


def env_sensitivity(d, y, expected, resid_mask, rules_params, floor2):
    """Season run-environment offset (LOMO, shrunk to 0) as a sensitivity for the runs stream."""
    from app.analytics.shrinkage import k_from_children, shrink_to_parent

    res = y - expected
    key = (d["competition_type"] + "|" + d["season_label"].astype(str)).to_numpy()
    mt = d["match_id"].to_numpy()
    t = pd.DataFrame({"key": key, "m": mt, "r": res, "r2": res**2, "inn": d["inn_key"].to_numpy()})
    cell = t.groupby("key").agg(n=("r", "size"), s=("r", "sum"), s2=("r2", "sum"),
                                innings=("inn", "nunique"))  # fmt: skip
    own = t.groupby(["key", "m"]).agg(n=("r", "size"), s=("r", "sum")).reset_index()
    own = own.merge(
        cell[["n", "s"]].rename(columns={"n": "cn", "s": "cs"}), left_on="key", right_index=True
    )
    own["off"] = (own["cs"] - own["s"]) / (own["cn"] - own["n"]).where((own["cn"] - own["n"]) > 0)
    kcomp = {}
    for comp in pf.SCOPE:
        c = cell[cell.index.str.startswith(comp + "|")]
        mean = c["s"] / c["n"]
        kk = k_from_children(
            c["n"], c["innings"], mean, c["s2"] - c["s"] ** 2 / c["n"], rules_params["tau2_floor"]
        )
        kcomp[comp] = kk
    omap = own.set_index(["key", "m"])["off"]
    off = omap.reindex(pd.MultiIndex.from_arrays([key, mt])).to_numpy()
    inn = cell["innings"].reindex(key).to_numpy()
    k = np.array([kcomp[x.split("|")[0]]["k"] for x in key])
    off_sh = shrink_to_parent(inn, np.nan_to_num(off), 0.0, k)
    supportable = cell[cell["innings"] >= rules_params["min_cell_innings"]]
    return {
        "season_cells": {k_: {"innings": int(v["innings"]), "rows": int(v["n"]),
                              "mean_residual": float(v["s"] / v["n"])} for k_, v in cell.iterrows()},
        "supportable_cells": int(len(supportable)), "cells": int(len(cell)),
        "k": {c: {"k": v["k"], "tau2": v["tau2"], "floor_hit": v["shrinkage_floor_hit"]}
              for c, v in kcomp.items()},
        "max_abs_offset_runs_per_ball": float(np.nanmax(np.abs(off_sh))),
        "expected_with_season": expected + off_sh,
        "status": "SENSITIVITY_ONLY_DEFAULT_OFF",
    }  # fmt: skip


def venue_counts(df, rules_params):
    d = df[df["base_pop"]]
    g = d.groupby("venue_id")["inn_key"].nunique()
    return {"venues": int(len(g)), "venues_ge_min_cell_innings": int((g >= rules_params["min_cell_innings"]).sum()),
            "max_innings": int(g.max()), "status": "NOT_USED_IN_BASELINE"}  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--store", type=Path, default=ps.EXPLORATORY_DB)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument("--n-boot", type=int, default=None)
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s, args.db)
    rules, df, meta = prepare(args.store)
    specs, flags = pf.build_candidates(df, rules)
    P = {"min_cell_innings": int(pf.param(rules, "min_cell_innings")),
         "tau2_floor": float(pf.param(rules, "tau2_floor"))}  # fmt: skip
    bs = pf.param(rules, "bootstrap")
    n_boot = args.n_boot or int(bs["n_resamples_baseline"])
    seed = int(bs["seed"])

    bat, bowl = be.batter_frame(df), be.bowler_frame(df)
    result: dict = {**STATUS, "config": {**P, "n_boot": n_boot, "seed": seed},
                    "frames": {"batter_rows": len(bat), "bowler_rows": len(bowl)}}  # fmt: skip
    summaries = {"batter": {}, "bowler": {}}
    built = {"batter": {}, "bowler": {}}
    for role, d, streams in (
        ("batter", bat, be.BATTER_STREAMS),
        ("bowler", bowl, be.BOWLER_STREAMS),
    ):
        for st, binary in streams.items():
            r = be.build_stream(d, st, binary, P)
            built[role][st] = r
            summaries[role][st] = be.stream_summary(r, be.LEVEL_NAMES)
    result["streams"] = summaries
    # tau2_floor sensitivity (spec section 8: 0.001 and 0.1, report floor-hit counts)
    tsens = []
    for tf in rules["parameters"]["tau2_floor"]["sensitivity"]:
        for role, d, streams in (("batter", bat, be.BATTER_STREAMS),
                                 ("bowler", bowl, be.BOWLER_STREAMS)):  # fmt: skip
            for st, binary in streams.items():
                r = be.build_stream(d, st, binary, {**P, "tau2_floor": float(tf)})
                base = built[role][st]["leave_player_out"]["expected"]
                e = r["leave_player_out"]
                tsens.append({"tau2_floor": float(tf), "role": role, "stream": st,
                              "floor_hit_rows": int(e["floor_hit"].sum()),
                              "floor_hit_parents": sum(p["floor_hit_parents"] for p in e["parents_info"]),
                              "mean_abs_diff_vs_primary": float(np.mean(np.abs(e["expected"] - base))),
                              "max_abs_diff_vs_primary": float(np.max(np.abs(e["expected"] - base)))})  # fmt: skip
    result["tau2_floor_sensitivity"] = tsens
    # reproducibility: rebuild one stream and compare
    r2 = be.build_stream(bat, "runs", False, P)
    result["reproducible_second_run_identical"] = bool(
        np.array_equal(r2["leave_player_out"]["expected"], built["batter"]["runs"]["leave_player_out"]["expected"],
                       equal_nan=True))  # fmt: skip
    # phase context: raw rates versus expectation (no raw death vs ordinary comparison)
    ctx_rows = []
    for role, d, stream in (("batter", bat, "runs"), ("bowler", bowl, "charged")):
        e = built[role][stream]["leave_player_out"]["expected"]
        t = pd.DataFrame({"comp": d["competition_type"], "ctx": d["role_ctx"], "phase": d["innings_phase"],
                          "actual": d[stream].to_numpy(), "expected": e})  # fmt: skip
        g = (
            t.groupby(["comp", "ctx", "phase"])
            .agg(rows=("actual", "size"), actual=("actual", "mean"), expected=("expected", "mean"))
            .reset_index()
        )
        for r in g.itertuples():
            ctx_rows.append({"role": role, "stream": stream, "comp": r.comp, "ctx": r.ctx,
                             "phase": r.phase, "rows": int(r.rows), "actual_mean": float(r.actual),
                             "expected_mean_lpo": float(r.expected),
                             "mean_residual": float(r.actual - r.expected)})  # fmt: skip
    result["phase_context"] = ctx_rows
    # pressure-sample actual versus expected under B0 and per-candidate baselines
    floors = FLOORS
    cand = []
    pl_block = {}
    for ctx, sig, q in DIAG:
        fb = union_flag(df, flags, ctx, sig, q, "batter")[bat["_src_index"].to_numpy()]
        fw = union_flag(df, flags, ctx, sig, q, "bowler")[bowl["_src_index"].to_numpy()]
        entry = {"ctx": ctx, "signal": sig, "q": q, "status": "DIAGNOSTIC_NOT_A_SELECTION"}
        for role, d, flag, st, bn in (("batter", bat, fb, "runs", False), ("bowler", bowl, fw, "charged", False),
                                      ("bowler", bowl, fw, "wkt", True)):  # fmt: skip
            b0 = built[role][st]["leave_player_out"]["expected"]
            y = built[role][st]["y"]
            rc = be.build_stream(d, st, bn, P, pressure=flag)
            ec = rc["leave_player_out"]
            entry[f"{role}_{st}"] = {
                "pressure_rows": int(flag.sum()),
                "b0_mean_residual_pressure_sample": float((y - b0)[flag].mean()),
                "candidate_baseline_mean_residual_pressure_sample": float((y - ec["expected"])[flag].mean()),
                "candidate_baseline_calibration": be.calibration(y, rc["pooled"]["raw_cell_mean"], rc["levels"][0]),
                "exp_cell_level_used": {str(i): int((ec["level_used"] == i).sum()) for i in range(rc["n_levels"])},
                "shrinkage_floor_hit_rows": int(ec["floor_hit"].sum()),
            }  # fmt: skip
        cand.append(entry)
        if (ctx, sig, q) == ("chase", "rrr", 0.75):
            yb = built["batter"]["runs"]
            pl_block["batter_runs"] = player_block(
                bat,
                yb["y"] - yb["leave_player_out"]["expected"],
                fb,
                "batter",
                n_boot,
                seed,
                floors["batter"]["balls"][1],
            )
            yc = built["bowler"]["charged"]
            pl_block["bowler_charged"] = player_block(
                bowl,
                yc["y"] - yc["leave_player_out"]["expected"],
                fw,
                "bowler",
                n_boot,
                seed,
                floors["bowler"]["balls"][1],
            )
            yw = built["bowler"]["wkt"]
            pl_block["bowler_wkt"] = player_block(
                bowl,
                yw["y"] - yw["leave_player_out"]["expected"],
                fw,
                "bowler",
                n_boot,
                seed,
                floors["bowler"]["balls"][1],
            )
            env = env_sensitivity(bat, yb["y"], yb["leave_player_out"]["expected"], fb, P, 60)
            exp_env = env.pop("expected_with_season")
            base_res = yb["y"] - yb["leave_player_out"]["expected"]
            env_res = yb["y"] - exp_env
            a = (
                be.player_match_stats(bat, base_res, fb)
                .groupby(["comp", "player_id"])[["n", "s", "s2"]]
                .sum()
            )
            b = (
                be.player_match_stats(bat, env_res, fb)
                .groupby(["comp", "player_id"])[["n", "s", "s2"]]
                .sum()
            )
            sa = be.shrink_players(a["n"].to_numpy(), a["s"].to_numpy(), a["s2"].to_numpy())[
                "shrunk"
            ]
            sb = be.shrink_players(b["n"].to_numpy(), b["s"].to_numpy(), b["s2"].to_numpy())[
                "shrunk"
            ]
            env["median_abs_shift_in_shrunk_residual_runs_per_ball"] = float(
                np.nanmedian(np.abs(sa - sb))
            )
            env["max_abs_shift_in_shrunk_residual_runs_per_ball"] = float(
                np.nanmax(np.abs(sa - sb))
            )
            env["sensitivity_candidate"] = "chase|rrr|abs|q0.75 (batter runs)"
            result["season_environment"] = env
    result["candidate_baselines"] = cand
    result["players"] = pl_block
    result["venue"] = venue_counts(df, P)
    result["floors_source"] = "Phase 2.5 eligibility_rules_v1 ladders (balls rung 2)"
    cal_ok = all(v["calibration_identity"]["max_abs_cell_residual"] < 1e-6
                 for r in summaries.values() for v in r.values())  # fmt: skip
    result["calibration_identity_holds"] = bool(cal_ok)
    out = args.reports_dir
    write_json_deterministic(out / "baseline_exploration.json", result)
    write_text(out / "baseline_methodology_v1.md", render(result))
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    print(
        f"calibration_identity_holds={cal_ok} reproducible={result['reproducible_second_run_identical']} "
        f"official_unchanged={not diff}"
    )
    return 0 if (cal_ok and not diff and result["reproducible_second_run_identical"]) else 1


def render(r: dict) -> str:
    L = ["# Baseline methodology v1 (Phase 3 Stage 4, EXPLORATORY)\n"]
    L.append(
        "Status `EXPLORATORY_NOT_VALIDATED`, official_ranking `False`, not_for_publication `True`.\n"
    )
    L.append("""## 1. Status: exploratory versus validated

- **Validated numbers in this document: none.** Every figure is an exploratory computation on the
  official DuckDB through the pre-delivery state table.
- The baseline estimates what a typical delivery in the same context would produce. Actual minus
  expected (AvE) is a diagnostic residual, not a pressure score and not a ranking.
- Expectations, shrinkage hyperparameters and bootstrap results here are FULL_SAMPLE and descriptive.
  Predictive use needs the strictly-prior variant and the temporal split of the validation plan.
- No model is trained. Players appear only as `player_id` in the technical sample, flagged
  `TECHNICAL_SAMPLE_NOT_A_RANKING`.
""")
    L.append("## 2. Design\n")
    L.append(
        """Separate baselines for batters and bowlers (different outcomes and different denominators).

| Role | Row unit | Streams |
|---|---|---|
| Batter | one ball faced (innings 1/2, not wide, not Penalty; the Phase 2.5 `BATTER_SQL` definition) | runs off the bat, dot, boundary, dismissal (striker dismissed, not Retire Out) |
| Bowler | one delivery charged to the bowler (all rows except Penalty, so wides and no-balls count) | charged runs (`BOWLER_SQL` definition), wicket credited to the bowler (Caught, Bowled, LBW, Stump, Hit Wicket), dot (legal ball, 0 runs), boundary |

Context controls (the cell): competition type (IPL/T20I), innings role (innings 1 or chase), innings
phase (powerplay/middle/death from the legal over index), wickets-remaining bin (global partition
from the Stage 3 merge). Match state enters through the role (chase versus innings 1) and, in the
per-candidate sensitivity baselines, through pressure membership as the finest level. The reference
baseline B0 has no pressure term, so it does not depend on any candidate definition.

Hierarchy (finest to coarsest): `comp|role|phase|wbin` -> `comp|role|phase` -> `comp|role` -> `comp`.
Per-candidate baselines add `pressure membership` as a new finest level above `L0`.

Estimator: for each level the cell mean (with the leave-out group removed) is shrunk to the value of
its parent level. Continuous streams use `shrink_to_parent(n_eff, cell_mean, parent_mean, k)`;
binary streams use `beta_binomial_shrink` with counts scaled by the design effect `n_eff / n`.
`k = sigma2_within / tau2` with `tau2 = max(between_moment, tau2_floor * sigma2_within)` and
`tau2_floor = %(tau2_floor)s`, so `k <= 1 / tau2_floor` and a zero or negative moment gives the
strongest shrinkage, never `k = 0`. `shrinkage_floor_hit` is recorded when the floor binds.
`n_eff` is the Kish effective number of innings in the cell (innings clustering, spec section 6
rule 6). This is conservative: the per-delivery variance is divided by an innings-sized count.
A cell with fewer than `min_cell_innings = %(min_cell_innings)s` distinct innings takes its parent value
entirely; the level actually used is recorded for every row as `exp_cell_level_used`.

Leave-out variants: `pooled` (descriptive B0), `leave_player_out` (a player's own deliveries never set
their own expectation; the primary variant for AvE), `leave_match_out` (the whole match removed; always
reported as a named sensitivity). `k` and the Kish sizes are FULL_SAMPLE hyperparameters.
A `strictly_prior` baseline is not built in this chunk.
"""
        % {
            "tau2_floor": r["config"]["tau2_floor"],
            "min_cell_innings": r["config"]["min_cell_innings"],
        }
    )
    L.append("## 3. Calibration identity (code-correctness check on RAW cell means)\n")
    L.append(
        "Inside every finest cell the sum of actual outcomes equals the sum of the raw pooled cell mean. "
        "Shrunk and leave-out expectations deliberately break this identity; their totals are shown beside it.\n"
    )
    rows = []
    for role, st in r["streams"].items():
        for name, v in st.items():
            rows.append(
                [
                    role,
                    name,
                    v["n"],
                    v["actual_mean"],
                    v["calibration_identity"]["cells"],
                    v["calibration_identity"]["max_abs_cell_residual"],
                    v["pooled"]["total_actual_minus_expected"],
                    v["leave_player_out"]["total_actual_minus_expected"],
                    v["leave_match_out"]["total_actual_minus_expected"],
                ]
            )
    L.append(
        md_table(
            [
                "role",
                "stream",
                "rows",
                "actual mean",
                "finest cells",
                "max |cell residual| (raw)",
                "sum(A-E) pooled shrunk",
                "sum(A-E) leave-player-out",
                "sum(A-E) leave-match-out",
            ],
            rows,
        )
    )
    L.append(
        f"Calibration identity holds for all streams: **{r['calibration_identity_holds']}**. "
        f"Second run identical (determinism): **{r['reproducible_second_run_identical']}**.\n"
    )
    L.append("## 4. Expected-value plausibility and levels used\n")
    rows = []
    for role, st in r["streams"].items():
        for name, v in st.items():
            lp = v["leave_player_out"]
            rows.append(
                [
                    role,
                    name,
                    lp["expected_min"],
                    lp["expected_mean"],
                    lp["expected_max"],
                    lp["n_nan"],
                    lp["mean_abs_diff_vs_pooled"],
                    v["leave_match_out"]["mean_abs_diff_vs_pooled"],
                ]
            )
    L.append(
        md_table(
            [
                "role",
                "stream",
                "expected min",
                "mean",
                "max",
                "NaN",
                "mean |LPO - pooled|",
                "mean |LMO - pooled|",
            ],
            rows,
        )
    )
    L.append("`exp_cell_level_used` (leave-player-out, rows per level) and shrinkage floor hits:\n")
    rows = []
    for role, st in r["streams"].items():
        for name, v in st.items():
            lp = v["leave_player_out"]
            c = lp["exp_cell_level_used"]
            rows.append(
                [role, name]
                + [c.get(n, 0) for n in be.LEVEL_NAMES]
                + [
                    lp["shrinkage_floor_hit_rows"],
                    sum(p["floor_hit_parents"] for p in lp["parents_info"]),
                    sum(p["parents"] for p in lp["parents_info"]),
                ]
            )
    L.append(
        md_table(
            ["role", "stream"]
            + be.LEVEL_NAMES
            + ["floor-hit rows", "floor-hit parents", "parents"],
            rows,
        )
    )
    L.append(
        "## 5. Phase context: raw rates are never compared across phases without expectation\n"
    )
    L.append(
        "Raw runs per ball differ strongly by phase. The expectation sits inside the phase cell, so the residual "
        "(actual minus expected) removes the phase effect before any player comparison.\n"
    )
    L.append(
        md_table(
            [
                "role",
                "stream",
                "comp",
                "ctx",
                "phase",
                "rows",
                "actual mean",
                "expected mean (LPO)",
                "mean residual",
            ],
            [
                [
                    x["role"],
                    x["stream"],
                    x["comp"],
                    x["ctx"],
                    x["phase"],
                    x["rows"],
                    x["actual_mean"],
                    x["expected_mean_lpo"],
                    x["mean_residual"],
                ]
                for x in r["phase_context"]
            ],
        )
    )
    L.append(
        "## 6. Pressure samples: B0 versus per-candidate baselines (diagnostic, not a selection)\n"
    )
    L.append(
        "B0 has no match-state or pressure term, so its mean residual in a pressure sample is not zero. The "
        "per-candidate baseline adds pressure membership and is the match-state control for that candidate. "
        "Four candidate definitions are used as diagnostics here; the other candidates are not built in this chunk.\n"
    )
    rows = []
    for c in r["candidate_baselines"]:
        for k, v in c.items():
            if isinstance(v, dict) and "pressure_rows" in v:
                rows.append(
                    [
                        c["ctx"],
                        c["signal"],
                        c["q"],
                        k,
                        v["pressure_rows"],
                        v["b0_mean_residual_pressure_sample"],
                        v["candidate_baseline_mean_residual_pressure_sample"],
                        v["candidate_baseline_calibration"]["max_abs_cell_residual"],
                        v["shrinkage_floor_hit_rows"],
                    ]
                )
    L.append(
        md_table(
            [
                "ctx",
                "signal",
                "q",
                "role_stream",
                "pressure rows",
                "B0 mean residual",
                "candidate-baseline mean residual",
                "calibration max |cell residual|",
                "floor-hit rows",
            ],
            rows,
        )
    )
    L.append(
        "## 7. Player actual-versus-expected, shrinkage and bootstrap (technical illustration)\n"
    )
    L.append(
        "Pressure sample: chase, RRR >= p75 (absolute, per format), used only to exercise the machinery. Residuals are "
        "leave-player-out B0. Each player-format is shrunk towards the pooled mean residual of OTHER players "
        "(FULL_SAMPLE, descriptive; strictly prior when used predictively); target 0 is the named sensitivity. "
        f"Bootstrap by match, stratified by format, seed {r['config']['seed']}, {r['config']['n_boot']} resamples, "
        "baseline held fixed inside the resample (the prior k is re-estimated per resample).\n"
    )
    rows = []
    for name, v in r["players"].items():
        rows.append(
            [
                name,
                v["pressure_rows"],
                v["pressure_sample_mean_residual"],
                v["players_any"],
                v["floor2"],
                v["players_ge_floor2"],
                v["median_n_ge_floor2"],
                v["median_matches_ge_floor2"],
                v["median_shrunk_ge_floor2"],
                v["median_ci_width_ge_floor2"],
                v["share_ci_excludes_zero_ge_floor2"],
                v["share_point_inside_ci_ge_floor2"],
                v["eb_k"],
                v["median_abs_shift_target_zero_vs_pooled_all"],
                v["median_abs_shift_target_zero_vs_pooled_ge_floor2"],
            ]
        )
    L.append(
        md_table(
            [
                "stream",
                "pressure rows",
                "pressure-sample mean residual",
                "player-formats",
                "floor 2",
                "players >= floor 2",
                "median n",
                "median matches",
                "median shrunk AvE",
                "median CI width",
                "share CI excludes 0",
                "share point inside CI",
                "eb k",
                "|shift| target 0 vs pooled (all)",
                "|shift| target 0 vs pooled (>= floor 2)",
            ],
            rows,
        )
    )
    L.append(
        "Technical sample (first ten `comp|player_id` with enough observations; ordered by id, not by value):\n"
    )
    for name, v in r["players"].items():
        L.append(f"**{name}**\n")
        L.append(
            md_table(
                [
                    "player (comp|id)",
                    "n",
                    "matches",
                    "shrunk residual",
                    "CI low",
                    "CI high",
                    "label",
                ],
                [
                    [
                        t["player"],
                        t["n"],
                        t["matches"],
                        t["shrunk_residual"],
                        t["ci95"][0],
                        t["ci95"][1],
                        t["label"],
                    ]
                    for t in v["technical_sample"]
                ],
            )
        )
    L.append(
        "The percentile interval comes from the bootstrap distribution with the shrinkage prior "
        "re-estimated in every resample. When the between-player variance is barely identified "
        "(wicket stream: eb k in the thousands) the full-sample point estimate can sit outside "
        "its own interval; the column share point inside CI reports how often this happens. "
        "Such intervals describe prior instability, not player skill.\n"
    )
    L.append("### tau2_floor sensitivity\n")
    L.append(
        "The floor is a fraction of the per-delivery within-cell variance, so it binds in most parents "
        "(the between-cell variance of runs per ball is small relative to the per-ball variance). "
        "Rows below show the leave-player-out expectation under the two sensitivity values.\n"
    )
    L.append(
        md_table(
            [
                "tau2_floor",
                "role",
                "stream",
                "floor-hit rows",
                "floor-hit parents",
                "mean |E - E_primary|",
                "max |E - E_primary|",
            ],
            [
                [
                    x["tau2_floor"],
                    x["role"],
                    x["stream"],
                    x["floor_hit_rows"],
                    x["floor_hit_parents"],
                    x["mean_abs_diff_vs_primary"],
                    x["max_abs_diff_vs_primary"],
                ]
                for x in r["tau2_floor_sensitivity"]
            ],
        )
    )
    L.append("## 8. Season, competition and venue environment\n")
    L.append(
        "Competition: for IPL one competition is one season, so a competition offset equals the season "
        "offset below. T20I competitions are many small tournaments and are not supportable as cells; "
        "the T20I season offset is used instead.\n"
    )
    env = r["season_environment"]
    L.append(
        f"Season cells: {env['cells']} (comp x season), supportable (>= {r['config']['min_cell_innings']} distinct "
        f"innings): {env['supportable_cells']}. A leave-one-match-out season offset on the batter runs residual, shrunk to 0, "
        f"was run as a sensitivity (`{env['status']}`): maximum |offset| {env['max_abs_offset_runs_per_ball']:.4f} runs per ball; "
        f"effect on shrunk player residuals (median |shift|) {env['median_abs_shift_in_shrunk_residual_runs_per_ball']:.5f}, "
        f"(max) {env['max_abs_shift_in_shrunk_residual_runs_per_ball']:.5f}. The primary baseline does not use it.\n"
    )
    L.append(
        md_table(
            ["comp|season", "innings", "rows", "mean residual (runs/ball)"],
            [
                [k, v["innings"], v["rows"], v["mean_residual"]]
                for k, v in env["season_cells"].items()
            ],
        )
    )
    ven = r["venue"]
    L.append(
        f"Venue: {ven['venues']} venues, {ven['venues_ge_min_cell_innings']} with at least "
        f"{r['config']['min_cell_innings']} innings (max {ven['max_innings']}). `{ven['status']}`: venue cells are too sparse "
        "for a per-venue baseline without further pooling, and pitch or dew data are absent.\n"
    )
    L.append("## 9. Model options considered and not used\n")
    L.append("""| Option | Why not now |
|---|---|
| Regularised logistic regression (dot, boundary, wicket) and linear/Poisson models for runs | Adds tuning freedom before the pressure definition is approved; needs the temporal-holdout calibration first |
| Gradient boosting | Same, plus interpretability cost; would hide the context cells that the report shows |
| Mixed models with player random effects | Player effects are exactly what the baseline must not absorb; reserved for the validation phase |
| Per-venue or per-season cells | Sparse (section 8); offered only as a sensitivity |

Nothing is trained in this phase.
""")
    L.append("## 10. Validation plan (not run here)\n")
    L.append("""1. Strictly-prior baselines and a temporal split (fit before a cut date, evaluate later).
2. Calibration of expected versus actual by decile and pressure band on the held-out period.
3. Ablation of wickets bins, phase and pressure membership; `min_cell_innings` 15/30/60; `tau2_floor` 0.001/0.01/0.1.
4. Rank stability across neighbouring thresholds and candidate definitions (Stage 5).
5. DQ sensitivities: `other` extras rows in and out, wicket-flag disagreement rows, ten Cricsheet-total innings.
""")
    L.append("## 11. Limitations\n")
    L.append("""1. Context is limited to format, innings role, phase and wickets bin (plus pressure membership in the sensitivity). Opposition, venue, pitch and weather are not controlled.
2. `n_eff` is a Kish count of innings; with per-delivery variance it over-shrinks, which is the conservative direction.
3. The bootstrap resamples matches but holds the baseline fixed; a refit-inside variant is not built.
4. Pressure-sample residuals under B0 are not zero because B0 has no match-state term; they are not a skill estimate.
5. The Stage 5 eligibility experiment and the Stage 6 weight sensitivity are separate steps awaiting approval.
""")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
