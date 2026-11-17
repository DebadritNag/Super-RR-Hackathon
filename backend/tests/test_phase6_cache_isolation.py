"""Ranking-cache isolation (Phase 6 cleanup, decision 6d).

Cache keys carry the filter hash, data/model/lock versions, gate state and visibility scope, and
cached payloads are private copies: mutating a response never changes a later response.
"""

from __future__ import annotations

import copy
import dataclasses
import threading

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase4 import classification as cl
from app.phase5.cache import GATE_CONFIG_VERSION, RankingCache, cache_key, gate_state_hash
from app.phase5.filters import FilterSpec
from tests.phase4_api_helpers import all_pass_gates
from tests.phase5_ctx_helpers import build_all, build_context_store, make_cfg, synth_stats

P = "/api/v1"
TOKEN = "tok"
H = {"X-Admin-Token": TOKEN}
SPEC = FilterSpec(role="batter", format="IPL", limit=5)
KW = {"scope": "internal", "lock_version": "l1", "gate_state": "s1"}


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("p6cache")
    stats = synth_stats()
    art = build_all(stats, make_cfg(300))
    store = build_context_store(tmp, stats, art)
    overrides = tmp / "overrides.csv"
    overrides.write_text(",".join(cl.OVERRIDE_COLUMNS) + "\n", encoding="utf-8")
    return {"store": store, "overrides": overrides}


def make_app(env, gates=None):
    return create_app(env["store"], env["overrides"], admin_token=TOKEN, gate_inputs=gates)


# ----------------------------------------------------------------------------- key components
BASE = ("spec", "d1", "m1", GATE_CONFIG_VERSION, "internal", "l1", "s1")


def test_every_key_component_changes_the_key():
    base = cache_key(*BASE)
    assert cache_key(*BASE) == base
    variants = []
    for i, alt in enumerate(["spec2", "d2", "m2", "g2", "public", "l2", "s2"]):
        parts = list(BASE)
        parts[i] = alt
        variants.append(cache_key(*parts))
    assert len({base, *variants}) == 8


def test_key_encoding_has_no_delimiter_collisions():
    a = cache_key("a|b", "c", "m", "g", "internal", "l", "s")
    b = cache_key("a", "b|c", "m", "g", "internal", "l", "s")
    assert a != b


def test_unknown_scope_is_refused():
    with pytest.raises(ValueError):
        cache_key("s", "d", "m", "g", "everyone", "l", "s")


def test_gate_state_hash_depends_on_the_failing_set_not_its_order():
    assert gate_state_hash(["b", "a"]) == gate_state_hash(["a", "b"])
    assert gate_state_hash(["a"]) != gate_state_hash(["a", "b"])
    assert gate_state_hash([]) != gate_state_hash(["a"])


# ----------------------------------------------------------------------------- copy isolation
def test_mutating_a_computed_value_does_not_change_the_cached_entry():
    cache = RankingCache(4)
    first, hit = cache.get_or_compute(
        "s", "d", "m", lambda: {"rows": [{"id": 1}], "versions": {"v": 1}}, **KW
    )
    assert hit is False
    first["rows"][0]["id"] = 999
    first["versions"]["v"] = 999
    second, hit2 = cache.get_or_compute("s", "d", "m", lambda: {"never": 1}, **KW)
    assert hit2 is True
    assert second == {"rows": [{"id": 1}], "versions": {"v": 1}}


def test_mutating_a_cache_hit_does_not_change_later_hits():
    cache = RankingCache(4)
    cache.get_or_compute("s", "d", "m", lambda: {"rows": [{"id": 1}]}, **KW)
    hit1, _ = cache.get_or_compute("s", "d", "m", lambda: {}, **KW)
    hit1["rows"].append({"id": 2})
    hit1["rows"][0]["id"] = -1
    hit2, _ = cache.get_or_compute("s", "d", "m", lambda: {}, **KW)
    assert hit2 == {"rows": [{"id": 1}]}
    assert hit1 is not hit2


def test_put_stores_a_copy_of_the_callers_object():
    cache = RankingCache(4)
    obj = {"rows": [1, 2]}
    cache.put("k", obj)
    obj["rows"].append(3)
    assert cache.get("k") == {"rows": [1, 2]}


# ----------------------------------------------------------------------------- no collisions
def test_scope_gate_state_and_lock_never_share_an_entry():
    cache = RankingCache(16)
    calls = []

    def make(tag):
        def compute():
            calls.append(tag)
            return {"tag": tag}

        return compute

    _, h1 = cache.get_or_compute("s", "d", "m", make("internal"), **KW)
    _, h2 = cache.get_or_compute("s", "d", "m", make("public"), **{**KW, "scope": "public"})
    _, h3 = cache.get_or_compute("s", "d", "m", make("gate"), **{**KW, "gate_state": "s2"})
    assert (h1, h2, h3) == (False, False, False)
    v, h4 = cache.get_or_compute("s", "d", "m", make("again"), **KW)
    assert h4 is True and v == {"tag": "internal"}
    v5, h5 = cache.get_or_compute("s", "d", "m", make("x"), **{**KW, "scope": "public"})
    assert h5 is True and v5 == {"tag": "public"}
    assert calls == ["internal", "public", "gate"]


def test_data_model_or_lock_version_change_drops_old_entries():
    cache = RankingCache(16)
    cache.get_or_compute("s", "d1", "m1", lambda: 1, **KW)
    _, hit = cache.get_or_compute("s", "d1", "m1", lambda: 2, **KW)
    assert hit is True
    _, hit_d = cache.get_or_compute("s", "d2", "m1", lambda: 3, **KW)
    _, hit_m = cache.get_or_compute("s", "d2", "m2", lambda: 4, **KW)
    _, hit_l = cache.get_or_compute("s", "d2", "m2", lambda: 5, **{**KW, "lock_version": "l2"})
    assert (hit_d, hit_m, hit_l) == (False, False, False)
    assert cache.invalidations == 3 and cache.stats()["entries"] == 1


def test_concurrent_access_returns_equal_but_distinct_objects():
    cache = RankingCache(8)
    out: list[dict] = []
    errors: list[BaseException] = []

    def work():
        try:
            v, _ = cache.get_or_compute("s", "d", "m", lambda: {"rows": list(range(50))}, **KW)
            v["rows"].append("mine")  # each caller mutates its own copy
            out.append(v)
        except BaseException as exc:  # noqa: BLE001 - reported below
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(out) == 8
    assert len({id(v) for v in out}) == 8
    assert all(v["rows"] == [*range(50), "mine"] for v in out)
    assert cache.get(cache_key("s", "d", "m", GATE_CONFIG_VERSION, "internal", "l1", "s1")) == {
        "rows": list(range(50))
    }


# ----------------------------------------------------------------------------- service level
def test_mutating_a_service_response_does_not_change_the_next_response(env):
    app = make_app(env)
    svc = app.state.service5
    first = svc.ranking(SPEC, internal=True)
    pristine = copy.deepcopy(first)
    first["page"]["items"][0]["score"] = -123.0
    first["page"]["items"].append({"junk": True})
    first["versions"]["model_version"] = "tampered"
    first["stage_counts"]["tampered"] = 1
    second = svc.ranking(SPEC, internal=True)
    assert second["cache_hit"] is True and first["cache_hit"] is False
    pristine["cache_hit"] = True
    assert second == pristine
    third = svc.ranking(SPEC, internal=True)
    assert third == second and third is not second


def test_api_responses_are_repeatable_after_a_mutating_client(env):
    c = TestClient(make_app(env))
    body = {"role": "bowler", "format": "T20I", "phase": "death", "limit": 4}
    a = c.post(f"{P}/internal/rankings/dynamic", json=body, headers=H).json()
    a["page"]["items"].clear()
    b = c.post(f"{P}/internal/rankings/dynamic", json=body, headers=H).json()
    d = c.post(f"{P}/internal/rankings/dynamic", json=body, headers=H).json()
    assert b["cache_hit"] is True and b["page"] == d["page"] and len(b["page"]["items"]) > 0


def test_internal_and_public_scopes_use_separate_cache_entries(env):
    app = make_app(env, gates=all_pass_gates())
    svc = app.state.service5
    internal = svc.ranking(SPEC, internal=True)
    public = svc.ranking(SPEC, internal=False)
    assert internal["cache_hit"] is False
    assert public["cache_hit"] is False  # a public caller never reads the internal entry
    assert svc.ranking(SPEC, internal=False)["cache_hit"] is True
    assert svc.ranking(SPEC, internal=True)["cache_hit"] is True
    assert svc.cache.stats()["entries"] == 2
    assert public["publication_status"] == "PUBLIC_ALLOWED"
    assert internal["page"]["items"] == public["page"]["items"]


def test_a_change_of_gate_state_misses_the_cache(env):
    app = make_app(env, gates=all_pass_gates())
    svc = app.state.service5
    assert svc.ranking(SPEC, internal=True)["cache_hit"] is False
    assert svc.ranking(SPEC, internal=True)["cache_hit"] is True
    failing_methodology = dataclasses.replace(all_pass_gates(), methodology={"validated": False})
    app.state.service._gate_override = failing_methodology
    assert svc.ranking(SPEC, internal=True)["cache_hit"] is False
    assert svc.ranking(SPEC, internal=True)["cache_hit"] is True


def test_the_lock_config_hash_is_part_of_the_service_key(env, monkeypatch):
    app = make_app(env)
    svc = app.state.service5
    assert svc.ranking(SPEC, internal=True)["cache_hit"] is False
    assert svc.ranking(SPEC, internal=True)["cache_hit"] is True
    monkeypatch.setattr(type(svc), "_lock_version", staticmethod(lambda: "other-lock"))
    assert svc.ranking(SPEC, internal=True)["cache_hit"] is False
