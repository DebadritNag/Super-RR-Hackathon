"""Phase 1 audit orchestration: runs every audit step and writes all report files."""

from __future__ import annotations

import hashlib
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from app.core.config import Settings
from app.core.logging import get_logger
from app.data_pipeline import (
    ball_by_ball_inspector as bbi,
)
from app.data_pipeline import (
    cricsheet_auditor as csa,
)
from app.data_pipeline import (
    data_quality as dq,
)
from app.data_pipeline.dataset_discovery import (
    EXPECTED_CSVS,
    EXPECTED_JSON_DIRS,
    discover_datasets,
    find_problem_statement_pdf,
)
from app.data_pipeline.pdf_extractor import extract_pdf_text, find_requirement_hints
from app.data_pipeline.schema_validator import (
    EXPECTED_SCHEMAS,
    compare_schema,
    describe_file,
    read_csv_header,
)
from app.data_pipeline.squad_auditor import audit_squad
from app.utils.jsonio import to_jsonable, write_json

log = get_logger(__name__)

KEYS: dict[str, list[str]] = {
    "competitions.csv": ["comp_id"],
    "teams.csv": ["comp_id", "team_id"],
    "matches.csv": ["match_id"],
    "playing_eleven.csv": ["match_id", "team_id", "player_id"],
    "competition_team_player_mapping.csv": ["comp_id", "team_id", "player_id"],
    "ball_by_ball.csv": bbi.KEY,
    "updated_ball_by_ball.csv": bbi.KEY,
    "ipl squad.csv": ["team_name", "player"],
}
ID_COLS: dict[str, list[str]] = {
    "competitions.csv": ["comp_id"],
    "teams.csv": ["comp_id", "team_id"],
    "matches.csv": ["match_id", "comp_id", "venue_id", "home_team_id", "away_team_id"],
    "playing_eleven.csv": ["match_id", "team_id", "player_id"],
    "competition_team_player_mapping.csv": ["comp_id", "team_id", "player_id"],
    "ball_by_ball.csv": [
        "match_id",
        "batting_team_id",
        "bowling_team_id",
        "striker_id",
        "non_striker_id",
        "bowler_id",
    ],
}
CATEGORY_COLS: dict[str, list[str]] = {
    "competitions.csv": ["match_format", "season"],
    "matches.csv": ["stage", "toss_opted", "knock_out", "venue_country", "man_of_the_match"],
    "playing_eleven.csv": [
        "is_played",
        "is_captain",
        "is_wk",
        "is_impact",
        "is_impact_off",
        "batting_order",
    ],
    "ball_by_ball.csv": [
        "innings",
        "extras_type",
        "is_wicket",
        "dismissal_type",
        "pace_or_spin",
        "batting_type",
        "over_or_around",
        "on_or_off",
    ],
}
VIEW_NAMES = {
    "competitions.csv": "competitions",
    "teams.csv": "teams",
    "matches.csv": "matches",
    "playing_eleven.csv": "playing_eleven",
    "competition_team_player_mapping.csv": "mapping",
    "ball_by_ball.csv": "bbb",
    "updated_ball_by_ball.csv": "bbb_u",
    "ipl squad.csv": "squad",
    "matches 2026.csv": "matches_2026",
    "batting_stats2026.csv": "batting_2026",
    "bowling_stats2026.csv": "bowling_2026",
    "fielding_stats2026.csv": "fielding_2026",
}
IPL_PRED = "(lower(c.comp_name) LIKE 'ipl %' OR lower(c.comp_name) LIKE '%indian premier league%')"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stream_line_count(path: Path) -> int:
    """Independent row counter: raw newline count minus header (no CSV parser)."""
    n = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            n += chunk.count(b"\n")
    return n


def snapshot_root(root: Path) -> list[dict]:
    out = []
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if p.is_file():
            st = p.stat()
            out.append(
                {
                    "name": p.name,
                    "bytes": st.st_size,
                    "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                }
            )
    return out


def _df(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    return con.execute(sql).df()


def audit_csv_files(con, found: dict[str, Path]) -> dict:
    out: dict = {}
    for name, path in found.items():
        exp = EXPECTED_CSVS.get(name)
        log.info("auditing %s", name)
        desc = describe_file(con, path)
        header = read_csv_header(path)
        entry = {
            "path": path,
            "bytes": path.stat().st_size,
            "rows": desc["rows"],
            "expected_rows": exp.expected_rows if exp else None,
            "row_delta_vs_spec": (desc["rows"] - exp.expected_rows)
            if exp and exp.expected_rows is not None
            else None,
            "columns": header,
            "column_count": len(header),
            "expected_column_count": exp.expected_cols if exp else None,
            "schema_vs_spec": compare_schema(header, EXPECTED_SCHEMAS[name])
            if name in EXPECTED_SCHEMAS
            else None,
            "column_stats": desc["column_stats"],
            "independent_line_count_minus_header": stream_line_count(path) - 1,
        }
        view = VIEW_NAMES[name]
        entry["exact_duplicate_rows"] = dq.duplicate_rows(con, view)
        if name in KEYS:
            entry["duplicate_primary_key"] = dq.duplicate_keys(con, view, KEYS[name])
        entry["invalid_ids"] = [dq.invalid_ids(con, view, c) for c in ID_COLS.get(name, [])]
        entry["categories"] = {
            c: dq.value_counts(con, view, c, 40) for c in CATEGORY_COLS.get(name, [])
        }
        out[name] = entry
    m = out["matches.csv"]
    m["date_range"] = dq.date_range(con, "matches", "match_date")
    m["result_classes"] = (
        _df(con, "SELECT result FROM matches")["result"]
        .map(dq.classify_result)
        .value_counts()
        .to_dict()
    )
    out["ball_by_ball.csv"]["delivery_time_range"] = con.execute(
        "SELECT min(delivery_ist_time), max(delivery_ist_time), "
        "count(*) FILTER (WHERE delivery_ist_time LIKE '% 00:00:00 UTC'), count(*) FROM bbb"
    ).fetchone()
    out["ball_by_ball.csv"]["date_range_from_matches"] = con.execute(
        "SELECT min(m.match_date), max(m.match_date) FROM matches m "
        "WHERE m.match_id IN (SELECT match_id FROM bbb)"
    ).fetchone()
    return out


def entity_counts(con) -> dict:
    q = lambda s: con.execute(s).fetchone()[0]  # noqa: E731
    return {
        "competitions": q("SELECT count(DISTINCT comp_id) FROM competitions"),
        "teams_rows": q("SELECT count(*) FROM teams"),
        "distinct_team_ids_in_teams": q("SELECT count(DISTINCT team_id) FROM teams"),
        "distinct_team_names_in_teams": q("SELECT count(DISTINCT team_name) FROM teams"),
        "matches": q("SELECT count(DISTINCT match_id) FROM matches"),
        "venues": q("SELECT count(DISTINCT venue_id) FROM matches"),
        "venue_countries": q("SELECT count(DISTINCT venue_country) FROM matches"),
        "players_in_mapping": q("SELECT count(DISTINCT player_id) FROM mapping"),
        "players_in_playing_eleven": q("SELECT count(DISTINCT player_id) FROM playing_eleven"),
        "players_in_ball_by_ball": q(
            "SELECT count(DISTINCT p) FROM (SELECT striker_id p FROM bbb UNION "
            "SELECT non_striker_id FROM bbb UNION SELECT bowler_id FROM bbb)"
        ),
        "matches_in_playing_eleven": q("SELECT count(DISTINCT match_id) FROM playing_eleven"),
        "matches_with_ball_by_ball": q("SELECT count(DISTINCT match_id) FROM bbb"),
    }


def comp_format_distribution(con) -> list[dict]:
    return _df(
        con,
        f"""
        SELECT c.match_format, CASE WHEN {IPL_PRED} THEN 'IPL' ELSE 'non-IPL' END AS ipl_flag,
               count(DISTINCT c.comp_id) AS competitions, count(m.match_id) AS matches,
               count(*) FILTER (WHERE m.match_id IN (SELECT match_id FROM bbb)) AS matches_with_balls,
               min(TRY_CAST(m.match_date AS DATE)) AS first_match, max(TRY_CAST(m.match_date AS DATE)) AS last_match
        FROM competitions c LEFT JOIN matches m ON m.comp_id = c.comp_id
        GROUP BY ALL ORDER BY 1, 2
        """,
    ).to_dict("records")


def ipl_competitions(con) -> list[dict]:
    return _df(
        con,
        f"""SELECT c.comp_id, c.comp_name, c.match_format, c.season, count(m.match_id) AS matches
        FROM competitions c LEFT JOIN matches m USING (comp_id)
        WHERE {IPL_PRED} GROUP BY ALL ORDER BY c.season""",
    ).to_dict("records")


def relationship_validation(con) -> dict:
    fk = dq.fk_orphans
    rels = [
        fk(con, "teams", ["comp_id"], "competitions", ["comp_id"]),
        fk(con, "matches", ["comp_id"], "competitions", ["comp_id"]),
        fk(con, "matches", ["comp_id", "home_team_id"], "teams", ["comp_id", "team_id"]),
        fk(con, "matches", ["comp_id", "away_team_id"], "teams", ["comp_id", "team_id"]),
        fk(con, "matches", ["home_team_id"], "teams", ["team_id"]),
        fk(con, "matches", ["win_team_id"], "teams", ["team_id"]),
        fk(con, "matches", ["toss_win_team_id"], "teams", ["team_id"]),
        fk(con, "matches", ["home_team_captain_id"], "mapping", ["player_id"]),
        fk(con, "matches", ["away_team_captain_id"], "mapping", ["player_id"]),
        fk(con, "playing_eleven", ["match_id"], "matches", ["match_id"]),
        fk(con, "playing_eleven", ["team_id"], "teams", ["team_id"]),
        fk(con, "playing_eleven", ["player_id"], "mapping", ["player_id"]),
        fk(con, "mapping", ["comp_id"], "competitions", ["comp_id"]),
        fk(con, "mapping", ["comp_id", "team_id"], "teams", ["comp_id", "team_id"]),
        fk(con, "bbb", ["match_id"], "matches", ["match_id"]),
        fk(con, "bbb", ["batting_team_id"], "teams", ["team_id"]),
        fk(con, "bbb", ["bowling_team_id"], "teams", ["team_id"]),
        fk(con, "bbb", ["striker_id"], "mapping", ["player_id"]),
        fk(con, "bbb", ["non_striker_id"], "mapping", ["player_id"]),
        fk(con, "bbb", ["bowler_id"], "mapping", ["player_id"]),
        fk(con, "bbb", ["dismissed_player_id"], "mapping", ["player_id"]),
        fk(con, "bbb", ["match_id", "striker_id"], "playing_eleven", ["match_id", "player_id"]),
        fk(con, "bbb", ["match_id", "bowler_id"], "playing_eleven", ["match_id", "player_id"]),
    ]
    q = lambda s: con.execute(s).fetchone()  # noqa: E731
    extra = {
        "playing_eleven_rows_without_mapping_for_match_comp_team_player": q(
            "SELECT count(*) FROM playing_eleven p JOIN matches m USING (match_id) WHERE NOT EXISTS "
            "(SELECT 1 FROM mapping x WHERE x.comp_id = m.comp_id AND x.team_id = p.team_id "
            "AND x.player_id = p.player_id)"
        )[0],
        "matches_home_team_name_differs_from_teams_table": q(
            "SELECT count(*) FROM matches m JOIN teams t ON t.comp_id = m.comp_id "
            "AND t.team_id = m.home_team_id WHERE t.team_name <> m.home_team"
        )[0],
        "matches_away_team_name_differs_from_teams_table": q(
            "SELECT count(*) FROM matches m JOIN teams t ON t.comp_id = m.comp_id "
            "AND t.team_id = m.away_team_id WHERE t.team_name <> m.away_team"
        )[0],
        "matches_without_playing_eleven_rows": q(
            "SELECT count(*) FROM matches m WHERE NOT EXISTS "
            "(SELECT 1 FROM playing_eleven p WHERE p.match_id = m.match_id)"
        )[0],
        "bbb_batting_team_not_home_or_away": q(
            "SELECT count(*) FROM (SELECT DISTINCT b.match_id, b.batting_team_id FROM bbb b "
            "JOIN matches m USING (match_id) WHERE b.batting_team_id NOT IN "
            "(m.home_team_id, m.away_team_id))"
        )[0],
        "matches_where_home_team_batted_first": q(
            "SELECT count(*) FROM matches m JOIN (SELECT match_id, any_value(batting_team_id) t "
            "FROM bbb WHERE innings = '1' GROUP BY 1) b USING (match_id) WHERE b.t = m.home_team_id"
        )[0],
        "matches_where_away_team_batted_first": q(
            "SELECT count(*) FROM matches m JOIN (SELECT match_id, any_value(batting_team_id) t "
            "FROM bbb WHERE innings = '1' GROUP BY 1) b USING (match_id) WHERE b.t = m.away_team_id"
        )[0],
    }
    names = {
        "mapping_player_ids_with_multiple_names": con.execute(
            "SELECT player_id, string_agg(DISTINCT player_name, ' | ' ORDER BY player_name) FROM mapping GROUP BY 1 "
            "HAVING count(DISTINCT player_name) > 1 ORDER BY TRY_CAST(player_id AS BIGINT) LIMIT 30"
        ).fetchall(),
        "mapping_player_names_with_multiple_player_ids": con.execute(
            "SELECT player_name, string_agg(DISTINCT player_id, ',' ORDER BY player_id) FROM mapping GROUP BY 1 "
            "HAVING count(DISTINCT player_id) > 1 ORDER BY 1 LIMIT 30"
        ).fetchall(),
        "count_names_with_multiple_ids": q(
            "SELECT count(*) FROM (SELECT player_name FROM mapping GROUP BY 1 "
            "HAVING count(DISTINCT player_id) > 1)"
        )[0],
        "count_ids_with_multiple_names": q(
            "SELECT count(*) FROM (SELECT player_id FROM mapping GROUP BY 1 "
            "HAVING count(DISTINCT player_name) > 1)"
        )[0],
        "count_normalised_names_with_multiple_ids": q(
            "SELECT count(*) FROM (SELECT lower(trim(regexp_replace(player_name,'\\s+',' ','g'))) n "
            "FROM mapping GROUP BY 1 HAVING count(DISTINCT player_id) > 1)"
        )[0],
        "bbb_names_differ_from_mapping_name_for_same_id": q(
            "SELECT count(*) FROM (SELECT DISTINCT striker_id, striker_name FROM bbb b JOIN "
            "(SELECT DISTINCT player_id, player_name FROM mapping) m ON m.player_id = b.striker_id "
            "WHERE m.player_name <> b.striker_name)"
        )[0],
    }
    return {
        "foreign_keys": rels,
        "extra_checks": extra,
        "player_identity": names,
        "team_id_uniqueness": dq.team_id_uniqueness(con),
    }


def playing_eleven_checks(con) -> dict:
    dist = con.execute(
        "SELECT n, count(*) FROM (SELECT match_id, team_id, count(*) FILTER "
        "(WHERE lower(is_played) = 'true') n FROM playing_eleven GROUP BY 1, 2) GROUP BY 1 ORDER BY 1"
    ).fetchall()
    return {
        "players_marked_played_per_team_match_distribution": [[int(a), int(b)] for a, b in dist],
        "impact_rows_by_flags": con.execute(
            "SELECT is_played, is_impact, is_impact_off, count(*) FROM playing_eleven GROUP BY ALL "
            "ORDER BY 4 DESC"
        ).fetchall(),
        "duplicate_pk_matches": con.execute(
            "SELECT count(DISTINCT match_id) FROM (SELECT match_id FROM playing_eleven "
            "GROUP BY match_id, team_id, player_id HAVING count(*) > 1)"
        ).fetchone()[0],
        "duplicate_pk_matches_that_have_super_over_innings_in_bbb": con.execute(
            "SELECT count(DISTINCT d.match_id) FROM (SELECT match_id FROM playing_eleven "
            "GROUP BY match_id, team_id, player_id HAVING count(*) > 1) d "
            "WHERE d.match_id IN (SELECT match_id FROM bbb WHERE innings IN ('3', '4'))"
        ).fetchone()[0],
        "bbb_matches_with_no_played_rows": con.execute(
            "SELECT count(*) FROM (SELECT DISTINCT match_id FROM bbb b WHERE NOT EXISTS "
            "(SELECT 1 FROM playing_eleven p WHERE p.match_id = b.match_id "
            "AND lower(p.is_played) = 'true'))"
        ).fetchone()[0],
    }


def ball_by_ball_deep(con) -> dict:
    out: dict = {}
    for view in ("bbb", "bbb_u"):
        out[view] = {
            "profile": bbi.profile_columns(con, view),
            "counter_behaviour": bbi.ball_counter_behaviour(con, view),
            "extras_crosstab_rows": int(len(bbi.extras_crosstab(con, view))),
        }
    out["original_extras1_codes_by_extras_type"] = [
        [r[0], r[1], int(r[2])]
        for r in con.execute(
            "SELECT extras_type, string_agg(DISTINCT extras1_runs, ',' ORDER BY extras1_runs), "
            "count(DISTINCT extras1_runs) FROM bbb GROUP BY 1 ORDER BY 1"
        ).fetchall()
    ]
    out["updated_extras1_values_by_extras_type"] = [
        [r[0], r[1], int(r[2])]
        for r in con.execute(
            "SELECT extras_type, string_agg(DISTINCT extras1_runs, ',' ORDER BY extras1_runs), "
            "count(DISTINCT extras1_runs) FROM bbb_u GROUP BY 1 ORDER BY 1"
        ).fetchall()
    ]
    out["compare_original_vs_updated"] = bbi.compare_ball_files(con, "bbb", "bbb_u")
    return out


def audit_2026_files(con, found: dict[str, Path], index: pd.DataFrame) -> dict:
    out: dict = {}
    for name in (
        "matches 2026.csv",
        "batting_stats2026.csv",
        "bowling_stats2026.csv",
        "fielding_stats2026.csv",
    ):
        p = found.get(name)
        if p is None:
            out[name] = {"status": "MISSING"}
            continue
        d = describe_file(con, p)
        out[name] = {
            "rows": d["rows"],
            "columns": d["columns"],
            "column_stats": d["column_stats"],
            "bytes": p.stat().st_size,
        }
    if "matches 2026.csv" in found:
        m26 = _df(con, "SELECT * FROM matches_2026")
        dates = pd.to_datetime(m26["date"], format="%B %d, %Y", errors="coerce")
        info = {
            "date_min": dates.min(),
            "date_max": dates.max(),
            "unparseable_dates": int(dates.isna().sum()),
            "teams": sorted(set(m26["team1"]) | set(m26["team2"])),
            "stage_counts": m26["stage"].value_counts().to_dict(),
            "match_result_counts": m26["match_result"].value_counts().to_dict(),
            "has_comp_id": "comp_id" in m26.columns,
            "match_id_range": [
                m26["match_id"].astype(int).min(),
                m26["match_id"].astype(int).max(),
            ],
        }
        official = _df(
            con,
            f"""SELECT m.match_id, m.match_date, m.home_team, m.away_team, m.result,
                (m.match_id IN (SELECT match_id FROM bbb)) AS has_balls
                FROM matches m JOIN competitions c USING (comp_id)
                WHERE {IPL_PRED} AND c.season = '2026'""",
        )
        info["official_ipl_2026_matches_in_matches_csv"] = int(len(official))
        info["official_ipl_2026_with_ball_by_ball"] = int(official["has_balls"].sum())
        info["official_ipl_2026_date_range"] = [
            official["match_date"].min(),
            official["match_date"].max(),
        ]
        od = set(official["match_date"].astype(str))
        d26 = set(dates.dropna().dt.strftime("%Y-%m-%d"))
        info["dates_in_2026_file"] = len(d26)
        info["dates_shared_with_official_ipl_2026"] = len(d26 & od)
        info["dates_only_in_2026_file"] = sorted(d26 - od)[:40]
        info["dates_only_in_official_ipl_2026"] = sorted(od - d26)[:40]
        if len(index):
            cs = index[
                (index["directory"] == "ipl_male_json")
                & (index["date"].astype(str) >= "2026-01-01")
            ]
            info["cricsheet_ipl_2026_matches"] = int(len(cs))
            info["cricsheet_ipl_2026_date_range"] = [cs["date"].min(), cs["date"].max()]
        # Per-match score check: only dates with exactly one match on each side.
        tot = _df(
            con,
            f"""
            SELECT m.match_date AS d, m.match_id,
              sum(TRY_CAST(b.runs AS INT) + TRY_CAST(b.extras1_runs AS INT)
                  + TRY_CAST(b.extras_2_runs AS INT)) FILTER (WHERE b.innings = '1') AS i1,
              count(*) FILTER (WHERE b.innings = '1' AND b.is_wicket = 'true') AS w1,
              sum(TRY_CAST(b.runs AS INT) + TRY_CAST(b.extras1_runs AS INT)
                  + TRY_CAST(b.extras_2_runs AS INT)) FILTER (WHERE b.innings = '2') AS i2,
              count(*) FILTER (WHERE b.innings = '2' AND b.is_wicket = 'true') AS w2
            FROM matches m JOIN competitions c USING (comp_id)
              JOIN bbb_u b USING (match_id)
            WHERE {IPL_PRED} AND c.season = '2026' GROUP BY 1, 2""",
        )
        f26 = m26.assign(d=dates.dt.strftime("%Y-%m-%d"))
        one_f = f26.groupby("d").size()
        one_o = tot.groupby("d").size()
        single = sorted(set(one_f[one_f == 1].index) & set(one_o[one_o == 1].index))
        cmp = f26[f26["d"].isin(single)].merge(tot, on="d")
        same = (
            (cmp["first_ings_score"].astype(float) == cmp["i1"].astype(float))
            & (cmp["second_ings_score"].astype(float) == cmp["i2"].astype(float))
            & (cmp["first_ings_wkts"].astype(float) == cmp["w1"].astype(float))
            & (cmp["second_ings_wkts"].astype(float) == cmp["w2"].astype(float))
        )
        info["score_check_dates_with_single_match_on_both_sides"] = len(single)
        info["score_check_matches_with_identical_scores_and_wickets"] = int(same.sum())
        info["score_check_mismatch_samples"] = (
            cmp[~same][["d", "team1", "team2", "first_ings_score", "i1", "second_ings_score", "i2"]]
            .head(10)
            .to_dict("records")
        )
        out["matches 2026.csv"]["analysis"] = info
    if "batting_stats2026.csv" in found:
        cutoff = out["matches 2026.csv"]["analysis"]["date_max"].strftime("%Y-%m-%d")
        out["batting_stats2026.csv"]["check_cutoff_date"] = cutoff
        out["batting_stats2026.csv"]["check_vs_updated_ball_by_ball"] = _df(
            con,
            f"""
            WITH ipl AS (SELECT m.match_id FROM matches m JOIN competitions c USING (comp_id)
                         WHERE {IPL_PRED} AND c.season = '2026' AND m.match_date <= '{cutoff}'),
            agg AS (SELECT striker_name AS name, sum(TRY_CAST(runs AS INT)) AS runs,
                    count(*) FILTER (WHERE extras_type <> 'wide') AS balls
                    FROM bbb_u WHERE match_id IN (SELECT match_id FROM ipl) GROUP BY 1)
            SELECT count(*) AS stat_rows,
              count(a.name) AS rows_with_same_name_in_ball_by_ball,
              count(*) FILTER (WHERE TRY_CAST(b.runs AS INT) = a.runs) AS runs_equal,
              count(*) FILTER (WHERE TRY_CAST(b.balls_faced AS INT) = a.balls) AS balls_equal,
              count(*) FILTER (WHERE TRY_CAST(b.runs AS INT) = a.runs
                               AND TRY_CAST(b.balls_faced AS INT) = a.balls) AS both_equal
            FROM batting_2026 b LEFT JOIN agg a ON a.name = b.batsman
            """,
        ).to_dict("records")[0]
        out["batting_stats2026.csv"]["check_note"] = (
            "Compared on exact player-name equality against official IPL 2026 matches that have "
            "ball-by-ball rows; names, not ids, because the stats file has no player_id."
        )
    return to_jsonable(out)


def extras_mapping_entries(
    crosstab_orig: pd.DataFrame,
    summary_u: dict,
    summary_o: dict,
    agg_linked: pd.DataFrame,
    orig_codes: list,
    comparison: dict,
    counters: dict,
) -> list[dict]:
    n_inn = summary_u["innings_compared"]
    n_match = summary_u["matches_compared"]

    def ev(key: str, s: dict = summary_u) -> str:
        v = s[key]
        return (
            f"{v['innings_ok']}/{s['innings_compared']} innings, "
            f"{v['matches_all_innings_ok']}/{s['matches_compared']} matches agree"
        )

    pen_rows = int(agg_linked["n_t5"].sum()) if "n_t5" in agg_linked else 0
    other_rows = int(agg_linked["n_t4"].sum()) if "n_t4" in agg_linked else 0
    over_rows = int(agg_linked["n_t1"].sum()) if "n_t1" in agg_linked else 0
    return [
        {
            "field": "runs",
            "code": "(all values)",
            "meaning": "Runs off the bat only (batter runs). Not team runs; excludes wides, byes, "
            "leg-byes, no-ball penalty and penalty runs.",
            "evidence": f"sum(runs) == Cricsheet batter runs: {ev('ok_runs_eq_batter_runs')}; "
            f"sum(runs) == Cricsheet innings total: {ev('F1_sum_runs')} (fails, as expected)",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "extras1_runs (updated_ball_by_ball.csv)",
            "code": "0..5",
            "meaning": "Runs scored from the primary extra on the delivery (wide runs incl. the wide "
            "penalty, no-ball runs, byes, leg-byes, penalty).",
            "evidence": f"runs+extras1+extras2 == Cricsheet innings total: {ev('F3_runs_plus_e1_plus_e2')}; "
            f"extras1+extras2 == Cricsheet extras: {ev('ok_e1_plus_e2_eq_extras')}; "
            f"extras1 on wide rows == Cricsheet wides: {ev('ok_e1_wide_eq_cs_wides')}; "
            f"byes: {ev('ok_e1_byes_eq_cs_byes')}; leg-byes: {ev('ok_e1_legbyes_eq_cs_legbyes')}",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "extras1_runs (ball_by_ball.csv, original)",
            "code": "1,2,3,4,5,6,7",
            "meaning": "NOT a run count. It is a category code that is redundant with extras_type: "
            "6=None, 2=wide, 3=legbyes, 4=byes, 1=Overstep, 5=other, 7=Penalty "
            "(one code per extras_type, see audit JSON original_extras1_codes_by_extras_type).",
            "evidence": f"one-to-one code/type pairing: {orig_codes}; "
            f"runs+extras1+extras2 == Cricsheet total: {ev('F3_runs_plus_e1_plus_e2', summary_o)}",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "extras_2_runs",
            "code": "0.. (mostly 0)",
            "meaning": "Additional extra runs on the same delivery (seen on Overstep/other rows, e.g. "
            "byes or leg-byes run off a no-ball). The exact split between extras1 and "
            "extras2 is not validated; only their sum is.",
            "evidence": f"extras1+extras2 == Cricsheet extras: {ev('ok_e1_plus_e2_eq_extras')}",
            "confidence": "MEDIUM",
            "status": "UNVERIFIED (sum verified, split not verified)",
        },
        {
            "field": "extras_type",
            "code": "'None'",
            "meaning": "Literal text 'None': no extra on the ball.",
            "evidence": f"{int(crosstab_orig[crosstab_orig['extras_type'] == 'None']['n'].sum())} "
            "rows in the original file carry extras_type 'None'; legal-ball rule below validated",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "extras_type",
            "code": "wide",
            "meaning": "Wide. Not a legal ball. Batter runs are 0.",
            "evidence": f"legal-ball rule R2 excludes wides: {ev('ok_legal_R2_also_not_other')}; "
            f"extras1 == Cricsheet wides: {ev('ok_e1_wide_eq_cs_wides')}",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "extras_type",
            "code": "legbyes / byes",
            "meaning": "Leg-byes / byes. Legal ball; runs are extras1_runs (updated file).",
            "evidence": f"byes: {ev('ok_e1_byes_eq_cs_byes')}; leg-byes: {ev('ok_e1_legbyes_eq_cs_legbyes')}",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "extras_type",
            "code": "Overstep",
            "meaning": "No-ball (overstep). Not a legal ball; batter runs on the ball are counted in "
            "`runs`.",
            "evidence": f"Overstep alone == Cricsheet noballs: {ev('ok_e1_Overstep_eq_cs_noballs')}; "
            f"Overstep+other == Cricsheet noballs: {ev('ok_e1_Overstep_plus_other_eq_cs_noballs')}; "
            f"{over_rows} Overstep rows in compared matches",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "extras_type",
            "code": "other",
            "meaning": "Behaves like a no-ball (not a legal ball, 1 extra run). The reason/label "
            "(e.g. free-hit or non-overstep no-ball) is not given in the data.",
            "evidence": f"legal rule excluding wide+Overstep+other == Cricsheet legal balls: "
            f"{ev('ok_legal_R2_also_not_other')} vs without 'other': "
            f"{ev('ok_legal_R1_not_wide_not_Overstep')}; {other_rows} rows in compared matches",
            "confidence": "MEDIUM",
            "status": "VERIFIED as no-ball-like; label meaning UNVERIFIED",
        },
        {
            "field": "extras_type",
            "code": "Penalty",
            "meaning": "Penalty runs (5 in the one observed row). Legal-ball status not determinable.",
            "evidence": f"{pen_rows} Penalty rows among Cricsheet-linked matches; "
            f"{int(crosstab_orig[crosstab_orig['extras_type'] == 'Penalty']['n'].sum())} in the original file",
            "confidence": "LOW",
            "status": "UNVERIFIED",
        },
        {
            "field": "legal delivery rule",
            "code": "extras_type NOT IN ('wide','Overstep','other')",
            "meaning": "A delivery counts as a legal ball when extras_type is not wide, Overstep or "
            "other. Row count per innings, not innings_ball_num, is what to count.",
            "evidence": f"legal rows == Cricsheet legal balls: {ev('ok_legal_R2_also_not_other')}; "
            f"rows == Cricsheet deliveries: {ev('ok_rows_eq_deliveries')}",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "is_wicket",
            "code": "'true'/'false'",
            "meaning": "Wicket on the delivery (any dismissal).",
            "evidence": f"wicket rows == Cricsheet wickets: {ev('ok_wicket_count')}",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
        {
            "field": "innings_ball_num / over_ball_num / overid",
            "code": "-",
            "meaning": "Row counters, not legal-ball counters. innings_ball_num runs 1..n over "
            "every row of the innings (wides and no-balls included); over_ball_num runs "
            "1..rows-in-over and so can exceed 6; overid is the 1-based over number. Count legal "
            "balls with the legal-delivery rule, not with these columns.",
            "evidence": f"innings with innings_ball_num exactly 1..n: "
            f"{counters['innings_ball_num_is_1_to_row_count_without_gaps_or_repeats']}/"
            f"{counters['innings_groups']}; overs with over_ball_num exactly 1..rows: "
            f"{counters['overs_where_over_ball_num_is_1_to_rows'][0]}/"
            f"{counters['overs_where_over_ball_num_is_1_to_rows'][1]}; max overid by innings: "
            f"{counters['max_overid_by_innings']}; innings 3 and 4 are super-over innings "
            f"(rows by innings: {counters['innings_row_counts_by_innings_number']}; "
            "innings numbers 3/4 as super overs is consistent with 1-over max overid, "
            "UNVERIFIED against Cricsheet super_over flags)",
            "confidence": "HIGH",
            "status": "VERIFIED (internal consistency); super-over meaning of innings 3/4 UNVERIFIED",
        },
        {
            "field": "file authority",
            "code": "-",
            "meaning": "Cross-file difference summary: " + comparison["verdict"],
            "evidence": f"{n_inn} innings / {n_match} matches linked to Cricsheet by date+teams",
            "confidence": "HIGH",
            "status": "VERIFIED",
        },
    ]


def write_extras_mapping_md(path: Path, entries: list[dict], extra: dict) -> None:
    lines = [
        "# Extras / runs encoding (data-derived)",
        "",
        "Every row is backed by counts computed in `scripts/audit_datasets.py`. "
        "Cricsheet is the reference, linked by exact date + normalised team names.",
        "",
        "| field | code | meaning | evidence | confidence | status |",
        "|---|---|---|---|---|---|",
    ]
    for e in entries:
        cells = [
            str(e[k]).replace("|", "/").replace("\n", " ")
            for k in ("field", "code", "meaning", "evidence", "confidence", "status")
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "## Unresolved discrepancies", ""]
    for k, v in extra.items():
        lines.append(f"- **{k}**: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_directory_tree(root: Path, extra_ignore: tuple[str, ...] = ()) -> str:
    ignore = {"__pycache__", ".venv", ".ruff_cache", ".pytest_cache", *extra_ignore}
    lines = [root.as_posix() + "/"]

    def walk(d: Path, prefix: str) -> None:
        items = sorted(
            (p for p in d.iterdir() if p.name not in ignore),
            key=lambda p: (p.is_file(), p.name.lower()),
        )
        for i, p in enumerate(items):
            last = i == len(items) - 1
            lines.append(f"{prefix}{'`-- ' if last else '|-- '}{p.name}{'/' if p.is_dir() else ''}")
            if p.is_dir():
                walk(p, prefix + ("    " if last else "|   "))

    walk(root, "")
    return "\n".join(lines) + "\n"


def workspace_listing(root: Path, json_dirs: dict) -> str:
    lines = [f"{root.as_posix()}/ (workspace root; raw datasets are read-only)"]
    for p in sorted(root.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        if p.is_dir():
            if p.name in json_dirs:
                lines.append(
                    f"  {p.name}/  ({json_dirs[p.name]['total_files']} files, "
                    f"{json_dirs[p.name]['json_files']} .json)"
                )
            else:
                lines.append(f"  {p.name}/")
        else:
            lines.append(f"  {p.name}  ({p.stat().st_size:,} bytes)")
    return "\n".join(lines) + "\n"


def md_table(rows: list[dict], cols: list[str], limit: int = 60) -> list[str]:
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows[:limit]:
        out.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/") for c in cols) + " |")
    return out


def run_full_audit(
    settings: Settings, skip_cricsheet: bool = False, output_dir: Path | None = None
) -> dict:
    out_dir = output_dir or settings.audit_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    root = settings.data_root
    before = snapshot_root(root)
    core_hash_files = [n for n in EXPECTED_CSVS if n != "ipl squad.csv"] + [
        "updated_ball_by_ball.csv"
    ]
    hashes_before = {n: sha256(root / n) for n in core_hash_files if (root / n).exists()}

    disc = discover_datasets(root, settings.cricsheet_root)
    log.info(
        "found=%d missing=%s supplementary=%d json_dirs=%d",
        len(disc.found),
        disc.missing,
        len(disc.supplementary),
        len(disc.json_dirs),
    )
    all_csv = {**disc.found, **disc.supplementary}
    con = duckdb.connect()
    dq.register_csv_views(con, {VIEW_NAMES[n]: p for n, p in all_csv.items()})

    bundle: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "duckdb": duckdb.__version__,
            "pandas": pd.__version__,
        },
        "settings": {"data_root": root, "cricsheet_root": settings.cricsheet_root},
        "discovery": {
            "found": disc.found,
            "missing": disc.missing,
            "supplementary": disc.supplementary,
            "other_files": disc.extras,
            "json_dirs": disc.json_dirs,
            "missing_json_dirs": disc.missing_json_dirs,
            "pdfs": disc.pdfs,
        },
        "root_snapshot_before": before,
        "sha256_before": hashes_before,
    }
    csvs = audit_csv_files(con, {**disc.found, **disc.supplementary})
    bundle["csv_files"] = csvs
    bundle["entity_counts"] = entity_counts(con)
    bundle["competition_format_distribution"] = comp_format_distribution(con)
    bundle["ipl_competitions"] = ipl_competitions(con)
    log.info("relationship validation")
    bundle["relationships"] = relationship_validation(con)
    bundle["playing_eleven_checks"] = playing_eleven_checks(con)

    # --- reconciliation ---
    rec = dq.reconcile_matches(con)
    rec_path = out_dir / "match_reconciliation.csv"
    rec.to_csv(rec_path, index=False, encoding="utf-8", lineterminator="\n")
    n_matches = con.execute("SELECT count(DISTINCT match_id) FROM matches").fetchone()[0]
    n_with = con.execute(
        "SELECT count(DISTINCT match_id) FROM matches WHERE match_id IN (SELECT match_id FROM bbb)"
    ).fetchone()[0]
    bundle["match_reconciliation"] = {
        "matches_csv_distinct_match_ids": n_matches,
        "matches_with_ball_by_ball": n_with,
        "matches_without_ball_by_ball": int(len(rec)),
        "identity_holds": bool(n_matches - n_with == len(rec)),
        "status_counts": rec["status"].value_counts().to_dict(),
        "ball_by_ball_match_ids_not_in_matches_csv": dq.bbb_matches_missing_from_matches(con),
        "output_file": rec_path,
    }
    log.info(
        "reconciliation: %d - %d = %d rows (identity %s)",
        n_matches,
        n_with,
        len(rec),
        bundle["match_reconciliation"]["identity_holds"],
    )

    # --- ball-by-ball deep ---
    log.info("ball-by-ball deep inspection")
    bundle["ball_by_ball_deep"] = ball_by_ball_deep(con)
    bbi.extras_crosstab(con, "bbb").to_csv(
        out_dir / "extras_crosstab_original.csv", index=False, lineterminator="\n"
    )
    bbi.extras_crosstab(con, "bbb_u").to_csv(
        out_dir / "extras_crosstab_updated.csv", index=False, lineterminator="\n"
    )

    # --- cricsheet ---
    index = pd.DataFrame()
    cs_report: dict = {"skipped": skip_cricsheet}
    if not skip_cricsheet:
        records: list[dict] = []
        per_dir: dict = {}
        for dname, expected in EXPECTED_JSON_DIRS.items():
            d = settings.cricsheet_root / dname
            if not d.is_dir():
                per_dir[dname] = {"status": "MISSING"}
                continue
            log.info("cricsheet %s", dname)
            a, r = csa.audit_cricsheet_dir(d, expected)
            per_dir[dname] = a
            records += r
        index = csa.build_index(records)
        index.to_parquet(settings.staging_dir / "cricsheet_index.parquet", index=False)
        matches_df = con.execute("SELECT * FROM matches").df()
        comps_df = con.execute("SELECT * FROM competitions").df()
        cs_report = {
            "skipped": False,
            "per_directory": per_dir,
            "per_directory_row_sum_equals_index_rows": sum(
                v.get("parsed_ok", 0) for v in per_dir.values()
            )
            == len(index),
            "cross_directory_overlap": csa.cross_directory_overlap(index),
            "ipl_cricsheet_vs_official_csv": csa.ipl_overlap_with_csv(index, matches_df, comps_df),
        }
        # ball-by-ball validation against Cricsheet
        ids = {r[0] for r in con.execute("SELECT DISTINCT match_id FROM bbb").fetchall()}
        links = bbi.link_matches_to_cricsheet(matches_df, index, ids)
        link_summary = links["link_status"].value_counts().to_dict()
        link_with_balls = links[links["has_ball_by_ball"]]["link_status"].value_counts().to_dict()
        val_summaries, vals = {}, {}
        for view in ("bbb", "bbb_u"):
            agg = bbi.csv_innings_aggregates(con, view)
            val = bbi.validate_against_cricsheet(agg, links, index)
            vals[view] = (agg, val)
            val_summaries[view] = bbi.summarise_validation(val)
        agg_u, val_u = vals["bbb_u"]
        val_u.to_csv(out_dir / "cricsheet_validation_updated.csv", index=False, lineterminator="\n")
        vals["bbb"][1].to_csv(
            out_dir / "cricsheet_validation_original.csv", index=False, lineterminator="\n"
        )
        mism = val_u[val_u["ok_innings_present_both_sides"] & ~val_u["F3_runs_plus_e1_plus_e2"]]
        cs_report["ball_by_ball_validation"] = {
            "link_status_all_official_matches": link_summary,
            "link_status_matches_with_ball_by_ball": link_with_balls,
            "summary_original_file": val_summaries["bbb"],
            "summary_updated_file": val_summaries["bbb_u"],
            "updated_file_total_formula_mismatches": mism[
                [
                    "match_id",
                    "cricsheet_id",
                    "innings",
                    "rows",
                    "cs_deliveries",
                    "s_runs",
                    "s_e1",
                    "s_e2",
                    "cs_total",
                    "cs_batter",
                    "cs_extras",
                    "cs_super_over",
                ]
            ].to_dict("records"),
            "first_10_matches_updated_file": val_u[val_u["ok_innings_present_both_sides"]]
            .sort_values(["match_id", "innings"], key=lambda s: pd.to_numeric(s, errors="coerce"))
            .head(20)[
                [
                    "match_id",
                    "cricsheet_id",
                    "innings",
                    "s_runs",
                    "s_e1",
                    "s_e2",
                    "cs_total",
                    "F3_runs_plus_e1_plus_e2",
                ]
            ]
            .to_dict("records"),
            "official_matches_without_cricsheet_counterpart_with_balls": links[
                links["has_ball_by_ball"] & (links["link_status"] != "LINKED")
            ]["match_id"].tolist(),
        }
        links.to_csv(
            out_dir / "official_to_cricsheet_candidate_links.csv", index=False, lineterminator="\n"
        )
        ipl_linked = links.merge(
            con.execute(
                f"SELECT m.match_id FROM matches m JOIN competitions c USING (comp_id) WHERE {IPL_PRED}"
            ).df(),
            on="match_id",
        )
        cs_report["ball_by_ball_validation"]["ipl_matches_linked"] = (
            ipl_linked["link_status"].value_counts().to_dict()
        )
        ent = extras_mapping_entries(
            bbi.extras_crosstab(con, "bbb"),
            val_summaries["bbb_u"],
            val_summaries["bbb"],
            agg_u[agg_u["match_id"].isin(links[links["link_status"] == "LINKED"]["match_id"])],
            bundle["ball_by_ball_deep"]["original_extras1_codes_by_extras_type"],
            bundle["ball_by_ball_deep"]["compare_original_vs_updated"],
            bundle["ball_by_ball_deep"]["bbb_u"]["counter_behaviour"],
        )
        mism_txt = (
            f"{len(mism)} innings (of {val_summaries['bbb_u']['innings_compared']}) do not "
            "match the Cricsheet total under runs+extras1+extras2; list in "
            "cricsheet_overlap_report.json -> ball_by_ball_validation -> "
            "updated_file_total_formula_mismatches. Cause not established (UNVERIFIED)."
        )
        write_extras_mapping_md(
            out_dir / "extras_mapping.md",
            ent,
            {
                "Remaining total-runs mismatches": mism_txt,
                "Coverage": f"Only matches linkable to Cricsheet by date+teams were checked "
                f"({link_with_balls}); the rest of ball_by_ball is UNVERIFIED against Cricsheet.",
            },
        )
        bundle["extras_mapping"] = ent
        bundle["twenty26_files"] = audit_2026_files(con, all_csv, index)
    else:
        bundle["twenty26_files"] = {}
    bundle["cricsheet"] = cs_report
    write_json(out_dir / "cricsheet_overlap_report.json", cs_report)

    # --- squad ---
    if "ipl squad.csv" in disc.found:
        mapping_df = con.execute("SELECT * FROM mapping").df()
        bundle["ipl_squad"] = audit_squad(disc.found["ipl squad.csv"], mapping_df)

    # --- PDF ---
    pdf = settings.problem_statement_pdf or find_problem_statement_pdf(root)
    if pdf:
        res = extract_pdf_text(pdf, out_dir / "problem_statement.txt")
        bundle["problem_statement"] = {
            "pdf": pdf,
            "pages": res["pages"],
            "characters": res["characters"],
            "keyword_hints": find_requirement_hints(res["text"]),
            "summary_file": "problem_statement_summary.md (hand-written from the extracted text)",
        }
    else:
        bundle["problem_statement"] = {"status": "PDF NOT FOUND"}

    # --- integrity of originals ---
    after = snapshot_root(root)
    hashes_after = {n: sha256(root / n) for n in hashes_before}
    bundle["originals_unmodified"] = {
        "snapshot_identical": before == after,
        "sha256_identical": hashes_before == hashes_after,
    }

    write_reports(bundle, out_dir, rec)
    (out_dir / "directory_tree.txt").write_text(
        "== workspace root ==\n"
        + workspace_listing(root, disc.json_dirs)
        + "\n== backend ==\n"
        + build_directory_tree(settings.backend_root),
        encoding="utf-8",
        newline="\n",
    )
    con.close()
    return bundle


def write_reports(bundle: dict, out_dir: Path, rec: pd.DataFrame) -> None:
    csvs = bundle["csv_files"]
    write_json(out_dir / "dataset_audit.json", bundle)
    # flat CSV
    rows = []
    for name, e in csvs.items():
        for col, s in e["column_stats"].items():
            rows.append(
                {
                    "file": name,
                    "file_rows": e["rows"],
                    "expected_rows": e["expected_rows"],
                    "column": col,
                    **s,
                }
            )
    pd.DataFrame(rows).to_csv(out_dir / "dataset_audit.csv", index=False, lineterminator="\n")
    write_json(
        out_dir / "schema_report.json",
        {
            "files": {
                n: {
                    "columns": e["columns"],
                    "column_count": e["column_count"],
                    "expected_column_count": e["expected_column_count"],
                    "schema_vs_spec": e["schema_vs_spec"],
                    "inferred_types": {c: s["inferred_type"] for c, s in e["column_stats"].items()},
                }
                for n, e in csvs.items()
            },
            "cricsheet_key_variations": {
                d: {
                    "top_keys": v["counters"]["top_keys"],
                    "info_keys": v["counters"]["info_keys"],
                    "outcome_keys": v["counters"]["outcome_keys"],
                    "innings_keys": v["counters"]["innings_keys"],
                    "delivery_keys": v["counters"]["delivery_keys"],
                    "extras_keys": v["counters"]["extras_keys"],
                    "data_version": v["counters"]["data_version"],
                }
                for d, v in bundle["cricsheet"].get("per_directory", {}).items()
                if "counters" in v
            },
        },
    )
    write_json(
        out_dir / "data_quality_report.json",
        {
            "files": {
                n: {
                    "rows": e["rows"],
                    "exact_duplicate_rows": e["exact_duplicate_rows"],
                    "duplicate_primary_key": e.get("duplicate_primary_key"),
                    "invalid_ids": e["invalid_ids"],
                    "categories": e["categories"],
                    "missing": {
                        c: {"null": s["null_count"], "empty": s["empty_string_count"]}
                        for c, s in e["column_stats"].items()
                        if s["null_count"] or s["empty_string_count"]
                    },
                }
                for n, e in csvs.items()
            },
            "relationships": bundle["relationships"],
            "playing_eleven_checks": bundle["playing_eleven_checks"],
            "match_reconciliation": bundle["match_reconciliation"],
            "entity_counts": bundle["entity_counts"],
            "originals_unmodified": bundle["originals_unmodified"],
        },
    )
    write_json(out_dir / "ball_by_ball_inspection.json", bundle["ball_by_ball_deep"])
    write_md(bundle, out_dir / "dataset_audit.md")


def write_md(b: dict, path: Path) -> None:
    csvs = b["csv_files"]
    L = [
        "# Dataset audit (Phase 1)",
        "",
        f"Generated: {b['generated_at']}",
        "",
        "All numbers below are produced by `scripts/audit_datasets.py`.",
        "",
        "## CSV files: actual vs spec",
        "",
    ]
    rows = [
        {
            "file": n,
            "rows": e["rows"],
            "spec_rows": e["expected_rows"],
            "delta": e["row_delta_vs_spec"],
            "cols": e["column_count"],
            "spec_cols": e["expected_column_count"],
            "dup_rows": e["exact_duplicate_rows"],
            "dup_pk": (e.get("duplicate_primary_key") or {}).get("duplicate_key_groups"),
            "streamed_rows": e["independent_line_count_minus_header"],
        }
        for n, e in csvs.items()
    ]
    L += md_table(
        rows,
        [
            "file",
            "rows",
            "spec_rows",
            "delta",
            "cols",
            "spec_cols",
            "dup_rows",
            "dup_pk",
            "streamed_rows",
        ],
    )
    L += [
        "",
        "Note: `streamed_rows` = raw newline count minus header; it differs from `rows` only "
        "if a file contains embedded newlines in quoted fields.",
        "",
        "## Schema differences vs spec",
        "",
    ]
    for n, e in csvs.items():
        s = e["schema_vs_spec"]
        if s:
            L.append(
                f"- `{n}`: exact={s['matches_exactly']}, missing={s['missing']}, "
                f"unexpected={s['unexpected']}, order_differs={s['order_differs']}"
            )
    L += ["", "## Missing values (null or empty string)", ""]
    for n, e in csvs.items():
        miss = {
            c: (s["null_count"], s["empty_string_count"])
            for c, s in e["column_stats"].items()
            if s["null_count"] or s["empty_string_count"]
        }
        L.append(
            f"- `{n}`: "
            + (", ".join(f"{c}={v[0]}/{v[1]}" for c, v in miss.items()) or "none")
            + " (column=null/empty)"
        )
    L += ["", "## Entity counts", ""] + [f"- {k}: {v}" for k, v in b["entity_counts"].items()]
    L += ["", "## Competition format distribution", ""]
    L += md_table(
        b["competition_format_distribution"],
        [
            "match_format",
            "ipl_flag",
            "competitions",
            "matches",
            "matches_with_balls",
            "first_match",
            "last_match",
        ],
    )
    L += ["", "## Relationships", ""]
    L += md_table(
        b["relationships"]["foreign_keys"],
        ["child", "parent", "child_rows_checked", "orphan_rows", "distinct_orphan_keys"],
    )
    tu = b["relationships"]["team_id_uniqueness"]
    L += [
        "",
        f"team_id is a globally unique key: **{tu['team_id_is_globally_unique_key']}** "
        f"(teams.csv ids with several names: {tu['teams']['team_ids_with_multiple_names']}, "
        f"mapping: {tu['mapping']['team_ids_with_multiple_names']})",
        "",
    ]
    L += [f"- {k}: {v}" for k, v in b["relationships"]["extra_checks"].items()]
    mr = b["match_reconciliation"]
    L += [
        "",
        "## matches.csv vs ball_by_ball reconciliation",
        "",
        f"{mr['matches_csv_distinct_match_ids']} matches - {mr['matches_with_ball_by_ball']} with "
        f"deliveries = {mr['matches_without_ball_by_ball']} without (identity holds: "
        f"{mr['identity_holds']}). Status counts: {mr['status_counts']}. "
        f"ball_by_ball match_ids absent from matches.csv: "
        f"{len(mr['ball_by_ball_match_ids_not_in_matches_csv'])}. Full list: "
        "`match_reconciliation.csv`.",
        "",
    ]
    cmp = b["ball_by_ball_deep"]["compare_original_vs_updated"]
    L += [
        "## ball_by_ball.csv vs updated_ball_by_ball.csv",
        "",
        f"Verdict: **{cmp['verdict']}**; rows {cmp['a_rows']} vs {cmp['b_rows']}; "
        f"differing values per column: {cmp['differing_rows_per_column']}.",
        "",
    ]
    cs = b["cricsheet"]
    if not cs.get("skipped"):
        L += ["## Cricsheet directories", ""]
        L += md_table(
            [
                {
                    "dir": d,
                    "json": v.get("json_files"),
                    "spec": v.get("expected_by_spec"),
                    "delta": v.get("delta_json_vs_spec"),
                    "date_min": v.get("date_min"),
                    "date_max": v.get("date_max"),
                    "errors": len(v.get("read_errors", [])),
                }
                for d, v in cs["per_directory"].items()
            ],
            ["dir", "json", "spec", "delta", "date_min", "date_max", "errors"],
        )
        ov = cs["cross_directory_overlap"]
        L += [
            "",
            f"Index rows {ov['total_index_rows']}, distinct match ids {ov['distinct_match_ids']}; "
            f"ids in several directories: {ov['match_ids_in_multiple_directories']} "
            f"({ov['id_overlap_by_directory_combo']}).",
            "",
        ]
        io = cs["ipl_cricsheet_vs_official_csv"]
        L += [
            f"IPL Cricsheet vs official CSV: csv={io['csv_ipl_matches']}, cricsheet="
            f"{io['cricsheet_ipl_matches']}, matched keys={io['matched_keys']}, "
            f"csv unmatched={io['csv_ipl_unmatched']}, cricsheet unmatched="
            f"{io['cricsheet_ipl_unmatched']}, ambiguous={io['ambiguous_keys']}.",
            "",
        ]
        v = cs["ball_by_ball_validation"]
        L += [
            "## Ball-by-ball totals vs Cricsheet",
            "",
            f"Original file: {v['summary_original_file']['innings_compared']} innings compared, "
            f"formula runs+e1+e2 agrees in "
            f"{v['summary_original_file']['F3_runs_plus_e1_plus_e2']['innings_ok']}.",
            f"Updated file: {v['summary_updated_file']['innings_compared']} innings compared, "
            f"formula runs+e1+e2 agrees in "
            f"{v['summary_updated_file']['F3_runs_plus_e1_plus_e2']['innings_ok']}.",
            "",
            "See `extras_mapping.md` for the full encoding table.",
            "",
        ]
    sq = b.get("ipl_squad")
    if sq:
        L += [
            "## ipl squad.csv",
            "",
            f"rows={sq['rows']}, teams={sq['teams']}, exact name matches (case-sensitive)="
            f"{sq['exact_case_sensitive_matches']}, normalised={sq['exact_normalised_matches']}, "
            f"candidate counts={sq['candidate_id_counts']}.",
            "",
        ]
    ps = b["problem_statement"]
    L += [
        "## Problem statement PDF",
        "",
        f"{ps.get('pages')} pages, {ps.get('characters')} characters "
        "extracted to `problem_statement.txt`; requirements summary in "
        "`problem_statement_summary.md`.",
        "",
        f"Originals unmodified during audit: {b['originals_unmodified']}",
        "",
    ]
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
