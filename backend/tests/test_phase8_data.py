"""Phase 8 data layer on the real stores (read-only) and on synthetic frames."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase8 import data as d
from app.phase8.constants import RESTRICTED_MATCH_IDS
from app.phase8.splits import assert_pre_test, check_match_partition


@pytest.fixture(scope="module")
def loaded():
    return d.load_pre_test_deliveries()


def test_no_test_rows_and_matches_stay_in_one_period(loaded):
    df, _ = loaded
    assert set(df["period"].unique()) == {"TRAIN", "VALIDATION"}
    assert_pre_test(df)
    out = check_match_partition(df)
    assert out["ok"]
    assert df["match_date"].max() <= pd.Timestamp("2025-12-31")


def test_scope_and_innings_rules(loaded):
    df, _ = loaded
    assert set(df["competition_type"].unique()) <= {"IPL", "T20I"}
    assert set(df["innings_number"].unique()) <= {1, 2}
    assert df["dls_exclude_primary"].fillna(False).eq(False).all()
    assert df["regulation_pressure_eligible"].all()
    assert not df["format_out_of_scope"].fillna(False).any()
    # restricted matches never contribute innings 3 or 4
    sub = df[df["match_id"].isin(RESTRICTED_MATCH_IDS)]
    assert sub["innings_number"].isin([1, 2]).all()


def test_exclusions_are_counted_with_real_reasons(loaded):
    _, excl = loaded
    reasons = set(excl["reason"])
    assert "OUT_OF_SCOPE_COMPETITION" in reasons
    assert "DLS_NOT_RECONSTRUCTABLE" in reasons
    assert (excl["rows"] > 0).all()


def test_metric_level_flags_do_not_drop_rows(loaded):
    df, excl = loaded
    m = excl.set_index("reason")["rows"]
    assert int((~df["ok_wicket_target"]).sum()) == int(m["METRIC_WICKET_FLAG_ANOMALY"])
    assert int((~df["ok_run_target"]).sum()) == int(m["METRIC_EXTRAS_LABEL_UNVERIFIED"])
    # flagged rows are still present in the frame
    assert (~df["ok_wicket_target"]).any() or m["METRIC_WICKET_FLAG_ANOMALY"] == 0


def test_missing_is_never_zero(loaded):
    df, _ = loaded
    first = df["legal_balls_bowled_before"] == 0
    assert df.loc[first, "projected_total"].isna().all()
    assert df["par_prior"].isna().any()  # insufficient prior history stays NULL
    zero = df["par_prior"] == 0  # a genuine zero par exists only before the first ball
    assert (df.loc[zero, "legal_balls_bowled_before"] == 0).all()
    assert df["rrr"].isna().any() and df.loc[df["innings_number"] == 1, "rrr"].isna().all()


def test_team_priors_exist_but_are_null_without_history(loaded):
    df, _ = loaded
    assert df["bat_team_prior"].notna().mean() > 0.8
    assert df["bat_team_prior"].dropna().between(0, 1).all()
    assert df["bowl_team_prior"].isna().any()


def test_feature_list_is_clean():
    assert d.assert_feature_list_clean(d.FEATURE_COLS) == d.FEATURE_COLS
    for bad in ("out_batter_runs", "den_legal_inc", "post_innings_wickets", "striker_id",
                "bowler_id", "match_id", "batter_residual", "not_a_feature"):  # fmt: skip
        with pytest.raises(d.FeatureLeakError):
            d.assert_feature_list_clean([*d.FEATURE_COLS[:3], bad])


def test_feature_whitelist_excludes_labels_flags_and_ids():
    f = set(d.FEATURE_COLS)
    assert not f & set(d.LABEL_COLS)
    assert not f & set(d.FLAG_COLS)
    assert not f & {"striker_id", "non_striker_id", "bowler_id", "match_id"}
    assert not any(c.startswith(("out_", "den_", "post_innings_")) for c in f)


def _matches(rows):
    return pd.DataFrame(
        rows, columns=["match_id", "match_date", "home_team_id", "away_team_id", "win_team_id"]
    )


def test_team_priors_use_strictly_earlier_decisive_matches():
    m = _matches(
        [
            (1, "2024-01-01", 10, 20, 10),
            (2, "2024-01-02", 10, 30, 30),
            (3, "2024-01-02", 10, 20, 20),  # same date as match 2: not in its history
            (4, "2024-01-05", 10, 20, None),  # no result: never counts as history
            (5, "2024-01-09", 10, 20, 10),
        ]
    )
    p = d.compute_team_priors(m).set_index(["match_id", "team_id"])["prior_win_rate"]
    assert np.isnan(p[(1, 10)])
    assert p[(2, 10)] == pytest.approx((1 + 2.5) / (1 + 5))
    assert p[(3, 10)] == pytest.approx((1 + 2.5) / (1 + 5))  # match 2 same date excluded
    assert p[(5, 10)] == pytest.approx((1 + 0 + 0 + 2.5) / (3 + 5))  # matches 1,2,3 (not 4)


def test_team_priors_ignore_the_match_itself_and_the_future():
    base = _matches(
        [
            (1, "2024-01-01", 10, 20, 10),
            (2, "2024-02-01", 10, 20, 20),
            (3, "2024-03-01", 10, 20, 10),
        ]
    )
    p0 = d.compute_team_priors(base)
    mut = base.copy()
    mut.loc[mut["match_id"] >= 2, "win_team_id"] = [10, 20]  # change the result of match 2 and 3
    mut.loc[mut["match_id"] == 2, "win_team_id"] = 10
    p1 = d.compute_team_priors(mut)
    a = p0[p0["match_id"] <= 2].set_index(["match_id", "team_id"])["prior_win_rate"]
    b = p1[p1["match_id"] <= 2].set_index(["match_id", "team_id"])["prior_win_rate"]
    pd.testing.assert_series_equal(a, b)  # prior of match 2 does not see match 2's result


def test_team_priors_reject_missing_columns():
    with pytest.raises(ValueError):
        d.compute_team_priors(pd.DataFrame({"match_id": [1]}))
