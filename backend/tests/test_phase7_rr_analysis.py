"""RR analysis: hand-built frame logic, the generated file, and the public endpoint."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.phase6.cleanup_scans import forbidden_public_names, walk_json_keys
from app.phase7 import rr_analysis as rr

REPORTS = Path(__file__).resolve().parents[1] / "data" / "reports"
DB = Path(__file__).resolve().parents[1] / "data" / "database"
RR, OTHER = 3, 9


def _frame() -> pd.DataFrame:
    rows = []
    mid = 0
    for season in ("2022", "2023"):
        for k in range(6):
            mid += 1
            for inn, (bat, bowl) in enumerate(((RR, OTHER), (OTHER, RR)), start=1):
                for b in range(24):
                    rows.append(
                        dict(
                            match_id=mid, innings_number=inn, season=season,
                            batting_team_id=bat, bowling_team_id=bowl, phase="middle",
                            bat_order=7 if b % 4 == 0 else 3,
                            pace_or_spin="Spin" if b % 2 else "Pace", bowler_id=100 + b % 5,
                            runs=0 if bat == RR else 2, legal=1,
                            wkt=0, bwkt=0, bruns=0 if bat == RR else 2, faced=1, boundary=0,
                        )
                    )  # fmt: skip
    return rr.prepare(pd.DataFrame(rows))


def test_compare_excludes_rr_from_league_and_flags_a_clear_gap():
    out = rr.compare(_frame(), RR)
    r = out[(out.metric == "bat_mid_rpo") & (out.period == "2022")].iloc[0]
    assert r.rr_value == 0.0 and r.league_value == pytest.approx(12.0)
    assert r.assessment == "RR_WORSE_SUPPORTED"  # zero-variance gap, both CIs collapse
    assert r.rr_matches == 6 and r.league_matches == 6


def test_low_sample_and_usage_labels():
    assert rr.assess(1, True, -1.0, 1.0) == "LOW_SAMPLE"
    assert rr.assess(0, False, 0.1, 0.2) == "USAGE_DESCRIPTIVE"
    assert rr.assess(-1, False, 0.1, 0.9) == "RR_WORSE_SUPPORTED"
    assert rr.assess(-1, False, -0.9, -0.1) == "RR_BETTER_SUPPORTED"
    assert rr.assess(1, False, -0.5, 0.5) == "NOT_DISTINGUISHABLE"


def test_primary_window_contains_only_pre_2026_and_2026_is_separate():
    out = rr.compare(_frame(), RR)
    assert set(out.period) == set(rr.PERIODS)
    pooled = out[(out.metric == "bat_mid_rpo") & (out.period == rr.PRIMARY)].iloc[0]
    assert pooled.rr_matches == 12  # the two synthetic seasons only


def test_bootstrap_is_seeded():
    a = rr.compare(_frame(), RR)
    b = rr.compare(_frame(), RR)
    pd.testing.assert_frame_equal(a, b)
    assert np.isfinite(a["ci_low"].dropna()).all()


def test_real_data_rr_match_count_and_name_lookup():
    d = json.loads((REPORTS / "rr_analysis_tables.json").read_text(encoding="utf-8"))
    con = duckdb.connect(str(DB / "superr.duckdb"), read_only=True)
    tid = con.execute("select team_id from teams where team_name='Rajasthan Royals'").fetchone()[0]
    assert d["team"]["team_id"] == tid
    n = con.execute(
        "select count(*) from matches m join competitions c using(comp_id) "
        "where m.competition_type='IPL' and c.season between '2022' and '2025' "
        "and (home_team_id=? or away_team_id=?)",
        [tid, tid],
    ).fetchone()[0]
    assert n == sum(int(r["n"]) for r in d["season_results"] if r["season"] != "2026") == 61
    assert d["descriptive_only"] is True
    assert {r["period"] for r in d["comparisons"]} == set(rr.PERIODS)


def test_candidate_tables_are_alphabetical_with_unknown_availability():
    d = json.loads((REPORTS / "rr_analysis_tables.json").read_text(encoding="utf-8"))
    for t in d["candidate_fit_tables"].values():
        names = [r["player_name"] for r in t["rows"]]
        assert names == sorted(names)
        if not d["retention"]["list_received"]:
            assert {r["availability"] for r in t["rows"]} <= {"UNKNOWN"}


def test_endpoint_is_public_descriptive_and_returns_copies():
    client = TestClient(create_app())
    r = client.get("/api/v1/rr/analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["descriptive_only"] is True
    assert forbidden_public_names(walk_json_keys(body)) == []
    body["comparisons"].clear()
    assert len(client.get("/api/v1/rr/analysis").json()["comparisons"]) == 168
    assert client.get("/api/v1/rr/analysis?official=true").status_code == 403
