"""FastAPI endpoints, schemas, gating, presets, uncapped rankings and profiles (Chunk 4)."""

from __future__ import annotations

import shutil
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase4 import classification as cl
from app.phase4 import uncapped as unc
from app.phase4.profiles import AXES, MIN_UNCAPPED_REFERENCE, percentile_rank
from app.phase4.views import ranking_frame
from app.phase5 import classification_v2 as c2
from app.repositories.phase4_repo import Phase4Repository, load_tables
from tests.phase4_api_helpers import (
    all_pass_gates,
    build_store,
    overrides_frame,
    write_strict_config,
)

P = "/api/v1"
UNCAPPED = [
    (7, "international_status", "Uncapped"),
    (8, "international_status", "Uncapped"),
    (9, "international_status", "Uncapped"),
    (19, "international_status", "Uncapped"),
    (20, "international_status", "Uncapped"),
]


def _client(
    tmp_path: Path, rows=None, token: str | None = None, strict: bool = False
) -> TestClient:
    """Phase 4 behaviour tests run with synthetic all-pass publication gates (Phase 5 mapping:
    legacy overrides are migrated; ``strict`` loads a synthetic authoritative source manifest)."""
    ov = overrides_frame(rows) if rows else None
    store = build_store(tmp_path, ov)
    overrides = tmp_path / "overrides.csv"
    overrides.write_text(",".join(cl.OVERRIDE_COLUMNS) + "\n", encoding="utf-8")
    kw = {}
    if strict:
        manifest, config = write_strict_config(tmp_path)
        kw = {"source_manifest": manifest, "classification_config": config}
    return TestClient(
        create_app(store, overrides, admin_token=token, gate_inputs=all_pass_gates(), **kw)
    )


@pytest.fixture()
def plain(tmp_path):
    return _client(tmp_path)


@pytest.fixture()
def with_uncapped(tmp_path):
    return _client(tmp_path, UNCAPPED, strict=True)


def _flags(body):
    assert body["status"] == "EXPERIMENTAL_NOT_VALIDATED"
    assert body["official_ranking"] is False
    assert body["disclaimer"]


def test_health_and_flags_on_every_experimental_response(plain):
    assert plain.get(f"{P}/health").json()["official_ranking"] is False
    # The public player directory is descriptive-only: it has its own flags (Phase 6 cleanup).
    for url in (f"{P}/players", f"{P}/players/1"):
        r = plain.get(url)
        assert r.status_code == 200, url
        assert r.json()["status"] == "EXPERIMENTAL_NOT_VALIDATED"
        assert r.json()["descriptive_only"] is True and r.json()["disclaimer"]
    for url in (
        f"{P}/players/1/profile",
        f"{P}/rankings/batter",
        f"{P}/rankings/bowler",
        f"{P}/rankings/uncapped/overall",
        f"{P}/compare?player_ids=1,2",
        f"{P}/selection/presets",
        f"{P}/meta/classification-coverage",
    ):
        r = plain.get(url)
        assert r.status_code == 200, url
        _flags(r.json())
    r = plain.post(f"{P}/selection/custom", json={"total": 3})
    assert r.status_code == 200
    _flags(r.json())


def test_ranking_rows_have_required_fields_and_no_padding(plain):
    body = plain.get(f"{P}/rankings/batter?format=IPL&limit=200").json()
    items = body["page"]["items"]
    required = {
        "player_id", "name", "nationality", "nationality_verification", "international_status",
        "international_status_verification", "eligibility", "score", "pressure_opportunities",
        "distinct_matches", "effective_sample_size", "interval_low", "interval_high",
        "restrictions_applied", "status", "official_ranking", "rank",
    }  # fmt: skip
    assert required <= set(items[0])
    assert body["page"]["total"] == body["pool_size"] == 22  # players 5 and 6 are not eligible
    assert [i["rank"] for i in items] == list(range(1, 23))
    scores = [i["score"] for i in items]
    assert scores == sorted(scores, reverse=True)
    assert all(i["eligibility"].startswith("ELIGIBLE") for i in items)
    assert body["shrinkage_config"] == "shrink_tau4"  # the shrink_none duplicates are ignored
    assert max(scores) < 1  # the 9.9 rows of the ignored configuration are absent
    inel = plain.get(f"{P}/rankings/batter?include_ineligible=true&limit=200").json()
    assert inel["page"]["total"] == 24
    assert {i["rank"] for i in inel["page"]["items"] if i["player_id"] in (5, 6)} == {None}


def test_bowler_score_is_negated_so_higher_is_better(plain):
    items = plain.get(f"{P}/rankings/bowler?limit=200").json()["page"]["items"]
    by = {i["player_id"]: i for i in items}
    # stored shrunk_estimate = -0.2 + 0.01 * pid (runs conceded vs baseline); score is its negative
    assert by[10]["score"] == pytest.approx(0.2 - 0.10)
    assert by[10]["rank"] < by[24]["rank"]
    assert by[10]["interval_low"] < by[10]["score"] < by[10]["interval_high"]


def test_pagination_and_safe_sorting(plain):
    p1 = plain.get(f"{P}/rankings/batter?limit=5&offset=0").json()["page"]
    p2 = plain.get(f"{P}/rankings/batter?limit=5&offset=5").json()["page"]
    assert p1["total"] == p2["total"] and p1["limit"] == 5 and p2["offset"] == 5
    assert not {i["player_id"] for i in p1["items"]} & {i["player_id"] for i in p2["items"]}
    assert plain.get(f"{P}/rankings/batter?limit=201").status_code == 422
    assert plain.get(f"{P}/rankings/batter?offset=-1").status_code == 422
    r = plain.get(f"{P}/rankings/batter?sort_by=player_name;DROP TABLE x")
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    asc = plain.get(f"{P}/players?sort_by=name&order=desc&limit=3").json()["page"]["items"]
    assert [i["name"] for i in asc] == ["Player 24", "Player 23", "Player 22"]


def test_no_sql_or_path_injection_surface(plain, tmp_path):
    r = plain.get(f"{P}/players", params={"q": "' OR 1=1; DROP TABLE p4_player_stats; --"})
    assert r.status_code == 200 and r.json()["page"]["total"] == 0
    assert plain.get(f"{P}/players", params={"q": "x" * 65}).status_code == 422
    assert plain.get(f"{P}/players/..%2F..%2Fsecret").status_code in (404, 422)
    assert plain.get(f"{P}/rankings/..").status_code in (404, 422)
    assert plain.get(f"{P}/players", params={"store": "C:/x.duckdb"}).status_code == 200  # ignored
    assert plain.get(f"{P}/players").json()["page"]["total"] == 24  # table untouched


def test_official_requests_are_refused(plain):
    for url in (f"{P}/rankings/batter?official=true", f"{P}/players?publish=true"):
        r = plain.get(url)
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "OFFICIAL_RANKING_NOT_AUTHORIZED"
    r = plain.post(f"{P}/selection/custom", json={"total": 3, "official": True})
    assert r.status_code == 403
    r = plain.post(f"{P}/selection/presets/best_indian_uncapped_xi", json={"official": True})
    assert r.status_code == 403


def test_error_model_and_not_found(plain):
    r = plain.get(f"{P}/players/9999")
    assert r.status_code == 404 and set(r.json()["error"]) == {"code", "message", "details"}
    assert plain.get(f"{P}/players/9999/profile").status_code == 404
    assert plain.get(f"{P}/compare?player_ids=1,9999").status_code == 404
    assert plain.get(f"{P}/compare?player_ids=1,2,3,4,5,6").status_code == 422
    assert plain.get(f"{P}/compare?player_ids=1,1").status_code == 422
    assert plain.post(f"{P}/selection/presets/nope").status_code == 404
    bad = plain.post(
        f"{P}/selection/custom", json={"total": 3, "groups": {"MARTIAN": {"exact": 1}}}
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "VALIDATION_ERROR"
    extra = plain.post(f"{P}/selection/custom", json={"total": 3, "sql": "select 1"})
    assert extra.status_code == 422


def test_missing_store_is_503(tmp_path):
    c = TestClient(create_app(tmp_path / "absent.duckdb"))
    r = c.get(f"{P}/rankings/batter")
    assert r.status_code == 503 and r.json()["error"]["code"] == "STORE_UNAVAILABLE"


def test_player_directory_filters(with_uncapped):
    c = with_uncapped

    def ids(qs):
        body = c.get(f"{P}/players?limit=200&{qs}").json()
        return {i["player_id"] for i in body["page"]["items"]}

    assert ids("classification=indian_uncapped") == {7, 8, 9}
    assert ids("classification=overseas_uncapped") == {19, 20}
    assert ids("classification=all_uncapped") == {7, 8, 9, 19, 20}
    assert ids("classification=capped_any") == set(range(1, 7)) | set(range(13, 19))
    assert ids("classification=unknown_international_status").isdisjoint({7, 8, 9, 19, 20})
    assert ids("uncapped_mode=exclude_uncapped") == set(range(1, 25)) - {7, 8, 9, 19, 20}
    assert ids("classification=all_uncapped&min_matches=50") == {
        19,
        20,
    }  # matches_played = 2 * (10 + pid)
    assert c.get(f"{P}/players?classification=martian").status_code == 422
    r = c.get(f"{P}/players?classification=all_uncapped&uncapped_mode=exclude_uncapped")
    assert r.status_code == 422 and r.json()["error"]["code"] == "CONFLICTING_FILTERS"


def test_uncapped_rankings_equal_filtered_main_ranking(with_uncapped, tmp_path):
    c = with_uncapped
    store = tmp_path / "synthetic_exploratory.duckdb"
    t = load_tables(store)
    basis = unc.ClassificationBasis.INCLUDE_DERIVED_CAPPED
    cases = {
        "indian_batters": ("batter", unc.ClassificationFilter.indian_uncapped),
        "overseas_batters": ("batter", unc.ClassificationFilter.overseas_uncapped),
        "indian_bowlers": ("bowler", unc.ClassificationFilter.indian_uncapped),
        "overseas_bowlers": ("bowler", unc.ClassificationFilter.overseas_uncapped),
    }
    for kind, (side, flt) in cases.items():
        main = ranking_frame(t, side, "IPL", basis)
        expected = unc.apply_filters(main, unc.FilterParams(flt))
        body = c.get(f"{P}/rankings/uncapped/{kind}?limit=200").json()
        got = body["page"]["items"]
        assert [i["player_id"] for i in got] == list(expected.sort_values("rank")["player_id"]), (
            kind
        )
        assert [i["score"] for i in got] == pytest.approx(
            list(expected.sort_values("rank")["score"])
        )
        assert [i["rank"] for i in got] == list(
            expected.sort_values("rank")["rank"]
        )  # main rank kept
        assert [i["view_rank"] for i in got] == list(range(1, len(got) + 1))
        assert all(i["international_status"] == "VERIFIED_UNCAPPED" for i in got)
        assert all(i["international_status_verification"] == cl.V_SOURCE for i in got)
    ib = c.get(f"{P}/rankings/uncapped/indian_batters").json()
    assert ib["verified_uncapped_in_pool"] == 5 and ib["page"]["total"] == 3
    ibw = c.get(f"{P}/rankings/uncapped/indian_bowlers").json()
    assert ibw["page"]["total"] == 0  # players 7-9 have no bowler score: bowlers start at id 10
    obw = c.get(f"{P}/rankings/uncapped/overseas_bowlers").json()
    assert {i["player_id"] for i in obw["page"]["items"]} == {19, 20}


def test_uncapped_ranking_reports_fewer_than_ten_and_excludes_unverified(with_uncapped):
    body = with_uncapped.get(f"{P}/rankings/uncapped/overall?include_unverified_list=true").json()
    assert body["page"]["total"] == 5 < 10
    ids = {i["player_id"] for i in body["page"]["items"]}
    unv = {i["player_id"] for i in body["unverified_candidates"]}
    assert ids == {7, 8, 9, 19, 20} and not ids & unv
    assert all(i["international_status"] == "UNKNOWN" for i in body["unverified_candidates"])
    assert all(i["group_label"] == "UNKNOWN_STATUS" for i in body["unverified_candidates"])
    assert "NOT verified uncapped" in body["unverified_note"]


def test_uncapped_ranking_is_disabled_without_verified_source(plain):
    # Phase 5: strict uncapped output is disabled (structured body, no rows, no approximation)
    body = plain.get(f"{P}/rankings/uncapped/indian_batters").json()
    assert body["result_status"] == "STRICT_UNCAPPED_DISABLED"
    assert body["rows"] == [] and "page" not in body
    assert body["capability"]["enabled"] is False
    assert "NO_AUTHORITATIVE_SOURCE" in body["capability"]["reasons"]


def test_custom_selection_example_and_infeasibility(with_uncapped):
    c = with_uncapped
    req = {
        "total": 10,
        "format": "IPL",
        "groups": {
            "IN_CAPPED": {"exact": 4},
            "IN_UNCAPPED": {"exact": 3},
            "OS_CAPPED": {"exact": 2},
            "OS_UNCAPPED": {"exact": 1},
        },
    }
    body = c.post(f"{P}/selection/custom", json=req).json()
    assert body["selection_status"] == "OK" and body["size"] == 10
    groups = [r["group"] for r in body["selected"]]
    assert {g: groups.count(g) for g in set(groups)} == {
        "IN_CAPPED": 4, "IN_UNCAPPED": 3, "OS_CAPPED": 2, "OS_UNCAPPED": 1,
    }  # fmt: skip
    assert len({r["player_id"] for r in body["selected"]}) == 10
    assert all(r["eligibility"].startswith("ELIGIBLE") for r in body["selected"])
    assert body["selected"][0]["view_rank"] == 1
    again = c.post(f"{P}/selection/custom", json=req).json()
    assert [r["player_id"] for r in again["selected"]] == [r["player_id"] for r in body["selected"]]
    big = {**req, "groups": {"OS_UNCAPPED": {"exact": 6}}, "total": 10}
    bad = c.post(f"{P}/selection/custom", json=big).json()
    assert bad["selection_status"] == "INFEASIBLE" and bad["selected"] == []
    e = [x for x in bad["explanations"] if x["constraint"] == "group OS_UNCAPPED min"][0]
    assert (e["required"], e["available"]) == (6, bad["available_by_group"]["OS_UNCAPPED"])
    assert e["available"] < 6


def test_custom_selection_exclude_uncapped_and_role_constraints(with_uncapped):
    r = with_uncapped.post(
        f"{P}/selection/custom",
        json={
            "total": 6,
            "uncapped_mode": "exclude_uncapped",
            "groups": {"IN_CAPPED": {"min": 1}, "OS_CAPPED": {"min": 1}},
            "roles": {"Bowler": {"min": 2}},
        },
    ).json()
    assert r["selection_status"] == "OK"
    assert all(x["group"] in ("IN_CAPPED", "OS_CAPPED") for x in r["selected"])  # UNKNOWN excluded
    assert sum(x["squad_role"] == "Bowler" for x in r["selected"]) >= 2
    assert r["excluded_unknown_role"] >= 0


def test_presets_degrade_honestly_without_verified_players(plain):
    items = plain.get(f"{P}/selection/presets").json()["items"]
    assert {i["preset_id"] for i in items} == {
        "best_indian_uncapped_xi", "top_indian_uncapped_batters", "top_indian_uncapped_bowlers",
        "best_overseas_uncapped_players", "emerging_domestic_talent", "mixed_capped_and_uncapped_xi",
    }  # fmt: skip
    for i in items:
        assert i["available"] is False and i["unavailable_reason"] == "STRICT_UNCAPPED_DISABLED"
        body = plain.post(f"{P}/selection/presets/{i['preset_id']}").json()
        assert body["result_status"] == "STRICT_UNCAPPED_DISABLED", i["preset_id"]
        assert body["rows"] == [] and "selected" not in body
        assert body["preset_id"] == i["preset_id"]


def test_presets_with_verified_players_return_fewer_when_pool_is_short(with_uncapped):
    c = with_uncapped
    b = c.post(f"{P}/selection/presets/top_indian_uncapped_batters").json()
    assert b["selection_status"] == "PARTIAL" and b["size"] == 3 < b["requested_total"]
    assert {r["player_id"] for r in b["selected"]} == {7, 8, 9}
    assert all(
        r["side"] == "batter" and r["international_status"] == "VERIFIED_UNCAPPED"
        for r in b["selected"]
    )
    xi = c.post(f"{P}/selection/presets/best_indian_uncapped_xi").json()
    assert (
        xi["selection_status"] == "POOL_TOO_SMALL" and xi["selected"] == []
    )  # only 3, never padded
    os_ = c.post(f"{P}/selection/presets/best_overseas_uncapped_players").json()
    assert {r["player_id"] for r in os_["selected"]} == {19, 20}
    talent = c.post(
        f"{P}/selection/presets/emerging_domestic_talent", json={"min_matches": 50}
    ).json()
    assert talent["selection_status"] == "POOL_TOO_SMALL"  # no verified Indian has 50 matches
    mixed = c.post(f"{P}/selection/presets/mixed_capped_and_uncapped_xi").json()
    assert mixed["selection_status"] == "OK" and mixed["size"] == 11
    g = [r["group"] for r in mixed["selected"]]
    assert g.count("IN_UNCAPPED") >= 2 and g.count("OS_UNCAPPED") >= 1


def test_profile_has_radar_data_and_insufficient_labels(plain):
    body = plain.get(f"{P}/players/12/profile?format=IPL").json()
    sides = {b["side"]: b for b in body["blocks"]}
    assert set(sides) == {"batter", "bowler"}
    bat = sides["batter"]
    assert [a["axis"] for a in bat["radar"]["axes"]] == [a.key for a in AXES["batter"]]
    for a in bat["radar"]["axes"]:
        assert a["formula"] and a["reference_overall_n"] >= 2
        assert a["label_uncapped"] == "INSUFFICIENT_DATA"  # nobody is verified uncapped here
        assert str(MIN_UNCAPPED_REFERENCE) in a["reason_uncapped"]
        assert a["percentile_uncapped"] is None
    assert bat["pressure"]["label"] == "OK"
    # player 12 is not eligible as a bowler
    assert sides["bowler"]["pressure"]["label"] == "INSUFFICIENT_DATA"
    assert "not eligible" in sides["bowler"]["pressure"]["reason"]
    pa = [a for a in sides["bowler"]["radar"]["axes"] if a["axis"] == "pressure_score"][0]
    assert pa["label_overall"] == "INSUFFICIENT_DATA" and pa["value"] is None
    assert bat["ranking_status"]["official_ranking"] is False


def test_profile_uncapped_percentile_and_strength_evidence(tmp_path):
    rows = [(p, "international_status", "Uncapped") for p in range(7, 13)]
    c = _client(tmp_path, rows)
    body = c.get(f"{P}/players/12/profile?format=IPL").json()
    bat = [b for b in body["blocks"] if b["side"] == "batter"][0]
    sr = [a for a in bat["radar"]["axes"] if a["axis"] == "strike_rate"][0]
    assert sr["reference_uncapped_n"] == 6 and sr["label_uncapped"] == "OK"
    assert 0 <= sr["percentile_uncapped"] <= 100
    for s in bat["strengths"]:
        axis = [a for a in bat["radar"]["axes"] if a["axis"] == s["axis"]][0]
        assert f"{axis['value']:.3f}" in s["evidence"] and s["percentile_overall"] >= 75
    # the player with a small sample is flagged rather than scored
    short = c.get(f"{P}/players/1/profile?format=T20I").json()
    t = [b for b in short["blocks"] if b["side"] == "batter"][0]
    assert any(a["label_overall"] == "INSUFFICIENT_DATA" for a in t["radar"]["axes"]) is True


def test_percentile_rank_hand_check():
    import numpy as np

    ref = np.array([1.0, 2.0, 3.0, 4.0])
    assert percentile_rank(3.0, ref, True) == pytest.approx(100 * (2 + 0.5) / 4)
    assert percentile_rank(3.0, ref, False) == pytest.approx(100 * (1 + 0.5) / 4)
    assert percentile_rank(10.0, ref, True) == 100.0
    with pytest.raises(ValueError):
        percentile_rank(1.0, np.array([]), True)


def test_compare_returns_profiles_for_requested_players(plain):
    body = plain.get(f"{P}/compare?player_ids=1,2,3&format=IPL").json()
    assert [i["player"]["player_id"] for i in body["items"]] == [1, 2, 3]


def test_coverage_endpoint_lists_all_nine_combinations(with_uncapped):
    cov = with_uncapped.get(f"{P}/meta/classification-coverage").json()["coverage"]
    combos = cov["summary"]["combinations_all_players"]
    assert len(combos) == 9  # 3 nationalities x 3 real status values
    # the 5 stored VERIFIED_UNCAPPED rows are the disabled placeholder, counted separately
    assert sum(c["players"] for c in combos) == 24 - 5
    assert cov["summary"]["disabled_placeholder_counts"] == {"VERIFIED_UNCAPPED": 5}
    assert cov["summary"]["uncapped_verified_count"] == 5


def test_admin_protection(tmp_path):
    (tmp_path / "a").mkdir()
    off = _client(tmp_path / "a")
    assert off.get(f"{P}/admin/classification/overrides").status_code == 503
    assert off.post(f"{P}/admin/classification/reload").json()["error"]["code"] == "ADMIN_DISABLED"
    (tmp_path / "b").mkdir()
    on = _client(tmp_path / "b", token="s3cret")
    assert on.get(f"{P}/admin/classification/overrides").status_code == 401
    bad = on.post(f"{P}/admin/classification/reload", headers={"X-Admin-Token": "wrong"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "ADMIN_AUTH_FAILED"
    ok = on.get(f"{P}/admin/classification/overrides", headers={"X-Admin-Token": "s3cret"})
    assert ok.status_code == 200 and ok.json() == {
        "count": 0, "items": [], "version": c2.CLASSIFICATION_V2_VERSION,
    }  # fmt: skip
    # public endpoints never need the token
    assert on.get(f"{P}/players?limit=1").status_code == 200


def test_admin_reload_applies_validated_overrides_and_rejects_invalid(tmp_path):
    store = build_store(tmp_path)
    ov = tmp_path / "ov.csv"
    ov.write_text(",".join(cl.OVERRIDE_COLUMNS) + "\n", encoding="utf-8")
    manifest, config = write_strict_config(tmp_path)
    c = TestClient(
        create_app(
            store, ov, admin_token="tok", gate_inputs=all_pass_gates(),
            source_manifest=manifest, classification_config=config,
        )
    )  # fmt: skip
    h = {"X-Admin-Token": "tok"}
    disabled = c.get(f"{P}/rankings/uncapped/overall").json()
    assert disabled["result_status"] == "STRICT_UNCAPPED_DISABLED"
    assert "NO_VERIFIED_ROWS" in disabled["capability"]["reasons"]
    ov.write_text(
        ",".join(cl.OVERRIDE_COLUMNS)
        + "\n7,international_status,VERIFIED_UNCAPPED,Cap sheet,Ann,2026-01-02\n",
        encoding="utf-8",
    )
    r = c.post(f"{P}/admin/classification/reload", headers=h)
    assert r.status_code == 200 and r.json()["overrides_applied"] == 1
    assert r.json()["uncapped_verified_count"] == 1 and r.json()["strict_uncapped_enabled"] is True
    body = c.get(f"{P}/rankings/uncapped/overall").json()
    assert [i["player_id"] for i in body["page"]["items"]] == [7]
    assert body["page"]["items"][0]["international_status_verification"] == cl.V_SOURCE
    listed = c.get(f"{P}/admin/classification/overrides", headers=h).json()
    assert listed["count"] == 1 and listed["items"][0]["source"] == "Cap sheet"
    # the base table is untouched so removing the override restores the original state
    ov.write_text(",".join(cl.OVERRIDE_COLUMNS) + "\n", encoding="utf-8")
    c.post(f"{P}/admin/classification/reload", headers=h)
    back = c.get(f"{P}/rankings/uncapped/overall").json()
    assert back["result_status"] == "STRICT_UNCAPPED_DISABLED"
    # an invalid file is rejected and nothing changes
    ov.write_text(
        ",".join(cl.OVERRIDE_COLUMNS) + "\n7,nationality,Martian,s,v,2026-01-01\n", encoding="utf-8"
    )
    bad = c.post(f"{P}/admin/classification/reload", headers=h)
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "INVALID_CLASSIFICATION_CONFIG"
    assert (
        c.get(f"{P}/rankings/uncapped/overall").json()["result_status"]
        == "STRICT_UNCAPPED_DISABLED"
    )


def test_classification_never_fabricates_uncapped_in_synthetic_store(plain):
    items = plain.get(f"{P}/players?limit=200").json()["page"]["items"]
    assert not [i for i in items if i["international_status"] == "VERIFIED_UNCAPPED"]
    assert all(i["international_status_verification"] in (cl.V_T20I, cl.V_NONE) for i in items)


def test_loader_ignores_test_window_and_noncarried_rows(tmp_path):
    store = build_store(tmp_path)
    con = duckdb.connect(str(store))
    con.execute(
        "INSERT INTO p4_pressure_scores_frozen_rules SELECT * REPLACE ('TEST' AS \"window\") "
        "FROM p4_pressure_scores_frozen_rules WHERE player_id = 1 AND role = 'batter' LIMIT 1"
    )
    con.close()
    t = load_tables(store, "shrink_tau4")
    assert set(t.scores["window"]) == {"PRE_TEST"}


def test_repository_reads_frozen_shrinkage_file(tmp_path):
    frozen = tmp_path / "frozen.json"
    store = build_store(tmp_path, frozen=frozen)
    from app.repositories.phase4_repo import frozen_shrinkage

    assert frozen_shrinkage(frozen) == "shrink_tau4"
    assert frozen_shrinkage(tmp_path / "missing.json") is None
    repo = Phase4Repository(store)
    assert repo.tables.meta["status"] == "EXPERIMENTAL_NOT_VALIDATED"
    shutil.rmtree(tmp_path / "unused", ignore_errors=True)
