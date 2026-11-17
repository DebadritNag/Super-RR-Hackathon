"""Phase 4 Stage F: spot checks and the report generators that read only stored results.

Writes ``phase4_spot_checks.json``, ``phase4_pressure_scoring_report.md`` (final version),
``phase4_data_quality_report.md`` and ``phase4_user_summary.md`` (also copied to the agents task
folder). Every number comes from stored results; nothing is typed into a template.
Exit 1 if official data changed or a spot check disagrees.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.phase4 import reports as rp  # noqa: E402
from app.phase4 import spotchecks as spc  # noqa: E402
from app.phase4.constants import REPORTS_DIR, SPLIT_CONFIG  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402

DEFAULT_HASH_BEFORE = Path("d:/Data/.agents/tasks/phase4_hash_before.txt")
DEFAULT_SUMMARY_COPY = Path("d:/Data/.agents/tasks/phase4_user_summary.md")


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--data-root", type=Path, default=s.data_root)
    ap.add_argument("--hash-before", type=Path, default=DEFAULT_HASH_BEFORE)
    ap.add_argument("--summary-copy", type=Path, default=DEFAULT_SUMMARY_COPY)
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s)
    rep = args.reports
    split_cfg = json.loads(SPLIT_CONFIG.read_text(encoding="utf-8"))

    spot = spc.run_all(args.store, rep, args.data_root, args.hash_before)
    write_json_deterministic(rep / "phase4_spot_checks.json", spot)

    b = rp.load_bundle(rep)
    write_text(rep / "phase4_pressure_scoring_report.md", rp.render_pressure_scoring(b))
    excl = rp.row_exclusions(args.store, split_cfg)
    late = rp.late_t20i_dates(args.store, split_cfg["test_core_end"])
    lits = rp.nonoutcome_literals(rp.phase4_sources(), "cricsheet")
    write_text(
        rep / "phase4_data_quality_report.md",
        rp.render_data_quality(b, split_cfg, excl, late, lits),
    )
    summary = rp.render_user_summary(b, split_cfg, late)
    write_text(rep / "phase4_user_summary.md", summary)
    if args.summary_copy:
        args.summary_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rep / "phase4_user_summary.md", args.summary_copy)

    diff = assert_unchanged(before, snapshot_from_settings(s))
    print("spot checks ok:", spot["all_ok"], "| official data unchanged:", not diff)
    return 0 if (not diff and spot["all_ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
