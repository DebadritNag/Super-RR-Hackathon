"""Retention stub: created empty, only in the analytical store, referenced by no scoring module."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pytest

from app.core.config import BACKEND_ROOT
from app.phase4.store import OFFICIAL_DB
from app.phase5.constants import REPORTS_DIR
from app.phase6 import retention_stub as rs
from app.phase6.store import StoreError
from app.services.pressure_service import EXPLORATORY_DB

APP = BACKEND_ROOT / "app"
ALLOWED = {APP / "phase6" / "retention_stub.py"}


def test_create_stub_makes_an_empty_table_with_the_documented_columns(tmp_path):
    store = tmp_path / "s.duckdb"
    assert rs.create_stub(store) == 0
    assert rs.create_stub(store) == 0  # idempotent
    con = duckdb.connect(str(store), read_only=True)
    try:
        cols = [r[0] for r in con.execute(f"DESCRIBE {rs.TABLE}").fetchall()]
        n = con.execute(f"SELECT count(*) FROM {rs.TABLE}").fetchone()[0]
    finally:
        con.close()
    assert tuple(cols) == rs.COLUMNS
    assert n == 0


def test_status_default_is_unknown_and_check_rejects_other_values(tmp_path):
    store = tmp_path / "s.duckdb"
    rs.create_stub(store)
    con = duckdb.connect(str(store))
    try:
        con.execute(f"INSERT INTO {rs.TABLE} (player_id, team) VALUES (1, 'X')")
        assert con.execute(f"SELECT status FROM {rs.TABLE}").fetchone()[0] == "unknown"
        with pytest.raises(duckdb.ConstraintException):
            con.execute(f"INSERT INTO {rs.TABLE} (player_id, status) VALUES (2, 'capped')")
        with pytest.raises(duckdb.ConstraintException):
            con.execute(f"INSERT INTO {rs.TABLE} (player_id, status) VALUES (3, 'uncapped')")
    finally:
        con.close()


def test_status_values_are_separate_availability_values_with_no_capped_wording():
    assert rs.STATUS_VALUES == ("retained", "released", "traded", "auction_available", "unknown")
    assert not any("cap" in v for v in rs.STATUS_VALUES)
    assert "player_id" in rs.COLUMNS and "snapshot_date" in rs.COLUMNS
    assert {"source", "verification_status", "mapping_status", "ambiguity_note"} <= set(rs.COLUMNS)


def test_stub_refuses_the_official_database(tmp_path):
    with pytest.raises(StoreError):
        rs.create_stub(OFFICIAL_DB, OFFICIAL_DB)


def test_no_scoring_api_service_schema_or_other_module_references_the_stub():
    needle = re.compile(r"retention_status_stub|p6_retention", re.I)
    hits = []
    for path in sorted(APP.rglob("*.py")):
        if path in ALLOWED:
            continue
        if needle.search(path.read_text(encoding="utf-8")):
            hits.append(str(path.relative_to(APP)))
    assert hits == []


def test_no_phase4_phase5_script_or_config_reads_the_stub():
    needle = re.compile(r"retention_status_stub|p6_retention", re.I)
    scripts = [p for p in (BACKEND_ROOT / "scripts").glob("*.py")
               if p.name not in {"phase6_retention_stub.py", "run_phase6.py"}]  # fmt: skip
    configs = list((BACKEND_ROOT / "config").glob("*.json"))
    for p in [*scripts, *configs]:
        assert not needle.search(p.read_text(encoding="utf-8")), p.name


def test_stored_stub_is_empty_and_not_in_the_official_database():
    if not Path(EXPLORATORY_DB).is_file():
        pytest.skip("exploratory store not present")
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        has = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [rs.TABLE]
        ).fetchone()[0]
        if not has:
            pytest.skip("stub not created yet (run scripts/phase6_retention_stub.py)")
        assert con.execute(f"SELECT count(*) FROM {rs.TABLE}").fetchone()[0] == 0
    finally:
        con.close()
    if Path(OFFICIAL_DB).is_file():
        con = duckdb.connect(str(OFFICIAL_DB), read_only=True)
        try:
            assert (
                con.execute(
                    "SELECT count(*) FROM information_schema.tables WHERE table_name LIKE '%retention%'"
                ).fetchone()[0]
                == 0
            )
        finally:
            con.close()


def test_design_note_states_the_required_rules():
    p = REPORTS_DIR / "phase6_retention_import_design.md"
    if not p.is_file():
        pytest.skip("design note not generated")
    t = p.read_text(encoding="utf-8").lower()
    for phrase in ("retained", "released", "traded", "auction_available", "unknown",
                   "snapshot_date", "verification_status", "ambiguous", "never infer",
                   "no retention data is imported"):  # fmt: skip
        assert phrase in t, phrase
    assert "never imply capped or uncapped" in t
