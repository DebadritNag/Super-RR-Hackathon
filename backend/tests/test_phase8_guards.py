"""Phase 8 guards: TEST lock, Cricsheet, protected files and splits."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from app.phase4.split import SplitIntegrityError
from app.phase8 import lockguard, splits
from app.phase8.constants import PREHASH_FILE
from app.phase8.lockguard import IntegrityError, LockGuardError

PKG = Path(__file__).resolve().parents[1] / "app" / "phase8"
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _code(p: Path) -> str:
    """Source without comments and docstring-only lines is not needed: scan raw text."""
    return p.read_text(encoding="utf-8")


def test_no_cricsheet_in_scoring_modules():
    """Only the criteria guard may name Cricsheet (as a forbidden input)."""
    for p in sorted(PKG.glob("*.py")) + sorted(SCRIPTS.glob("phase8_*.py")):
        text = _code(p).lower()
        if p.name == "criteria.py":
            continue
        assert "cricsheet" not in text, p.name


def test_phase8_never_opens_the_test_lock():
    for p in sorted(PKG.glob("*.py")) + sorted(SCRIPTS.glob("phase8_*.py")):
        text = _code(p)
        assert "evaluate_on_test" not in text, p.name
        assert "_open_for_evaluation" not in text, p.name
        assert "TestLock(" not in text, p.name


def test_no_source_csv_reads_of_excluded_files():
    for p in sorted(PKG.glob("*.py")) + sorted(SCRIPTS.glob("phase8_*.py")):
        text = _code(p)
        assert "read_csv" not in text, p.name
        if p.name != "criteria.py":  # the criteria text names the excluded files as unused
            assert not re.search(r"matches 2026|stats2026", text), p.name


def test_test_rows_are_refused():
    df = pd.DataFrame({"match_id": [1, 2], "period": ["TRAIN", "TEST"]})
    with pytest.raises(LockGuardError):
        lockguard.assert_no_test_rows(df)
    with pytest.raises(LockGuardError):
        splits.assert_pre_test(df)
    with pytest.raises(SplitIntegrityError):
        splits.assert_pre_test(pd.DataFrame({"match_id": [1]}))
    with pytest.raises(SplitIntegrityError):
        splits.assert_pre_test(pd.DataFrame({"match_id": [1], "period": ["OTHER"]}))
    ok = pd.DataFrame({"match_id": [1, 2], "period": ["TRAIN", "VALIDATION"]})
    assert splits.assert_pre_test(ok) is ok


def test_lock_state_is_stable_and_unopened():
    before = lockguard.lock_state()
    after = lockguard.assert_lock_state_unchanged(before)
    assert after["phase5_events"] == 0
    assert before["phase4_lock_log_sha256"] == after["phase4_lock_log_sha256"]


def test_split_matches_phase4_config():
    sp = splits.load_split()
    assert str(sp.train_end.date()) == "2024-12-31"
    assert sp.period_of("2025-06-01") == "VALIDATION"
    assert sp.period_of("2026-01-01") == "TEST"


def _frame(rows):
    return pd.DataFrame(rows, columns=["match_id", "match_date", "period"])


def test_split_integrity_detects_straddling_match():
    df = _frame(
        [
            (1, pd.Timestamp("2024-12-30"), "TRAIN"),
            (1, pd.Timestamp("2024-12-30"), "VALIDATION"),
        ]
    )
    with pytest.raises(SplitIntegrityError):
        splits.check_match_partition(df)


def test_split_integrity_detects_wrong_period_label():
    df = _frame([(1, pd.Timestamp("2025-03-01"), "TRAIN")])
    with pytest.raises(SplitIntegrityError):
        splits.check_match_partition(df)


def test_split_integrity_accepts_chronological_partition():
    df = _frame(
        [
            (1, pd.Timestamp("2024-05-01"), "TRAIN"),
            (2, pd.Timestamp("2024-05-02"), "TRAIN"),
            (3, pd.Timestamp("2025-05-01"), "VALIDATION"),
        ]
    )
    out = splits.check_match_partition(df)
    assert out["matches_per_period"] == {"TRAIN": 2, "VALIDATION": 1}


def test_fold_assignment_is_deterministic_and_keeps_matches_together():
    ids = pd.Series([5, 6, 7, 5, 6, 7, 10])
    f1, f2 = splits.fold_of(ids), splits.fold_of(ids)
    assert list(f1) == list(f2) == [0, 1, 2, 0, 1, 2, 0]
    assert f1.groupby(ids.to_numpy()).nunique().max() == 1


def test_assert_fit_on_train():
    df = pd.DataFrame({"match_id": [1, 2, 3], "period": ["TRAIN", "TRAIN", "VALIDATION"]})
    splits.assert_fit_on_train([1, 2], df)
    with pytest.raises(SplitIntegrityError):
        splits.assert_fit_on_train([1, 3], df)


def test_protected_files_unchanged():
    out = lockguard.check_protected()
    assert out["ok"] and out["checked"] >= 2


def test_protected_check_detects_a_change(tmp_path):
    target = tmp_path / "f.duckdb"
    target.write_bytes(b"abc")
    rec = tmp_path / "pre.json"
    rec.write_text(json.dumps({str(target): "0" * 64}), encoding="utf-8")
    with pytest.raises(IntegrityError):
        lockguard.check_protected(rec)
    rec.write_text(json.dumps({str(tmp_path / "gone.duckdb"): "0" * 64}), encoding="utf-8")
    with pytest.raises(IntegrityError):
        lockguard.check_protected(rec)


def test_prehash_file_covers_both_databases():
    rec = lockguard.load_prehash(PREHASH_FILE)
    names = " ".join(rec)
    assert "exploratory.duckdb" in names and "superr.duckdb" in names
