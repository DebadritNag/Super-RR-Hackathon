"""Phase 7 protected-file check (read-only).

Compares every file in .agents/tasks/phase7_prehash.json by SHA-256, reports the two
TEST-lock logs, and exits non-zero on any mismatch.

Modes:
  default     compare phase7_prehash.json
  --phase6    also compare phase6_prerun_hashes.json (exploratory.duckdb is expected to differ
              because Phase 6 added p6_* tables after that snapshot)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("d:/Data")
PREHASH = ROOT / ".agents/tasks/phase7_prehash.json"
PHASE6_PRERUN = ROOT / ".agents/tasks/phase6_prerun_hashes.json"
REPORTS = ROOT / "backend/data/reports"
LOCK4_SHA = "cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compare(mapping: dict[str, str]) -> tuple[int, list[str]]:
    bad: list[str] = []
    for name, expected in mapping.items():
        p = Path(name)
        if not p.is_absolute():
            p = ROOT / name
        if not p.exists():
            bad.append(f"MISSING {name}")
        elif sha256_file(p) != expected:
            bad.append(f"CHANGED {name}")
    return len(mapping), bad


def lock_status() -> tuple[bool, dict]:
    log4 = REPORTS / "phase4_lock_log.json"
    log5 = REPORTS / "phase5_lock_log.json"
    events = [e.get("event") for e in json.loads(log4.read_text(encoding="utf-8-sig"))]
    info = {
        "phase4_lock_log_sha256": sha256_file(log4),
        "phase4_events": events,
        "phase5_lock_log_content": json.loads(log5.read_text(encoding="utf-8-sig")),
    }
    ok = (
        info["phase4_lock_log_sha256"] == LOCK4_SHA
        and events == ["FREEZE", "OPEN", "CLOSE"]
        and info["phase5_lock_log_content"] == []
    )
    return ok, info


def main(argv: list[str]) -> int:
    failed = False
    pre = json.loads(PREHASH.read_text(encoding="utf-8-sig"))
    n, bad = compare(pre)
    print(f"phase7_prehash: {n} files compared, {len(bad)} mismatches")
    for b in bad:
        print("  ", b)
    failed |= bool(bad)
    if "--phase6" in argv:
        raw = json.loads(PHASE6_PRERUN.read_text(encoding="utf-8-sig"))
        files = raw.get("files", raw)
        files = {k: (v["sha256"] if isinstance(v, dict) else v) for k, v in files.items()}
        n6, bad6 = compare(files)
        expected_diff = [b for b in bad6 if b.endswith("exploratory.duckdb")]
        other = [b for b in bad6 if b not in expected_diff]
        print(
            f"phase6_prerun: {n6} entries, {len(other)} unexpected mismatches, "
            f"{len(expected_diff)} expected (exploratory.duckdb gained p6_* tables)"
        )
        for b in other:
            print("  ", b)
        failed |= bool(other)
    ok, info = lock_status()
    print("lock logs:", json.dumps(info))
    print("lock check:", "PASS" if ok else "FAIL")
    failed |= not ok
    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
