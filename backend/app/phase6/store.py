"""Writer for p6_ tables in the exploratory store (never the official database).

``p6_run_log`` is append-only: the only write path is ``append_run_log`` (insert, no update, no
delete, no replace) and ``write_p6_table`` refuses that table name.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

from app.phase4.store import OFFICIAL_DB
from app.phase5.store import table_hashes  # noqa: F401  (re-exported for the Phase 6 scripts)
from app.phase6.constants import TABLE_PREFIX
from app.services.pressure_service import EXPLORATORY_DB, StoreError

_NAME = re.compile(r"^p6_[a-z0-9_]+$")
RUN_LOG = "p6_run_log"


def _check_store(store_path: Path | str, official_db: Path | str) -> Path:
    store, official = Path(store_path).resolve(), Path(official_db).resolve()
    if store == official:
        raise StoreError("the exploratory store must not be the official database")
    store.parent.mkdir(parents=True, exist_ok=True)
    return store


def write_p6_table(
    df: pd.DataFrame,
    table: str,
    store_path: Path | str = EXPLORATORY_DB,
    official_db: Path | str = OFFICIAL_DB,
) -> int:
    """Create or replace one p6_ table in the exploratory store. Returns the row count."""
    if not table.startswith(TABLE_PREFIX) or not _NAME.match(table):
        raise StoreError(f"only p6_ tables may be written, got '{table}'")
    if table == RUN_LOG:
        raise StoreError("p6_run_log is append-only; use append_run_log")
    store = _check_store(store_path, official_db)
    con = duckdb.connect(str(store))
    try:
        con.register("p6_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM p6_df")
        con.unregister("p6_df")
        return int(con.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
    finally:
        con.close()


def read_run_log(store_path: Path | str = EXPLORATORY_DB) -> pd.DataFrame:
    """All run-log rows ordered by ``seq`` (empty frame when the table does not exist)."""
    cols = ["seq", "step", "started_utc", "criteria_sha256", "config_sha256", "git_blob_sha"]
    if not Path(store_path).exists():
        return pd.DataFrame(columns=cols)
    con = duckdb.connect(str(store_path), read_only=True)
    try:
        has = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [RUN_LOG]
        ).fetchone()[0]
        if not has:
            return pd.DataFrame(columns=cols)
        return con.execute(f"SELECT * FROM {RUN_LOG} ORDER BY seq").df()
    finally:
        con.close()


def append_run_log(
    step: str,
    criteria_sha256: str,
    config_sha256: str,
    git_blob_sha: str,
    store_path: Path | str = EXPLORATORY_DB,
    official_db: Path | str = OFFICIAL_DB,
) -> int:
    """Insert one run-log row with ``seq = max + 1`` and return ``seq``. Never updates a row."""
    store = _check_store(store_path, official_db)
    con = duckdb.connect(str(store))
    try:
        con.execute(
            f"CREATE TABLE IF NOT EXISTS {RUN_LOG} (seq INTEGER PRIMARY KEY, step VARCHAR, "
            "started_utc TIMESTAMP, criteria_sha256 VARCHAR, config_sha256 VARCHAR, "
            "git_blob_sha VARCHAR)"
        )
        seq = int(con.execute(f"SELECT coalesce(max(seq), 0) + 1 FROM {RUN_LOG}").fetchone()[0])
        now = datetime.now(UTC).replace(tzinfo=None)
        con.execute(
            f"INSERT INTO {RUN_LOG} VALUES (?, ?, ?, ?, ?, ?)",
            [seq, step, now, criteria_sha256, config_sha256, git_blob_sha],
        )
        return seq
    finally:
        con.close()
