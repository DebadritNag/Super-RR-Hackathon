"""Public descriptive endpoints on a synthetic reports folder (hand-checkable) plus guards.

The synthetic folder is built by the real builder from ``phase7_desc_helpers.synthetic_frame``.
"""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase6.cleanup_scans import forbidden_public_names, walk_json_keys, walk_model_fields
from app.phase7 import views as vw
from app.schemas import phase7 as sc7
from tests.phase4_api_helpers import build_store
from tests.phase7_desc_helpers import write_reports

P = "/api/v1/descriptive"
BANNED_TEXT = ("better", "best", "worse", "winner", "top 10", "top10", "rank")
RESPONSE_MODELS = (
    sc7.BatterListResponse,
    sc7.BowlerListResponse,
    sc7.PlayerProfileResponse,
    sc7.CompareResponse,
    sc7.RadarResponse,
    sc7.OverviewResponse,
    sc7.MethodologyResponse,
)


@pytest.fixture(scope="module")
def reports(tmp_path_factory):
    d = tmp_path_factory.mktemp("p7reports")
    write_reports(d)
    return d


@pytest.fixture(scope="module")
def client(reports):
    return TestClient(create_app(admin_token="tok", descriptive_reports=reports))


def lower_json(r) -> str:
    return r.text.lower()


# ----------------------------------------------------------------------------- schemas
@pytest.mark.parametrize("model", RESPONSE_MODELS, ids=lambda m: m.__name__)
def test_descriptive_models_have_no_score_rank_or_eligibility_fields(model):
    names = walk_model_fields(model)
    assert names
    assert forbidden_public_names(names) == []


def test_descriptive_routes_use_only_the_clean_models():
    app = create_app()
    paths = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith(P):
            assert forbidden_public_names(walk_model_fields(route.response_model)) == []
            paths.add(route.path)
    assert paths == {
        f"{P}/profiles/batters",
        f"{P}/profiles/bowlers",
        f"{P}/profiles/{{player_id}}",
        f"{P}/compare",
        f"{P}/radar",
        f"{P}/overview",
        f"{P}/methodology/summary",
    }


def test_no_composite_or_ordering_field_in_any_response_model():
    for model in RESPONSE_MODELS:
        names = {n.lower() for n in walk_model_fields(model)}
        assert not {"composite", "overall", "total_score", "winner", "better", "index"} & names


# ----------------------------------------------------------------------------- listings
def test_batter_listing_pagination_and_totals(client):
    r = client.get(f"{P}/profiles/batters?limit=5&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert (
        body["descriptive_only"] is True and body["status"] == "DESCRIPTIVE_NOT_A_PRESSURE_MEASURE"
    )
    assert body["page"] == {"total": 17, "limit": 5, "offset": 0}
    assert len(body["items"]) == 5
    nxt = client.get(f"{P}/profiles/batters?limit=5&offset=15").json()
    assert len(nxt["items"]) == 2 and nxt["page"]["total"] == 17
    ids = [i["player_id"] for i in body["items"]]
    assert len(set(ids)) == 5
    assert forbidden_public_names(walk_json_keys(body)) == []


def test_listing_filters(client):
    q = client.get(f"{P}/profiles/batters?q=player 02").json()
    assert {i["player_id"] for i in q["items"]} == {21, 22, 23, 24, 25}
    nat = client.get(f"{P}/profiles/batters?nationality=Indian&limit=200").json()
    assert nat["page"]["total"] == len([i for i in range(1, 13) if i % 2] + [21, 23, 25])
    assert client.get(f"{P}/profiles/batters?min_balls=81").json()["page"]["total"] == 0
    assert client.get(f"{P}/profiles/batters?format=T20I").json()["page"]["total"] == 0
    assert client.get(f"{P}/profiles/bowlers").json()["page"]["total"] == 3


def test_listing_rejects_unsafe_or_unknown_parameters(client):
    for url in (
        f"{P}/profiles/batters?sort_by=strike_rate",
        f"{P}/profiles/batters?sort_by=rank",
        f"{P}/profiles/batters?limit=201",
        f"{P}/profiles/batters?limit=0",
        f"{P}/profiles/batters?offset=-1",
        f"{P}/profiles/batters?format=OTHER_T20",
        f"{P}/profiles/batters?nationality=x' OR 1=1 --",
        f"{P}/profiles/batters?order=up",
    ):
        r = client.get(url)
        assert r.status_code == 422, url
        assert "error" in r.json()


def test_volume_sort_is_not_a_performance_order(client):
    r = client.get(f"{P}/profiles/batters?sort_by=volume&order=desc&limit=3").json()
    assert "not an ordering by performance" in r["sort_note"]
    assert [i["balls_faced"] for i in r["items"]] == sorted(
        [i["balls_faced"] for i in r["items"]], reverse=True
    )


def test_profile_numbers_match_the_builder_and_hand_calculation(client, reports):
    item = client.get(f"{P}/profiles/batters?q=Player 021").json()["items"][0]
    assert item["player_id"] == 21
    assert (item["balls_faced"], item["runs"], item["dismissals"]) == (80, 480, 0)
    assert item["strike_rate"] == pytest.approx(600.0)
    assert item["average"] is None  # no dismissals: unavailable, not 0
    assert item["balls_per_dismissal"] is None
    assert item["sixes"] == 80 and item["fours"] == 0
    assert item["boundary_run_share"] == pytest.approx(1.0)
    assert item["context_sample"]["label"] == "DESCRIPTIVE_EXPERIMENTAL_COUNT_ONLY"
    assert "average:NO_DISMISSALS" in item["quality"]["missing_value_notes"]
    splits = {s["key"]: s for s in item["splits"]}
    assert splits["pp"]["balls"] == 16 and splits["chase"]["balls"] == 0
    assert splits["chase"]["rate"] is None and splits["chase"]["runs"] is None
    assert splits["chase"]["unavailable_reason"] == "NO_BALLS_IN_SPLIT"


def test_bowler_listing_fields(client):
    items = client.get(f"{P}/profiles/bowlers?limit=10").json()["items"]
    assert [i["player_id"] for i in items] == [101, 102, 103]
    assert (
        sum(i["legal_balls"] for i in items) == 12 * 80 + 5 * 80 + 0
    )  # every ball is bowled by one of three
    for i in items:
        assert i["economy"] == pytest.approx(6 * i["runs_conceded"] / i["legal_balls"])


def test_player_profile_detail_and_404(client):
    r = client.get(f"{P}/profiles/21")
    assert r.status_code == 200
    body = r.json()
    assert body["player_id"] == 21 and len(body["batting"]) == 1 and body["bowling"] == []
    assert body["explanations"] and body["limitations"]
    assert forbidden_public_names(walk_json_keys(body)) == []
    assert client.get(f"{P}/profiles/999999").status_code == 404
    assert client.get(f"{P}/profiles/0").status_code == 422


def test_explanations_use_only_the_players_numbers_and_no_ranking_language(client):
    for pid in (21, 22, 1):
        text = " ".join(client.get(f"{P}/profiles/{pid}").json()["explanations"]).lower()
        assert not any(w in text for w in BANNED_TEXT), text
    t21 = " ".join(client.get(f"{P}/profiles/21").json()["explanations"])
    assert "480 runs from 80 balls" in t21 and "600.0 runs per 100 balls" in t21
    assert "count only" in t21


def test_explain_player_flags_small_samples():
    p = {
        "player_id": 5,
        "player_name": "Short Sample",
        "side": "batter",
        "format": "IPL",
        "seasons_covered": ["2024"],
        "balls_faced": 6,
        "runs": 9,
        "dismissals": 1,
        "matches_with_participation": 1,
        "strike_rate": 150.0,
        "ci_low": None,
        "ci_high": None,
        "ci_unavailable_reason": "FEWER_THAN_5_MATCHES",
        "average": 9.0,
        "dot_ball_share": 0.5,
        "fours": 1,
        "sixes": 0,
        "splits": [{"key": "pp", "label": "Powerplay overs", "balls": 6, "rate": 150.0}],
        "quality": {"sample_sufficiency": "LOW_SAMPLE", "sample_note": "fewer than 60 balls faced"},
        "context_sample": {"balls": 2},
    }
    text = " ".join(vw.explain_player(p))
    assert "No strike-rate range is given (FEWER_THAN_5_MATCHES)" in text
    assert "Small-sample warning" in text and "fewer than 30 balls" in text


# ----------------------------------------------------------------------------- compare
def test_compare_returns_values_denominators_ci_and_evidence(client):
    r = client.get(f"{P}/compare?player_ids=21,22&side=batter&format=IPL")
    assert r.status_code == 200
    body = r.json()
    assert [p["player_id"] for p in body["players"]] == [21, 22]
    sr = next(m for m in body["metrics"] if m["metric"] == "strike_rate")
    v = {x["player_id"]: x for x in sr["values"]}
    assert v[21]["value"] == pytest.approx(600.0) and v[21]["denominator"] == 80
    assert v[22]["value"] == 0.0 and v[22]["numerator"] == 0  # a real zero, with its runs
    d = sr["differences"][0]
    assert d["difference"] == pytest.approx(600.0)
    assert d["evidence"] == "SUPPORTED" and d["ci_low"] > 0
    assert "600.000" in d["text"] and "80 balls in 8 matches" in d["text"]
    assert forbidden_public_names(walk_json_keys(body)) == []
    assert not any(w in lower_json(r) for w in BANNED_TEXT)
    assert body["limitations"] and "bootstrap" in body["method"]


def test_compare_identical_patterns_are_not_distinguishable(client):
    body = client.get(f"{P}/compare?player_ids=23,24&side=batter&format=IPL").json()
    sr = next(m for m in body["metrics"] if m["metric"] == "strike_rate")
    d = sr["differences"][0]
    assert d["difference"] == 0.0
    assert d["evidence"] == "NOT_DISTINGUISHABLE"
    assert d["ci_low"] < 0 < d["ci_high"]


def test_compare_marks_zero_dismissals_unavailable_not_zero(client):
    body = client.get(f"{P}/compare?player_ids=21,22&side=batter&format=IPL").json()
    bpd = next(m for m in body["metrics"] if m["metric"] == "balls_per_dismissal")
    assert all(x["value"] is None for x in bpd["values"])
    assert all(x["unavailable_reason"] for x in bpd["values"])
    assert bpd["differences"][0]["evidence"] == "UNAVAILABLE"
    assert bpd["differences"][0]["difference"] is None


def test_compare_four_players_gives_six_pairs_per_metric(client):
    body = client.get(f"{P}/compare?player_ids=21,22,23,24&side=batter&format=IPL").json()
    assert all(len(m["differences"]) == 6 for m in body["metrics"])
    assert "24 pairwise differences" in body["summary"][0]


def test_compare_player_counts_and_ids_are_validated(client):
    assert client.get(f"{P}/compare?player_ids=21").status_code == 422
    assert client.get(f"{P}/compare?player_ids=1,2,3,4,5").status_code == 422
    assert client.get(f"{P}/compare?player_ids=21,21").status_code == 422
    assert client.get(f"{P}/compare?player_ids=21,abc").status_code == 422
    assert client.get(f"{P}/compare?player_ids=21,-3").status_code == 422
    assert client.get(f"{P}/compare?player_ids=21,999999").status_code == 404
    assert client.get(f"{P}/compare?player_ids=21,22&side=bowler").status_code == 404
    assert client.get(f"{P}/compare?player_ids=21,22&format=T20I").status_code == 404


def test_compare_bowlers(client):
    r = client.get(f"{P}/compare?player_ids=101,102&side=bowler&format=IPL")
    assert r.status_code == 200
    assert {m["metric"] for m in r.json()["metrics"]} == {
        "economy",
        "boundary_conceded_share",
        "dot_ball_share",
        "balls_per_wicket",
    }


def test_compare_interval_equals_the_profile_interval_for_the_main_rate(client):
    prof = client.get(f"{P}/profiles/batters?q=Player 003").json()["items"][0]
    assert prof["player_id"] == 3
    cmp_ = client.get(f"{P}/compare?player_ids=3,4&side=batter&format=IPL").json()
    sr = next(m for m in cmp_["metrics"] if m["metric"] == "strike_rate")
    v3 = next(x for x in sr["values"] if x["player_id"] == 3)
    assert v3["ci_low"] == pytest.approx(prof["ci_low"], abs=1e-5)
    assert v3["ci_high"] == pytest.approx(prof["ci_high"], abs=1e-5)


# ----------------------------------------------------------------------------- radar
def test_percentile_of_hand_values():
    import numpy as np

    c = np.array([1.0, 2.0, 3.0, 4.0])
    assert vw.percentile_of(2.0, c) == pytest.approx(37.5)
    assert vw.percentile_of(0.5, c) == 0.0
    assert vw.percentile_of(9.0, c) == 100.0
    assert vw.percentile_of(2.0, np.array([2.0, 2.0])) == 50.0


def test_radar_returns_raw_values_denominators_and_cohort(client):
    r = client.get(f"{P}/radar?player_ids=21&side=batter&format=IPL")
    assert r.status_code == 200
    body = r.json()
    assert "17" not in body["cohort_name"] and "IPL batters" in body["cohort_name"]
    dims = {d["key"]: d for d in body["players"][0]["dimensions"]}
    sr = dims["strike_rate"]
    assert sr["raw_value"] == pytest.approx(600.0)
    assert (sr["numerator"], sr["denominator"]) == (480, 80)
    assert sr["available"] is True and sr["cohort_size"] == 17
    assert sr["percentile_in_cohort"] == pytest.approx(
        100 * (16 + 0.5) / 17
    )  # highest of 17, own value counts as a half tie
    assert forbidden_public_names(walk_json_keys(body)) == []


def test_radar_missing_is_unavailable_not_zero(client):
    dims = {
        d["key"]: d
        for d in client.get(f"{P}/radar?player_ids=21&side=batter&format=IPL").json()["players"][0][
            "dimensions"
        ]
    }
    bpd = dims["balls_per_dismissal"]  # no dismissals
    assert bpd["raw_value"] is None and bpd["available"] is False
    assert bpd["percentile_in_cohort"] is None
    assert bpd["unavailable_reason"] == "VALUE_UNDEFINED_NO_DENOMINATOR"
    for key in ("pp_strike_rate", "death_strike_rate"):  # 16 and 24 balls, below the 30 minimum
        assert dims[key]["available"] is False
        assert dims[key]["raw_value"] is not None  # the raw value is shown with its denominator
        assert dims[key]["unavailable_reason"] == "BELOW_MIN_SAMPLE_30_BALLS"
    assert dims["mid_strike_rate"]["available"] is True  # 40 balls


def test_radar_has_no_composite_and_keeps_sides_separate(client):
    body = client.get(f"{P}/radar?player_ids=21,22&side=batter&format=IPL").json()
    assert set(body) == {
        "status",
        "disclaimer",
        "descriptive_only",
        "side",
        "format",
        "cohort_name",
        "cohort_definition",
        "percentile_definition",
        "players",
        "notes",
    }
    for p in body["players"]:
        assert set(p) == {"player_id", "player_name", "dimensions"}
        assert all("economy" not in d["key"] for d in p["dimensions"])
    b = client.get(f"{P}/radar?player_ids=101&side=bowler&format=IPL").json()
    assert all("strike_rate" not in d["key"] for d in b["players"][0]["dimensions"])
    assert (
        "does not say whether a higher or lower value is preferable" in b["percentile_definition"]
    )


def test_radar_small_cohort_returns_no_percentile(client):
    body = client.get(f"{P}/radar?player_ids=101&side=bowler&format=IPL").json()
    for d in body["players"][0]["dimensions"]:
        if d["raw_value"] is not None and d["cohort_size"] < 10:
            assert d["percentile_in_cohort"] is None and d["unavailable_reason"]


def test_radar_validation(client):
    assert client.get(f"{P}/radar?player_ids=1,2,3,4,5&side=batter").status_code == 422
    assert client.get(f"{P}/radar?player_ids=999999&side=batter").status_code == 404
    assert client.get(f"{P}/radar?player_ids=1&side=wicketkeeper").status_code == 422


# ----------------------------------------------------------------------------- overview
def test_overview_and_methodology_summary_read_the_context_file(client):
    o = client.get(f"{P}/overview")
    assert o.status_code == 200
    b = o.json()
    assert b["matches_total"] == 883 and b["delivery_rows_total"] == 200999
    assert b["lists_available"] is False and b["why_no_ordered_lists"]
    assert b["late_t20i_dates_unverified"] == 42
    assert b["reliability_checks"][0]["status"] == "NOT_MET"
    assert forbidden_public_names(walk_json_keys(b)) == []
    m = client.get(f"{P}/methodology/summary")
    assert m.status_code == 200
    assert m.json()["primary_definition_label"].startswith("PROVISIONAL")
    assert m.json()["reliability_facts"]["contexts_at_variance_floor"] == 48


# ----------------------------------------------------------------------------- cache, cors, access
def test_cache_returns_independent_copies_and_public_scope(reports):
    app = create_app(descriptive_reports=reports)
    svc = app.state.descriptive
    a = svc.cached("overview", {}, lambda: vw.overview(svc.data))
    a["matches_total"] = -1
    a["why_no_ordered_lists"].append("tampered")
    b = svc.cached("overview", {}, lambda: vw.overview(svc.data))
    assert b["matches_total"] == 883 and "tampered" not in b["why_no_ordered_lists"]
    assert svc.cache.stats()["hits"] >= 1


def test_cache_key_has_scope_and_versions(reports, monkeypatch):
    svc = create_app(descriptive_reports=reports).state.descriptive
    seen = {}
    real = svc.cache.get_or_compute

    def spy(spec, data_version, model_version, compute, **kw):
        seen.update(spec=spec, data_version=data_version, model_version=model_version, **kw)
        return real(spec, data_version, model_version, compute, **kw)

    monkeypatch.setattr(svc.cache, "get_or_compute", spy)
    svc.cached("overview", {}, lambda: {"x": 1})
    assert seen["scope"] == "public"
    assert seen["data_version"] == svc.data.version and len(seen["data_version"]) == 64
    assert seen["model_version"] == "p7_descriptive_v1"
    assert seen["gate_state"] == "none" and seen["lock_version"] == "none"


def test_changed_data_changes_the_version_and_the_answer(reports, tmp_path):
    import json
    import shutil

    other = tmp_path / "r2"
    shutil.copytree(reports, other)
    ctx = json.loads((other / "phase7_descriptive_context.json").read_text("utf-8"))
    ctx["overview"]["official"]["matches_total"] = 884
    (other / "phase7_descriptive_context.json").write_text(json.dumps(ctx), encoding="utf-8")
    c1 = TestClient(create_app(descriptive_reports=reports))
    c2 = TestClient(create_app(descriptive_reports=other))
    assert c1.get(f"{P}/overview").json()["matches_total"] == 883
    assert c2.get(f"{P}/overview").json()["matches_total"] == 884
    assert c1.app.state.descriptive.data.version != c2.app.state.descriptive.data.version


def test_missing_report_files_answer_503(tmp_path):
    c = TestClient(create_app(descriptive_reports=tmp_path))
    r = c.get(f"{P}/overview")
    assert r.status_code == 503 and r.json()["error"]["code"] == "DESCRIPTIVE_DATA_UNAVAILABLE"


def test_cors_allows_only_the_vite_origins(client):
    ok = client.options(
        f"{P}/overview",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(
        f"{P}/overview",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad.headers
    post = client.options(
        f"{P}/overview",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "DELETE"},
    )
    assert post.status_code == 400


def test_descriptive_routes_need_no_token_and_refuse_official_requests(client):
    assert client.get(f"{P}/overview").status_code == 200
    assert client.get(f"{P}/overview?official=true").status_code == 403


# ----------------------------------------------------------------------------- /players unchanged
def test_public_players_stays_clean_and_internal_stays_protected(tmp_path, reports):
    store = build_store(tmp_path)
    c = TestClient(create_app(store, admin_token="tok", descriptive_reports=reports))
    pub = c.get("/api/v1/players?limit=200")
    assert pub.status_code == 200
    body = pub.json()
    assert body["descriptive_only"] is True and "publication_status" not in body
    assert forbidden_public_names(walk_json_keys(body)) == []
    assert (
        c.get("/api/v1/players?min_pressure_matches=9999&limit=200").json()["page"]["total"]
        == (body["page"]["total"])
    )
    assert c.get("/api/v1/internal/players").status_code == 401
    assert (
        c.get("/api/v1/internal/players?limit=2", headers={"X-Admin-Token": "tok"}).status_code
        == 200
    )
    gated = c.get("/api/v1/compare?player_ids=1,2")
    assert gated.status_code == 403  # the gated pressure compare is untouched
    assert "min_pressure_matches" not in str(
        c.get("/openapi.json").json()["paths"]["/api/v1/players"]
    )
