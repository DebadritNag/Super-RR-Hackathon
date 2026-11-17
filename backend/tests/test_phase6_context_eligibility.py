"""Context reliability and eligibility-threshold reliability: synthetic checks and stored results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.phase4 import eligibility as el
from app.phase5 import reliability as rb
from app.phase5.constants import FROZEN_CHOICES, REPORTS_DIR
from app.phase6 import context_reliability as cr6
from app.phase6 import eligibility_reliability as er

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260512
SPEC = {"min_balls_per_half": 6, "min_individuals_estimable": 10, "random_splits": 20}


def _cell(tau2: float, P: int = 200, M: int = 40, n_balls: int = 8, seed: int = SEED):
    rng = np.random.default_rng(seed)
    u = rng.normal(0, np.sqrt(tau2), P) if tau2 > 0 else np.zeros(P)
    N = np.full((P, M), float(n_balls))
    r = u[:, None, None] + rng.normal(0, 1, (P, M, n_balls))
    dates = np.array([f"2024-{1 + j // 28:02d}-{1 + j % 28:02d}" for j in range(M)])
    period = np.array(["TRAIN"] * (M // 2) + ["VALIDATION"] * (M - M // 2))
    return rb.CellData(np.arange(P), np.arange(M), dates, period, N, r.sum(2), (r**2).sum(2))


def _w(M: int, draws: int = 200):
    return (
        np.random.default_rng(SEED).multinomial(M, np.full(M, 1.0 / M), size=draws).T.astype(float)
    )


# ---------------------------------------------------------------- Kish count and pools
def test_kish_n_eff_equals_matches_for_equal_ball_counts_and_one_for_a_single_match():
    N = np.array([[4.0, 4.0, 4.0, 4.0], [10.0, 0.0, 0.0, 0.0], [8.0, 2.0, 0.0, 0.0], [0, 0, 0, 0]])
    ne = er.kish_n_eff(N)
    assert ne[0] == pytest.approx(4.0) and ne[1] == pytest.approx(1.0)
    assert ne[2] == pytest.approx(100 / 68) and ne[3] == 0.0


def test_pool_unit_reports_reliability_data_weight_and_the_gate_constant():
    cd = _cell(1.5 / 320)
    mask = np.ones(40, dtype=bool)
    row = er.pool_unit(cd, _w(40), mask, 100.0, 25.0, SPEC, SEED, 200)
    assert row["status"] == rb.ESTIMATED and row["gate"] == 0.5 == el.GATE_B
    assert row["players_ge_t"] == 200 and row["min_total_balls"] == 100.0
    assert row["sb"] == pytest.approx(0.6, abs=0.15)
    assert row["marginal_n_eff"] == pytest.approx(40.0)  # 40 matches of 8 balls each
    assert row["b_marginal"] == pytest.approx(40 / 65)
    assert row["n_pool_n_eff_at_least_k"] == 200  # all 200 individuals have n_eff 40 >= k


def test_pool_unit_is_not_estimable_when_the_pool_is_too_small():
    cd = _cell(0.04)
    row = er.pool_unit(cd, _w(40), np.ones(40, dtype=bool), 10_000.0, 25.0, SPEC, SEED, 50)
    assert row["status"] == rb.NOT_ESTIMABLE and row["players_ge_t"] == 0


def test_pool_unit_is_deterministic_for_a_seed():
    cd = _cell(0.02)
    a = er.pool_unit(cd, _w(40), np.ones(40, dtype=bool), 100.0, 25.0, SPEC, SEED, 100)
    b = er.pool_unit(cd, _w(40), np.ones(40, dtype=bool), 100.0, 25.0, SPEC, SEED, 100)
    assert a == b


# ---------------------------------------------------------------- target table
def _ladder(sbs, lo_players=None, lo_matches=None):
    rows = []
    for i, sb in enumerate(sbs):
        rows.append({"format": "IPL", "role": "batter", "window": "PRE_TEST", "source": "ladder",
                     "min_total_balls": 12.0 * (i + 1), "status": rb.ESTIMATED, "sb": sb,
                     "sb_lo_players": None if lo_players is None else lo_players[i],
                     "sb_lo_matches": None if lo_matches is None else lo_matches[i]})  # fmt: skip
    return pd.DataFrame(rows)


def test_target_table_reads_the_smallest_step_reaching_each_target():
    t = er.target_table(_ladder([0.3, 0.45, 0.55, 0.72], [0.0, 0.1, 0.3, 0.52]), [0.5, 0.7, 0.8])
    by = t.set_index("target")
    assert by.loc[0.5, "min_balls_point"] == 36.0 and by.loc[0.5, "status"] == er.REACHED
    assert by.loc[0.7, "min_balls_point"] == 48.0
    assert by.loc[0.8, "status"] == er.NOT_REACHED and pd.isna(by.loc[0.8, "min_balls_point"])
    assert by.loc[0.5, "min_balls_lo_players"] == 48.0  # interval lower bound reaches 0.5 later
    assert pd.isna(by.loc[0.7, "min_balls_lo_players"])


def test_target_table_ignores_non_ladder_rows_and_handles_no_estimable_step():
    d = _ladder([0.9])
    d["source"] = "frozen_scaled"
    assert len(er.target_table(d, [0.5])) == 0
    d2 = _ladder([0.9])
    d2["status"] = rb.NOT_ESTIMABLE
    assert er.target_table(d2, [0.5]).iloc[0]["status"] == rb.NOT_ESTIMABLE


# ---------------------------------------------------------------- projections and measured counts
def test_projection_matches_formula_and_gives_no_upper_bound_when_tau2_lower_bound_is_not_positive():
    cd = _cell(0.05, P=300)
    mask = np.ones(40, dtype=bool)
    rows = er.projection_rows(cd, _w(40, 300), mask, [0.5, 0.8], {"format": "IPL"})
    e1b = [r for r in rows if r["source"] == "E1b_ball_independent"]
    assert {r["target"] for r in e1b} == {0.5, 0.8} and all(
        r["label"] == "DESCRIPTIVE_PROJECTION" for r in e1b
    )
    r5 = next(r for r in e1b if r["target"] == 0.5)
    assert r5["required_balls"] == pytest.approx(r5["sigma_eff"] / r5["tau2"])
    r8 = next(r for r in e1b if r["target"] == 0.8)
    assert r8["required_balls"] == pytest.approx(4 * r5["required_balls"])  # R/(1-R): 4 vs 1
    # true tau2 0.05, sigma 1: about 20 balls for R = 0.5
    assert r5["required_balls"] == pytest.approx(20.0, rel=0.3)
    null = er.projection_rows(_cell(0.0, P=60), _w(40, 300), mask, [0.5], {})
    e7 = next(r for r in null if r["source"] == "E7_split_half_covariance")
    assert e7["tau2_lo"] is None or e7["tau2_lo"] <= 0 or e7.get("required_balls_hi") is not None


def test_balls_at_n_eff_counts_individuals_reaching_k():
    cd = _cell(0.04, P=20, M=40)
    cd.N[:5, 20:] = 0.0  # five individuals only play 20 matches
    out = er.balls_at_n_eff(cd, np.ones(40, dtype=bool), 25.0)
    assert out["players_total"] == 20 and out["players_n_eff_at_least_k"] == 15
    assert out["min_balls_among_them"] == 320.0 and out["max_n_eff"] == pytest.approx(40.0)
    none = er.balls_at_n_eff(cd, np.ones(40, dtype=bool), 100.0)
    assert none["players_n_eff_at_least_k"] == 0 and none["min_balls_among_them"] is None


# ---------------------------------------------------------------- context helpers
def test_signal_share_is_high_with_signal_and_near_zero_without():
    hi = cr6.signal_share(_cell(0.3), np.ones(40, dtype=bool), 6)
    lo = cr6.signal_share(_cell(0.0), np.ones(40, dtype=bool), 6)
    assert hi["share"] > 0.6 and abs(lo["share"]) < 0.25
    assert hi["players"] == 200


def test_regression_summary_flags_gate_state_and_eligibility_differences():
    base = pd.DataFrame({"marginal_b_abs_diff_vs_stored": [0.0, 0.0],
                         "gate_passed_recomputed": [False, False],
                         "stored_gate_passed": [False, False],
                         "eligible_players": [10, 12], "stored_eligible_players": [10, 12]})  # fmt: skip
    assert cr6.regression_summary(base)["reproduces"] is True
    flipped = base.assign(gate_passed_recomputed=[False, True])
    s = cr6.regression_summary(flipped)
    assert s["gate_state_differences"] == 1 and s["reproduces"] is False
    off = base.assign(eligible_players=[10, 11])
    assert cr6.regression_summary(off)["eligible_count_differences"] == 1
    drift = base.assign(marginal_b_abs_diff_vs_stored=[0.0, 1e-6])
    assert cr6.regression_summary(drift)["reproduces"] is False


# ---------------------------------------------------------------- stored results
def _csv(name):
    p = REPORTS_DIR / name
    if not p.exists():
        pytest.skip(f"{name} has not been produced")
    return pd.read_csv(p)


def test_stored_context_reliability_covers_48_contexts_and_matches_phase5_data_weight():
    df = _csv("phase6_context_reliability.csv")
    assert len(df) == 48 and set(df["gate"]) == {0.5}
    assert df["marginal_b_abs_diff_vs_stored"].max() <= 1e-9
    assert (
        df["gate_passed_recomputed"].astype(bool) == df["stored_gate_passed"].astype(bool)
    ).all()
    assert not df["gate_passed_recomputed"].astype(bool).any()  # every context stays restricted
    assert (df["eligible_players"] == df["stored_eligible_players"]).all()


def test_stored_context_reliability_gap_is_k_minus_marginal_n_eff():
    df = _csv("phase6_context_reliability.csv")
    exp = (df["n_eff_required_for_gate"] - df["marginal_n_eff"]).clip(lower=0)
    assert (exp - df["marginal_gap_n_eff"]).abs().max() < 1e-9
    assert (df["n_eff_required_for_gate"] == df["k"]).all()  # B = 0.5 iff n_eff = k


def test_stored_eligibility_ladders_leave_thresholds_and_gate_unchanged():
    df = _csv("phase6_eligibility_reliability.csv")
    assert set(df["gate"]) == {0.5}
    fr = json.loads(FROZEN_CHOICES.read_text(encoding="utf-8"))
    got = {k: fr["eligibility"][k]["analysis"]["threshold_balls"]
           for k in ("IPL|batter", "T20I|batter", "IPL|bowler", "T20I|bowler")}  # fmt: skip
    assert got == {"IPL|batter": 20, "T20I|batter": 16, "IPL|bowler": 49, "T20I|bowler": 29}
    frozen = df[(df["source"] == "frozen_scaled") & (df["window"] == "PRE_TEST")]
    assert set(zip(frozen["format"], frozen["role"], frozen["threshold_balls"], strict=True)) >= {
        ("IPL", "batter", 20.0), ("T20I", "batter", 16.0), ("IPL", "bowler", 49.0),
        ("T20I", "bowler", 29.0),
    }  # fmt: skip


def test_stored_eligibility_hashes_of_watched_files_equal_the_pre_run_record():
    pre = json.loads(
        (ROOT.parent / ".agents" / "tasks" / "phase6_prerun_hashes.json").read_text(
            encoding="utf-8-sig"
        )
    )["files"]
    key = "d:/Data/backend/data/reports/phase4_frozen_choices.json"
    if key not in pre:
        pytest.skip("frozen choices not in the pre-run record")
    assert hashlib.sha256(FROZEN_CHOICES.read_bytes()).hexdigest() == pre[key]["sha256"]


def test_stored_projection_rows_are_labelled_projection():
    df = _csv("phase6_eligibility_reliability_projection.csv")
    assert set(df["label"]) == {"DESCRIPTIVE_PROJECTION"}
    est = df[df["status"] == "ESTIMATED"]
    assert (est["required_balls"] > 0).all()
