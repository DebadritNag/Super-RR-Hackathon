"""Builders for the serving tables (descriptive player stats, classification tables).

Everything is derived from the exploratory analytical store and the official database opened
read-only. Only ``p4_`` tables are written, and only to the analytical store.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.phase4.classification import (
    CLASSIFICATION_VERSION,
    apply_overrides,
    build_classification,
    coverage,
    load_config,
    load_overrides,
    load_squad,
)
from app.phase4.store import write_p4_table

STATS_RESTRICTIONS = (
    "innings 1-2 only; IPL/T20I only; TRAIN+VALIDATION (PRE_TEST) matches only; "
    "no TEST outcomes; DLS rows are NOT excluded from these descriptive totals; "
    "all delivery rows preserved in the official database"
)

STATS_SQL = """
WITH d AS (
    SELECT s.*, p.period
    FROM exp_pre_delivery_state s
    JOIN p4_match_period p USING (match_id)
    WHERE s.competition_type IN ('IPL', 'T20I')
      AND s.innings_number IN (1, 2)
      AND s.format_out_of_scope = FALSE
      AND p.period <> 'TEST'
), bat AS (
    SELECT striker_id AS player_id, competition_type AS format,
           count(DISTINCT match_id) AS bat_matches,
           sum(den_counts_as_ball_faced) AS bat_balls,
           sum(out_batter_runs) AS bat_runs,
           sum(CASE WHEN out_is_four THEN 1 ELSE 0 END) AS bat_fours,
           sum(CASE WHEN out_is_six THEN 1 ELSE 0 END) AS bat_sixes,
           sum(CASE WHEN out_is_wicket AND out_dismissed_player_id = striker_id THEN 1 ELSE 0 END)
               AS bat_dismissals
    FROM d GROUP BY 1, 2
), bowl AS (
    SELECT bowler_id AS player_id, competition_type AS format,
           count(DISTINCT match_id) AS bowl_matches,
           sum(CASE WHEN out_is_legal_ball THEN 1 ELSE 0 END) AS bowl_balls,
           sum(den_bowler_charged_runs) AS bowl_runs,
           sum(den_bowler_credited_wicket) AS bowl_wickets,
           sum(CASE WHEN out_is_legal_ball AND out_runs_row = 0 THEN 1 ELSE 0 END) AS bowl_dots
    FROM d GROUP BY 1, 2
)
SELECT coalesce(b.player_id, w.player_id) AS player_id,
       coalesce(b.format, w.format) AS format,
       coalesce(bat_matches, 0) AS bat_matches, coalesce(bat_balls, 0) AS bat_balls,
       coalesce(bat_runs, 0) AS bat_runs, coalesce(bat_fours, 0) AS bat_fours,
       coalesce(bat_sixes, 0) AS bat_sixes, coalesce(bat_dismissals, 0) AS bat_dismissals,
       coalesce(bowl_matches, 0) AS bowl_matches, coalesce(bowl_balls, 0) AS bowl_balls,
       coalesce(bowl_runs, 0) AS bowl_runs, coalesce(bowl_wickets, 0) AS bowl_wickets,
       coalesce(bowl_dots, 0) AS bowl_dots
FROM bat b FULL OUTER JOIN bowl w ON b.player_id = w.player_id AND b.format = w.format
ORDER BY 1, 2
"""


def build_player_stats(store: Path | str, official_db: Path | str) -> pd.DataFrame:
    """Per player x format descriptive totals plus matches played (squad ``is_played``)."""
    e = duckdb.connect(str(store), read_only=True)
    try:
        stats = e.execute(STATS_SQL).df()
        periods = e.execute("SELECT match_id, period FROM p4_match_period").df()
    finally:
        e.close()
    o = duckdb.connect(str(official_db), read_only=True)
    try:
        played = o.execute(
            "SELECT DISTINCT s.player_id, s.match_id, m.competition_type AS format "
            "FROM match_squads s JOIN matches m USING (match_id) "
            "WHERE s.is_played AND m.competition_type IN ('IPL', 'T20I')"
        ).df()
    finally:
        o.close()
    played = played.merge(periods, on="match_id")
    played = played[played["period"] != "TEST"]
    mp = played.groupby(["player_id", "format"]).size().rename("matches_played").reset_index()
    out = stats.merge(mp, on=["player_id", "format"], how="outer").fillna(0)
    for c in out.columns:
        if c not in ("format",):
            out[c] = out[c].astype("int64")
    out["window"] = "PRE_TEST"
    out["restrictions"] = STATS_RESTRICTIONS
    return out.sort_values(["player_id", "format"]).reset_index(drop=True)


def load_classification_inputs(
    official_db: Path | str, cfg: dict[str, Any]
) -> dict[str, pd.DataFrame]:
    o = duckdb.connect(str(official_db), read_only=True)
    try:
        players = o.execute(
            "SELECT player_id, player_name, name_variants FROM players ORDER BY player_id"
        ).df()
        comp = o.execute(
            "SELECT comp_id FROM competitions WHERE competition_type = ? AND season = ?",
            [cfg["squad_competition"]["competition_type"], cfg["squad_competition"]["season"]],
        ).df()
        if len(comp) != 1:
            raise ValueError(f"expected exactly one squad competition, found {len(comp)}")
        mapping = o.execute(
            "SELECT DISTINCT player_id, team_id FROM player_competition_mapping WHERE comp_id = ?",
            [int(comp["comp_id"].iloc[0])],
        ).df()
        teams = o.execute("SELECT team_id, team_name FROM teams").df()
        t20i = o.execute(
            "SELECT DISTINCT s.player_id, s.match_id, t.team_name, m.match_date "
            "FROM match_squads s JOIN matches m USING (match_id) "
            "JOIN teams t ON t.team_id = s.team_id "
            "WHERE s.is_played AND m.competition_type = 'T20I'"
        ).df()
    finally:
        o.close()
    return {"players": players, "mapping": mapping, "teams": teams, "t20i": t20i}


def run_classification(
    official_db: Path | str,
    store: Path | str,
    squad_csv: Path | str,
    overrides_csv: Path | str,
    config_path: Path | str | None = None,
    scored_ids: list[int] | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path) if config_path else load_config()
    inp = load_classification_inputs(official_db, cfg)
    squad = load_squad(squad_csv)
    built = build_classification(
        inp["players"], squad, inp["mapping"], inp["t20i"], cfg, teams=inp["teams"]
    )
    overrides = load_overrides(overrides_csv, inp["players"]["player_id"])
    final = apply_overrides(built["classification"], overrides)
    cov = coverage(final, scored_ids)
    write_p4_table(built["classification"], "p4_player_classification_base", store)
    write_p4_table(final, "p4_player_classification", store)
    write_p4_table(built["evidence"], "p4_classification_evidence", store)
    write_p4_table(built["unresolved"], "p4_classification_unresolved", store)
    rows = pd.DataFrame(cov["combinations_all_players"]).assign(population="ALL_PLAYERS")
    if "combinations_scored_players" in cov:
        rows = pd.concat(
            [
                rows,
                pd.DataFrame(cov["combinations_scored_players"]).assign(
                    population="SCORED_PLAYERS"
                ),
            ]
        )
    write_p4_table(rows, "p4_classification_coverage", store)
    return {
        "config": cfg,
        "inputs": inp,
        "squad": squad,
        "overrides": overrides,
        "built": built,
        "final": final,
        "coverage": cov,
        "version": CLASSIFICATION_VERSION,
    }
