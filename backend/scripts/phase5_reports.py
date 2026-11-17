"""Phase 5 Chunk 5: write the lock/refit report, the unresolved-issues list and the user summary.

Reads stored outputs only (it computes nothing). Safe to run before the lock and the refit exist; it
then says so. Copies ``phase5_user_summary.md`` to ``.agents/tasks`` when that folder is present.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.reporting import write_text  # noqa: E402
from app.phase5 import reports as rp  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase5.outputs import Preservation  # noqa: E402

TASKS_COPY = ROOT.parent / ".agents" / "tasks" / "phase5_user_summary.md"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--no-copy", action="store_true")
    args = ap.parse_args(argv)
    pres = Preservation(args.reports)
    inp = rp.load_inputs(args.reports)
    write_text(args.reports / "phase5_unresolved_issues.md", rp.render_unresolved(inp))
    write_text(args.reports / "phase5_methodology_lock_and_refit.md", rp.render_lock_refit(inp))
    write_text(args.reports / "phase5_user_summary.md", rp.render_user_summary(inp))
    if not args.no_copy and TASKS_COPY.parent.is_dir():
        shutil.copyfile(args.reports / "phase5_user_summary.md", TASKS_COPY)
    print(
        "reports written; lock present:",
        inp["lock"] is not None,
        "refit present:",
        inp["refit"] is not None,
    )
    return 0 if pres.verify()["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
