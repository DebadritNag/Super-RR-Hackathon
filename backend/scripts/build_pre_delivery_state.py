"""Build the exploratory pre-delivery state table (separate store, official DB read-only).

Exit code 1 when any official data changed. EXPLORATORY_NOT_VALIDATED; not a ranking.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services import pressure_service as ps  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=s.duckdb_path)
    ap.add_argument("--store", type=Path, default=ps.EXPLORATORY_DB)
    ap.add_argument("--reports-dir", type=Path, default=s.phase25_reports_dir)
    args = ap.parse_args(argv)
    m = ps.build_and_store(s, args.db, args.store, args.reports_dir)
    c = m["checks"]
    print(
        f"rows={c['rows']} regulation_rows={c['regulation_rows']} restricted={c['restricted_rows']}"
    )
    print(f"store={m['store']['path']} manifest={args.reports_dir / ps.MANIFEST_NAME}")
    ok = m["preservation"]["official_data_unchanged"]
    print("official data unchanged:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
