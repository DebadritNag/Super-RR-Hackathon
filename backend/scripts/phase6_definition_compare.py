"""Phase 6: compare the nine pressure definitions on the pre-declared reliability criteria.

Refuses to run when the criteria file or its hash is missing or changed (see
``app.phase6.criteria``) or when stored results were made under another criteria hash. Writes
``p6_definition_reliability``, ``p6_definition_summary``, ``p6_definition_resampling``,
``p6_definition_outcome`` and ``phase6_definition_reliability_comparison.md/json/csv``. TEST rows
are never loaded, no lock event is created, Cricsheet is not an input, no player is named.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import code_version, md_table, write_text  # noqa: E402
from app.phase5 import pipeline as pl  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6 import criteria as cr  # noqa: E402
from app.phase6 import definition_compare as dc  # noqa: E402
from app.phase6.constants import (  # noqa: E402
    CRITERIA_FILE,
    CRITERIA_HASH_FILE,
    INVESTIGATION_CONFIG,
    STATUS,
)
from app.phase6.lockguard import assert_lock_state_unchanged, lock_state  # noqa: E402
from app.phase6.outputs import Preservation, rows_of, save_table  # noqa: E402
from app.phase6.store import table_hashes  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

NAME = "phase6_definition_reliability_comparison"


def _stamp(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    out = df.copy()
    for k, v in meta.items():
        out[k] = v
    return out


def render(res: dict) -> str:
    cells, summ, outc = res["cells"], res["summary"], res["outcome"]
    pre_c = cells[cells["window"] == "PRE_TEST"]
    pre_s = summ[summ["window"] == "PRE_TEST"].sort_values("definition")
    trn_s = summ[summ["window"] == "TRAIN"].sort_values("definition")
    final = outc[outc["window"] == "FINAL"].iloc[0]
    pre_o = outc[outc["window"] == "PRE_TEST"].iloc[0]
    trn_o = outc[outc["window"] == "TRAIN"].iloc[0]
    est = pre_c[pre_c["status"] == "ESTIMATED"]
    mid_below = int((0.5 * (est["sb_lo"] + est["sb_hi"]) < est["sb"]).sum())
    sizes = json.loads(pre_o["intersection_sizes"])
    L = [
        "# Phase 6 definition reliability comparison",
        "",
        f"Status: {STATUS}. INTERNAL, `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. TEST outcomes: not "
        "used. Cricsheet: not used. No gate, threshold or Phase 4/5 artifact was changed. "
        f"Code version `{res['code_version'][:16]}`, seed {res['seed']}, {res['n_boot']} "
        f"match-cluster bootstrap draws. Criteria SHA-256 `{res['criteria']['sha256']}` (declared "
        f"before any estimator output; run-log seq {res['criteria']['seq']} for this step).",
        "",
        "**This report names no player and selects nothing.** The comparison uses only the "
        "metrics and the rule in the criteria file. The provisional definition `any|q0.75` stays "
        "provisional whatever the table says; a change needs a user decision. Nine candidates were "
        "examined side by side and no multiplicity correction was applied, so any top group is "
        "provisional.",
        "",
        "## 1. Result",
        f"- Final status: **{final['status']}**.",
        f"- Pass list (PRE_TEST): {json.loads(pre_o['pass_list']) or 'none'}.",
        f"- Top group named: {json.loads(final['top_group']) or 'none'}.",
        f"- PRE_TEST status {pre_o['status']}; TRAIN-only status {trn_o['status']}; stability: "
        f"{final['stability']} (TRAIN top group {json.loads(trn_o['top_group']) or 'none'}).",
        f"- Individuals eligible under all nine definitions (PRE_TEST odd/even, at least "
        f"{res['min_half']} balls per half), per format and role: {sizes}. The rule needs at least "
        f"{dc.MIN_INTERSECTION} in every cell to use the intersection versions of M1 and M5; "
        f"otherwise it reports `{dc.CONFOUNDED}` and the pass list only. Confounded: "
        f"{bool(pre_o['confounded'])}. The intersection versions (M1 int., M5 int.) pool only the "
        f"cells that keep at least {res['min_players']} individuals and are not interpretable "
        "when the intersection is this small; they are shown for completeness.",
        "",
        "## 2. Rule and metrics (from the criteria file, not edited here)",
        f"- R: {res['crit']['metrics']['R']}.",
        f"- Rule: {res['crit']['rule']}",
        f"- Stability: {res['crit']['stability_outcomes']}.",
        f"- Confound control: {res['crit']['confound_control']}.",
        "- M1 is the Spearman-Brown corrected value of the Fisher-z pooled Pearson correlation of "
        "the four cells (weights n - 3, clip 0.99). SE1 is the SD over bootstrap draws of that "
        "pooled value. M4 uses individuals estimable for the odd/even split; the same median over "
        "all individuals with pressure balls is in the cell table. M2, M3 and M6 are descriptive "
        "and never enter the rule.",
        "",
        "## 3. Definition summary, PRE_TEST (primary streams, four format x role cells)",
        "",
        md_table(
            [
                "definition",
                "cells est.",
                "cells lo>0",
                "passes",
                "M1",
                "SE1",
                "M1 int.",
                "SE1 int.",
                "cells int.",
                "M4 balls",
                "M5",
                "M5 int.",
                "M2 mean",
                "M3 mean",
                "M6 mean",
            ],
            rows_of(
                pre_s,
                [
                    "definition",
                    "cells_estimable",
                    "cells_lo_positive",
                    "passes",
                    "m1",
                    "se1",
                    "m1_int",
                    "se1_int",
                    "cells_int",
                    "m4",
                    "m5",
                    "m5_int",
                    "m2_mean",
                    "m3_mean",
                    "m6_mean",
                ],
            ),
        ),
        "",
        "## 3b. Where the interval lower bound is above 0 (PRE_TEST, nine definitions)",
        "",
        md_table(
            ["format", "role", "definitions with lo > 0", "definitions estimable"],
            [
                [f, r, int((g["sb_lo"] > 0).sum()), int((g["status"] == "ESTIMATED").sum())]
                for (f, r), g in pre_c.groupby(["format", "role"])
            ],
        ),
        "",
        "## 4. Cells, PRE_TEST (odd/even Spearman-Brown R and its match-cluster bootstrap interval)",
        "",
        md_table(
            [
                "definition",
                "format",
                "role",
                "status",
                "individuals",
                "R (SB)",
                "lo",
                "hi",
                "share draws <= 0",
                "M2",
                "M3",
                "M4 balls",
                "M5 median",
                "M5 p5",
                "M6 control SB",
            ],
            rows_of(
                pre_c.sort_values(["definition", "format", "role"]),
                [
                    "definition",
                    "format",
                    "role",
                    "status",
                    "players",
                    "sb",
                    "sb_lo",
                    "sb_hi",
                    "share_nonpositive",
                    "m2_signal_share",
                    "m3_share_excluding_cell_mean",
                    "m4_median_balls",
                    "m5_median",
                    "m5_p5",
                    "m6_control_sb",
                ],
            ),
        ),
        "",
        "## 5. Resampling instability (M5)",
        "For each of the bootstrap resamples of matches the per-individual mean residual is "
        "recomputed and its Spearman correlation with the full-window ordering is taken over the "
        "individuals estimable for the split. M5 is the median over resamples; the 5th percentile "
        "shows the bad end. Values are in the cell table above and in "
        "`p6_definition_resampling`. A low M5 means a different set of matches would reorder "
        "individuals markedly.",
        "",
        md_table(
            ["definition", "M5 (median over cells)", "M5 intersection", "M4 balls"],
            rows_of(pre_s, ["definition", "m5", "m5_int", "m4"]),
        ),
        "",
        "## 6. TRAIN-only repeat (stability check)",
        "",
        md_table(
            ["definition", "cells est.", "cells lo>0", "passes", "M1", "SE1", "M1 int.", "M5"],
            rows_of(
                trn_s,
                [
                    "definition",
                    "cells_estimable",
                    "cells_lo_positive",
                    "passes",
                    "m1",
                    "se1",
                    "m1_int",
                    "m5",
                ],
            ),
        ),
        "",
        "## 7. Limits",
        "- In-sample. Thresholds, baseline and pressure flags were fitted on TRAIN; this is a "
        "diagnostic of measurement reliability, not validation, and a definition that passes is "
        "not shown to measure pressure skill.",
        "- The definitions differ in how many balls each individual contributes (M4). Higher "
        "reliability can come from more balls rather than a better definition; the intersection "
        "versions control for the set of individuals, not for the ball count.",
        f"- The match-cluster bootstrap interval is not centred on the point estimate (midpoint "
        f"below the point estimate in {mid_below}/{len(est)} PRE_TEST cells). Counts of 'lower "
        "bound above 0' are therefore conservative or inconsistent and must be read with that in "
        "mind.",
        "- Individuals with at least 6 balls in each half are a selected, more active subset.",
        "- The M6 control draws, for every player-match of the pressure sample, the same number "
        "of non-pressure balls (or all of them when fewer exist). It shows reliability that "
        "ordinary balls give at a comparable sample size and is never a selection input.",
        "- No player identity, score level, rank or Top-10 membership entered the rule; the "
        "output tables have no player column.",
        "- Cross-checks inside the same data (TRAIN versus PRE_TEST, intersection versus all "
        "individuals) are consistency checks, not independent validation.",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--criteria", type=Path, default=CRITERIA_FILE)
    ap.add_argument("--criteria-hash", type=Path, default=CRITERIA_HASH_FILE)
    ap.add_argument("--n-boot", type=int, default=None)
    args = ap.parse_args(argv)
    t0 = time.time()
    rep, store = args.reports, args.store
    guard = Preservation(rep)
    lock_before = lock_state()
    p4_before, p5_before = table_hashes(store, "p4_"), table_hashes(store, "p5_")
    try:
        info = dc.begin_comparison(args.criteria, args.criteria_hash, INVESTIGATION_CONFIG, store)
    except cr.CriteriaError as e:
        print(f"REFUSED: {e}")
        return 1
    cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    crit = cr.load_criteria(args.criteria)
    n_boot = int(args.n_boot or crit["split_half"]["bootstrap_draws"])
    study = pl.load_study(store, n_boot=n_boot, seed=cfg["seed"])
    defns = cfg["definitions"]["candidates"]
    meta = {"fit_on": "WINDOW_IN_SAMPLE", "seed": study.seed, "n_boot": n_boot,
            "criteria_sha256": info["sha256"]}  # fmt: skip
    cells_l, summ_l, outcomes = [], [], {}
    for window in dc.WINDOWS:
        c, s, o = dc.evaluate_window(study, defns, window, crit, control=window == "PRE_TEST",
                                     progress=lambda m: print("done", m, flush=True))  # fmt: skip
        cells_l.append(c)
        summ_l.append(s)
        outcomes[window] = o
    cells, summ = pd.concat(cells_l, ignore_index=True), pd.concat(summ_l, ignore_index=True)
    final = dc.stability(outcomes["PRE_TEST"], outcomes["TRAIN"])
    outc = dc.outcome_table(outcomes, final, {"label": "IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION",
                                              **meta})  # fmt: skip
    cells, summ = _stamp(cells, meta), _stamp(summ, meta)
    resamp = _stamp(dc.resampling_table(cells), meta)
    for df in (cells, summ, resamp, outc):
        dc.assert_no_player_columns(df)
    # criteria must still be intact right before the results are written
    cr.verify_criteria(args.criteria, args.criteria_hash, store)
    save_table(cells, NAME, rep, store, "p6_definition_reliability")
    save_table(summ, f"{NAME}_summary", rep, store, "p6_definition_summary")
    save_table(resamp, f"{NAME}_resampling", rep, store, "p6_definition_resampling")
    save_table(outc, f"{NAME}_outcome", rep, store, "p6_definition_outcome")
    res = {"cells": cells, "summary": summ, "outcome": outc, "criteria": info, "crit": crit,
           "seed": study.seed, "n_boot": n_boot, "code_version": code_version(),
           "min_half": crit["split_half"]["min_balls_per_half"],
           "min_players": crit["split_half"]["min_individuals_estimable"]}  # fmt: skip
    write_text(rep / f"{NAME}.md", render(res))
    if table_hashes(store, "p4_") != p4_before or table_hashes(store, "p5_") != p5_before:
        print("FATAL: a p4_ or p5_ table changed")
        return 1
    assert_lock_state_unchanged(lock_before)
    pres = guard.verify()
    if not pres["all_preserved"]:
        print("FATAL: preservation failed", pres)
        return 1
    print(json.dumps({"seconds": round(time.time() - t0, 1), "cell_rows": len(cells),
                      "final_status": final["status"], "pass_list": final["pass_list"],
                      "top_group": final["top_group"], "stability": final.get("stability"),
                      "preservation": pres}, default=str))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
