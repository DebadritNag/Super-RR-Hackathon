"""Write the predeclared Phase 8 criteria, their SHA-256 and the run-log ``plan`` row (step 1).

Run this before any other phase8 script. It is idempotent and refuses to rewrite changed criteria.
"""

from __future__ import annotations

import json
import sys

from app.phase8.criteria import write_criteria
from app.phase8.lockguard import check_protected


def main() -> int:
    check_protected()
    rec = write_criteria()
    print(json.dumps(rec, indent=2, sort_keys=True))
    check_protected()
    return 0


if __name__ == "__main__":
    sys.exit(main())
