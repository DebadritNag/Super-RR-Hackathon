"""Phase 4 shrinkage: hand-checkable estimates, leave-one-player-out target, configs, choice."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.phase4 import shrink as sh


def make_fit(sigma2=1.0, between=0.25, train=None):
    train = train if train is not None else {1: (10.0, 20.0), 2: (-10.0, 20.0), 3: (0.0, 20.0)}
    s = pd.Series({k: v[0] for k, v in train.items()})
    n = pd.Series({k: v[1] for k, v in train.items()})
    return {"sigma2": sigma2, "between": between, "players": len(s), "total_s": float(s.sum()),
            "total_n": float(n.sum()), "train_s": s, "train_n": n}  # fmt: skip


def table(rows):
    pt = pd.DataFrame(rows, columns=["player_id", "n", "mean", "n_eff"]).set_index("player_id")
    pt["s"] = pt["n"] * pt["mean"]
    pt["s2"] = 0.0
    pt["matches"] = 3
    return pt


def test_normal_normal_hand_check():
    fit = make_fit(sigma2=1.0, between=0.25, train={7: (0.0, 50.0)})  # other players' mean = 0
    pt = table([(1, 4.0, 1.0, 4.0)])
    out = sh.estimate(pt, fit, "shrink_eb")
    # tau2 = 0.25, k = 4, B = 4 / 8 = 0.5, target 0 -> 0.5
    assert out.loc[1, "k"] == 4.0
    assert abs(out.loc[1, "B"] - 0.5) < 1e-12
    assert abs(out.loc[1, "shrunk"] - 0.5) < 1e-12


def test_tau2_below_floor_gives_strong_shrinkage_and_flag():
    fit = make_fit(sigma2=1.0, between=-0.3, train={7: (0.0, 50.0)})
    k = sh.k_for(fit, "shrink_eb")
    assert k["k"] == 100.0 and k["floor_hit"] is True
    out = sh.estimate(table([(1, 1.0, 5.0, 1.0)]), fit)
    assert abs(out.loc[1, "shrunk"]) < 0.06  # one ball: pulled to the pooled mean of others


def test_zero_shrinkage_equals_raw_residual():
    fit = make_fit()
    pt = table([(1, 5.0, 0.7, 5.0), (2, 1.0, -0.4, 1.0)])
    out = sh.estimate(pt, fit, "shrink_none")
    assert np.allclose(out["shrunk"], pt["mean"])
    assert (out["k"] == 0).all()


def test_equal_residuals_and_one_ball_player_approach_the_common_value():
    # every other player has mean +0.2; zero variance -> floor, shrink target is 0.2
    fit = make_fit(sigma2=0.0, between=0.0, train={7: (10.0, 50.0), 8: (4.0, 20.0)})
    out = sh.estimate(table([(1, 1.0, 0.2, 1.0), (2, 30.0, 0.2, 30.0)]), fit)
    assert np.allclose(out["shrunk"], 0.2)


def test_leave_one_player_out_target_excludes_own_train_data():
    fit = make_fit(train={1: (10.0, 10.0), 2: (-10.0, 10.0), 3: (0.0, 10.0)})
    t = sh.lpo_target(fit, pd.Index([1, 2, 99]))
    assert np.allclose(t, [(-10 + 0) / 20, (10 + 0) / 20, 0.0])
    # mutation: changing player 1's own TRAIN residuals must not change player 1's target
    fit2 = make_fit(train={1: (999.0, 10.0), 2: (-10.0, 10.0), 3: (0.0, 10.0)})
    assert sh.lpo_target(fit2, pd.Index([1]))[0] == t[0]


def test_strength_grid_orders_k():
    fit = make_fit(sigma2=1.0, between=0.5)
    ks = {c: sh.k_for(fit, c)["k"] for c in sh.CONFIGS}
    assert ks["shrink_tau0.5"] > ks["shrink_eb"] > ks["shrink_tau2"] > ks["shrink_tau4"]
    assert ks["shrink_none"] == 0.0


def test_target0_uses_zero_target():
    fit = make_fit(train={7: (50.0, 50.0)})
    out = sh.estimate(table([(1, 4.0, 1.0, 4.0)]), fit, "shrink_target0")
    assert out.loc[1, "target"] == 0.0


def test_fit_cell_uses_only_given_table_and_is_deterministic():
    rows = pd.DataFrame(
        {
            "player_id": [1, 1, 2, 2, 3, 3],
            "match_id": [1, 2, 1, 2, 1, 2],
            "resid": [0.5, 0.1, -0.3, 0.2, 0.0, 0.4],
        }  # fmt: skip
    )
    pt = sh.player_table(sh.match_stats(rows))
    assert sh.fit_cell(pt)["sigma2"] == sh.fit_cell(pt.copy())["sigma2"]
    assert pt.loc[1, "n"] == 2 and pt.loc[1, "matches"] == 2


def test_bootstrap_is_seeded_and_interval_contains_estimate_for_stable_player():
    rows = pd.DataFrame(
        {
            "player_id": np.repeat([1, 2], 40),
            "match_id": np.tile(np.arange(40), 2),
            "resid": np.r_[np.full(40, 0.5), np.full(40, -0.5)],
        }  # fmt: skip
    )
    ms = sh.match_stats(rows)
    pt = sh.player_table(ms)
    fit = sh.fit_cell(pt)
    est = sh.estimate(pt, fit)
    d1 = sh.bootstrap_draws(ms, est, 200, 1)
    d2 = sh.bootstrap_draws(ms, est, 200, 1)
    assert d1.equals(d2)
    lo, hi = sh.interval(d1)
    assert (lo <= est["shrunk"] + 1e-9).all() and (hi >= est["shrunk"] - 1e-9).all()


def _choice_cells(seed=0, n=30, matches=20):
    rng = np.random.default_rng(seed)
    true = rng.normal(0, 0.3, n)
    tr = pd.DataFrame(
        {
            "player_id": np.repeat(np.arange(n), 10),
            "match_id": np.tile(np.arange(10), n),
            "resid": rng.normal(np.repeat(true, 10), 1.0),
        }  # fmt: skip
    )
    va = pd.DataFrame(
        {
            "player_id": np.repeat(np.arange(n), matches),
            "match_id": np.tile(np.arange(matches), n),
            "resid": rng.normal(np.repeat(true, matches), 1.0),
        }  # fmt: skip
    )
    tpt = sh.player_table(sh.match_stats(tr))
    return [{"fit": sh.fit_cell(tpt), "train_pt": tpt, "val_ms": sh.match_stats(va)}]


def test_choice_is_recorded_deterministic_and_never_zero_shrinkage(tmp_path):
    c1 = sh.choose_shrinkage(_choice_cells(), 200)
    c2 = sh.choose_shrinkage(_choice_cells(), 200)
    assert c1 == c2
    assert c1["chosen"] in sh.CHOOSABLE and c1["test_outcomes_used"] is False
    assert c1["selection_data"] == ["TRAIN", "VALIDATION"]
    assert c1["losses"]["shrink_none"]["choosable"] is False
    p = sh.record_choice(c1, tmp_path / "choice.json")
    assert p.exists()


def test_choice_without_validation_overlap_keeps_default():
    cells = _choice_cells()
    cells[0]["val_ms"] = cells[0]["val_ms"].iloc[0:0]
    assert sh.choose_shrinkage(cells, 50)["chosen"] == sh.DEFAULT_CONFIG
