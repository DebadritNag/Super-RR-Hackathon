"""Phase 6: write the unresolved-issues register and the user summary, check deliverables.

All numbers are read from the stored outputs. Copies ``phase6_user_summary.md`` to
``d:/Data/.agents/tasks/``. Fails if a named deliverable is missing or empty.
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

from app.analytics.reporting import write_text  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase6 import reports as rp  # noqa: E402

TASKS_COPY = Path("d:/Data/.agents/tasks/phase6_user_summary.md")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--copy-to", type=Path, default=TASKS_COPY)
    args = ap.parse_args(argv)
    rep = args.reports
    n = rp.collect(rep)
    p5 = rp.phase5_items(rep)
    write_text(rep / "phase6_unresolved_issues.md", rp.render_register(n, p5))
    write_text(rep / "phase6_user_summary.md", rp.render_summary(n))
    missing = [d for d in rp.DELIVERABLES
               if not (rep / d).is_file() or (rep / d).stat().st_size == 0]  # fmt: skip
    if args.copy_to and args.copy_to.parent.is_dir():
        shutil.copyfile(rep / "phase6_user_summary.md", args.copy_to)
    print(json.dumps({"phase5_items": sorted(p5), "missing_deliverables": missing}))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
