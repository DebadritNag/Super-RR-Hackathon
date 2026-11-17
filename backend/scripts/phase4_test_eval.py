"""Phase 4: the single final TEST-period evaluation of the frozen configuration.

Refuses to run unless ``phase4_frozen_choices.json`` exists and matches its FREEZE entry in the
lock log. Opens the test lock exactly once (a second run on the same lock log raises). Writes
``phase4_test_evaluation.json`` and ``phase4_test_evaluation.md``. No choice is changed here.
Exit 1 if official data changed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import assert_unchanged, snapshot_from_settings  # noqa: E402
from app.analytics.reporting import write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.phase4 import reports as rp  # noqa: E402
from app.phase4.constants import FROZEN_CHOICES, REPORTS_DIR  # noqa: E402
from app.phase4.split import Split, TestLock  # noqa: E402
from app.phase4.test_eval import N_BOOT, evaluate_frozen  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    args = ap.parse_args(argv)
    before = snapshot_from_settings(s)
    lock = TestLock(args.reports / "phase4_lock_log.json")
    res = evaluate_frozen(
        args.reports / FROZEN_CHOICES.name, lock, Split.from_config(), args.store, args.n_boot
    )
    write_json_deterministic(args.reports / "phase4_test_evaluation.json", res)
    write_text(args.reports / "phase4_test_evaluation.md", rp.render_test_evaluation(res))
    diff = assert_unchanged(before, snapshot_from_settings(s))
    events = [e["event"] for e in lock.entries]
    print("lock events:", events[-3:], "| official data unchanged:", not diff)
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
