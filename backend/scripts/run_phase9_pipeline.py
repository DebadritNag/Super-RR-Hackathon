"""Phase 9 pipeline runner: runs the parameterised Phase 8 stage scripts with SUPERR_PHASE=phase9.

Each stage is a separate process (log in d:/Data/.agents/tasks/_p9_logs). Every stage script verifies
the criteria hash (``begin_step``) and the protected files before and after it runs.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("d:/Data/backend")
LOGS = Path("d:/Data/.agents/tasks/_p9_logs")
STAGES = [
    ("plan", "phase9_plan_row.py", []),
    ("data", "phase8_data.py", []),
    ("intensity", "phase8_intensity.py", []),
    ("a_models", "phase8_approach_a.py", ["models"]),
    ("a_tests", "phase8_approach_a.py", ["tests"]),
    ("a_estimate", "phase8_approach_a.py", ["estimate"]),
    ("b_winprob", "phase8_approach_b.py", ["winprob"]),
    ("b_tests", "phase8_approach_b.py", ["tests"]),
    ("b_estimate", "phase8_approach_b.py", ["estimate"]),
    ("c_estimate", "phase8_approach_c.py", ["estimate"]),
    ("final_compare", "phase8_final_ranking.py", ["compare"]),
    ("final_rank", "phase8_final_ranking.py", ["rank"]),
]


def main(argv: list[str]) -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    only = set(argv)
    env = {**os.environ, "SUPERR_PHASE": "phase9", "PYTHONUTF8": "1", "PYTHONPATH": str(ROOT)}
    for name, script, args in STAGES:
        if only and name not in only:
            continue
        t0 = time.time()
        with (LOGS / f"{name}.log").open("w", encoding="utf-8") as fh:
            rc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script), *args],
                cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT, check=False,
            ).returncode  # fmt: skip
        print(f"{name}: rc={rc} {time.time() - t0:.0f}s", flush=True)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
