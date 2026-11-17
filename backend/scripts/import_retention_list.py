"""Import (or preview) an official retention list: CSV or XLSX.

Exit codes: 0 ok, 1 invalid file or parameters, 2 file not found (no list yet).
Example (preview only):  python scripts/import_retention_list.py --file list.xlsx --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data_pipeline import retention_importer as ri  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True)
    ap.add_argument("--snapshot-date", required=True, help="YYYY-MM-DD date the list was published")
    ap.add_argument("--source", default="", help="document or URL the list came from")
    ap.add_argument("--verification", default="UNVERIFIED", choices=ri.VERIFICATIONS)
    ap.add_argument("--authoritative", action="store_true",
                    help="the source is the official IPL/franchise document")  # fmt: skip
    ap.add_argument("--season", default="")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--store", default=str(ri.EXPLORATORY_DB))
    ap.add_argument("--raw-dir", default=str(ri.RAW_DIR))
    ap.add_argument("--reports-dir", default=str(ri.REPORTS_DIR))
    a = ap.parse_args(argv)
    if not Path(a.file).is_file():
        print(
            f"NO RETENTION FILE: {a.file} does not exist (no list received yet). Nothing changed."
        )
        return 2
    try:
        res = ri.import_file(
            a.file, snapshot_date=a.snapshot_date, source=a.source, verification=a.verification,
            authoritative=a.authoritative, season=a.season, sheet=a.sheet, dry_run=a.dry_run,
            store=a.store, raw_dir=a.raw_dir,
        )  # fmt: skip
        if res["changed"]:
            ri.export_review_csv(a.store, Path(a.reports_dir) / "retention_review_queue.csv")
    except ri.RetentionImportError as exc:
        print(f"INVALID: {exc}")
        return 1
    print(f"{res['status']}: {res['n_rows']} rows, {res['n_review']} need manual review, "
          f"statuses {res['status_counts']}, sha256 {res['file_sha256'][:16]}")  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
