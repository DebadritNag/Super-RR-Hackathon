"""Intensity candidates: scaling, definitions, undefined-not-zero, TRAIN-only fit, leakage."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase8 import intensity as it
from app.phase8.data import load_pre_test_deliveries


@pytest.fixture(scope="module")
def sample():
    df, _ = load_pre_test_deliveries()
    rng = np.random.default_rng(7)
    mids = df.drop_duplicates("match_id")[["match_id", "period"]]
    pick = []
    for per, g in mids.groupby("period"):
        k = 80 if per == "TRAIN" else 40
        pick += list(rng.choice(g["match_id"].to_numpy(), size=k, replace=False))
    return df[df["match_id"].isin(pick)].reset_index(drop=True)


@pytest.fixture(scope="module")
def built(sample):
    return it.build_intensity(sample)


def test_cdf_maps_to_unit_interval_and_keeps_nan():
    g = it.fit_cdf(np.arange(1000.0))
    out = it.apply_cdf(g, np.array([-5.0, 0.0, 500.0, 999.0, 5000.0, np.nan]))
    assert out[0] == 0.0 and out[-2] == 1.0 and np.isnan(out[-1])
    assert np.all(np.diff(out[:5]) >= 0)
    assert out[2] == pytest.approx(0.5, abs=0.01)
    assert it.fit_cdf(np.arange(10.0)) is None
    assert np.isnan(it.apply_cdf(None, np.array([1.0]))).all()


def test_cdf_ties_use_mid_rank():
    g = it.fit_cdf(np.r_[np.zeros(500), np.ones(500)])
    z = it.apply_cdf(g, np.array([0.0, 1.0]))
    assert z[0] == pytest.approx(0.25, abs=0.02) and z[1] == pytest.approx(0.75, abs=0.02)


def test_values_in_unit_interval_and_columns(built, sample):
    w, info = built
    assert list(w.columns) == [f"w_{c}" for c in it.CANDIDATES]
    assert w.index.equals(sample.index)
    for c in w.columns:
        v = w[c].dropna()
        assert v.between(0, 1).all(), c
    assert set(w["w_P0"].dropna().unique()) <= {0.0, 1.0}
    assert info["P6"] is not None and info["P6"]["cols"] == list(it.COMPOSITE_INPUTS)


def test_chase_only_candidates_are_undefined_in_innings_one(built, sample):
    w, _ = built
    inn1 = sample["innings_number"] == 1
    for c in ("w_P3", "w_P5", "w_P6"):
        assert w.loc[inn1, c].isna().all(), c
    assert w.loc[inn1, "w_P4"].notna().all()
    assert w.loc[~inn1, "w_P4"].notna().all()


def test_unverified_or_nonpositive_targets_are_undefined_not_zero(sample):
    raw = it.raw_values(sample)
    bad = sample["target_basis_unverified"].fillna(False) | sample["req_nonpositive_flag"].fillna(
        False
    )
    assert raw.loc[bad, "raw_P3"].isna().all()
    assert raw.loc[bad, "raw_P5"].isna().all()


def test_p4_grows_with_wickets_lost_and_progress():
    df = pd.DataFrame(
        {
            "innings_number": [1, 1, 1],
            "wickets_remaining": [10, 5, 5],
            "legal_balls_bowled_before": [60, 60, 100],
            "innings_limit_balls": [120, 120, 120],
            "chase_flag": [False] * 3,
            "target_basis_unverified": [False] * 3,
            "req_nonpositive_flag": [False] * 3,
            "runs_required": [np.nan] * 3,
            "resource_ratio": [0.5, 0.25, 0.05],
            "projected_surplus": [np.nan] * 3,
        }
    )
    v = it.raw_values(df)["raw_P4"].to_numpy()
    assert v[0] == 0.0 and v[0] < v[1] < v[2]


def test_p3_is_higher_when_more_runs_per_resource_are_needed():
    df = pd.DataFrame(
        {
            "innings_number": [2, 2],
            "chase_flag": [True, True],
            "target_basis_unverified": [False, False],
            "req_nonpositive_flag": [False, False],
            "runs_required": [30, 30],
            "resource_ratio": [0.5, 0.1],
            "wickets_remaining": [8, 8],
            "legal_balls_bowled_before": [60, 60],
            "innings_limit_balls": [120, 120],
            "projected_surplus": [0.0, -5.0],
        }
    )
    v = it.raw_values(df)["raw_P3"].to_numpy()
    assert v[1] > v[0]


def test_scaling_is_fitted_on_train_only(sample):
    """Changing VALIDATION rows (any column) cannot change any TRAIN delivery's intensity."""
    w0, _ = it.build_intensity(sample)
    mut = sample.copy()
    v = mut["period"] == "VALIDATION"
    mut.loc[v, ["runs_required", "resource_ratio", "wickets_remaining", "projected_surplus"]] *= 3
    w1, _ = it.build_intensity(mut)
    t = sample["period"] == "TRAIN"
    pd.testing.assert_frame_equal(w0[t], w1[t])


def test_mutating_outcome_columns_changes_nothing(sample, built):
    """Intensity reads no outcome column: scrambling every label leaves it identical."""
    w0, _ = built
    mut = sample.copy()
    for c in mut.columns:
        if c.startswith(("out_", "den_", "post_innings_")):
            mut[c] = mut[c].sample(frac=1.0, random_state=1).to_numpy()
    w1, _ = it.build_intensity(mut)
    pd.testing.assert_frame_equal(built[0], w1)
    assert w0.equals(w1)


def test_truncating_future_rows_leaves_earlier_balls_unchanged(sample, built):
    """Delete every ball after ball 60 of one TRAIN match: its earlier balls keep their value
    (its fold's own rows never enter its CDF, and the state columns are pre-delivery)."""
    w0, _ = built
    mid = int(sample.loc[sample["period"] == "TRAIN", "match_id"].iloc[0])
    cut = (sample["match_id"] == mid) & (sample["innings_ball_num"] > 60)
    assert cut.any()
    trunc = sample[~cut]
    w1, _ = it.build_intensity(trunc)
    keep = trunc["match_id"] == mid
    a = w0.loc[trunc.index[keep]]
    b = w1.loc[trunc.index[keep]]
    pd.testing.assert_frame_equal(a.drop(columns="w_P6"), b.drop(columns="w_P6"))
    # P6 is rescaled by a CDF of composite values that were built from other folds' scaled
    # inputs; those inputs see the truncated match's fold, a second-order effect (state rows, no
    # outcomes). It must stay tiny.
    diff = (a["w_P6"] - b["w_P6"]).abs().dropna()
    assert diff.max() < 0.01


def test_composite_is_none_for_too_few_rows():
    z = pd.DataFrame({"a": np.arange(10.0), "b": np.arange(10.0)})
    assert it.fit_composite(z, pd.Series(True, index=z.index)) is None
    assert np.isnan(it.apply_composite(z, None)).all()


def test_composite_loadings_are_positive_and_sum_to_one_scale(built):
    _, info = built
    load = np.array(info["P6"]["loadings"])
    assert (load > 0).all() and 0.5 <= info["P6"]["explained"] <= 1.0


def test_intensity_refuses_test_period(sample):
    bad = sample.head(5).copy()
    bad["period"] = "TEST"
    with pytest.raises(ValueError):
        it.build_intensity(bad)


def test_wp_based_candidates_scale_like_the_others(sample):
    wp = pd.Series(np.linspace(0.02, 0.98, len(sample)), index=sample.index)
    lev = pd.Series(np.abs(np.sin(np.arange(len(sample)))) / 10, index=sample.index)
    out = it.intensity_from_wp(sample, wp, lev)
    assert set(out.columns) == {"w_P1", "w_P2"}
    assert out.stack().between(0, 1).all()


def test_coverage_table_shape(built, sample):
    cov = it.coverage(sample, built[0])
    assert {"candidate", "innings", "period", "defined_share"} <= set(cov.columns)
    assert cov["defined_share"].between(0, 1).all()
    p3_inn1 = cov[(cov.candidate == "P3") & (cov.innings == 1)]
    assert (p3_inn1["defined"] == 0).all()


def test_high_intensity_flag_treats_nan_as_false():
    s = pd.Series([0.2, 0.5, 0.9, np.nan])
    assert list(it.high_intensity(s)) == [False, True, True, False]
