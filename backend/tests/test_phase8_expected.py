"""Expected-outcome models: feature guard, leakage controls, OOF scoring, orientation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase8 import expected as ex
from app.phase8.data import FEATURE_COLS, FeatureLeakError, assert_feature_list_clean


def _frame(n_matches=40, per=30, seed=4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    mids = np.repeat(np.arange(1, n_matches + 1), per)
    n = len(mids)
    df = pd.DataFrame(
        {
            "match_id": mids,
            "period": np.where(mids <= 30, "TRAIN", "VALIDATION"),
            "innings_number": 1,
            "innings_phase": rng.choice(["powerplay", "middle", "death"], n),
            "wickets_remaining": rng.integers(1, 10, n),
            "legal_balls_bowled_before": rng.integers(1, 120, n),
            "striker_id": rng.integers(1, 8, n),
            "den_legal_inc": 1,
            "den_counts_as_ball_faced": 1,
            "ok_run_target": True,
            "ok_wicket_target": True,
            "out_batter_runs": rng.integers(0, 7, n),
            "out_is_four": False,
            "out_is_six": False,
            "out_is_wicket": rng.uniform(size=n) < 0.05,
            "den_bowler_charged_runs": rng.integers(0, 7, n),
            "den_bowler_credited_wicket": (rng.uniform(size=n) < 0.04).astype(int),
        }
    )
    df["out_dismissed_player_id"] = np.where(df["out_is_wicket"], df["striker_id"], pd.NA)
    df["out_dismissed_player_id"] = df["out_dismissed_player_id"].astype("Int64")
    return df


def test_feature_list_has_no_label_or_player_columns():
    assert_feature_list_clean(list(FEATURE_COLS))
    for bad in ("out_batter_runs", "den_legal_inc", "striker_id", "post_innings_total"):
        with pytest.raises(FeatureLeakError):
            assert_feature_list_clean([bad])


def test_features_are_row_wise_and_ignore_outcome_columns():
    df = _frame()
    x = ex.prepare_features(df, ex.category_codes(df))
    sub = df[df["match_id"] <= 10]
    xs = ex.prepare_features(sub, ex.category_codes(df))
    assert x.loc[sub.index].equals(xs)  # truncation: later rows cannot change an earlier row
    mut = df.copy()
    for c in (
        "out_batter_runs",
        "out_is_wicket",
        "den_bowler_charged_runs",
        "den_bowler_credited_wicket",
    ):
        mut[c] = 0
    assert ex.prepare_features(mut, ex.category_codes(df)).equals(x)  # mutation of the future
    assert list(x.columns) == list(FEATURE_COLS)
    assert x.isna().all(axis=0).sum() > 0 and not (x == 0).all().all()  # missing is not zero


def test_target_populations_and_labels():
    df = _frame()
    df.loc[0, "den_counts_as_ball_faced"] = 0
    df.loc[1, "ok_run_target"] = False
    y, pop = ex.target_frame(df, ex.spec_for("batter", "runs"))
    assert not pop[0] and not pop[1] and y.isna()[[0, 1]].all()
    yw, popw = ex.target_frame(df, ex.spec_for("batter", "wicket"))
    assert yw[popw].isin([0.0, 1.0]).all()
    yb, popb = ex.target_frame(df, ex.spec_for("bowler", "runs"))
    assert popb[0]  # a wide-like delivery stays in the charged-runs population


def test_oof_scoring_never_uses_the_scored_match_and_fits_on_train_only():
    df = _frame()
    x = ex.prepare_features(df, ex.category_codes(df))
    seen: list[set[int]] = []
    out_idx: list[set[int]] = []

    def fit(kind_model, kind, params, x_fit, y_fit):
        seen.append(set(df.loc[x_fit.index, "match_id"]))
        model = ex.Predictor("const", kind, float(np.mean(y_fit)))

        def pred(xx):
            out_idx.append(set(df.loc[xx.index, "match_id"]))
            return model(xx)

        return pred

    r = ex.score_target(df, x, ex.spec_for("batter", "runs"), fit=fit)
    assert all(m <= set(range(1, 31)) for m in seen)  # every fit set is TRAIN matches only
    folds = [(s, o) for s, o in zip(seen[-5:], out_idx[-5:], strict=True)]
    assert all(not (s & o) for s, o in folds)
    assert r["expected"].notna().sum() == r["pop"].sum()
    assert r["metrics"]["chosen"] in ("gbm", "const", "lookup")


def test_orientation_signs_and_missing_stays_missing():
    df = _frame()
    x = ex.prepare_features(df, ex.category_codes(df))
    r = ex.score_target(
        df, x, ex.spec_for("bowler", "runs"), fit=lambda *a: ex.Predictor("const", a[1], 1.0)
    )
    res = ex.oriented_residual(r, ex.spec_for("bowler", "runs"))
    assert np.allclose(res.dropna(), -(df["den_bowler_charged_runs"] - 1.0).loc[res.dropna().index])
    df2 = df.copy()
    df2.loc[3, "ok_run_target"] = False
    r2 = ex.score_target(df2, ex.prepare_features(df2, ex.category_codes(df2)), ex.spec_for("bowler", "runs"),
                         fit=lambda *a: ex.Predictor("const", a[1], 1.0))  # fmt: skip
    assert np.isnan(ex.oriented_residual(r2, ex.spec_for("bowler", "runs"))[3])
