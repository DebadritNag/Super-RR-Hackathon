"""Split-half reliability on synthetic players with known reliability, Spearman-Brown, bootstrap."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase5 import reliability as rb
from app.phase6 import split_half as sp

SEED = 20260512


def _players(tau2: float, P: int = 400, M: int = 40, n_balls: int = 8, seed: int = SEED):
    rng = np.random.default_rng(seed)
    u = rng.normal(0, np.sqrt(tau2), P) if tau2 > 0 else np.zeros(P)
    N = np.full((P, M), float(n_balls))
    r = u[:, None, None] + rng.normal(0, 1, (P, M, n_balls))
    dates = np.array([f"2024-{1 + j // 28:02d}-{1 + j % 28:02d}" for j in range(M)])
    period = np.array(["TRAIN"] * (M // 2) + ["VALIDATION"] * (M - M // 2))
    return rb.CellData(np.arange(P), np.arange(M), dates, period, N, r.sum(2), (r**2).sum(2))


def test_spearman_brown_formula():
    assert float(rb.sb(0.5)) == pytest.approx(2.0 / 3.0)
    assert float(rb.sb(0.0)) == 0.0
    assert float(rb.sb(-0.2)) == pytest.approx(-0.4 / 0.8)  # negative stays negative, not clipped


def test_known_reliability_is_recovered():
    # half mean noise = 1/160, so reliability 0.6 of the full mean needs tau2 = 1.5 / 320
    cd = _players(1.5 / 320)
    mask = np.ones(40, dtype=bool)
    row, ci = sp.split_half_unit(cd, None, mask, "odd_even", 6, SEED, n_boot=500)
    assert row["status"] == rb.ESTIMATED
    assert row["sb_pearson"] == pytest.approx(0.6, abs=0.1)
    lo, hi = ci[0]["lo"], ci[0]["hi"]
    assert lo < 0.6 < hi
    rrow, _ = sp.split_half_unit(cd, None, mask, "random", 6, SEED, n_random=50, n_boot=200)
    assert rrow["sb_pearson"] == pytest.approx(0.6, abs=0.1)
    assert rrow["split_sd_sb"] > 0


def test_pure_noise_interval_covers_zero():
    cd = _players(0.0, seed=11)
    row, ci = sp.split_half_unit(cd, None, np.ones(40, dtype=bool), "odd_even", 6, SEED, n_boot=500)
    assert row["status"] == rb.ESTIMATED
    assert ci[0]["lo"] <= 0.0 <= ci[0]["hi"]
    assert abs(row["sb_pearson"]) < 0.2


def test_matches_phase5_odd_even_and_early_late():
    cd = _players(0.01)
    sub = cd
    for mode in ("odd_even", "early_late"):
        mine, _ = sp.split_half_unit(cd, None, np.ones(40, dtype=bool), mode, 6, SEED, n_boot=200)
        ref = rb.split_half(sub, "PRE_TEST", mode, 6, None, SEED)
        assert mine["r_pearson"] == pytest.approx(ref["r_pearson"], abs=1e-12)
        assert mine["players"] == ref["players"]


def test_bootstrap_seed_determinism():
    rng = np.random.default_rng(1)
    m1 = rng.normal(size=100)
    m2 = 0.4 * m1 + rng.normal(size=100)
    a = sp.bootstrap_players(m1, m2, 300, 42)
    b = sp.bootstrap_players(m1, m2, 300, 42)
    c = sp.bootstrap_players(m1, m2, 300, 43)
    np.testing.assert_array_equal(a, b)
    assert not np.array_equal(a, c)


def test_unit_rows_deterministic_and_seed_sensitive_for_random_mode():
    cd = _players(0.01, P=150)
    mask = np.ones(40, dtype=bool)
    kw = {"n_random": 30, "n_boot": 100}
    r1, c1 = sp.split_half_unit(cd, None, mask, "random", 6, 5, **kw)
    r2, c2 = sp.split_half_unit(cd, None, mask, "random", 6, 5, **kw)
    r3, c3 = sp.split_half_unit(cd, None, mask, "random", 6, 6, **kw)
    assert r1 == r2 and c1 == c2
    assert r1["r_pearson"] != r3["r_pearson"] or c1 != c3


def test_match_bootstrap_interval_with_weights():
    cd = _players(0.01, P=150)
    gm = np.random.default_rng(3)
    w = gm.multinomial(40, np.full(40, 1 / 40), size=300).T.astype(float)
    row, ci = sp.split_half_unit(cd, w, np.ones(40, dtype=bool), "odd_even", 6, SEED, n_boot=100)
    methods = {c["ci_method"] for c in ci}
    assert methods == {"player_bootstrap", "match_bootstrap"}
    mb = next(c for c in ci if c["ci_method"] == "match_bootstrap")
    # each draw drops about 37% of the matches, so half means get noisier and the match-bootstrap
    # interval sits below the point estimate; it is a conservative check for "above 0", not centred
    assert mb["lo"] < mb["hi"] < row["sb_pearson"]


def test_not_estimable_with_too_few_players():
    cd = _players(0.01, P=6)
    row, ci = sp.split_half_unit(cd, None, np.ones(40, dtype=bool), "odd_even", 6, SEED)
    assert row["status"] == rb.NOT_ESTIMABLE and row["sb_pearson"] is None and ci == []


def test_unknown_mode_and_window_raise():
    cd = _players(0.01, P=20)
    with pytest.raises(ValueError):
        sp.split_half_unit(cd, None, np.ones(40, dtype=bool), "bogus", 6, 1)
    with pytest.raises(ValueError):
        sp.window_mask(cd, "TEST")


def test_window_mask_by_period_and_date():
    cd = _players(0.01, P=10)
    assert sp.window_mask(cd, "TRAIN").sum() == 20
    assert sp.window_mask(cd, "PRE_TEST").sum() == 40
    m = sp.window_mask(cd, None, start="2024-02-01")
    assert m.sum() == int((pd.Series(cd.dates) >= "2024-02-01").sum())
    both = sp.window_mask(cd, "TRAIN", start="2024-02-01")
    assert both.sum() == int(
        ((pd.Series(cd.dates) >= "2024-02-01").to_numpy() & (cd.period == "TRAIN")).sum()
    )


def test_fisher_pool_weights_and_clip():
    p = sp.fisher_pool(np.array([0.5, 0.5]), np.array([100, 300]))
    assert p["r"] == pytest.approx(0.5, abs=1e-9)
    assert p["se"] == pytest.approx(1 / np.sqrt(97 + 297))
    big = sp.fisher_pool(np.array([1.0]), np.array([50]))
    assert big["r"] == pytest.approx(0.99)
    assert np.isnan(sp.fisher_pool(np.array([np.nan]), np.array([50]))["r"])


def test_unit_seed_is_stable_and_key_dependent():
    assert sp.unit_seed(1, "a", "b") == sp.unit_seed(1, "a", "b")
    assert sp.unit_seed(1, "a", "b") != sp.unit_seed(1, "a", "c")
    assert sp.unit_seed(1, "a") != sp.unit_seed(2, "a")
