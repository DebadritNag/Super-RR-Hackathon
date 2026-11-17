"""Ingestion tests on synthetic CSVs (plus one skippable real-data integration test)."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import duckdb
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.data_pipeline.csv_loader import BALL_COLUMNS
from app.services.ingestion_service import IngestionService

MATCH_COLS = (
    "match_id,comp_id,match_number,match_date,stage,venue_id,venue_country,home_team_id,home_team,"
    "away_team_id,away_team,home_team_captain_id,away_team_captain_id,toss_win_team_id,toss_opted,"
    "man_of_the_match,first_inn_revised_overs,second_inn_revised_overs,revised_target,knock_out,"
    "win_team_id,result"
).split(",")
PE_COLS = "match_id,team_id,player_id,batting_order,is_played,is_captain,is_wk,is_impact,is_impact_off".split(
    ","
)
MAP_COLS = "comp_id,comp_name,team_id,team_name,player_id,player_name".split(",")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def match(mid, comp, date, home, away, win, result, mom=0, captains=("", "")):
    hn = {10: "A", 11: "B", 12: "C", 13: "D", 14: "E"}
    return [
        mid, comp, 1, date, "League", 5, "India", home, hn[home], away, hn[away],
        captains[0], captains[1], home, "Fielding", mom, "", "", "", 0, win, result,
    ]  # fmt: skip


def ball(
    mid,
    inn,
    n,
    bat,
    bowl,
    striker,
    non,
    bowler,
    runs=0,
    extras="None",
    e1=0,
    e2=0,
    wicket="false",
    dismissed="",
    dtype="",
    dtid="",
    sname=None,
    time="2024-04-01 14:00:00 UTC",
):
    row = {c: "" for c in BALL_COLUMNS}
    row.update(
        match_id=mid, innings=inn, overid=1, over_ball_num=n, innings_ball_num=n,
        batting_team_id=bat, bowling_team_id=bowl, striker_id=striker,
        striker_name=sname or f"P{striker}", non_striker_id=non, non_striker_name=f"P{non}",
        bowler_id=bowler, bowler_name=f"P{bowler}", batting_order=1, runs=runs, is_four="false",
        is_six="false", is_wicket=wicket, dismissal_type_id=dtid, dismissal_type=dtype,
        dismissed_player_id=dismissed, extras_type=extras, extras1_runs=e1, extras_2_runs=e2,
        delivery_ist_time=time,
    )  # fmt: skip
    return row


UPDATED_ROWS = [
    ball(1, 1, 1, 10, 11, 100, 101, 102, runs=4),
    ball(1, 1, 2, 10, 11, 100, 101, 102, extras="wide", e1=1),
    ball(1, 1, 3, 10, 11, 100, 101, 103, extras="legbyes", e1=1),
    ball(1, 1, 4, 10, 11, 100, 101, 103, wicket="true", dismissed=100, dtype="Caught", dtid=1),
    ball(1, 2, 1, 11, 10, 102, 103, 100, runs=1, time="2024-04-01 00:00:00 UTC"),
    ball(1, 2, 2, 11, 10, 102, 103, 100),
    ball(2, 1, 1, 10, 12, 100, 101, 104, extras="other", e1=1),
    ball(2, 1, 2, 10, 12, 100, 101, 104, extras="Penalty", e1=5),
    ball(2, 1, 3, 10, 12, 100, 101, 104, extras="byes", e1=1, e2=1),
    ball(2, 2, 1, 12, 10, 105, 104, 100, runs=2),
    ball(2, 3, 1, 10, 12, 100, 101, 104, runs=6),
    ball(2, 3, 2, 10, 12, 100, 101, 104, wicket="false", dismissed=100),
    ball(4, 1, 1, 13, 14, 106, 107, 108, runs=1),
    ball(4, 2, 1, 14, 13, 107, 106, 109),
]


def original_rows():
    rows = [dict(r) for r in UPDATED_ROWS]
    codes = {"None": 6, "wide": 2, "legbyes": 3, "byes": 4, "Overstep": 1, "other": 5, "Penalty": 7}
    for r in rows:
        r["extras1_runs"] = codes[r["extras_type"]]
    rows[0]["striker_name"] = "Alias Name"
    return rows


def make_dataset(root: Path, with_skipped: bool = True) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_csv(
        root / "competitions.csv",
        ["comp_id", "comp_name", "match_format", "season"],
        [
            [1, "IPL 2024", "T20", "2024"],
            [2, "Series T20I", "T20I", "2024"],
            [3, "Rising Stars", "T20", "2024"],
        ],
    )
    write_csv(
        root / "teams.csv",
        ["comp_id", "team_id", "team_name"],
        [[1, 10, "A"], [1, 11, "B"], [2, 10, "A"], [2, 12, "C"], [3, 13, "D"], [3, 14, "E"]],
    )
    write_csv(
        root / "matches.csv",
        MATCH_COLS,
        [
            match(1, 1, "2024-04-01", 10, 11, 10, "A Won by 5 Wickets", captains=(100, 102)),
            match(2, 2, "2024-04-02", 10, 12, 12, "C Won by 3 Runs", mom=104),
            match(3, 1, "2024-04-03", 10, 11, "", "Match Abandoned"),
            match(4, 3, "2024-04-04", 13, 14, 13, "D Won by 1 Run"),
        ],
    )
    pe = lambda m, t, p, played="true": [m, t, p, 1, played, "false", "false", 0, 0]  # noqa: E731
    write_csv(
        root / "playing_eleven.csv",
        PE_COLS,
        [
            pe(1, 10, 100), pe(1, 10, 101), pe(1, 10, 101), pe(1, 11, 102), pe(1, 11, 103),
            pe(2, 10, 100), pe(2, 10, 101), pe(2, 12, 104),
            pe(3, 10, 100), pe(3, 11, 102, "false"),
        ],
    )  # fmt: skip
    write_csv(
        root / "competition_team_player_mapping.csv",
        MAP_COLS,
        [
            [1, "IPL 2024", 10, "A", 100, "Alpha"], [1, "IPL 2024", 10, "A", 101, "Bravo"],
            [1, "IPL 2024", 11, "B", 102, "Charlie"], [1, "IPL 2024", 11, "B", 103, "Delta"],
            [2, "Series T20I", 10, "A", 100, "Alpha"],
            [2, "Series T20I", 12, "C", 104, "Echo"], [2, "Series T20I", 12, "C", 105, "Foxtrot"],
        ],
    )  # fmt: skip
    for name, rows in (
        ("updated_ball_by_ball.csv", UPDATED_ROWS),
        ("ball_by_ball.csv", original_rows()),
    ):
        write_csv(root / name, BALL_COLUMNS, [[r[c] for c in BALL_COLUMNS] for r in rows])
    write_csv(
        root / "ipl squad.csv",
        ["team_no", "team_name", "player", "nationality", "role", "designation"],
        [[1, "A", "Alpha", "Indian", "Batter", ""]],
    )
    if with_skipped:
        write_csv(root / "matches 2026.csv", ["match_id", "date"], [[1, "2026-04-01"]])
        for name in ("batting_stats2026.csv", "bowling_stats2026.csv", "fielding_stats2026.csv"):
            write_csv(root / name, ["player", "runs"], [["X", 1], ["Y", 2]])


def make_settings(tmp: Path) -> Settings:
    return Settings(
        _env_file=None,
        data_root=tmp / "data",
        cricsheet_root=tmp / "data",
        duckdb_path=tmp / "db.duckdb",
        audit_dir=tmp / "audit",
    )


@pytest.fixture
def env(tmp_path):
    make_dataset(tmp_path / "data")
    return make_settings(tmp_path)


def q(settings: Settings, sql: str, params=None):
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        return con.execute(sql, params or []).fetchall()
    finally:
        con.close()


def run(settings, **kw):
    hook = kw.pop("fault_hook", None)
    return IngestionService(settings, expected_counts={}, fault_hook=hook).run(**kw)


DATA_TABLES = [
    "competitions", "teams", "competition_teams", "venues", "players", "player_competition_mapping",
    "matches", "match_squads", "innings", "deliveries", "match_reconciliation",
    "raw_ball_by_ball", "raw_ball_by_ball_updated", "ball_by_ball_comparison",
    "ball_by_ball_comparison_detail",
]  # fmt: skip


def snapshot(settings: Settings) -> dict:
    """Row counts and a content hash per table (provenance run ids excluded)."""
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    out = {}
    try:
        for t in DATA_TABLES:
            cols = [
                r[0]
                for r in con.execute(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name = '{t}' ORDER BY ordinal_position"
                ).fetchall()
                if r[0] != "ingestion_run_id"
            ]
            rows = con.execute(f"SELECT {', '.join(cols)} FROM {t} ORDER BY ALL").fetchall()
            out[t] = (len(rows), hashlib.sha256(repr(rows).encode()).hexdigest())
    finally:
        con.close()
    return out


# --------------------------------------------------------------------------- idempotency / runs
def test_first_run_loads_and_validates(env):
    res = run(env)
    assert res.status == "SUCCESS", res.error
    assert res.validation.get("FAIL", 0) == 0
    assert res.exit_code == 0
    counts = {t: q(env, f"SELECT count(*) FROM {t}")[0][0] for t in DATA_TABLES}
    assert counts["matches"] == 4 and counts["deliveries"] == 14 and counts["match_squads"] == 10
    assert counts["competition_teams"] == 6 and counts["teams"] == 5
    assert counts["raw_ball_by_ball"] == counts["raw_ball_by_ball_updated"] == 14


def test_second_run_is_no_change_and_identical(env):
    run(env)
    before = snapshot(env)
    res = run(env)
    assert res.status == "NO_CHANGE"
    assert snapshot(env) == before
    assert q(env, "SELECT count(*) FROM dataset_lineage WHERE run_id = ?", [res.run_id])[0][0] == 0


def test_force_reload_gives_identical_content(env):
    first = run(env)
    before = snapshot(env)
    res = run(env, force=True)
    assert res.status == "SUCCESS" and res.run_id != first.run_id
    assert snapshot(env) == before
    assert q(env, "SELECT DISTINCT ingestion_run_id FROM deliveries") == [(res.run_id,)]


def test_changed_source_triggers_reload(env):
    run(env)
    path = env.data_root / "competitions.csv"
    path.write_text(path.read_text(encoding="utf-8") + "4,Extra T20,T20,2025\n", encoding="utf-8")
    write_csv(
        env.data_root / "teams.csv",
        ["comp_id", "team_id", "team_name"],
        [
            [1, 10, "A"],
            [1, 11, "B"],
            [2, 10, "A"],
            [2, 12, "C"],
            [3, 13, "D"],
            [3, 14, "E"],
            [4, 10, "A"],
        ],
    )
    res = run(env)
    assert res.status == "SUCCESS" and "changed" in res.reason
    assert q(env, "SELECT count(*) FROM competitions")[0][0] == 4


def test_rollback_on_mid_load_failure_keeps_previous_state(env):
    ok = run(env)
    before = snapshot(env)

    def boom(step: str) -> None:
        if step == "deliveries":
            raise RuntimeError("injected fault")

    res = run(env, force=True, fault_hook=boom)
    assert res.status == "FAILED" and res.exit_code == 1
    assert snapshot(env) == before
    assert q(env, "SELECT DISTINCT ingestion_run_id FROM deliveries") == [(ok.run_id,)]
    assert q(env, "SELECT status FROM ingestion_runs WHERE run_id = ?", [res.run_id]) == [
        ("FAILED",)
    ]
    errs = q(env, "SELECT error_type, message FROM ingestion_errors WHERE run_id = ?", [res.run_id])
    assert errs and errs[0][0] == "EXCEPTION" and "injected fault" in errs[0][1]
    text = env.ingestion_errors_csv.read_text(encoding="utf-8")
    assert "injected fault" in text
    # the next run recovers and reloads because the last good lineage run is not the newest run
    again = run(env)
    assert again.status in ("NO_CHANGE", "SUCCESS")


def test_failed_first_run_leaves_no_data_tables_populated(env):
    def boom(step: str) -> None:
        if step == "matches":
            raise RuntimeError("fault")

    res = run(env, fault_hook=boom)
    assert res.status == "FAILED"
    con = duckdb.connect(str(env.duckdb_path), read_only=True)
    try:
        tables = {
            r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
        assert "matches" not in tables and "ingestion_runs" in tables
        assert con.execute("SELECT count(*) FROM dataset_lineage").fetchone()[0] == 0
    finally:
        con.close()


def test_header_mismatch_fails_before_loading(env):
    write_csv(env.data_root / "competitions.csv", ["comp_id", "name"], [[1, "x"]])
    res = run(env)
    assert res.status == "FAILED"
    assert (
        q(env, "SELECT error_type FROM ingestion_errors WHERE run_id = ?", [res.run_id])[0][0]
        == "HEADER_MISMATCH"
    )


def test_missing_required_file_fails(env):
    (env.data_root / "matches.csv").unlink()
    res = run(env)
    assert res.status == "FAILED"
    assert (
        q(env, "SELECT error_type FROM ingestion_errors WHERE run_id = ?", [res.run_id])[0][0]
        == "MISSING_FILE"
    )


def test_non_numeric_key_fails_and_rolls_back(env):
    write_csv(
        env.data_root / "competitions.csv",
        ["comp_id", "comp_name", "match_format", "season"],
        [["x", "IPL", "T20", "2024"]],
    )
    res = run(env)
    assert res.status == "FAILED"
    assert (
        q(env, "SELECT error_type FROM ingestion_errors WHERE run_id = ?", [res.run_id])[0][0]
        == "CAST_FAILURE"
    )


def test_validate_only_does_not_reload(env):
    run(env)
    before = snapshot(env)
    res = run(env, validate_only=True)
    assert res.status == "SUCCESS" and res.mode == "VALIDATE_ONLY"
    assert snapshot(env) == before


# --------------------------------------------------------------------------- data semantics
def test_duplicate_playing_eleven_preserved(env):
    run(env)
    rows = q(
        env,
        "SELECT squad_row_no, duplicate_key_flag, duplicate_group_size, source_row_no FROM match_squads WHERE match_id = 1 AND team_id = 10 AND player_id = 101 ORDER BY squad_row_no",
    )
    assert rows == [(1, True, 2, 2), (2, True, 2, 3)]
    assert (
        q(
            env,
            "SELECT count(*) FROM match_squads WHERE NOT duplicate_key_flag AND player_id = 100 AND match_id = 1",
        )[0][0]
        == 1
    )
    errs = q(
        env, "SELECT count(*) FROM ingestion_errors WHERE error_type = 'DUPLICATE_KEY_PRESERVED'"
    )
    assert errs == [(2,)]


def test_innings_3_is_unverified_and_no_super_over_column(env):
    run(env)
    assert q(
        env, "SELECT innings_role_status FROM innings WHERE match_id = 2 ORDER BY innings_number"
    ) == [("STANDARD",), ("STANDARD",), ("UNVERIFIED",)]
    cols = q(
        env, "SELECT column_name FROM information_schema.columns WHERE column_name ILIKE '%super%'"
    )
    assert cols == []
    open_ = q(
        env,
        "SELECT status, affected_rows FROM data_quality_results WHERE check_name = 'open_innings_3_4_role_unverified'",
    )
    assert open_ == [("OPEN", 1)]


def test_extras_handling(env):
    run(env)
    rows = {
        r[0]: r[1:]
        for r in q(
            env,
            "SELECT extras_type, has_extra, is_legal_ball, extras_label_unverified, legal_ball_status, extras_split_status "
            "FROM deliveries WHERE match_id IN (1, 2) ORDER BY match_id, innings_number, innings_ball_num",
        )
    }
    assert rows["None"] == (False, True, False, "VERIFIED", "UNVERIFIED")
    assert rows["wide"] == (True, False, False, "VERIFIED", "UNVERIFIED")
    assert rows["legbyes"] == (True, True, False, "VERIFIED", "UNVERIFIED")
    assert rows["other"] == (True, False, True, "VERIFIED", "UNVERIFIED")
    assert rows["Penalty"] == (True, True, True, "UNVERIFIED", "UNVERIFIED")
    assert q(env, "SELECT count(*) FROM deliveries WHERE extras_type IS NULL")[0][0] == 0
    assert q(
        env,
        "SELECT extras_primary_runs, extras_secondary_runs FROM deliveries WHERE extras_type = 'byes'",
    ) == [(1, 1)]
    assert q(
        env,
        "SELECT batter_runs FROM deliveries WHERE match_id = 1 AND innings_number = 1 AND innings_ball_num = 1",
    ) == [(4,)]


def test_legal_ball_count_and_totals_per_innings(env):
    run(env)
    assert q(
        env,
        "SELECT delivery_count, legal_ball_count, batter_runs_total, extras_primary_total, source_total_runs FROM innings WHERE match_id = 1 AND innings_number = 1",
    ) == [(4, 3, 4, 2, 6)]
    assert q(
        env, "SELECT legal_ball_count FROM innings WHERE match_id = 2 AND innings_number = 1"
    ) == [(2,)]


def test_dismissal_fields_verbatim_and_anomaly_flags(env):
    run(env)
    assert q(
        env,
        "SELECT is_wicket, dismissal_type, dismissed_player_id, dismissal_field_anomaly FROM deliveries WHERE match_id = 1 AND innings_ball_num = 4 AND innings_number = 1",
    ) == [(True, "Caught", 100, None)]
    assert q(
        env,
        "SELECT dismissal_field_anomaly FROM deliveries WHERE match_id = 2 AND innings_number = 3 AND innings_ball_num = 2",
    ) == [("DISMISSED_PLAYER_WITHOUT_WICKET",)]
    assert q(
        env,
        "SELECT affected_rows FROM data_quality_results WHERE check_name = 'open_dismissed_player_without_wicket_flag'",
    ) == [(1,)]


def test_orphans_are_kept_recorded_and_reported(env):
    run(env)
    # striker 105 (match 2) and strikers/bowlers of match 4 are not in a squad; nothing dropped
    assert q(env, "SELECT count(*) FROM deliveries")[0][0] == 14
    orphan = q(
        env,
        "SELECT count(*) FROM ingestion_errors WHERE error_type = 'ORPHAN_RECORDED_NOT_DROPPED' AND table_name = 'deliveries'",
    )[0][0]
    assert orphan > 0
    assert q(
        env,
        "SELECT status FROM data_quality_results WHERE check_name = 'open_delivery_striker_not_in_match_squad'",
    ) == [("OPEN",)]
    assert q(
        env,
        "SELECT status FROM data_quality_results WHERE check_name = 'open_matches_without_playing_eleven_rows'",
    ) == [("OPEN",)]
    assert q(
        env, "SELECT mapping_row_exists FROM match_squads WHERE match_id = 2 AND player_id = 101"
    ) == [(False,)]
    # players unknown to the mapping exist from deliveries, with their delivery names
    assert q(env, "SELECT player_name, name_source FROM players WHERE player_id = 106") == [
        ("P106", "DELIVERIES")
    ]


def test_players_not_merged_by_name(env):
    path = env.data_root / "competition_team_player_mapping.csv"
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write("2,Series T20I,12,C,200,Alpha\r\n")
    run(env)
    assert q(env, "SELECT count(*) FROM players WHERE player_name = 'Alpha'")[0][0] == 2
    assert (
        q(
            env,
            "SELECT count(*) FROM players WHERE player_name = 'Alpha' AND shares_name_with_other_id",
        )[0][0]
        == 2
    )


def test_match_reconciliation_and_result_status(env):
    run(env)
    assert q(
        env,
        "SELECT has_deliveries, result_status, no_deliveries_explained FROM match_reconciliation WHERE match_id = 3",
    ) == [(False, "ABANDONED", True)]
    assert q(env, "SELECT count(*) FROM match_reconciliation WHERE has_deliveries")[0][0] == 3
    assert q(env, "SELECT reason FROM match_reconciliation WHERE match_id = 3")[0][0].startswith(
        "no deliveries"
    )
    assert q(
        env,
        "SELECT status FROM data_quality_results WHERE check_name = 'reconcile_no_delivery_matches_explained'",
    ) == [("PASS",)]
    assert q(env, "SELECT competition_type FROM matches ORDER BY match_id") == [
        ("IPL",),
        ("T20I",),
        ("IPL",),
        ("OTHER_T20",),
    ]
    assert q(env, "SELECT first_innings_batting_team_id FROM matches ORDER BY match_id") == [
        (10,),
        (10,),
        (None,),
        (13,),
    ]


def test_original_vs_updated_comparison(env):
    run(env)
    diff = dict(
        q(
            env,
            "SELECT column_name, rows_different FROM ball_by_ball_comparison WHERE rows_different > 0",
        )
    )
    assert diff["extras1_runs"] > 0 and diff["striker_name"] == 1
    assert q(
        env,
        "SELECT original_value, updated_value FROM ball_by_ball_comparison_detail WHERE column_name = 'striker_name'",
    ) == [("Alias Name", "P100")]
    assert (
        q(
            env,
            "SELECT count(*) FROM ball_by_ball_comparison_detail WHERE column_name = 'extras1_runs'",
        )[0][0]
        == 0
    )
    cross = json.loads(
        q(env, "SELECT details FROM ball_by_ball_comparison WHERE column_name = 'extras1_runs'")[0][
            0
        ]
    )
    assert {"original_value": "2", "updated_value": "1", "extras_type": "wide", "rows": 1} in cross
    assert q(
        env,
        "SELECT rows_only_in_original + rows_only_in_updated FROM ball_by_ball_comparison WHERE column_name = 'runs'",
    ) == [(0,)]


def test_skipped_and_pending_files_in_lineage_without_data(env):
    run(env)
    rows = {
        r[0]: r[1:]
        for r in q(
            env,
            "SELECT file_name, role, load_status, target_table, row_count, sha256 FROM dataset_lineage",
        )
    }
    for name in (
        "matches 2026.csv",
        "batting_stats2026.csv",
        "bowling_stats2026.csv",
        "fielding_stats2026.csv",
    ):
        role, status, target, n, sha = rows[name]
        assert (
            role == status == "SKIPPED_BY_DECISION" and target is None and n >= 1 and len(sha) == 64
        )
    assert rows["ipl squad.csv"][0] == "PENDING_PHASE"
    assert rows["updated_ball_by_ball.csv"][0] == "PRIMARY"
    assert rows["ball_by_ball.csv"][0] == "COMPARISON_RAW"
    tables = {r[0] for r in q(env, "SELECT table_name FROM information_schema.tables")}
    assert not any(
        "2026" in t or "cricsheet" in t or "squad" in t.replace("match_squads", "") for t in tables
    )


def test_missing_optional_files_are_recorded(tmp_path):
    make_dataset(tmp_path / "data", with_skipped=False)
    settings = make_settings(tmp_path)
    res = run(settings)
    assert res.status == "SUCCESS", res.error
    assert q(
        settings,
        "SELECT sha256, load_status FROM dataset_lineage WHERE file_name = 'matches 2026.csv'",
    ) == [(None, "SKIPPED_BY_DECISION")]


def test_provenance_on_every_imported_record(env):
    run(env)
    for t in DATA_TABLES:
        if t in ("ball_by_ball_comparison", "ball_by_ball_comparison_detail"):
            cols = "source_file IS NULL OR ingestion_run_id IS NULL"
        else:
            cols = "source_file IS NULL OR ingestion_run_id IS NULL"
        assert q(env, f"SELECT count(*) FROM {t} WHERE {cols}")[0][0] == 0, t
    for t in ("deliveries", "match_squads", "matches", "competition_teams", "raw_ball_by_ball"):
        assert q(env, f"SELECT count(*) FROM {t} WHERE source_row_no IS NULL")[0][0] == 0, t
    assert q(env, "SELECT min(source_row_no), max(source_row_no) FROM deliveries") == [(1, 14)]


def test_delivery_timestamps(env):
    run(env)
    assert q(
        env,
        "SELECT delivery_time_raw, delivery_ts IS NOT NULL, delivery_time_is_midnight FROM deliveries WHERE match_id = 1 AND innings_number = 2 AND innings_ball_num = 1",
    ) == [("2024-04-01 00:00:00 UTC", True, True)]
    assert q(
        env,
        "SELECT affected_rows FROM data_quality_results WHERE check_name = 'open_delivery_time_midnight_rows'",
    ) == [(1,)]


def test_validation_checks_recorded_and_open_counts_recomputed(env):
    run(env)
    statuses = dict(q(env, "SELECT status, count(*) FROM data_quality_results GROUP BY 1"))
    assert statuses.get("FAIL", 0) == 0 and statuses["PASS"] > 20 and statuses["OPEN"] > 5
    assert q(
        env,
        "SELECT affected_rows FROM data_quality_results WHERE check_name = 'open_extras_type_other_label_unverified'",
    ) == [(1,)]
    assert q(
        env,
        "SELECT affected_rows FROM data_quality_results WHERE check_name = 'open_extras_type_Penalty_label_unverified'",
    ) == [(1,)]
    assert env.validation_report_json.exists() and env.validation_report_md.exists()
    assert (env.audit_dir / "ball_by_ball_comparison.json").exists()
    assert (env.audit_dir / "phase2_match_reconciliation.csv").exists()
    assert env.ingestion_errors_csv.exists()


def test_source_files_are_never_modified(env):
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in env.data_root.iterdir()}
    run(env)
    run(env, force=True)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in env.data_root.iterdir()}
    assert before == after


def test_source_changed_during_run_is_detected(env):
    def mutate(step: str) -> None:
        if step == "metadata":
            p = env.data_root / "ipl squad.csv"
            p.write_text(
                p.read_text(encoding="utf-8") + "2,B,Zed,Indian,Bowler,\n", encoding="utf-8"
            )

    res = run(env, fault_hook=mutate)
    assert res.status == "FAILED"
    assert (
        q(env, "SELECT error_type FROM ingestion_errors WHERE run_id = ?", [res.run_id])[0][0]
        == "SOURCE_CHANGED_DURING_RUN"
    )


def test_model_versions_and_metric_definitions(env):
    run(env)
    cfg = q(env, "SELECT config_json, status FROM model_versions WHERE kind = 'WEIGHTING_CONFIG'")
    assert len(cfg) == 1 and cfg[0][1] == "PROVISIONAL"
    assert (
        json.loads(cfg[0][0])["ipl_weight"] == 0.7 and json.loads(cfg[0][0])["t20i_weight"] == 0.3
    )
    assert q(
        env, "SELECT status FROM metric_definitions WHERE metric_name = 'extras_label_unverified'"
    ) == [("UNVERIFIED",)]
    assert (
        q(
            env,
            "SELECT count(*) FROM model_versions WHERE kind IN ('DATA_VERSION', 'SCHEMA_VERSION')",
        )[0][0]
        == 2
    )


def test_run_without_ingest_keeps_running_runs_aborted(env):
    run(env)
    con = duckdb.connect(str(env.duckdb_path))
    con.execute(
        "INSERT INTO ingestion_runs (started_at, status, mode) VALUES (current_timestamp, 'RUNNING', 'LOAD')"
    )
    con.close()
    res = run(env)
    assert res.status == "NO_CHANGE"
    assert (
        q(
            env,
            "SELECT count(*) FROM ingestion_runs WHERE status = 'RUNNING' AND run_id <> ?",
            [res.run_id],
        )[0][0]
        == 0
    )


# --------------------------------------------------------------------------- settings
def test_weights_default_and_validation():
    s = Settings(_env_file=None)
    assert (s.ipl_weight, s.t20i_weight) == (0.70, 0.30)
    assert Settings(_env_file=None, ipl_weight=0.5, t20i_weight=0.5).ipl_weight == 0.5
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ipl_weight=0.6, t20i_weight=0.6)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ipl_weight=-0.2, t20i_weight=1.2)


def test_weights_env_override(monkeypatch):
    monkeypatch.setenv("SUPERR_IPL_WEIGHT", "0.6")
    monkeypatch.setenv("SUPERR_T20I_WEIGHT", "0.4")
    s = Settings(_env_file=None)
    assert (s.ipl_weight, s.t20i_weight) == (0.6, 0.4)
    monkeypatch.setenv("SUPERR_T20I_WEIGHT", "0.9")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_weights_stored_from_settings(tmp_path):
    make_dataset(tmp_path / "data")
    settings = make_settings(tmp_path).model_copy(update={"ipl_weight": 0.6, "t20i_weight": 0.4})
    run(settings)
    name, cfg = q(
        settings, "SELECT name, config_json FROM model_versions WHERE kind = 'WEIGHTING_CONFIG'"
    )[0]
    assert name == "weighting-ipl0.60-t20i0.40" and json.loads(cfg)["ipl_weight"] == 0.6


# --------------------------------------------------------------------------- real data
REAL_ROOT = Path("d:/Data")


@pytest.mark.realdata
@pytest.mark.skipif(
    not (REAL_ROOT / "updated_ball_by_ball.csv").exists(), reason="real CSVs absent"
)
def test_real_data_ingestion_into_temp_db(tmp_path):
    settings = Settings(
        _env_file=None,
        data_root=REAL_ROOT,
        duckdb_path=tmp_path / "real.duckdb",
        audit_dir=tmp_path / "audit",
    )
    res = IngestionService(settings).run()
    assert res.status == "SUCCESS", res.error
    assert res.validation.get("FAIL", 0) == 0
    expected = {
        "competitions": 141, "competition_teams": 353, "teams": 38, "matches": 883,
        "match_squads": 28381, "player_competition_mapping": 6413, "raw_ball_by_ball": 200999,
        "raw_ball_by_ball_updated": 200999, "deliveries": 200999, "match_reconciliation": 883,
    }  # fmt: skip
    for table, n in expected.items():
        assert q(settings, f"SELECT count(*) FROM {table}")[0][0] == n, table
    assert q(
        settings,
        "SELECT count(*) FILTER (WHERE has_deliveries), count(*) FILTER (WHERE NOT has_deliveries) FROM matches",
    ) == [(867, 16)]
    assert q(
        settings,
        "SELECT count(*), count(DISTINCT (match_id, team_id, player_id)) FROM match_squads WHERE duplicate_key_flag",
    ) == [(75, 35)]
    diff = dict(
        q(
            settings,
            "SELECT column_name, rows_different FROM ball_by_ball_comparison WHERE rows_different > 0",
        )
    )
    assert diff == {"extras1_runs": 199980, "non_striker_name": 33, "striker_name": 24}
    assert q(
        settings,
        "SELECT count(*) FROM matches WHERE NOT has_deliveries AND NOT EXISTS (SELECT 1 FROM match_reconciliation r WHERE r.match_id = matches.match_id AND r.no_deliveries_explained)",
    ) == [(0,)]
    again = IngestionService(settings).run()
    assert again.status == "NO_CHANGE"
