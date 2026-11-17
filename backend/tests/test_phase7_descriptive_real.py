"""Real-data checks of the generated Phase 7 descriptive CSVs (skipped when files are absent).

The independent recomputation reads the organiser's raw ``updated_ball_by_ball.csv`` with pandas
and takes match dates and competition type from the official ``matches`` table. It shares no code
with ``app.phase7``.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from app.phase6.cleanup_scans import FORBIDDEN_PUBLIC_FIELD
from app.phase7 import descriptive as ds

REP = ds.REPORTS
RAW = Path("d:/Data/updated_ball_by_ball.csv")
pytestmark = pytest.mark.realdata

needs = pytest.mark.skipif(
    not (REP / ds.BATTER_CSV).exists()
    or not (REP / ds.BOWLER_CSV).exists()
    or not ds.EXPLORATORY_DB.exists()
    or not ds.OFFICIAL_DB.exists(),
    reason="generated descriptive CSVs or databases absent",
)


@pytest.fixture(scope="module")
def tables():
    return {
        "bat": pd.read_csv(REP / ds.BATTER_CSV),
        "bowl": pd.read_csv(REP / ds.BOWLER_CSV),
        "pm": pd.read_csv(REP / ds.PER_MATCH_CSV),
    }


@pytest.fixture(scope="module")
def raw_scope():
    if not RAW.exists():
        pytest.skip("raw ball-by-ball csv absent")
    d = pd.read_csv(RAW)
    o = duckdb.connect(str(ds.OFFICIAL_DB), read_only=True)
    try:
        m = o.execute("SELECT match_id, match_date, competition_type FROM matches").df()
    finally:
        o.close()
    m["match_date"] = pd.to_datetime(m["match_date"])
    d = d.merge(m, on="match_id")
    split = json.loads((ds.BACKEND_ROOT / "config" / "phase4_split_v1.json").read_text("utf-8"))
    assert split  # the cut-off below is the documented TRAIN+VALIDATION end
    return d[
        d.competition_type.isin(["IPL", "T20I"])
        & d.innings.isin([1, 2])
        & (d.match_date <= "2025-12-31")
    ]


@needs
def test_row_counts_and_sort_order(tables):
    print(
        "batter rows",
        len(tables["bat"]),
        "bowler rows",
        len(tables["bowl"]),
        "per-match",
        len(tables["pm"]),
    )
    assert len(tables["bat"]) > 800 and len(tables["bowl"]) > 600
    for k in ("bat", "bowl"):
        t = tables[k]
        assert list(t["player_id"]) == sorted(t["player_id"])
        assert not t.duplicated(["player_id", "format"]).any()
        assert set(t["format"]) == {"IPL", "T20I"}


@needs
def test_no_forbidden_column_names(tables):
    for t in tables.values():
        assert [c for c in t.columns if FORBIDDEN_PUBLIC_FIELD.search(c)] == []


@needs
def test_totals_reconcile_with_phase4_player_stats(tables):
    e = duckdb.connect(str(ds.EXPLORATORY_DB), read_only=True)
    try:
        p4 = e.execute("SELECT * FROM p4_player_stats").df()
        penalty_legal = int(
            e.execute(
                "SELECT count(*) FROM exp_pre_delivery_state s JOIN p4_match_period p USING (match_id) "
                "WHERE s.competition_type IN ('IPL','T20I') AND s.innings_number IN (1,2) "
                "AND s.format_out_of_scope = FALSE AND p.period <> 'TEST' "
                "AND s.out_is_legal_ball AND s.den_legal_inc = 0"
            ).fetchone()[0]
        )
    finally:
        e.close()
    b = tables["bat"].merge(p4, on=["player_id", "format"], how="left", validate="one_to_one")
    assert b["bat_balls"].notna().all()
    assert (b["balls_faced"] == b["bat_balls"]).all()
    assert (b["runs"] == b["bat_runs"]).all()
    assert (b["dismissals"] == b["bat_dismissals"]).all()
    assert (b["fours"] == b["bat_fours"]).all() and (b["sixes"] == b["bat_sixes"]).all()
    w = tables["bowl"].merge(p4, on=["player_id", "format"], how="left", validate="one_to_one")
    assert (w["runs_conceded"] == w["bowl_runs"]).all()
    assert (w["wickets"] == w["bowl_wickets"]).all()
    assert (w["dot_balls"] == w["bowl_dots"]).all()
    # the only difference is the Penalty row, which the restriction register removes from legal balls
    assert int((w["bowl_balls"] - w["legal_balls"]).sum()) == penalty_legal
    assert penalty_legal <= 1


@needs
def test_no_test_period_match_is_present(tables):
    e = duckdb.connect(str(ds.EXPLORATORY_DB), read_only=True)
    try:
        per = e.execute("SELECT match_id, period, match_date FROM p4_match_period").df()
    finally:
        e.close()
    test_ids = set(per.loc[per["period"] == "TEST", "match_id"])
    assert test_ids and not (set(tables["pm"]["match_id"]) & test_ids)
    assert tables["pm"]["match_date"].max() <= "2025-12-31"


@needs
def test_missing_values_are_empty_not_zero(tables):
    b, w = tables["bat"], tables["bowl"]
    assert b.loc[b["dismissals"] == 0, "average"].isna().all()
    assert b.loc[b["balls_faced"] == 0, "strike_rate"].isna().all()
    assert b.loc[b["dismissals"] > 0, "average"].notna().all()
    assert w.loc[w["wickets"] == 0, "balls_per_wicket"].isna().all()
    for p in ("pp", "mid", "death", "inn1", "chase", "vs_pace", "vs_spin"):
        empty = b[f"{p}_balls"] == 0
        assert b.loc[empty, f"{p}_strike_rate"].isna().all(), p
        assert b.loc[empty, f"{p}_runs"].isna().all(), p
    for p in ("vs_rhb", "vs_lhb"):
        assert w.loc[w[f"{p}_balls"] == 0, f"{p}_economy"].isna().all(), p
    short = b[b["strike_rate_ci_low"].isna()]
    assert short["strike_rate_ci_unavailable_reason"].notna().all()


@needs
def test_every_row_carries_source_hashes_and_the_manifest_matches(tables):
    man = json.loads((REP / ds.MANIFEST_JSON).read_text("utf-8"))
    assert man["inputs"]["superr.duckdb"] == ds.sha256_file(ds.OFFICIAL_DB)
    assert man["inputs"]["exploratory.duckdb"] == ds.sha256_file(ds.EXPLORATORY_DB)
    for name, digest in man["outputs_sha256"].items():
        assert ds.sha256_file(REP / name) == digest, name
    for k in ("bat", "bowl"):
        assert (tables[k]["official_db_sha256"] == man["inputs"]["superr.duckdb"]).all()
        assert tables[k]["context_sample_label"].eq("DESCRIPTIVE_EXPERIMENTAL_COUNT_ONLY").all()


@needs
@pytest.mark.parametrize("pid,fmt", [(8, "IPL"), (4722, "IPL"), (4722, "T20I"), (1187, "T20I")])
def test_independent_recomputation_from_the_raw_csv(tables, raw_scope, pid, fmt):
    d = raw_scope[raw_scope.competition_type == fmt]
    s = d[d.striker_id == pid]
    faced = s[~s.extras_type.isin(["wide", "Penalty"])]
    row = tables["bat"][(tables["bat"].player_id == pid) & (tables["bat"].format == fmt)]
    if len(row):
        r = row.iloc[0]
        assert r.balls_faced == len(faced)
        assert r.runs == s.runs.sum()
        out = int(((s.is_wicket) & (s.dismissed_player_id == pid)).sum())
        assert r.dismissals == out
        assert r.strike_rate == pytest.approx(100 * s.runs.sum() / len(faced), abs=1e-5)
        assert r.dot_balls == int((faced.runs == 0).sum())
        assert r.fours == int(s.is_four.sum()) and r.sixes == int(s.is_six.sum())
        if out:
            assert r.average == pytest.approx(s.runs.sum() / out, abs=1e-5)
    bw = d[d.bowler_id == pid]
    row = tables["bowl"][(tables["bowl"].player_id == pid) & (tables["bowl"].format == fmt)]
    if len(row):
        r = row.iloc[0]
        legal = bw[~bw.extras_type.isin(["wide", "Overstep", "other", "Penalty"])]
        charged_extras = bw.extras1_runs.where(
            bw.extras_type.isin(["wide", "Overstep", "other"]), 0
        )
        charged = bw.runs.sum() + charged_extras.sum()
        credited = bw[
            bw.is_wicket
            & ~bw.dismissal_type.isin(["RunOut", "Retire Out", "Obstracting the field"])
        ]
        assert r.legal_balls == len(legal)
        assert r.runs_conceded == charged
        assert r.wickets == len(credited)
        assert r.economy == pytest.approx(6 * charged / len(legal), abs=1e-5)
        assert r.wides == int((bw.extras_type == "wide").sum())


def _sample_ids(df):
    n = len(df)
    idx = sorted({0, n // 3, n // 2, (2 * n) // 3, n - 1})
    return [(int(df.iloc[i]["player_id"]), df.iloc[i]["format"]) for i in idx]


def _close(a, b):
    if pd.isna(b):
        return a is None
    return a == pytest.approx(float(b), abs=1e-5)


@needs
def test_exported_csvs_match_the_api_for_sampled_players(tables):
    from fastapi.testclient import TestClient

    from app.main import create_app

    c = TestClient(create_app())
    for side, key, vol, main in (
        ("batters", "bat", "balls_faced", "strike_rate"),
        ("bowlers", "bowl", "legal_balls", "economy"),
    ):
        df = tables[key]
        for pid, fmt in _sample_ids(df):
            csv = df[(df.player_id == pid) & (df.format == fmt)].iloc[0]
            r = c.get(
                f"/api/v1/descriptive/profiles/{side}?format={fmt}&limit=200&q={csv.player_name}"
            )
            assert r.status_code == 200
            api = next(i for i in r.json()["items"] if i["player_id"] == pid)
            assert api[vol] == csv[vol]
            assert _close(api[main], csv[main])
            assert _close(api["dot_ball_share"], csv["dot_ball_share"])
            assert _close(api["ci_low"], csv[f"{main}_ci_low"])
            assert _close(api["ci_high"], csv[f"{main}_ci_high"])
            assert api["context_sample"]["balls"] == csv["context_sample_balls"]
            assert api["provenance"]["official_db_sha256"] == csv["official_db_sha256"]
            for s in api["splits"]:
                assert s["balls"] == csv[f"{s['key']}_balls"]
                assert _close(s["rate"], csv[f"{s['key']}_{main}"])


@needs
def test_overview_and_methodology_use_real_report_values():
    from fastapi.testclient import TestClient

    from app.main import create_app

    c = TestClient(create_app())
    o = c.get("/api/v1/descriptive/overview").json()
    off = duckdb.connect(str(ds.OFFICIAL_DB), read_only=True)
    try:
        n_matches = off.execute("SELECT count(*) FROM matches").fetchone()[0]
        n_rows = off.execute("SELECT count(*) FROM deliveries").fetchone()[0]
    finally:
        off.close()
    assert (o["matches_total"], o["delivery_rows_total"]) == (n_matches, n_rows)
    assert o["lists_available"] is False
    assert o["late_t20i_dates_unverified"] == 42
    assert {x["check_id"] for x in o["reliability_checks"]} >= {"variance_floor", "data_weight"}
    assert all(x["status"] == "NOT_MET" for x in o["reliability_checks"])
    assert o["match_periods"]["TEST"] > 0
    m = c.get("/api/v1/descriptive/methodology/summary").json()
    f = m["reliability_facts"]
    e = duckdb.connect(str(ds.EXPLORATORY_DB), read_only=True)
    try:
        pooled = e.execute(
            "SELECT pooled_sb FROM p6_split_half_pooled WHERE definition='any|q0.75' "
            "AND stream_group='primary' AND \"window\"='PRE_TEST' AND \"mode\"='odd_even'"
        ).fetchone()[0]
        floor = e.execute("SELECT sum(CAST(floor_hit AS INTEGER)) FROM p5_context_fit").fetchone()[
            0
        ]
        passed = e.execute(
            "SELECT sum(CAST(data_weight_gate_passed AS INTEGER)) FROM p6_data_weight_gate_status"
        ).fetchone()[0]
    finally:
        e.close()
    assert f["pooled_odd_even_reliability"] == pytest.approx(pooled)
    assert f["contexts_at_variance_floor"] == floor == f["contexts"]
    assert f["contexts_passing_data_weight_check"] == passed == 0
    assert round(f["pooled_odd_even_reliability"], 2) == 0.37
