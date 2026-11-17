"""Definition comparison: pass list, top group, stability, confounding, metrics (synthetic data)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from app.phase5 import reliability as rb
from app.phase6 import definition_compare as dc

SEED = 20260512


def _cells(rows):
    """rows: (definition, status, sb_lo) per cell."""
    return pd.DataFrame([{"definition": d, "status": s, "sb_lo": lo} for d, s, lo in rows])


def _summary(items):
    """items: (definition, passes, m1, se1, m4, m5)."""
    df = pd.DataFrame(items, columns=["definition", "passes", "m1", "se1", "m4", "m5"])
    df["m1_int"], df["se1_int"], df["m5_int"] = df["m1"], df["se1"], df["m5"]
    return df


# ---------------------------------------------------------------- PASS(d)
def test_pass_requires_all_cells_estimable_and_three_lower_bounds_above_zero():
    cells = _cells(
        [("a", "ESTIMATED", 0.1)] * 3
        + [("a", "ESTIMATED", -0.1)]
        + [("b", "ESTIMATED", 0.1)] * 2
        + [("b", "ESTIMATED", -0.1)] * 2
        + [("c", "ESTIMATED", 0.2)] * 3
        + [("c", "NOT_ESTIMABLE", None)]
        + [("d", "ESTIMATED", 0.2)] * 4
    )
    p = dc.pass_table(cells, 4).set_index("definition")
    assert bool(p.loc["a", "passes"]) is True  # 3 of 4 lower bounds above 0
    assert bool(p.loc["b", "passes"]) is False  # only 2
    assert bool(p.loc["c", "passes"]) is False  # one cell not estimable
    assert bool(p.loc["d", "passes"]) is True
    assert int(p.loc["c", "cells_estimable"]) == 3
    assert int(p.loc["a", "cells_lo_positive"]) == 3


def test_lower_bound_exactly_zero_does_not_count():
    cells = _cells([("a", "ESTIMATED", 0.0)] * 4)
    assert not dc.pass_table(cells, 4)["passes"].iloc[0]


# ---------------------------------------------------------------- TOP(d)
def test_top_group_is_within_one_se_of_the_best_and_ordered_by_m4_m5_id():
    s = _summary(
        [
            ("d1", True, 0.50, 0.05, 40.0, 0.70),
            ("d2", True, 0.47, 0.05, 60.0, 0.70),  # within SE of the best
            ("d3", True, 0.44, 0.05, 90.0, 0.90),  # outside: 0.44 < 0.45
            ("d4", False, 0.99, 0.05, 99.0, 0.99),  # does not pass: never in the group
        ]
    )
    assert dc.top_group(s) == ["d2", "d1"]  # M4 descending


def test_top_group_ties_fall_back_to_m5_then_id():
    s = _summary(
        [
            ("b", True, 0.50, 0.10, 50.0, 0.70),
            ("a", True, 0.50, 0.10, 50.0, 0.70),
            ("c", True, 0.50, 0.10, 50.0, 0.80),
        ]
    )
    assert dc.top_group(s) == ["c", "a", "b"]  # M5 first, then id ascending


def test_top_group_empty_without_a_passing_definition():
    s = _summary([("a", False, 0.5, 0.1, 10.0, 0.5)])
    assert dc.top_group(s) == []


# ---------------------------------------------------------------- decide and stability
SIZES_BIG = {"IPL|batter": 40, "IPL|bowler": 41, "T20I|batter": 42, "T20I|bowler": 43}
SIZES_SMALL = {"IPL|batter": 3, "IPL|bowler": 19, "T20I|batter": 2, "T20I|bowler": 11}


def test_decide_names_a_provisional_top_group_when_not_confounded():
    s = _summary([("a", True, 0.5, 0.1, 50.0, 0.7), ("b", False, 0.9, 0.1, 99.0, 0.9)])
    out = dc.decide(s, SIZES_BIG, 4)
    assert out["status"] == dc.TOP_PROVISIONAL
    assert out["pass_list"] == ["a"] and out["top_group"] == ["a"]
    assert out["confounded"] is False


def test_decide_is_confounded_when_any_intersection_is_below_thirty():
    s = _summary([("a", True, 0.5, 0.1, 50.0, 0.7)])
    out = dc.decide(s, SIZES_SMALL, 4)
    assert out["status"] == dc.CONFOUNDED
    assert out["pass_list"] == ["a"] and out["top_group"] == []


def test_decide_reports_no_pass():
    s = _summary([("a", False, 0.5, 0.1, 50.0, 0.7)])
    out = dc.decide(s, SIZES_BIG, 4)
    assert out["status"] == dc.NO_PASS and out["pass_list"] == [] and out["top_group"] == []


def test_decide_rule_uses_the_intersection_versions():
    s = _summary([("a", True, 0.1, 0.01, 50.0, 0.7), ("b", True, 0.1, 0.01, 40.0, 0.7)])
    s["m1_int"] = [0.20, 0.50]  # in the intersection b is far ahead of a
    s["se1_int"] = [0.05, 0.05]
    out = dc.decide(s, SIZES_BIG, 4)
    assert out["top_group"] == ["b"]


def test_stability_flags_different_top_sets_and_names_no_group():
    pre = {"status": dc.TOP_PROVISIONAL, "pass_list": ["a", "b"], "top_group": ["a"],
           "confounded": False}  # fmt: skip
    train = {"status": dc.TOP_PROVISIONAL, "pass_list": ["a", "b"], "top_group": ["b"],
             "confounded": False}  # fmt: skip
    out = dc.stability(pre, train)
    assert out["status"] == dc.NOT_STABLE and out["top_group"] == []
    assert out["pass_list"] == ["a", "b"] and out["train_top_group"] == ["b"]


def test_stability_keeps_the_group_when_sets_are_equal():
    pre = {
        "status": dc.TOP_PROVISIONAL,
        "pass_list": ["a"],
        "top_group": ["a"],
        "confounded": False,
    }
    train = {
        "status": dc.TOP_PROVISIONAL,
        "pass_list": ["a"],
        "top_group": ["a"],
        "confounded": False,
    }
    out = dc.stability(pre, train)
    assert out["status"] == dc.TOP_PROVISIONAL and out["top_group"] == ["a"]


def test_stability_confounded_stays_confounded():
    pre = {"status": dc.CONFOUNDED, "pass_list": ["a"], "top_group": [], "confounded": True}
    train = {
        "status": dc.TOP_PROVISIONAL,
        "pass_list": ["b"],
        "top_group": ["b"],
        "confounded": False,
    }
    out = dc.stability(pre, train)
    assert out["status"] == dc.CONFOUNDED and out["top_group"] == []


# ---------------------------------------------------------------- metrics
def _cell(tau2: float, P: int = 300, M: int = 40, n_balls: int = 8, seed: int = SEED):
    rng = np.random.default_rng(seed)
    u = rng.normal(0, np.sqrt(tau2), P) if tau2 > 0 else np.zeros(P)
    N = np.full((P, M), float(n_balls))
    r = u[:, None, None] + rng.normal(0, 1, (P, M, n_balls))
    dates = np.array([f"2024-{1 + j // 28:02d}-{1 + j % 28:02d}" for j in range(M)])
    period = np.array(["TRAIN"] * (M // 2) + ["VALIDATION"] * (M - M // 2))
    return rb.CellData(np.arange(P), np.arange(M), dates, period, N, r.sum(2), (r**2).sum(2))


def _weights(M: int, draws: int, seed: int = SEED):
    return (
        np.random.default_rng(seed).multinomial(M, np.full(M, 1.0 / M), size=draws).T.astype(float)
    )


def test_spearman_draws_matches_scipy_and_skips_missing():
    rng = np.random.default_rng(1)
    ref = rng.normal(size=30)
    draws = np.column_stack([ref + rng.normal(0, 0.5, 30), rng.normal(size=30)])
    draws[3, 1] = np.nan
    out = dc.spearman_draws(draws, ref)
    assert out[0] == pytest.approx(spearmanr(draws[:, 0], ref).statistic)
    ok = np.isfinite(draws[:, 1])
    assert out[1] == pytest.approx(spearmanr(draws[ok, 1], ref[ok]).statistic)


def test_unit_metrics_recovers_known_reliability_and_is_deterministic():
    cd = _cell(1.5 / 320)  # true reliability 0.6 of the full mean
    mask = np.ones(40, dtype=bool)
    w = _weights(40, 300)
    a = dc.unit_metrics(cd, w, mask)
    b = dc.unit_metrics(cd, w, mask)
    assert a["status"] == rb.ESTIMATED
    assert a["sb"] == pytest.approx(0.6, abs=0.1)
    assert a["sb_lo"] < a["sb"] and a["sb_lo"] < a["sb_hi"]
    assert a["sb"] == b["sb"] and a["sb_lo"] == b["sb_lo"] and a["m5_median"] == b["m5_median"]
    assert 0.0 <= a["m3"] <= 1.0
    assert a["m4_median_balls"] == 320.0  # every individual has 40 matches x 8 balls
    assert 0.0 < a["m5_median"] <= 1.0
    assert 0.0 < a["m2"] < 1.0


def test_unit_metrics_pure_noise_has_no_reliability():
    cd = _cell(0.0)
    out = dc.unit_metrics(cd, _weights(40, 300), np.ones(40, dtype=bool))
    assert abs(out["sb"]) < 0.2
    assert out["sb_lo"] < 0 < out["sb_hi"]  # the interval covers 0


def test_unit_metrics_keep_restricts_the_individuals():
    cd = _cell(1.5 / 320)
    keep = np.zeros(300, dtype=bool)
    keep[:50] = True
    out = dc.unit_metrics(cd, _weights(40, 100), np.ones(40, dtype=bool), keep=keep)
    assert out["players"] == 50 and set(out["ok_ids"]) <= set(range(50))


def test_unit_metrics_not_estimable_below_ten_individuals():
    cd = _cell(0.04, P=6)
    out = dc.unit_metrics(cd, _weights(40, 50), np.ones(40, dtype=bool))
    assert out["status"] == rb.NOT_ESTIMABLE


def test_pooled_sb_draws_matches_hand_formula():
    r1, r2 = np.array([0.4, 0.2]), np.array([0.2, 0.2])
    out = dc.pooled_sb_draws([r1, r2], [53, 103])
    z = lambda r: np.arctanh(r)  # noqa: E731
    expect = np.tanh((50 * z(r1) + 100 * z(r2)) / 150)
    assert out == pytest.approx(2 * expect / (1 + expect))


# ---------------------------------------------------------------- control sample
def test_control_sample_matches_pressure_balls_per_player_match():
    from app.phase4 import engine as en

    rng = np.random.default_rng(3)
    rows = []
    for p in range(12):
        for m in range(6):
            n_press = int(rng.integers(1, 4))
            n_rest = int(rng.integers(0, 6))
            for i in range(n_press + n_rest):
                rows.append({"src": len(rows), "player_id": p, "match_id": m, "comp": "IPL",
                             "period": "TRAIN" if m < 3 else "VALIDATION",
                             "date": f"2024-01-{m + 1:02d}", "actual": 1.0, "expected": 0.5,
                             "resid": float(rng.normal()), "in_pop": True, "press": i < n_press})  # fmt: skip
    t = pd.DataFrame(rows)
    cell = en.build_cell(t[t["press"]], "IPL", "batter", "runs")
    ctrl = dc.control_cd(t, cell, "IPL", "batter", "runs", 7)
    for p in range(12):
        for m in range(6):
            n_press = int(((t.player_id == p) & (t.match_id == m) & t.press).sum())
            n_rest = int(((t.player_id == p) & (t.match_id == m) & ~t.press).sum())
            if n_rest == 0 or ctrl is None:
                continue
            pi = list(ctrl.players).index(p)
            mi = list(ctrl.match_ids).index(m)
            assert ctrl.N[pi, mi] == min(n_press, n_rest)
    again = dc.control_cd(t, cell, "IPL", "batter", "runs", 7)
    assert np.array_equal(ctrl.S, again.S)  # seeded


# ---------------------------------------------------------------- no player-level output
def test_player_columns_are_rejected():
    dc.assert_no_player_columns(pd.DataFrame({"definition": ["a"], "players": [3]}))
    for bad in ("player_id", "player", "Player_Name"):
        with pytest.raises(ValueError):
            dc.assert_no_player_columns(pd.DataFrame({bad: [1]}))


def test_table_builders_carry_no_player_columns():
    cells = pd.DataFrame(
        {"definition": ["a"], "format": ["IPL"], "role": ["batter"], "stream": ["runs"],
         "window": ["PRE_TEST"], "status": ["ESTIMATED"], "players": [30], "m5_median": [0.8],
         "m5_p5": [0.6], "m5_draws": [1000], "label": ["x"]}
    )  # fmt: skip
    dc.assert_no_player_columns(dc.resampling_table(cells))
    out = dc.outcome_table({"PRE_TEST": {"status": "s", "pass_list": [], "top_group": []}},
                           {"status": "s", "pass_list": [], "top_group": []}, {"seed": 1})  # fmt: skip
    dc.assert_no_player_columns(out)
    assert set(out["window"]) == {"PRE_TEST", "FINAL"}


def test_stored_definition_tables_have_no_player_column_and_carry_the_hash():
    import json

    from app.phase5.constants import REPORTS_DIR
    from app.phase6.constants import CRITERIA_HASH_FILE

    digest = json.loads(CRITERIA_HASH_FILE.read_text(encoding="utf-8"))["sha256"]
    base = "phase6_definition_reliability_comparison"
    found = 0
    for suffix in ("", "_summary", "_resampling", "_outcome"):
        p = REPORTS_DIR / f"{base}{suffix}.csv"
        if not p.exists():
            continue
        found += 1
        df = pd.read_csv(p)
        dc.assert_no_player_columns(df)
        assert set(df["criteria_sha256"]) == {digest}
    if not found:
        pytest.skip("definition comparison has not been run")
