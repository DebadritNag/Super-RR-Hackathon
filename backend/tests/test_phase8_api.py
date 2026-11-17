"""Phase 8 chunk 6: schema and safety tests of the public submission routes.

The routes read the generated Phase 8 reports and store; tests that need them skip when absent.
Synthetic profile files (clearly synthetic ids and names) cover the radar edge cases.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase8.constants import PHASE8_DB, REPORTS_DIR
from app.schemas.phase8_submission import StatusLabel
from app.services.submission_service import NAVIGATION, SubmissionService

LABELS = set(StatusLabel.__args__)
REAL = (
    PHASE8_DB.exists()
    and (REPORTS_DIR / "pressure_batters_top10.csv").exists()
    and (REPORTS_DIR / "pressure_bowlers_top10.csv").exists()
)
real = pytest.mark.skipif(not REAL, reason="Phase 8 outputs not generated")
TOKEN = "unit-test-token"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(admin_token=TOKEN))


def _ids(client: TestClient, role: str) -> list[int]:
    return [r["player_id"] for r in client.get(f"/api/v1/submission/top10/{role}").json()["rows"]]


@real
@pytest.mark.parametrize(
    "path",
    [
        "/overview",
        "/top10/batters",
        "/top10/bowlers",
        "/why/batters",
        "/why/bowlers?kind=NEAR_MISS",
        "/methodology",
        "/validation",
        "/profiles/batters?limit=3",
        "/profiles/bowlers?limit=3",
    ],
)
def test_every_public_response_carries_status_and_caveats(client, path):
    r = client.get(f"/api/v1/submission{path}")
    assert r.status_code == 200
    j = r.json()
    assert j["status_label"] in LABELS
    assert j["validated"] is False
    assert isinstance(j["caveats"], list) and j["caveats"]
    assert j["publication_status"] == "COMPETITION_SUBMISSION_NOT_VALIDATED"
    assert isinstance(j["gate_results"], list)


@real
@pytest.mark.parametrize("role", ["batters", "bowlers"])
def test_top10_lists_are_ordered_labelled_and_never_validated(client, role):
    j = client.get(f"/api/v1/submission/top10/{role}").json()
    rows = j["rows"]
    assert 0 < len(rows) <= 10
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    assert j["list_status"]["list_status"] == j["status_label"]
    for r in rows:
        assert r["ranking_status"] in LABELS and r["list_status"] in LABELS
        assert r["interval_low"] is None or r["interval_low"] <= r["interval_high"]
    assert j["status_label"] != "VALIDATED"
    assert "NOT" in j["list_status"]["banner"].upper() or j["status_label"] != "PROVISIONAL"


@real
def test_overview_has_exactly_the_ten_navigation_items(client):
    j = client.get("/api/v1/submission/overview").json()
    assert j["navigation"] == NAVIGATION and len(NAVIGATION) == 10
    assert {x["role"] for x in j["lists"]} == {"batter", "bowler"}
    for f in j["files"]:
        assert re.fullmatch(r"[0-9a-f]{64}", f["sha256"])


@real
def test_player_evidence_for_selected_and_not_selected(client):
    pid = _ids(client, "batters")[0]
    j = client.get(f"/api/v1/submission/players/batters/{pid}").json()
    assert j["selection_state"] == "SELECTED" and j["top10_row"]["player_id"] == pid
    assert j["explanations"] and j["estimate"] is not None
    near = client.get("/api/v1/submission/why/batters?kind=NEAR_MISS&limit=1").json()["rows"][0]
    k = client.get(f"/api/v1/submission/players/batters/{near['player_id']}").json()
    assert k["selection_state"] == "NOT_SELECTED_ELIGIBLE"
    assert k["top10_row"] is None and k["explanations"]


@real
def test_unknown_and_malformed_inputs_are_refused_safely(client):
    assert client.get("/api/v1/submission/players/batters/999999999").status_code == 404
    assert client.get("/api/v1/submission/players/batters/1;DROP TABLE x").status_code == 422
    assert client.get("/api/v1/submission/top10/everyone").status_code == 422
    assert client.get("/api/v1/submission/why/batters?kind=x' OR '1'='1").status_code == 422
    assert client.get("/api/v1/submission/profiles/batters?q=%27%3B--&limit=2").status_code == 200
    assert client.get("/api/v1/submission/profiles/batters?limit=100000").status_code == 422
    assert client.get("/api/v1/submission/profiles/batters?sort_by=score").status_code == 422
    assert client.get("/api/v1/submission/top10/batters?official=true").status_code == 403


@real
def test_pagination_is_consistent(client):
    a = client.get("/api/v1/submission/profiles/batters?limit=5&offset=0").json()
    b = client.get("/api/v1/submission/profiles/batters?limit=5&offset=5").json()
    assert a["page"]["total"] == b["page"]["total"] > 10
    assert {(r["player_id"], r["format"]) for r in a["rows"]}.isdisjoint(
        {(r["player_id"], r["format"]) for r in b["rows"]}
    )
    assert all("rank" not in r and "pressure_score" not in r for r in a["rows"])


@real
def test_compare_makes_no_superiority_claim_and_validates_ids(client):
    ids = _ids(client, "batters")[:2]
    j = client.get(f"/api/v1/submission/compare/batters?player_ids={ids[0]},{ids[1]}").json()
    assert j["superiority_claim"] == "NOT_MADE" and len(j["players"]) == 2
    assert client.get(f"/api/v1/submission/compare/batters?player_ids={ids[0]}").status_code == 422
    assert client.get("/api/v1/submission/compare/batters?player_ids=1,2,3,4,5").status_code == 422
    assert client.get("/api/v1/submission/compare/batters?player_ids=1,1").status_code == 422


@real
def test_radar_has_raw_values_denominators_and_no_composite(client):
    pid = _ids(client, "batters")[0]
    j = client.get(f"/api/v1/submission/radar/batters/{pid}?format=IPL")
    if j.status_code == 404:
        j = client.get(f"/api/v1/submission/radar/batters/{pid}?format=T20I")
    j = j.json()
    assert j["composite"] is None and j["normalisation_cohort"]
    for d in j["dimensions"]:
        assert d["denominator_label"]
        if d["available"]:
            assert d["value"] is not None and d["denominator"] is not None
            assert 0 <= d["cohort_percentile"] <= 100
        else:
            assert d["cohort_percentile"] is None and d["unavailable_reason"]


def test_radar_marks_thin_and_undefined_dimensions_unavailable_not_zero(tmp_path: Path):
    cols = ["player_id", "player_name", "format", "balls_faced", "strike_rate", "boundary_ball_share",
            "dot_ball_share", "balls_per_dismissal", "pp_balls", "pp_strike_rate", "mid_balls",
            "mid_strike_rate", "death_balls", "death_strike_rate", "vs_pace_balls",
            "vs_pace_strike_rate", "vs_spin_balls", "vs_spin_strike_rate",
            "descriptive_version"]  # fmt: skip
    rows = []
    for i in range(1, 6):
        rows.append([i, f"Synthetic {i}", "IPL", 100 * i, 100 + i, 0.1, 0.3, 20.0, 30 + i, 120.0,
                     40, 110.0, 5, float("nan"), 50, 130.0, 50, 90.0, "v"])  # fmt: skip
    pd.DataFrame(rows, columns=cols).to_csv(
        tmp_path / "descriptive_batter_profiles.csv", index=False
    )
    svc = SubmissionService(tmp_path, tmp_path / "none.duckdb", tmp_path)
    out = svc.radar("batters", 1, "IPL")
    by = {d["key"]: d for d in out["dimensions"]}
    assert by["death_strike_rate"]["available"] is False
    assert (
        by["death_strike_rate"]["value"] is None
        and by["death_strike_rate"]["cohort_percentile"] is None
    )
    assert by["strike_rate"]["available"] and by["strike_rate"][
        "cohort_percentile"
    ] == pytest.approx(10.0)
    assert out["composite"] is None


@real
def test_players_route_stays_descriptive_only(client):
    j = client.get("/api/v1/players").json()
    assert j["descriptive_only"] is True
    banned = re.compile(r"rank|score|pressure|eligib", re.I)
    for item in j["page"]["items"]:
        assert not [k for k in item if banned.search(k)], item.keys()


@real
def test_internal_ai_route_is_token_protected(client):
    url = "/api/v1/internal/experimental-ai/batters"
    assert client.get(url).status_code == 401
    assert client.get(url, headers={"X-Admin-Token": "wrong"}).status_code == 401
    ok = client.get(url, headers={"X-Admin-Token": TOKEN})
    assert ok.status_code == 200
    j = ok.json()
    assert j["status_label"] == "EXPERIMENTAL_NOT_VALIDATED" and j["validated"] is False
    assert all(r["status_label"] == "EXPERIMENTAL_NOT_VALIDATED" for r in j["rows"])
    # not reachable without a configured token either
    assert TestClient(create_app()).get(url).status_code in (401, 503)


@real
def test_internal_routes_stay_protected_and_submission_is_read_only(client):
    for path in ("/api/v1/internal/model-status", "/api/v1/internal/experimental-predictions"):
        assert client.get(path).status_code == 401
    spec = client.get("/openapi.json").json()["paths"]
    for p, ops in spec.items():
        if p.startswith("/api/v1/submission"):
            assert set(ops) == {"get"}, p


@real
def test_submitted_list_never_reads_experimental_ai_output(client):
    lst = client.get("/api/v1/submission/top10/batters").json()
    assert "experimental_ai" not in str(lst).lower()
    assert "EXPERIMENTAL_NOT_VALIDATED" not in {r["list_status"] for r in lst["rows"]}


def test_service_sql_interpolates_only_fixed_fragments():
    """Values are bound parameters; f-string SQL may name only table names and fixed clauses."""
    src = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "submission_service.py"
    ).read_text(encoding="utf-8")
    sql_lines = [
        ln for ln in src.splitlines() if "SELECT" in ln or "FROM {" in ln or "WHERE {" in ln
    ]
    names = set()
    for ln in sql_lines:
        names |= set(re.findall(r"\{(\w+)\}", ln))
    assert names <= {"table", "tab", "where"}
    assert ".format(" not in "\n".join(sql_lines) and "% (" not in "\n".join(sql_lines)
