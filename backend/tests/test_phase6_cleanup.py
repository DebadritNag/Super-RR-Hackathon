"""Phase 6 cleanup checks as run by ``scripts/phase6_cleanup_checks.py`` (static parts only)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def checks():
    spec = importlib.util.spec_from_file_location(
        "phase6_cleanup_checks", ROOT / "scripts" / "phase6_cleanup_checks.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_wording_scan_is_clean_on_the_real_files(checks):
    out = checks.check_wording()
    assert out["files_scanned"] == len(checks.WORDING_FILES) >= 8
    assert out["hits"] == {}


def test_vacuous_scan_is_clean_and_detects_the_three_original_lines(checks):
    out = checks.check_vacuous()
    assert out["found_after_cleanup"] == []
    assert out["scanner_detects_the_original_lines"] is True
    assert len(out["found_before_cleanup"]) == 3
    assert out["test_files_scanned"] == len(list((ROOT / "tests").rglob("*.py")))


def test_public_directory_schema_is_clean_and_internal_one_is_not(checks):
    app = create_app()
    out = checks.check_schema(app)
    assert out["public_directory_routes_clean"] is True
    assert all(v == [] for v in out["forbidden_names_in_public_models"].values())
    assert {"eligible_scopes", "conflict_flag"} <= set(
        out["fields_only_on_internal_directory_model"]
    )
    scopes = {(r["path"], r["scope"]) for r in out["routes"]}
    assert ("/api/v1/players", "public") in scopes
    assert ("/api/v1/internal/players", "internal") in scopes


def test_every_edited_test_has_a_reason_and_exists(checks):
    for rel, why in checks.TESTS_EDITED:
        assert (ROOT / rel).is_file() and len(why) > 20, rel
    for rel in checks.FILES_ADDED:
        assert (ROOT / rel).is_file(), rel


def test_written_report_and_json_agree_when_present():
    path = ROOT / "data" / "reports" / "phase6_cleanup_checks.json"
    if not path.is_file():
        pytest.skip("run scripts/phase6_cleanup_checks.py first")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["all_checks_passed"] is True
    assert data["official_ranking"] is False
    assert data["classification"]["status_values"] == [
        "VERIFIED_CAPPED",
        "DERIVED_CAPPED",
        "UNKNOWN",
    ]
    assert data["classification"]["disabled_placeholder_values"] == ["VERIFIED_UNCAPPED"]
    assert (ROOT / "data" / "reports" / "phase6_cleanup_report.md").is_file()
