"""Thin DuckDB connection abstraction.

All persistence goes through `Database`, so a later PostgreSQL backend only has to replace this
module and the SQL builders in `app.data_pipeline.csv_loader`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "data" / "audit" / "phase2_schema.sql"
PERSISTENT_MARKER = "-- ==== PERSISTENT ===="
REPLACEABLE_MARKER = "-- ==== REPLACEABLE ===="

# Child-first drop order of the replaceable data layer.
REPLACEABLE_TABLES: tuple[str, ...] = (
    "ball_by_ball_comparison_detail",
    "ball_by_ball_comparison",
    "match_reconciliation",
    "deliveries",
    "innings",
    "match_squads",
    "matches",
    "player_competition_mapping",
    "players",
    "venues",
    "competition_teams",
    "teams",
    "competitions",
    "raw_ball_by_ball_updated",
    "raw_ball_by_ball",
)


def split_statements(sql: str) -> list[str]:
    """Split DDL text on ';' after removing full-line and trailing `--` comments."""
    lines = []
    for line in sql.splitlines():
        if "--" in line:
            line = line.split("--", 1)[0]
        lines.append(line)
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def schema_text(path: Path = SCHEMA_SQL) -> str:
    return path.read_text(encoding="utf-8")


def ddl_sha256(path: Path = SCHEMA_SQL) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blocks(text: str) -> tuple[str, str]:
    head, _, rest = text.partition(PERSISTENT_MARKER)
    persistent, _, replaceable = rest.partition(REPLACEABLE_MARKER)
    return persistent, replaceable


class Database:
    """A DuckDB connection with explicit transaction control and schema helpers."""

    def __init__(self, path: Path | str, read_only: bool = False) -> None:
        self.path = str(path)
        if self.path != ":memory:" and not read_only:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(self.path, read_only=read_only)

    def execute(self, sql: str, params: list | None = None) -> duckdb.DuckDBPyConnection:
        return self.con.execute(sql, params) if params is not None else self.con.execute(sql)

    def query(self, sql: str, params: list | None = None) -> list[tuple]:
        return self.execute(sql, params).fetchall()

    def scalar(self, sql: str, params: list | None = None):
        row = self.execute(sql, params).fetchone()
        return None if row is None else row[0]

    @contextmanager
    def transaction(self) -> Iterator[Database]:
        """BEGIN ... COMMIT; any exception rolls back and is re-raised."""
        self.con.execute("BEGIN TRANSACTION")
        try:
            yield self
        except BaseException:
            self.con.execute("ROLLBACK")
            raise
        else:
            self.con.execute("COMMIT")

    def table_exists(self, name: str) -> bool:
        return bool(
            self.scalar(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [name]
            )
        )

    def apply_persistent_schema(self, path: Path = SCHEMA_SQL) -> None:
        for stmt in split_statements(_blocks(schema_text(path))[0]):
            self.con.execute(stmt)

    def drop_replaceable(self) -> None:
        for table in REPLACEABLE_TABLES:
            self.con.execute(f"DROP TABLE IF EXISTS {table}")

    def create_replaceable(self, path: Path = SCHEMA_SQL) -> None:
        for stmt in split_statements(_blocks(schema_text(path))[1]):
            self.con.execute(stmt)

    def close(self) -> None:
        self.con.close()


def connect(path: Path | str, read_only: bool = False) -> Database:
    return Database(path, read_only=read_only)
