"""Deep inspection of the ball-by-ball files and validation against Cricsheet totals."""

from __future__ import annotations

import json

import duckdb
import pandas as pd

from app.data_pipeline.cricsheet_auditor import normalise_team

PROFILE_COLS = [
    "extras_type",
    "extras1_runs",
    "extras_2_runs",
    "runs",
    "is_wicket",
    "is_four",
    "is_six",
    "dismissal_type_id",
    "dismissal_type",
    "overid",
    "innings",
    "over_ball_num",
    "pace_or_spin",
    "over_or_around",
    "on_or_off",
    "batting_type",
]
KEY = ["match_id", "innings", "innings_ball_num", "overid", "over_ball_num"]
EXTRA_TYPES = ["wide", "Overstep", "byes", "legbyes", "other", "Penalty", "None"]


def profile_columns(con: duckdb.DuckDBPyConnection, view: str) -> dict:
    out: dict = {}
    for col in PROFILE_COLS:
        rows = con.execute(
            f'SELECT "{col}", count(*) n FROM {view} GROUP BY 1 ORDER BY TRY_CAST("{col}" AS DOUBLE), 1'
        ).fetchall()
        out[col] = [[r[0], int(r[1])] for r in rows[:60]]
        out[col + "__distinct"] = len(rows)
    r = con.execute(
        f"SELECT min(TRY_CAST(innings_ball_num AS INT)), max(TRY_CAST(innings_ball_num AS INT)), "
        f"min(TRY_CAST(over_ball_num AS INT)), max(TRY_CAST(over_ball_num AS INT)), "
        f"min(TRY_CAST(overid AS INT)), max(TRY_CAST(overid AS INT)) FROM {view}"
    ).fetchone()
    out["ranges"] = dict(
        zip(
            [
                "innings_ball_num_min",
                "innings_ball_num_max",
                "over_ball_num_min",
                "over_ball_num_max",
                "overid_min",
                "overid_max",
            ],
            r,
        )
    )
    out["wicket_without_dismissed_player_id"] = int(
        con.execute(
            f"SELECT count(*) FROM {view} WHERE is_wicket = 'true' AND dismissed_player_id IS NULL"
        ).fetchone()[0]
    )
    out["dismissed_player_id_without_wicket"] = int(
        con.execute(
            f"SELECT count(*) FROM {view} WHERE is_wicket <> 'true' AND dismissed_player_id IS NOT NULL"
        ).fetchone()[0]
    )
    out["wicket_rows_by_dismissal"] = [
        [r[0], r[1], int(r[2])]
        for r in con.execute(
            f"SELECT dismissal_type_id, dismissal_type, count(*) FROM {view} "
            "WHERE is_wicket = 'true' GROUP BY 1, 2 ORDER BY 3 DESC"
        ).fetchall()
    ]
    out["dismissed_is_striker_or_non_striker"] = [
        [r[0], int(r[1])]
        for r in con.execute(
            f"SELECT CASE WHEN dismissed_player_id = striker_id THEN 'striker' "
            f"WHEN dismissed_player_id = non_striker_id THEN 'non_striker' ELSE 'other' END, count(*) "
            f"FROM {view} WHERE is_wicket = 'true' AND dismissed_player_id IS NOT NULL GROUP BY 1"
        ).fetchall()
    ]
    return out


def extras_crosstab(con: duckdb.DuckDBPyConnection, view: str) -> pd.DataFrame:
    return con.execute(
        "SELECT * FROM (SELECT extras_type, extras1_runs, extras_2_runs, runs, count(*) AS n "
        f"FROM {view} GROUP BY ALL) ORDER BY extras_type, TRY_CAST(extras1_runs AS INT), "
        "TRY_CAST(extras_2_runs AS INT), TRY_CAST(runs AS INT)"
    ).df()


def ball_counter_behaviour(con: duckdb.DuckDBPyConnection, view: str) -> dict:
    """How innings_ball_num / over_ball_num / overid behave, incl. on wides/no-balls."""
    con.execute(
        f"CREATE OR REPLACE TEMP VIEW _t AS SELECT match_id, TRY_CAST(innings AS INT) inn, "
        f"TRY_CAST(innings_ball_num AS INT) ibn, TRY_CAST(overid AS INT) ov, "
        f"TRY_CAST(over_ball_num AS INT) obn, extras_type FROM {view}"
    )
    g = con.execute(
        "SELECT count(*), count(*) FILTER (WHERE mn = 1 AND mx = n AND d = n), "
        "count(*) FILTER (WHERE mn <> 1), count(*) FILTER (WHERE d < n), "
        "count(*) FILTER (WHERE mx > n) FROM (SELECT match_id, inn, min(ibn) mn, max(ibn) mx, "
        "count(*) n, count(DISTINCT ibn) d FROM _t GROUP BY 1, 2)"
    ).fetchone()
    out: dict = {
        "innings_groups": int(g[0]),
        "innings_ball_num_is_1_to_row_count_without_gaps_or_repeats": int(g[1]),
        "innings_starting_not_at_1": int(g[2]),
        "innings_with_repeated_ball_num": int(g[3]),
        "innings_with_gaps": int(g[4]),
    }
    out["rows_per_over_distribution"] = [
        [int(r[0]), int(r[1])]
        for r in con.execute(
            "SELECT n, count(*) FROM (SELECT match_id, inn, ov, count(*) n FROM _t GROUP BY 1,2,3) "
            "GROUP BY 1 ORDER BY 1"
        ).fetchall()
    ]
    out["over_ball_num_by_extras_type"] = [
        [r[0], int(r[1]), int(r[2]), int(r[3])]
        for r in con.execute(
            "SELECT extras_type, max(obn), min(obn), count(*) FROM _t GROUP BY 1 ORDER BY 4 DESC"
        ).fetchall()
    ]
    # Does over_ball_num count every row of the over (including wides) or legal balls only?
    out["overs_where_over_ball_num_is_1_to_rows"] = [
        int(x)
        for x in con.execute(
            "SELECT count(*) FILTER (WHERE mn = 1 AND mx = n AND d = n), count(*) FROM ("
            "SELECT match_id, inn, ov, min(obn) mn, max(obn) mx, count(*) n, "
            "count(DISTINCT obn) d FROM _t GROUP BY 1,2,3)"
        ).fetchone()
    ]
    out["max_overid_by_innings"] = [
        [int(r[0]), int(r[1])]
        for r in con.execute("SELECT inn, max(ov) FROM _t GROUP BY 1 ORDER BY 1").fetchall()
    ]
    out["innings_row_counts_by_innings_number"] = [
        [int(r[0]), int(r[1]), int(r[2])]
        for r in con.execute(
            "SELECT inn, count(DISTINCT match_id), count(*) FROM _t GROUP BY 1 ORDER BY 1"
        ).fetchall()
    ]
    con.execute("DROP VIEW _t")
    return out


def compare_ball_files(con: duckdb.DuckDBPyConnection, a: str, b: str) -> dict:
    """Compare two ball-by-ball views on the composite key."""
    ka = ", ".join(KEY)
    n_a = con.execute(f"SELECT count(*) FROM {a}").fetchone()[0]
    n_b = con.execute(f"SELECT count(*) FROM {b}").fetchone()[0]
    dup_a = con.execute(
        f"SELECT count(*) FROM (SELECT {ka} FROM {a} GROUP BY ALL HAVING count(*) > 1)"
    ).fetchone()[0]
    dup_b = con.execute(
        f"SELECT count(*) FROM (SELECT {ka} FROM {b} GROUP BY ALL HAVING count(*) > 1)"
    ).fetchone()[0]
    using = ", ".join(KEY)
    joined = con.execute(f"SELECT count(*) FROM {a} JOIN {b} USING ({using})").fetchone()[0]
    only_a = con.execute(
        f"SELECT count(*) FROM {a} x WHERE NOT EXISTS (SELECT 1 FROM {b} y WHERE "
        + " AND ".join(f"x.{k} = y.{k}" for k in KEY)
        + ")"
    ).fetchone()[0]
    only_b = con.execute(
        f"SELECT count(*) FROM {b} y WHERE NOT EXISTS (SELECT 1 FROM {a} x WHERE "
        + " AND ".join(f"x.{k} = y.{k}" for k in KEY)
        + ")"
    ).fetchone()[0]
    cols_a = [r[0] for r in con.execute(f"DESCRIBE {a}").fetchall()]
    cols_b = [r[0] for r in con.execute(f"DESCRIBE {b}").fetchall()]
    diffs = {}
    for col in cols_a:
        if col in KEY or col not in cols_b:
            continue
        n = con.execute(
            f"SELECT count(*) FROM {a} x JOIN {b} y USING ({using}) "
            f"WHERE x.{col} IS DISTINCT FROM y.{col}"
        ).fetchone()[0]
        if n:
            diffs[col] = int(n)
    any_diff = con.execute(
        f"SELECT count(*) FROM {a} x JOIN {b} y USING ({using}) WHERE "
        + " OR ".join(
            f"x.{c} IS DISTINCT FROM y.{c}" for c in cols_a if c not in KEY and c in cols_b
        )
    ).fetchone()[0]
    if only_a == 0 and only_b == 0 and n_a == n_b:
        verdict = "SAME_ROWS_SAME_KEYS_VALUES_DIFFER" if diffs else "IDENTICAL"
    elif only_a == 0 and only_b > 0:
        verdict = "B_IS_SUPERSET_OF_A"
    elif only_b == 0 and only_a > 0:
        verdict = "A_IS_SUPERSET_OF_B"
    else:
        verdict = "DIFFERENT_ROW_SETS"
    name_diffs = {}
    for col in ("striker_name", "non_striker_name"):
        if col in diffs:
            name_diffs[col] = con.execute(
                f"SELECT x.{col}, y.{col}, count(*) FROM {a} x JOIN {b} y USING ({using}) "
                f"WHERE x.{col} IS DISTINCT FROM y.{col} GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15"
            ).fetchall()
    return {
        "a_rows": int(n_a),
        "b_rows": int(n_b),
        "a_duplicate_key_groups": int(dup_a),
        "b_duplicate_key_groups": int(dup_b),
        "joined_rows": int(joined),
        "only_in_a": int(only_a),
        "only_in_b": int(only_b),
        "rows_with_any_differing_value": int(any_diff),
        "differing_rows_per_column": diffs,
        "name_difference_samples": [[list(x) for x in v] for v in name_diffs.values()],
        "name_difference_columns": list(name_diffs.keys()),
        "verdict": verdict,
    }


def csv_innings_aggregates(con: duckdb.DuckDBPyConnection, view: str) -> pd.DataFrame:
    """Per (match_id, innings) sums used to test run semantics and legal-ball rules."""
    parts = [
        "match_id",
        "TRY_CAST(innings AS INT) AS innings",
        "count(*) AS rows",
        "sum(TRY_CAST(runs AS INT)) AS s_runs",
        "sum(TRY_CAST(extras1_runs AS INT)) AS s_e1",
        "sum(TRY_CAST(extras_2_runs AS INT)) AS s_e2",
        "count(*) FILTER (WHERE is_wicket = 'true') AS wickets",
        "count(*) FILTER (WHERE extras_type NOT IN ('wide','Overstep')) AS legal_r1",
        "count(*) FILTER (WHERE extras_type NOT IN ('wide','Overstep','other')) AS legal_r2",
        "count(*) FILTER (WHERE extras_type <> 'wide') AS legal_r3",
    ]
    for i, t in enumerate(EXTRA_TYPES):
        parts += [
            f"count(*) FILTER (WHERE extras_type = '{t}') AS n_t{i}",
            f"coalesce(sum(TRY_CAST(extras1_runs AS INT)) FILTER (WHERE extras_type = '{t}'),0) AS e1_t{i}",
            f"coalesce(sum(TRY_CAST(extras_2_runs AS INT)) FILTER (WHERE extras_type = '{t}'),0) AS e2_t{i}",
            f"coalesce(sum(TRY_CAST(runs AS INT)) FILTER (WHERE extras_type = '{t}'),0) AS r_t{i}",
        ]
    return con.execute(
        f"SELECT {', '.join(parts)} FROM {view} GROUP BY match_id, TRY_CAST(innings AS INT)"
    ).df()


def link_matches_to_cricsheet(
    matches: pd.DataFrame, index: pd.DataFrame, ball_match_ids: set[str]
) -> pd.DataFrame:
    """Link official match_ids to Cricsheet ids by exact date + normalised team names.

    Only links that are one official match to one distinct Cricsheet id are accepted.
    """
    idx = index.drop_duplicates("match_id")
    by_key: dict[str, list[str]] = {}
    for key, mid in zip(idx["date"].astype(str) + "#" + idx["teams_key"], idx["match_id"]):
        by_key.setdefault(key, []).append(mid)
    m = matches.copy()
    m["key"] = [
        f"{d}#" + "|".join(sorted([normalise_team(a), normalise_team(b)]))
        for d, a, b in zip(m["match_date"], m["home_team"], m["away_team"])
    ]
    counts = m.groupby("key")["match_id"].transform("count")
    rows = []
    for mid, key, cnt in zip(m["match_id"], m["key"], counts):
        cands = by_key.get(key, [])
        if len(cands) == 1 and cnt == 1:
            status, cs = "LINKED", cands[0]
        elif not cands:
            status, cs = "NO_CRICSHEET_MATCH", None
        else:
            status, cs = "AMBIGUOUS", None
        rows.append(
            {
                "match_id": mid,
                "cricsheet_id": cs,
                "link_status": status,
                "has_ball_by_ball": mid in ball_match_ids,
            }
        )
    return pd.DataFrame(rows)


def _cs_innings_frame(index: pd.DataFrame, ids: set[str]) -> pd.DataFrame:
    rows = []
    sub = index.drop_duplicates("match_id")
    for mid, js in zip(sub["match_id"], sub["innings_json"]):
        if mid not in ids:
            continue
        for pos, inn in enumerate(json.loads(js), start=1):
            rows.append(
                {"cricsheet_id": mid, "innings": pos, **{f"cs_{k}": v for k, v in inn.items()}}
            )
    return pd.DataFrame(rows)


def validate_against_cricsheet(
    agg: pd.DataFrame, links: pd.DataFrame, index: pd.DataFrame
) -> pd.DataFrame:
    """Per-innings comparison between CSV aggregates and Cricsheet innings summaries."""
    linked = links[(links["link_status"] == "LINKED") & links["has_ball_by_ball"]]
    cs = _cs_innings_frame(index, set(linked["cricsheet_id"]))
    df = agg.merge(linked[["match_id", "cricsheet_id"]], on="match_id").merge(
        cs, on=["cricsheet_id", "innings"], how="outer", indicator=True
    )
    df = df[df["match_id"].notna()].copy()
    ti = {t: i for i, t in enumerate(EXTRA_TYPES)}
    wi, oi, bi, li, ot, pe = (
        ti["wide"],
        ti["Overstep"],
        ti["byes"],
        ti["legbyes"],
        ti["other"],
        ti["Penalty"],
    )
    f = df
    f["ok_rows_eq_deliveries"] = f["rows"] == f["cs_deliveries"]
    f["F1_sum_runs"] = f["s_runs"] == f["cs_total"]
    f["F2_runs_plus_e2"] = (f["s_runs"] + f["s_e2"]) == f["cs_total"]
    f["F3_runs_plus_e1_plus_e2"] = (f["s_runs"] + f["s_e1"] + f["s_e2"]) == f["cs_total"]
    f["F4_runs_plus_e1"] = (f["s_runs"] + f["s_e1"]) == f["cs_total"]
    f["ok_runs_eq_batter_runs"] = f["s_runs"] == f["cs_batter"]
    f["ok_e1_plus_e2_eq_extras"] = (f["s_e1"] + f["s_e2"]) == f["cs_extras"]
    f["ok_wicket_count"] = f["wickets"] == f["cs_wickets"]
    f["ok_legal_R1_not_wide_not_Overstep"] = f["legal_r1"] == f["cs_legal_balls"]
    f["ok_legal_R2_also_not_other"] = f["legal_r2"] == f["cs_legal_balls"]
    f["ok_legal_R3_not_wide_only"] = f["legal_r3"] == f["cs_legal_balls"]
    f["ok_e1_wide_eq_cs_wides"] = f[f"e1_t{wi}"] == f["cs_wides"]
    f["ok_e1_Overstep_eq_cs_noballs"] = f[f"e1_t{oi}"] == f["cs_noballs"]
    f["ok_e1_Overstep_plus_other_eq_cs_noballs"] = (f[f"e1_t{oi}"] + f[f"e1_t{ot}"]) == f[
        "cs_noballs"
    ]
    f["ok_e1_byes_eq_cs_byes"] = f[f"e1_t{bi}"] == f["cs_byes"]
    f["ok_e1_legbyes_eq_cs_legbyes"] = f[f"e1_t{li}"] == f["cs_legbyes"]
    f["ok_e1_Penalty_eq_cs_penalty"] = f[f"e1_t{pe}"] == f["cs_penalty"]
    f["ok_innings_present_both_sides"] = f["cs_total"].notna()
    drop = [c for c in f.columns if c.startswith(("n_t", "e1_t", "e2_t", "r_t"))]
    return f.drop(columns=drop + ["_merge"])


def summarise_validation(val: pd.DataFrame) -> dict:
    """Counts of innings (and matches) where each candidate rule agrees with Cricsheet."""
    v = val[val["ok_innings_present_both_sides"]]
    ok_cols = [
        c for c in v.columns if c.startswith(("F", "ok_")) and c != "ok_innings_present_both_sides"
    ]
    out = {
        "innings_compared": int(len(v)),
        "matches_compared": int(v["match_id"].nunique()),
        "innings_without_cricsheet_counterpart": int((~val["ok_innings_present_both_sides"]).sum()),
    }
    for c in ok_cols:
        per_match = v.groupby("match_id")[c].all()
        out[c] = {"innings_ok": int(v[c].sum()), "matches_all_innings_ok": int(per_match.sum())}
    return out
