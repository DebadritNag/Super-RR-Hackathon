"""Dynamic ranking checks on the real analytical store (skipped when it is absent)."""

from __future__ import annotations

import duckdb
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase5.filters import FilterSpec, spec_hash
from app.repositories.phase5_repo import Phase5Repository
from app.services.pressure_service import EXPLORATORY_DB

pytestmark = pytest.mark.realdata

H = {"X-Admin-Token": "tok"}
DYN = "/api/v1/internal/rankings/dynamic"


def _have_tables() -> bool:
    if not EXPLORATORY_DB.exists():
        return False
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        have = {
            t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
    finally:
        con.close()
    return {"p5_context_stats", "p5_context_scores", "p5_context_coverage"} <= have


@pytest.fixture(scope="module")
def real():
    if not _have_tables():
        pytest.skip("context tables not built (run scripts/phase5_context_engine.py)")
    app = create_app(admin_token="tok")
    return TestClient(app), app


def test_stored_context_rows_hold_no_test_period_matches():
    if not _have_tables():
        pytest.skip("context tables not built")
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        periods = {
            p for (p,) in con.execute("SELECT DISTINCT period FROM p5_context_stats").fetchall()
        }
        leaked = con.execute(
            "SELECT count(*) FROM p5_context_stats s JOIN p4_match_period p USING (match_id) "
            "WHERE p.period = 'TEST'"
        ).fetchone()[0]
    finally:
        con.close()
    assert periods <= {"TRAIN", "VALIDATION"} and leaked == 0


def test_overall_context_reproduces_the_phase4_scores():
    if not _have_tables():
        pytest.skip("context tables not built")
    con = duckdb.connect(str(EXPLORATORY_DB), read_only=True)
    try:
        sc = con.execute(
            "SELECT * FROM p5_context_scores WHERE phase = 'ALL' AND situation = 'ALL'"
        ).df()
        ref = con.execute(
            "SELECT player_id, role, format AS comp, shrunk_estimate, pressure_opportunities "
            "FROM p4_pressure_scores_frozen_rules WHERE is_carried_definition AND "
            "shrinkage_config = 'shrink_tau4' AND \"window\" = 'PRE_TEST' AND "
            "stream IN ('runs', 'charged') AND format IN ('IPL', 'T20I')"
        ).df()
    finally:
        con.close()
    m = sc.merge(ref, on=["player_id", "role", "comp"])
    assert len(m) == len(ref) > 800
    assert np.abs(m["shrunk"] - m["shrunk_estimate"]).max() < 1e-9
    assert (m["n"] == m["pressure_opportunities"]).all()


def test_stored_coverage_equals_the_engine_pools_for_the_example_filter_sets(real):
    c, app = real
    svc = app.state.service5
    eng, cls = svc.engine(), svc._cls()
    table = svc.repo.coverage_table().set_index("spec_hash")
    examples = [
        dict(role="batter"),
        dict(role="bowler"),
        dict(role="batter", nationality="Indian"),
        dict(role="batter", nationality="Overseas", status="CAPPED_ANY"),
        dict(role="bowler", nationality="Overseas", status="DERIVED_CAPPED"),
        dict(role="bowler", phase="death"),
        dict(role="batter", situation="chase"),
        dict(
            role="batter",
            phase="death",
            situation="chase",
            nationality="Indian",
            status="DERIVED_CAPPED",
        ),
    ]
    for kw in examples:
        spec = FilterSpec(**kw)
        pool = eng.resolve_pool(spec, cls, False)
        row = table.loc[spec_hash(spec)]
        assert int(row["final_pool"]) == pool.size, kw
        body = c.post(DYN, json=kw, headers=H).json()
        assert body["pool_size"] == pool.size
        assert body["publication_status"] == "INTERNAL_EXPERIMENTAL_ONLY"
        assert len(body["page"]["items"]) == min(10, pool.size if pool.size >= 5 else 0)
    # a thin fragment is reported with reasons, never padded
    thin = FilterSpec(role="batter", format="T20I", phase="powerplay", situation="chase",
                      nationality="Indian", status="DERIVED_CAPPED")  # fmt: skip
    res = c.post(DYN, json=thin.model_dump(exclude_none=True), headers=H).json()
    assert len(res["page"]["items"]) == (res["pool_size"] if res["pool_size"] >= 5 else 0)
    assert res["pool_size"] < 10 and res["reasons"]


def test_strict_uncapped_is_disabled_on_the_real_app(real):
    c, _ = real
    for role in ("batter", "bowler"):
        d = c.post(
            DYN,
            json={"role": role, "status": "VERIFIED_UNCAPPED", "nationality": "Indian"},
            headers=H,
        ).json()
        assert d["result_status"] == "STRICT_UNCAPPED_DISABLED" and d["rows"] == []
    cov = c.get(
        DYN + "/coverage", params={"status": "VERIFIED_UNCAPPED", "limit": 200}, headers=H
    ).json()
    assert cov["page"]["total"] > 0 and not any(i["enabled"] for i in cov["page"]["items"])
    assert isinstance(Phase5Repository().config()["min_internal_pool"], int)
