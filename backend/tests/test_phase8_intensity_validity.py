"""Intensity validity tests on synthetic deliveries with a known effect."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.phase8.intensity_validity import (
    assign_bins,
    decile_edges,
    run_validity_tests,
    summarise_candidates,
)


def _frame(effect: float, n=24000, seed=2):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 1, n)
    df = pd.DataFrame(
        {
            "match_id": rng.integers(0, 400, n),
            "innings_number": rng.integers(1, 3, n),
            "innings_phase": rng.choice(["powerplay", "middle", "death"], n),
            "period": np.where(rng.uniform(size=n) < 0.7, "TRAIN", "VALIDATION"),
            "ok_run_target": True,
            "ok_wicket_target": True,
        }
    )
    df["den_bowler_charged_runs"] = np.clip(np.round(rng.normal(1.4 - effect * x, 1.5)), 0, 6)
    df["out_is_wicket"] = rng.uniform(size=n) < (0.04 + 0.06 * effect * x)
    return df, pd.DataFrame({"w_PX": x, "w_PN": rng.uniform(0, 1, n)}, index=df.index)


def test_edges_and_bins_are_equal_count():
    x = np.random.default_rng(0).uniform(size=5000)
    e = decile_edges(x)
    b = assign_bins(x, e)
    assert len(e) == 9
    assert np.bincount(b).min() > 450
    assert (assign_bins(np.array([np.nan]), e) == -1).all()


def test_real_effect_passes_a_and_b_and_noise_fails():
    df, w = _frame(1.0)
    t = run_validity_tests(df, w)
    s = summarise_candidates(t, reference=()).set_index("candidate")
    assert bool(s.loc["PX", "test_a"]) and bool(s.loc["PX", "test_b"])
    assert not bool(s.loc["PN", "test_a"])
    assert s.loc["PX", "test_d"] == "NOT_AVAILABLE_NO_WP_MODEL"


def test_small_cells_are_not_estimable_and_validation_uses_train_edges():
    df, w = _frame(1.0, n=3000)
    t = run_validity_tests(df, w)
    assert (t["status"] == "NOT_ESTIMABLE").any()
    df, w = _frame(1.0)
    t = run_validity_tests(df, w)
    v = t[
        (t["period"] == "VALIDATION") & (t["stratum"] == "pooled") & (t["candidate"] == "PX")
    ].iloc[0]
    assert v["n_bins"] == 10


def test_reference_candidate_is_never_primary_and_basis_is_stated():
    df, w = _frame(1.0)
    s = summarise_candidates(run_validity_tests(df, w), reference=("PX",))
    assert not s.loc[s["candidate"] == "PX", "primary"].iloc[0]
    assert s["primary_basis"].isin(["", "PASSING", "BEST_AVAILABLE_NOT_PASSING"]).all()
    assert s["primary"].sum() == 1
