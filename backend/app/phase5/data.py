"""Phase 5 data loaders. TEST outcomes are never loaded.

``load_test_match_state_nonoutcome`` selects an explicit allow-list of identity columns for TEST
matches and refuses any column the Phase 4 split classes as an outcome (``out_``, ``den_``,
``post_innings_`` prefixes or ``residual`` in the name).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from app.phase4.split import Split
from app.services.pressure_service import EXPLORATORY_DB

TEST_STATE_COLUMNS = ("match_id", "innings_number", "innings_ball_num", "striker_id", "bowler_id")


class OutcomeColumnError(RuntimeError):
    """An outcome column was requested from the TEST period."""


def check_columns(columns: tuple[str, ...], split: Split | None = None) -> None:
    split = split or Split.from_config()
    bad = [c for c in columns if split.is_outcome_column(c)]
    if bad:
        raise OutcomeColumnError(f"outcome columns are not allowed for TEST rows: {bad}")


def load_test_match_state_nonoutcome(
    store_path: Path | str = EXPLORATORY_DB,
    columns: tuple[str, ...] = TEST_STATE_COLUMNS,
) -> pd.DataFrame:
    """Identity-only state rows of TEST matches (one row per delivery)."""
    check_columns(columns)
    cols = ", ".join(f"s.{c}" for c in columns)
    con = duckdb.connect(str(store_path), read_only=True)
    try:
        return con.execute(
            f"SELECT {cols} FROM exp_pre_delivery_state s "
            "JOIN p4_match_period p ON p.match_id = s.match_id WHERE p.period = 'TEST' "
            "ORDER BY s.match_id, s.innings_number, s.innings_ball_num"
        ).df()
    finally:
        con.close()
