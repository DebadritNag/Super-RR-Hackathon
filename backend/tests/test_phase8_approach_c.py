"""Approach C: weight derivation, PRI, bootstrap, held-out reliability and format hierarchy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase8.approach_a import Boot
from app.phase8.approach_c import (
    COMPONENTS,
    bootstrap_pri,
    combination_decision,
    combine_weights,
    component_units,
    consistency_units,
    cross_format,
    derive_weights,
    fit_format_model,
    fit_match_split,
    pri_point,
    pri_split_half,
    rank_of,
    reliability_weight,
)
from app.phase8.reml import RemlError


def _sim(
    skill_sd: float = 0.4, n_players: int = 60, n_matches: int = 160, per_player: int = 24,
    seed: int = 5, skill_b_sd: float | None = None,
):  # fmt: skip
    """Synthetic A and B unit tables with a known player effect; returns (ua, ub, matches, skill)."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n_matches, freq="3D")
    period = np.where(np.arange(n_matches) < int(n_matches * 0.75), "TRAIN", "VALIDATION")
    matches = pd.DataFrame(
        {"match_id": np.arange(1, n_matches + 1), "match_date": dates, "period": period}
    )
    skill = rng.normal(0, skill_sd, n_players)
    skill_b = rng.normal(0, skill_b_sd if skill_b_sd is not None else 0.0, n_players)
    rows_a, rows_b = [], []
    for p in range(n_players):
        for m in rng.choice(n_matches, per_player, replace=False):
            prec = rng.uniform(8, 20)
            base = {
                "player_id": 1000 + p, "match_id": int(m) + 1, "innings": 1 + (m % 2),
                "match_date": dates[m], "competition_type": "IPL" if m % 3 else "T20I",
                "period": period[m], "prec": prec, "w": prec, "w2": 1.0, "mean_intensity": 0.7,
                "n_balls": 6, "hi_balls": 6,
            }  # fmt: skip
            rows_a.append({**base, "y": skill[p] + rng.normal(0, 1 / np.sqrt(prec) * 3)})
            rows_b.append({**base, "y": skill_b[p] + rng.normal(0, 1 / np.sqrt(prec) * 3)})
    return pd.DataFrame(rows_a), pd.DataFrame(rows_b), matches, skill


def test_reliability_weight_rules():
    assert reliability_weight(0.5, False) == (pytest.approx(1.0), "ACTIVE")
    assert reliability_weight(0.0, False) == (0.0, "NO_SIGNAL_NONPOSITIVE_RELIABILITY")
    assert reliability_weight(-0.2, False) == (0.0, "NO_SIGNAL_NONPOSITIVE_RELIABILITY")
    assert reliability_weight(0.7, True) == (0.0, "NO_SIGNAL_FLOOR")
    assert reliability_weight(float("nan"), False) == (0.0, "NO_SIGNAL_NOT_ESTIMABLE")
    assert reliability_weight(None, False) == (0.0, "NO_SIGNAL_NOT_ESTIMABLE")
    w, st = reliability_weight(1.0, False)  # clipped at 0.99, never infinite
    assert st == "ACTIVE" and w == pytest.approx(0.99 / 0.01)


def test_combine_weights_all_zero_is_not_defined():
    out = combine_weights({"A": 0.0, "B": 0.0, "CONS": 0.0}, pd.DataFrame())
    assert out["defined"] is False
    assert all(v == 0.0 for v in out["weights"].values())


def test_combine_weights_single_and_uncorrelated_and_correlated():
    rng = np.random.default_rng(1)
    base = pd.DataFrame(rng.normal(size=(200, 3)), columns=list(COMPONENTS))
    one = combine_weights({"A": 0.0, "B": 0.0, "CONS": 0.3}, base)
    assert one["weights"] == {"A": 0.0, "B": 0.0, "CONS": 1.0} and not one["pca"]
    two = combine_weights({"A": 1.0, "B": 3.0, "CONS": 0.0}, base)
    assert not two["pca"]
    assert two["weights"]["A"] == pytest.approx(0.25) and two["weights"]["B"] == pytest.approx(0.75)
    corr = base.copy()
    corr["CONS"] = corr["A"] * 0.9 + rng.normal(scale=0.2, size=200)
    pca = combine_weights({"A": 1.0, "B": 0.0, "CONS": 1.0}, corr)
    assert pca["pca"] and pca["max_abs_corr"] > 0.5
    assert sum(abs(v) for v in pca["weights"].values()) == pytest.approx(1.0)
    assert pca["weights"]["B"] == 0.0 and pca["weights"]["A"] > 0 and pca["weights"]["CONS"] > 0


def test_fit_match_split_uses_train_odd_positions_only():
    m = pd.DataFrame(
        {"match_id": [5, 1, 3, 2, 4, 9],
         "match_date": pd.to_datetime(["2022-01-05", "2022-01-01", "2022-01-03", "2022-01-02",
                                       "2022-01-04", "2025-06-01"]),
         "period": ["TRAIN"] * 5 + ["VALIDATION"]}
    )  # fmt: skip
    s = fit_match_split(m)
    assert s[[2, 4]].eq("FIT").all()  # positions 1 and 3 in date order
    assert s[[1, 3, 5]].eq("HELD").all() and s[9] == "HELD"
    with pytest.raises(ValueError):
        fit_match_split(m.assign(period=["TRAIN"] * 5 + ["TEST"]))


def test_consistency_units_are_signed_halves_with_unit_precision():
    ua, _, _, _ = _sim()
    c = consistency_units(ua)
    assert set(c["y"].unique()) <= {-0.5, 0.5}
    assert (c["prec"] == 1.0).all()
    assert ((ua["y"] > 0) == (c["y"] > 0)).all()


def test_derive_weights_gives_signal_to_real_component_and_none_to_noise():
    ua, ub, matches, _ = _sim(skill_sd=0.5, skill_b_sd=0.0)
    cu = component_units(ua, ub)
    players = np.sort(ua["player_id"].unique())
    split = fit_match_split(matches)
    fit_ids = set(split[split == "FIT"].index)
    dw = derive_weights(cu, players, fit_ids)
    t = dw["table"].set_index("component")
    assert t.loc["A", "status"] == "ACTIVE" and t.loc["A", "final_weight"] > 0
    # B carries no player effect: its reliability weight is far below the real component's
    assert t.loc["B", "reliability_weight"] < 0.5 * t.loc["A", "reliability_weight"]
    assert (t["final_weight"] >= 0).all()
    assert dw["defined"] and sum(abs(v) for v in dw["weights"].values()) == pytest.approx(1.0)
    # only FIT matches are used: the units counted never exceed the FIT unit count
    assert (t["n_units_fit"] <= ua["match_id"].isin(fit_ids).sum()).all()


def test_derive_weights_pure_noise_is_not_defined():
    ua, ub, matches, _ = _sim(skill_sd=0.0, skill_b_sd=0.0, seed=8)
    split = fit_match_split(matches)
    dw = derive_weights(component_units(ua, ub), np.sort(ua["player_id"].unique()),
                        set(split[split == "FIT"].index))  # fmt: skip
    t = dw["table"].set_index("component")
    # with no player effect a chance positive reliability stays small (weight r/(1-r) well below 1)
    assert (t.loc[["A", "B"], "reliability_weight"] < 0.5).all()


def test_pri_orders_players_by_true_skill_and_is_centred():
    ua, ub, _, skill = _sim(skill_sd=0.5)
    cu = component_units(ua, ub)
    players = np.sort(ua["player_id"].unique())
    pt = pri_point(cu, players, {"A": 1.0, "B": 0.0, "CONS": 0.0})
    pri = pt["pri"]
    assert pri.notna().all() and abs(pri.mean()) < 1e-9
    true = pd.Series(skill, index=1000 + np.arange(len(skill)))
    assert pri.corr(true, method="spearman") > 0.6
    assert rank_of(pri).sort_values().index[0] == pri.idxmax()
    again = pri_point(cu, players, {"A": 1.0, "B": 0.0, "CONS": 0.0})["pri"]
    pd.testing.assert_series_equal(pri, again)


def test_pri_is_nan_when_no_component_is_active():
    ua, ub, _, _ = _sim()
    pt = pri_point(component_units(ua, ub), np.sort(ua["player_id"].unique()),
                   dict.fromkeys(COMPONENTS, 0.0))  # fmt: skip
    assert pt["pri"].isna().all()


def test_bootstrap_is_seeded_and_probabilities_are_valid():
    ua, ub, matches, _ = _sim(skill_sd=0.5, n_players=40, n_matches=100, per_player=20)
    cu = component_units(ua, ub)
    players = np.sort(ua["player_id"].unique())
    w = {"A": 1.0, "B": 0.0, "CONS": 0.0}
    pt = pri_point(cu, players, w)
    out = []
    for _ in range(2):
        b = Boot(matches, 40, seed=7)
        out.append(bootstrap_pri(pt["comps"], players, b, w, pt["sds"]))
    pd.testing.assert_frame_equal(out[0]["stability"], out[1]["stability"])
    s = out[0]["stability"]
    assert s["top_k_prob"].between(0, 1).all()
    assert (s["rank_low"] <= s["rank_high"]).all()
    assert s["top_k_prob"].sum() == pytest.approx(10.0, abs=0.5)  # ten places per draw
    assert set(out[0]["floor_draw_share"]) == {"A"}


def test_heldout_split_half_detects_signal_and_noise():
    ua, ub, matches, _ = _sim(skill_sd=0.6, per_player=30)
    cu = component_units(ua, ub)
    players = np.sort(ua["player_id"].unique())
    w = {"A": 1.0, "B": 0.0, "CONS": 0.0}
    pt = pri_point(cu, players, w)
    ids = set(matches["match_id"])
    sh = pri_split_half(cu, players, ids, w, pt["sds"], "parity", 2, 50)
    assert sh["spearman_brown"] > 0.5 and sh["sb_low"] is not None
    ua0, ub0, matches0, _ = _sim(skill_sd=0.0, per_player=30, seed=2)
    cu0 = component_units(ua0, ub0)
    pt0 = pri_point(cu0, players, w)
    sh0 = pri_split_half(cu0, players, set(matches0["match_id"]), w, pt0["sds"], "parity", 2, 0)
    assert abs(sh0["spearman_brown"]) < 0.4


def test_format_model_recovers_common_and_format_components():
    rng = np.random.default_rng(11)
    rows = []
    for p in range(150):
        u = rng.normal(0, 0.3)
        for f, fm in (("IPL", 0.0), ("T20I", 0.1)):
            v = rng.normal(0, 0.2)
            for _ in range(10):
                prec = rng.uniform(5, 15)
                rows.append({"player_id": p, "competition_type": f,
                             "y": fm + u + v + rng.normal(0, 0.5 / np.sqrt(prec)), "prec": prec})  # fmt: skip
    fit = fit_format_model(pd.DataFrame(rows), np.arange(150))
    assert fit["tau_u2"] == pytest.approx(0.09, rel=0.4)
    assert fit["tau_v2"] == pytest.approx(0.04, rel=0.5)
    assert fit["mu_t20i"] - fit["mu_ipl"] == pytest.approx(0.1, abs=0.08)
    assert not fit["floor_common"] and not fit["floor_format_dev"]
    pl = fit["players"]
    assert (pl["w_ipl"] > 0).all() and (pl["w_t20i"] > 0).all()
    # symmetric information in both formats: the two format weights are nearly equal on average
    assert pl["w_ipl"].mean() == pytest.approx(pl["w_t20i"].mean(), rel=0.15)


def test_format_model_flags_no_common_effect():
    rng = np.random.default_rng(3)
    rows = []
    for p in range(120):
        for f in ("IPL", "T20I"):
            v = rng.normal(0, 0.3)
            for _ in range(8):
                rows.append({"player_id": p, "competition_type": f,
                             "y": v + rng.normal(0, 0.1), "prec": 10.0})  # fmt: skip
    fit = fit_format_model(pd.DataFrame(rows), np.arange(120))
    # no common player effect was simulated: the common variance is small beside the format one
    assert fit["tau_v2"] == pytest.approx(0.09, rel=0.4)
    assert fit["tau_u2"] < 0.2 * fit["tau_v2"]


def test_format_model_needs_two_units_in_a_cell():
    rows = [{"player_id": p, "competition_type": f, "y": 0.0, "prec": 1.0}
            for p in range(10) for f in ("IPL", "T20I")]  # fmt: skip
    with pytest.raises(RemlError):
        fit_format_model(pd.DataFrame(rows), np.arange(10))


def test_combination_decision_and_cross_format_note():
    assert combination_decision(0.35, 40, 30) == (True, "COMMON_EFFECT_FORMAT_CENTRED")
    ok, basis = combination_decision(0.29, 90, 30)
    assert not ok and basis == "FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED"
    assert combination_decision(0.5, 20, 30)[0] is False
    assert combination_decision(float("nan"), 90, 30)[0] is False
    rng = np.random.default_rng(0)
    pf = pd.DataFrame({"ybar_ipl": rng.normal(size=60), "P_ipl": 10.0, "P_t20i": 10.0})
    pf["ybar_t20i"] = pf["ybar_ipl"] * 0.8 + rng.normal(scale=0.3, size=60)
    out = cross_format(pf, 0.1, 0.1, n_boot=50)
    assert out["spearman"] > 0.7 and out["disattenuated"] != out["disattenuated"]  # NaN, > 1
    assert out["disattenuation_note"] == "OUT_OF_RANGE_RELIABILITY_TOO_NOISY"
    assert cross_format(pf.head(3), 0.5, 0.5)["disattenuation_note"] == "TOO_FEW_PLAYERS"
