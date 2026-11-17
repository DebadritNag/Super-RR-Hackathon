"""Phase 7 live endpoint probe (FastAPI TestClient against the real read-only store).

Checks the Phase 6 public/internal separation and the ranking-cache isolation with real calls.
Writes data/reports/phase7_endpoint_probe.json. Never writes to either DuckDB.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.phase5.cache import RankingCache, cache_key

REP = Path("d:/Data/backend/data/reports")
FORBIDDEN = re.compile(
    r"score|rank|eligib|interval|top10|inclusion|publication|gate|shrunk|residual|pressure|conflict",
    re.I,
)
TOKEN = "probe-token-not-a-secret"


def walk_keys(obj, found: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(str(k))
            walk_keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            walk_keys(v, found)


def main() -> None:
    res: dict = {}
    client = TestClient(create_app(admin_token=TOKEN))
    H = {"X-Admin-Token": TOKEN}

    r = client.get("/api/v1/players", params={"limit": 3})
    body = r.json()
    keys: set[str] = set()
    walk_keys(body, keys)
    res["public_players"] = {
        "status": r.status_code,
        "keys": sorted(keys),
        "forbidden_keys": sorted(k for k in keys if FORBIDDEN.search(k)),
        "descriptive_only": body.get("descriptive_only"),
        "has_publication_status": "publication_status" in body,
        "items_returned": len(body.get("items", body.get("page", {}).get("items", []))),
        "total": body.get("total", body.get("page", {}).get("total")),
    }

    r2 = client.get("/api/v1/players", params={"min_pressure_matches": 5, "limit": 3})
    b2 = r2.json()
    res["public_min_pressure_matches_ignored"] = {
        "status": r2.status_code,
        "total_unfiltered": res["public_players"]["total"],
        "total_with_param": b2.get("total", b2.get("page", {}).get("total")),
    }
    schema = client.get("/openapi.json").json()
    pub_params = [
        p["name"] for p in schema["paths"]["/api/v1/players"]["get"].get("parameters", [])
    ]
    int_params = [
        p["name"] for p in schema["paths"]["/api/v1/internal/players"]["get"].get("parameters", [])
    ]
    res["openapi_params"] = {
        "public_players": pub_params,
        "internal_players": int_params,
        "public_has_min_pressure_matches": "min_pressure_matches" in pub_params,
        "internal_has_min_pressure_matches": "min_pressure_matches" in int_params,
    }

    res["internal_players"] = {
        "no_token": client.get("/api/v1/internal/players").status_code,
        "wrong_token": client.get(
            "/api/v1/internal/players", headers={"X-Admin-Token": "x"}
        ).status_code,
    }
    ri = client.get("/api/v1/internal/players", headers=H, params={"limit": 3})
    ik: set[str] = set()
    walk_keys(ri.json(), ik)
    res["internal_players"].update(
        {
            "with_token": ri.status_code,
            "has_eligible_scopes": "eligible_scopes" in ik,
            "has_conflict_flag": "conflict_flag" in ik,
            "has_publication_status": "publication_status" in ik,
        }
    )
    unconfigured = TestClient(create_app())
    res["internal_players"]["no_token_configured"] = unconfigured.get(
        "/api/v1/internal/players"
    ).status_code

    res["public_rankings_batter"] = client.get("/api/v1/rankings/batter").status_code
    res["public_dynamic_rankings"] = client.post(
        "/api/v1/dynamic-rankings", json={"role": "batter", "format": "IPL"}
    ).status_code

    # Live cache isolation through the service (internal vs public scope, copy semantics).
    spec = {"role": "batter", "format": "IPL"}
    a = client.post("/api/v1/internal/rankings/dynamic", headers=H, json=spec)
    res["cache_live"] = {"internal_first": a.status_code}
    if a.status_code == 200:
        first = a.json()
        second = client.post("/api/v1/internal/rankings/dynamic", headers=H, json=spec).json()
        res["cache_live"]["internal_second_cache_hit"] = second.get("cache_hit")
        pub = client.post("/api/v1/dynamic-rankings", json=spec)
        res["cache_live"]["public_status"] = pub.status_code
        stats = client.get("/api/v1/internal/filters/catalog", headers=H).json().get("cache", {})
        res["cache_live"]["stats"] = stats
        res["cache_live"]["first_has_cache_hit_false"] = first.get("cache_hit") is False
    svc = client.app.state.service5
    cache = svc.cache
    if cache is not None:
        # mutate a returned object and confirm the next read is unchanged
        before = json.dumps(
            svc.ranking(
                __import__("app.phase5.filters", fromlist=["FilterSpec"]).FilterSpec(**spec)
            ),
            sort_keys=True,
            default=str,
        )
        got = svc.ranking(
            __import__("app.phase5.filters", fromlist=["FilterSpec"]).FilterSpec(**spec)
        )
        got["page"]["items"].append({"INJECTED": True})
        got["versions"]["data_version"] = "MUTATED"
        after = json.dumps(
            svc.ranking(
                __import__("app.phase5.filters", fromlist=["FilterSpec"]).FilterSpec(**spec)
            ),
            sort_keys=True,
            default=str,
        )
        norm = lambda s: json.loads(s) | {"cache_hit": None}  # noqa: E731
        res["cache_live"]["mutation_leaks_into_cache"] = norm(before) != norm(after)

    # key construction: each component changes the key; scope separates entries
    base = ("s", "d", "m", "g", "internal", "l", "gs")
    k0 = cache_key(*base)
    changed = {}
    names = ["spec", "data", "model", "gate_version", "scope", "lock", "gate_state"]
    for i, n in enumerate(names):
        parts = list(base)
        parts[i] = "public" if n == "scope" else parts[i] + "X"
        changed[n] = cache_key(*parts) != k0
    res["cache_key_components_change_key"] = changed
    c = RankingCache()
    c.put(k0, {"a": [1]})
    g = c.get(k0)
    g["a"].append(2)
    res["cache_unit_copy_isolation"] = c.get(k0) == {"a": [1]}
    try:
        cache_key("s", "d", "m", "g", "other", "l", "gs")
        res["cache_unknown_scope_refused"] = False
    except ValueError:
        res["cache_unknown_scope_refused"] = True

    (REP / "phase7_endpoint_probe.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
