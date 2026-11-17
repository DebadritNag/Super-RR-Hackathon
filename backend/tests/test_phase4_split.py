"""Temporal split integrity, test-period lock, p4 store guard."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from app.phase4.config import Phase4ConfigError, load_split_config
from app.phase4.constants import SPLIT_CONFIG
from app.phase4.split import (
    Split,
    SplitIntegrityError,
    TestLock,
    TestPeriodLockError,
    assign_matches,
    attach_period,
    check_split_integrity,
    evaluate_on_test,
    split_frames,
    write_frozen_choices,
)
from app.phase4.store import write_p4_table
from app.services.pressure_service import StoreError
from tests.phase4_helpers import many_matches


@pytest.fixture()
def split():
    return Split.from_config()


def dates(*d):
    return pd.Series(pd.to_datetime(list(d)))


def test_boundaries_come_from_the_config_file():
    cfg = load_split_config()
    assert cfg["periods"]["TRAIN"]["end"] == "2024-12-31"
    s = Split.from_config()
    assert s.train_end == pd.Timestamp("2024-12-31")
    assert s.test_start == pd.Timestamp("2026-01-01")
    shifted = json.loads(SPLIT_CONFIG.read_text(encoding="utf-8"))
    shifted["periods"]["TRAIN"]["end"] = "2023-12-31"
    shifted["periods"]["VALIDATION"]["start"] = "2024-01-01"
    s2 = Split.from_config(shifted)
    assert s2.period_of("2024-06-01") == "VALIDATION"
    assert s.period_of("2024-06-01") == "TRAIN"


def test_assign_period_at_the_boundaries(split):
    got = split.assign_period(
        dates("2022-01-22", "2024-12-31", "2025-01-01", "2025-12-31", "2026-01-01", "2026-11-01")
    ).tolist()
    assert got == ["TRAIN", "TRAIN", "VALIDATION", "VALIDATION", "TEST", "TEST"]


def test_time_of_day_does_not_move_a_match(split):
    got = split.assign_period(
        pd.Series(pd.to_datetime(["2024-12-31 23:59:59", "2025-12-31 18:00:00"]))
    )
    assert got.tolist() == ["TRAIN", "VALIDATION"]


def test_invalid_boundaries_are_rejected():
    cfg = load_split_config()
    gap = json.loads(json.dumps(cfg))
    gap["periods"]["VALIDATION"]["start"] = "2025-02-01"
    with pytest.raises(SplitIntegrityError):
        Split.from_config(gap)
    missing = {k: v for k, v in cfg.items() if k != "periods"}
    with pytest.raises(Phase4ConfigError):
        Split.from_config(missing)


def test_missing_dates_are_rejected(split):
    with pytest.raises(SplitIntegrityError):
        split.assign_period(pd.Series([pd.Timestamp("2024-01-01"), pd.NaT]))


def test_matches_and_deliveries_stay_together(split):
    df = many_matches(
        [
            (1, "2024-12-31", "IPL", 1.0),
            (2, "2025-01-01", "IPL", 1.0),
            (3, "2026-03-01", "T20I", 1.0),
        ]
    )
    d = attach_period(df, split)
    assert d.groupby("match_id")["period"].nunique().max() == 1
    assert d.groupby("match_id")["period"].first().to_dict() == {
        1: "TRAIN",
        2: "VALIDATION",
        3: "TEST",
    }
    report = check_split_integrity(d, split)
    assert report["matches_in_more_than_one_period"] == 0
    assert report["rows_with_period_not_equal_to_date_rule"] == 0
    assert report["periods_strictly_ordered_by_date"] is True
    m = assign_matches(d, split)
    assert m["period"].tolist() == ["TRAIN", "VALIDATION", "TEST"]


def test_integrity_check_detects_a_row_level_split(split):
    d = attach_period(many_matches([(1, "2024-06-01", "IPL", 1.0)]), split)
    d.loc[d.index[:10], "period"] = "TEST"  # a row-level (random-style) assignment
    report = check_split_integrity(d, split)
    assert report["matches_in_more_than_one_period"] == 1
    assert report["rows_with_period_not_equal_to_date_rule"] == 10


def test_assignment_is_deterministic_and_order_independent(split):
    df = many_matches([(i, f"202{4 + i % 3}-0{1 + i % 9}-15", "IPL", 1.0) for i in range(1, 12)])
    a = attach_period(df, split)["period"].tolist()
    b = attach_period(df.sample(frac=1.0, random_state=3).sort_index(), split)["period"].tolist()
    assert a == b


def test_real_state_split_is_chronological(split):
    from app.phase4.data import load_state_with_period

    try:
        df = load_state_with_period(split)
    except Exception:  # pragma: no cover - store absent
        pytest.skip("exploratory store not available")
    rep = check_split_integrity(df, split)
    assert rep["matches_in_more_than_one_period"] == 0
    assert rep["rows_with_period_not_equal_to_date_rule"] == 0
    assert rep["periods_strictly_ordered_by_date"] is True


def test_rolling_origins_fit_strictly_before_the_origin(split):
    folds = split.rolling_folds()
    assert [f["origin"] for f in folds] == [pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")]
    d = pd.Series(pd.to_datetime(["2023-12-31", "2024-01-01", "2024-12-31", "2025-01-01"]))
    fit, ev = split.fold_masks(d, folds[0])
    assert fit.tolist() == [True, False, False, False]
    assert ev.tolist() == [False, True, True, False]
    assert not (fit & ev).any()


# ---------------------------------------------------------------- lock
def _frames(split, lock):
    df = many_matches(
        [
            (1, "2024-06-01", "IPL", 1.0),
            (2, "2025-06-01", "IPL", 1.0),
            (3, "2026-06-01", "IPL", 1.0),
        ]
    )
    return split_frames(df, split, lock)


def test_test_outcomes_are_unreadable_and_logged(split, tmp_path):
    lock = TestLock(tmp_path / "lock.json")
    fr = _frames(split, lock)
    assert "out_runs_row" not in fr.test_state.columns
    assert "post_innings_wickets" not in fr.test_state.columns
    assert "rrr" in fr.test_state.columns  # non-outcome state stays readable
    assert "out_runs_row" in fr.test_outcomes.columns
    with pytest.raises(TestPeriodLockError):
        fr.test_outcomes["out_runs_row"]
    with pytest.raises(TestPeriodLockError):
        fr.test_outcomes.to_numpy()
    log = json.loads((tmp_path / "lock.json").read_text(encoding="utf-8"))
    assert [e["event"] for e in log] == ["READ_DENIED", "READ_DENIED"]
    assert [e["seq"] for e in log] == [1, 2]
    assert "out_runs_row" in log[0]["columns"]
    assert len(fr.train) == 120 and len(fr.validation) == 120 and len(fr.test_state) == 120
    assert "out_runs_row" in fr.train.columns  # TRAIN outcomes are ordinary data


def test_evaluation_opens_the_lock_once_after_a_freeze(split, tmp_path):
    lock = TestLock(tmp_path / "lock.json")
    fr = _frames(split, lock)
    frozen = tmp_path / "frozen.json"
    write_frozen_choices({"definition": "chase|q0.9", "shrinkage": "primary"}, frozen, lock)
    total = evaluate_on_test(frozen, lock, lambda lk: float(fr.test_outcomes["out_runs_row"].sum()))
    assert total == 120.0
    assert not lock.is_open  # closed again
    events = [e["event"] for e in lock.entries]
    assert events == ["FREEZE", "OPEN", "CLOSE"]
    with pytest.raises(TestPeriodLockError):
        fr.test_outcomes["out_runs_row"]
    with pytest.raises(TestPeriodLockError):  # second opening is refused
        evaluate_on_test(frozen, lock, lambda lk: None)


def test_evaluation_refuses_missing_or_modified_frozen_file(split, tmp_path):
    lock = TestLock(tmp_path / "lock.json")
    with pytest.raises(TestPeriodLockError):
        evaluate_on_test(tmp_path / "absent.json", lock, lambda lk: None)
    frozen = tmp_path / "frozen.json"
    write_frozen_choices({"definition": "chase|q0.9"}, frozen, lock)
    frozen.write_text('{"definition": "inn1|q0.95"}\n', encoding="utf-8")
    with pytest.raises(TestPeriodLockError):
        evaluate_on_test(frozen, lock, lambda lk: None)
    assert not lock.opened_before()


def test_evaluation_refuses_without_a_freeze_entry(split, tmp_path):
    lock = TestLock(tmp_path / "lock.json")
    frozen = tmp_path / "frozen.json"
    frozen.write_text("{}\n", encoding="utf-8")  # written but never frozen
    with pytest.raises(TestPeriodLockError):
        evaluate_on_test(frozen, lock, lambda lk: None)


def test_mutating_test_outcomes_does_not_change_train_or_validation(split, tmp_path):
    df = many_matches(
        [
            (1, "2024-06-01", "IPL", 1.0),
            (2, "2025-06-01", "IPL", 2.0),
            (3, "2026-06-01", "IPL", 3.0),
        ]
    )
    mutated = df.copy()
    mutated.loc[mutated["match_id"] == 3, ["out_runs_row", "team_runs_before"]] = 99.0
    a = split_frames(df, split, TestLock(tmp_path / "a.json"))
    b = split_frames(mutated, split, TestLock(tmp_path / "b.json"))
    pd.testing.assert_frame_equal(a.train, b.train)
    pd.testing.assert_frame_equal(a.validation, b.validation)
    pd.testing.assert_frame_equal(
        a.test_state.drop(columns=["team_runs_before"]),
        b.test_state.drop(columns=["team_runs_before"]),
    )


# ---------------------------------------------------------------- store guard
def test_store_writes_only_p4_tables_and_never_the_official_db(tmp_path):
    store = tmp_path / "exploratory.duckdb"
    df = pd.DataFrame({"a": [1, 2]})
    assert write_p4_table(df, "p4_demo", store, tmp_path / "official.duckdb") == 2
    with pytest.raises(StoreError):
        write_p4_table(df, "exp_pre_delivery_state", store, tmp_path / "official.duckdb")
    with pytest.raises(StoreError):
        write_p4_table(df, "p4_x; DROP TABLE y", store, tmp_path / "official.duckdb")
    with pytest.raises(StoreError):
        write_p4_table(df, "p4_demo", store, store)
