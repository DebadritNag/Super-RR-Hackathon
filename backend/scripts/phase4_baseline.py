"""Phase 4 Chunk 2, Stage B: train-frozen calibrated baselines and calibration report.

Reads the exploratory state read-only, fits B0 on TRAIN rows, validates on VALIDATION rows, writes
``phase4_calibration.json``, ``phase4_baseline_calibration_report.md`` and p4_calibration_* tables.
TEST rows are dropped before any fitting. Exit 1 if official data changed.
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
from app.analytics.reporting import md_table, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.phase4 import baseline as bl  # noqa: E402
from app.phase4.constants import REPORTS_DIR, STATUS  # noqa: E402
from app.phase4.data import load_state_with_period  # noqa: E402
from app.phase4.lockguard import drop_test_rows  # noqa: E402
from app.phase4.split import Split  # noqa: E402
from app.phase4.store import write_p4_table  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def load_pre_test(store: Path):
    split = Split.from_config()
    raw = drop_test_rows(load_state_with_period(split, store))
    d, wb = bl.prepare_frame(raw, split)
    return d, wb


def render(rep: dict, wb: dict) -> str:
    L = [
        "# Phase 4 baseline calibration report",
        "",
        f"Status: {STATUS}. Baseline `{rep['baseline_version']}`, fitted on TRAIN only.",
        "",
        "Method: stratified empirical-Bayes cells (`comp|role|phase|wickets-bin` down to `comp`), "
        "shrinkage strength from TRAIN, wickets-remaining bins from TRAIN, one additive offset per "
        "format fitted on TRAIN. TRAIN rows use leave-player-out expectations; VALIDATION rows use "
        "the frozen tables. TEST rows were not loaded. B0 has no pressure term.",
        "",
        f"Wickets-remaining bins (TRAIN): {wb['labels']}",
        "",
        "## Calibration identity (TRAIN, pooled expectation)",
    ]
    rows = []
    for s, v in rep["streams"].items():
        for c, i in v["calibration_identity_train_pooled"].items():
            rows.append([s, c, i["sum_actual"], i["sum_expected"], i["rel_diff"]])
    L.append(md_table(["stream", "format", "sum actual", "sum expected", "relative diff"], rows))
    L += ["", "## Residuals and coverage by period"]
    rows = []
    for s, v in rep["streams"].items():
        for p, b in v["periods"].items():
            rows.append(
                [s, p, b["rows"], b["mean_residual"], b["residual_sd"],
                 b["fallback_rows_finest_cell_unseen"], b["level_usage"]]
            )  # fmt: skip
    L.append(
        md_table(
            ["stream", "period", "rows", "mean residual", "sd", "finest cell unseen", "levels"],
            rows,
        )
    )
    for title, key in (
        ("Out-of-period (VALIDATION) by format", "by_format"),
        ("Out-of-period (VALIDATION) by phase", "by_phase"),
        ("Out-of-period (VALIDATION) by wickets-remaining bin", "by_wickets_remaining_bin"),
        ("Out-of-period (VALIDATION) by expected decile", "by_expected_decile"),
        ("Stability over time (all fitted periods) by year", "by_year"),
    ):
        L += ["", f"## {title}"]
        rows = []
        for s, v in rep["streams"].items():
            for p, b in v["periods"].items():
                if key != "by_year" and p != "VALIDATION":
                    continue
                for g in b[key]:
                    rows.append(
                        [s, p, g["group"], g["rows"], g["actual"], g["expected"], g["residual"]]
                    )
        L.append(
            md_table(["stream", "period", "group", "rows", "actual", "expected", "residual"], rows)
        )
    L += [
        "",
        "## Limitations",
        "- The offset makes the identity hold by construction on TRAIN; VALIDATION is the "
        "genuine check.",
        "- Binary streams use a beta-binomial shrink; expectations are clipped to [0, 1].",
        "- DLS-affected innings are excluded by mask (not imputed); no delivery rows are deleted.",
    ]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s)
    d, wb = load_pre_test(args.store)
    bs = bl.fit_baseline_set(d)
    rep = bl.calibration_report(bs, d)
    rep["identity_ok"] = bl.identity_ok(rep)
    rep["status"] = STATUS
    write_json_deterministic(args.reports / "phase4_calibration.json", rep)
    write_text(args.reports / "phase4_baseline_calibration_report.md", render(rep, wb))
    flat = []
    for sname, v in rep["streams"].items():
        for p, b in v["periods"].items():
            for g in b["by_expected_decile"]:
                flat.append({"stream": sname, "period": p, **g})
    write_p4_table(pd.DataFrame(flat), "p4_calibration", args.store)
    diff = assert_unchanged(before, snapshot_from_settings(s))
    print("identity_ok:", rep["identity_ok"], "official data unchanged:", not diff)
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
