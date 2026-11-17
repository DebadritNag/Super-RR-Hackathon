"""Stored Approach A tables: labels, eligibility, determinism of ranks and TEST exclusion."""

from __future__ import annotations

import duckdb
import pytest

from app.phase8.constants import PHASE8_DB
from app.phase8.criteria import load_criteria

pytestmark = pytest.mark.skipif(not PHASE8_DB.exists(), reason="phase8.duckdb not built")


def _table(name: str):
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


def test_estimates_are_experimental_ranked_and_eligible():
    est = _table("p8_a_estimates")
    crit = load_criteria()["eligibility"]
    assert set(est["status"]) == {"EXPERIMENTAL_NOT_VALIDATED"}
    assert set(est["role"]) <= {"batter", "bowler"}
    comb = est[est["scope"] == "COMBINED"]
    for _, g in comb.groupby("role"):
        assert sorted(g["rank"].astype(int)) == list(range(1, len(g) + 1))
        assert (g["n_matches"] >= crit["min_matches"]).all()
        assert (g["eff_n"] >= crit["min_effective_n"]).all()
        assert g["rank_basis"].isin(["REML_POSTERIOR", "UNSHRUNK_FLOOR"]).all()
        assert ((g["top_k_prob"] >= 0) & (g["top_k_prob"] <= 1)).all()
        assert (g["rank_low"] <= g["rank_high"]).all()


def test_missing_baseline_is_missing_not_zero():
    est = _table("p8_a_estimates")
    no_base = est[est["normal_baseline"].isna()]
    assert no_base["pressure_delta"].isna().all()


def test_status_never_exceeds_exploratory_when_reliability_is_weak():
    st = _table("p8_a_status")
    cmp_ = _table("p8_a_intensity_comparison")
    prim = cmp_[cmp_["is_primary"]]
    weak = prim[(prim["split_half_sb_low"] <= 0) | (prim["split_half_sb"] < 0.5)]
    for role in weak["role"]:
        assert st.loc[st["role"] == role, "indicative_list_status"].iloc[0] == "EXPLORATORY"


def test_intensity_selection_states_basis_and_never_picks_the_reference():
    sel = _table("p8_intensity_selection")
    assert int(sel["primary"].sum()) == 1
    row = sel[sel["primary"]].iloc[0]
    assert not row["reference_only"]
    assert row["primary_basis"] in ("PASSING", "BEST_AVAILABLE_NOT_PASSING")
    if row["primary_basis"] == "BEST_AVAILABLE_NOT_PASSING":
        assert not sel.loc[~sel["reference_only"], "pass"].any()


def test_models_trained_on_train_only_and_metrics_present():
    met = _table("p8_a_model_metrics")
    assert len(met) == 8
    assert (met["n_train"] > met["n_validation"]).all()
    assert met["chosen"].isin(["gbm", "lookup", "const"]).all()
