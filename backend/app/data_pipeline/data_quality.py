"""Data-quality checks over CSV views registered in DuckDB (read-only)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from app.utils.paths import posix, sql_quote


def _q(col: str) -> str:
    return '"' + col.replace('"', '""') + '"'


def register_csv_views(con: duckdb.DuckDBPyConnection, files: dict[str, Path]) -> None:
    """Create all-VARCHAR views so nothing is silently coerced. files: view name -> path."""
    for view, path in files.items():
        con.execute(
            f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_csv({sql_quote(posix(path))}, "
            "header=true, all_varchar=true, sample_size=-1)"
        )


def duplicate_rows(con: duckdb.DuckDBPyConnection, view: str) -> int:
    """Number of surplus rows that are exact duplicates of another row."""
    total = con.execute(f"SELECT count(*) FROM {view}").fetchone()[0]
    distinct = con.execute(f"SELECT count(*) FROM (SELECT DISTINCT * FROM {view})").fetchone()[0]
    return int(total - distinct)


def duplicate_keys(
    con: duckdb.DuckDBPyConnection, view: str, key_cols: list[str], sample: int = 20
) -> dict:
    keys = ", ".join(_q(c) for c in key_cols)
    n = con.execute(
        f"SELECT count(*), coalesce(sum(c), 0) FROM (SELECT count(*) c FROM {view} "
        f"GROUP BY {keys} HAVING count(*) > 1)"
    ).fetchone()
    samples = con.execute(
        f"SELECT {keys}, count(*) c FROM {view} GROUP BY {keys} HAVING count(*) > 1 "
        f"ORDER BY c DESC, {keys} LIMIT {int(sample)}"
    ).fetchall()
    return {
        "key": key_cols,
        "duplicate_key_groups": int(n[0]),
        "rows_in_duplicate_groups": int(n[1]),
        "samples": [list(r) for r in samples],
    }


def invalid_ids(con: duckdb.DuckDBPyConnection, view: str, col: str) -> dict:
    c = _q(col)
    r = con.execute(
        f"SELECT count(*) FILTER (WHERE {c} IS NULL OR trim({c}) = ''), "
        f"count(*) FILTER (WHERE {c} IS NOT NULL AND trim({c}) <> '' "
        f"AND TRY_CAST({c} AS BIGINT) IS NULL), "
        f"count(*) FILTER (WHERE TRY_CAST({c} AS BIGINT) <= 0) FROM {view}"
    ).fetchone()
    return {
        "column": col,
        "null_or_empty": int(r[0]),
        "non_numeric": int(r[1]),
        "non_positive": int(r[2]),
    }


def value_counts(
    con: duckdb.DuckDBPyConnection, view: str, col: str, limit: int = 50
) -> list[tuple]:
    c = _q(col)
    return con.execute(
        f"SELECT {c} v, count(*) n FROM {view} GROUP BY {c} ORDER BY n DESC, v LIMIT {int(limit)}"
    ).fetchall()


def date_range(con: duckdb.DuckDBPyConnection, view: str, col: str) -> dict:
    c = _q(col)
    r = con.execute(
        f"SELECT min(TRY_CAST({c} AS DATE)), max(TRY_CAST({c} AS DATE)), "
        f"count(*) FILTER (WHERE {c} IS NOT NULL AND TRY_CAST({c} AS DATE) IS NULL) FROM {view}"
    ).fetchone()
    return {"column": col, "min": r[0], "max": r[1], "unparseable": int(r[2])}


def fk_orphans(
    con: duckdb.DuckDBPyConnection,
    child: str,
    child_cols: list[str],
    parent: str,
    parent_cols: list[str],
    sample: int = 10,
) -> dict:
    """Child rows (with non-null keys) that have no parent row."""
    on = " AND ".join(f"c.{_q(a)} = p.{_q(b)}" for a, b in zip(child_cols, parent_cols))
    notnull = " AND ".join(f"c.{_q(a)} IS NOT NULL AND trim(c.{_q(a)}) <> ''" for a in child_cols)
    sel = ", ".join(f"c.{_q(a)}" for a in child_cols)
    base = f"FROM {child} c WHERE {notnull} AND NOT EXISTS (SELECT 1 FROM {parent} p WHERE {on})"
    rows = con.execute(f"SELECT count(*) {base}").fetchone()[0]
    distinct = con.execute(f"SELECT count(*) FROM (SELECT DISTINCT {sel} {base})").fetchone()[0]
    samples = con.execute(f"SELECT DISTINCT {sel} {base} LIMIT {int(sample)}").fetchall()
    total = con.execute(f"SELECT count(*) FROM {child} c WHERE {notnull}").fetchone()[0]
    return {
        "child": f"{child}({', '.join(child_cols)})",
        "parent": f"{parent}({', '.join(parent_cols)})",
        "child_rows_checked": int(total),
        "orphan_rows": int(rows),
        "distinct_orphan_keys": int(distinct),
        "samples": [list(s) for s in samples],
    }


def team_id_uniqueness(con: duckdb.DuckDBPyConnection) -> dict:
    """Is team_id a global key (one id -> one team name)? Needs views teams and mapping."""
    out: dict = {}
    for view in ("teams", "mapping"):
        r = con.execute(
            f"SELECT count(DISTINCT team_id), count(*) FILTER (WHERE n > 1) FROM ("
            f"SELECT team_id, count(DISTINCT team_name) n FROM {view} GROUP BY team_id)"
        ).fetchone()
        multi = con.execute(
            f"SELECT team_id, string_agg(DISTINCT team_name, ' | ' ORDER BY team_name) FROM {view} GROUP BY team_id "
            "HAVING count(DISTINCT team_name) > 1 ORDER BY TRY_CAST(team_id AS BIGINT) LIMIT 30"
        ).fetchall()
        out[view] = {
            "distinct_team_ids": int(r[0]),
            "team_ids_with_multiple_names": int(r[1]),
            "samples": [list(x) for x in multi],
        }
    name_multi = con.execute(
        "SELECT count(*) FROM (SELECT team_name FROM teams GROUP BY team_name "
        "HAVING count(DISTINCT team_id) > 1)"
    ).fetchone()[0]
    out["team_names_with_multiple_ids_in_teams"] = int(name_multi)
    out["team_id_is_globally_unique_key"] = (
        out["teams"]["team_ids_with_multiple_names"] == 0
        and out["mapping"]["team_ids_with_multiple_names"] == 0
    )
    return out


def classify_result(result: str | None) -> str:
    """Classify a matches.csv `result` string. Unrecognised text -> UNKNOWN (never guessed)."""
    if result is None or not str(result).strip():
        return "UNKNOWN"
    r = " ".join(str(result).lower().split())
    if "abandon" in r:
        return "ABANDONED"
    if "no result" in r:
        return "NO_RESULT"
    if "super over" in r or "one over eliminator" in r or "bowl out" in r:
        return "TIED_DECIDED_BY_TIEBREAK"
    if r == "match tied" or "tied" in r:
        return "TIED"
    if " won " in f" {r} " or r.startswith("won"):
        return "COMPLETED"
    return "UNKNOWN"


def reconcile_matches(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Every matches.csv match_id with no ball_by_ball rows, classified from actual fields.

    Needs views: matches, competitions, bbb, playing_eleven.
    """
    df = con.execute(
        """
        SELECT m.match_id, m.match_date, m.comp_id, c.comp_name, c.match_format, m.stage,
               m.home_team, m.away_team, m.result, m.win_team_id, m.knock_out,
               m.first_inn_revised_overs, m.second_inn_revised_overs, m.revised_target,
               (SELECT count(*) FROM playing_eleven p WHERE p.match_id = m.match_id) AS squad_rows,
               (SELECT count(*) FROM playing_eleven p WHERE p.match_id = m.match_id
                  AND lower(p.is_played) = 'true') AS played_rows
        FROM matches m LEFT JOIN competitions c ON c.comp_id = m.comp_id
        WHERE NOT EXISTS (SELECT 1 FROM bbb b WHERE b.match_id = m.match_id)
        ORDER BY TRY_CAST(m.match_id AS BIGINT)
        """
    ).df()
    df["result_class"] = df["result"].map(classify_result)
    df["has_winner_id"] = df["win_team_id"].notna() & (
        df["win_team_id"].astype(str).str.strip() != ""
    )

    def status(row: pd.Series) -> str:
        cls = row["result_class"]
        if cls == "COMPLETED":
            return "COMPLETED_NO_BALLS"
        return cls

    df["status"] = df.apply(status, axis=1)
    df["note"] = df.apply(
        lambda r: (
            "no deliveries in ball_by_ball; result text classified as "
            f"{r['result_class']}; squad_rows={r['squad_rows']}, played_rows={r['played_rows']}"
        ),
        axis=1,
    )
    return df


def bbb_matches_missing_from_matches(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        "SELECT DISTINCT match_id FROM bbb b WHERE NOT EXISTS "
        "(SELECT 1 FROM matches m WHERE m.match_id = b.match_id) ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]
