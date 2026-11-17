"""Floor arithmetic (k_for), the 48 stored contexts and the context runner on synthetic rows."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.phase4 import shrink as sh
from app.phase5 import context_stats as cs
from app.phase5.constants import REPORTS_DIR
from app.phase6 import variance_floor as vf
from app.phase6.criteria import CRITERIA
from app.phase6.lockguard import LockGuardError
from tests.phase5_ctx_helpers import synth_stats

HAND = {"shrink_none": 0.0, "shrink_eb": 100.0, "shrink_tau0.5": 100.0, "shrink_tau2": 50.0,
        "shrink_tau4": 25.0, "shrink_floor0.001": 1000.0, "shrink_target0": 100.0}  # fmt: skip


def test_floor_hit_k_matches_hand_formula_for_every_config():
    fit = {"sigma2": 3.0, "between": -1.0}
    for name, cfg in sh.CONFIGS.items():
        got = sh.k_for(fit, name)["k"]
        if cfg["zero"]:
            assert got == 0.0
        else:
            hand = 3.0 / (max(cfg["mult"] * cfg["floor"], cfg["floor"]) * 3.0)
            assert got == pytest.approx(hand)
        assert got == pytest.approx(HAND[name])


def test_tau4_floor_hit_is_25_not_100():
    fit = {"sigma2": 3.12, "between": -1.08}
    k = sh.k_for(fit, "shrink_tau4")
    assert k["floor_hit"] is True
    assert k["k"] == pytest.approx(25.0)
    assert k["tau2"] == pytest.approx(4 * 0.01 * 3.12)
    assert k["k"] == pytest.approx(3.12 / (0.01 * 3.12 * 4.0))


def test_multiplier_below_one_cannot_go_under_the_floor():
    assert sh.k_for({"sigma2": 2.0, "between": -5.0}, "shrink_tau0.5")["k"] == pytest.approx(100.0)


def test_non_finite_branch_returns_one_over_floor():
    fit = {"sigma2": float("nan"), "between": float("nan")}
    assert sh.k_for(fit, "shrink_tau4")["k"] == pytest.approx(100.0)
    assert sh.k_for(fit, "shrink_floor0.001")["k"] == pytest.approx(1000.0)
    assert sh.k_for(fit, "shrink_tau4")["floor_hit"] is True


def test_floor_arithmetic_table_agrees_and_covers_all_configs():
    t = vf.floor_arithmetic_table()
    assert set(t["config"]) == set(sh.CONFIGS)
    assert len(t) == 2 * len(sh.CONFIGS)
    assert t["agrees"].all()
    row = t[(t["config"] == "shrink_tau4") & (t["branch"] == "floor_hit")].iloc[0]
    assert row["k_for"] == pytest.approx(25.0) and row["k_hand"] == pytest.approx(25.0)


@pytest.mark.skipif(
    not (REPORTS_DIR / "phase5_context_fit.json").exists(), reason="stored Phase 5 fit absent"
)
def test_stored_48_contexts_all_floor_hits_with_k_25():
    recs = json.loads((REPORTS_DIR / "phase5_context_fit.json").read_text("utf-8"))["records"]
    assert len(recs) == 48
    assert all(r["shrink_config"] == "shrink_tau4" for r in recs)
    assert all(r["floor_hit"] for r in recs)
    assert all(r["k"] == pytest.approx(25.0) for r in recs)
    assert all(r["between"] < 0.01 * r["sigma2"] for r in recs)


def test_context_keys_are_48():
    keys = vf.context_keys()
    assert len(keys) == 48 and len(set(keys)) == 48


def test_runner_on_synthetic_contexts_returns_a_row_per_context_and_window():
    stats = synth_stats()
    inv = {"min_train_players_for_fit": 8, "min_balls_variants": [1, 12],
           "shrinkage_config": "shrink_tau4", "reliability_targets": [0.5, 0.7, 0.8],
           "detectability": {"tau2_over_sigma2_grid": [0.005, 0.01], "replications": 50}}  # fmt: skip
    est, dg = vf.run_contexts(stats, CRITERIA, inv, n_boot=60, seed=5)
    ctx = dg[dg["unit_kind"] == "context"]
    assert len(ctx) == 96  # 48 contexts x 2 windows
    assert set(ctx["window"]) == {"TRAIN", "PRE_TEST"}
    assert set(ctx["verdict"]) <= {*vf.VERDICTS, "NOT_ESTIMABLE"}
    assert est["estimator"].isin(["E1", "E1b", "E1c", "E2", "E3", "E5", "E6", "E7"]).all()
    est2, dg2 = vf.run_contexts(stats, CRITERIA, inv, n_boot=60, seed=5)
    pd.testing.assert_frame_equal(dg, dg2)  # seeded and deterministic
    pd.testing.assert_frame_equal(est, est2)


def test_runner_refuses_test_rows():
    stats = synth_stats()
    stats.loc[stats.index[0], "period"] = "TEST"
    with pytest.raises(cs.ContextStatsError):
        vf.run_contexts(stats, CRITERIA, {}, n_boot=10, seed=1)


def test_cd_from_context_refuses_test_rows():
    stats = synth_stats()
    sub = cs.select(stats, "IPL", "batter", cs.ALL, cs.ALL).copy()
    sub.loc[sub.index[0], "period"] = "TEST"
    with pytest.raises(LockGuardError):
        vf.cd_from_context(sub)


def test_fit_from_cd_matches_phase4_fit_on_a_context():
    stats = synth_stats()
    sub = cs.select(stats, "IPL", "batter", cs.ALL, cs.ALL)
    cd, cell = vf.cd_from_context(sub)
    mine = vf.fit_from_cd(cd.select_cols(np.isin(cd.period, ["TRAIN"])))
    ref = cell.fit()
    assert mine["sigma2"] == pytest.approx(ref["sigma2"], rel=1e-9)
    assert mine["between"] == pytest.approx(ref["between"], rel=1e-9)
    assert mine["players"] == ref["players"]
