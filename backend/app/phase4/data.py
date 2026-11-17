"""Phase 4 data access: state frame with period, primary-scoring masks, row-preservation checks."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import duckdb
import pandas as pd

from app.analytics import pressure_features as pf
from app.phase4.constants import SCOPE
from app.phase4.split import Split, attach_period
from app.services.pressure_service import EXPLORATORY_DB, STATE_TABLE


def load_state(
    store_path: Path | str = EXPLORATORY_DB, extra_columns: Iterable[str] = ()
) -> pd.DataFrame:
    """Read the exploratory pre-delivery state read-only, in deterministic order."""
    cols = list(dict.fromkeys([*pf.STATE_COLS, *extra_columns]))
    con = duckdb.connect(str(store_path), read_only=True)
    try:
        df = con.execute(
            f"SELECT {', '.join(cols)} FROM {STATE_TABLE} "
            "ORDER BY match_id, innings_number, innings_ball_num"
        ).df()
    finally:
        con.close()
    df["match_date"] = pd.to_datetime(df["match_date"])
    return df


def load_state_with_period(
    split: Split, store_path: Path | str = EXPLORATORY_DB, extra_columns: Iterable[str] = ()
) -> pd.DataFrame:
    return attach_period(load_state(store_path, extra_columns), split)


def primary_mask(df: pd.DataFrame) -> pd.Series:
    """Rows that enter primary scoring. Exclusions are masks, never deletes."""
    return pf.add_populations(df)["base_pop"]


def with_primary_mask(df: pd.DataFrame) -> pd.DataFrame:
    """Return df plus ``in_primary_scoring``; asserts that no delivery row is dropped."""
    out = df.copy()
    out["in_primary_scoring"] = primary_mask(df).to_numpy()
    if len(out) != len(df):
        raise AssertionError("delivery rows must be preserved")
    return out


def in_scope(df: pd.DataFrame) -> pd.Series:
    return df["competition_type"].isin(SCOPE)
