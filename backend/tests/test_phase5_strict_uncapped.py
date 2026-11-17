"""Strict-uncapped capability and the STRICT_UNCAPPED_DISABLED responses (Phase 5)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase4 import classification as cl
from app.phase5 import classification_v2 as c2
from tests.phase4_api_helpers import (
    all_pass_gates,
    base_classification_v2,
    build_store,
    overrides_frame,
    write_strict_config,
)

P = "/api/v1"
TOKEN = "tok"
H = {"X-Admin-Token": TOKEN}
KINDS = ("indian_batters", "indian_bowlers", "overseas_batters", "overseas_bowlers", "overall")
PRESETS = (
    "best_indian_uncapped_xi",
    "top_indian_uncapped_batters",
    "top_indian_uncapped_bowlers",
    "best_overseas_uncapped_players",
    "emerging_domestic_talent",
    "mixed_capped_and_uncapped_xi",
)
CFG = {"min_verified_coverage": 0.5, "source_needed": "an authoritative id-keyed source"}
AUTH = {"sources": [{"id": "board", "authoritative": True, "id_keyed": True}]}


UNK = [*range(7, 13), *range(19, 25)]  # the synthetic players whose status is UNKNOWN


def _classification(verified: list[int] | None = None) -> pd.DataFrame:
    """Synthetic migrated classification with VERIFIED_UNCAPPED override rows for ``verified``."""
    base = base_classification_v2()
    if not verified:
        return base
    raw = pd.DataFrame(
        [
            (str(p), "international_status", "VERIFIED_UNCAPPED", "src", "me", "2026-01-01")
            for p in verified
        ],
        columns=list(cl.OVERRIDE_COLUMNS),
    )
    ov = c2.validate_overrides_v2(raw, base, date(2026, 6, 1))
    return c2.apply_overrides_v2(base, ov)


# ----------------------------------------------------------------------------- capability


def test_capability_is_false_today_with_empty_inputs():
    cap = c2.strict_uncapped_capability(
        _classification(), {"sources": [], "malformed": False}, range(1, 25), CFG
    )
    assert cap["enabled"] is False
    assert cap["reasons"] == [
        "NO_AUTHORITATIVE_SOURCE",
        "NO_VERIFIED_ROWS",
        "COVERAGE_BELOW_MINIMUM",
    ]
    assert cap["verified_coverage"] == 0.0 and cap["source_needed"] == CFG["source_needed"]


def test_shipped_manifest_and_overrides_give_a_disabled_capability():
    manifest = c2.load_source_manifest(
        c2.CLASSIFICATION_V2_CONFIG.parent / "classification_source_manifest_v1.json"
    )
    assert manifest == {"sources": [], "malformed": False}
    cap = c2.strict_uncapped_capability(_classification(), manifest, range(1, 25), c2.load_config())
    assert cap["enabled"] is False and cap["min_verified_coverage"] == 0.95


def test_capability_enabled_only_when_all_three_conditions_hold():
    cls = _classification(UNK)
    ok = c2.strict_uncapped_capability(cls, {**AUTH, "malformed": False}, UNK, CFG)
    assert ok["enabled"] is True and ok["reasons"] == [] and ok["verified_coverage"] == 1.0


@pytest.mark.parametrize(
    ("manifest", "verified", "pool", "reason"),
    [
        ({"sources": [], "malformed": False}, UNK, UNK, "NO_AUTHORITATIVE_SOURCE"),
        (
            {"sources": [{"authoritative": True, "id_keyed": False}], "malformed": False},
            UNK, UNK, "NO_AUTHORITATIVE_SOURCE",
        ),
        (
            {"sources": [{"authoritative": False, "id_keyed": True}], "malformed": False},
            UNK, UNK, "NO_AUTHORITATIVE_SOURCE",
        ),
        ({**AUTH, "malformed": False}, [], range(1, 25), "NO_VERIFIED_ROWS"),
        ({**AUTH, "malformed": False}, [7, 8], range(1, 25), "COVERAGE_BELOW_MINIMUM"),
        ({**AUTH, "malformed": False}, UNK, [], "COVERAGE_BELOW_MINIMUM"),
        ({"sources": [], "malformed": True}, UNK, UNK, "MANIFEST_MALFORMED"),
    ],
)  # fmt: skip
def test_each_missing_condition_keeps_the_flag_false(manifest, verified, pool, reason):
    cap = c2.strict_uncapped_capability(_classification(verified), manifest, pool, CFG)
    assert cap["enabled"] is False and reason in cap["reasons"]


def test_manifest_fails_closed_on_missing_or_malformed_file(tmp_path):
    assert c2.load_source_manifest(tmp_path / "absent.json")["malformed"] is True
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert c2.load_source_manifest(bad)["malformed"] is True
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"sources": "x"}), encoding="utf-8")
    assert c2.load_source_manifest(wrong)["malformed"] is True
    good = tmp_path / "good.json"
    good.write_text(json.dumps(AUTH), encoding="utf-8")
    assert c2.load_source_manifest(good) == {**AUTH, "malformed": False}


# ----------------------------------------------------------------------------- disabled responses


def _client(tmp_path: Path, **kw) -> TestClient:
    store = build_store(tmp_path)
    return TestClient(create_app(store, admin_token=TOKEN, **kw))


def _assert_disabled(body: dict) -> None:
    assert body["result_status"] == "STRICT_UNCAPPED_DISABLED"
    assert body["rows"] == []
    assert body["reason"] and "authoritative" in body["reason"]
    assert "player_id" in body["source_needed"]
    assert body["capability"]["enabled"] is False
    assert {"NO_AUTHORITATIVE_SOURCE", "NO_VERIFIED_ROWS"} <= set(body["capability"]["reasons"])
    assert body["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
    assert body["official_ranking"] is False
    assert "strict_classification_available" in body["failing_gates"]
    for forbidden in ("page", "selected", "items"):
        assert forbidden not in body


@pytest.fixture()
def internal_client(tmp_path):
    return _client(tmp_path)  # real gates: nothing public, internal routes behind the token


@pytest.mark.parametrize("kind", KINDS)
def test_every_uncapped_ranking_kind_is_disabled(internal_client, kind):
    r = internal_client.get(f"{P}/internal/rankings/uncapped/{kind}", headers=H)
    assert r.status_code == 200
    _assert_disabled(r.json())


@pytest.mark.parametrize("preset", PRESETS)
def test_every_preset_is_disabled_not_approximated(internal_client, preset):
    r = internal_client.post(f"{P}/internal/selection/presets/{preset}", headers=H)
    assert r.status_code == 200
    body = r.json()
    _assert_disabled(body)
    assert body["preset_id"] == preset
    catalog = internal_client.get(f"{P}/selection/presets").json()["items"]
    entry = [i for i in catalog if i["preset_id"] == preset][0]
    assert entry["available"] is False and entry["unavailable_reason"] == "STRICT_UNCAPPED_DISABLED"


@pytest.mark.parametrize(
    "groups",
    [
        {"IN_UNCAPPED": {"min": 1}},
        {"IN_UNCAPPED": {"exact": 3}},
        {"OS_UNCAPPED": {"min": 2}},
        {"OS_UNCAPPED": {"exact": 1}, "IN_CAPPED": {"exact": 2}},
    ],
)
def test_uncapped_composition_constraints_are_disabled(internal_client, groups):
    r = internal_client.post(
        f"{P}/internal/selection/custom", json={"total": 5, "groups": groups}, headers=H
    )
    assert r.status_code == 200
    _assert_disabled(r.json())


def test_include_uncapped_mode_and_uncapped_filters_are_disabled(internal_client):
    body = internal_client.post(
        f"{P}/internal/selection/custom",
        json={"total": 3, "uncapped_mode": "include_uncapped"},
        headers=H,
    ).json()
    _assert_disabled(body)
    for url in (
        f"{P}/internal/rankings/batter?classification=indian_uncapped",
        f"{P}/internal/rankings/bowler?classification=overseas_uncapped",
        f"{P}/internal/rankings/batter?classification=all_uncapped",
        f"{P}/internal/rankings/batter?uncapped_mode=include_uncapped",
        f"{P}/internal/players?classification=all_uncapped",
        f"{P}/internal/players?uncapped_mode=include_uncapped",
    ):
        r = internal_client.get(url, headers=H)
        assert r.status_code == 200, url
        _assert_disabled(r.json())
    for url in (
        f"{P}/players?classification=all_uncapped",
        f"{P}/players?uncapped_mode=include_uncapped",
    ):  # public directory: minimal disabled answer, no rows, no publication fields
        body = internal_client.get(url).json()
        assert body["result_status"] == "STRICT_UNCAPPED_DISABLED"
        assert "page" not in body and "rows" not in body and "gate_results" not in body


def test_requests_that_select_nothing_uncapped_still_work(internal_client):
    ok = internal_client.post(
        f"{P}/internal/selection/custom",
        json={
            "total": 4, "uncapped_mode": "exclude_uncapped",
            "groups": {"IN_UNCAPPED": {"max": 0}, "OS_UNCAPPED": {"exact": 0}},
        },
        headers=H,
    ).json()  # fmt: skip
    assert "result_status" not in ok and ok["selection_status"] in ("OK", "PARTIAL")
    assert all(not r["group"].endswith("UNCAPPED") for r in ok["selected"])
    r = internal_client.get(
        f"{P}/internal/rankings/batter?classification=capped_derived", headers=H
    )
    assert r.status_code == 200 and "page" in r.json()


def test_public_uncapped_routes_answer_the_gate_error_first(internal_client):
    for method, url in (
        ("get", f"{P}/rankings/uncapped/overall"),
        ("post", f"{P}/selection/presets/best_indian_uncapped_xi"),
        ("get", f"{P}/rankings/batter?classification=all_uncapped"),
    ):
        r = getattr(internal_client, method)(url)
        assert r.status_code == 403, url
        e = r.json()["error"]
        assert e["code"] == "PUBLICATION_GATE_NOT_SATISFIED"
        failed = {
            g["gate_id"]
            for g in e["details"]["gate_results"]
            if g["applicable"] and not g["passed"]
        }
        assert "strict_classification_available" in failed
        assert "rows" not in r.json() and "page" not in r.json()


def test_unknown_status_group_is_never_returned_as_uncapped(tmp_path):
    store = build_store(tmp_path, overrides_frame([(7, "international_status", "Uncapped")]))
    manifest, config = write_strict_config(tmp_path)
    c = TestClient(
        create_app(
            store, admin_token=TOKEN, gate_inputs=all_pass_gates(),
            source_manifest=manifest, classification_config=config,
        )
    )  # fmt: skip
    body = c.get(f"{P}/rankings/uncapped/overall?include_unverified_list=true&limit=200").json()
    assert {i["player_id"] for i in body["page"]["items"]} == {7}
    unknown = body["unverified_candidates"]
    assert unknown and all(i["group_label"] == "UNKNOWN_STATUS" for i in unknown)
    assert all(i["international_status"] == "UNKNOWN" for i in unknown)
    assert 7 not in {i["player_id"] for i in unknown}
    assert "NOT_PROVEN_CAPPED_IS_NOT_UNCAPPED" in body["unverified_note"]


def test_enabled_capability_lifts_the_block_through_the_validated_reload(tmp_path):
    store = build_store(tmp_path)
    manifest, config = write_strict_config(tmp_path)
    ov = tmp_path / "ov.csv"
    ov.write_text(",".join(cl.OVERRIDE_COLUMNS) + "\n", encoding="utf-8")
    c = TestClient(
        create_app(
            store, ov, admin_token=TOKEN, gate_inputs=all_pass_gates(),
            source_manifest=manifest, classification_config=config,
        )
    )  # fmt: skip
    assert (
        c.get(f"{P}/rankings/uncapped/overall").json()["result_status"]
        == "STRICT_UNCAPPED_DISABLED"
    )
    ov.write_text(
        ",".join(cl.OVERRIDE_COLUMNS)
        + "\n9,international_status,VERIFIED_UNCAPPED,Board,Ann,2026-01-01\n",
        encoding="utf-8",
    )
    out = c.post(f"{P}/admin/classification/reload", headers=H).json()
    assert out["strict_uncapped_enabled"] is True
    body = c.get(f"{P}/rankings/uncapped/overall").json()
    assert [i["player_id"] for i in body["page"]["items"]] == [9]
    assert body["page"]["items"][0]["international_status"] == "VERIFIED_UNCAPPED"
    # an invalid override file is rejected whole and nothing changes
    ov.write_text(
        ",".join(cl.OVERRIDE_COLUMNS) + "\n9,international_status,Uncapped,,,\n", encoding="utf-8"
    )
    bad = c.post(f"{P}/admin/classification/reload", headers=H)
    assert bad.status_code == 422
    assert "LEGACY_STATUS_VALUE" in bad.json()["error"]["message"]
    assert c.get(f"{P}/rankings/uncapped/overall").json()["page"]["total"] == 1
