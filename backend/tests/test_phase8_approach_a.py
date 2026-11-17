"""Approach A: intensity rule, units, eligibility, evidence classes, status, bootstrap, cell run."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase8 import approach_a as aa
from app.phase8.criteria import load_criteria


@pytest.fixture(scope="module")
def crit():
    return load_criteria()


def _deliveries(n_players=40, n_matches=60, per=18, seed=5):
    rng = np.random.default_rng(seed)
    skill = rng.normal(0, 0.15, n_players)
    rows = []
    for m in range(1, n_matches + 1):
        date = pd.Timestamp("2023-01-01") + pd.Timedelta(days=3 * m)
        fmt = "IPL" if m % 3 else "T20I"
        for k in range(per):
            p = int(rng.integers(0, n_players))
            rows.append(
                {
                    "match_id": m,
                    "innings_number": 1 + (k % 2),
                    "innings_phase": "death",
                    "match_date": date,
                    "competition_type": fmt,
                    "period": "TRAIN" if m <= 45 else "VALIDATION",
                    "striker_id": p,
                    "bowler_id": 100 + int(rng.integers(0, 15)),
                    "den_counts_as_ball_faced": 1,
                    "den_legal_inc": 1,
                    "res": skill[p] + rng.normal(0, 1),
                    "w": float(rng.uniform(0, 1)),
                }
            )
    d = pd.DataFrame(rows)
    return d, d["w"], d["res"]


def test_final_intensity_uses_p4_only_where_innings2_only_candidate_is_undefined():
    w = pd.DataFrame({"w_P3": [np.nan, 0.8], "w_P4": [0.6, 0.1]})
    s, info = aa.final_intensity(w, "P3")
    assert s.tolist() == [0.6, 0.8] and info["innings1_fallback"] == "P4"
    s4, info4 = aa.final_intensity(w, "P4")
    assert s4.tolist() == [0.6, 0.1] and info4["innings1_fallback"] is None


def test_pressure_units_only_keep_intensity_at_least_half_and_never_zero_fill():
    d, w, r = _deliveries()
    r = r.copy()
    r.iloc[:50] = np.nan
    u = aa.pressure_units(d, "batter", w, r)
    assert (u["w"] > 0).all() and (u["mean_intensity"] >= 0.5).all()
    assert (u["prec"] <= u["n_balls"] + 1e-9).all() and (u["prec"] > 0).all()
    assert u["y"].notna().all()


def test_format_centring_removes_format_means():
    d, w, r = _deliveries()
    u, mu = aa.centre_by_format(aa.pressure_units(d, "batter", w, r))
    for f, g in u.groupby("competition_type"):
        assert np.average(g["y"], weights=g["prec"]) == pytest.approx(0.0, abs=1e-9)
    assert set(mu) == {"IPL", "T20I"}


def test_eligibility_uses_each_predeclared_floor(crit):
    e = crit["eligibility"]
    base = {"n_matches": e["min_matches"], "eff_n": e["min_effective_n"], "balls": e["min_balls_faced"],
            "hi_units": e["min_high_intensity_units"]}  # fmt: skip
    c = pd.DataFrame([base, {**base, "n_matches": 7}, {**base, "eff_n": 59}, {**base, "balls": 59},
                      {**base, "hi_units": 7}])  # fmt: skip
    assert aa.eligible_players(c, "batter", crit).tolist() == [True, False, False, False, False]
    assert aa.eligible_players(c, "batter", crit, 0.5).all()
    assert not aa.eligible_players(c.assign(balls=71), "bowler", crit).iloc[0]


def test_evidence_class_order_is_first_match_wins():
    est = pd.DataFrame(
        {"eligible": [False, True, True, True, True, True],
         "ci_low": [1.0, 1.0, 0.5, -0.1, -0.2, -0.5],
         "n_matches": [3, 30, 30, 10, 9, 8],
         "pos_share": [0.9, 0.3, 0.7, 0.6, 0.6, 0.5],
         "disp": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
         "estimate": [1.0, 1.0, 0.9, 1.2, 0.9, -1.0]}
    )  # fmt: skip
    got = aa.evidence_class(est, 8).tolist()
    assert got[0] == "INSUFFICIENT"
    assert got[1] == "INCONSISTENT"
    assert got[2] == "STRONG_SUBSTANTIAL"
    assert got[3] == "STRONG_LIMITED"
    assert got[5] == "UNCLASSIFIED_LOW"


def test_floor_or_weak_reliability_can_never_be_provisional_or_validated(crit):
    st = aa.list_status(crit, 0.9, 0.8, 0.6, True, 50, 50, 50)
    assert st["status"] == "EXPLORATORY" and "floor" in st["reason"]
    st = aa.list_status(crit, 0.37, 0.2, 0.3, False, 50, 50, 50)
    assert st["status"] == "EXPLORATORY"
    st = aa.list_status(crit, 0.6, 0.55, 0.2, False, 50, 50, 50)
    assert st["status"] == "PROVISIONAL"
    st = aa.list_status(crit, 0.8, 0.6, 0.4, False, 50, 50, 50)
    assert st["status"] == "VALIDATED"
    assert (
        aa.list_status(crit, 0.8, 0.6, 0.4, False, 5, 50, 50)["status"] == "INSUFFICIENT_EVIDENCE"
    )
    assert aa.list_status(crit, 0.8, 0.6, 0.4, False, 50, 10, 50)["status"] == "EXPLORATORY"


def test_bootstrap_is_seeded_and_match_clustered():
    d, _, _ = _deliveries()
    b1, b2 = aa.Boot(d, 50), aa.Boot(d, 50)
    assert (b1.counts == b2.counts).all()
    assert b1.counts.sum(axis=1).min() == len(
        b1.mids
    )  # each draw resamples every match once on average
    per = d.drop_duplicates("match_id").sort_values("match_id")["period"].to_numpy()
    for p in ("TRAIN", "VALIDATION"):
        assert (b1.counts[:, per == p].sum(axis=1) == (per == p).sum()).all()  # strata preserved


def test_run_cell_end_to_end_on_synthetic_data(crit):
    d, w, r = _deliveries()
    small = {**crit, "eligibility": {**crit["eligibility"], "min_matches": 4, "min_effective_n": 20,
                                     "min_balls_faced": 20, "min_high_intensity_units": 3,
                                     "min_matches_2025_window": 2, "min_players_out_of_time": 5,
                                     "min_players_split_half": 5}}  # fmt: skip
    deliv = aa.player_counts(d, "batter", w, r)
    cell = aa.run_cell(d, deliv, "batter", w, r, small, aa.Boot(d, 100), 1.0, True, 50)
    comb = cell["scopes"]["COMBINED"]
    assert len(comb["players"]) >= 10 and "fit" in comb
    ranks = comb["rank"].dropna().sort_values()
    assert ranks.iloc[0] == 1 and ranks.is_unique
    st = comb["boot"]["stability"]
    assert ((st["top_k_prob"] >= 0) & (st["top_k_prob"] <= 1)).all()
    assert (st["rank_low"] <= st["rank_high"]).all()
    assert (comb["fit"]["players"]["theta"].notna()).all()
    assert comb["reliability"]["parity"]["n_players"] >= 3
    assert (st["boot_method"] == "FULL_REFIT").all()
    assert comb["boot"]["check"]["draws"] == 100 and comb["boot"]["check"]["max_abs_gap"] >= 0
    est = aa.refit_draws(comb["units"], comb["players"], aa.Boot(d, 30), 10)
    assert est.shape == (10, len(comb["players"])) and np.isfinite(est).any()
    ov = aa.overlap_row(comb["rank"], comb["rank"])
    assert ov["top10_overlap"] == 10 and ov["spearman"] == pytest.approx(1.0)
