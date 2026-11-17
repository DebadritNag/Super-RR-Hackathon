"""Schema and replace-strategy regression tests (in-memory DuckDB)."""

from __future__ import annotations

import duckdb
import pytest

from app.core.database import REPLACEABLE_TABLES, connect, split_statements


def fresh():
    db = connect(":memory:")
    db.apply_persistent_schema()
    db.create_replaceable()
    return db


def test_schema_applies_and_creates_every_replaceable_table() -> None:
    db = fresh()
    for table in REPLACEABLE_TABLES:
        assert db.table_exists(table), table
    for table in ("ingestion_runs", "ingestion_errors", "dataset_lineage", "data_quality_results"):
        assert db.table_exists(table), table
    assert db.table_exists("model_versions") and db.table_exists("metric_definitions")


def test_no_super_over_column_anywhere() -> None:
    db = fresh()
    n = db.scalar(
        "SELECT count(*) FROM information_schema.columns WHERE column_name ILIKE '%super%'"
    )
    assert n == 0


def test_foreign_keys_are_enforced() -> None:
    db = fresh()
    db.execute(
        "INSERT INTO competitions VALUES (1, 'IPL 2024', 'T20', '2024', 'IPL', 'c.csv', 1, 1)"
    )
    with pytest.raises(duckdb.ConstraintException):
        db.execute("INSERT INTO competition_teams VALUES (1, 99, 'X', 't.csv', 1, 1)")
    with pytest.raises(duckdb.ConstraintException):
        db.execute("INSERT INTO competition_teams VALUES (2, 99, 'X', 't.csv', 1, 1)")


def test_replace_inside_transaction_is_restored_on_rollback() -> None:
    db = fresh()
    db.execute(
        "INSERT INTO competitions VALUES (1, 'IPL 2024', 'T20', '2024', 'IPL', 'c.csv', 1, 1)"
    )
    db.execute("INSERT INTO teams VALUES (1, 'A', 't.csv', 1, 1)")
    db.execute("INSERT INTO competition_teams VALUES (1, 1, 'A', 't.csv', 1, 1)")
    with pytest.raises(RuntimeError):
        with db.transaction():
            db.drop_replaceable()
            db.create_replaceable()
            db.execute(
                "INSERT INTO competitions VALUES (2, 'X', 'T20', '2024', 'OTHER_T20', 'c.csv', 1, 1)"
            )
            raise RuntimeError("boom")
    assert db.query("SELECT comp_id FROM competitions") == [(1,)]
    assert db.scalar("SELECT count(*) FROM competition_teams") == 1


def test_replace_inside_transaction_is_visible_after_commit() -> None:
    db = fresh()
    db.execute(
        "INSERT INTO competitions VALUES (1, 'IPL 2024', 'T20', '2024', 'IPL', 'c.csv', 1, 1)"
    )
    db.execute("INSERT INTO teams VALUES (1, 'A', 't.csv', 1, 1)")
    db.execute("INSERT INTO competition_teams VALUES (1, 1, 'A', 't.csv', 1, 1)")
    with db.transaction():
        db.drop_replaceable()
        db.create_replaceable()
        db.execute(
            "INSERT INTO competitions VALUES (2, 'X', 'T20', '2024', 'OTHER_T20', 'c.csv', 1, 1)"
        )
    assert db.query("SELECT comp_id FROM competitions") == [(2,)]
    assert db.scalar("SELECT count(*) FROM competition_teams") == 0


def test_delete_then_insert_of_referenced_parent_fails_documenting_strategy_choice() -> None:
    """DuckDB cannot DELETE+INSERT an FK-referenced parent in one transaction, hence DROP+CREATE."""
    db = fresh()
    db.execute(
        "INSERT INTO competitions VALUES (1, 'IPL 2024', 'T20', '2024', 'IPL', 'c.csv', 1, 1)"
    )
    db.execute("INSERT INTO teams VALUES (1, 'A', 't.csv', 1, 1)")
    db.execute("INSERT INTO competition_teams VALUES (1, 1, 'A', 't.csv', 1, 1)")
    with pytest.raises(duckdb.Error):
        with db.transaction():
            db.execute("DELETE FROM competition_teams")
            db.execute("DELETE FROM competitions")
            db.execute(
                "INSERT INTO competitions VALUES (1, 'IPL 2024', 'T20', '2024', 'IPL', 'c.csv', 1, 1)"
            )
            db.execute("INSERT INTO competition_teams VALUES (1, 1, 'A', 't.csv', 1, 1)")


def test_split_statements_strips_comments() -> None:
    assert split_statements("-- a; b\nSELECT 1; -- tail\nSELECT 2;") == ["SELECT 1", "SELECT 2"]
