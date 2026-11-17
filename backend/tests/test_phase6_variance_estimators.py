"""Variance estimators on synthetic data with known between-player variance."""

from __future__ import annotations

import numpy as np
import pytest

from app.phase4 import engine as en
from app.phase5 import reliability as rb
from app.phase6 import estimators as es
from app.phase6 import variance_floor as vf

SEED = 20260512


def _normal_normal(tau2: float, n: int = 300, seed: int = SEED):
    rng = np.random.default_rng(seed)
    v0 = rng.uniform(0.02, 0.10, n)
    y = rng.normal(0.0, np.sqrt(tau2), n) + rng.normal(0.0, np.sqrt(v0))
    return y, v0


def test_reml_and_ml_recover_known_tau2():
    y, v0 = _normal_normal(0.04)
    for fn in (es.tau2_reml, es.tau2_ml):
        r = fn(y, v0)
        assert r["converged"]
        assert r["value"] == pytest.approx(0.04, rel=0.25)
        assert r["status"] == rb.ESTIMATED


def test_ml_is_not_above_reml_by_construction_of_the_correction():
    y, v0 = _normal_normal(0.04, n=40, seed=3)
    assert es.tau2_ml(y, v0)["value"] <= es.tau2_reml(y, v0)["value"] + 1e-9


def test_zero_between_variance_gives_estimate_near_zero_not_large_positive():
    y, v0 = _normal_normal(0.0)
    for fn in (es.tau2_reml, es.tau2_ml):
        r = fn(y, v0)
        assert r["converged"]
        assert r["value"] < 0.01  # noise variance is 0.02 to 0.10
    assert es.tau2_reml(y, v0)["value"] < 0.2 * float(v0.mean())


def test_moments_floor_recovers_positive_and_applies_floor_when_negative():
    y, v0 = _normal_normal(0.04)
    r = es.tau2_moments_floor(y, v0, sigma2=1.0)
    assert r["status"] == rb.ESTIMATED
    assert r["value"] == pytest.approx(0.04, rel=0.3)
    assert not r["floor_hit"]
    # noise much larger than the spread of the means: the moment is negative, the floor applies
    rng = np.random.default_rng(1)
    y2 = rng.normal(0.0, 0.1, 200)
    r2 = es.tau2_moments_floor(y2, np.full(200, 1.0), sigma2=2.0)
    assert r2["between"] < 0
    assert r2["status"] == rb.BETWEEN_NOT_POSITIVE
    assert r2["floor_hit"] is True
    assert r2["value"] == pytest.approx(0.01 * 2.0)


def test_moments_not_estimable_without_variance_or_players():
    assert es.tau2_moments_floor(np.array([1.0, 2.0]), np.array([1.0, 1.0]), 1.0)["status"] == (
        rb.NOT_ESTIMABLE
    )
    assert es.tau2_moments_floor(np.arange(10.0), np.ones(10), float("nan"))["status"] == (
        rb.NOT_ESTIMABLE
    )


def test_beta_binomial_recovers_known_variance_and_flags_no_overdispersion():
    rng = np.random.default_rng(SEED)
    a, b = 2.0, 18.0
    p = rng.beta(a, b, 500)
    n = rng.integers(50, 200, 500).astype(float)
    x = rng.binomial(n.astype(int), p).astype(float)
    r = es.tau2_beta_binomial(x, n)
    true = a * b / ((a + b) ** 2 * (a + b + 1))
    assert r["value"] == pytest.approx(true, rel=0.25)
    assert r["status"] == rb.ESTIMATED
    x0 = rng.binomial(n.astype(int), 0.1).astype(float)
    r0 = es.tau2_beta_binomial(x0, n)
    assert r0["value"] < 0.2 * true


def test_gamma_poisson_recovers_known_rate_variance():
    rng = np.random.default_rng(SEED)
    shape, scale = 4.0, 0.05
    lam = rng.gamma(shape, scale, 500)
    e = rng.integers(20, 100, 500).astype(float)
    c = rng.poisson(lam * e).astype(float)
    r = es.tau2_gamma_poisson(c, e)
    assert r["value"] == pytest.approx(shape * scale**2, rel=0.25)
    c0 = rng.poisson(0.2 * e).astype(float)
    assert es.tau2_gamma_poisson(c0, e)["value"] < 0.3 * shape * scale**2


def test_small_samples_are_not_estimable():
    assert es.tau2_beta_binomial(np.ones(3), np.full(3, 10.0))["status"] == rb.NOT_ESTIMABLE
    assert es.tau2_gamma_poisson(np.ones(3), np.ones(3))["status"] == rb.NOT_ESTIMABLE


def _cell(tau2: float, seed: int = SEED, P: int = 120, M: int = 30) -> rb.CellData:
    rng = np.random.default_rng(seed)
    u = rng.normal(0, np.sqrt(tau2), P)
    N = rng.integers(2, 9, (P, M)).astype(float)
    mask = np.arange(8)[None, None, :] < N[:, :, None]
    r = (u[:, None, None] + rng.normal(0, 1, (P, M, 8))) * mask
    S, S2 = r.sum(2), (r**2).sum(2)
    dates = np.array([f"2024-{1 + j // 28:02d}-{1 + j % 28:02d}" for j in range(M)])
    return rb.CellData(np.arange(P), np.arange(M), dates, np.array(["TRAIN"] * M), N, S, S2)


def test_cluster_bootstrap_is_seed_deterministic_and_seed_sensitive():
    cd = _cell(0.05)
    gm, W1 = en.global_weights(np.arange(30), 200, 7)
    _, W1b = en.global_weights(np.arange(30), 200, 7)
    _, W2 = en.global_weights(np.arange(30), 200, 8)
    a = es.cluster_bootstrap(cd, W1.T)
    b = es.cluster_bootstrap(cd, W1b.T)
    c = es.cluster_bootstrap(cd, W2.T)
    assert a["match_cluster"] == b["match_cluster"]
    assert a["match_cluster"]["lo"] != c["match_cluster"]["lo"]
    assert a["match_cluster"]["lo"] <= a["match_cluster"]["value"] <= a["match_cluster"]["hi"]


def test_icc_oneway_recovers_known_intraclass_correlation():
    rng = np.random.default_rng(SEED)
    g, m = 500, 10
    eff = rng.normal(0, 1, g)
    x = eff[:, None] + rng.normal(0, 1, (g, m))  # ICC = 0.5
    icc = es.icc_oneway(np.full(g, m), x.sum(1), (x**2).sum(1))
    assert icc == pytest.approx(0.5, abs=0.05)
    y = rng.normal(0, 1, (g, m))
    assert abs(es.icc_oneway(np.full(g, m), y.sum(1), (y**2).sum(1))) < 0.05


def test_tercile_variance_ratio_detects_heteroscedasticity():
    rng = np.random.default_rng(SEED)
    n = rng.integers(5, 200, 300).astype(float)
    var = np.where(n < 70, 4.0, 1.0)
    ssw = var * (n - 1)
    ratio = es.tercile_variance_ratio(n, ssw * (1 + rng.normal(0, 0.01, 300)))
    assert ratio > 2.5
    assert es.tercile_variance_ratio(n, np.ones(300) * (n - 1)) == pytest.approx(1.0)


def test_pearson_dispersion_near_one_for_correct_model():
    y, v0 = _normal_normal(0.04, n=2000)
    assert es.pearson_dispersion(y, v0, 0.04) == pytest.approx(1.0, abs=0.1)
    assert es.pearson_dispersion(y, v0 * 0.2, 0.0) > 1.5  # understated noise


def test_dispersion_diagnostics_reports_kish_arithmetic():
    cd = _cell(0.05)
    d = es.dispersion_diagnostics(cd)
    assert d["status"] == rb.ESTIMATED
    # with near-equal match sizes n_eff is close to the match count, so noise/sigma2 is ~ 1/m
    assert d["kish_noise_over_ball_noise"] > 1.0
    assert d["balls_per_player_match"] == pytest.approx(5.0, abs=0.5)


@pytest.mark.parametrize(
    "a_null,a_power,b,c,expected",
    [
        (True, True, False, False, "H-A_SUPPORTED"),
        (True, True, False, True, "H-A_SUPPORTED"),
        (True, False, False, False, "UNIDENTIFIED"),
        (True, False, True, True, "UNIDENTIFIED"),
        (False, False, True, True, "MIXED"),
        (True, True, True, True, "MIXED"),
        (False, True, True, False, "H-B_SUPPORTED"),
        (True, True, True, False, "H-B_SUPPORTED"),
        (False, False, False, True, "H-C_SUPPORTED"),
        (False, False, False, False, "UNIDENTIFIED"),
    ],
)
def test_verdict_table_every_row(a_null, a_power, b, c, expected):
    assert vf.verdict_from_flags(a_null, a_power, b, c) == expected


def test_identification_status_rules():
    ok = {"status": rb.ESTIMATED}
    assert vf.identification_status({**ok, "lo": 0.01, "hi": 0.1}, {**ok, "share_positive": 0.95},
                                    0.9) == "identified_positive"  # fmt: skip
    assert vf.identification_status({**ok, "lo": -0.01, "hi": 0.1}, {**ok, "share_positive": 0.5},
                                    0.9) == "not_identified"  # fmt: skip
    assert vf.identification_status({**ok, "lo": -0.01, "hi": 0.1}, {**ok, "share_positive": 0.95},
                                    0.9) == "weakly_identified"  # fmt: skip
    assert vf.identification_status({"status": rb.NOT_ESTIMABLE}, ok, 0.9) == rb.NOT_ESTIMABLE


def test_flags_use_declared_thresholds_only():
    from app.phase6.criteria import CRITERIA

    fl = CRITERIA["variance_floor"]["flags"]
    diag = {"kish_ratio_over_balls_per_match": 1.0, "tercile_variance_ratio": 2.0,
            "icc_match": 0.0, "icc_player_match": 0.06, "pearson_dispersion": 0.5}  # fmt: skip
    e7 = {"lo": -0.1, "hi": 0.2, "value": 0.05, "status": rb.ESTIMATED}
    e6 = {"share_positive": 0.5, "lo": -0.1}
    f = vf.compute_flags(fl, e7, e6, diag, 0.9, -1.0, 0.2, None, 20.0)
    assert f["flag_H-A_null"] and f["flag_H-A_power"]
    assert f["flag_H-B_i"] and f["flag_H-B_ii"] and f["flag_H-B_iii"] and f["flag_H-B_iv"]
    assert f["flag_H-B_overall"] and not f["flag_H-C"]
    assert f["verdict"] == "H-B_SUPPORTED"
