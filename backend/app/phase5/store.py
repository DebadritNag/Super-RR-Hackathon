"""Writer for p5_ tables in the exploratory store (never the official database)."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

from app.phase4.store import OFFICIAL_DB
from app.phase5.constants import TABLE_PREFIX
from app.services.pressure_service import EXPLORATORY_DB, StoreError

_NAME = re.compile(r"^p5_[a-z0-9_]+$")
_NAME_ANY = re.compile(r"^[a-z0-9_]+$")


def write_p5_table(
    df: pd.DataFrame,
    table: str,
    store_path: Path | str = EXPLORATORY_DB,
    official_db: Path | str = OFFICIAL_DB,
) -> int:
    """Create or replace one p5_ table in the exploratory store. Returns the row count."""
    if not table.startswith(TABLE_PREFIX) or not _NAME.match(table):
        raise StoreError(f"only p5_ tables may be written, got '{table}'")
    store, official = Path(store_path).resolve(), Path(official_db).resolve()
    if store == official:
        raise StoreError("the exploratory store must not be the official database")
    store.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(store))
    try:
        con.register("p5_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM p5_df")
        con.unregister("p5_df")
        return int(con.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
    finally:
        con.close()


def table_hashes(store_path: Path | str, prefix: str = "p4_") -> dict[str, str]:
    """SHA-256 of the content of every table whose name starts with ``prefix`` (read-only).

    Rows are read in ``ORDER BY ALL`` order and serialised as CSV, so the hash depends on content
    only and is the same across runs. Used to prove that Phase 4 tables are unchanged.
    """
    import hashlib

    con = duckdb.connect(str(store_path), read_only=True)
    try:
        names = [
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE starts_with(table_name, ?) ORDER BY table_name",
                [prefix],
            ).fetchall()
        ]
        out = {}
        for t in names:
            if not _NAME_ANY.match(t):
                continue
            df = con.execute(f"SELECT * FROM {t} ORDER BY ALL").df()
            out[t] = hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()
        return out
    finally:
        con.close()
