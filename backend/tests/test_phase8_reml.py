"""REML: recovers known variance components, floor handling, posterior algebra, multiplicity."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase8.reml import RemlError, fit_reml, player_summary, posterior


def _sim(tau: float, sigma: float, n_players=200, n_units=12, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_players):
        u = rng.normal(0, tau)
        for j in range(n_units):
            prec = rng.uniform(5, 30)
            rows.append(
                {"player_id": p, "y": 0.2 + u + rng.normal(0, sigma / np.sqrt(prec)), "prec": prec}
            )
    return pd.DataFrame(rows)


def test_recovers_known_components():
    f = fit_reml(_sim(0.3, 1.0))
    assert f["floor"] is False
    assert f["tau2"] == pytest.approx(0.09, rel=0.25)
    assert f["sigma2"] == pytest.approx(1.0, rel=0.1)
    assert f["mu"] == pytest.approx(0.2, abs=0.05)


def test_no_between_player_signal_hits_the_floor_and_collapses_posterior():
    # Every player has the same unit pattern, so player means are identical: no between variance.
    rows = [
        {"player_id": p, "y": 0.5 * (-1) ** j + 0.1 * j, "prec": 10.0}
        for p in range(30)
        for j in range(8)
    ]
    f = fit_reml(pd.DataFrame(rows))
    assert f["floor"] is True and f["tau2"] == 0.0
    assert f["label"] == "NO_BETWEEN_PLAYER_SIGNAL"
    assert (f["players"]["theta"] == f["mu"]).all()
    assert (f["players"]["B"] == 0).all()


def test_posterior_is_a_convex_combination_of_mean_and_player_mean():
    f = fit_reml(_sim(0.3, 1.0, seed=5))
    p = f["players"]
    lo = np.minimum(p["ybar"], f["mu"])
    hi = np.maximum(p["ybar"], f["mu"])
    assert ((p["theta"] >= lo - 1e-12) & (p["theta"] <= hi + 1e-12)).all()
    assert ((p["B"] >= 0) & (p["B"] <= 1)).all()
    assert (p["se"] >= 0).all()


def test_more_data_gives_less_shrinkage():
    f = fit_reml(_sim(0.3, 1.0, seed=5))
    assert (
        posterior(np.array([1.0]), np.array([1000.0]), 0.0, f["tau2"], f["sigma2"])[0]
        > posterior(np.array([1.0]), np.array([5.0]), 0.0, f["tau2"], f["sigma2"])[0]
    )


def test_multiplicity_equals_replication():
    u = _sim(0.3, 1.0, n_players=40, n_units=6, seed=9)
    mult = pd.Series(np.random.default_rng(1).integers(0, 3, len(u)), index=u.index)
    a = player_summary(u.assign(mult=mult))
    rep = u.loc[u.index.repeat(mult.to_numpy())]
    b = player_summary(rep)
    assert np.allclose(a["ybar"].reindex(b.index), b["ybar"])
    assert np.allclose(a["S"].reindex(b.index), b["S"])
    assert np.allclose(a["P"].reindex(b.index), b["P"])


def test_unidentifiable_inputs_raise():
    one = pd.DataFrame({"player_id": range(5), "y": np.zeros(5), "prec": np.ones(5)})
    with pytest.raises(RemlError):
        fit_reml(one)
    with pytest.raises(RemlError):
        fit_reml(pd.DataFrame({"player_id": [1, 1], "y": [0.0, 1.0], "prec": [1.0, 1.0]}))
    with pytest.raises(RemlError):
        player_summary(pd.DataFrame({"player_id": [1], "y": [0.0], "prec": [0.0]}))
