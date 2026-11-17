"""TEST-lock guards for Phase 6. Nothing here opens, resets or writes a lock log."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.phase5.lockguard import (  # noqa: F401  (re-exported)
    LOCK_LOG,
    PHASE5_LOCK_LOG,
    LockGuardError,
    assert_phase4_lock_untouched,
    assert_phase5_lock_not_opened,
    file_sha256,
    read_events,
)


def assert_no_test_rows(df: pd.DataFrame) -> None:
    """Raise ``LockGuardError`` if a frame holds a TEST period in any period column."""
    for col in ("period", "period_orig"):
        if col in df.columns and (df[col].astype(str) == "TEST").any():
            raise LockGuardError(f"TEST rows found in column '{col}'")


def lock_state() -> dict[str, Any]:
    """Current evidence: Phase 4 lock log hash and Phase 5 lock event count (read-only)."""
    return {
        "phase4_lock_log_sha256": file_sha256(LOCK_LOG) if LOCK_LOG.exists() else None,
        "phase4_events": [str(e.get("event")) for e in read_events(LOCK_LOG)],
        "phase5_events": len(read_events(PHASE5_LOCK_LOG)),
    }


def assert_lock_state_unchanged(before: dict[str, Any]) -> dict[str, Any]:
    """Raise if the Phase 4 lock log changed or any Phase 5 lock event appeared."""
    now = lock_state()
    if now["phase4_lock_log_sha256"] != before["phase4_lock_log_sha256"]:
        raise LockGuardError("the phase4 TEST lock log changed during this run")
    if now["phase5_events"] != before["phase5_events"] or now["phase5_events"] != 0:
        raise LockGuardError("a phase5 TEST lock event exists or was added")
    assert_phase5_lock_not_opened()
    return now
