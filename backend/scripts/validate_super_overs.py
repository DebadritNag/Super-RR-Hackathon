"""Validate official innings 3/4 against Cricsheet Super Overs (validation-only, read-only)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics.integrity import (  # noqa: E402
    assert_unchanged,
    open_official_readonly,
    snapshot_from_settings,
)
from app.analytics.reporting import provenance, write_json_deterministic, write_text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.validation.cricsheet_super_over import (  # noqa: E402
    finalize,
    load_cricsheet_records,
    load_official_matches,
    render_report,
    validate_super_overs,
)


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument("--cricsheet-root", type=Path, default=s.cricsheet_root)
    ap.add_argument("--index", type=Path, default=s.staging_dir / "cricsheet_index.parquet")
    args = ap.parse_args(argv)

    before = snapshot_from_settings(s, args.db)
    db = open_official_readonly(args.db)
    try:
        official = load_official_matches(db)
        prov = provenance(db, None, seed=None)
    finally:
        db.close()
    records = load_cricsheet_records(args.index, args.cricsheet_root, s.cricsheet_dirs)
    res = finalize(validate_super_overs(official, records, args.cricsheet_root))
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    res["provenance"] = prov
    res["preservation"] = {"unchanged": not diff, "diff": diff, "snapshot": before}

    out = args.reports_dir
    write_json_deterministic(out / "cricsheet_super_over_validation.json", res)
    write_text(out / "cricsheet_super_over_validation.md", render_report(res))
    print(f"wrote super over validation to {out.as_posix()}; preservation unchanged={not diff}")
    for m in res["matches"]:
        print(m["match_id"], m["classification"], m["mapping"]["status"], m["reason_codes"])
    print("classification counts:", res["classification_counts"])
    print("converse count:", res["converse_check"]["count"])
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
