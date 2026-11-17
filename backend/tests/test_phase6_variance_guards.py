"""TEST-lock guard, store guards and the no-Cricsheet rule for the chunk 2 modules."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from app.phase5.constants import REPORTS_DIR
from app.phase6 import lockguard as lg
from app.phase6.store import write_p6_table
from app.services.pressure_service import StoreError

ROOT = Path(__file__).resolve().parents[1]
PHASE6_FILES = sorted((ROOT / "app" / "phase6").glob("*.py")) + sorted(
    (ROOT / "scripts").glob("phase6_*.py")
)


def test_assert_no_test_rows_raises_on_test_period():
    ok = pd.DataFrame({"period": ["TRAIN", "VALIDATION"]})
    lg.assert_no_test_rows(ok)
    with pytest.raises(lg.LockGuardError):
        lg.assert_no_test_rows(pd.DataFrame({"period": ["TRAIN", "TEST"]}))
    with pytest.raises(lg.LockGuardError):
        lg.assert_no_test_rows(pd.DataFrame({"period": ["TRAIN"], "period_orig": ["TEST"]}))


def test_lock_state_is_read_only_and_unchanged_across_a_noop():
    before = lg.lock_state()
    assert before["phase5_events"] == 0
    after = lg.assert_lock_state_unchanged(before)
    assert after["phase4_lock_log_sha256"] == before["phase4_lock_log_sha256"]


def test_lock_state_change_is_detected():
    before = lg.lock_state()
    tampered = {**before, "phase4_lock_log_sha256": "0" * 64}
    with pytest.raises(lg.LockGuardError):
        lg.assert_lock_state_unchanged(tampered)
    with pytest.raises(lg.LockGuardError):
        lg.assert_lock_state_unchanged({**before, "phase5_events": 1})


def test_phase5_lock_log_has_no_events():
    p = REPORTS_DIR / "phase5_lock_log.json"
    if p.exists():
        assert json.loads(p.read_text("utf-8") or "[]") == []


def test_p6_writer_rejects_other_prefixes_and_the_official_database(tmp_path):
    df = pd.DataFrame({"a": [1]})
    store = tmp_path / "s.duckdb"
    for bad in ("p5_x", "p4_x", "x", "p6_", "P6_X", "p6_x;drop"):
        with pytest.raises(StoreError):
            write_p6_table(df, bad, store)
    official = tmp_path / "off.duckdb"
    with pytest.raises(StoreError):
        write_p6_table(df, "p6_x", official, official_db=official)
    assert write_p6_table(df, "p6_ok", store) == 1


def test_no_cricsheet_and_no_lock_writes_in_phase6_sources():
    assert PHASE6_FILES
    for f in PHASE6_FILES:
        tree = ast.parse(f.read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not [n for n in names if "cricsheet" in n.lower()], f.name
        text = f.read_text("utf-8")
        for needle in ("open_test", "TestLock(", ".open(", "reset_lock"):
            assert needle not in text or f.name == "cleanup_scans.py", (f.name, needle)
