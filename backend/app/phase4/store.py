"""Writer for the exploratory analytical store (p4_ tables only, never the official DB)."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

from app.core.config import BACKEND_ROOT
from app.phase4.constants import TABLE_PREFIX
from app.services.pressure_service import EXPLORATORY_DB, StoreError

OFFICIAL_DB = BACKEND_ROOT / "data" / "database" / "superr.duckdb"
_NAME = re.compile(r"^p4_[a-z0-9_]+$")


def write_p4_table(
    df: pd.DataFrame,
    table: str,
    store_path: Path | str = EXPLORATORY_DB,
    official_db: Path | str = OFFICIAL_DB,
) -> int:
    """Create or replace one p4_ table in the exploratory store. Returns the row count."""
    if not table.startswith(TABLE_PREFIX) or not _NAME.match(table):
        raise StoreError(f"only p4_ tables may be written, got '{table}'")
    store, official = Path(store_path).resolve(), Path(official_db).resolve()
    if store == official:
        raise StoreError("the exploratory store must not be the official database")
    store.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(store))
    try:
        con.register("p4_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM p4_df")
        con.unregister("p4_df")
        return int(con.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
    finally:
        con.close()
