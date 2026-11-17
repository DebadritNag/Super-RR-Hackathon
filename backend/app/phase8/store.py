"""Writer for p8_ tables in ``phase8.duckdb`` (never the official or the exploratory database).

``p8_run_log`` is append-only: the only write path is ``append_run_log``. ``write_p8_table`` refuses
that table, refuses any write until the criteria were declared (run-log ``seq = 1`` is a ``plan``
row) and stamps ``criteria_sha256`` and ``run_seq`` on every result table.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

from app.phase8.constants import EXPLORATORY_DB, OFFICIAL_DB, PHASE8_DB, TABLE_PREFIX
from app.services.pressure_service import StoreError

RUN_LOG = "p8_run_log"
_NAME = re.compile(r"^p8_[a-z0-9_]+$")
LOG_COLS = ["seq", "step", "ts", "criteria_sha256", "git_sha", "inputs_hash", "note"]


def _check_store(store_path: Path | str) -> Path:
    store = Path(store_path).resolve()
    if store in (Path(OFFICIAL_DB).resolve(), Path(EXPLORATORY_DB).resolve()):
        raise StoreError("phase 8 tables are never written to the official or exploratory database")
    store.parent.mkdir(parents=True, exist_ok=True)
    return store


def read_run_log(store_path: Path | str = PHASE8_DB) -> pd.DataFrame:
    """All run-log rows ordered by ``seq`` (empty frame when the table does not exist)."""
    if not Path(store_path).exists():
        return pd.DataFrame(columns=LOG_COLS)
    con = duckdb.connect(str(store_path), read_only=True)
    try:
        has = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [RUN_LOG]
        ).fetchone()[0]
        if not has:
            return pd.DataFrame(columns=LOG_COLS)
        return con.execute(f"SELECT * FROM {RUN_LOG} ORDER BY seq").df()
    finally:
        con.close()


def append_run_log(
    step: str,
    criteria_sha256: str,
    git_sha: str = "",
    inputs_hash: str = "",
    note: str = "",
    store_path: Path | str = PHASE8_DB,
) -> int:
    """Insert one run-log row with ``seq = max + 1`` and return ``seq``. Never updates a row."""
    store = _check_store(store_path)
    con = duckdb.connect(str(store))
    try:
        con.execute(
            f"CREATE TABLE IF NOT EXISTS {RUN_LOG} (seq INTEGER PRIMARY KEY, step VARCHAR, "
            "ts TIMESTAMP, criteria_sha256 VARCHAR, git_sha VARCHAR, inputs_hash VARCHAR, "
            "note VARCHAR)"
        )
        seq = int(con.execute(f"SELECT coalesce(max(seq), 0) + 1 FROM {RUN_LOG}").fetchone()[0])
        now = datetime.now(UTC).replace(tzinfo=None)
        con.execute(
            f"INSERT INTO {RUN_LOG} VALUES (?, ?, ?, ?, ?, ?, ?)",
            [seq, step, now, criteria_sha256, git_sha, inputs_hash, note],
        )
        return seq
    finally:
        con.close()


def write_p8_table(df: pd.DataFrame, table: str, store_path: Path | str = PHASE8_DB) -> int:
    """Create or replace one p8_ table. Needs the declared criteria (run-log seq 1 = plan)."""
    if not table.startswith(TABLE_PREFIX) or not _NAME.match(table):
        raise StoreError(f"only p8_ tables may be written, got '{table}'")
    if table == RUN_LOG:
        raise StoreError("p8_run_log is append-only; use append_run_log")
    log = read_run_log(store_path)
    if len(log) == 0 or int(log.iloc[0]["seq"]) != 1 or log.iloc[0]["step"] != "plan":
        raise StoreError("results cannot be written before the criteria are declared (plan row)")
    store = _check_store(store_path)
    out = df.copy()
    if "criteria_sha256" not in out.columns:
        out["criteria_sha256"] = log.iloc[0]["criteria_sha256"]
    if "run_seq" not in out.columns:
        out["run_seq"] = int(log.iloc[-1]["seq"])
    con = duckdb.connect(str(store))
    try:
        con.register("p8_df", out)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM p8_df")
        con.unregister("p8_df")
        return int(con.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
    finally:
        con.close()
