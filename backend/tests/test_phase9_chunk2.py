"""Phase 9 (chunk 2): API serves Phase 9 outputs, frontend text scan, Phase 8 source preserved."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase8.constants import PHASE8_DB, PHASE9_DB, REPORTS_DIR
from app.services.submission_service import SubmissionService

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
real = pytest.mark.skipif(
    not (PHASE9_DB.exists() and (REPORTS_DIR / "pressure_batters_top10.csv").exists()),
    reason="generated Phase 9 outputs not present",
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(admin_token="t"))


@real
@pytest.mark.parametrize("role", ["batters", "bowlers"])
def test_api_serves_phase9_top10(client, role):
    j = client.get(f"/api/v1/submission/top10/{role}").json()
    dv = j["data_version"]
    assert dv["submission_source"] == "phase9"
    assert dv["phase8_store_file"] == "phase9.duckdb"
    assert dv["methodology_version"] == "phase9_methodology_v1"
    assert "window:2022-01-22..2026-11-01" in dv["data_version_hash"]
    assert dv["criteria_sha256"].startswith("9258aa6d")
    assert 0 < len(j["rows"]) <= 10


@real
def test_data_version_in_every_response_changes_with_source():
    p9 = SubmissionService(source="phase9").data_version()
    p8 = SubmissionService(source="phase8").data_version()
    assert p9["submission_source"] != p8["submission_source"]
    assert p9["data_version_hash"] != p8["data_version_hash"]
    assert p9.get("manifest_sha256")


@real
def test_phase8_source_still_served_from_phase8_copies():
    s = SubmissionService(source="phase8")
    assert s.db == PHASE8_DB and s.prefix == "p8_"
    t = s.top10("bowlers")
    assert t["data_version"]["methodology_version"] == "phase8_methodology_v1"
    assert t["rows"][0]["player_name"] != ""


def test_unknown_source_refused():
    with pytest.raises(ValueError):
        SubmissionService(source="phase7")


@real
def test_players_route_stays_descriptive_and_internal_protected(client):
    j = client.get("/api/v1/submission/profiles/batters?limit=2").json()
    assert j["status_label"] == "DESCRIPTIVE_ONLY"
    for r in j["rows"]:
        assert not {"rank", "pressure_score", "list_status"} & set(r)
    assert TestClient(create_app()).get("/api/v1/internal/experimental-ai/batters").status_code in (
        401,
        403,
        503,
    )


def test_frontend_src_has_no_retired_status_word():
    """Presentation decision D2: no source string of the frontend carries the retired word."""
    pat = re.compile("xplor" + "atory", re.I)
    hits = [
        str(f.relative_to(FRONTEND_SRC))
        for f in FRONTEND_SRC.rglob("*")
        if f.is_file()
        and f.suffix in {".ts", ".tsx", ".css", ".html"}
        and pat.search(f.read_text(encoding="utf-8"))
    ]
    assert hits == []


def test_frontend_has_no_status_banner_or_pill():
    text = "\n".join(f.read_text(encoding="utf-8") for f in FRONTEND_SRC.rglob("*.tsx"))
    assert "StatusBanner" not in text and "StatusPill" not in text
    assert "Why this status" not in text


def test_frontend_scrubs_api_text():
    utils = (FRONTEND_SRC / "lib" / "utils.ts").read_text(encoding="utf-8")
    api = (FRONTEND_SRC / "services" / "submissionApi.ts").read_text(encoding="utf-8")
    assert "sanitizeText" in utils and "scrub(" in api
