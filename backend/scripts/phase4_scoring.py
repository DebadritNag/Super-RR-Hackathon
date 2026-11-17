"""Phase 4 Chunk 2, Stage C: shrinkage choice (TRAIN/VALIDATION) and experimental pressure scores.

Scores are written for the provisional leading definition ``chase|q0.9`` over the PRE_TEST window
(TRAIN + VALIDATION) with the shrinkage configuration chosen on VALIDATION and with zero
shrinkage. The shrinkage choice file is written BEFORE any scoring. TEST rows are never loaded.
Exit 1 if official data changed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import md_table, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.phase4 import baseline as bl  # noqa: E402
from app.phase4 import scoring as sc  # noqa: E402
from app.phase4 import shrink as sh  # noqa: E402
from app.phase4.constants import REPORTS_DIR, SCOPE, STATUS  # noqa: E402
from app.phase4.split import TestLock  # noqa: E402
from app.phase4.store import write_p4_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402
from scripts.phase4_baseline import load_pre_test  # noqa: E402


def selection_cells(d, bs, defn, thr, lock):
    cells = []
    for role, stream, _ in bl.STREAMS:
        rows = sc.residual_rows(d, bs, defn, thr, role, stream, lock)
        for comp in SCOPE:
            r = rows[rows["comp"] == comp]
            tpt = sh.player_table(sh.match_stats(r[r["period"] == "TRAIN"]))
            cells.append(
                {
                    "cell": f"{role}:{stream}:{comp}",
                    "fit": sh.fit_cell(tpt),
                    "train_pt": tpt,
                    "val_ms": sh.match_stats(r[r["period"] == "VALIDATION"]),
                }
            )
    return cells


def render(df: pd.DataFrame, choice: dict, defn: str, thr: dict) -> str:
    L = [
        "# Phase 4 pressure scoring report (first version)",
        "",
        f"Status: {STATUS}. Not an official ranking. Definition `{defn}` is the provisional "
        "leading candidate, not a validated definition. Eligibility is the Phase 3 PLACEHOLDER "
        "rule until Chunk 3.",
        "",
        f"TRAIN-only thresholds: {thr}",
        f"Shrinkage chosen on TRAIN/VALIDATION: `{choice['chosen']}` (rule: {choice.get('rule')}).",
        "",
        "## Shrinkage choice (VALIDATION loss)",
        md_table(
            ["config", "loss", "diff vs eb", "bootstrap SE"],
            [
                [k, v["loss"], v["diff_vs_eb"], v["bootstrap_se"]]
                for k, v in choice["losses"].items()
            ],
        ),
        "",
        "## Record counts",
    ]
    g = (
        df.groupby(["role", "stream", "format", "shrinkage_config"])
        .size()
        .reset_index(name="records")
    )
    L.append(md_table(list(g.columns), g.values.tolist()))
    el = df[df["eligibility_status"].str.startswith("ELIGIBLE")]
    g2 = (
        el.groupby(["role", "stream", "format", "shrinkage_config"])
        .size()
        .reset_index(name="eligible")
    )
    L += ["", "## Placeholder-eligible players (fewer than ten is reported as is)"]
    L.append(md_table(list(g2.columns), g2.values.tolist()))
    L += [
        "",
        "## Limitations",
        "- The primary residual mixes pressure-specific and general skill (no player term in B0).",
        "- Bowler pressure uses the same state signals as batters (bowler signal B is Chunk 3).",
        "- Intervals hold k and the shrink target fixed; tau2 uncertainty is not propagated.",
        "- Combined records exist only for players eligible in both formats (default 70:30).",
    ]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--definition", default=sc.LEADING_DEFINITION)
    ap.add_argument("--n-boot", type=int, default=1000)
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s)
    d, _ = load_pre_test(args.store)
    lock = TestLock(args.reports / "phase4_lock_log.json")
    d = sc.add_signals(d, lock)
    bs = bl.fit_baseline_set(d)
    _, q = sc.parse_definition(args.definition)
    thr = sc.fit_thresholds(d[d["period"] == "TRAIN"], q)
    choice = sh.choose_shrinkage(selection_cells(d, bs, args.definition, thr, lock), args.n_boot)
    sh.record_choice(choice, args.reports / "phase4_shrinkage_choice.json")
    configs = list(dict.fromkeys([choice["chosen"], "shrink_none"]))
    df = sc.score_all(d, bs, args.definition, thr, configs, lock, n_boot=args.n_boot)
    sc.write_scores(
        df, args.reports / "phase4_pressure_scores_experimental.csv",
        args.reports / "phase4_pressure_scores_experimental.json",
    )  # fmt: skip
    write_p4_table(df, "p4_pressure_scores", args.store)
    write_text(
        args.reports / "phase4_pressure_scoring_report.md", render(df, choice, args.definition, thr)
    )
    diff = assert_unchanged(before, snapshot_from_settings(s))
    print("records:", len(df), "chosen:", choice["chosen"], "official data unchanged:", not diff)
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
