"""Phase 5 Chunk 5: experimental refit on TRAIN + VALIDATION (artifact set p5_refit_trainval_v1).

Refuses to run without a valid ``phase5_methodology_lock.json`` (create it with
``scripts/phase5_methodology_lock.py --confirm-lock``). EXPERIMENTAL_NOT_VALIDATED. TEST is not
read. Phase 4 tables and reports are hashed before and after and must be byte-identical.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.phase5 import lock_manifest as lm  # noqa: E402
from app.phase5 import refit as rf  # noqa: E402
from app.phase5.constants import REPORTS_DIR  # noqa: E402
from app.phase5.outputs import Preservation  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    ap.add_argument("--lock-path", type=Path, default=None)
    args = ap.parse_args(argv)
    lock_path = args.lock_path or (args.reports / "phase5_methodology_lock.json")
    pres = Preservation(args.reports)
    try:
        res = rf.run_refit(args.store, args.reports, lock_path)
    except lm.LockError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    s = res.summary
    print(
        "refit",
        s["refit_id"],
        "rows",
        s["rows"],
        "matches",
        s["matches"],
        s["date_min"],
        s["date_max"],
    )
    print(res.frames["comparison"].to_string(index=False))
    full = pres.verify()
    print(
        "preservation (refit):",
        s["preservation"]["all_preserved"],
        "| overall:",
        full["all_preserved"],
    )
    return 0 if s["preservation"]["all_preserved"] and full["all_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
