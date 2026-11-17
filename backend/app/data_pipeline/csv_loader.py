"""Source specs, file profiling and DuckDB SQL builders for the official-CSV ingestion.

Everything that is DuckDB-dialect SQL for loading lives here, so a PostgreSQL backend only needs a
different version of this module and of `app.core.database`.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.utils.paths import posix, sql_quote

BALL_COLUMNS: tuple[str, ...] = (
    "match_id,innings,overid,over_ball_num,innings_ball_num,batting_team_id,bowling_team_id,"
    "striker_id,striker_name,non_striker_id,non_striker_name,bowler_id,bowler_name,batting_type,"
    "bowling_type,batting_order,runs,is_four,is_six,is_wicket,dismissal_type_id,dismissal_type,"
    "dismissed_player_id,extras_type,extras1_runs,extras_2_runs,pace_or_spin,bowl_speed,stroke,"
    "delivery_style,over_or_around,on_or_off,delivery_ist_time"
).split(",")

UPDATED = "updated_ball_by_ball.csv"
ORIGINAL = "ball_by_ball.csv"

# Roles and load statuses stored in dataset_lineage.
PRIMARY = "PRIMARY"
COMPARISON_RAW = "COMPARISON_RAW"
SKIPPED = "SKIPPED_BY_DECISION"
PENDING = "PENDING_PHASE"


@dataclass(frozen=True)
class SourceSpec:
    file_name: str
    role: str
    target_tables: tuple[str, ...]
    columns: tuple[str, ...] | None
    stage_table: str | None
    required: bool
    note: str
    column_order_free: bool = False

    @property
    def load_status(self) -> str:
        if self.role in (PRIMARY, COMPARISON_RAW):
            return "LOADED"
        return self.role


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        "competitions.csv",
        PRIMARY,
        ("competitions",),
        ("comp_id", "comp_name", "match_format", "season"),
        "stg_competitions",
        True,
        "Official competition reference.",
    ),
    SourceSpec(
        "teams.csv",
        PRIMARY,
        ("competition_teams", "teams"),
        ("comp_id", "team_id", "team_name"),
        "stg_teams",
        True,
        "Competition team membership; distinct team ids form `teams`.",
    ),
    SourceSpec(
        "matches.csv",
        PRIMARY,
        ("matches", "venues", "match_reconciliation"),
        (
            "match_id,comp_id,match_number,match_date,stage,venue_id,venue_country,home_team_id,"
            "home_team,away_team_id,away_team,home_team_captain_id,away_team_captain_id,"
            "toss_win_team_id,toss_opted,man_of_the_match,first_inn_revised_overs,"
            "second_inn_revised_overs,revised_target,knock_out,win_team_id,result"
        ).split(","),
        "stg_matches",
        True,
        "Official matches.",
    ),
    SourceSpec(
        "playing_eleven.csv",
        PRIMARY,
        ("match_squads",),
        (
            "match_id",
            "team_id",
            "player_id",
            "batting_order",
            "is_played",
            "is_captain",
            "is_wk",
            "is_impact",
            "is_impact_off",
        ),
        "stg_pe",
        True,
        "Loaded without de-duplication (repeated keys preserved and flagged).",
    ),
    SourceSpec(
        "competition_team_player_mapping.csv",
        PRIMARY,
        ("player_competition_mapping",),
        ("comp_id", "comp_name", "team_id", "team_name", "player_id", "player_name"),
        "stg_map",
        True,
        "Official player to competition/team mapping.",
    ),
    SourceSpec(
        UPDATED,
        PRIMARY,
        ("raw_ball_by_ball_updated", "deliveries", "innings"),
        tuple(BALL_COLUMNS),
        "stg_upd",
        True,
        "Authoritative delivery-level dataset (user decision 1).",
        True,
    ),
    SourceSpec(
        ORIGINAL,
        COMPARISON_RAW,
        ("raw_ball_by_ball", "ball_by_ball_comparison", "ball_by_ball_comparison_detail"),
        tuple(BALL_COLUMNS),
        "stg_orig",
        True,
        "Original file kept raw for comparison and provenance only (user decision 1).",
        True,
    ),
    SourceSpec("matches 2026.csv", SKIPPED, (), None, None, False, "Skipped by user decision 2."),
    SourceSpec(
        "batting_stats2026.csv", SKIPPED, (), None, None, False, "Skipped by user decision 2."
    ),
    SourceSpec(
        "bowling_stats2026.csv", SKIPPED, (), None, None, False, "Skipped by user decision 2."
    ),
    SourceSpec(
        "fielding_stats2026.csv", SKIPPED, (), None, None, False, "Skipped by user decision 2."
    ),
    SourceSpec(
        "ipl squad.csv",
        PENDING,
        (),
        None,
        None,
        False,
        "Franchise squad file; hash and row count only, no table populated in Phase 2.",
    ),
)

SPEC_BY_NAME = {s.file_name: s for s in SOURCES}

# Source file -> tables whose row count must equal the file row count (idempotency tamper guard).
COUNT_TABLES: dict[str, tuple[str, ...]] = {
    "competitions.csv": ("competitions",),
    "teams.csv": ("competition_teams",),
    "matches.csv": ("matches", "match_reconciliation"),
    "playing_eleven.csv": ("match_squads",),
    "competition_team_player_mapping.csv": ("player_competition_mapping",),
    UPDATED: ("raw_ball_by_ball_updated", "deliveries"),
    ORIGINAL: ("raw_ball_by_ball",),
}

COUNT_TABLES_ALL: tuple[str, ...] = (
    "competitions",
    "teams",
    "competition_teams",
    "venues",
    "players",
    "player_competition_mapping",
    "matches",
    "match_squads",
    "innings",
    "deliveries",
    "match_reconciliation",
    "raw_ball_by_ball",
    "raw_ball_by_ball_updated",
    "ball_by_ball_comparison",
    "ball_by_ball_comparison_detail",
)

# Row counts stated in the brief / Phase 1; used only as `expected` labels in validation.
EXPECTED_ROWS: dict[str, int] = {
    "competitions": 141,
    "competition_teams": 353,
    "teams": 38,
    "matches": 883,
    "match_squads": 28381,
    "player_competition_mapping": 6413,
    "raw_ball_by_ball": 200999,
    "raw_ball_by_ball_updated": 200999,
    "deliveries": 200999,
    "match_reconciliation": 883,
}


# ----------------------------------------------------------------------------------------------
# File profiling
# ----------------------------------------------------------------------------------------------
def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def read_header(path: Path) -> list[str]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh), [])


def read_csv_sql(path: Path) -> str:
    return (
        f"read_csv({sql_quote(posix(path))}, header=true, delim=',', quote='\"', escape='\"', all_varchar=true, "
        "parallel=false, sample_size=-1)"
    )


def count_rows(db, path: Path) -> int:
    return int(db.scalar(f"SELECT count(*) FROM {read_csv_sql(path)}"))


def header_problem(spec: SourceSpec, header: list[str]) -> str | None:
    if spec.columns is None:
        return None
    expected = list(spec.columns)
    if spec.column_order_free:
        if sorted(header) != sorted(expected):
            return f"header mismatch: expected {sorted(expected)}, found {sorted(header)}"
    elif header != expected:
        return f"header mismatch: expected {expected}, found {header}"
    return None


# ----------------------------------------------------------------------------------------------
# Cast expressions
# ----------------------------------------------------------------------------------------------
def q(col: str) -> str:
    return '"' + col.replace('"', '""') + '"'


_BOOL = "CASE lower(trim({c})) WHEN 'true' THEN TRUE WHEN 'false' THEN FALSE WHEN '1' THEN TRUE WHEN '0' THEN FALSE END"
_TS = "try_strptime(replace(trim({c}), ' UTC', ''), '%Y-%m-%d %H:%M:%S')"


def cast_expr(col: str, kind: str, alias: str = "") -> str:
    c = f"{alias}.{q(col)}" if alias else q(col)
    return {
        "INTEGER": f"TRY_CAST({c} AS INTEGER)",
        "DOUBLE": f"TRY_CAST({c} AS DOUBLE)",
        "DATE": f"TRY_CAST({c} AS DATE)",
        "BOOL": _BOOL.format(c=c),
        "TS": _TS.format(c=c),
    }[kind]


# stage table -> list of (column, kind, is_key). A key failure aborts the run.
CAST_SPECS: dict[str, list[tuple[str, str, bool]]] = {
    "stg_competitions": [("comp_id", "INTEGER", True)],
    "stg_teams": [("comp_id", "INTEGER", True), ("team_id", "INTEGER", True)],
    "stg_matches": [
        ("match_id", "INTEGER", True),
        ("comp_id", "INTEGER", True),
        ("match_number", "INTEGER", False),
        ("match_date", "DATE", True),
        ("venue_id", "INTEGER", False),
        ("home_team_id", "INTEGER", True),
        ("away_team_id", "INTEGER", True),
        ("home_team_captain_id", "INTEGER", False),
        ("away_team_captain_id", "INTEGER", False),
        ("toss_win_team_id", "INTEGER", False),
        ("man_of_the_match", "INTEGER", False),
        ("first_inn_revised_overs", "DOUBLE", False),
        ("second_inn_revised_overs", "DOUBLE", False),
        ("revised_target", "INTEGER", False),
        ("knock_out", "BOOL", False),
        ("win_team_id", "INTEGER", False),
    ],
    "stg_pe": [
        ("match_id", "INTEGER", True),
        ("team_id", "INTEGER", True),
        ("player_id", "INTEGER", True),
        ("batting_order", "INTEGER", False),
        ("is_played", "BOOL", False),
        ("is_captain", "BOOL", False),
        ("is_wk", "BOOL", False),
        ("is_impact", "BOOL", False),
        ("is_impact_off", "BOOL", False),
    ],
    "stg_map": [
        ("comp_id", "INTEGER", True),
        ("team_id", "INTEGER", True),
        ("player_id", "INTEGER", True),
    ],
    "stg_upd": [
        ("match_id", "INTEGER", True),
        ("innings", "INTEGER", True),
        ("innings_ball_num", "INTEGER", True),
        ("batting_team_id", "INTEGER", True),
        ("bowling_team_id", "INTEGER", True),
        ("overid", "INTEGER", False),
        ("over_ball_num", "INTEGER", False),
        ("striker_id", "INTEGER", False),
        ("non_striker_id", "INTEGER", False),
        ("bowler_id", "INTEGER", False),
        ("batting_order", "INTEGER", False),
        ("runs", "INTEGER", False),
        ("is_four", "BOOL", False),
        ("is_six", "BOOL", False),
        ("is_wicket", "BOOL", False),
        ("dismissal_type_id", "INTEGER", False),
        ("dismissed_player_id", "INTEGER", False),
        ("extras1_runs", "INTEGER", False),
        ("extras_2_runs", "INTEGER", False),
        ("bowl_speed", "DOUBLE", False),
        ("delivery_ist_time", "TS", False),
    ],
}


def cast_failure_sql(stage: str, col: str, kind: str) -> str:
    c = q(col)
    return (
        f"SELECT source_row_no, {c} FROM {stage} WHERE {c} IS NOT NULL AND trim({c}) <> '' "
        f"AND {cast_expr(col, kind)} IS NULL ORDER BY source_row_no"
    )


# ----------------------------------------------------------------------------------------------
# Staging and typed INSERT statements
# ----------------------------------------------------------------------------------------------
def stage_sql(table: str, path: Path) -> str:
    return (
        f"CREATE OR REPLACE TEMP TABLE {table} AS SELECT *, "
        f"CAST(row_number() OVER () AS INTEGER) AS source_row_no FROM {read_csv_sql(path)}"
    )


def insert_raw_sql(target: str, stage: str, file_name: str, run_id: int) -> str:
    cols = ", ".join(q(c) for c in BALL_COLUMNS)
    return (
        f"INSERT INTO {target} ({cols}, source_file, source_row_no, ingestion_run_id) "
        f"SELECT {cols}, {sql_quote(file_name)}, source_row_no, {int(run_id)} FROM {stage}"
    )


def insert_competitions_sql(run_id: int) -> str:
    return f"""
INSERT INTO competitions
SELECT TRY_CAST(comp_id AS INTEGER), comp_name, match_format, season,
       CASE WHEN comp_name LIKE 'IPL%' THEN 'IPL'
            WHEN match_format = 'T20I' THEN 'T20I' ELSE 'OTHER_T20' END,
       'competitions.csv', source_row_no, {int(run_id)}
FROM stg_competitions"""


def insert_teams_sql(run_id: int) -> str:
    return f"""
INSERT INTO teams
SELECT TRY_CAST(team_id AS INTEGER), min(team_name), 'teams.csv', min(source_row_no),
       {int(run_id)}
FROM stg_teams GROUP BY TRY_CAST(team_id AS INTEGER)"""


def insert_competition_teams_sql(run_id: int) -> str:
    return f"""
INSERT INTO competition_teams
SELECT TRY_CAST(comp_id AS INTEGER), TRY_CAST(team_id AS INTEGER), team_name,
       'teams.csv', source_row_no, {int(run_id)}
FROM stg_teams"""


def insert_venues_sql(run_id: int) -> str:
    return f"""
INSERT INTO venues
SELECT TRY_CAST(venue_id AS INTEGER), min(venue_country), 'matches.csv', min(source_row_no),
       {int(run_id)}
FROM stg_matches WHERE venue_id IS NOT NULL GROUP BY TRY_CAST(venue_id AS INTEGER)"""


def insert_players_sql(run_id: int) -> str:
    return f"""
INSERT INTO players
WITH map AS (
    SELECT TRY_CAST(player_id AS INTEGER) pid, player_name nm FROM stg_map),
pe AS (SELECT DISTINCT TRY_CAST(player_id AS INTEGER) pid FROM stg_pe),
dl AS (
    SELECT TRY_CAST(striker_id AS INTEGER) pid, striker_name nm FROM stg_upd
    UNION ALL SELECT TRY_CAST(non_striker_id AS INTEGER), non_striker_name FROM stg_upd
    UNION ALL SELECT TRY_CAST(bowler_id AS INTEGER), bowler_name FROM stg_upd
    UNION ALL SELECT TRY_CAST(dismissed_player_id AS INTEGER), NULL FROM stg_upd),
cap AS (
    SELECT TRY_CAST(home_team_captain_id AS INTEGER) pid FROM stg_matches
    UNION SELECT TRY_CAST(away_team_captain_id AS INTEGER) FROM stg_matches),
ids AS (
    SELECT pid FROM map UNION SELECT pid FROM pe UNION SELECT pid FROM dl
    UNION SELECT pid FROM cap),
names AS (
    SELECT pid, nm, 'M' src FROM map WHERE nm IS NOT NULL
    UNION ALL SELECT pid, nm, 'D' FROM dl WHERE nm IS NOT NULL),
agg AS (
    SELECT pid, min(nm) FILTER (WHERE src = 'M') map_name,
           min(nm) FILTER (WHERE src = 'D') del_name,
           CAST(to_json(list_sort(list_distinct(list(nm)))) AS VARCHAR) variants
    FROM names GROUP BY pid),
dup_names AS (
    SELECT nm FROM map WHERE nm IS NOT NULL GROUP BY nm HAVING count(DISTINCT pid) > 1)
SELECT i.pid,
       coalesce(a.map_name, a.del_name, '<unknown id ' || i.pid || '>'),
       CASE WHEN a.map_name IS NOT NULL THEN 'MAPPING'
            WHEN a.del_name IS NOT NULL THEN 'DELIVERIES' ELSE 'UNKNOWN' END,
       coalesce(a.variants, '[]'),
       coalesce(i.pid IN (SELECT pid FROM map WHERE pid IS NOT NULL), FALSE),
       coalesce(i.pid IN (SELECT pid FROM pe WHERE pid IS NOT NULL), FALSE),
       coalesce(i.pid IN (SELECT pid FROM dl WHERE pid IS NOT NULL), FALSE),
       coalesce(i.pid IN (SELECT pid FROM cap WHERE pid IS NOT NULL), FALSE),
       coalesce(a.map_name IN (SELECT nm FROM dup_names), FALSE),
       'competition_team_player_mapping.csv; playing_eleven.csv; updated_ball_by_ball.csv; matches.csv',
       {int(run_id)}
FROM ids i LEFT JOIN agg a ON a.pid = i.pid WHERE i.pid IS NOT NULL"""


def insert_mapping_sql(run_id: int) -> str:
    return f"""
INSERT INTO player_competition_mapping
SELECT TRY_CAST(comp_id AS INTEGER), TRY_CAST(team_id AS INTEGER),
       TRY_CAST(player_id AS INTEGER), player_name,
       'competition_team_player_mapping.csv', source_row_no, {int(run_id)}
FROM stg_map"""


def insert_matches_sql(run_id: int) -> str:
    c = cast_expr
    return f"""
INSERT INTO matches
SELECT {c("match_id", "INTEGER", "m")}, {c("comp_id", "INTEGER", "m")},
       {c("match_number", "INTEGER", "m")}, {c("match_date", "DATE", "m")}, m.stage,
       {c("venue_id", "INTEGER", "m")}, m.venue_country,
       {c("home_team_id", "INTEGER", "m")}, m.home_team,
       {c("away_team_id", "INTEGER", "m")}, m.away_team,
       {c("home_team_captain_id", "INTEGER", "m")}, {c("away_team_captain_id", "INTEGER", "m")},
       {c("toss_win_team_id", "INTEGER", "m")}, m.toss_opted,
       {c("man_of_the_match", "INTEGER", "m")},
       {c("first_inn_revised_overs", "DOUBLE", "m")}, {c("second_inn_revised_overs", "DOUBLE", "m")},
       {c("revised_target", "INTEGER", "m")}, {c("knock_out", "BOOL", "m")},
       {c("win_team_id", "INTEGER", "m")}, m.result,
       rm.result_status, comp.competition_type, d.mid IS NOT NULL, d.first_bat,
       'matches.csv', m.source_row_no, {int(run_id)}
FROM stg_matches m
LEFT JOIN competitions comp ON comp.comp_id = {c("comp_id", "INTEGER", "m")}
LEFT JOIN stg_result_map rm ON rm.result = coalesce(m.result, '')
LEFT JOIN (
    SELECT match_id AS mid, min(batting_team_id) FILTER (WHERE innings_number = 1) AS first_bat
    FROM t_del GROUP BY match_id) d ON d.mid = {c("match_id", "INTEGER", "m")}"""


def create_t_del_sql() -> str:
    """Typed deliveries from the authoritative file (temp table; not provenance-stamped)."""
    c = cast_expr
    return f"""
CREATE OR REPLACE TEMP TABLE t_del AS
SELECT {c("match_id", "INTEGER")} AS match_id, {c("innings", "INTEGER")} AS innings_number,
       {c("innings_ball_num", "INTEGER")} AS innings_ball_num,
       {c("overid", "INTEGER")} AS overid, {c("over_ball_num", "INTEGER")} AS over_ball_num,
       {c("batting_team_id", "INTEGER")} AS batting_team_id,
       {c("bowling_team_id", "INTEGER")} AS bowling_team_id,
       {c("striker_id", "INTEGER")} AS striker_id,
       {c("non_striker_id", "INTEGER")} AS non_striker_id,
       {c("bowler_id", "INTEGER")} AS bowler_id,
       {c("batting_order", "INTEGER")} AS batting_order,
       batting_type, bowling_type, pace_or_spin, {c("bowl_speed", "DOUBLE")} AS bowl_speed,
       stroke, delivery_style, over_or_around, on_or_off,
       {c("is_four", "BOOL")} AS is_four, {c("is_six", "BOOL")} AS is_six,
       {c("is_wicket", "BOOL")} AS is_wicket,
       {c("dismissal_type_id", "INTEGER")} AS dismissal_type_id, dismissal_type,
       {c("dismissed_player_id", "INTEGER")} AS dismissed_player_id,
       {c("runs", "INTEGER")} AS batter_runs, extras_type,
       (extras_type IS NOT NULL AND extras_type <> 'None') AS has_extra,
       {c("extras1_runs", "INTEGER")} AS extras_primary_runs,
       {c("extras_2_runs", "INTEGER")} AS extras_secondary_runs,
       'UNVERIFIED' AS extras_split_status,
       (extras_type IS NULL OR extras_type NOT IN ('wide', 'Overstep', 'other')) AS is_legal_ball,
       CASE WHEN extras_type = 'Penalty' THEN 'UNVERIFIED' ELSE 'VERIFIED' END AS legal_ball_status,
       coalesce(extras_type IN ('other', 'Penalty'), FALSE) AS extras_label_unverified,
       CASE WHEN {c("is_wicket", "BOOL")} IS NOT TRUE
                 AND {c("dismissed_player_id", "INTEGER")} IS NOT NULL
            THEN 'DISMISSED_PLAYER_WITHOUT_WICKET'
            WHEN {c("is_wicket", "BOOL")} IS TRUE
                 AND {c("dismissed_player_id", "INTEGER")} IS NULL
            THEN 'WICKET_WITHOUT_DISMISSED_PLAYER' END AS dismissal_field_anomaly,
       delivery_ist_time AS delivery_time_raw, {c("delivery_ist_time", "TS")} AS delivery_ts,
       CASE WHEN {c("delivery_ist_time", "TS")} IS NULL THEN NULL
            ELSE CAST({c("delivery_ist_time", "TS")} AS TIME) = TIME '00:00:00'
       END AS delivery_time_is_midnight,
       source_row_no
FROM stg_upd"""


def insert_match_squads_sql(run_id: int) -> str:
    c = cast_expr
    return f"""
INSERT INTO match_squads
WITH p AS (
    SELECT {c("match_id", "INTEGER")} AS match_id, {c("team_id", "INTEGER")} AS team_id,
           {c("player_id", "INTEGER")} AS player_id, {c("batting_order", "INTEGER")} AS bo,
           {c("is_played", "BOOL")} AS is_played, {c("is_captain", "BOOL")} AS is_captain,
           {c("is_wk", "BOOL")} AS is_wk, {c("is_impact", "BOOL")} AS is_impact,
           {c("is_impact_off", "BOOL")} AS is_impact_off, source_row_no
    FROM stg_pe)
SELECT p.match_id, p.team_id, p.player_id,
       CAST(row_number() OVER w AS INTEGER), p.bo, p.is_played, p.is_captain, p.is_wk,
       p.is_impact, p.is_impact_off,
       count(*) OVER g > 1, CAST(count(*) OVER g AS INTEGER),
       pm.player_id IS NOT NULL,
       'playing_eleven.csv', p.source_row_no, {int(run_id)}
FROM p
LEFT JOIN matches mm ON mm.match_id = p.match_id
LEFT JOIN player_competition_mapping pm
       ON pm.comp_id = mm.comp_id AND pm.team_id = p.team_id AND pm.player_id = p.player_id
WINDOW w AS (PARTITION BY p.match_id, p.team_id, p.player_id ORDER BY p.source_row_no),
       g AS (PARTITION BY p.match_id, p.team_id, p.player_id)"""


def insert_innings_sql(run_id: int) -> str:
    return f"""
INSERT INTO innings
SELECT match_id, innings_number, min(batting_team_id), min(bowling_team_id),
       count(DISTINCT batting_team_id) = 1 AND count(DISTINCT bowling_team_id) = 1,
       CAST(count(*) AS INTEGER), CAST(count(*) FILTER (WHERE is_legal_ball) AS INTEGER),
       CAST(sum(batter_runs) AS INTEGER), CAST(sum(extras_primary_runs) AS INTEGER),
       CAST(sum(extras_secondary_runs) AS INTEGER),
       CAST(coalesce(sum(batter_runs), 0) + coalesce(sum(extras_primary_runs), 0)
            + coalesce(sum(extras_secondary_runs), 0) AS INTEGER),
       CAST(count(*) FILTER (WHERE is_wicket) AS INTEGER), max(overid),
       CASE WHEN innings_number >= 3 THEN 'UNVERIFIED' ELSE 'STANDARD' END,
       {sql_quote(UPDATED)}, min(source_row_no), max(source_row_no), {int(run_id)}
FROM t_del GROUP BY match_id, innings_number"""


def insert_deliveries_sql(run_id: int) -> str:
    return f"""
INSERT INTO deliveries
SELECT match_id, innings_number, innings_ball_num, overid, over_ball_num, batting_team_id,
       bowling_team_id, striker_id, non_striker_id, bowler_id, batting_order, batting_type,
       bowling_type, pace_or_spin, bowl_speed, stroke, delivery_style, over_or_around, on_or_off,
       is_four, is_six, is_wicket, dismissal_type_id, dismissal_type, dismissed_player_id,
       batter_runs, extras_type, has_extra, extras_primary_runs, extras_secondary_runs,
       extras_split_status, is_legal_ball, legal_ball_status, extras_label_unverified,
       dismissal_field_anomaly, delivery_time_raw, delivery_ts, delivery_time_is_midnight,
       {sql_quote(UPDATED)}, source_row_no, {int(run_id)}
FROM t_del"""


def insert_reconciliation_sql(run_id: int) -> str:
    return f"""
INSERT INTO match_reconciliation
SELECT m.match_id, m.comp_id, m.match_date, m.home_team_id, m.away_team_id, m.result,
       m.result_status, m.win_team_id, m.has_deliveries,
       coalesce(d.n, 0), coalesce(i.n, 0), coalesce(s.n, 0), coalesce(s.played, 0),
       (NOT m.has_deliveries AND m.result_status IN ('ABANDONED', 'NO_RESULT')
        AND m.win_team_id IS NULL),
       CASE WHEN m.has_deliveries THEN NULL
            ELSE 'no deliveries; result=' || coalesce(m.result, '<null>')
                 || '; result_status=' || m.result_status
                 || '; win_team_id=' || coalesce(CAST(m.win_team_id AS VARCHAR), '<null>')
                 || '; squad_rows=' || coalesce(s.n, 0) END,
       'matches.csv', m.source_row_no, {int(run_id)}
FROM matches m
LEFT JOIN (SELECT match_id, CAST(count(*) AS INTEGER) n FROM deliveries GROUP BY match_id) d
       ON d.match_id = m.match_id
LEFT JOIN (SELECT match_id, CAST(count(*) AS INTEGER) n FROM innings GROUP BY match_id) i
       ON i.match_id = m.match_id
LEFT JOIN (SELECT match_id, CAST(count(*) AS INTEGER) n,
                  CAST(count(*) FILTER (WHERE is_played) AS INTEGER) played
           FROM match_squads GROUP BY match_id) s ON s.match_id = m.match_id"""


def comparison_sql(run_id: int) -> list[str]:
    """Statements filling ball_by_ball_comparison(+detail) from stg_orig vs stg_upd."""
    cols = list(BALL_COLUMNS)
    on = "o.match_id = u.match_id AND o.innings = u.innings AND o.innings_ball_num = u.innings_ball_num"
    stmts: list[str] = []
    for col in cols:
        cc = q(col)
        extra = "NULL"
        if col == "extras1_runs":
            extra = (
                "(SELECT CAST(to_json(list({'original_value': a, 'updated_value': b, "
                "'extras_type': t, 'rows': n})) AS VARCHAR) FROM ("
                "SELECT o.extras1_runs a, u.extras1_runs b, u.extras_type t, count(*) n "
                f"FROM stg_orig o JOIN stg_upd u ON {on} "
                "GROUP BY 1, 2, 3 ORDER BY t, a, b))"
            )
        stmts.append(
            f"""INSERT INTO ball_by_ball_comparison
SELECT {sql_quote(col)},
       (SELECT count(*) FROM stg_orig o JOIN stg_upd u ON {on}),
       (SELECT count(*) FROM stg_orig o JOIN stg_upd u ON {on}
         WHERE o.{cc} IS DISTINCT FROM u.{cc}),
       (SELECT count(*) FROM stg_orig o WHERE NOT EXISTS (
            SELECT 1 FROM stg_upd u WHERE {on})),
       (SELECT count(*) FROM stg_upd u WHERE NOT EXISTS (
            SELECT 1 FROM stg_orig o WHERE {on})),
       {extra}, {sql_quote(ORIGINAL + " vs " + UPDATED)}, {int(run_id)}"""
        )
        if col != "extras1_runs":
            stmts.append(
                f"""INSERT INTO ball_by_ball_comparison_detail
SELECT o.match_id, o.innings, o.innings_ball_num, {sql_quote(col)}, o.{cc}, u.{cc},
       {sql_quote(ORIGINAL + " vs " + UPDATED)}, {int(run_id)}
FROM stg_orig o JOIN stg_upd u ON {on} WHERE o.{cc} IS DISTINCT FROM u.{cc}"""
            )
    return stmts
