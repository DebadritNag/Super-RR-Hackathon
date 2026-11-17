"""Phase 6: declare the investigation before any result exists.

Writes ``config/phase6_selection_criteria_v1.json``, its SHA-256 hash file, the run-log row
``seq = 1`` in ``p6_run_log`` and ``data/reports/phase6_investigation_plan.md``. Re-running with
unchanged criteria is a no-op for the criteria; different criteria are refused.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import md_table, write_text  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6 import criteria as cr  # noqa: E402
from app.phase6.constants import (  # noqa: E402
    CRITERIA_FILE,
    CRITERIA_HASH_FILE,
    INVESTIGATION_CONFIG,
    PLAN_REPORT,
    STATUS,
)
from app.phase6.lockguard import assert_lock_state_unchanged, lock_state  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def render(info: dict, crit: dict, cfg: dict) -> str:
    vf = crit["variance_floor"]
    fl = vf["flags"]
    flag_rows = [[k, v] for k, v in vf["flag_definitions"].items()]
    thr_rows = [[k, v] for k, v in fl.items()]
    verdict_rows = [[a, b] for a, b in vf["verdict_table_in_order"]]
    metric_rows = [[k, v] for k, v in crit["metrics"].items()]
    L = [
        "# Phase 6 investigation plan: pressure definition and reliability validation",
        "",
        f"Status: {STATUS}. INTERNAL. No official Top 10, no public experimental ranking, no "
        "official ML training. TEST outcomes are not used. Cricsheet is not used. The 0.5 "
        "data-weight gate is not changed.",
        "",
        "## 1. What was declared before any result",
        f"- Criteria file: `config/phase6_selection_criteria_v1.json`, SHA-256 `{info['sha256']}`.",
        f"- Git blob hash of the same bytes (`git hash-object` value): `{info['git_blob_sha']}`. "
        "The workspace is not a git repository; the value is computed from the bytes so it can be "
        "checked later.",
        f"- Investigation config: `config/phase6_investigation_v1.json`, SHA-256 "
        f"`{info['investigation_config_sha256']}`.",
        "- Run order is enforced by the append-only table `p6_run_log` in `exploratory.duckdb`: "
        "row `seq = 1` (step `plan`) carries the criteria hash. Every later step verifies that "
        "the criteria file on disk still has that hash before it writes anything, and appends its "
        "own row. A rewritten criteria file therefore makes every later step fail.",
        "- The criteria contain no individual identity, ordering, score level or Top-10 "
        "membership as an input (`forbidden_inputs`). A hash-time scan rejects the words "
        "`player`, `rank`, `top10` and `promot` outside that list.",
        "",
        "## 2. Questions",
        "1. Between-player variance of pressure residuals sits at the shrinkage floor in all 48 "
        "contexts. Is the true value about zero, is the noise model misspecified, or are the "
        "samples too small to tell?",
        "2. How reliable are the pressure streams under odd/even, early/late and repeated random "
        "match splits, per stream, format, role and definition, with Spearman-Brown correction "
        "and bootstrap intervals?",
        "",
        "## 3. Data and windows",
        "- Primary window `PRE_TEST` = TRAIN + VALIDATION (723 matches, 2022-01-22 to "
        "2025-12-19). TEST rows are not loaded. The 42 late-dated T20I matches are TEST by date "
        "and stay excluded.",
        "- `TRAIN` (512 matches) is run next to it because the Phase 4 floor was fitted on TRAIN.",
        "- In-sample diagnostics only. The label on every row is "
        "`IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`.",
        f"- Seed {cfg['seed']}, {cfg['n_boot']} match-cluster bootstrap draws, "
        f"{cfg['split_half']['random_splits']} random splits.",
        f"- Definitions examined (nine, multiplicity not corrected): "
        f"{', '.join('`' + d + '`' for d in cfg['definitions']['candidates'])}. "
        "`any|q0.75` stays PROVISIONAL.",
        "",
        "## 4. Variance estimators",
        "E1 moments with floor (Phase 4 basis), E1b moments with independent-ball noise, E1c "
        "moments with match-cluster noise, E2 REML, E3 ML, E4 beta-binomial (binary streams), "
        "E5 gamma-Poisson (count streams, flagged `MISSPECIFIED_FOR_RUNS` on runs), E6 "
        "match-cluster bootstrap of E1c, E7 split-half covariance (model-free). E4 and E5 are "
        "sensitivity only and never enter a verdict.",
        "",
        "Identification rule:",
        "",
        md_table(["class", "condition"], [[k, v] for k, v in vf["identification_rule"].items()]),
        "",
        "## 5. Flags and verdict (thresholds fixed in the criteria file)",
        "",
        md_table(["threshold", "value"], thr_rows),
        "",
        md_table(["flag", "supported when"], flag_rows),
        "",
        "Verdict table, evaluated in this order:",
        "",
        md_table(["condition", "verdict"], verdict_rows),
        "",
        f"Sparse contexts: {vf['sparse_context']}.",
        "",
        "## 6. Floor arithmetic",
        "`k_for` computes `floor_abs = floor * sigma2`, `tau2 = max(max(between, floor_abs) * "
        "mult, floor_abs)`, `k = sigma2 / tau2`. On a floor hit `shrink_tau4` therefore gives "
        "`k = 1 / (4 * 0.01) = 25`. The investigation recomputes this from the code and from a "
        "hand formula, and compares it with the stored `p5_context_fit` values.",
        "",
        "## 7. Split-half reliability",
        f"Modes {', '.join(crit['split_half']['modes'])}; minimum "
        f"{crit['split_half']['min_balls_per_half']} pressure balls per half; at least "
        f"{crit['split_half']['min_individuals_estimable']} individuals; Spearman-Brown "
        f"{crit['split_half']['spearman_brown']}; pooling {crit['split_half']['aggregation']}; "
        "intervals from a bootstrap over individuals and a match-cluster bootstrap "
        "(odd/even, early/late) and a bootstrap of the per-repeat median (random).",
        "",
        "## 8. Selection criteria for the definition comparison (a later step)",
        "",
        md_table(["metric", "definition"], metric_rows),
        "",
        f"Rule: {crit['rule']}",
        "",
        f"Stability: {crit['stability_outcomes']}.",
        "",
        f"Confound control: {crit['confound_control']}.",
        "",
        f"Multiplicity: {crit['multiplicity']}.",
        "",
        "## 9. What counts as evidence",
        "- Between-variance is called identified and positive only if the model-free split "
        "covariance has a bootstrap lower bound above 0 and the match-cluster estimate is "
        "positive in at least 90% of bootstrap draws.",
        "- A split-half reliability counts as above zero only if its bootstrap interval excludes "
        "0.",
        "- Agreement between sources inside the same data is a consistency check, not validation.",
        "",
        "## 10. What the data cannot show",
        "- Out-of-sample validity: every number is computed on the same TRAIN and VALIDATION "
        "matches used to build the baseline and thresholds.",
        "- TEST was opened once in Phase 4 and is not pristine; it is not used here at all.",
        "- The noise model cannot be tested with these data alone; the bases bracket the truth.",
        "- Within-innings dependence cannot be separated because stored context rows hold "
        "match-level sums.",
        "- A definition passing a reliability criterion is not shown to measure pressure skill.",
        "",
        "## 11. Not done in this plan",
        "No threshold, gate, methodology lock or Phase 4/5 artifact is edited. The 0.5 "
        f"data-weight gate stays at {cfg['gate_value_expected']}. No result is published.",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap.parse_args(argv)
    before = lock_state()
    cfg = json.loads(INVESTIGATION_CONFIG.read_text(encoding="utf-8"))
    info = cr.write_criteria(CRITERIA_FILE, CRITERIA_HASH_FILE, INVESTIGATION_CONFIG, args.store)
    crit = cr.load_criteria(CRITERIA_FILE)
    cr.verify_criteria(CRITERIA_FILE, CRITERIA_HASH_FILE, args.store)
    write_text(PLAN_REPORT if args.reports == REPORTS_DIR else args.reports / PLAN_REPORT.name,
               render(info, crit, cfg))  # fmt: skip
    assert_lock_state_unchanged(before)
    print(json.dumps({"sha256": info["sha256"], "already_written": info["already_written"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
