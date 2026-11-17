"""Assess the impact of the outstanding data-quality rows (read-only, no deletions)."""

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
from app.validation.data_quality_impact import build_report, render_report  # noqa: E402
from app.validation.restrictions import load_restrictions  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    ap.add_argument(
        "--restrictions", type=Path, default=s.config_dir / "data_quality_restrictions_v1.json"
    )
    ap.add_argument(
        "--phase1-report", type=Path, default=s.audit_dir / "cricsheet_overlap_report.json"
    )
    args = ap.parse_args(argv)

    cfg = load_restrictions(args.restrictions)
    before = snapshot_from_settings(s, args.db)
    db = open_official_readonly(args.db)
    try:
        rep = build_report(db, cfg, args.phase1_report)
        prov = provenance(db, args.restrictions, seed=None)
    finally:
        db.close()
    after = snapshot_from_settings(s, args.db)
    diff = assert_unchanged(before, after)
    rep["provenance"] = prov
    rep["preservation"] = {"unchanged": not diff, "diff": diff, "snapshot": before}

    out = args.reports_dir
    write_json_deterministic(out / "data_quality_impact_report.json", rep)
    write_text(out / "data_quality_impact_report.md", render_report(rep))
    reg = rep["issue_register"]
    print(
        f"wrote data-quality impact report to {out.as_posix()}; preservation unchanged={not diff}"
    )
    print("classification counts:", reg["classification_counts"])
    for e in reg["entries"]:
        if e["count_agrees_with_db"] is False:
            print("DISAGREES:", e["check_name"], e["db_affected_rows"], e["recomputed_count"])
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
