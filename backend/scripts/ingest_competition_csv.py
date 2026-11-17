"""Idempotent, transactional ingestion of the official competition CSVs into DuckDB.

Exit codes: 0 success or no change, 1 failed (rolled back), 2 loaded but a validation check FAILED.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.services.ingestion_service import IngestionService  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="reload even if nothing changed")
    ap.add_argument("--validate-only", action="store_true", help="re-run validation, no load")
    ap.add_argument("--db", type=Path, default=None, help="DuckDB file (default: settings)")
    ap.add_argument("--data-root", type=Path, default=None, help="folder with the CSV files")
    args = ap.parse_args()

    settings = get_settings()
    if args.data_root:
        settings = settings.model_copy(update={"data_root": args.data_root})
    configure_logging(settings.log_level)
    service = IngestionService(settings, db_path=args.db)
    result = service.run(force=args.force, validate_only=args.validate_only)

    print(f"run_id: {result.run_id}")
    print(f"mode: {result.mode}")
    print(f"status: {result.status}")
    print(f"reason: {result.reason}")
    print(f"elapsed_seconds: {result.elapsed_seconds}")
    if result.status == "NO_CHANGE":
        print("no change: nothing was reloaded")
    if result.error:
        print(f"error: {result.error}")
    if result.counts:
        print("table row counts:")
        for table, n in result.counts.items():
            print(f"  {table}: {n}")
    if result.validation:
        print("validation: " + ", ".join(f"{k}={v}" for k, v in sorted(result.validation.items())))
    print(f"exit_code: {result.exit_code}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
