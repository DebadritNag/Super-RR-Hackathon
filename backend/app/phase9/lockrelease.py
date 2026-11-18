"""Owner release of the TEST period (Phase 9, decision D1).

``app.phase4.split.TestLock`` has no release API (FREEZE / OPEN / CLOSE / READ_DENIED only, one
OPEN). The Phase 4 and Phase 5 lock logs are protected evidence and are never edited. The release is
therefore a separate append-only record, ``phase9_lock_release_log.json``, with the same layout as
``TestLock._append`` (list of events with ``seq``) plus the SHA-256 of every earlier lock log and of
the criteria file, so that the release is tied to the exact state it was made from.

From the release on there is no pristine hold-out: every report must say so.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.analytics.integrity import sha256_file
from app.phase8.constants import CRITERIA_FILE, REPORTS_DIR
from app.phase8.lockguard import LockGuardError

RELEASE_LOG = REPORTS_DIR / "phase9_lock_release_log.json"
PHASE4_LOCK_LOG = REPORTS_DIR / "phase4_lock_log.json"
PHASE5_LOCK_LOG = REPORTS_DIR / "phase5_lock_log.json"
FROZEN_CHOICES = REPORTS_DIR / "phase4_frozen_choices.json"
REASON = "owner decision phase 9"
EXPECTED_CRITERIA_SHA256 = "9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64"


class ReleaseError(LockGuardError):
    """The TEST period was requested without a recorded owner release."""


def read_release_events(path: Path | str = RELEASE_LOG) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8") or "[]")
    return data if isinstance(data, list) else []


def is_released(path: Path | str = RELEASE_LOG) -> bool:
    return any(e.get("event") == "RELEASE" for e in read_release_events(path))


def assert_test_released(path: Path | str = RELEASE_LOG) -> dict[str, Any]:
    """Return the RELEASE event or raise ``ReleaseError`` when no owner release was recorded."""
    for e in read_release_events(path):
        if e.get("event") == "RELEASE" and e.get("reason") == REASON:
            return e
    raise ReleaseError("TEST is locked: no owner RELEASE record (phase 9) exists")


def _hash(p: Path) -> str | None:
    return sha256_file(p) if p.exists() else None


def release_test_lock(
    path: Path | str = RELEASE_LOG, date: str = "2026-11-18", owner_note: str = ""
) -> dict[str, Any]:
    """Append the RELEASE event once (idempotent: an existing release is returned unchanged).

    Earlier lock logs are only read and hashed. Nothing is deleted or rewritten.
    """
    events = read_release_events(path)
    for e in events:
        if e.get("event") == "RELEASE":
            return e
    crit = _hash(Path(CRITERIA_FILE))
    if crit != EXPECTED_CRITERIA_SHA256:
        raise ReleaseError(f"criteria file hash {crit} differs from the declared hash")
    event = {
        "event": "RELEASE",
        "seq": len(events) + 1,
        "reason": REASON,
        "date": date,
        "recorded_at": datetime.now(UTC).isoformat(),
        "scope": "2026 matches (period TEST of config/phase4_split_v1.json), IPL and T20I",
        "owner_attestation": (
            "All the 2026 data are genuine, including the 42 late-dated T20I matches "
            "(owner attestation, not an official third-party verification)."
        ),
        "pristine_holdout_remaining": False,
        "phase4_lock_log_sha256": _hash(PHASE4_LOCK_LOG),
        "phase5_lock_log_sha256": _hash(PHASE5_LOCK_LOG),
        "phase4_frozen_choices_sha256": _hash(FROZEN_CHOICES),
        "criteria_sha256": crit,
        "note": owner_note
        or "Phase 4 and Phase 5 lock logs are unchanged; this is a separate append-only record.",
    }
    events.append(event)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(events, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return event
