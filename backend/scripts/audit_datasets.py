"""Run the Phase 1 dataset audit and write reports to data/audit/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.data_pipeline.audit_runner import run_full_audit  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-cricsheet", action="store_true", help="skip Cricsheet JSON parsing")
    ap.add_argument("--output-dir", type=Path, default=None)
    args = ap.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    bundle = run_full_audit(
        settings, skip_cricsheet=args.skip_cricsheet, output_dir=args.output_dir
    )
    mr = bundle["match_reconciliation"]
    print(
        f"audit complete: {mr['matches_without_ball_by_ball']} matches without deliveries; "
        f"originals unmodified: {bundle['originals_unmodified']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
