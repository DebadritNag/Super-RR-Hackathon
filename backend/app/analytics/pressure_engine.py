"""Pre-delivery match-state engine (Phase 3 prep, Stage 2). EXPLORATORY, not validated.

For each delivery the state is computed IMMEDIATELY BEFORE the delivery from strictly earlier
rows of the same innings, plus match context known before the delivery. The innings-2 target uses
innings 1, which is complete before innings 2 starts. Nothing here reads a result, a margin, a
later delivery, the innings total of the same innings or any Cricsheet value.

Column groups of the output (a feature function must only read the first four):
  lineage / context / state / dq      pre-delivery or fixed before the match
  post_*                              needs the finished innings; selects populations only
  out_*                               the outcome of the delivery itself
  den_*                               outcome-conditioned denominator flags and row-level anomaly flags
The mutation test asserts that changing row k's extras_type changes nothing outside out_*, den_*.

No database is written here (the exploratory store is written by app.services.pressure_service).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.analytics import cricket_calculations as cc
from app.analytics.phase_engine import phase_label, phase_rule
from app.core.config import BACKEND_ROOT
from app.core.database import connect

RULES_PATH = BACKEND_ROOT / "config" / "pressure_rules_v1.json"
STATUS_FIELDS = {
    "status": "EXPLORATORY_NOT_VALIDATED",
    "official_ranking": False,
    "not_for_publication": True,
}
IN_SCOPE_FORMATS = ("IPL", "T20I")
KEY = ["match_id", "innings_number", "innings_ball_num"]

DELIVERY_COLUMNS = [
    "match_id", "innings_number", "innings_ball_num", "overid", "over_ball_num",
    "batting_team_id", "bowling_team_id", "striker_id", "non_striker_id", "bowler_id",
    "batting_order", "is_four", "is_six", "is_wicket", "dismissal_type",
    "dismissed_player_id", "batter_runs", "extras_type", "extras_primary_runs",
    "extras_secondary_runs", "is_legal_ball", "extras_label_unverified",
]  # fmt: skip

MATCH_SQL = """
SELECT m.match_id, m.comp_id, m.match_date, m.stage, m.venue_id, m.knock_out,
       m.competition_type, m.first_inn_revised_overs, m.second_inn_revised_overs,
       m.revised_target, c.season AS season_source
FROM matches m LEFT JOIN competitions c USING (comp_id)
WHERE m.has_deliveries
"""


class StateEngineError(ValueError):
    """Raised when the data contradict a verified assumption (the build fails, never guesses)."""


def load_rules(path: Path | str = RULES_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_inputs(db_path: Path | str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read deliveries and match context from the official DuckDB, read-only."""
    db = connect(db_path, read_only=True)
    try:
        cols = ", ".join(f"d.{c}" for c in DELIVERY_COLUMNS)
        deliveries = db.execute(
            f"SELECT {cols} FROM deliveries d JOIN matches m USING (match_id) "
            "WHERE m.has_deliveries ORDER BY d.match_id, d.innings_number, d.innings_ball_num"
        ).df()
        matches = db.execute(MATCH_SQL).df()
    finally:
        db.close()
    return deliveries, matches


def season_label(competition_type: pd.Series, season_source: pd.Series, match_date: pd.Series):
    """IPL: the competition season (a year). T20I and OTHER_T20: calendar year of match_date."""
    year = pd.to_datetime(match_date).dt.year.astype("Int64").astype("string")
    return season_source.astype("string").where(competition_type == "IPL", year)


def _int(s: pd.Series) -> pd.Series:
    return s.astype("Int64")


def _check_inputs(d: pd.DataFrame) -> None:
    if d.duplicated(KEY).any():
        raise StateEngineError("duplicate (match_id, innings_number, innings_ball_num) key")
    for col in ("batter_runs", "extras_primary_runs", "extras_secondary_runs", "is_legal_ball",
                "is_wicket"):  # fmt: skip
        if d[col].isna().any():
            raise StateEngineError(f"{col} has NULL values; unknown values are never set to 0")


def _revised_limit(m: pd.DataFrame, unit: int = 6) -> pd.DataFrame:
    for col in ("first_inn_revised_overs", "second_inn_revised_overs"):
        v = m[col].dropna()
        if len(v) and not cc.is_multiple_of(v, unit):
            raise StateEngineError(f"{col} has values that are not whole overs in balls")
    return m


def compute_pre_delivery_state(
    deliveries: pd.DataFrame,
    matches: pd.DataFrame,
    rules: dict[str, Any] | None = None,
    cricsheet_total_innings: set[tuple[int, int]] | None = None,
) -> pd.DataFrame:
    """Return one row per delivery with the state immediately before it."""
    rules = rules or load_rules()
    eng = rules["engine"]
    default_limit = int(eng["default_innings_limit_balls"])
    wk_total = int(eng["wickets_total"])
    credited = tuple(eng["bowler_credited_dismissals"])
    charged_types = tuple(eng["bowler_charged_extras_types"])
    fractions = rules["parameters"]["phase_fractions"]["value"]
    reasons = rules["restricted_innings"]["reason_codes"]
    default_reason = rules["restricted_innings"]["default_reason_code"]
    regulation = tuple(rules["restricted_innings"]["regulation_innings"])

    m = _revised_limit(matches.copy())
    d = deliveries.copy()
    _check_inputs(d)
    d = d.sort_values(KEY, kind="mergesort").reset_index(drop=True)
    d = d.merge(m, on="match_id", how="left", validate="many_to_one")
    if d["competition_type"].isna().any():
        raise StateEngineError("deliveries without a match row")
    mid, inn = d["match_id"], d["innings_number"]
    g = [mid, inn]

    # ------------------------------------------------------------- row-level (outcome) helpers
    et = cc.normalise_extras_type(d["extras_type"])
    legal_inc = cc.legal_increment(d["is_legal_ball"], et)
    faced = cc.counts_as_ball_faced(d["striker_id"], et, inn)
    runs_row = d["batter_runs"] + d["extras_primary_runs"] + d["extras_secondary_runs"]
    is_wk = d["is_wicket"].astype(bool)
    dismissed = d["dismissed_player_id"].notna()
    wk_alt = (is_wk | dismissed).astype("int64")
    anomaly_row = (dismissed & ~is_wk).astype("int64")
    wk_i = is_wk.astype("int64")

    # ------------------------------------------------------------- strictly-earlier counters
    runs_b = cc.exclusive_cumsum(runs_row.astype("int64"), g)
    wk_b = cc.exclusive_cumsum(wk_i, g)
    wk_alt_b = cc.exclusive_cumsum(wk_alt, g)
    legal_b = cc.exclusive_cumsum(legal_inc, g)
    anomaly_b = cc.exclusive_cumsum(anomaly_row, g)
    wrem = wk_total - wk_b
    wrem_alt = wk_total - wk_alt_b

    # ------------------------------------------------------------- innings limit (balls)
    first_rev, second_rev = d["first_inn_revised_overs"], d["second_inn_revised_overs"]
    rev_target = d["revised_target"]
    limit = pd.Series(np.nan, index=d.index, dtype="float64")
    source = pd.Series(pd.NA, index=d.index, dtype="string")
    r1, r2 = inn == 1, inn == 2
    limit[r1] = np.where(first_rev[r1].notna(), first_rev[r1], default_limit)
    source[r1] = np.where(first_rev[r1].notna(), "REVISED_FIELD", "DEFAULT_120")
    own2 = second_rev[r2].notna()
    carried = ~own2 & first_rev[r2].notna() & rev_target[r2].isna()
    limit[r2] = np.where(own2, second_rev[r2], np.where(carried, first_rev[r2], default_limit))
    source[r2] = np.where(
        own2,
        "REVISED_FIELD",
        np.where(carried, "CARRIED_FROM_FIRST_INNINGS_UNVERIFIED", "DEFAULT_120"),
    )
    reg = inn.isin(regulation)
    limit[~reg] = np.nan
    source[~reg] = pd.NA
    brem = limit - legal_b
    if ((brem - legal_inc) < 0)[reg].any():
        raise StateEngineError("an innings has more legal balls than its limit")

    # ------------------------------------------------------------- target (innings 2 only)
    inn1_total = (
        runs_row.where(r1).groupby(mid).transform("sum").where(r1.groupby(mid).transform("any"))
    )
    inn1_legal = legal_inc.where(r1).groupby(mid).transform("sum")
    inn1_wkts = wk_i.where(r1).groupby(mid).transform("sum")
    has_inn1 = r1.groupby(mid).transform("any")
    plus1 = (inn1_total + 1).where(has_inn1)
    target = pd.Series(np.nan, index=d.index, dtype="float64")
    target[r2] = np.where(rev_target[r2].notna(), rev_target[r2], plus1[r2])
    target_source = pd.Series(pd.NA, index=d.index, dtype="string")
    target_source[r2] = np.where(
        rev_target[r2].notna(), "REVISED_TARGET",
        np.where(plus1[r2].notna(), "INNINGS1_TOTAL_PLUS_1", "NO_INNINGS_1_TARGET"),
    )  # fmt: skip
    first_limit = np.where(first_rev.notna(), first_rev, default_limit)
    target_basis_unverified = (
        r2 & has_inn1 & (inn1_wkts < wk_total) & (inn1_legal < first_limit)
        & first_rev.isna() & rev_target.isna()
    )  # fmt: skip

    # ------------------------------------------------------------- rates and chase state
    crr = cc.safe_rate_per_over(runs_b, legal_b).where(reg)
    req = (target - runs_b).where(r2)
    req_nonpos = (target.notna() & (req <= 0)).fillna(False)
    rrr = cc.required_run_rate(req, brem).where(r2)
    gap = rrr - crr
    surplus = cc.projected_surplus(crr, rrr, brem).where(r2)
    res_ratio = cc.resource_ratio(brem, wrem, limit).where(reg)
    phase = phase_label(legal_b, limit, fractions)

    # ------------------------------------------------------------- DLS state
    dls_flag = (r1 & first_rev.notna()) | (r2 & (second_rev.notna() | rev_target.notna()))
    dls_match = first_rev.notna() | second_rev.notna() | rev_target.notna()
    has_inn2 = r2.groupby(mid).transform("any")
    unstated = r2 & first_rev.notna() & second_rev.isna() & rev_target.isna() & has_inn2
    fields_complete = pd.Series(pd.NA, index=d.index, dtype="boolean")
    own_rev = np.where(r1, first_rev.notna(), second_rev.notna())
    fc = own_rev & (r1 | rev_target.notna())
    fields_complete[dls_flag] = fc[dls_flag]
    fields_complete[unstated] = False
    resource_status = pd.Series("NOT_APPLICABLE", index=d.index, dtype="string")
    resource_status[dls_flag | unstated] = "NOT_RECONSTRUCTED"

    # ------------------------------------------------------------- post-innings (selection only)
    tot_legal = legal_inc.groupby(g).transform("sum")
    tot_wk = wk_i.groupby(g).transform("sum")
    tot_runs = runs_row.groupby(g).transform("sum")
    chase_done = r2 & target.notna() & (tot_runs >= target)
    ended_short = dls_flag & reg & (tot_legal < limit) & (tot_wk < wk_total) & ~chase_done
    reliable = fields_complete.copy()
    reliable[dls_flag & ended_short] = False

    # ------------------------------------------------------------- batter and bowler before-state
    faced_runs = d["batter_runs"].astype("int64")
    gb = [mid, inn, d["striker_id"]]
    bat_faced_b = cc.exclusive_cumsum(faced, gb)
    bat_runs_b = cc.exclusive_cumsum(faced_runs, gb)
    bowler_rows = (et != "Penalty").astype("int64")
    charged = d["batter_runs"] + np.where(et.isin(charged_types), d["extras_primary_runs"], 0)
    charged = (charged * bowler_rows).astype("int64")
    cred_wk = (is_wk & d["dismissal_type"].isin(credited)).astype("int64")
    gw = [mid, inn, d["bowler_id"]]
    bowl_legal_b = cc.exclusive_cumsum(legal_inc, gw)
    bowl_deliv_b = cc.exclusive_cumsum(bowler_rows, gw)
    bowl_runs_b = cc.exclusive_cumsum(charged, gw)
    bowl_wk_b = cc.exclusive_cumsum(cred_wk, gw)

    # ------------------------------------------------------------- restrictions (masks only)
    restricted = ~reg
    code = pd.Series(pd.NA, index=d.index, dtype="string")
    confirmed = set(reasons["CONFIRMED_SUPER_OVER_BY_CRICSHEET"])
    code[restricted] = np.where(
        mid[restricted].isin(confirmed), "CONFIRMED_SUPER_OVER_BY_CRICSHEET", default_reason
    )
    in_scope = d["competition_type"].isin(IN_SCOPE_FORMATS)
    cs_pairs = cricsheet_total_innings or set()
    cs_flag = pd.Series(
        [(a, b) in cs_pairs for a, b in zip(mid.tolist(), inn.tolist(), strict=True)], index=d.index
    )

    out = pd.DataFrame(
        {
            "match_id": mid, "innings_number": inn, "innings_ball_num": d["innings_ball_num"],
            "match_date": d["match_date"], "competition_type": d["competition_type"],
            "season_label": season_label(d["competition_type"], d["season_source"], d["match_date"]),
            "season_source": d["season_source"], "venue_id": d["venue_id"], "stage": d["stage"],
            "knock_out": d["knock_out"],
            "batting_team_id": d["batting_team_id"], "bowling_team_id": d["bowling_team_id"],
            "striker_id": d["striker_id"], "non_striker_id": d["non_striker_id"],
            "bowler_id": d["bowler_id"], "striker_batting_order": d["batting_order"],
            "chase_flag": r2,
            "team_runs_before": runs_b, "team_wickets_before": wk_b,
            "team_wickets_alt_before": wk_alt_b, "wickets_remaining": wrem,
            "wickets_remaining_alt": wrem_alt, "legal_balls_bowled_before": legal_b,
            "innings_limit_balls": _int(limit), "limit_source": source,
            "legal_balls_remaining": _int(brem), "over_k": cc.over_index(legal_b).where(reg),
            "ball_in_over_k": cc.ball_in_over(legal_b).where(reg),
            "crr": crr, "innings_phase": phase, "phase_rule": phase_rule(limit),
            "target": _int(target), "target_source": target_source,
            "target_basis_unverified": target_basis_unverified,
            "runs_required": _int(req), "req_nonpositive_flag": req_nonpos, "rrr": rrr,
            "gap": gap, "projected_surplus": surplus, "resource_ratio": res_ratio,
            "resource_status": resource_status,
            "dls_flag": dls_flag, "dls_match_flag": dls_match, "innings_limit_unstated": unstated,
            "dls_fields_complete": fields_complete,
            "limit_applied_from_start_assumed": dls_flag | unstated,
            "dls_exclude_primary": dls_flag | unstated,
            "state_wicket_flag_disagreement": anomaly_b > 0,
            "batter_balls_faced_before": bat_faced_b, "batter_runs_before": bat_runs_b,
            "bowler_deliveries_before": bowl_deliv_b, "bowler_legal_balls_before": bowl_legal_b,
            "bowler_overs_completed_before": bowl_legal_b // 6,
            "bowler_runs_charged_before": bowl_runs_b, "bowler_wickets_credited_before": bowl_wk_b,
            "regulation_flag": reg, "restricted_innings_flag": restricted,
            "exclusion_reason_code": code,
            "exclusion_rule_id": pd.Series(np.where(restricted, "RULE_INNINGS_3_4", None), index=d.index, dtype="string"),
            "format_out_of_scope": ~in_scope,
            "regulation_pressure_eligible": reg & in_scope,
            "dq_cricsheet_total_disagreement_innings": cs_flag,
            "post_innings_legal_balls": tot_legal, "post_innings_wickets": tot_wk,
            "post_innings_ended_short_of_stated_limit": ended_short,
            "post_dls_state_reliable": reliable,
            "out_batter_runs": d["batter_runs"], "out_is_four": d["is_four"],
            "out_is_six": d["is_six"], "out_is_wicket": d["is_wicket"],
            "out_dismissal_type": d["dismissal_type"],
            "out_dismissed_player_id": d["dismissed_player_id"],
            "out_extras_type": d["extras_type"],
            "out_extras_primary_runs": d["extras_primary_runs"],
            "out_extras_secondary_runs": d["extras_secondary_runs"],
            "out_is_legal_ball": d["is_legal_ball"], "out_runs_row": runs_row,
            "den_legal_inc": legal_inc, "den_counts_as_ball_faced": faced,
            "den_bowler_counts_row": bowler_rows, "den_bowler_charged_runs": charged,
            "den_bowler_credited_wicket": cred_wk,
            "den_extras_label_unverified": et.isin(tuple(eng["unverified_extras_types"])),
            "den_extras_category_known": cc.extras_category_known(et),
            "den_extras_runs_with_none_type": (et == "None")
            & ((d["extras_primary_runs"] != 0) | (d["extras_secondary_runs"] != 0)),
            "den_wicket_flag_anomaly": dismissed & ~is_wk,
            "den_wicket_without_dismissed": is_wk & ~dismissed,
            "state_version": rules["state_version"], "config_version": rules["config_version"],
        }
    )  # fmt: skip
    for col in ("team_runs_before", "team_wickets_before", "team_wickets_alt_before",
                "wickets_remaining", "wickets_remaining_alt", "legal_balls_bowled_before",
                "over_k", "ball_in_over_k"):  # fmt: skip
        out[col] = _int(out[col])
    return out


def state_columns(state: pd.DataFrame) -> list[str]:
    """Columns that must not depend on the outcome of the delivery itself."""
    return [c for c in state.columns if not c.startswith(("out_", "den_"))]


def pre_delivery_columns(state: pd.DataFrame) -> list[str]:
    """State columns without post_* (which need the finished innings)."""
    return [c for c in state_columns(state) if not c.startswith("post_")]


def build_checks(state: pd.DataFrame, matches: pd.DataFrame) -> dict[str, Any]:
    """Counts the build reports and asserts (never assumed)."""
    reg = state[state["regulation_flag"]]
    inn_key = ["match_id", "innings_number"]
    innings = reg.drop_duplicates(inn_key)
    restricted = state[state["restricted_innings_flag"]]
    by_reason = {
        str(k): {
            "matches": sorted(int(x) for x in g["match_id"].unique()),
            "rows": int(len(g)),
        }
        for k, g in restricted.groupby("exclusion_reason_code")
    }
    chase = reg[reg["chase_flag"]]
    dls_inn = innings[innings["dls_flag"]]
    return {
        "rows": int(len(state)),
        "matches": int(state["match_id"].nunique()),
        "rows_by_innings": {str(k): int(v) for k, v in state["innings_number"].value_counts().sort_index().items()},
        "regulation_rows": int(len(reg)),
        "regulation_innings": int(len(innings)),
        "regulation_pressure_eligible_rows": int(state["regulation_pressure_eligible"].sum()),
        "format_out_of_scope_rows": int(state["format_out_of_scope"].sum()),
        "format_out_of_scope_matches": int(state.loc[state["format_out_of_scope"], "match_id"].nunique()),
        "restricted_rows": int(len(restricted)),
        "restricted_by_reason": by_reason,
        "rows_innings_limit_exceeded": 0,
        "req_nonpositive_rows": int(reg["req_nonpositive_flag"].sum()),
        "req_nonpositive_matches": sorted(int(x) for x in reg.loc[reg["req_nonpositive_flag"], "match_id"].unique()),
        "chase_rows_without_target": int(chase["target"].isna().sum()),
        "target_basis_unverified_innings": int(innings["target_basis_unverified"].sum()),
        "target_source_counts_innings": {
            str(k): int(v) for k, v in innings["target_source"].value_counts().items()
        },
        "crr_null_rows": int(reg["crr"].isna().sum()),
        "crr_null_rows_with_zero_legal_balls": int(
            (reg["crr"].isna() & (reg["legal_balls_bowled_before"] == 0)).sum()
        ),
        "rows_with_zero_legal_balls_before": int((reg["legal_balls_bowled_before"] == 0).sum()),
        "dls": {
            "matches_with_any_revised_field": int(matches[["first_inn_revised_overs", "second_inn_revised_overs", "revised_target"]].notna().any(axis=1).sum()),
            "first_inn_revised_overs_not_null": int(matches["first_inn_revised_overs"].notna().sum()),
            "second_inn_revised_overs_not_null": int(matches["second_inn_revised_overs"].notna().sum()),
            "revised_target_not_null": int(matches["revised_target"].notna().sum()),
            "dls_flag_innings_1": int((dls_inn["innings_number"] == 1).sum()),
            "dls_flag_innings_2": int((dls_inn["innings_number"] == 2).sum()),
            "innings_limit_unstated": int(innings["innings_limit_unstated"].sum()),
            "dls_exclude_primary_innings": int(innings["dls_exclude_primary"].sum()),
            "post_innings_ended_short_innings_1": int(
                (innings["post_innings_ended_short_of_stated_limit"] & (innings["innings_number"] == 1)).sum()
            ),
            "post_innings_ended_short_innings_2": int(
                (innings["post_innings_ended_short_of_stated_limit"] & (innings["innings_number"] == 2)).sum()
            ),
            "post_innings_ended_short_matches_innings_1": sorted(
                int(x) for x in innings.loc[
                    innings["post_innings_ended_short_of_stated_limit"] & (innings["innings_number"] == 1),
                    "match_id",
                ]
            ),
            "dls_state_reliable_true_innings": int((innings["post_dls_state_reliable"] == True).sum()),  # noqa: E712
            "dls_state_reliable_false_innings": int((innings["post_dls_state_reliable"] == False).sum()),  # noqa: E712
            "resource_status_not_reconstructed_rows": int((reg["resource_status"] == "NOT_RECONSTRUCTED").sum()),
            "distinct_limits_innings": {str(int(k)): int(v) for k, v in innings["innings_limit_balls"].value_counts().sort_index().items()},
        },
        "wicket_flag_disagreement": {
            "dismissed_without_flag_rows": int(state["den_wicket_flag_anomaly"].sum()),
            "wicket_without_dismissed_rows": int(state["den_wicket_without_dismissed"].sum()),
            "later_rows_in_affected_innings": int(state["state_wicket_flag_disagreement"].sum()),
        },
        "extras": {
            "type_counts": {str(k): int(v) for k, v in state["out_extras_type"].value_counts().items()},
            "unverified_label_rows": int(state["den_extras_label_unverified"].sum()),
            "unknown_category_rows": int((~state["den_extras_category_known"]).sum()),
            "none_type_with_runs_rows": int(state["den_extras_runs_with_none_type"].sum()),
            "legal_rows": int(state["den_legal_inc"].sum()),
        },
        "phase_rows_regulation": {str(k): int(v) for k, v in reg["innings_phase"].value_counts().items()},
        "dq_cricsheet_total_disagreement_innings_rows": int(state["dq_cricsheet_total_disagreement_innings"].sum()),
    }  # fmt: skip
