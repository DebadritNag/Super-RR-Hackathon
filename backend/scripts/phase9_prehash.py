"""Step 1 of Phase 9: verify the protected files against the pre-run hashes and the criteria hash.

``phase9_prerun_hashes.json`` was recorded before any Phase 9 work. Every entry that is not a
submission report must still match (databases, models, config, source CSVs). Phase 8 submission
reports are overwritten on purpose (after being copied to ``*_phase8.*``), so they go to
``phase9_report_hashes.json`` and are checked through their copies. The remaining entries are written
to ``phase9_prehash.json`` (the file ``check_protected`` reads in Phase 9).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.analytics.integrity import sha256_file
from app.phase8.constants import CRITERIA_FILE

TASKS = Path("d:/Data/.agents/tasks")
PRERUN = TASKS / "phase9_prerun_hashes.json"
CRITERIA_SHA256 = "9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64"


def main() -> int:
    if sha256_file(CRITERIA_FILE) != CRITERIA_SHA256:
        print("criteria hash mismatch", file=sys.stderr)
        return 2
    rec = json.loads(PRERUN.read_text(encoding="utf-8-sig"))
    protected, reports, bad = {}, {}, []
    for name, digest in rec.items():
        p = Path(name)
        (reports if "/data/reports/" in name.lower() else protected)[name] = digest
        if "/data/reports/" in name.lower():
            continue
        if not p.exists() or sha256_file(p) != digest:
            bad.append(name)
    if bad:
        print("protected files differ from the pre-run hashes:", bad, file=sys.stderr)
        return 3
    (TASKS / "phase9_prehash.json").write_text(
        json.dumps(protected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (TASKS / "phase9_report_hashes.json").write_text(
        json.dumps(reports, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "criteria_sha256": CRITERIA_SHA256,
                "protected": len(protected),
                "reports": len(reports),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
