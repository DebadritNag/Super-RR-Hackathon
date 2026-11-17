"""Public descriptive player directory vs gated outputs (Phase 6 cleanup, decision 6c).

The public ``/players`` surface is descriptive only: identity, classification with verification
status and match counts. It carries no score, rank, interval, eligibility or publication field.
Everything that does carry them is on a token-protected ``/internal`` route or is gate-refused.
"""

from __future__ import annotations

import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase4 import classification as cl
from app.phase6.cleanup_scans import (
    FORBIDDEN_PUBLIC_FIELD,
    forbidden_public_names,
    walk_json_keys,
    walk_model_fields,
)
from app.schemas import phase4 as sc
from tests.phase4_api_helpers import all_pass_gates, build_store

P = "/api/v1"
TOKEN = "tok"
H = {"X-Admin-Token": TOKEN}
PUBLIC_MODELS = (
    sc.PublicPlayerRow,
    sc.PublicPlayerListResponse,
    sc.PublicPlayerDetailResponse,
    sc.PublicDisabled,
    sc.PublicPlayerListResponse | sc.PublicDisabled,
)
PUBLIC_DIRECTORY_PATHS = {f"{P}/players", f"{P}/players/{{player_id}}"}


@pytest.fixture()
def paths(tmp_path):
    store = build_store(tmp_path)
    overrides = tmp_path / "overrides.csv"
    overrides.write_text(",".join(cl.OVERRIDE_COLUMNS) + "\n", encoding="utf-8")
    return store, overrides


def make_client(paths, token=TOKEN, gates=None):
    store, overrides = paths
    return TestClient(create_app(store, overrides, admin_token=token, gate_inputs=gates))


# ----------------------------------------------------------------------------- schema
@pytest.mark.parametrize("model", PUBLIC_MODELS, ids=lambda m: getattr(m, "__name__", str(m)))
def test_public_models_have_no_score_rank_or_eligibility_fields(model):
    names = walk_model_fields(model)
    assert names, "walker found no fields"
    assert forbidden_public_names(names) == []


def test_walker_sees_nested_and_union_fields():
    names = walk_model_fields(sc.PublicPlayerListResponse)
    assert {"page", "items", "player_id", "international_status_verification"} <= names
    assert {"eligible_scopes", "conflict_flag"} <= walk_model_fields(sc.PlayerListResponse)
    assert {"score", "rank", "interval_low"} <= walk_model_fields(sc.RankingResponse)
    assert forbidden_public_names(walk_model_fields(sc.PlayerListResponse)) != []


def test_public_directory_routes_use_only_the_public_models():
    app = create_app()
    seen = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path in PUBLIC_DIRECTORY_PATHS:
            assert forbidden_public_names(walk_model_fields(route.response_model)) == [], route.path
            seen.add(route.path)
    assert seen == PUBLIC_DIRECTORY_PATHS


def test_classification_fields_are_allowed_and_carry_the_verification_status():
    names = walk_model_fields(sc.PublicPlayerRow)
    assert {
        "nationality",
        "nationality_verification",
        "international_status",
        "international_status_verification",
    } <= names
    assert not FORBIDDEN_PUBLIC_FIELD.search("international_status_verification")


def test_public_models_expose_the_descriptive_flags_not_the_publication_flags():
    fields = set(sc.PublicPlayerListResponse.model_fields)
    assert {"status", "disclaimer", "descriptive_only"} <= fields
    assert not {"publication_status", "gate_results", "official_ranking"} & fields


# ----------------------------------------------------------------------------- json
def test_public_directory_json_has_no_forbidden_keys(paths):
    c = make_client(paths)
    listing = c.get(f"{P}/players?limit=200")
    assert listing.status_code == 200
    body = listing.json()
    assert body["page"]["total"] == 24 and body["descriptive_only"] is True
    assert forbidden_public_names(walk_json_keys(body)) == []
    detail = c.get(f"{P}/players/1")
    assert detail.status_code == 200
    assert forbidden_public_names(walk_json_keys(detail.json())) == []
    assert detail.json()["player"]["international_status_verification"]


def test_public_directory_json_has_no_forbidden_keys_with_every_gate_passing(paths):
    c = make_client(paths, gates=all_pass_gates())
    for url in (f"{P}/players?limit=50", f"{P}/players/12"):
        assert forbidden_public_names(walk_json_keys(c.get(url).json())) == [], url


def test_public_directory_ignores_the_pressure_match_filter(paths):
    c = make_client(paths)
    plain = c.get(f"{P}/players?limit=200").json()["page"]["total"]
    assert c.get(f"{P}/players?min_pressure_matches=9999&limit=200").json()["page"]["total"] == (
        plain
    )  # unknown query parameters are ignored; the filter exists only on /internal/players
    internal = c.get(f"{P}/internal/players?min_pressure_matches=9999&limit=200", headers=H)
    assert internal.status_code == 200


def test_internal_directory_keeps_eligibility_and_publication_fields(paths):
    c = make_client(paths)
    body = c.get(f"{P}/internal/players?limit=3", headers=H).json()
    item = body["page"]["items"][0]
    assert {"eligible_scopes", "conflict_flag"} <= set(item)
    assert body["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY" and body["gate_results"]
    detail = c.get(f"{P}/internal/players/1", headers=H).json()
    assert "eligible_scopes" in detail["player"] and detail["gate_results"]


def test_public_disabled_answer_for_strict_uncapped_has_no_rows_or_gate_fields(paths):
    c = make_client(paths)
    body = c.get(f"{P}/players?classification=all_uncapped").json()
    assert body["result_status"] == "STRICT_UNCAPPED_DISABLED"
    assert set(body) == {
        "status",
        "disclaimer",
        "descriptive_only",
        "result_status",
        "reason",
        "source_needed",
        "request_kind",
    }


# ----------------------------------------------------------------------------- protection
def internal_routes(app):
    return [
        r for r in app.routes if isinstance(r, APIRoute) and r.path.startswith(f"{P}/internal/")
    ]


def fill(path: str) -> str:
    subs = {"player_id": "1", "role": "batter", "kind": "overall", "preset_id": "x"}
    return re.sub(r"\{(\w+)\}", lambda m: subs.get(m.group(1), "1"), path)


def call(c, route, headers=None):
    method = sorted(route.methods - {"HEAD", "OPTIONS"})[0]
    kw = {"json": {}} if method == "POST" else {}
    return c.request(method, fill(route.path), headers=headers, **kw)


def test_every_internal_route_rejects_missing_and_wrong_tokens(paths):
    app = create_app(*paths, admin_token=TOKEN)
    routes = internal_routes(app)
    assert len(routes) >= 12
    assert f"{P}/internal/players" in {r.path for r in routes}
    c = TestClient(app)
    for route in routes:
        assert call(c, route).status_code == 401, route.path
        wrong = call(c, route, {"X-Admin-Token": "nope"})
        assert wrong.status_code == 401, route.path
        assert wrong.json()["error"]["code"] == "ADMIN_AUTH_FAILED"


def test_every_internal_route_is_unavailable_when_no_token_is_configured(paths, monkeypatch):
    monkeypatch.delenv("SUPERR_ADMIN_TOKEN", raising=False)
    app = create_app(*paths, admin_token=None)
    c = TestClient(app)
    for route in internal_routes(app):
        r = call(c, route, H)
        assert r.status_code == 503, route.path
        assert r.json()["error"]["code"] == "ADMIN_DISABLED"


def test_score_bearing_public_routes_refuse_without_rows_under_real_gates(paths):
    c = make_client(paths)
    for url in (
        "/rankings/batter",
        "/rankings/uncapped/overall",
        "/players/1/profile",
        "/compare?player_ids=1,2",
    ):
        r = c.get(P + url)
        assert r.status_code == 403, url
        assert r.json()["error"]["code"] == "PUBLICATION_GATE_NOT_SATISFIED"
        assert not {"page", "items", "rows", "score"} & walk_json_keys(r.json()), url
    r = c.post(P + "/selection/custom", json={"total": 3})
    assert r.status_code == 403
    r = c.post(P + "/dynamic-rankings", json={"role": "batter"})
    assert r.status_code == 403
    assert not {"page", "items", "rows"} & walk_json_keys(r.json())
