"""Dynamic ranking API: schemas, gating, admin protection, strict-uncapped, caching (Phase 5)."""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase4 import classification as cl
from app.phase5 import coverage as cov
from app.phase5.filters import FilterSpec, spec_hash
from app.phase5.store import write_p5_table
from app.repositories.phase5_repo import Phase5Repository
from app.schemas import phase5_dynamic as sd
from tests.phase4_api_helpers import all_pass_gates
from tests.phase5_ctx_helpers import build_all, build_context_store, make_cfg, synth_stats

P = "/api/v1"
INT = P + "/internal"
TOKEN = "tok"
H = {"X-Admin-Token": TOKEN}
APP = Path(__file__).resolve().parents[1] / "app"
DYN = INT + "/rankings/dynamic"


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("p5api")
    stats = synth_stats()
    art = build_all(stats, make_cfg(1000))
    store = build_context_store(tmp, stats, art)
    overrides = tmp / "overrides.csv"
    overrides.write_text(",".join(cl.OVERRIDE_COLUMNS) + "\n", encoding="utf-8")
    return {"store": store, "overrides": overrides, "stats": stats, "art": art}


def client(env, token: str | None = TOKEN, gates=None) -> TestClient:
    return TestClient(
        create_app(env["store"], env["overrides"], admin_token=token, gate_inputs=gates)
    )


@pytest.fixture()
def c(env):
    return client(env)


# ----------------------------------------------------------------------------- catalog
def test_catalog_lists_enabled_and_disabled_values_with_reasons(c):
    r = c.get(INT + "/filters/catalog", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
    assert {g["gate_id"] for g in body["gate_results"]} >= {"data_weight_gate_passed"}
    f = body["filters"]
    assert body["strict_uncapped_enabled"] is False
    unc = next(i for i in f["status"] if i["value"] == "VERIFIED_UNCAPPED")
    assert unc["enabled"] is False and "authoritative" in unc["reason"]
    assert all(i["enabled"] for i in f["status"] if i["value"] != "VERIFIED_UNCAPPED")
    assert f["wickets_remaining_band"][0]["enabled"] is False
    assert f["all_rounder_role"][0]["enabled"] is False
    assert [i["value"] for i in f["role"]] == ["batter", "bowler"]
    assert [i["value"] for i in f["phase"]] == ["ALL", "powerplay", "middle", "death"]
    assert set(body["semantics"]) >= {"and", "roles", "unknown_toggles", "context_filters", "order"}
    sd.CatalogResponse.model_validate(body)


# ----------------------------------------------------------------------------- admin protection
def _internal_routes(app):
    return [r for r in app.routes if isinstance(r, APIRoute) and r.path.startswith(INT + "/")
            and ("dynamic" in r.path or "filters" in r.path)]  # fmt: skip


def test_every_internal_dynamic_route_needs_the_token(env):
    app = create_app(env["store"], env["overrides"], admin_token=TOKEN)
    routes = _internal_routes(app)
    assert len(routes) == 4
    c = TestClient(app)
    for rt in routes:
        method = sorted(rt.methods - {"HEAD", "OPTIONS"})[0]
        kw = {"json": {"role": "batter"}} if method == "POST" else {}
        assert c.request(method, rt.path, **kw).status_code == 401, rt.path
        wrong = c.request(method, rt.path, headers={"X-Admin-Token": "nope"}, **kw)
        assert wrong.status_code == 401 and wrong.json()["error"]["code"] == "ADMIN_AUTH_FAILED"
        assert c.request(method, rt.path, headers=H, **kw).status_code == 200, rt.path
    off = TestClient(create_app(env["store"], env["overrides"], admin_token=None))
    for rt in routes:
        method = sorted(rt.methods - {"HEAD", "OPTIONS"})[0]
        kw = {"json": {"role": "batter"}} if method == "POST" else {}
        r = off.request(method, rt.path, headers=H, **kw)
        assert r.status_code == 503 and r.json()["error"]["code"] == "ADMIN_DISABLED"


# ----------------------------------------------------------------------------- ranking
def test_ranking_response_schema_gating_and_explanation(c):
    r = c.post(DYN, json={"role": "batter", "format": "IPL", "limit": 5}, headers=H)
    assert r.status_code == 200
    body = r.json()
    model = sd.DynamicRankingResponse.model_validate(body)
    assert model.publication_status == "INTERNAL_EXPERIMENTAL_ONLY"
    assert model.official_ranking is False and len(model.gate_results) == 5
    assert body["spec_hash"] == spec_hash(FilterSpec(role="batter", format="IPL"))
    assert body["filter_echo"]["role"] == "batter" and body["filter_echo"]["limit"] == 5
    assert body["versions"]["definition_label"] == "PROVISIONAL"
    assert body["versions"]["model_version"] == "p5_context_v1_train"
    items = body["page"]["items"]
    assert [i["rank"] for i in items] == [1, 2, 3, 4, 5]
    assert body["page"]["total"] == body["pool_size"] >= 5
    row = items[0]
    for k in ("raw", "expected", "residual", "shrunk", "interval_low", "interval_high",
              "top10_inclusion_prob", "rank_lo", "rank_hi", "n", "matches", "n_eff",
              "eligibility_status", "restrictions_applied", "international_status_verification"):  # fmt: skip
        assert k in row
    assert (
        row["nationality_verification"] and row["restrictions_applied"] == "synthetic restrictions"
    )


def test_second_identical_request_is_served_from_the_cache_with_equal_content(c):
    body = {"role": "bowler", "format": "T20I", "phase": "death"}
    a = c.post(DYN, json=body, headers=H).json()
    b = c.post(DYN, json=body, headers=H).json()
    assert (a["cache_hit"], b["cache_hit"]) == (False, True)
    assert a["page"] == b["page"] and a["spec_hash"] == b["spec_hash"]
    page2 = c.post(DYN, json={**body, "limit": 3, "offset": 3}, headers=H).json()
    assert page2["cache_hit"] is True  # paging does not change the cache key
    assert [i["rank"] for i in page2["page"]["items"]] == [4, 5, 6][: len(page2["page"]["items"])]
    cat = c.get(INT + "/filters/catalog", headers=H).json()["cache"]
    assert cat["hits"] >= 2 and cat["entries"] >= 1


def test_cache_is_invalidated_when_the_stored_data_version_changes(env, tmp_path):
    stats = env["stats"]
    store = build_context_store(tmp_path, stats, env["art"])
    app = create_app(store, env["overrides"], admin_token=TOKEN)
    c = TestClient(app)
    body = {"role": "batter", "format": "IPL"}
    first = c.post(DYN, json=body, headers=H).json()
    assert c.post(DYN, json=body, headers=H).json()["cache_hit"] is True
    con = duckdb.connect(str(store))
    try:
        sc = con.execute("SELECT * FROM p5_context_scores").df()
    finally:
        con.close()
    top = first["page"]["items"][0]["player_id"]
    hit = (sc.comp == "IPL") & (sc.role == "batter") & (sc.phase == "ALL") & (sc.situation == "ALL")
    sc.loc[hit & (sc.player_id == top), "score"] -= 5.0
    write_p5_table(sc, "p5_context_scores", store)
    app.state.service5.repo.reset()
    after = c.post(DYN, json=body, headers=H).json()
    assert after["cache_hit"] is False
    assert after["versions"]["data_version"] != first["versions"]["data_version"]
    assert after["page"]["items"][0]["player_id"] != top


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"role": "all_rounder"},
        {"role": "batter", "format": "ODI"},
        {"role": "batter", "phase": "slog"},
        {"role": "batter", "situation": "powerplay"},
        {"role": "batter", "nationality": "Martian"},
        {"role": "batter", "status": "Uncapped"},
        {"role": "batter", "limit": 0},
        {"role": "batter", "limit": 51},
        {"role": "batter", "offset": -1},
        {"role": "batter", "offset": 10001},
        {"role": "batter", "sort": "player_id; DROP TABLE x"},
        {"role": "batter", "order": "sideways"},
        {"role": "batter", "min_matches": -1},
        {"role": "batter", "sql": "select 1"},
        {"role": "batter", "path": "C:/Windows/system.ini"},
        {"role": "batter", "table": "p5_context_scores"},
        {"role": "batter", "wickets_remaining": 3},
    ],
)
def test_invalid_requests_are_rejected_without_touching_the_store(c, body):
    for url in (DYN, DYN + "/context-preview"):
        r = c.post(url, json=body, headers=H)
        assert r.status_code == 422, (url, body)
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_routes_import_no_sql_or_filesystem_access():
    for rel in ("api/v1/routes_phase5.py", "services/phase5_service.py", "phase5/filters.py"):
        tree = ast.parse((APP / rel).read_text(encoding="utf-8"))
        mods = {
            a.name.split(".")[0]
            for n in ast.walk(tree)
            if isinstance(n, ast.Import)
            for a in n.names
        }
        mods |= {
            (n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
        }
        assert not mods & {"duckdb", "os", "pathlib", "subprocess", "sqlite3", "shutil"}, rel
        calls = {
            n.func.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        assert not calls & {"open", "eval", "exec"}, rel


# ----------------------------------------------------------------------------- preview
def test_context_preview_counts_before_ranking_and_returns_no_rows(c):
    body = {"role": "batter", "format": "IPL", "nationality": "Indian", "phase": "death"}
    pv = c.post(DYN + "/context-preview", json=body, headers=H)
    assert pv.status_code == 200
    p = pv.json()
    sd.ContextPreviewResponse.model_validate(p)
    assert "page" not in p and "rows" not in p
    rk = c.post(DYN, json=body, headers=H).json()
    assert p["qualifying_players"] == p["pool_size"] == rk["pool_size"]
    assert p["stage_counts"] == rk["stage_counts"] and p["excluded_counts"] == rk["excluded_counts"]
    assert p["would_return_rows"] is (rk["pool_size"] >= 5)
    codes = {r["code"] for r in p["reasons"]}
    assert (
        "CLASSIFICATION_UNKNOWN_EXCLUDED" in codes
        or p["excluded_counts"]["unknown_nationality_excluded"] == 0
    )
    assert p["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
    inc = c.post(
        DYN + "/context-preview", json={**body, "include_unknown_nationality": True}, headers=H
    ).json()
    assert inc["pool_size"] == p["pool_size"] + p["excluded_counts"]["unknown_nationality_excluded"]


def test_empty_and_short_results_carry_reason_codes(c):
    r = c.post(DYN, json={"role": "bowler", "status": "VERIFIED_CAPPED"}, headers=H).json()
    assert r["result_status"] == "EMPTY" and r["page"]["items"] == [] and r["pool_size"] == 0
    codes = {x["code"] for x in r["reasons"]}
    assert {"CLASS_EMPTY", "POOL_TOO_SMALL"} <= codes
    assert r["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"


# ----------------------------------------------------------------------------- coverage
def test_coverage_endpoint_pagination_filters_and_minimum_pool_rule(c, env):
    r = c.get(INT + "/rankings/dynamic/coverage", params={"limit": 7, "role": "bowler"}, headers=H)
    assert r.status_code == 200
    body = r.json()
    sd.CoverageResponse.model_validate(body)
    assert (
        len(body["page"]["items"]) == 7 and body["page"]["total"] == body["summary"]["combinations"]
    )
    assert all(i["role"] == "bowler" for i in body["page"]["items"])
    assert body["minimum_pool_rule"]["min_internal_pool"] == 5
    assert body["minimum_pool_rule"]["min_public_pool"] == 10
    nxt = c.get(
        INT + "/rankings/dynamic/coverage",
        params={"limit": 7, "offset": 7, "role": "bowler"},
        headers=H,
    )
    assert nxt.json()["page"]["items"][0] != body["page"]["items"][0]
    dis = c.get(
        INT + "/rankings/dynamic/coverage", params={"status": "VERIFIED_UNCAPPED"}, headers=H
    ).json()
    assert dis["page"]["items"] and all(
        not i["enabled"] and i["final_pool"] == 0 for i in dis["page"]["items"]
    )
    ok = c.get(
        INT + "/rankings/dynamic/coverage",
        params={"meets_internal_min": True, "limit": 5},
        headers=H,
    ).json()
    assert all(i["final_pool"] >= 5 for i in ok["page"]["items"])
    assert (
        c.get(INT + "/rankings/dynamic/coverage", params={"limit": 201}, headers=H).status_code
        == 422
    )
    assert (
        c.get(INT + "/rankings/dynamic/coverage", params={"role": "keeper"}, headers=H).status_code
        == 422
    )
    # a listed combination matches the ranking endpoint
    item = ok["page"]["items"][0]
    spec = {k: item[k] for k in ("format", "role", "phase", "situation")}
    if item["nationality"]:
        spec["nationality"] = item["nationality"]
    if item["status"]:
        spec["status"] = item["status"]
    spec["include_unknown_nationality"] = item["include_unknown_nationality"]
    spec["include_unknown_status"] = item["include_unknown_status"]
    rk = c.post(DYN, json=spec, headers=H).json()
    assert rk["spec_hash"] == item["spec_hash"] and rk["pool_size"] == item["final_pool"]


def test_stored_coverage_table_is_served_when_the_classification_matches(env, tmp_path):
    store = build_context_store(tmp_path, env["stats"], env["art"])
    app = create_app(store, env["overrides"], admin_token=TOKEN)
    svc = app.state.service5
    eng, cls = svc.engine(), svc._cls()
    write_p5_table(cov.build_coverage(eng, cls, False), "p5_context_coverage", store)
    app2 = create_app(store, env["overrides"], admin_token=TOKEN)
    r = TestClient(app2).get(INT + "/rankings/dynamic/coverage", headers=H).json()
    assert r["coverage_source"] == "STORED_TABLE"
    assert isinstance(app2.state.service5.repo, Phase5Repository)


# ----------------------------------------------------------------------------- public gating
PUBLIC = [
    ("POST", P + "/dynamic-rankings", {"json": {"role": "batter"}}),
    ("POST", P + "/dynamic-rankings/context-preview", {"json": {"role": "batter"}}),
    ("GET", P + "/dynamic-rankings/coverage", {}),
]


@pytest.mark.parametrize(("method", "url", "kw"), PUBLIC)
def test_public_routes_return_the_gate_response_without_rows(env, method, url, kw):
    for gates in (None, dataclasses.replace(all_pass_gates(), date_gate=None)):
        r = client(env, gates=gates).request(method, url, **kw)
        assert r.status_code == 403
        err = r.json()["error"]
        assert err["code"] == "PUBLICATION_GATE_NOT_SATISFIED"
        assert err["details"]["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
        failed = [
            g["gate_id"]
            for g in err["details"]["gate_results"]
            if g["applicable"] and not g["passed"]
        ]
        assert failed
        text = json.dumps(r.json())
        assert '"page"' not in text and '"rows"' not in text and "player_id" not in text


def test_public_routes_return_rows_only_when_every_gate_passes(env):
    ok = client(env, gates=all_pass_gates())
    r = ok.post(P + "/dynamic-rankings", json={"role": "batter", "format": "IPL", "limit": 3})
    assert r.status_code == 200 and r.json()["publication_status"] == "PUBLIC_ALLOWED"
    assert len(r.json()["page"]["items"]) == 3
    assert (
        ok.post(P + "/dynamic-rankings/context-preview", json={"role": "batter"}).status_code == 200
    )
    assert ok.get(P + "/dynamic-rankings/coverage").status_code == 200
    # a failing minimum pool is enforced after the rows are known
    big = client(env, gates=all_pass_gates(min_pool=1000))
    r2 = big.post(P + "/dynamic-rankings", json={"role": "batter", "format": "IPL"})
    assert r2.status_code == 403
    assert "min_eligible_pool" in json.dumps(r2.json()["error"]["details"]["gate_results"])
    # each single failing gate blocks the public route
    base = all_pass_gates()
    broken = {
        "data_weight_gate_passed": dataclasses.replace(base, cell_statuses={"IPL|batter": "THRESHOLD_NOT_VALIDATED"} | dict.fromkeys(["a", "b", "c"], "THRESHOLD_NOT_VALIDATED")),
        "methodology_validated": dataclasses.replace(base, methodology={"validated": False}),
        "date_verification": dataclasses.replace(base, date_gate={"passed": False, "detail": "x"}),
    }  # fmt: skip
    for gate_id, inp in broken.items():
        r3 = client(env, gates=inp).post(P + "/dynamic-rankings", json={"role": "batter"})
        assert r3.status_code == 403, gate_id
        res = r3.json()["error"]["details"]["gate_results"]
        assert next(g for g in res if g["gate_id"] == gate_id)["passed"] is False


# ----------------------------------------------------------------------------- strict uncapped
def test_strict_uncapped_is_disabled_on_every_route(c):
    bodies = [
        {"role": "batter", "status": "VERIFIED_UNCAPPED"},
        {"role": "bowler", "status": "VERIFIED_UNCAPPED", "nationality": "Indian"},
        {
            "role": "batter",
            "status": "VERIFIED_UNCAPPED",
            "nationality": "Overseas",
            "phase": "death",
        },
    ]
    for body in bodies:
        for url in (DYN, DYN + "/context-preview"):
            r = c.post(url, json=body, headers=H)
            assert r.status_code == 200
            d = r.json()
            assert d["result_status"] == "STRICT_UNCAPPED_DISABLED" and d["rows"] == []
            assert d["capability"]["enabled"] is False and d["source_needed"] and d["reason"]
            assert d["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
            assert d["filter_echo"]["status"] == "VERIFIED_UNCAPPED"
            assert "page" not in d
    # the earlier uncapped endpoints, all six presets and a custom uncapped constraint
    for kind in (
        "indian_batters",
        "indian_bowlers",
        "overseas_batters",
        "overseas_bowlers",
        "overall",
    ):
        d = c.get(f"{INT}/rankings/uncapped/{kind}", headers=H).json()
        assert d["result_status"] == "STRICT_UNCAPPED_DISABLED", kind
    presets = c.get(P + "/selection/presets").json()["items"]
    assert len(presets) == 6
    for pr in presets:
        d = c.post(f"{INT}/selection/presets/{pr['preset_id']}", json={}, headers=H).json()
        assert d["result_status"] == "STRICT_UNCAPPED_DISABLED", pr["preset_id"]
    custom = {"total": 5, "groups": {"IN_UNCAPPED": {"min": 1}}}
    assert (
        c.post(INT + "/selection/custom", json=custom, headers=H).json()["result_status"]
        == "STRICT_UNCAPPED_DISABLED"
    )
    # public twin: gate response first, no rows
    r = c.post(P + "/dynamic-rankings", json=bodies[0])
    assert r.status_code == 403 and r.json()["error"]["code"] == "PUBLICATION_GATE_NOT_SATISFIED"
    # a verified-capped filter is a valid, empty class (no verified source loaded)
    vc = c.post(DYN, json={"role": "batter", "status": "VERIFIED_CAPPED"}, headers=H).json()
    assert vc["result_status"] == "EMPTY" and "CLASS_EMPTY" in {x["code"] for x in vc["reasons"]}


def test_unknown_status_is_a_separate_labelled_group_never_uncapped(c):
    d = c.post(
        DYN, json={"role": "batter", "status": "UNKNOWN_STATUS", "format": "IPL"}, headers=H
    ).json()
    assert d["page"]["items"]
    assert {i["international_status"] for i in d["page"]["items"]} == {"UNKNOWN"}
    assert "UNCAPPED" not in json.dumps(d["page"])


def test_gate_fields_are_present_on_every_dynamic_response(c):
    for method, url, kw in (
        ("POST", DYN, {"json": {"role": "batter"}}),
        ("POST", DYN + "/context-preview", {"json": {"role": "bowler"}}),
        ("GET", INT + "/rankings/dynamic/coverage", {}),
        ("GET", INT + "/filters/catalog", {}),
    ):
        d = c.request(method, url, headers=H, **kw).json()
        assert d["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
        assert {g["gate_id"] for g in d["gate_results"]} == {
            "data_weight_gate_passed", "methodology_validated", "strict_classification_available",
            "min_eligible_pool", "date_verification",
        }  # fmt: skip
        assert d["official_ranking"] is False


def test_official_flags_are_refused_on_the_dynamic_routes(c):
    r = c.post(DYN + "?official=true", json={"role": "batter"}, headers=H)
    assert r.status_code == 403 and r.json()["error"]["code"] == "OFFICIAL_RANKING_NOT_AUTHORIZED"


# ----------------------------------------------------------------------------- store problems
def test_missing_context_tables_give_503_not_a_crash(env, tmp_path):
    from tests.phase4_api_helpers import build_store

    store = build_store(tmp_path)
    c = TestClient(create_app(store, env["overrides"], admin_token=TOKEN))
    r = c.post(DYN, json={"role": "batter"}, headers=H)
    assert r.status_code == 503 and r.json()["error"]["code"] == "STORE_UNAVAILABLE"
    assert isinstance(pd.DataFrame(), pd.DataFrame)
