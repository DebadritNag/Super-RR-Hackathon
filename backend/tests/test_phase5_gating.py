"""Publication gating: INTERNAL_EXPERIMENTAL_ONLY unless every gate passes (Phase 5)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase5 import gating as g
from app.phase5.constants import FROZEN_CHOICES, METHODOLOGY_STATUS
from tests.phase4_api_helpers import all_pass_gates, build_store

P = "/api/v1"
TOKEN = "tok"
H = {"X-Admin-Token": TOKEN}
ALL_GATES = (
    "data_weight_gate_passed",
    "methodology_validated",
    "strict_classification_available",
    "min_eligible_pool",
    "date_verification",
)
STRICT = g.RequestNeeds(uses_strict_classification=True, eligible_pool=20)
ROWS = g.RequestNeeds(uses_strict_classification=False, eligible_pool=20)


def _status(inp: g.GateInput, needs: g.RequestNeeds = STRICT) -> str:
    return g.publication_status(g.evaluate_gates(inp, needs))


# ----------------------------------------------------------------------------- pure functions


def test_everything_internal_when_all_gates_fail():
    inp = g.GateInput(
        cell_statuses={f"c{i}": "THRESHOLD_NOT_VALIDATED" for i in range(4)},
        methodology={"validated": False},
        date_gate={"passed": False},
        strict_enabled=False,
        min_public_pool=10,
    )
    gates = g.evaluate_gates(inp, g.RequestNeeds(True, 3))
    assert [x.gate_id for x in gates] == list(ALL_GATES)
    assert not any(x.passed for x in gates)
    assert g.publication_status(gates) == "INTERNAL_EXPERIMENTAL_ONLY"
    assert {x.gate_id for x in g.failing(gates)} == set(ALL_GATES)


def test_public_allowed_only_when_every_gate_passes():
    inp = all_pass_gates(min_pool=10)
    gates = g.evaluate_gates(inp, STRICT)
    assert all(x.passed for x in gates) and g.publication_status(gates) == "PUBLIC_ALLOWED"


@pytest.mark.parametrize(
    ("gate", "change"),
    [
        ("data_weight_gate_passed", {"cell_statuses": {"a": "THRESHOLD_NOT_VALIDATED", "b": "OK", "c": "OK", "d": "OK"}}),
        ("methodology_validated", {"methodology": {"validated": False, "validated_by": "x", "validated_date": "d", "evidence_path": "p"}}),
        ("strict_classification_available", {"strict_enabled": False}),
        ("min_eligible_pool", {"min_public_pool": 21}),
        ("date_verification", {"date_gate": {"passed": False, "detail": "42 unverified"}}),
    ],
)  # fmt: skip
def test_each_single_failing_gate_blocks_public_allowed(gate, change):
    inp = dataclasses.replace(all_pass_gates(min_pool=10), **change)
    gates = {x.gate_id: x for x in g.evaluate_gates(inp, STRICT)}
    assert gates[gate].passed is False
    assert [k for k, v in gates.items() if not v.passed] == [gate]
    assert g.publication_status(list(gates.values())) == "INTERNAL_EXPERIMENTAL_ONLY"


@pytest.mark.parametrize("field", ["cell_statuses", "methodology", "date_gate", "strict_enabled"])
def test_missing_inputs_fail_closed(field):
    inp = dataclasses.replace(all_pass_gates(min_pool=10), **{field: None})
    assert _status(inp) == "INTERNAL_EXPERIMENTAL_ONLY"


def test_methodology_true_without_evidence_fields_is_read_as_false():
    inp = all_pass_gates(min_pool=1)
    for missing in ("validated_by", "validated_date", "evidence_path"):
        m = {**inp.methodology, missing: " "}
        res = {
            x.gate_id: x for x in g.evaluate_gates(dataclasses.replace(inp, methodology=m), ROWS)
        }
        assert res["methodology_validated"].passed is False
    assert res["methodology_validated"].detail


def test_strict_gate_is_applicable_only_to_strict_requests():
    inp = dataclasses.replace(all_pass_gates(min_pool=1), strict_enabled=False)
    plain = {x.gate_id: x for x in g.evaluate_gates(inp, ROWS)}
    assert plain["strict_classification_available"].applicable is False
    assert g.publication_status(list(plain.values())) == "PUBLIC_ALLOWED"
    strict = {x.gate_id: x for x in g.evaluate_gates(inp, STRICT)}
    assert strict["strict_classification_available"].applicable is True
    assert strict["strict_classification_available"].passed is False


def test_min_pool_is_per_request_and_not_applicable_without_rows():
    inp = all_pass_gates(min_pool=10)
    small = {x.gate_id: x for x in g.evaluate_gates(inp, g.RequestNeeds(False, 9))}
    assert small["min_eligible_pool"].passed is False
    exact = {x.gate_id: x for x in g.evaluate_gates(inp, g.RequestNeeds(False, 10))}
    assert exact["min_eligible_pool"].passed is True
    none = {x.gate_id: x for x in g.evaluate_gates(inp, g.RequestNeeds())}
    assert none["min_eligible_pool"].applicable is False


def test_apply_gates_raises_on_public_and_labels_internal():
    failing_inp = dataclasses.replace(all_pass_gates(min_pool=1), date_gate={"passed": False})
    with pytest.raises(g.PublicationGateError) as ei:
        g.apply_gates({"rows": [1]}, failing_inp, ROWS, internal=False)
    assert {r["gate_id"] for r in ei.value.gate_results if not r["passed"]} == {"date_verification"}
    out = g.apply_gates({"rows": [1]}, failing_inp, ROWS, internal=True)
    assert out["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY" and out["rows"] == [1]
    assert len(out["gate_results"]) == 5
    ok = g.apply_gates({"rows": [1]}, all_pass_gates(min_pool=1), ROWS, internal=False)
    assert ok["publication_status"] == "PUBLIC_ALLOWED" and ok["rows"] == [1]


# ----------------------------------------------------------------------------- file inputs


def _write(tmp: Path, name: str, data) -> Path:
    p = tmp / name
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return p


def test_load_gate_inputs_from_files_and_malformed_files_fail_closed(tmp_path):
    frozen = _write(
        tmp_path,
        "f.json",
        {"eligibility": {f"c{i}": {"decision": {"status": "OK"}} for i in range(4)}},
    )
    meth = _write(
        tmp_path,
        "m.json",
        {"validated": True, "validated_by": "a", "validated_date": "d", "evidence_path": "e"},
    )
    date = _write(tmp_path, "d.json", {"gate": {"passed": True, "detail": "ok"}})
    cfg = _write(tmp_path, "g.json", {"min_public_pool": 7})
    inp = g.load_gate_inputs(True, frozen, meth, date, cfg)
    assert inp.min_public_pool == 7 and _status(inp) == "PUBLIC_ALLOWED"
    for path in (frozen, meth, date):
        path.write_text("{broken", encoding="utf-8")
    broken = g.load_gate_inputs(True, frozen, meth, date, cfg)
    res = {x.gate_id: x for x in g.evaluate_gates(broken, STRICT)}
    assert res["data_weight_gate_passed"].detail == "INPUT_UNAVAILABLE"
    assert res["methodology_validated"].detail == "INPUT_UNAVAILABLE"
    assert res["date_verification"].detail == "NOT_RUN" and not res["date_verification"].passed
    missing = g.load_gate_inputs(
        True, tmp_path / "x", tmp_path / "y", tmp_path / "z", tmp_path / "w"
    )
    assert missing.min_public_pool == 10 and _status(missing) == "INTERNAL_EXPERIMENTAL_ONLY"


def test_real_inputs_fail_today_and_nothing_sets_methodology_validated():
    inp = g.load_gate_inputs(False)
    res = {x.gate_id: x for x in g.evaluate_gates(inp, STRICT)}
    assert res["methodology_validated"].passed is False
    assert json.loads(METHODOLOGY_STATUS.read_text(encoding="utf-8"))["validated"] is False
    if FROZEN_CHOICES.exists():
        assert res["data_weight_gate_passed"].passed is False
    assert res["strict_classification_available"].passed is False
    assert g.publication_status(list(res.values())) == "INTERNAL_EXPERIMENTAL_ONLY"
    src = Path(g.__file__).read_text(encoding="utf-8")
    assert '"validated": True' not in src and "validated=True" not in src  # no code path sets it


# ----------------------------------------------------------------------------- API


@pytest.fixture()
def real_gates_client(tmp_path):
    return TestClient(create_app(build_store(tmp_path), admin_token=TOKEN))


GATED_GET = (
    "/rankings/batter",
    "/rankings/bowler",
    "/rankings/uncapped/overall",
    "/compare?player_ids=1,2",
    "/players/1/profile",
)


@pytest.mark.parametrize("path", GATED_GET)
def test_public_routes_return_the_gate_error_and_no_rows(real_gates_client, path):
    r = real_gates_client.get(P + path)
    assert r.status_code == 403
    body = r.json()
    assert set(body) == {"error"}
    err = body["error"]
    assert err["code"] == "PUBLICATION_GATE_NOT_SATISFIED"
    assert err["details"]["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
    failed = {
        x["gate_id"] for x in err["details"]["gate_results"] if x["applicable"] and not x["passed"]
    }
    assert {"methodology_validated", "date_verification"} <= failed
    assert "page" not in body and "items" not in body and "selected" not in body


def test_public_post_routes_return_the_gate_error(real_gates_client):
    for url, payload in (
        ("/selection/custom", {"total": 3}),
        ("/selection/presets/mixed_capped_and_uncapped_xi", None),
    ):
        r = (
            real_gates_client.post(P + url, json=payload)
            if payload
            else real_gates_client.post(P + url)
        )
        assert (
            r.status_code == 403 and r.json()["error"]["code"] == "PUBLICATION_GATE_NOT_SATISFIED"
        )
        assert "selected" not in r.json()


@pytest.mark.parametrize("path", GATED_GET[:2] + ("/compare?player_ids=1,2", "/players/1/profile"))
def test_internal_routes_need_the_token_and_return_the_status(real_gates_client, path):
    assert real_gates_client.get(P + "/internal" + path).status_code == 401
    assert (
        real_gates_client.get(
            P + "/internal" + path, headers={"X-Admin-Token": "wrong"}
        ).status_code
        == 401
    )
    r = real_gates_client.get(P + "/internal" + path, headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
    assert {x["gate_id"] for x in body["gate_results"]} == set(ALL_GATES)
    assert body["official_ranking"] is False and body["status"] == "EXPERIMENTAL_NOT_VALIDATED"


def test_internal_routes_are_disabled_without_a_configured_token(tmp_path):
    c = TestClient(create_app(build_store(tmp_path)))
    r = c.get(P + "/internal/rankings/batter", headers=H)
    assert r.status_code == 503 and r.json()["error"]["code"] == "ADMIN_DISABLED"


def test_internal_ranking_rows_are_labelled_and_match_the_ungated_numbers(real_gates_client):
    body = real_gates_client.get(P + "/internal/rankings/batter?limit=200", headers=H).json()
    assert body["page"]["total"] == 22 and body["pool_size"] == 22
    by_gate = {x["gate_id"]: x for x in body["gate_results"]}
    assert by_gate["min_eligible_pool"]["passed"] is True  # 22 rows >= 10
    assert by_gate["min_eligible_pool"]["detail"].startswith("22 eligible rows")


def test_descriptive_routes_stay_public_and_carry_the_flags(real_gates_client):
    for url in ("/players", "/players/1"):  # descriptive directory: no publication fields at all
        r = real_gates_client.get(P + url)
        assert r.status_code == 200, url
        assert r.json()["descriptive_only"] is True
        assert "publication_status" not in r.json() and "gate_results" not in r.json()
    for url in ("/selection/presets", "/meta/classification-coverage"):
        r = real_gates_client.get(P + url)
        assert r.status_code == 200, url
        assert r.json()["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
        assert len(r.json()["gate_results"]) == 5


def test_publication_gates_endpoint_lists_every_failing_gate(real_gates_client):
    body = real_gates_client.get(P + "/meta/publication-gates").json()
    assert {x["gate_id"] for x in body["gates"]} == set(ALL_GATES)
    assert {"methodology_validated", "date_verification"} <= set(body["failing_gates"])
    assert body["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"


def test_all_pass_fixture_returns_rows_as_public_allowed(tmp_path):
    c = TestClient(create_app(build_store(tmp_path), gate_inputs=all_pass_gates(min_pool=10)))
    for path in ("/rankings/batter?limit=5", "/players/1/profile", "/compare?player_ids=1,2"):
        r = c.get(P + path)
        assert r.status_code == 200, path
        assert r.json()["publication_status"] == "PUBLIC_ALLOWED"
        assert all(x["passed"] for x in r.json()["gate_results"] if x["applicable"])
    body = c.get(P + "/rankings/batter?limit=5").json()
    assert len(body["page"]["items"]) == 5 and body["official_ranking"] is False
    sel = c.post(P + "/selection/custom", json={"total": 3}).json()
    assert sel["publication_status"] == "PUBLIC_ALLOWED" and sel["size"] == 3


@pytest.mark.parametrize(
    "change",
    [
        {"cell_statuses": {"a": "THRESHOLD_NOT_VALIDATED", "b": "OK", "c": "OK", "d": "OK"}},
        {"methodology": {"validated": False}},
        {"date_gate": {"passed": False, "detail": "42 unverified"}},
        {"cell_statuses": None},
    ],
)
def test_single_failing_gate_blocks_the_public_route_but_not_the_internal_one(tmp_path, change):
    inp = dataclasses.replace(all_pass_gates(min_pool=1), **change)
    c = TestClient(create_app(build_store(tmp_path), admin_token=TOKEN, gate_inputs=inp))
    r = c.get(P + "/rankings/batter")
    assert r.status_code == 403 and r.json()["error"]["code"] == "PUBLICATION_GATE_NOT_SATISFIED"
    internal = c.get(P + "/internal/rankings/batter", headers=H)
    assert internal.status_code == 200
    assert internal.json()["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"


def test_minimum_pool_gate_blocks_a_public_filter_result_that_is_too_small(tmp_path):
    c = TestClient(create_app(build_store(tmp_path), gate_inputs=all_pass_gates(min_pool=10)))
    assert c.get(P + "/rankings/batter").status_code == 200  # 22 eligible players
    small = c.get(P + "/rankings/batter?classification=capped_derived&min_matches=30")
    assert small.status_code == 403  # fewer than 10 rows after the filter: never shown publicly
    d = {x["gate_id"]: x for x in small.json()["error"]["details"]["gate_results"]}
    assert d["min_eligible_pool"]["passed"] is False


def test_unavailable_store_is_reported_before_gates(tmp_path):
    c = TestClient(create_app(tmp_path / "absent.duckdb"))
    assert c.get(P + "/rankings/batter").status_code == 503


RETENTION_ADMIN = "/api/v1/internal/retention"  # Phase 7 chunk 3 admin routes
PUBLIC_DESCRIPTIVE_PATHS = {
    "/api/v1/players",
    "/api/v1/players/{player_id}",
    # Phase 7 descriptive endpoints: descriptive_only models, no gate fields
    "/api/v1/descriptive/profiles/batters",
    "/api/v1/descriptive/profiles/bowlers",
    "/api/v1/descriptive/profiles/{player_id}",
    "/api/v1/descriptive/compare",
    "/api/v1/descriptive/radar",
    "/api/v1/descriptive/overview",
    "/api/v1/descriptive/methodology/summary",
}


def test_every_rows_returning_route_carries_the_publication_fields():
    """A new route cannot forget the gate fields: enumerate every registered route."""
    from app.main import create_app as make

    app = make()
    exempt = {
        "/api/v1/health",
        "/api/v1/admin/classification/reload",
        "/api/v1/admin/classification/overrides",
    }
    checked = 0
    for route in app.routes:
        if (
            not isinstance(route, APIRoute)
            or not route.path.startswith("/api/v1")
            or route.path in exempt
            or route.path.startswith(RETENTION_ADMIN)  # file-admin routes, no ranking rows
        ):
            continue
        model = route.response_model
        assert model is not None, route.path
        members = getattr(model, "__args__", None) or (model,)
        for m in members:
            fields = set(m.model_fields)
            if route.path in PUBLIC_DESCRIPTIVE_PATHS:  # descriptive directory: no gate fields
                assert "descriptive_only" in fields, (route.path, m.__name__)
                assert not {"publication_status", "gate_results"} & fields, route.path
                continue
            assert {"publication_status", "gate_results"} <= fields, (route.path, m.__name__)
        checked += 1
    assert checked >= 15
    internal = [
        r.path
        for r in app.routes
        if isinstance(r, APIRoute)
        and "/internal/" in r.path
        and not r.path.startswith(RETENTION_ADMIN)
    ]
    public = [
        r.path
        for r in app.routes
        if isinstance(r, APIRoute) and r.path.startswith("/api/v1/rankings")
    ]
    # Phase 5 chunk 4 adds four internal dynamic-ranking routes (catalog, ranking, preview,
    # coverage); the public /rankings/* surface is unchanged (the public twins live under
    # /dynamic-rankings).
    # Phase 6 cleanup adds /internal/players and /internal/players/{player_id} (gated directory).
    assert len(internal) == 12 and len(public) == 2
