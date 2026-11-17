"""Phase 4 baseline calibration, scoring records, leakage and the test-lock guard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase4 import baseline as bl
from app.phase4 import scoring as sc
from app.phase4.constants import STATUS
from app.phase4.lockguard import drop_test_rows, guard_frame
from app.phase4.split import TestLock, TestPeriodLockError
from tests.phase4_scoring_helpers import synth_frame

PARAMS = {"min_cell_innings": 5, "tau2_floor": 0.01}


@pytest.fixture(scope="module")
def frame():
    return synth_frame(1)


@pytest.fixture(scope="module")
def bset(frame):
    return bl.fit_baseline_set(frame, PARAMS)


@pytest.fixture
def lock(tmp_path):
    return TestLock(tmp_path / "lock.json")


def test_calibration_identity_on_train(frame, bset):
    rep = bl.calibration_report(bset, frame)
    assert bl.identity_ok(rep, 1e-9)
    assert set(rep["streams"]) == {
        "batter:runs",
        "batter:dismissal",
        "bowler:charged",
        "bowler:wkt",
    }


def test_validation_report_has_out_of_period_groups_and_coverage(frame, bset):
    rep = bl.calibration_report(bset, frame)
    blk = rep["streams"]["batter:runs"]["periods"]["VALIDATION"]
    for key in ("by_format", "by_phase", "by_wickets_remaining_bin", "by_expected_decile"):
        assert blk[key]
    assert blk["fallback_rows_finest_cell_unseen"] == 0
    assert sum(blk["level_usage"].values()) == blk["rows"]


def test_later_outcomes_do_not_change_frozen_expectations(frame, bset):
    fr = bl.role_frame("batter", frame)
    base = bset.expected("batter", "runs", fr)["expected"]
    mutated = frame.copy()
    later = mutated["period"] != "TRAIN"
    mutated.loc[later, "out_batter_runs"] = 6.0
    fr2 = bl.role_frame("batter", mutated)
    again = bset.expected("batter", "runs", fr2)["expected"]
    assert np.allclose(base, again)


def test_refit_after_train_mutation_changes_but_validation_mutation_does_not(frame):
    mutated = frame.copy()
    mutated.loc[mutated["period"] == "VALIDATION", "out_batter_runs"] = 6.0
    b2 = bl.fit_baseline_set(mutated, PARAMS)
    b1 = bl.fit_baseline_set(frame, PARAMS)
    f1, f2 = b1.frozen[("batter", "runs")], b2.frozen[("batter", "runs")]
    assert all(np.allclose(a, b) for a, b in zip(f1.value, f2.value, strict=True))
    assert f1.offsets == f2.offsets


def test_unseen_cell_falls_back_to_parent_level(frame, bset):
    fr = bl.role_frame("batter", frame[frame["period"] == "VALIDATION"].head(50))
    fr = fr.assign(wbin="unseen-bin")
    out = bset.expected("batter", "runs", fr)
    assert (out["finest_cell_seen"] == False).all()  # noqa: E712
    assert (out["level_used"] >= 1).all() and out["expected"].notna().all()


def test_train_rows_use_leave_player_out(frame, bset):
    fr = bl.role_frame("batter", frame[frame["period"] == "TRAIN"])
    out = bset.expected("batter", "runs", fr)
    assert (out["basis"] == "TRAIN_LEAVE_PLAYER_OUT").all()


def test_leave_player_out_ignores_own_outcomes(frame):
    mutated = frame.copy()
    m = (mutated["period"] == "TRAIN") & (mutated["striker_id"] == 1)
    mutated.loc[m, "out_batter_runs"] = 6.0
    b1 = bl.fit_baseline_set(frame, PARAMS)
    b2 = bl.fit_baseline_set(mutated, PARAMS)
    e1 = b1.train_lpo[("batter", "runs")]
    e2 = b2.train_lpo[("batter", "runs")]
    own = bl.role_frame("batter", frame[frame["period"] == "TRAIN"])
    own_idx = own.index[own["player_id"] == 1]
    assert np.allclose(e1.loc[own_idx], e2.loc[own_idx])


# ---------------------------------------------------------------- scoring
def test_thresholds_are_train_only(frame):
    with pytest.raises(ValueError):
        sc.fit_thresholds(frame, 0.9)
    tr = frame[frame["period"] == "TRAIN"]
    t1 = sc.fit_thresholds(tr, 0.9)
    mutated = frame.copy()
    mutated.loc[mutated["period"] != "TRAIN", "rrr"] = 99.0
    t2 = sc.fit_thresholds(mutated[mutated["period"] == "TRAIN"], 0.9)
    assert t1 == t2


def test_pressure_flag_by_definition(frame):
    tr = frame[frame["period"] == "TRAIN"]
    thr = sc.fit_thresholds(tr, 0.9)
    chase = sc.pressure_flag(frame, "chase|q0.9", thr)
    assert not chase[frame["innings_number"] == 1].any()
    assert chase.sum() > 0
    anyf = sc.pressure_flag(frame, "any|q0.9", thr)
    assert (anyf | ~chase).all() and anyf.sum() >= chase.sum()
    with pytest.raises(ValueError):
        sc.parse_definition("bogus|q0.9")


def test_unavailable_par_rows_are_never_flagged(frame):
    thr = {k: -1e9 for k in ("chase|IPL", "inn1|IPL", "chase|T20I", "inn1|T20I")}
    d = frame.copy()
    d.loc[d.index[:20], "neg_par_dev_prior"] = np.nan  # as strictly_prior_par does
    flag = sc.pressure_flag(d, "inn1|q0.5", thr)
    assert not flag.iloc[:20].any()


def test_record_schema_and_status(frame, bset, lock):
    thr = sc.fit_thresholds(frame[frame["period"] == "TRAIN"], 0.5)
    rows = sc.residual_rows(frame, bset, "chase|q0.5", thr, "batter", "runs", lock)
    recs, info = sc.score_cell(rows, "batter", "runs", "IPL", "chase|q0.5", bset.version,
                               "shrink_eb", n_boot=50)  # fmt: skip
    assert recs
    r = recs[0].model_dump()
    required = {"raw_pressure_outcome", "expected_baseline_outcome", "residual", "shrunk_estimate",
                "interval_low", "interval_high", "pressure_opportunities", "distinct_matches",
                "effective_sample_size", "eligibility_status", "applied_restrictions",
                "baseline_version", "definition_version", "definition_id"}  # fmt: skip
    assert required <= set(r)
    assert r["status"] == STATUS and r["official_ranking"] is False
    assert r["interval_low"] <= r["interval_high"]
    assert r["pressure_opportunities"] >= r["distinct_matches"] >= 1


def test_scores_do_not_depend_on_outcomes_of_other_formats(frame, bset, lock):
    thr = sc.fit_thresholds(frame[frame["period"] == "TRAIN"], 0.5)
    rows = sc.residual_rows(frame, bset, "chase|q0.5", thr, "batter", "runs", lock)
    a, _ = sc.score_cell(rows, "batter", "runs", "IPL", "chase|q0.5", "v", "shrink_eb", 30)
    rows2 = rows.copy()
    rows2.loc[rows2["comp"] == "T20I", "resid"] += 5.0
    b, _ = sc.score_cell(rows2, "batter", "runs", "IPL", "chase|q0.5", "v", "shrink_eb", 30)
    assert [x.shrunk_estimate for x in a] == [x.shrunk_estimate for x in b]


def test_combined_requires_both_formats_and_never_zero_fills():
    est_i = pd.DataFrame({"shrunk": [1.0, 2.0]}, index=[1, 2])
    est_t = pd.DataFrame({"shrunk": [3.0, 4.0]}, index=[2, 3])
    dr_i = pd.DataFrame(np.ones((2, 5)), index=[1, 2])
    dr_t = pd.DataFrame(np.ones((2, 5)) * 3, index=[2, 3])
    out = sc.combine_formats((est_i, dr_i), (est_t, dr_t), 0.7)
    assert list(out.index) == [2]
    assert abs(out.loc[2, "shrunk"] - (0.7 * 2.0 + 0.3 * 3.0)) < 1e-12


def test_score_all_emits_single_format_and_combined(frame, bset, lock):
    thr = sc.fit_thresholds(frame[frame["period"] == "TRAIN"], 0.5)
    df = sc.score_all(frame, bset, "chase|q0.5", thr, ["shrink_eb", "shrink_none"], lock,
                      n_boot=20)  # fmt: skip
    assert {"IPL", "T20I"} <= set(df["format"])
    assert set(df["shrinkage_config"]) == {"shrink_eb", "shrink_none"}
    assert (df["status"] == STATUS).all()


# ---------------------------------------------------------------- lock guard
def test_guard_refuses_test_rows_and_logs(tmp_path):
    lock = TestLock(tmp_path / "lock.json")
    d = synth_frame(2, with_test=True)
    with pytest.raises(TestPeriodLockError):
        guard_frame(d, lock, "unit")
    assert any(e["event"] == "READ_DENIED" and e["caller"] == "unit" for e in lock.entries)
    assert "TEST" not in set(drop_test_rows(d)["period"])
    with pytest.raises(TestPeriodLockError):
        sc.score_all(d, bl.fit_baseline_set(drop_test_rows(d), PARAMS), "chase|q0.5",
                     {"chase|IPL": 0, "chase|T20I": 0, "inn1|IPL": 0, "inn1|T20I": 0},
                     ["shrink_eb"], lock, n_boot=5)  # fmt: skip


def test_guard_requires_period_column(lock):
    with pytest.raises(TestPeriodLockError):
        guard_frame(pd.DataFrame({"a": [1]}), lock, "x")


def test_test_scoring_needs_a_freeze_and_runs_once(tmp_path):
    lock = TestLock(tmp_path / "lock.json")
    d = synth_frame(3, with_test=True)
    pre = drop_test_rows(d)
    b = bl.fit_baseline_set(pre, PARAMS)
    thr = sc.fit_thresholds(pre[pre["period"] == "TRAIN"], 0.5)
    frozen = tmp_path / "frozen.json"
    frozen.write_text("{}\n", encoding="utf-8")
    args = (b, "chase|q0.5", thr, ["shrink_eb"])
    with pytest.raises(TestPeriodLockError):  # no FREEZE entry yet
        sc.evaluate_test_scores(frozen, lock, lambda: d, *args, n_boot=5)
    lock.freeze(frozen)
    out = sc.evaluate_test_scores(frozen, lock, lambda: d, *args, n_boot=5)
    assert len(out) > 0
    with pytest.raises(TestPeriodLockError):  # a second opening is refused
        sc.evaluate_test_scores(frozen, lock, lambda: d, *args, n_boot=5)


def test_combined_record_populates_sample_fields_from_formats():
    def rec(fmt, n, m, ess, raw, exp):
        return sc.PressureRecord(
            player_id=1, role="batter", stream="runs", format=fmt, window="PRE_TEST",
            definition_id="chase|q0.9", baseline_version="b", shrinkage_config="shrink_eb",
            raw_pressure_outcome=raw, expected_baseline_outcome=exp, residual=raw - exp,
            shrunk_estimate=0.1, interval_low=0.0, interval_high=0.2, posterior_sd=0.1,
            data_weight=0.5, shrinkage_k=10.0, shrinkage_floor_hit=False,
            pressure_opportunities=n, distinct_matches=m, effective_sample_size=ess,
            eligibility_status="ELIGIBLE_PLACEHOLDER", applied_restrictions="x",
        )  # fmt: skip

    a = rec("IPL", 100, 20, 80.0, 1.2, 1.0)
    b = rec("T20I", 50, 10, 40.0, 0.8, 1.0)
    row = pd.Series({"shrunk": 0.1, "interval_low": 0.0, "interval_high": 0.2})
    out = sc._combined_record(1, "batter", "runs", "d", "b", "shrink_eb", 0.7, row, (a, b))
    assert out["pressure_opportunities"] == 150
    assert out["distinct_matches"] == 30
    assert out["effective_sample_size"] == pytest.approx(1 / (0.49 / 80 + 0.09 / 40))
    assert out["raw_pressure_outcome"] == pytest.approx(0.7 * 1.2 + 0.3 * 0.8)
    assert out["residual"] == pytest.approx(
        out["raw_pressure_outcome"] - out["expected_baseline_outcome"]
    )
    assert out["shrinkage_k"] is None and out["status"] == STATUS
