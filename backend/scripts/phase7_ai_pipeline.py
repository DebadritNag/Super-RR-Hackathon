"""Phase 7 chunk 5: run the verification of the statistical baseline/shrinkage pipeline.
Writes the two experimental CSVs, the model registry JSON and the metrics JSON into the reports
folder. No database is written and the TEST period is not loaded. Exit 1 on any guard failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.phase4.constants import REPORTS_DIR  # noqa: E402
from app.phase7 import ai_pipeline as ap  # noqa: E402
from app.services.pressure_service import EXPLORATORY_DB  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap_ = argparse.ArgumentParser(description=__doc__)
    ap_.add_argument("--store", type=Path, default=EXPLORATORY_DB)
    ap_.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap_.parse_args(argv)
    res = ap.run_pipeline(args.store, args.reports)
    hashes = ap.write_outputs(res, args.reports)
    m = res["metrics"]
    print("model:", ap.MODEL_LABEL)
    print("version:", res["version"])
    print("rows written:", {k: len(v) for k, v in res["outputs"].items()})
    print("thresholds max abs diff vs frozen:", m["thresholds_max_abs_diff_vs_phase4_frozen"])
    print("test match ids in frame:", m["data_checks"]["test_match_ids_in_frame"])
    print("lock unchanged:", res["registry"]["lock_unchanged"])
    print("digest:", ap.deterministic_digest(res))
    print(json.dumps(hashes, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
