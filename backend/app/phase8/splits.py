"""Chronological, match-level splits for Phase 8 (reuses the Phase 4 split configuration).

Matches are never split between partitions or folds. Folds are ``match_id % 5`` (deterministic).
TEST is never loaded; ``assert_pre_test`` refuses any frame that contains it.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.phase4.split import Split, SplitIntegrityError, assign_matches
from app.phase8.constants import N_FOLDS, PRE_TEST_PERIODS
from app.phase8.lockguard import assert_no_test_rows


def load_split() -> Split:
    """The frozen Phase 4 split (TRAIN to 2024-12-31, VALIDATION 2025, TEST 2026+)."""
    return Split.from_config()


def fold_of(match_ids: pd.Series | list[int]) -> pd.Series:
    """Deterministic fold of each match (never Python's randomised ``hash``)."""
    return pd.Series(match_ids, dtype="int64") % N_FOLDS


def fit_group(df: pd.DataFrame) -> pd.Series:
    """Model-fit group of each row: ``fit_group`` (Phase 9) or else ``period`` (Phase 8)."""
    return df["fit_group"] if "fit_group" in df.columns else df["period"]


def assert_pre_test(df: pd.DataFrame) -> pd.DataFrame:
    """Refuse a frame with a TEST period or a period outside TRAIN and VALIDATION."""
    assert_no_test_rows(df)
    if "period" not in df.columns:
        raise SplitIntegrityError("frame has no 'period' column; cannot prove it excludes TEST")
    bad = set(df["period"].astype(str).unique()) - set(PRE_TEST_PERIODS)
    if bad:
        raise SplitIntegrityError(f"unexpected periods {sorted(bad)}")
    return df


def check_match_partition(df: pd.DataFrame, split: Split | None = None) -> dict[str, Any]:
    """Integrity of a delivery-level frame: one period per match, chronological periods.

    Raises ``SplitIntegrityError`` on a straddling match or overlapping period dates.
    """
    sp = split or load_split()
    per_match = df.groupby("match_id")["period"].nunique()  # Phase 9: relabelled, still one each
    if (per_match > 1).any():
        raise SplitIntegrityError(
            f"matches in more than one period: {per_match[per_match > 1].index.tolist()[:5]}"
        )
    src = "period_src" if "period_src" in df.columns else "period"
    expected = assign_matches(df, sp).set_index("match_id")["period"]
    got = df.drop_duplicates("match_id").set_index("match_id")[src]
    if not (expected.reindex(got.index) == got).all():
        raise SplitIntegrityError("period labels disagree with the split dates")
    bounds = df.groupby("period")["match_date"].agg(["min", "max"])
    if {"TRAIN", "VALIDATION"} <= set(bounds.index):
        if not bounds.loc["TRAIN", "max"] < bounds.loc["VALIDATION", "min"]:
            raise SplitIntegrityError("TRAIN and VALIDATION dates overlap")
    counts = df.drop_duplicates("match_id").groupby("period").size().to_dict()
    return {"matches_per_period": {k: int(v) for k, v in counts.items()}, "ok": True}


def training_mask(df: pd.DataFrame) -> pd.Series:
    """Rows a model may be fitted on: TRAIN only."""
    return df["period"] == "TRAIN"


def assert_fit_on_train(fit_match_ids: pd.Series | list[int], df: pd.DataFrame) -> None:
    """Raise unless every match used for fitting is a TRAIN match of ``df``."""
    train = set(df.loc[fit_group(df) == "TRAIN", "match_id"].unique())
    extra = set(pd.Series(fit_match_ids).unique()) - train
    if extra:
        raise SplitIntegrityError(f"model fitted on non-TRAIN matches: {sorted(extra)[:5]}")


def oof_assignment(df: pd.DataFrame) -> pd.Series:
    """Fold for every delivery; a delivery's model must be fitted on the other folds only."""
    return fold_of(df["match_id"]).set_axis(df.index)
