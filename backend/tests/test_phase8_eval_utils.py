"""Calibration, reliability and stability utilities on synthetic data with known answers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase8 import calibration as cal
from app.phase8 import reliability as rel
from app.phase8 import stability as stab
from app.phase8 import units as un


# ----------------------------------------------------------------------------- calibration
def _sim(n=40000, seed=1, slope=1.0, shift=0.0):
    rng = np.random.default_rng(seed)
    p_true = rng.uniform(0.02, 0.98, n)
    y = (rng.uniform(size=n) < p_true).astype(float)
    logit = np.log(p_true / (1 - p_true))
    p_pred = 1 / (1 + np.exp(-(shift + slope * logit)))
    return y, p_pred


def test_perfectly_calibrated_model_has_slope_one_and_intercept_zero():
    y, p = _sim()
    r = cal.calibration_slope_intercept(y, p)
    assert r["slope"] == pytest.approx(1.0, abs=0.06)
    assert r["intercept"] == pytest.approx(0.0, abs=0.06)
    t = cal.decile_table(y, p)
    assert (t["mean_pred"] - t["mean_obs"]).abs().max() < 0.03


def test_overconfident_model_has_slope_below_one_and_worse_brier():
    y, p_good = _sim()
    _, p_over = _sim(slope=2.0)
    assert cal.calibration_slope_intercept(y, p_over)["slope"] == pytest.approx(0.5, abs=0.05)
    assert cal.brier(y, p_over) > cal.brier(y, p_good)
    assert cal.log_loss(y, p_over) > cal.log_loss(y, p_good)


def test_biased_model_shows_a_negative_intercept():
    y, p = _sim(shift=1.0)
    assert cal.calibration_slope_intercept(y, p)["intercept"] == pytest.approx(-1.0, abs=0.08)


def test_brier_and_log_loss_known_values():
    y = np.array([1.0, 0.0, 1.0, 0.0])
    p = np.array([0.8, 0.2, 0.6, 0.4])
    assert cal.brier(y, p) == pytest.approx((0.04 + 0.04 + 0.16 + 0.16) / 4)
    assert cal.log_loss(y, p) == pytest.approx(-(2 * np.log(0.8) + 2 * np.log(0.6)) / 4)
    assert cal.brier(y, y) == 0.0


def test_report_gain_over_constant_baseline():
    y, p = _sim()
    rep = cal.calibration_report(y, p)
    assert rep["brier_gain"] > 0.05 and rep["n"] == len(y)
    const = np.full_like(p, y.mean())
    assert cal.calibration_report(y, const)["brier_gain"] == pytest.approx(0.0, abs=1e-9)
    assert len(rep["deciles"]) == 10


def test_calibration_input_validation():
    with pytest.raises(ValueError):
        cal.brier(np.array([0.0, 2.0]), np.array([0.5, 0.5]))
    with pytest.raises(ValueError):
        cal.brier(np.array([0.0, 1.0]), np.array([0.5, 1.5]))
    with pytest.raises(ValueError):
        cal.brier(np.array([0.0, 1.0]), np.array([0.5]))
    with pytest.raises(ValueError):
        cal.brier(np.array([np.nan]), np.array([np.nan]))


# ----------------------------------------------------------------------------- reliability
def _units(n_players=120, n_matches=12, signal_sd=1.0, noise_sd=1.0, seed=3):
    rng = np.random.default_rng(seed)
    skill = rng.normal(0, signal_sd, n_players)
    rows = []
    mid = 0
    for p in range(n_players):
        for m in range(n_matches):
            mid += 1
            rows.append(
                (p + 1, mid, pd.Timestamp("2023-01-01") + pd.Timedelta(days=m * 7),
                 skill[p] + rng.normal(0, noise_sd), 1.0)
            )  # fmt: skip
    return pd.DataFrame(rows, columns=rel.UNIT_COLS)


def test_spearman_brown_values():
    assert rel.spearman_brown(0.5) == pytest.approx(2 * 0.5 / 1.5)
    assert rel.spearman_brown(0.0) == 0.0
    assert rel.spearman_brown(-0.2) < 0
    assert np.isnan(rel.spearman_brown(-1.0))
    assert rel.spearman_brown(np.array([0.2, 0.6])).shape == (2,)


def test_split_half_recovers_known_reliability():
    # half-test mean variance: signal 1, noise 1/6  -> r = 1/(1+1/6) = 0.857
    u = _units()
    r = rel.split_half(u, "parity")
    assert r["r"] == pytest.approx(1 / (1 + 1 / 6), abs=0.06)
    assert r["spearman_brown"] == pytest.approx(2 * r["r"] / (1 + r["r"]))
    assert r["n_players"] == 120


def test_split_half_is_about_zero_without_signal():
    u = _units(signal_sd=0.0)
    r = rel.split_half(u, "parity")
    assert abs(r["r"]) < 0.2


def test_time_split_matches_parity_when_skill_is_stable():
    u = _units()
    assert rel.split_half(u, "time")["r"] == pytest.approx(
        rel.split_half(u, "parity")["r"], abs=0.1
    )


def test_split_half_bootstrap_interval_is_seeded_and_brackets_estimate():
    u = _units(n_players=60, n_matches=8)
    a = rel.split_half(u, "parity", n_boot=60, seed=5)
    b = rel.split_half(u, "parity", n_boot=60, seed=5)
    assert a == b
    assert a["sb_low"] <= a["spearman_brown"] <= a["sb_high"]
    c = rel.split_half(u, "parity", n_boot=60, seed=6)
    assert (c["sb_low"], c["sb_high"]) != (a["sb_low"], a["sb_high"])


def test_halves_alternate_in_date_order_and_split_in_time():
    u = pd.DataFrame(
        {
            "player_id": [1] * 4,
            "match_id": [4, 3, 2, 1],
            "match_date": pd.to_datetime(["2023-04-01", "2023-03-01", "2023-02-01", "2023-01-01"]),
            "y": [0.0] * 4,
            "w": [1.0] * 4,
        }
    )
    par = rel.assign_halves(u, "parity")
    assert dict(zip(u["match_id"], par, strict=True)) == {1: 0, 2: 1, 3: 0, 4: 1}
    tm = rel.assign_halves(u, "time")
    assert dict(zip(u["match_id"], tm, strict=True)) == {1: 0, 2: 0, 3: 1, 4: 1}
    with pytest.raises(ValueError):
        rel.assign_halves(u, "random")


def test_icc_recovers_known_value_and_handles_no_signal():
    u = _units(n_matches=30, signal_sd=1.0, noise_sd=1.0)
    assert rel.icc1(u)["icc"] == pytest.approx(0.5, abs=0.07)
    z = _units(signal_sd=0.0)
    assert abs(rel.icc1(z)["icc"]) < 0.06
    assert np.isnan(rel.icc1(u.head(2))["icc"])


def test_unit_table_validation():
    with pytest.raises(ValueError):
        rel.split_half(pd.DataFrame({"player_id": [1]}))
    bad = _units(n_players=3, n_matches=2)
    bad.loc[0, "w"] = 0.0
    with pytest.raises(ValueError):
        rel.split_half(bad)


def test_precision_weighted_means_and_effective_n():
    u = pd.DataFrame(
        {
            "player_id": [1, 1, 2],
            "match_id": [1, 2, 3],
            "match_date": pd.to_datetime(["2023-01-01"] * 3),
            "y": [1.0, 3.0, 2.0],
            "w": [1.0, 3.0, 2.0],
        }
    )
    e = rel.precision_weighted_means(u).set_index("player_id")
    assert e.loc[1, "ybar"] == pytest.approx((1 + 9) / 4)
    assert e.loc[1, "w_eff"] == pytest.approx(16 / 10)
    assert e.loc[2, "n_matches"] == 1


def test_out_of_time_needs_enough_players():
    a = pd.DataFrame({"player_id": range(40), "ybar": np.arange(40.0)})
    b = pd.DataFrame({"player_id": range(40), "ybar": np.arange(40.0)[::-1]})
    assert rel.out_of_time_correlation(a, a)["spearman"] == pytest.approx(1.0)
    assert rel.out_of_time_correlation(a, b)["spearman"] == pytest.approx(-1.0)
    small = rel.out_of_time_correlation(a.head(10), a.head(10))
    assert small["status"] == "NOT_ESTIMABLE" and small["spearman"] is None


# ----------------------------------------------------------------------------- stability
def test_match_count_draws_are_seeded_and_sum_to_n():
    ids = np.arange(50)
    a = stab.match_count_draws(ids, 20, seed=9)
    b = stab.match_count_draws(ids, 20, seed=9)
    assert (a == b).all() and (a.sum(axis=1) == 50).all()
    assert not (a == stab.match_count_draws(ids, 20, seed=10)).all()
    with pytest.raises(ValueError):
        stab.match_count_draws(np.array([1, 1]), 5)


def test_stratified_draws_keep_stratum_sizes():
    ids = np.arange(30)
    strata = np.array(["TRAIN"] * 20 + ["VALIDATION"] * 10)
    c = stab.match_count_draws(ids, 40, seed=2, strata=strata)
    assert (c[:, :20].sum(axis=1) == 20).all() and (c[:, 20:].sum(axis=1) == 10).all()


def test_bootstrap_means_centre_on_the_full_estimate():
    u = _units(n_players=20, n_matches=10)
    draws, players = stab.bootstrap_weighted_means(u, n_draws=300, seed=4)
    full = rel.precision_weighted_means(u).set_index("player_id")["ybar"].reindex(players)
    assert np.nanmean(draws, axis=0) == pytest.approx(full.to_numpy(), abs=0.35)
    again, _ = stab.bootstrap_weighted_means(u, n_draws=300, seed=4)
    assert np.array_equal(draws, again, equal_nan=True)


def test_rank_stability_clear_top_players_have_probability_near_one():
    rng = np.random.default_rng(0)
    means = np.r_[np.full(10, 5.0), np.zeros(40)]
    draws = means + rng.normal(0, 0.2, (400, 50))
    s = stab.rank_stability(draws, pd.Index(range(1, 51)))
    assert (s.loc[:9, "top_k_prob"] > 0.99).all()
    assert (s.loc[10:, "top_k_prob"] < 0.01).all()
    assert (s["rank_low"] <= s["rank_median"]).all() and (s["rank_median"] <= s["rank_high"]).all()


def test_rank_stability_equal_players_split_probability_and_tie_by_id():
    draws = np.zeros((50, 20))
    s = stab.rank_stability(draws, pd.Index(range(1, 21)))
    assert list(s.loc[s["top_k_prob"] == 1.0, "player_id"]) == list(range(1, 11))  # id ascending
    # genuinely noisy equal players share the Top 10 about equally
    rng = np.random.default_rng(1)
    noisy = rng.normal(0, 1, (2000, 20))
    p = stab.rank_stability(noisy, pd.Index(range(1, 21)))["top_k_prob"]
    assert p.mean() == pytest.approx(0.5, abs=0.01) and p.std() < 0.06


def test_rank_stability_nan_estimates_are_not_ranked():
    draws = np.array([[1.0, np.nan, 3.0], [2.0, 5.0, np.nan]])
    s = stab.rank_stability(draws, pd.Index([1, 2, 3]), top_k=1).set_index("player_id")
    assert s.loc[3, "top_k_prob"] == 0.5 and s.loc[2, "top_k_prob"] == 0.5
    assert s.loc[2, "draws_present"] == 1


def test_point_ranking_ties_break_by_player_id_only():
    est = pd.Series([1.0, 1.0, 2.0, np.nan], index=[7, 3, 9, 4])
    r = stab.point_ranking(est)
    assert r[9] == 1 and r[3] == 2 and r[7] == 3 and np.isnan(r[4])
    near = pd.Series([1.0, 1.0 + 1e-9], index=[1, 2])
    assert stab.point_ranking(near)[2] == 1  # not an exact tie: ordering by value


def test_top_k_overlap():
    a = pd.Series(range(1, 21), index=range(20))
    b = pd.Series(list(range(11, 21)) + list(range(1, 11)), index=range(20))
    o = stab.top_k_overlap(a, b, 10)
    assert o["overlap"] == 0 and stab.top_k_overlap(a, a, 10)["share"] == 1.0


def test_bootstrap_statistic_interval():
    u = _units(n_players=15, n_matches=6)
    out = stab.bootstrap_statistic(u, lambda f: float(f["y"].mean()), n_draws=60, seed=3)
    assert out["n"] == 60 and out["low"] <= u["y"].mean() + 0.5 and out["high"] >= out["low"]


# ----------------------------------------------------------------------------- units
def test_units_are_weighted_and_never_zero_filled():
    df = pd.DataFrame(
        {
            "striker_id": [1, 1, 1, 2],
            "bowler_id": [9, 9, 9, 9],
            "match_id": [10, 10, 10, 10],
            "innings_number": [1, 1, 1, 1],
            "match_date": pd.to_datetime(["2024-01-01"] * 4),
            "competition_type": ["IPL"] * 4,
            "period": ["TRAIN"] * 4,
        }
    )
    w = pd.Series([0.5, 1.0, np.nan, 0.0])
    r = pd.Series([2.0, -1.0, 5.0, 4.0])
    u = un.build_units(df, "batter", w, r).set_index("player_id")
    assert list(u.index) == [1]  # player 2 has zero weight, the NaN-intensity ball is skipped
    assert u.loc[1, "w"] == 1.5 and u.loc[1, "y"] == pytest.approx((1.0 - 1.0) / 1.5)
    assert u.loc[1, "n_balls"] == 2 and u.loc[1, "hi_balls"] == 2
    assert un.build_units(df, "bowler", w, r)["player_id"].tolist() == [9]
    with pytest.raises(ValueError):
        un.build_units(df, "fielder", w, r)
    eff = un.effective_n(un.build_units(df, "batter", w, r).assign(player_id=1))
    assert eff.iloc[0] > 0
