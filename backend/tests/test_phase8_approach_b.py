"""Approach B glue (out-of-fold grouping, WPA regression, leverage weighting) and stored outputs."""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
import pytest

from app.phase8 import approach_b as ab
from app.phase8.constants import PHASE8_DB
from app.phase8.criteria import load_criteria


def _frame(n=600, seed=2):
    rng = np.random.default_rng(seed)
    m = rng.integers(1, 41, n)
    d = pd.DataFrame({
        "match_id": m, "period": np.where(m <= 30, "TRAIN", "VALIDATION"),
        "innings_number": 1 + (np.arange(n) % 2),
        "innings_phase": rng.choice(["powerplay", "middle", "death"], n),
        "striker_id": rng.integers(1, 20, n),
    })  # fmt: skip
    d["lev"] = rng.uniform(0, 0.1, n)
    d["exp"] = rng.uniform(0, 2, n)
    d["credit"] = 0.5 * d["lev"] + 0.01 * d["exp"] + rng.normal(0, 0.01, n)
    return d


def test_model_groups_cover_every_row_once_and_keep_train_folds_apart():
    d = _frame()
    groups = ab.model_groups(d)
    all_pos = np.concatenate([g[1] for g in groups])
    assert sorted(all_pos.tolist()) == list(range(len(d)))
    for label, pos, fold in groups:
        sub = d.iloc[pos]
        if fold is None:
            assert (sub["period"] == "VALIDATION").all() and label == "VALIDATION"
        else:
            assert (sub["period"] == "TRAIN").all() and (sub["match_id"] % 5 == fold).all()


def test_wpa_residual_is_out_of_fold_for_train_and_train_fit_for_validation():
    d = _frame()
    x = ab.design_matrix(d, d["lev"], d["exp"])
    res, coefs = ab.wpa_residuals(d, d["credit"], x)
    assert len(coefs) == 6 and res.notna().all()
    # a TRAIN row of fold f uses the fit that excludes fold f
    f = 2
    rows = d.index[(d["period"] == "TRAIN") & (d["match_id"] % 5 == f)]
    b = coefs[coefs["fit"] == f"FOLD_{f}"].iloc[0][list(x.columns)].to_numpy(dtype=float)
    expect = d.loc[rows, "credit"].to_numpy() - x.loc[rows].to_numpy() @ b
    assert np.allclose(res.loc[rows].to_numpy(), expect)
    # VALIDATION labels never enter any fit: changing them changes no coefficient
    d2 = d.assign(credit=np.where(d["period"] == "VALIDATION", d["credit"] + 5.0, d["credit"]))
    _, coefs2 = ab.wpa_residuals(d2, d2["credit"], x)
    pd.testing.assert_frame_equal(coefs, coefs2)


def test_missing_credit_gives_missing_residual_not_zero():
    d = _frame()
    credit = d["credit"].copy()
    credit.iloc[:25] = np.nan
    res, _ = ab.wpa_residuals(d, credit, ab.design_matrix(d, d["lev"], d["exp"]))
    assert res.iloc[:25].isna().all() and res.iloc[25:].notna().all()


def test_leverage_weighted_wpa_formula_and_missing_handling():
    d = pd.DataFrame({"striker_id": [1, 1, 1, 2, 2]})
    credit = pd.Series([0.1, -0.05, np.nan, 0.2, 0.0])
    lev = pd.Series([0.2, 0.1, 0.3, np.nan, 0.5])
    out = ab.leverage_weighted(d, "striker_id", credit, lev)
    assert out.loc[1, "lw_wpa_per_opp"] == pytest.approx((0.2 * 0.1 + 0.1 * -0.05) / 0.3)
    assert out.loc[1, "n_wpa_balls"] == 2
    assert out.loc[2, "n_wpa_balls"] == 1 and out.loc[2, "lw_wpa_per_opp"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------------------------
# stored outputs
# ---------------------------------------------------------------------------------------------
stored = pytest.mark.skipif(not PHASE8_DB.exists(), reason="phase8.duckdb not built")


def _table(name: str) -> pd.DataFrame:
    con = duckdb.connect(str(PHASE8_DB), read_only=True)
    try:
        has = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [name]
        ).fetchone()[0]
        if not has:
            pytest.skip(f"{name} not built")
        return con.execute(f"SELECT * FROM {name}").df()
    finally:
        con.close()


@stored
def test_stored_b_estimates_are_experimental_ranked_eligible_and_floor_labelled():
    est = _table("p8_b_estimates")
    crit = load_criteria()["eligibility"]
    assert set(est["status"]) == {"EXPERIMENTAL_NOT_VALIDATED"}
    comb = est[est["scope"] == "COMBINED"]
    for _, g in comb.groupby("role"):
        assert sorted(g["rank"].astype(int)) == list(range(1, len(g) + 1))
        assert (g["n_matches"] >= crit["min_matches"]).all()
        assert g["rank_basis"].isin(["REML_POSTERIOR", "UNSHRUNK_FLOOR"]).all()
        assert ((g["top_k_prob"] >= 0) & (g["top_k_prob"] <= 1)).all()
    assert est["criteria_sha256"].nunique() == 1


@stored
def test_stored_b_status_never_exceeds_exploratory_with_weak_reliability():
    status = _table("p8_b_status")
    cmp_ = _table("p8_b_intensity_comparison")
    assert set(status["indicative_list_status"]) == {"EXPLORATORY"}
    primary = cmp_[cmp_["is_primary"].astype(bool) & cmp_["split_half_sb"].notna()]
    assert (primary["split_half_sb"] < 0.5).all()


@stored
def test_stored_wp_metrics_beat_the_constant_and_record_the_gate():
    m = _table("p8_wp_metrics").set_index("model")
    for k in ("W1", "W2"):
        assert m.loc[k, "brier"] < m.loc[k, "brier_const"]
        assert m.loc[k, "log_loss"] < m.loc[k, "log_loss_const"]
        gate_ok = (0.8 <= m.loc[k, "slope"] <= 1.2) and m.loc[k, "brier_gain_vs_const"] >= 0.02
        assert bool(m.loc[k, "gate_passed"]) == gate_ok
    assert m.loc["W2", "brier_gain_vs_logit"] > 0  # beats the logistic baseline too


@stored
def test_stored_timeline_is_bounded_and_missing_is_not_zero():
    t = _table("p8_delivery_leverage")
    assert set(t["period"]) <= {"TRAIN", "VALIDATION"}  # TEST never loaded
    wb = t["wp_before"].dropna()
    assert wb.between(0.005, 0.995).all()
    assert t["leverage"].dropna().ge(0).all()
    ex = t[t["excluded_reason"] != ""]
    assert ex["wpa_d"].isna().all()  # excluded balls carry no WPA value
    # WPA of a ball is exactly WP_after - WP_before
    ok = t["wpa_d"].notna() & t["wp_after"].notna()
    assert np.allclose(t.loc[ok, "wpa_d"], (t.loc[ok, "wp_after"] - t.loc[ok, "wp_before"]))


@stored
def test_stored_wp_labels_exclude_super_over_and_dls_matches():
    lab = _table("p8_wp_label_exclusions")
    assert {34429, 45512, 40725}.issubset(set(lab["match_id"]))  # Super Over matches
    assert lab["reason"].notna().all()
    assert not lab["match_id"].duplicated().any()


@stored
def test_stored_validity_tests_cover_p1_p2_and_test_d():
    sel = _table("p8_b_intensity_selection")
    assert {"P1", "P2", "P4"} <= set(sel["candidate"])
    assert "test_d" in sel.columns
    assert not sel.loc[sel["candidate"] == "P0", "primary"].astype(bool).any()
    td = _table("p8_b_test_d")
    mech = td[td["candidate"].isin(["P1", "P2"]) & (td["status"] == "ESTIMATED")]
    assert mech["mechanical"].astype(bool).all()
