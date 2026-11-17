"""Phase 7: the OpenAPI contract of /players must not advertise the removed pressure filter."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _params(schema: dict, path: str) -> list[str]:
    return [p["name"] for p in schema["paths"][path]["get"].get("parameters", [])]


def test_public_players_openapi_has_no_min_pressure_matches_but_internal_keeps_it():
    schema = TestClient(create_app(admin_token="t")).get("/openapi.json").json()
    assert "min_pressure_matches" not in _params(schema, "/api/v1/players")
    assert "min_pressure_matches" in _params(schema, "/api/v1/internal/players")


def test_public_players_detail_openapi_has_no_pressure_parameter():
    schema = TestClient(create_app(admin_token="t")).get("/openapi.json").json()
    assert not any("pressure" in n for n in _params(schema, "/api/v1/players/{player_id}"))
