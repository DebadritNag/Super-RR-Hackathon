"""Phase 9 step 0: declare the unchanged Phase 8 criteria in the Phase 9 run log (``p9_run_log``).

The criteria file is verified against its hash first and is never rewritten. The ``plan`` row
(seq 1) of ``p9_run_log`` carries the same SHA-256 so every later step can verify it.
"""

from __future__ import annotations

import json
import os
import sys

os.environ["SUPERR_PHASE"] = "phase9"

from app.analytics.integrity import sha256_file  # noqa: E402
from app.phase8 import store  # noqa: E402
from app.phase8.constants import CRITERIA_FILE, CRITERIA_HASH_FILE  # noqa: E402
from app.phase8.criteria import CriteriaError, git_blob_sha  # noqa: E402
from app.phase8.lockguard import check_protected  # noqa: E402
from app.phase9.lockrelease import EXPECTED_CRITERIA_SHA256, assert_test_released  # noqa: E402


def main() -> int:
    check_protected()
    digest = sha256_file(CRITERIA_FILE)
    rec = json.loads(CRITERIA_HASH_FILE.read_text(encoding="utf-8"))
    if digest != EXPECTED_CRITERIA_SHA256 or rec.get("sha256") != digest:
        raise CriteriaError("criteria hash differs from the declared value")
    assert_test_released()
    log = store.read_run_log()
    if len(log) == 0:
        blob = git_blob_sha(CRITERIA_FILE.read_bytes())
        store.append_run_log(
            "plan", digest, blob, "", "criteria unchanged from phase 8; re-declared for phase 9"
        )
    log = store.read_run_log()
    print(json.dumps({"criteria_sha256": digest, "run_log_rows": len(log)}))
    check_protected()
    return 0


if __name__ == "__main__":
    sys.exit(main())
