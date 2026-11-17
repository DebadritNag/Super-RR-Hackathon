"""Data-quality impact register for the outstanding Phase 2 rows and carried-over issues.

Read-only: rows come from `v_latest_data_quality`; counts are recomputed with SQL on the official
tables. Classifications and restrictions live in this register and in
`config/data_quality_restrictions_v1.json`; nothing is written to a database table, no record is
deleted and no match is excluded globally.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.analytics.reporting import PROXY_FIELDS, fmt, md_table
from app.validation.restrictions import load_restrictions, rule_by_id

BLOCKING = "BLOCKING"
NON_BLOCKING = "NON_BLOCKING_WITH_RESTRICTIONS"
INFORMATIONAL = "INFORMATIONAL"
CLASSIFICATIONS = (BLOCKING, NON_BLOCKING, INFORMATIONAL)


def _delivery_sql(where: str) -> str:
    """(count, delivery rows, matches, players) for a predicate on deliveries d."""
    return (
        f"WITH x AS (SELECT * FROM deliveries d WHERE {where}) "
        "SELECT (SELECT count(*) FROM x), (SELECT count(*) FROM x), "
        "(SELECT count(DISTINCT match_id) FROM x), "
        "(SELECT count(DISTINCT p) FROM (SELECT striker_id p FROM x UNION "
        "SELECT bowler_id FROM x))"
    )


_NOT_IN_SQUAD = (
    "EXISTS (SELECT 1 FROM match_squads s WHERE s.match_id = d.match_id) AND NOT EXISTS "
    "(SELECT 1 FROM match_squads s WHERE s.match_id = d.match_id AND s.player_id = d.{col})"
)

# ---------------------------------------------------------------------------- impact queries
SQL = {
    "reconcile_matches_without_deliveries": (
        "SELECT (SELECT count(*) FROM matches WHERE NOT has_deliveries), 0, "
        "(SELECT count(*) FROM matches WHERE NOT has_deliveries), 0"
    ),
    "result_status_distribution": ("SELECT (SELECT count(*) FROM matches), NULL, NULL, NULL"),
    "competition_type_distribution": ("SELECT (SELECT count(*) FROM matches), NULL, NULL, NULL"),
    "ipl_competitions_not_format_T20": (
        "SELECT (SELECT count(*) FROM competitions WHERE competition_type = 'IPL' "
        "AND match_format <> 'T20'), NULL, NULL, NULL"
    ),
    "comparison_columns_that_differ": (
        "SELECT (SELECT sum(rows_different) FROM ball_by_ball_comparison), NULL, "
        "(SELECT count(DISTINCT match_id) FROM ball_by_ball_comparison_detail), NULL"
    ),
    "open_playing_eleven_repeated_keys": (
        "SELECT (SELECT count(*) FROM match_squads WHERE duplicate_key_flag), NULL, "
        "(SELECT count(DISTINCT match_id) FROM match_squads WHERE duplicate_key_flag), "
        "(SELECT count(DISTINCT player_id) FROM match_squads WHERE duplicate_key_flag)"
    ),
    "open_matches_without_playing_eleven_rows": (
        "SELECT (SELECT count(*) FROM matches m WHERE NOT EXISTS "
        "(SELECT 1 FROM match_squads s WHERE s.match_id = m.match_id)), "
        "(SELECT count(*) FROM deliveries d WHERE NOT EXISTS "
        "(SELECT 1 FROM match_squads s WHERE s.match_id = d.match_id)), "
        "(SELECT count(*) FROM matches m WHERE NOT EXISTS "
        "(SELECT 1 FROM match_squads s WHERE s.match_id = m.match_id)), NULL"
    ),
    "open_playing_eleven_rows_without_mapping_row": (
        "SELECT (SELECT count(*) FROM match_squads WHERE NOT mapping_row_exists), NULL, "
        "(SELECT count(DISTINCT match_id) FROM match_squads WHERE NOT mapping_row_exists), "
        "(SELECT count(DISTINCT player_id) FROM match_squads WHERE NOT mapping_row_exists)"
    ),
    "open_delivery_striker_not_in_match_squad": _delivery_sql(
        _NOT_IN_SQUAD.format(col="striker_id")
    ),
    "open_delivery_bowler_not_in_match_squad": _delivery_sql(_NOT_IN_SQUAD.format(col="bowler_id")),
    "open_dismissed_player_without_wicket_flag": _delivery_sql(
        "dismissed_player_id IS NOT NULL AND NOT is_wicket"
    ),
    "open_wicket_without_dismissed_player": _delivery_sql(
        "is_wicket AND dismissed_player_id IS NULL"
    ),
    "open_extras_type_other_label_unverified": _delivery_sql("extras_type = 'other'"),
    "open_extras_type_Penalty_label_unverified": _delivery_sql("extras_type = 'Penalty'"),
    "open_extras_secondary_split_unverified": _delivery_sql("extras_secondary_runs > 0"),
    "open_innings_3_4_role_unverified": (
        "SELECT (SELECT count(*) FROM innings WHERE innings_number >= 3), "
        "(SELECT count(*) FROM deliveries WHERE innings_number >= 3), "
        "(SELECT count(DISTINCT match_id) FROM innings WHERE innings_number >= 3), "
        "(SELECT count(DISTINCT p) FROM (SELECT striker_id p FROM deliveries "
        "WHERE innings_number >= 3 UNION SELECT bowler_id FROM deliveries "
        "WHERE innings_number >= 3))"
    ),
    "open_man_of_the_match_zero_sentinel": (
        "SELECT (SELECT count(*) FROM matches WHERE man_of_the_match = 0), "
        "(SELECT count(*) FROM deliveries d JOIN matches m USING (match_id) "
        "WHERE m.man_of_the_match = 0), "
        "(SELECT count(*) FROM matches WHERE man_of_the_match = 0), NULL"
    ),
    "open_delivery_time_utc_suffix_vs_ist_column_name": _delivery_sql(
        "delivery_time_raw LIKE '%UTC%'"
    ),
    "open_delivery_time_midnight_rows": _delivery_sql("delivery_time_is_midnight"),
    "open_duplicate_player_names_with_different_ids": (
        "SELECT (SELECT count(*) FROM (SELECT player_name FROM players GROUP BY 1 "
        "HAVING count(*) > 1)), "
        "(SELECT count(*) FROM deliveries d WHERE d.striker_id IN (SELECT player_id FROM players "
        "WHERE shares_name_with_other_id) OR d.bowler_id IN (SELECT player_id FROM players "
        "WHERE shares_name_with_other_id)), "
        "(SELECT count(DISTINCT match_id) FROM deliveries d WHERE d.striker_id IN "
        "(SELECT player_id FROM players WHERE shares_name_with_other_id) OR d.bowler_id IN "
        "(SELECT player_id FROM players WHERE shares_name_with_other_id)), "
        "(SELECT count(*) FROM players WHERE shares_name_with_other_id)"
    ),
    "carried_no_result_or_abandoned_with_deliveries": (
        "SELECT (SELECT count(*) FROM matches WHERE has_deliveries AND result_status IN "
        "('NO_RESULT', 'ABANDONED')), "
        "(SELECT count(*) FROM deliveries d JOIN matches m USING (match_id) WHERE m.has_deliveries "
        "AND m.result_status IN ('NO_RESULT', 'ABANDONED')), "
        "(SELECT count(*) FROM matches WHERE has_deliveries AND result_status IN "
        "('NO_RESULT', 'ABANDONED')), NULL"
    ),
    "carried_dls_revised_targets": (
        "SELECT (SELECT count(*) FROM matches WHERE has_deliveries AND (revised_target IS NOT NULL "
        "OR first_inn_revised_overs IS NOT NULL OR second_inn_revised_overs IS NOT NULL)), "
        "(SELECT count(*) FROM deliveries d JOIN matches m USING (match_id) WHERE m.has_deliveries "
        "AND (m.revised_target IS NOT NULL OR m.first_inn_revised_overs IS NOT NULL "
        "OR m.second_inn_revised_overs IS NOT NULL)), "
        "(SELECT count(*) FROM matches WHERE has_deliveries AND (revised_target IS NOT NULL "
        "OR first_inn_revised_overs IS NOT NULL OR second_inn_revised_overs IS NOT NULL)), NULL"
    ),
    "carried_playing_xi_count_not_11": (
        "SELECT (SELECT count(*) FROM (SELECT match_id, team_id FROM match_squads "
        "WHERE is_played GROUP BY 1, 2 HAVING count(*) <> 11)), NULL, "
        "(SELECT count(DISTINCT match_id) FROM (SELECT match_id, team_id FROM match_squads "
        "WHERE is_played GROUP BY 1, 2 HAVING count(*) <> 11)), NULL"
    ),
    "carried_first_innings_batting_team_not_fk": (
        "SELECT (SELECT count(*) FROM matches m JOIN innings i ON i.match_id = m.match_id "
        "AND i.innings_number = 1 WHERE m.first_innings_batting_team_id IS NOT NULL AND "
        "(m.first_innings_batting_team_id <> i.batting_team_id OR m.first_innings_batting_team_id "
        "NOT IN (SELECT team_id FROM teams))), NULL, "
        "(SELECT count(*) FROM matches WHERE first_innings_batting_team_id IS NOT NULL), NULL"
    ),
}


def _spec(
    rule_id,
    cls,
    why,
    could_block,
    calculations,
    features,
    labels,
    models,
    handling,
    phase,
    resolvable,
    evidence,
    unit="rows",
):
    return {
        "rule_id": rule_id,
        "classification": cls,
        "justification": why,
        "what_it_could_block": could_block,
        "affects": {
            "calculations": calculations,
            "features": features,
            "labels": labels,
            "models": models,
        },
        "handling": handling,
        "implementing_phase": phase,
        "resolvable_with_evidence": {"possible": resolvable, "evidence_needed": evidence},
        "unit": unit,
    }


NB, INFO = NON_BLOCKING, INFORMATIONAL

SPECS: dict[str, dict[str, Any]] = {
    "open_innings_3_4_role_unverified": _spec(
        "RULE_INNINGS_3_4",
        NB,
        "Innings 3 and 4 are probably Super Overs but the official file does not say so. "
        "Regulation metrics are well defined without them, so nothing blocks.",
        "Treating them as Super Overs (or as regulation innings) without evidence.",
        ["any regulation-innings aggregate (runs, balls, wickets, required rate)"],
        ["phase and over-number features, chase state features"],
        ["pressure state labels, win/loss and chase outcomes"],
        ["any model trained on regulation-innings pressure"],
        "Keep the rows; exclude innings 3/4 from the listed metrics by rule. Cricsheet evidence "
        "(cricsheet_super_over_validation) is context only and does not relabel the data.",
        "Phase 3 (metric extraction)",
        True,
        "Official statement of the innings role, or a human decision accepting the Cricsheet match.",
        "innings",
    ),
    "open_extras_type_other_label_unverified": _spec(
        "RULE_EXTRAS_OTHER",
        NB,
        "The meaning of extras_type 'other' is not documented. It behaves like a no-ball in "
        "the Cricsheet comparison but this is not assumed. Proxy metrics can be run both ways.",
        "Any metric that needs a wide/no-ball/bye split for these rows.",
        ["balls faced, legal balls bowled, runs charged to the bowler"],
        ["extras-type features, no-ball/wide rates"],
        [],
        ["models using extras-type features"],
        "Keep the rows and the legal_ball_status already stored. Report affected metrics with and "
        "without these rows (sensitivity). Do not map 'other' to a named extras type.",
        "Phase 3",
        True,
        "Source documentation of the 'other' label from the data provider.",
    ),
    "open_extras_type_Penalty_label_unverified": _spec(
        "RULE_EXTRAS_PENALTY",
        NB,
        "{count} row(s); excluded from ball and charged-run counts by rule. Impact is negligible.",
        "Nothing at this size.",
        ["balls faced, legal balls, bowler runs charged"],
        ["extras-type features"],
        [],
        [],
        "Keep the row. Exclude it from the listed metrics; never assume it is a penalty-run "
        "type or a delivery.",
        "Phase 3",
        True,
        "Source documentation of the 'Penalty' label.",
    ),
    "open_extras_secondary_split_unverified": _spec(
        "RULE_EXTRAS_SECONDARY",
        NB,
        "{count} rows carry extras_secondary_runs; how these runs split with the primary extras is "
        "unverified. Secondary runs are not charged to the bowler in any proxy.",
        "Reconstructing innings totals or bowler runs conceded exactly.",
        ["bowler runs conceded, innings totals rebuilt from components"],
        ["extras-type features"],
        [],
        [],
        "Do not interpret extras_secondary_runs; use source_total_runs for innings totals.",
        "Phase 3",
        True,
        "Provider description of the extras_1/extras_2 split.",
    ),
    "open_playing_eleven_repeated_keys": _spec(
        "RULE_XI_DUPLICATES",
        NB,
        "{count} repeated squad rows in {matches} matches. They are kept, flagged with duplicate_key_flag. "
        "Ball-level metrics do not read the squad table.",
        "Team-composition or batting-order features for the affected matches.",
        ["squad size and composition counts"],
        ["team composition, batting order, squad membership"],
        [],
        ["models using team-composition features"],
        "Do not de-duplicate silently. Features from match_squads must carry the flag or skip "
        "flagged matches for that feature only.",
        "Phase 3 / 4",
        True,
        "Provider correction of the duplicated playing-XI rows.",
    ),
    "open_matches_without_playing_eleven_rows": _spec(
        "RULE_NO_XI_MATCHES",
        NB,
        "{count} matches have deliveries but no playing XI rows. Ball-level metrics are unaffected.",
        "Team-composition features for the affected matches.",
        ["team composition counts"],
        ["team composition, squad membership"],
        [],
        ["models using squad features"],
        "Keep the matches; leave squad features missing (never imputed) for them.",
        "Phase 3 / 4",
        True,
        "Playing XI rows for the affected matches from the provider.",
        "matches",
    ),
    "open_playing_eleven_rows_without_mapping_row": _spec(
        "RULE_NO_MAPPING_ROW",
        INFO,
        "{count} squad rows have no competition-team mapping row. The rows are kept and only affect "
        "mapping-based lookups, which no current metric uses.",
        "Nothing planned.",
        [],
        ["squad membership via the competition mapping"],
        [],
        [],
        "Keep the rows; use match_squads directly instead of the mapping table.",
        "Phase 4",
        True,
        "Mapping rows for the affected players.",
    ),
    "open_delivery_striker_not_in_match_squad": _spec(
        "RULE_STRIKER_NOT_IN_SQUAD",
        NB,
        "{count} delivery rows in {matches} matches have a striker who is absent from the "
        "match squad. The deliveries are real, only the squad list is incomplete.",
        "Inferring who played from the squad table.",
        [],
        ["squad membership and role inferred from squads"],
        [],
        [],
        "Keep the deliveries in ball-level metrics; never infer participation from the squad table.",
        "Phase 3 / 4",
        True,
        "Corrected playing-XI rows.",
    ),
    "open_delivery_bowler_not_in_match_squad": _spec(
        "RULE_BOWLER_NOT_IN_SQUAD",
        NB,
        "{count} delivery rows in {matches} matches have a bowler absent from the match squad. "
        "Same handling as the striker case.",
        "Inferring who played from the squad table.",
        [],
        ["squad membership and role inferred from squads"],
        [],
        [],
        "Keep the deliveries in ball-level metrics; never infer participation from the squad table.",
        "Phase 3 / 4",
        True,
        "Corrected playing-XI rows.",
    ),
    "open_dismissed_player_without_wicket_flag": _spec(
        "RULE_DISMISSED_NO_FLAG",
        NB,
        "{count} rows name a dismissed player but is_wicket is false. The flag and the player "
        "field disagree and the truth is unknown.",
        "Exact wicket counts for the affected innings.",
        ["wickets taken, dismissals, wickets in hand"],
        ["wickets-in-hand, wicket-event features"],
        ["wicket event labels"],
        ["models using wicket counts or wicket events"],
        "Proxy metrics count only rows with is_wicket true. Report a sensitivity run that counts "
        "these rows; do not edit the flag.",
        "Phase 3",
        True,
        "Provider correction or a rule that decides the flag from dismissal text.",
    ),
    "open_wicket_without_dismissed_player": _spec(
        "RULE_WICKET_NO_DISMISSED",
        NB,
        "{count} Retire Out row(s) have is_wicket true and no dismissed player. It cannot be attributed to "
        "a batter and Retire Out is not bowler-credited.",
        "Dismissal attribution for one row.",
        ["batter dismissal counts"],
        ["wicket-event features"],
        ["wicket event labels"],
        [],
        "Keep the row; exclude it from batter dismissal metrics; not credited to a bowler.",
        "Phase 3",
        True,
        "Dismissed player id from the provider.",
    ),
    "open_man_of_the_match_zero_sentinel": _spec(
        "RULE_MOM_SENTINEL",
        NB,
        "{count} matches use 0 as man_of_the_match, which is not a player id. Phase 3 does not need "
        "Man of the Match.",
        "Using Man of the Match as a label or target.",
        [],
        [],
        ["player-of-the-match label"],
        ["any model trained on that label"],
        "Do not use man_of_the_match as a label until the sentinel is decoded; do not join it "
        "to players.",
        "Not planned",
        True,
        "Provider documentation of the 0 value.",
        "matches",
    ),
    "open_delivery_time_utc_suffix_vs_ist_column_name": _spec(
        "RULE_UTC_SUFFIX",
        NB,
        "All delivery timestamps carry a UTC suffix although the column is named IST. The time "
        "zone is unverified; ordering within a match uses innings_ball_num instead.",
        "Any feature that depends on the clock time of a delivery.",
        [],
        ["time-of-day, day/night, elapsed-time features"],
        [],
        [],
        "Do not convert time zones; do not derive time features. Order deliveries by "
        "innings_ball_num.",
        "Not planned",
        True,
        "Provider statement of the time zone.",
    ),
    "open_delivery_time_midnight_rows": _spec(
        "RULE_MIDNIGHT_TIMES",
        INFO,
        "{count} rows have a 00:00:00 time part, probably a date only. No metric uses timestamps.",
        "Nothing planned.",
        [],
        ["time-of-day features"],
        [],
        [],
        "Keep the rows; ignore the time part.",
        "Not planned",
        True,
        "Provider statement on date-only timestamps.",
    ),
    "open_duplicate_player_names_with_different_ids": _spec(
        "RULE_DUPLICATE_NAMES",
        INFO,
        "{count} names map to {players} player ids. Everything joins on player_id, so no metric is affected "
        "as long as nobody joins on a name.",
        "Name-based joins (reports, Cricsheet linking by name).",
        [],
        ["player identity joins"],
        [],
        [],
        "Join on player_id only; do not merge or de-duplicate players.",
        "All phases",
        False,
        "Not resolvable from the data; ids are authoritative.",
        "player names",
    ),
    "open_cricsheet_innings_total_disagreements": _spec(
        "RULE_CRICSHEET_TOTALS",
        NB,
        "{count} innings in {matches} matches disagree with Cricsheet totals. The official data stays "
        "authoritative; the affected innings can perturb run-based metrics a little.",
        "Exact innings totals and chase targets for those innings.",
        ["innings totals, runs per ball, runs conceded"],
        ["chase target and required-rate features for the same matches"],
        ["chase outcome labels in those matches"],
        ["models using run-based features from those innings"],
        "Keep the rows (official file is authoritative). Run a sensitivity analysis that drops "
        "these innings for the listed metrics only.",
        "Phase 3",
        True,
        "Provider confirmation of which source total is right.",
        "innings",
    ),
    "open_matches_not_linkable_to_cricsheet": _spec(
        "RULE_UNLINKABLE_MATCHES",
        INFO,
        "Some official matches have no Cricsheet counterpart. Cricsheet is validation-only, so "
        "rankings never depend on the link.",
        "Nothing; it limits validation coverage only.",
        [],
        [],
        [],
        [],
        "Report validation coverage from the mapping counts; do not add Cricsheet-only matches.",
        "Not planned",
        False,
        "Not resolvable; Cricsheet simply lacks these matches.",
        "matches",
    ),
    "reconcile_matches_without_deliveries": _spec(
        "RULE_INFO_NO_DELIVERY_MATCHES",
        INFO,
        "{count} matches have no deliveries and all are explained (abandoned without a ball).",
        "Nothing.",
        ["match coverage denominators"],
        [],
        [],
        [],
        "Use matches with deliveries as the denominator for coverage statements.",
        "Phase 3",
        False,
        "Not applicable.",
        "matches",
    ),
    "result_status_distribution": _spec(
        "RULE_INFO_RESULT_STATUS",
        INFO,
        "Distribution of result statuses; informational.",
        "Nothing.",
        [],
        [],
        ["match outcome labels"],
        [],
        "Outcome labels must handle TIED, TIED_DECIDED_BY_TIEBREAK, NO_RESULT, ABANDONED "
        "explicitly.",
        "Phase 3",
        False,
        "Not applicable.",
        "matches",
    ),
    "competition_type_distribution": _spec(
        "RULE_INFO_COMP_TYPE",
        INFO,
        "Distribution of IPL, T20I and OTHER_T20 competitions; informational.",
        "Nothing.",
        [],
        ["format assignment"],
        [],
        [],
        "OTHER_T20 matches stay in the database and never enter IPL or T20I scores.",
        "Phase 3",
        False,
        "Not applicable.",
        "matches",
    ),
    "ipl_competitions_not_format_T20": _spec(
        "RULE_INFO_IPL_FORMAT",
        INFO,
        "No IPL competition has a non-T20 format; check passes with zero rows.",
        "Nothing.",
        [],
        ["format assignment"],
        [],
        [],
        "No action.",
        "Not planned",
        False,
        "Not applicable.",
        "competitions",
    ),
    "comparison_columns_that_differ": _spec(
        "RULE_INFO_EXTRAS1_COMPARISON",
        INFO,
        "The original and updated ball-by-ball files differ in extras1_runs and two name "
        "columns. The updated file is the approved authority; the original is kept for "
        "provenance.",
        "Nothing; the approved source decision covers it.",
        [],
        ["extras-type features"],
        [],
        [],
        "Use updated_ball_by_ball.csv only; keep the comparison tables as provenance.",
        "Not planned",
        False,
        "Not applicable.",
        "cell differences",
    ),
    "carried_no_result_or_abandoned_with_deliveries": _spec(
        "RULE_NO_RESULT_MATCHES",
        NB,
        "NO_RESULT and ABANDONED matches that still have deliveries have no valid outcome, but "
        "their balls are real. Only outcome-based labels are affected.",
        "Outcome-based labels for these matches.",
        [],
        ["win-probability and chase-completion features"],
        ["match outcome labels"],
        ["models trained on match outcomes"],
        "Keep the deliveries in ball-level metrics; exclude the matches from outcome labels only.",
        "Phase 3",
        False,
        "Not resolvable; there is no result.",
        "matches",
    ),
    "carried_dls_revised_targets": _spec(
        "RULE_DLS_TARGETS",
        NB,
        "{count} matches with revised overs or targets (DLS-style) change the chase target and balls "
        "available. Features must use the revised fields.",
        "Chase target and required-rate features that use the original 20 overs.",
        [],
        ["required run rate, balls remaining, target"],
        ["chase outcome labels"],
        ["models using chase features"],
        "Use revised_target and revised overs where present; never assume 20 overs for these "
        "matches.",
        "Phase 3",
        True,
        "None; the revised fields exist in the official matches table.",
        "matches",
    ),
    "carried_playing_xi_count_not_11": _spec(
        "RULE_XI_COUNT",
        NB,
        "{count} (match, team) pairs have a played-row count different from 11. A count of 12 "
        "is explained by impact substitutes in the IPL; other counts are anomalies. Ball-level metrics do not depend "
        "on it.",
        "Team-composition features.",
        [],
        ["team composition counts"],
        [],
        [],
        "Do not infer the XI from is_played counts; derive participation from deliveries.",
        "Phase 3 / 4",
        True,
        "Provider-verified playing XI.",
        "match-team pairs",
    ),
    "carried_first_innings_batting_team_not_fk": _spec(
        "RULE_FIRST_INNINGS_TEAM",
        INFO,
        "matches.first_innings_batting_team_id has no foreign key in the schema. The recount "
        "finds no orphan and no disagreement with innings 1.",
        "Nothing; a missing constraint, not bad data.",
        [],
        ["innings order"],
        [],
        [],
        "Use innings.batting_team_id for innings order.",
        "Not planned",
        False,
        "Not applicable.",
        "matches",
    ),
}

CARRIED = (
    (
        "carried_no_result_or_abandoned_with_deliveries",
        "RECONCILIATION",
        "Matches with result_status NO_RESULT or ABANDONED that still have delivery rows.",
    ),
    (
        "carried_dls_revised_targets",
        "CONSISTENCY",
        "Matches with a revised target or revised overs (rain-affected).",
    ),
    (
        "carried_playing_xi_count_not_11",
        "CONSISTENCY",
        "(match, team) pairs whose played-row count in the squad table is not 11.",
    ),
    (
        "carried_first_innings_batting_team_not_fk",
        "CONSISTENCY",
        "matches.first_innings_batting_team_id has no declared foreign key.",
    ),
)

UNMAPPED_SPEC = _spec(
    "",
    BLOCKING,
    "No impact assessment is defined for this data-quality row, so its effect is unknown.",
    "Any calculation until the row is assessed.",
    [],
    [],
    [],
    [],
    "Assess the row and add it to the register before using it.",
    "Phase 2.5",
    True,
    "An impact assessment for the new data-quality check.",
)


def _recount(db, sql: str | None) -> dict[str, Any]:
    if sql is None:
        return {"count": None, "delivery_rows": None, "matches": None, "players": None}
    row = db.query(sql)[0]
    to_int = lambda v: None if v is None else int(v)  # noqa: E731
    return {
        "count": to_int(row[0]),
        "delivery_rows": to_int(row[1]),
        "matches": to_int(row[2]),
        "players": to_int(row[3]),
    }


def _fill(text: str, recount: dict[str, Any]) -> str:
    """Insert recomputed counts into the prose so no number is typed by hand."""
    vals = {k: ("an unknown number of" if v is None else v) for k, v in recount.items()}
    return text.format(**vals)


def _share(num: int | None, den: int) -> float | None:
    return None if num is None or not den else num / den


def denominators(db) -> dict[str, int]:
    return {
        "deliveries": int(db.scalar("SELECT count(*) FROM deliveries")),
        "matches": int(db.scalar("SELECT count(*) FROM matches")),
        "matches_with_deliveries": int(
            db.scalar("SELECT count(*) FROM matches WHERE has_deliveries")
        ),
        "players": int(db.scalar("SELECT count(*) FROM players")),
    }


def load_phase1_mismatches(path: Path | None) -> list[dict[str, Any]]:
    """The ten Cricsheet total disagreements recorded by the Phase 1 audit (artifact, not raw)."""
    if path is None or not Path(path).exists():
        return []
    rep = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = rep.get("ball_by_ball_validation", {}).get("updated_file_total_formula_mismatches", [])
    return [
        {
            "match_id": int(r["match_id"]),
            "innings": int(r["innings"]),
            "official_rows": r.get("rows"),
            "cricsheet_deliveries": r.get("cs_deliveries"),
            "official_total_formula": (r.get("s_runs") or 0)
            + (r.get("s_e1") or 0)
            + (r.get("s_e2") or 0),
            "cricsheet_total": r.get("cs_total"),
        }
        for r in rows
    ]


def perturbation(db, innings: list[dict[str, Any]]) -> dict[str, Any]:
    """How much of each player's proxy sample sits in the disagreeing innings (read-only)."""
    if not innings:
        return {"innings": [], "batters": None, "bowlers": None}
    values = ", ".join(f"({i['match_id']}, {i['innings']})" for i in innings)
    aff = f"WITH aff(match_id, innings_number) AS (VALUES {values})"
    detail = db.query(
        f"{aff} SELECT a.match_id, a.innings_number, m.competition_type, "
        "count(d.match_id) FROM aff a JOIN matches m ON m.match_id = a.match_id "
        "LEFT JOIN deliveries d ON d.match_id = a.match_id AND d.innings_number = a.innings_number "
        "GROUP BY ALL ORDER BY 1, 2"
    )

    def shares(col: str) -> dict[str, Any]:
        rows = db.query(
            f"{aff} SELECT d.{col} AS p, "
            "count(*) FILTER (WHERE (d.match_id, d.innings_number) IN "
            "(SELECT match_id, innings_number FROM aff)) AS n_aff, count(*) AS n_tot "
            "FROM deliveries d WHERE d.innings_number IN (1, 2) GROUP BY 1 "
            "HAVING n_aff > 0 ORDER BY 1"
        )
        sh = sorted(r[1] / r[2] for r in rows)
        return {
            "players_touched": len(rows),
            "max_share_of_player_deliveries": max(sh) if sh else None,
            "median_share_of_player_deliveries": sh[len(sh) // 2] if sh else None,
            "players_with_share_at_least_0_25": sum(1 for s in sh if s >= 0.25),
        }

    return {
        "innings": [
            {
                "match_id": int(r[0]),
                "innings_number": int(r[1]),
                "competition_type": r[2],
                "official_delivery_rows": int(r[3]),
            }
            for r in detail
        ],
        "batters": shares("striker_id"),
        "bowlers": shares("bowler_id"),
        "metrics_that_could_be_perturbed": [
            "batter_runs_per_ball",
            "bowler_economy",
            "innings_total_runs",
            "chase_target_features",
        ],
    }


def _entry_from(
    issue_id: str,
    check_name: str,
    source: str,
    category: str,
    db_severity: str | None,
    db_status: str | None,
    db_affected: int | None,
    spec: dict[str, Any],
    recount: dict[str, Any],
    den: dict[str, int],
    cfg: dict[str, Any],
    note: str | None = None,
) -> dict[str, Any]:
    cls = spec["classification"]
    detail = None
    recomputed = recount["count"]
    agrees = None if (recomputed is None or db_affected is None) else recomputed == db_affected
    if agrees is False:
        cls = BLOCKING
        detail = (
            f"recomputed count {recomputed} differs from the stored data-quality row "
            f"({db_affected}); the register cannot be trusted until this is reconciled"
        )
    if spec["classification"] == BLOCKING and detail is None:
        detail = _fill(spec["justification"], recount)
    rule = rule_by_id(spec["rule_id"], cfg) if spec["rule_id"] else None
    restriction = (
        {
            "rule_id": rule["rule_id"],
            "applies_to_metrics": rule["applies_to_metrics"],
            "row_filter": rule["row_filter"],
            "effect": rule["effect"],
            "global_exclusion": False,
        }
        if rule
        else {
            "rule_id": None,
            "applies_to_metrics": [],
            "row_filter": "none defined",
            "effect": None,
            "global_exclusion": False,
        }
    )
    return {
        "issue_id": issue_id,
        "check_name": check_name,
        "source": source,
        "category": category,
        "db_severity": db_severity,
        "db_status": db_status,
        "db_affected_rows": db_affected,
        "unit": spec["unit"],
        "recomputed_count": recomputed,
        "recomputed_delivery_rows": recount["delivery_rows"],
        "recomputed_matches": recount["matches"],
        "recomputed_players": recount["players"],
        "count_agrees_with_db": agrees,
        "share_of_deliveries": _share(recount["delivery_rows"], den["deliveries"]),
        "share_of_matches": _share(recount["matches"], den["matches"]),
        "share_of_players": _share(recount["players"], den["players"]),
        "classification": cls,
        "justification": _fill(spec["justification"], recount),
        "what_it_could_block": spec["what_it_could_block"],
        "affects": spec["affects"],
        "restriction": restriction,
        "handling": spec["handling"],
        "implementing_phase": spec["implementing_phase"],
        "resolvable_with_evidence": spec["resolvable_with_evidence"],
        "blocking_detail": detail if cls == BLOCKING else None,
        "note": note,
    }


def build_register(
    db,
    restrictions_cfg: dict[str, Any] | None = None,
    phase1_overlap_report: Path | None = None,
) -> dict[str, Any]:
    """Register of every OPEN and INFO row of the latest run plus carried-over issues."""
    cfg = restrictions_cfg if restrictions_cfg is not None else load_restrictions()
    den = denominators(db)
    rows = db.query(
        "SELECT result_id, check_name, category, severity, status, affected_rows, observed "
        "FROM v_latest_data_quality WHERE status IN ('OPEN', 'INFO') "
        "ORDER BY CASE status WHEN 'OPEN' THEN 0 ELSE 1 END, result_id"
    )
    mismatches = load_phase1_mismatches(phase1_overlap_report)
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for n, (rid, check, cat, sev, status, affected, observed) in enumerate(rows, start=1):
        spec = SPECS.get(check, UNMAPPED_SPEC)
        note = None
        if check in SQL:
            recount = _recount(db, SQL[check])
        elif check == "open_cricsheet_innings_total_disagreements":
            recount = {"count": len(mismatches) or None, "delivery_rows": None,
                       "matches": len({m["match_id"] for m in mismatches}) or None, "players": None}  # fmt: skip
            note = "recounted from the Phase 1 audit artifact (Cricsheet is not loaded)"
        elif check == "open_matches_not_linkable_to_cricsheet":
            recount = _recount(db, None)
            note = "Cricsheet-derived; see super-over validation mapping counts"
        else:
            recount = _recount(db, None)
            note = None if check in SPECS else f"no impact assessment defined; stored: {observed}"
        entries.append(
            _entry_from(
                f"DQ-{n:03d}",
                check,
                "phase2_data_quality_table",
                cat,
                sev,
                status,
                None if affected is None else int(affected),
                spec,
                recount,
                den,
                cfg,
                note,
            )  # fmt: skip
        )
        seen.add(check)
    for check, cat, desc in CARRIED:
        if check in seen:
            continue
        entries.append(
            _entry_from(
                f"DQ-{len(entries) + 1:03d}",
                check,
                "carried_over_phase1",
                cat,
                None,
                None,
                None,
                SPECS[check],
                _recount(db, SQL[check]),
                den,
                cfg,
                desc,
            )  # fmt: skip
        )
    counts = {c: sum(1 for e in entries if e["classification"] == c) for c in CLASSIFICATIONS}
    return {
        "denominators": den,
        "entries": entries,
        "classification_counts": counts,
        "open_rows": sum(1 for e in entries if e["db_status"] == "OPEN"),
        "info_rows": sum(1 for e in entries if e["db_status"] == "INFO"),
        "carried_over_rows": sum(1 for e in entries if e["source"] == "carried_over_phase1"),
        "perturbation_cricsheet_total_innings": perturbation(
            db,
            [{"match_id": m["match_id"], "innings": m["innings"]} for m in mismatches],
        ),
        "cricsheet_total_disagreements": mismatches,
    }


def restriction_matrix(cfg: dict[str, Any]) -> dict[str, list[str]]:
    """metric -> rule ids (what Phase 3 must consult per metric)."""
    out: dict[str, list[str]] = {m: [] for m in cfg["metric_vocabulary"]}
    for r in cfg["restrictions"]:
        for m in r["applies_to_metrics"]:
            out[m].append(r["rule_id"])
    return out


def build_report(db, restrictions_cfg=None, phase1_overlap_report=None) -> dict[str, Any]:
    cfg = restrictions_cfg if restrictions_cfg is not None else load_restrictions()
    reg = build_register(db, cfg, phase1_overlap_report)
    return {
        **PROXY_FIELDS,
        "global_exclusion": False,
        "records_deleted": 0,
        "matches_excluded_globally": 0,
        "issue_register": reg,
        "restriction_matrix": restriction_matrix(cfg),
        "restrictions_config": {"version": cfg["version"], "rules": len(cfg["restrictions"])},
        "definitions": {
            BLOCKING: "Prevents a planned calculation, label or model from being trusted until "
            "resolved.",
            NON_BLOCKING: "Work can proceed; named metrics, features or labels carry a "
            "documented, scoped restriction.",
            INFORMATIONAL: "Context only; no metric needs a restriction beyond a note.",
        },
    }


# ---------------------------------------------------------------------------------- report


def render_report(rep: dict[str, Any]) -> str:
    reg = rep["issue_register"]
    L = ["# Data-quality impact report", "", "## 1. Interpretation and status", ""]
    L += [
        "- Read-only assessment of the open Phase 2 data-quality rows and carried-over issues. "
        "No record was deleted, no match is excluded globally and nothing was written to a "
        "database table.",
        f"- proxy_run: {fmt(rep['proxy_run'])}; pressure_status: {rep['pressure_status']}; "
        f"not_for_publication: {fmt(rep['not_for_publication'])}.",
        f"- Register size: {len(reg['entries'])} issues ({reg['open_rows']} OPEN rows, "
        f"{reg['info_rows']} INFO rows, {reg['carried_over_rows']} carried over). "
        + ", ".join(f"{k}: {v}" for k, v in reg["classification_counts"].items())
        + ".",
        "",
    ]
    for k, v in rep["definitions"].items():
        L.append(f"- {k}: {v}")
    L += ["", "## 2. Register", ""]
    L.append(
        md_table(
            ["id", "check", "class", "rows", "recomputed", "agrees", "rule"],
            [
                [
                    e["issue_id"],
                    e["check_name"],
                    e["classification"],
                    e["db_affected_rows"],
                    e["recomputed_count"],
                    e["count_agrees_with_db"],
                    e["restriction"]["rule_id"],
                ]
                for e in reg["entries"]
            ],
        )
    )
    L += ["## 3. Issue detail", ""]
    for e in reg["entries"]:
        r = e["restriction"]
        shares = ", ".join(
            f"{k.replace('share_of_', '')} {e[k] * 100:.2f}%"
            for k in ("share_of_deliveries", "share_of_matches", "share_of_players")
            if e[k] is not None
        )
        L += [
            f"### {e['issue_id']} {e['check_name']} ({e['classification']})",
            "",
            f"- Source: {e['source']}; stored rows: {fmt(e['db_affected_rows'])}; recomputed "
            f"{e['unit']}: {fmt(e['recomputed_count'])}; shares: {shares or 'not applicable'}.",
            f"- Why this class: {e['justification']}",
            f"- Could block: {e['what_it_could_block']}",
            "- Affects: "
            + "; ".join(f"{k}: {', '.join(v) or 'none'}" for k, v in e["affects"].items()),
            f"- Restriction {r['rule_id']}: metrics {', '.join(r['applies_to_metrics']) or 'none'}; "
            f"filter `{r['row_filter']}`; effect {r['effect']}; global exclusion: no.",
            f"- Handling: {e['handling']}",
            f"- Phase: {e['implementing_phase']}; resolvable with evidence: "
            f"{fmt(e['resolvable_with_evidence']['possible'])} "
            f"({e['resolvable_with_evidence']['evidence_needed']})",
        ]
        if e["blocking_detail"]:
            L.append(f"- BLOCKING: {e['blocking_detail']}")
        if e["note"]:
            L.append(f"- Note: {e['note']}")
        L.append("")
    p = reg["perturbation_cricsheet_total_innings"]
    L += ["## 4. Cricsheet total disagreements: perturbation", ""]
    if p["innings"]:
        L.append(
            md_table(
                ["match", "innings", "type", "official delivery rows"],
                [
                    [
                        str(i["match_id"]),
                        i["innings_number"],
                        i["competition_type"],
                        i["official_delivery_rows"],
                    ]
                    for i in p["innings"]
                ],
            )
        )
        for role in ("batters", "bowlers"):
            s = p[role]
            L.append(
                f"- {role}: {s['players_touched']} players touched; largest share of one player's "
                f"innings 1/2 deliveries inside these innings {fmt(s['max_share_of_player_deliveries'], 3)}; "
                f"median {fmt(s['median_share_of_player_deliveries'], 3)}; "
                f"{s['players_with_share_at_least_0_25']} players with a share of 25% or more."
            )
        L.append("")
    else:
        L += ["Phase 1 artifact not available; no perturbation computed.", ""]
    L += ["## 5. Restrictions per metric (for Phase 3)", ""]
    L.append(
        md_table(
            ["metric", "rules"],
            [[m, ", ".join(r) or "none"] for m, r in rep["restriction_matrix"].items()],
        )
    )
    pres = rep.get("preservation")
    if pres:
        L += [
            "## 6. Preservation",
            "",
            f"Official CSV hashes, official table hashes and Cricsheet manifests unchanged: "
            f"{fmt(pres['unchanged'])}.",
            "",
        ]
    return "\n".join(L)
