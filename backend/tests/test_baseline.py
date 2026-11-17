"""Stage 4 baseline tests: shrinkage helpers, hierarchical expectation, leave-out arithmetic,
calibration identity, NULL handling, phase context and seeded bootstrap. EXPLORATORY code."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analytics import baseline_engine as be
from app.analytics.shrinkage import (
    beta_binomial_shrink,
    k_from_children,
    pooled_other_mean,
    shrink_to_parent,
)


# ---------------------------------------------------------------- shrinkage helpers
def test_shrink_to_parent_limits_and_monotone():
    assert shrink_to_parent(0.0, 5.0, 1.0, 10.0) == pytest.approx(1.0)
    assert shrink_to_parent(1e9, 5.0, 1.0, 10.0) == pytest.approx(5.0, rel=1e-6)
    vals = shrink_to_parent(np.array([0, 1, 10, 100, 1000.0]), 5.0, 1.0, 10.0)
    assert np.all(np.diff(vals) > 0) and vals[0] == pytest.approx(1.0) and vals[-1] < 5.0


def test_shrink_to_parent_null_cell_mean_takes_parent():
    assert shrink_to_parent(0.0, np.nan, 2.5, 3.0) == pytest.approx(2.5)


def test_k_from_children_zero_between_variance_hits_floor():
    # identical child means -> between moment <= 0 -> tau2 = floor * sigma2 -> k = 1/floor
    n = np.array([50, 60, 70.0])
    ss = np.array([40.0, 48.0, 56.0])  # within variance 0.8 per obs
    out = k_from_children(n, n, np.array([1.0, 1.0, 1.0]), ss, tau2_floor=0.01)
    assert out["shrinkage_floor_hit"] is True
    assert out["k"] == pytest.approx(100.0)
    assert np.isfinite(shrink_to_parent(n, 1.0, 0.0, out["k"])).all()


def test_k_from_children_negative_moment_behaves_like_floor():
    n = np.array([5, 5.0])
    ss = np.array([400.0, 400.0])  # huge within variance, tiny mean spread -> negative moment
    out = k_from_children(n, n, np.array([1.0, 1.01]), ss, tau2_floor=0.05)
    assert out["between_moment"] < 0
    assert out["shrinkage_floor_hit"] is True and out["k"] == pytest.approx(20.0)


def test_k_from_children_real_spread_does_not_hit_floor():
    n = np.array([1000, 1000, 1000.0])
    ss = np.array([1000.0, 1000.0, 1000.0])  # sigma2 ~ 1
    out = k_from_children(n, n, np.array([0.0, 1.0, 2.0]), ss, tau2_floor=0.01)
    assert out["shrinkage_floor_hit"] is False and out["k"] < 100


def test_beta_binomial_bounds_and_design_effect():
    p = beta_binomial_shrink(np.array([0, 10.0]), np.array([10, 10.0]), np.array([10, 10.0]),
                             0.5, 10.0)  # fmt: skip
    assert np.all((p >= 0) & (p <= 1))
    assert p[0] == pytest.approx(0.25) and p[1] == pytest.approx(0.75)
    # halving n_eff with the same rate pulls harder toward the parent
    q = beta_binomial_shrink(np.array([10.0]), np.array([10.0]), np.array([5.0]), 0.5, 10.0)
    assert q[0] < p[1]


def test_pooled_other_mean_excludes_own_and_nulls_when_alone():
    out = pooled_other_mean(10.0, 20.0, np.array([2.0, 10.0]), np.array([4.0, 20.0]))
    assert out[0] == pytest.approx(8.0 / 16.0)
    assert np.isnan(out[1])


def test_player_shrink_target_is_pooled_other_residual():
    # all residuals +0.2: a one-ball player shrinks toward +0.2, not toward 0
    rng = np.random.default_rng(1)
    n = np.r_[np.full(40, 200.0), 1.0]
    s = n * 0.2 + rng.normal(0, 0.5, n.size) * np.sqrt(n)
    s[-1] = 0.2
    s2 = s**2 / n + n * 1.0
    pooled = be.shrink_players(n, s, s2)
    zero = be.shrink_players(n, s, s2, target="zero")
    assert pooled["shrunk"][-1] == pytest.approx(0.2, abs=0.05)
    assert abs(zero["shrunk"][-1]) < abs(pooled["shrunk"][-1])
    assert np.isnan(be.shrink_players(np.array([0.0, 5.0]), np.array([0.0, 1.0]),
                                      np.array([0.0, 1.0]))["shrunk"][0])  # fmt: skip


# ---------------------------------------------------------------- expected values
def _synthetic(n_innings=40, balls=12, seed=0):
    """Two formats x two phases; death runs 2.0, middle runs 1.0 on average; 4 players."""
    rng = np.random.default_rng(seed)
    rows = []
    for comp in ("IPL", "T20I"):
        for i in range(n_innings):
            m = (1000 if comp == "IPL" else 2000) + i
            for b in range(balls):
                ph = "death" if b >= balls // 2 else "middle"
                mu = 2.0 if ph == "death" else 1.0
                rows.append({"competition_type": comp, "role_ctx": "chase", "innings_phase": ph,
                             "wbin": "10-8", "match_id": m, "inn_key": m * 10 + 2,
                             "player_id": int(rng.integers(1, 5)),
                             "runs": float(rng.poisson(mu))})  # fmt: skip
    return pd.DataFrame(rows)


def test_calibration_identity_on_raw_cell_means():
    d = _synthetic()
    r = be.build_stream(d, "runs", False, {"min_cell_innings": 5, "tau2_floor": 0.01})
    cal = be.calibration(r["y"], r["pooled"]["raw_cell_mean"], r["levels"][0])
    assert cal["max_abs_cell_residual"] < 1e-9


def test_death_rows_use_death_cell_expectation():
    d = _synthetic()
    r = be.build_stream(d, "runs", False, {"min_cell_innings": 5, "tau2_floor": 0.01})
    e = r["leave_player_out"]["expected"]
    death = (d["innings_phase"] == "death").to_numpy()
    assert e[death].mean() > 1.6 and e[~death].mean() < 1.4
    assert set(r["leave_player_out"]["level_used"]) == {0}


def test_leave_player_out_arithmetic_single_level():
    y = np.array([1.0, 2.0, 3.0, 6.0])
    cell = [np.zeros(4, dtype=int)]
    inn = np.array([0, 1, 2, 3])
    pl = np.array([0, 0, 1, 2])
    out = be.expected_values(y, cell, inn, pl, False, min_cell_innings=1)
    assert out["expected"] == pytest.approx([4.5, 4.5, 3.0, 2.0])
    pooled = be.expected_values(y, cell, inn, None, False, min_cell_innings=1)
    assert pooled["expected"] == pytest.approx([3.0] * 4)


def test_empty_child_after_leave_out_takes_parent_value():
    # player 0 is alone in child cell 0; leaving him out empties it -> parent (other cells) value
    y = np.array([10.0, 1.0, 1.0, 3.0, 3.0])
    child = np.array([0, 1, 1, 2, 2])
    parent = np.zeros(5, dtype=int)
    inn = np.arange(5)
    pl = np.array([0, 1, 2, 3, 4])
    out = be.expected_values(y, [child, parent], inn, pl, False, min_cell_innings=1)
    assert out["expected"][0] == pytest.approx((1 + 1 + 3 + 3) / 4)
    assert np.isfinite(out["expected"]).all()


def test_sparse_cell_falls_back_to_parent_level():
    d = _synthetic(n_innings=40)
    d.loc[d.index[:3], "wbin"] = "7-1"  # a tiny L0 cell (one innings)
    r = be.build_stream(d, "runs", False, {"min_cell_innings": 5, "tau2_floor": 0.01})
    lvl = r["leave_player_out"]["level_used"]
    assert set(lvl[:3]) == {1} and set(lvl[3:]) == {0}


def test_binary_stream_expectations_are_probabilities():
    d = _synthetic()
    d["dot"] = (d["runs"] == 0).astype(float)
    r = be.build_stream(d, "dot", True, {"min_cell_innings": 5, "tau2_floor": 0.01})
    for tag in ("pooled", "leave_player_out", "leave_match_out"):
        e = r[tag]["expected"]
        assert np.all((e >= 0) & (e <= 1))


def test_pressure_membership_level_is_finest():
    d = _synthetic()
    flag = np.zeros(len(d), dtype=bool)
    flag[::2] = True
    r = be.build_stream(
        d, "runs", False, {"min_cell_innings": 5, "tau2_floor": 0.01}, pressure=flag
    )
    assert r["n_levels"] == 5
    assert (
        be.calibration(r["y"], r["pooled"]["raw_cell_mean"], r["levels"][0])[
            "max_abs_cell_residual"
        ]
        < 1e-9
    )


def test_build_is_deterministic():
    d = _synthetic()
    p = {"min_cell_innings": 5, "tau2_floor": 0.01}
    a = be.build_stream(d, "runs", False, p)["leave_player_out"]["expected"]
    b = be.build_stream(d, "runs", False, p)["leave_player_out"]["expected"]
    assert np.array_equal(a, b)


# ---------------------------------------------------------------- bootstrap
def _player_match_stats():
    d = _synthetic()
    r = be.build_stream(d, "runs", False, {"min_cell_innings": 5, "tau2_floor": 0.01})
    resid = r["y"] - r["leave_player_out"]["expected"]
    return be.player_match_stats(d, resid, np.ones(len(d), dtype=bool))


def test_bootstrap_seeded_reproducible_and_seed_sensitive():
    ps = _player_match_stats()
    a = be.bootstrap_by_match(ps, 50, 20260512)
    b = be.bootstrap_by_match(ps, 50, 20260512)
    c = be.bootstrap_by_match(ps, 50, 7)
    assert np.array_equal(a["draws"], b["draws"], equal_nan=True)
    assert not np.array_equal(a["draws"], c["draws"], equal_nan=True)
    assert np.all(a["lo"] <= a["hi"])


def test_bootstrap_resamples_matches_not_deliveries():
    # a player observed in exactly one match is either fully present or absent in a resample
    ps = pd.DataFrame({"comp": ["IPL"] * 4, "player_id": [1, 2, 2, 3], "match_id": [10, 11, 12, 13],
                       "n": [5, 3, 4, 6], "s": [1.0, 0.5, 0.2, -1.0], "s2": [2.0, 1, 1, 3]})  # fmt: skip
    out = be.bootstrap_by_match(ps, 200, 1)
    i = list(out["players"]).index("IPL|1")
    present = out["present_share"][i]
    assert 0 < present < 1  # absent in some resamples (match 10 not drawn)
    assert out["n"][i] == 5 and out["matches"][i] == 1


def test_player_match_stats_counts_rows_by_player_and_match():
    d = pd.DataFrame({"competition_type": ["IPL"] * 5, "player_id": [1, 1, 1, 2, 2],
                      "match_id": [7, 7, 8, 7, 9]})  # fmt: skip
    out = be.player_match_stats(d, np.array([1.0, -1, 2, 0, 3]), np.array([1, 1, 1, 1, 0], bool))
    got = {(r.player_id, r.match_id): (r.n, r.s) for r in out.itertuples()}
    assert got == {(1, 7): (2, 0.0), (1, 8): (1, 2.0), (2, 7): (1, 0.0)}
