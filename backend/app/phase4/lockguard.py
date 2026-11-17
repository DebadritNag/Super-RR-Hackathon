"""Test-period lock guard for Phase 4 scoring code.

Any frame that still contains TEST-period rows is refused (and the refusal is logged in the
append-only lock log) unless ``evaluate_on_test`` has opened the lock. The guard is a
convention-level control, not a security boundary.
"""

from __future__ import annotations

import pandas as pd

from app.phase4.split import TestLock, TestPeriodLockError


def guard_frame(df: pd.DataFrame, lock: TestLock, caller: str) -> pd.DataFrame:
    """Return ``df`` unchanged, or raise (and log) when it holds TEST rows with the lock closed."""
    if "period" not in df.columns:
        raise TestPeriodLockError("frame has no 'period' column; cannot prove it excludes TEST")
    if not lock.is_open and bool((df["period"] == "TEST").any()):
        lock.denied(caller, ["period=TEST"])
        raise TestPeriodLockError(f"{caller}: TEST rows refused while the test lock is closed")
    return df


def drop_test_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Selection-time view: TRAIN and VALIDATION rows only (rows are filtered, never deleted)."""
    return df[df["period"] != "TEST"].reset_index(drop=True)
