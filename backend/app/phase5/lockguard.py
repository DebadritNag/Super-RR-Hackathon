"""Read-only TEST-lock guards for Phase 5. Nothing here opens, resets or writes a lock log."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.phase4.split import LOCK_LOG
from app.phase5.constants import REPORTS_DIR

PHASE5_LOCK_LOG = REPORTS_DIR / "phase5_lock_log.json"


class LockGuardError(RuntimeError):
    """The TEST lock evidence changed or a Phase 5 opening was recorded."""


def file_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_events(path: Path | str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8") or "[]")
    return data if isinstance(data, list) else []


def phase4_lock_events(path: Path | str = LOCK_LOG) -> list[str]:
    return [str(e.get("event")) for e in read_events(path)]


def assert_phase4_lock_untouched(expected_sha256: str, path: Path | str = LOCK_LOG) -> str:
    """Raise unless the Phase 4 lock log bytes still hash to ``expected_sha256``."""
    digest = file_sha256(path)
    if digest != expected_sha256:
        raise LockGuardError(f"phase4 lock log changed: {digest} != {expected_sha256}")
    return digest


def assert_phase5_lock_not_opened(path: Path | str = PHASE5_LOCK_LOG) -> int:
    """Raise if the Phase 5 lock log holds an OPEN event. Returns the event count."""
    events = read_events(path)
    if any(e.get("event") == "OPEN" for e in events):
        raise LockGuardError("the phase5 TEST lock log records an OPEN event")
    return len(events)
