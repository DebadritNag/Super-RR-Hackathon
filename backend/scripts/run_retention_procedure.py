"""One-command 17 November procedure: import -> run report -> availability-aware outputs.

    python scripts/run_retention_procedure.py --file <list.csv|xlsx> --snapshot-date 2026-11-17 `
        --source "<official document>" --verification OFFICIAL_VERIFIED --authoritative

With no file (or a missing path) it reports the explicit state 'no retention file yet', writes a
header-only candidate_availability.csv and exits 0. It never invents rows.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data_pipeline import retention_importer as ri  # noqa: E402
from app.data_pipeline.retention_availability import build_availability  # noqa: E402


def _report(lines: list[str], reports: Path) -> Path:
    p = reports / "retention_import_run_report.md"
    reports.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", default=None)
    ap.add_argument("--snapshot-date", default=None)
    ap.add_argument("--source", default="")
    ap.add_argument("--verification", default="UNVERIFIED", choices=ri.VERIFICATIONS)
    ap.add_argument("--authoritative", action="store_true")
    ap.add_argument("--season", default="")
    ap.add_argument("--store", default=str(ri.EXPLORATORY_DB))
    ap.add_argument("--raw-dir", default=str(ri.RAW_DIR))
    ap.add_argument("--reports-dir", default=str(ri.REPORTS_DIR))
    ap.add_argument("--profile-dir", default=str(ri.REPORTS_DIR))
    a = ap.parse_args(argv)
    reports = Path(a.reports_dir)
    stamp = datetime.now(UTC).isoformat()
    lines = ["# Retention import run report", f"Generated: {stamp}", ""]
    code = 0
    if not a.file or not Path(a.file).is_file():
        lines += ["State: **NO RETENTION FILE YET**. No list was imported; no row was created.",
                  f"File argument: {a.file or '(none)'}"]  # fmt: skip
        print("NO RETENTION FILE YET: nothing imported. Writing header-only availability output.")
    else:
        try:
            if not a.snapshot_date:
                raise ri.RetentionImportError("--snapshot-date is required with a file")
            res = ri.import_file(
                a.file, snapshot_date=a.snapshot_date, source=a.source,
                verification=a.verification, authoritative=a.authoritative, season=a.season,
                store=a.store, raw_dir=a.raw_dir,
            )  # fmt: skip
            ri.export_review_csv(a.store, reports / "retention_review_queue.csv")
            lines += [
                f"State: **{res['status']}** (import_id {res['import_id']}, changed: {res['changed']})",
                f"File: {res['file']}  sha256 `{res['file_sha256']}`",
                f"Snapshot {res['snapshot_date']}; verification {res['verification_status']}; "
                f"authoritative: {res['authoritative']}",
                f"Rows {res['n_rows']}; status counts {res['status_counts']}",
                f"Mapping counts {res['mapping_counts']}; flags {res['flag_counts']}",
                f"Rows in the manual-review queue: {res['n_review']} "
                "(`retention_review_queue.csv`). Resolve them before relying on exclusions.",
                f"Confirmed available (authoritative AUCTION_AVAILABLE rows): "
                f"{res['n_confirmed_available']}",
            ]
            print(f"{res['status']}: {res['n_rows']} rows, {res['n_review']} for review")
        except ri.RetentionImportError as exc:
            lines += [f"State: **INVALID FILE**: {exc}"]
            print(f"INVALID: {exc}")
            code = 1
    if code == 0:
        m = build_availability(a.store, reports, a.profile_dir)
        lines += ["", f"Availability output state: {m['state']}; rows {m['rows']}; "
                  f"retained excluded {m['retained_excluded']}; "
                  f"confirmed available {m['confirmed_available']}; "
                  f"unresolved list rows {m['unresolved_rows_in_list']}",
                  m["statement"]]  # fmt: skip
        print(f"availability: {m['state']}, {m['rows']} rows")
    _report(lines, reports)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
