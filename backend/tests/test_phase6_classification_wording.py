"""Three real classification values plus one disabled placeholder (Phase 6 cleanup, decision 1)."""

from __future__ import annotations

import typing
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase4 import classification as cl
from app.phase5 import classification_v2 as c2
from app.phase5.filters import FilterSpec
from app.phase6.cleanup_scans import scan_wording
from app.schemas import phase5 as sc5
from tests.phase4_api_helpers import base_classification_v2, build_store

P = "/api/v1"
H = {"X-Admin-Token": "tok"}
ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 6, 1)
REAL = ("VERIFIED_CAPPED", "DERIVED_CAPPED", "UNKNOWN")


def raw(rows):
    return pd.DataFrame(rows, columns=list(cl.OVERRIDE_COLUMNS), dtype=str)


def good(pid="7", value="VERIFIED_UNCAPPED"):
    return (pid, "international_status", value, "Board cap list 2026", "Ann Lee", "2026-02-01")


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(build_store(tmp_path), admin_token="tok"))


# ----------------------------------------------------------------------------- enums
def test_status_values_are_exactly_the_three_real_values():
    assert c2.STATUS_VALUES == REAL
    assert typing.get_args(sc5.ClassificationStatus) == REAL


def test_placeholder_is_separate_and_not_a_real_status():
    assert c2.DISABLED_PLACEHOLDER_VALUES == ("VERIFIED_UNCAPPED",)
    assert "VERIFIED_UNCAPPED" not in c2.STATUS_VALUES
    assert "VERIFIED_UNCAPPED" not in typing.get_args(sc5.ClassificationStatus)
    assert set(c2.ACCEPTED_STORED_VALUES) == {*REAL, "VERIFIED_UNCAPPED"}


def test_capabilities_list_three_values_and_the_placeholder_separately(client):
    caps = client.get(f"{P}/meta/capabilities").json()
    assert caps["classification_values"] == list(REAL)
    assert caps["disabled_placeholder_values"] == ["VERIFIED_UNCAPPED"]
    assert caps["strict_uncapped_enabled"] is False
    props = sc5.CapabilitiesResponse.model_json_schema()["properties"]
    assert "disabled placeholder" in props["disabled_placeholder_values"]["description"].lower()
    assert "VERIFIED_UNCAPPED" not in str(props["classification_values"])


def test_coverage_has_nine_combinations_and_separate_placeholder_count(client):
    summary = client.get(f"{P}/meta/classification-coverage").json()["coverage"]["summary"]
    assert len(summary["combinations_all_players"]) == 9
    assert {c["international_status"] for c in summary["combinations_all_players"]} == set(REAL)
    assert set(summary["status_counts"]) == set(REAL)
    assert summary["disabled_placeholder_counts"] == {"VERIFIED_UNCAPPED": 0}
    assert sum(summary["status_counts"].values()) == summary["players_total"]


def test_migration_still_maps_uncapped_source_rows_to_the_placeholder():
    assert c2.MIGRATION_MAP[("Uncapped", cl.V_SOURCE)] == "VERIFIED_UNCAPPED"
    assert set(c2.MIGRATION_MAP.values()) == set(c2.ACCEPTED_STORED_VALUES)


# ----------------------------------------------------------------------------- mechanism kept
def test_override_mechanism_still_accepts_the_placeholder_value():
    base = base_classification_v2()
    ov = c2.validate_overrides_v2(raw([good("7")]), base, TODAY)
    final = c2.apply_overrides_v2(base, ov)
    assert final.set_index("player_id").loc[7, "international_status"] == "VERIFIED_UNCAPPED"
    cov = c2.coverage_v2(final)
    assert cov["disabled_placeholder_counts"] == {"VERIFIED_UNCAPPED": 1}
    assert "VERIFIED_UNCAPPED" not in cov["status_counts"]
    assert sum(cov["status_counts"].values()) == len(final) - 1


def test_override_to_a_non_value_is_still_rejected():
    base = base_classification_v2()
    with pytest.raises(cl.ClassificationConfigError):
        c2.validate_overrides_v2(raw([good("7", "UNCAPPED_MAYBE")]), base, TODAY)


def test_strict_uncapped_stays_disabled_on_public_and_internal_routes(client):
    for url in (
        f"{P}/internal/rankings/batter?classification=all_uncapped",
        f"{P}/internal/rankings/uncapped/overall",
    ):
        r = client.get(url, headers=H)
        assert r.status_code == 200 and r.json()["result_status"] == "STRICT_UNCAPPED_DISABLED"
    pub = client.get(f"{P}/players?classification=all_uncapped").json()
    assert pub["result_status"] == "STRICT_UNCAPPED_DISABLED"
    spec = FilterSpec(role="batter", status="VERIFIED_UNCAPPED")
    assert spec.status == "VERIFIED_UNCAPPED"  # still accepted, answered as disabled


def test_status_filter_description_names_the_placeholder_as_disabled():
    desc = FilterSpec.model_json_schema()["properties"]["status"]["description"]
    assert "disabled placeholder" in desc and "STRICT_UNCAPPED_DISABLED" in desc


# ----------------------------------------------------------------------------- wording scans
DOCS = ("docs/frontend_backend_contracts.md", "docs/backend_implementation_spec.md")
SOURCES = (
    "app/phase5/classification_v2.py",
    "app/phase5/reports.py",
    "app/phase5/filters.py",
    "app/schemas/phase5.py",
    "app/services/phase4_service.py",
    "scripts/phase5_classification.py",
)


@pytest.mark.parametrize("rel", DOCS + SOURCES)
def test_no_text_calls_the_classification_four_valued(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert scan_wording(text) == [], rel


def test_wording_scanner_detects_the_old_phrases():
    assert scan_wording("now one of four **separate** values") != []
    assert scan_wording("moved to four separate statuses") != []
    assert scan_wording("a fourth status") != []
    assert scan_wording("3 nationalities x 4 statuses") != []
    assert scan_wording("three real statuses plus a disabled placeholder") == []
    assert scan_wording("none of the four format-role cells") == []
    assert scan_wording("not an established fourth status") == []
    assert scan_wording("Phase 4 status") == []


def test_contract_doc_states_three_values_and_a_disabled_placeholder():
    text = (ROOT / "docs/frontend_backend_contracts.md").read_text(encoding="utf-8")
    assert "three real values" in text and "disabled placeholder" in text
    assert "disabled_placeholder_values" in text
