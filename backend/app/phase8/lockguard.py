"""TEST-lock and protected-file guards for Phase 8. Nothing here opens or writes a lock log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.analytics.integrity import sha256_file
from app.phase5.lockguard import LockGuardError
from app.phase6.lockguard import (  # noqa: F401  (re-exported)
    assert_lock_state_unchanged,
    assert_no_test_rows,
    lock_state,
)
from app.phase8.constants import active_prehash


class IntegrityError(RuntimeError):
    """A protected file differs from the recorded pre-run hash."""


def load_prehash(path: Path | str | None = None) -> dict[str, str]:
    p = Path(path or active_prehash())
    if not p.exists():
        raise IntegrityError(f"prehash file missing: {p}")
    return json.loads(p.read_text(encoding="utf-8-sig"))


def check_protected(
    path: Path | str | None = None, only: tuple[str, ...] = ("duckdb",)
) -> dict[str, Any]:
    """Compare protected files with the recorded hashes; raise ``IntegrityError`` on a change.

    ``only`` limits the check to recorded paths containing one of the given substrings (the full
    manifest is checked by passing an empty tuple).
    """
    rec = load_prehash(path)
    bad, checked = [], 0
    for name, digest in rec.items():
        if only and not any(s in name for s in only):
            continue
        p = Path(name)
        if not p.exists():
            bad.append((name, "missing"))
            continue
        checked += 1
        if sha256_file(p) != digest:
            bad.append((name, "changed"))
    if bad:
        raise IntegrityError(f"protected files changed or missing: {bad}")
    return {"checked": checked, "ok": True}


__all__ = [
    "IntegrityError",
    "LockGuardError",
    "assert_lock_state_unchanged",
    "assert_no_test_rows",
    "check_protected",
    "load_prehash",
    "lock_state",
]
