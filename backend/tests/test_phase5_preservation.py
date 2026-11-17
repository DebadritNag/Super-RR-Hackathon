"""Phase 5 preservation: official data, Phase 4 outputs, TEST lock logs, no Cricsheet in scoring.

Hash checks compare against ``.agents/tasks/phase5_prerun_hashes.json`` (written before Phase 5
started) and are skipped when that record or the real data is absent.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from app.core.config import BACKEND_ROOT
from app.phase5.constants import REPORTS_DIR
from app.phase5.lockguard import PHASE5_LOCK_LOG, read_events
from app.services.pressure_service import EXPLORATORY_DB

PRERUN = BACKEND_ROOT.parent / ".agents" / "tasks" / "phase5_prerun_hashes.json"
APP = BACKEND_ROOT / "app"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def prerun() -> dict:
    if not PRERUN.is_file():
        pytest.skip("pre-run hash record not available")
    return json.loads(PRERUN.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- official data preserved
def test_official_database_and_source_csvs_unchanged(prerun):
    official = {
        **{k: v for k, v in prerun["duckdb"].items() if Path(k).name == "superr.duckdb"},
        **prerun["source_csvs"],
        **prerun["config_csvs"],
    }
    assert len(official) >= 14
    for path, expected in official.items():
        p = Path(path)
        if not p.is_file():
            pytest.skip(f"{p} is not present")
        assert _sha(p) == expected.lower(), f"{p.name} changed"


def test_phase4_reports_unchanged(prerun):
    assert len(prerun["phase4_reports"]) >= 50
    for path, expected in prerun["phase4_reports"].items():
        p = Path(path)
        if not p.is_file():
            pytest.skip(f"{p} is not present")
        assert _sha(p) == expected.lower(), f"{p.name} changed"


def test_phase4_lock_log_has_exactly_one_opening_and_phase5_has_none():
    p4 = REPORTS_DIR / "phase4_lock_log.json"
    if not p4.is_file():
        pytest.skip("phase4 lock log not present")
    assert [e["event"] for e in read_events(p4)] == ["FREEZE", "OPEN", "CLOSE"]
    assert not any(e.get("event") == "OPEN" for e in read_events(PHASE5_LOCK_LOG))


def test_phase4_tables_still_present_in_the_exploratory_store():
    if not EXPLORATORY_DB.is_file():
        pytest.skip("exploratory store not present")
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        n = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE starts_with(table_name, 'p4_')"
        ).fetchone()[0]
        rows = con.execute("SELECT count(*) FROM p4_pressure_scores_frozen_rules").fetchone()[0]
    finally:
        con.close()
    assert n >= 20
    assert rows == 19762


# ---------------------------------------------------------------- no Cricsheet in scoring
FORBIDDEN_IMPORTS = ("cricsheet_auditor", "cricsheet_super_over")
FORBIDDEN_LITERALS = ("_male_json", "cricsheet_index", "staging/")
DATE_VERIFICATION = APP / "phase5" / "date_verification.py"


def scoring_modules() -> list[Path]:
    """Scoring, baseline, ranking and serving modules of Phases 4 and 5 (date verification excluded)."""
    mods = sorted((APP / "phase4").glob("*.py")) + sorted((APP / "phase5").glob("*.py"))
    mods += [APP / "services" / "phase5_service.py", APP / "repositories" / "phase5_repo.py"]
    mods += sorted((APP / "repositories").glob("*.py"))
    return sorted({m for m in mods if m.is_file() and m != DATE_VERIFICATION})


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def scan(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = _docstring_nodes(tree)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *[a.name for a in node.names]]
        else:
            names = []
        hits += [f"import {n}" for n in names if any(f in n for f in FORBIDDEN_IMPORTS)]
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in skip
            and any(f in node.value for f in FORBIDDEN_LITERALS)
        ):
            hits.append(f"literal {node.value[:60]!r}")
    return hits


def test_scoring_modules_import_no_cricsheet_loader_and_name_no_cricsheet_directory():
    mods = scoring_modules()
    assert len(mods) > 30
    bad = {m.relative_to(APP).as_posix(): h for m in mods if (h := scan(m))}
    assert not bad, bad


def test_date_verification_is_the_only_phase5_cricsheet_reader():
    importers = [
        m.relative_to(APP).as_posix()
        for m in sorted((APP / "phase5").glob("*.py"))
        if any("cricsheet" in h for h in scan(m))
    ]
    assert importers == ["phase5/date_verification.py"]
    text = DATE_VERIFICATION.read_text(encoding="utf-8")
    assert "cricsheet_auditor" in text and "validation only" in text.lower()


def test_scoring_scripts_do_not_import_the_date_verification_module():
    offenders = []
    for p in sorted(APP.rglob("*.py")):
        if p == DATE_VERIFICATION:
            continue
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            mod = node.module if isinstance(node, ast.ImportFrom) else None
            if mod == "app.phase5.date_verification" and p.name not in ALLOWED_DATE_IMPORTERS:
                offenders.append(p.name)
    assert offenders == []


# test_manifest only reads the date class constant; the service and repository read stored results.
ALLOWED_DATE_IMPORTERS = {"test_manifest.py"}


def test_p5_scoring_tables_have_no_cricsheet_columns():
    if not EXPLORATORY_DB.is_file():
        pytest.skip("exploratory store not present")
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        rows = con.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE starts_with(table_name, 'p5_') AND lower(column_name) LIKE '%cricsheet%'"
        ).fetchall()
    finally:
        con.close()
    tables = {t for t, _ in rows}
    allowed = {t for t in tables if "date_verification" in t or "test_match_date_check" in t}
    assert tables <= allowed, sorted(tables - allowed)
    scoring = [t for t in tables if "score" in t or "refit" in t or "context" in t]
    assert scoring == []


def test_refit_scoring_columns_are_not_cricsheet_derived():
    from app.phase5 import refit as rf

    src = Path(rf.__file__).read_text(encoding="utf-8").lower()
    assert "cricsheet" not in src
