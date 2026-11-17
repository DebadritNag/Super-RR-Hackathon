"""Schema inspection for CSV files (read-only)."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb

from app.utils.paths import posix, sql_quote

EXPECTED_SCHEMAS: dict[str, list[str]] = {
    "competitions.csv": ["comp_id", "comp_name", "match_format", "season"],
    "teams.csv": ["comp_id", "team_id", "team_name"],
    "matches.csv": [
        "match_id",
        "comp_id",
        "match_number",
        "match_date",
        "stage",
        "venue_id",
        "venue_country",
        "home_team_id",
        "home_team",
        "away_team_id",
        "away_team",
        "home_team_captain_id",
        "away_team_captain_id",
        "toss_win_team_id",
        "toss_opted",
        "man_of_the_match",
        "first_inn_revised_overs",
        "second_inn_revised_overs",
        "revised_target",
        "knock_out",
        "win_team_id",
        "result",
    ],
    "playing_eleven.csv": [
        "match_id",
        "team_id",
        "player_id",
        "batting_order",
        "is_played",
        "is_captain",
        "is_wk",
        "is_impact",
        "is_impact_off",
    ],
    "competition_team_player_mapping.csv": [
        "comp_id",
        "comp_name",
        "team_id",
        "team_name",
        "player_id",
        "player_name",
    ],
    # Order as listed in the brief (grouped); the real file differs in column order.
    "ball_by_ball.csv": [
        "match_id",
        "innings",
        "overid",
        "over_ball_num",
        "innings_ball_num",
        "delivery_ist_time",
        "batting_team_id",
        "bowling_team_id",
        "striker_id",
        "striker_name",
        "non_striker_id",
        "non_striker_name",
        "bowler_id",
        "bowler_name",
        "batting_order",
        "batting_type",
        "bowling_type",
        "runs",
        "is_four",
        "is_six",
        "is_wicket",
        "dismissal_type_id",
        "dismissal_type",
        "dismissed_player_id",
        "extras_type",
        "extras1_runs",
        "extras_2_runs",
        "pace_or_spin",
        "bowl_speed",
        "stroke",
        "delivery_style",
        "over_or_around",
        "on_or_off",
    ],
    "ipl squad.csv": ["team_no", "team_name", "player", "nationality", "role", "designation"],
}


def read_csv_header(path: Path) -> list[str]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def compare_schema(actual: list[str], expected: list[str]) -> dict:
    missing = [c for c in expected if c not in actual]
    unexpected = [c for c in actual if c not in expected]
    common_actual = [c for c in actual if c in expected]
    common_expected = [c for c in expected if c in actual]
    return {
        "missing": missing,
        "unexpected": unexpected,
        "order_differs": common_actual != common_expected,
        "matches_exactly": actual == expected,
    }


def describe_file(con: duckdb.DuckDBPyConnection, path: Path, max_distinct: bool = True) -> dict:
    """Row count, columns, inferred DuckDB types and per-column null/empty/distinct counts."""
    p = sql_quote(posix(path))
    typed = con.execute(
        f"DESCRIBE SELECT * FROM read_csv({p}, header=true, sample_size=-1)"
    ).fetchall()
    inferred = {r[0]: r[1] for r in typed}
    con.execute(
        f"CREATE OR REPLACE TEMP VIEW _desc AS SELECT * FROM read_csv({p}, header=true, "
        "all_varchar=true, sample_size=-1)"
    )
    n = con.execute("SELECT count(*) FROM _desc").fetchone()[0]
    cols = [r[0] for r in con.execute("DESCRIBE _desc").fetchall()]
    exprs = []
    for c in cols:
        q = '"' + c.replace('"', '""') + '"'
        exprs.append(f"count(*) FILTER (WHERE {q} IS NULL)")
        exprs.append(f"count(*) FILTER (WHERE trim({q}) = '')")
        exprs.append(f"count(DISTINCT {q})" if max_distinct else "0")
    row = con.execute("SELECT " + ", ".join(exprs) + " FROM _desc").fetchone()
    col_stats = {}
    for i, c in enumerate(cols):
        col_stats[c] = {
            "inferred_type": inferred.get(c),
            "null_count": int(row[3 * i]),
            "empty_string_count": int(row[3 * i + 1]),
            "distinct_count": int(row[3 * i + 2]),
        }
    con.execute("DROP VIEW _desc")
    return {"path": path, "rows": int(n), "columns": cols, "column_stats": col_stats}
