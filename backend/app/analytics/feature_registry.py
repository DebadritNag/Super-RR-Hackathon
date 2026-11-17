"""Feature registry for the exploratory pressure framework (Phase 3 prep). EXPLORATORY.

Every feature carries its availability (known before the delivery, partly known, outcome of the
delivery, or post-match), formula, source columns and the register metrics it feeds. The
restriction rules that apply to a feature are DERIVED from those metrics and the register, never
typed by hand. Nothing here is a validated pressure score.
"""

from __future__ import annotations

from typing import Any

PRE = "PRE_DELIVERY"
PARTIAL = "PARTIAL_PRE_DELIVERY"
OUTCOME = "OUTCOME_OF_DELIVERY"
POST_INNINGS = "POST_INNINGS"
POST_MATCH = "POST_MATCH"
DENOM = "OUTCOME_CONDITIONED_DENOMINATOR_FLAG"
AVAILABILITY = (PRE, PARTIAL, OUTCOME, DENOM, POST_INNINGS, POST_MATCH)

FEATURE_REGISTRY: list[dict[str, Any]] = []


def _f(name, group, availability, definition, formula, inputs, unit, metrics, use, leak, note=""):
    FEATURE_REGISTRY.append(
        {
            "name": name,
            "group": group,
            "availability": availability,
            "definition": definition,
            "formula": formula,
            "inputs": inputs,
            "unit": unit,
            "register_metrics": metrics,
            "allowed_use": use,
            "leakage_risk": leak,
            "handling_note": note,
            "status": "EXPLORATORY_NOT_VALIDATED",
        }
    )


_STATE = ["pressure_state_label"]
_TGT = ["chase_target_features", "pressure_state_label", "win_probability_features"]
_BAT = ["batter_pressure_sample", "batter_balls_faced"]
_BOWL = ["bowler_pressure_sample", "bowler_legal_balls"]
_ST = "state feature"
_CTX = "context"
_IN = ["deliveries (rows before this one in the same innings)"]

# ---- match state, counted from earlier rows only
_f(
    "team_runs_before",
    _ST,
    PRE,
    "Team runs before delivery k",
    "R_k = sum of total runs of rows < k",
    _IN,
    "runs",
    _STATE,
    "state, par, baseline cell",
    "none (exclusive cumulative sum)",
)
_f(
    "team_wickets_before",
    _ST,
    PRE,
    "Wickets fallen before delivery k (is_wicket flag)",
    "W_k = count(is_wicket) over rows < k",
    _IN,
    "wickets",
    _STATE,
    "state",
    "none",
    "Uses the is_wicket flag. Wicket-flag disagreements (RULE_DISMISSED_NO_FLAG) are "
    "reported through team_wickets_alt_before, not by dropping rows",
)
_f(
    "team_wickets_alt_before",
    _ST,
    PRE,
    "Wickets before k counting rows with a dismissed player",
    "W_alt_k = count(is_wicket OR dismissed_player_id notnull) over rows < k",
    _IN,
    "wickets",
    _STATE,
    "sensitivity only",
    "none",
)
_f(
    "wickets_remaining",
    _ST,
    PRE,
    "Wickets in hand",
    "Wrem_k = 10 - W_k",
    ["team_wickets_before"],
    "wickets",
    _STATE,
    "state, baseline cell",
    "none",
)
_f(
    "wickets_remaining_alt",
    _ST,
    PRE,
    "Wickets in hand under the alternative wicket count",
    "10 - W_alt_k",
    ["team_wickets_alt_before"],
    "wickets",
    _STATE,
    "sensitivity only",
    "none",
)
_f(
    "legal_balls_bowled_before",
    _ST,
    PRE,
    "Legal balls bowled before k",
    "B_k = sum(legal_inc) over rows < k; legal_inc = is_legal_ball AND extras_type <> Penalty",
    _IN,
    "balls",
    _STATE,
    "state",
    "none (denominator flag of EARLIER rows only)",
    "RULE_EXTRAS_PENALTY: Penalty never counts. Unknown extras keep their own category",
)
_f(
    "innings_limit_balls",
    _ST,
    PRE,
    "Balls available in the innings",
    "L = 120, or the revised limit (in balls) for DLS innings",
    ["matches.first_inn_revised_overs", "matches.second_inn_revised_overs"],
    "balls",
    ["chase_target_features", "pressure_state_label"],
    "state",
    "PARTIAL for revised limits: the announcement ball is unknown",
)
_f(
    "legal_balls_remaining",
    _ST,
    PRE,
    "Legal balls left",
    "Brem_k = L - B_k",
    ["innings_limit_balls", "legal_balls_bowled_before"],
    "balls",
    _STATE,
    "state",
    "none",
)
_f(
    "over_k",
    _ST,
    PRE,
    "Legal over index (1-based)",
    "floor(B_k / 6) + 1",
    ["legal_balls_bowled_before"],
    "over",
    _STATE,
    "state",
    "none",
    "Derived from legal balls, never from overid or over_ball_num",
)
_f(
    "ball_in_over_k",
    _ST,
    PRE,
    "Legal ball position inside the over",
    "B_k mod 6 + 1",
    ["legal_balls_bowled_before"],
    "ball",
    _STATE,
    "state",
    "none",
)
_f(
    "crr",
    _ST,
    PRE,
    "Current run rate per over",
    "6 * R_k / B_k (NULL when B_k = 0)",
    ["team_runs_before", "legal_balls_bowled_before"],
    "runs/over",
    _STATE,
    "state",
    "none",
)
_f(
    "innings_phase",
    _ST,
    PRE,
    "Powerplay / middle / death label",
    "from B_k and L under the phase rule in config/pressure_rules_v1.json",
    ["legal_balls_bowled_before", "innings_limit_balls"],
    "label",
    _STATE,
    "state, baseline cell",
    "none",
)
_f(
    "target",
    "chase",
    PRE,
    "Runs to win, innings 2",
    "T = innings-1 total + 1, or revised_target for DLS",
    ["innings 1 rows", "matches.revised_target"],
    "runs",
    _TGT,
    "state",
    "none for unrevised; PARTIAL for revised (final target, not target at ball k)",
)
_f(
    "runs_required",
    "chase",
    PRE,
    "Runs still needed",
    "Req_k = T - R_k",
    ["target", "team_runs_before"],
    "runs",
    _TGT,
    "state",
    "none",
)
_f(
    "req_nonpositive_flag",
    "chase",
    PRE,
    "Req_k <= 0 marker",
    "Req_k <= 0",
    ["runs_required"],
    "flag",
    _TGT,
    "population filter",
    "none",
    "RRR is NULL when this flag is true",
)
_f(
    "rrr",
    "chase",
    PRE,
    "Required run rate per over",
    "6 * Req_k / Brem_k (NULL if Brem_k = 0, no target or Req_k <= 0)",
    ["runs_required", "legal_balls_remaining"],
    "runs/over",
    _TGT,
    "state, pressure signal",
    "none for unrevised target",
)
_f(
    "gap",
    "chase",
    PRE,
    "Required minus current run rate",
    "RRR_k - CRR_k",
    ["rrr", "crr"],
    "runs/over",
    _TGT,
    "pressure signal",
    "none",
)
_f(
    "projected_surplus",
    "chase",
    PRE,
    "Projected finish at current rate minus target",
    "R_k + CRR_k * Brem_k / 6 - T",
    ["team_runs_before", "crr", "target"],
    "runs",
    _TGT,
    "pressure signal",
    "none",
)
_f(
    "resource_ratio",
    "chase",
    PRE,
    "Resources left: balls and wickets share",
    "resource definition in spec section 3",
    ["legal_balls_remaining", "wickets_remaining"],
    "ratio",
    _TGT,
    "pressure signal",
    "none",
)
_f(
    "chase_flag",
    _CTX,
    PRE,
    "Innings 2 of a regulation match",
    "innings_number = 2",
    ["deliveries.innings_number"],
    "flag",
    _STATE,
    "population",
    "none",
)
# ---- DLS and population flags
_f(
    "dls_flag",
    "dls",
    PRE,
    "Row belongs to an innings with a revised limit or target",
    "revised fields non-null for the innings",
    ["matches revised fields"],
    "flag",
    _TGT,
    "population",
    "PARTIAL: revision announcement ball unknown",
)
_f(
    "dls_match_flag",
    "dls",
    PRE,
    "Match has any revised field",
    "any of revised_target, first_inn_revised_overs, second_inn_revised_overs non-null",
    ["matches revised fields"],
    "flag",
    _TGT,
    "population",
    "none",
)
_f(
    "dls_fields_complete",
    "dls",
    PRE,
    "Revised target and both revised limits are stated",
    "all three revised fields non-null",
    ["matches revised fields"],
    "flag",
    _TGT,
    "population",
    "none",
)
_f(
    "innings_limit_unstated",
    "dls",
    PRE,
    "Revised innings without a stated limit",
    "revised match, limit NULL for this innings",
    ["matches revised fields"],
    "flag",
    _TGT,
    "population",
    "none",
)
_f(
    "limit_applied_from_start_assumed",
    "dls",
    PARTIAL,
    "Revised limit applied from ball 1",
    "assumption flag",
    ["innings_limit_balls"],
    "flag",
    _TGT,
    "population",
    "hindsight for rows before the interruption",
)
_f(
    "dls_exclude_primary",
    "dls",
    PRE,
    "Row left out of primary populations because the revised state is not reconstructable",
    "dls_flag AND NOT reliably reconstructed",
    ["dls_flag", "dls_fields_complete"],
    "flag",
    _TGT,
    "population filter",
    "none",
    "RULE_DLS_TARGETS: revised fields are required",
)
_f(
    "target_basis_unverified",
    "chase",
    PRE,
    "Innings-1 total basis unverified",
    "innings 1 incomplete or has revised fields",
    ["innings 1 rows"],
    "flag",
    _TGT,
    "population filter",
    "none",
)
_f(
    "state_wicket_flag_disagreement",
    "dq",
    PRE,
    "Wicket flag and dismissed-player disagree in earlier rows",
    "any earlier row with dismissed_player_id and NOT is_wicket",
    _IN,
    "flag",
    ["wicket_event_label", "batter_dismissal_rate"],
    "population filter",
    "none",
)
_f(
    "regulation_flag",
    "population",
    PRE,
    "Innings 1 or 2",
    "innings_number IN (1, 2)",
    ["innings_number"],
    "flag",
    ["pressure_state_label"],
    "population",
    "none",
)
_f(
    "restricted_innings_flag",
    "population",
    PRE,
    "Innings 3 or 4 (Super Over or unverified)",
    "innings_number IN (3, 4)",
    ["innings_number"],
    "flag",
    ["pressure_state_label", "batter_pressure_sample", "bowler_pressure_sample"],
    "mask",
    "none",
    "RULE_INNINGS_3_4: excluded from regulation-pressure metrics; source rows preserved",
)
_f(
    "exclusion_reason_code",
    "population",
    PRE,
    "Why a row is restricted",
    "CONFIRMED_SUPER_OVER_BY_CRICSHEET or UNVERIFIED_INNINGS_ROLE",
    ["restricted_innings_flag"],
    "code",
    ["pressure_state_label"],
    "report",
    "none",
)
_f(
    "exclusion_rule_id",
    "population",
    PRE,
    "Register rule behind the exclusion",
    "RULE_INNINGS_3_4 for restricted rows",
    ["restricted_innings_flag"],
    "code",
    ["pressure_state_label"],
    "report",
    "none",
)
_f(
    "format_out_of_scope",
    "population",
    PRE,
    "OTHER_T20 rows",
    "competition_type = OTHER_T20",
    ["competitions.competition_type"],
    "flag",
    ["format_assignment"],
    "population",
    "none",
)
_f(
    "regulation_pressure_eligible",
    "population",
    PRE,
    "Row may enter regulation-pressure metrics",
    "regulation_flag AND NOT restricted_innings_flag",
    ["regulation_flag"],
    "flag",
    ["pressure_state_label", "batter_pressure_sample", "bowler_pressure_sample"],
    "population",
    "none",
)
# ---- player context
_f(
    "batter_balls_faced_before",
    "player context",
    PRE,
    "Striker balls faced earlier in innings",
    "sum(counts_as_ball_faced) over earlier rows for the striker",
    _IN,
    "balls",
    _BAT,
    "context",
    "none (earlier rows only)",
    "RULE_EXTRAS_PENALTY: Penalty not a ball faced",
)
_f(
    "batter_runs_before",
    "player context",
    PRE,
    "Striker runs earlier in innings",
    "sum(batter_runs) over earlier rows for the striker",
    _IN,
    "runs",
    _BAT,
    "context",
    "none",
)
_f(
    "bowler_deliveries_before",
    "player context",
    PRE,
    "Bowler rows earlier in innings",
    "count of earlier rows by the bowler",
    _IN,
    "rows",
    _BOWL,
    "context",
    "none",
)
_f(
    "bowler_legal_balls_before",
    "player context",
    PRE,
    "Bowler legal balls earlier",
    "sum(legal_inc) over earlier rows by the bowler",
    _IN,
    "balls",
    _BOWL,
    "context",
    "none",
    "RULE_EXTRAS_OTHER / RULE_EXTRAS_PENALTY apply",
)
_f(
    "bowler_overs_completed_before",
    "player context",
    PRE,
    "Completed overs by the bowler",
    "floor(bowler_legal_balls_before / 6)",
    ["bowler_legal_balls_before"],
    "overs",
    _BOWL,
    "context",
    "none",
)
_f(
    "bowler_runs_charged_before",
    "player context",
    PRE,
    "Runs charged to the bowler earlier",
    "sum(charged runs) over earlier rows (batter_runs + wide/Overstep/other primary extras)",
    _IN,
    "runs",
    ["bowler_economy"],
    "context",
    "none",
    "extras_secondary_runs never interpreted (RULE_EXTRAS_SECONDARY)",
)
_f(
    "bowler_wickets_credited_before",
    "player context",
    PRE,
    "Bowler-credited wickets earlier",
    "count of earlier Caught/Bowled/LBW/Stump/Hit Wicket rows",
    _IN,
    "wickets",
    ["bowler_wicket_rate"],
    "context",
    "none",
)
_f(
    "striker_id",
    "player context",
    PRE,
    "Striker player_id",
    "deliveries.striker_id",
    ["deliveries"],
    "id",
    ["player_identity_join"],
    "context; joins on player_id only",
    "none",
    "RULE_DUPLICATE_NAMES: never joined on name",
)
_f(
    "non_striker_id",
    "player context",
    PRE,
    "Non-striker player_id",
    "deliveries.non_striker_id",
    ["deliveries"],
    "id",
    ["player_identity_join"],
    "context",
    "none",
)
_f(
    "bowler_id",
    "player context",
    PRE,
    "Bowler player_id",
    "deliveries.bowler_id",
    ["deliveries"],
    "id",
    ["player_identity_join"],
    "context",
    "none",
)
_f(
    "striker_batting_order",
    "player context",
    PRE,
    "Striker's batting position",
    "deliveries.batting_order for the striker",
    ["deliveries"],
    "position",
    ["batting_order_features"],
    "context",
    "none",
)
# ---- match context
for _n, _d in (
    ("competition_type", "IPL / T20I / OTHER_T20"),
    ("season_label", "Season key from competitions.season and match_date"),
    ("venue_id", "Venue id"),
    ("stage", "Match stage"),
    ("knock_out", "Knock-out flag"),
    ("batting_team_id", "Batting team id"),
    ("bowling_team_id", "Bowling team id"),
    ("match_date", "Match date"),
):
    _f(
        _n,
        "match context",
        PRE,
        _d,
        "fixed before the match",
        ["matches / competitions"],
        "context",
        ["format_assignment"] if _n == "competition_type" else [],
        "baseline cell, context",
        "none",
    )
# ---- signals (exploratory)
_P = "exploratory signal"
for _n, _d, _a, _fm in (
    (
        "par_runs_lomo",
        "Par score at this state, other matches (LOMO)",
        PARTIAL,
        "mean runs of comparable innings in cell, own match excluded",
    ),
    ("par_deviation_lomo", "Runs minus LOMO par", PARTIAL, "R_k - par_runs_lomo"),
    (
        "par_runs_prior",
        "Par from strictly earlier matches",
        PRE,
        "cell mean over matches dated before this match",
    ),
    ("par_deviation_prior", "Runs minus strictly-prior par", PRE, "R_k - par_runs_prior"),
    (
        "exp_remaining",
        "Expected remaining runs (LOMO)",
        PARTIAL,
        "cell mean of runs scored from this state, own match excluded",
    ),
    ("req_to_exp", "Required runs over expected remaining", PARTIAL, "Req_k / exp_remaining"),
    (
        "proj_total_gap_lomo",
        "Projected total minus par total",
        PARTIAL,
        "R_k + exp_remaining - par_total",
    ),
    ("bowl_signal_B", "Bowling pressure signal B", PARTIAL, "spec section 7.4"),
    ("bowl_rel_A", "Bowling relative signal A", PARTIAL, "spec section 7.4"),
    (
        "rank_bat_pressure_rel",
        "Within-cell percentile of batting pressure",
        PARTIAL,
        "rank of signal inside its cell, own match excluded",
    ),
    (
        "rank_bowl_rel_B",
        "Within-cell percentile of bowling signal B",
        PARTIAL,
        "rank of bowl_signal_B inside its cell",
    ),
):
    _f(
        _n,
        _P,
        _a,
        _d,
        _fm,
        ["state columns", "other matches"],
        "varies",
        ["pressure_state_label"],
        "descriptive only" if _a == PARTIAL else "state",
        "LOMO uses later matches: descriptive, not predictive" if _a == PARTIAL else "none",
    )
_f(
    "exp_cell_level_used",
    _P,
    PARTIAL,
    "Baseline fallback level used for exp_remaining",
    "level index 0..n",
    ["state columns"],
    "level",
    ["pressure_state_label"],
    "report",
    "none",
)
_f(
    "shrinkage_floor_hit",
    _P,
    PARTIAL,
    "Shrinkage floor reached",
    "flag",
    ["state columns"],
    "flag",
    ["pressure_state_label"],
    "report",
    "none",
)
_f(
    "wbin",
    _P,
    PARTIAL,
    "Merged wickets-remaining bin",
    "merge algorithm, spec section 8",
    ["wickets_remaining"],
    "label",
    ["pressure_state_label"],
    "descriptive only",
    "FULL_SAMPLE counts decide the merge",
)
_f(
    "bowl_B_early_flag",
    _P,
    PRE,
    "Early-innings flag for bowl_signal_B",
    "B_k < 12 legal balls",
    ["legal_balls_bowled_before"],
    "flag",
    ["pressure_state_label"],
    "population filter",
    "none",
)
# ---- outcomes of delivery k: labels, never state
_L = "outcome label"
for _n, _d, _m in (
    (
        "out_batter_runs",
        "Runs off the bat on delivery k",
        ["batter_runs_per_ball", "batter_strike_rate"],
    ),
    ("out_is_four", "Four on delivery k", ["batter_runs_per_ball"]),
    ("out_is_six", "Six on delivery k", ["batter_runs_per_ball"]),
    ("out_runs_row", "Total runs on delivery k", ["innings_total_runs", "bowler_economy"]),
    (
        "out_is_wicket",
        "Wicket flag on delivery k",
        ["wicket_event_label", "batter_dismissal_rate", "bowler_wicket_rate"],
    ),
    ("out_dismissal_type", "Dismissal type on delivery k", ["wicket_event_label"]),
    (
        "out_dismissed_player_id",
        "Dismissed player on delivery k",
        ["wicket_event_label", "batter_dismissal_rate"],
    ),
    (
        "out_extras_type",
        "Extras category on delivery k (other, Penalty, None kept separate)",
        ["extras_type_features"],
    ),
    (
        "out_extras_primary_runs",
        "Primary extras runs on delivery k",
        ["extras_type_features", "bowler_economy"],
    ),
    (
        "out_extras_secondary_runs",
        "Secondary extras runs on delivery k (not interpreted)",
        ["extras_type_features", "bowler_economy"],
    ),
    ("out_is_legal_ball", "Source legal-ball flag on delivery k", ["bowler_legal_balls"]),
):
    _f(
        _n,
        _L,
        OUTCOME,
        _d,
        "source column of the delivery being predicted",
        ["deliveries row k"],
        "varies",
        _m,
        "label only, never a state input",
        "forbidden in state (spec 5.4)",
    )
for _n, _d, _m in (
    ("den_legal_inc", "Legal ball increment of row k", ["bowler_legal_balls"]),
    ("den_counts_as_ball_faced", "Row k counts as ball faced", ["batter_balls_faced"]),
    ("den_bowler_counts_row", "Row k counts for bowler workload", ["bowler_legal_balls"]),
    ("den_bowler_charged_runs", "Runs charged to the bowler on row k", ["bowler_economy"]),
    ("den_bowler_credited_wicket", "Bowler-credited wicket on row k", ["bowler_wicket_rate"]),
    (
        "den_extras_label_unverified",
        "Row k has an unverified extras label",
        ["extras_type_features"],
    ),
    ("den_extras_category_known", "Row k extras category is a known one", ["extras_type_features"]),
    (
        "den_extras_runs_with_none_type",
        "Extras runs present but extras_type is None",
        ["extras_type_features", "innings_total_runs"],
    ),
    ("den_wicket_flag_anomaly", "Wicket flag anomaly on row k", ["wicket_event_label"]),
    (
        "den_wicket_without_dismissed",
        "is_wicket true without dismissed player",
        ["wicket_event_label", "batter_dismissal_rate"],
    ),
):
    _f(
        _n,
        "denominator flag",
        DENOM,
        _d,
        "depends on the outcome of row k",
        ["deliveries row k"],
        "flag",
        _m,
        "selects rows for rates; never enters a state, par or rank cell",
        "outcome-conditioned (spec 5.3)",
    )
# ---- post-innings and post-match
for _n, _d in (
    ("post_innings_legal_balls", "Legal balls of the whole innings"),
    ("post_innings_wickets", "Wickets of the whole innings"),
    ("post_innings_ended_short_of_stated_limit", "Innings ended short of limit"),
    ("post_dls_state_reliable", "Revised state reliable (diagnostic)"),
    (
        "dq_cricsheet_total_disagreement_innings",
        "Innings total disagrees with Cricsheet (mask only)",
    ),
):
    _f(
        _n,
        "post-innings",
        POST_INNINGS,
        _d,
        "aggregate over the full innings",
        ["deliveries"],
        "varies",
        ["innings_total_runs"],
        "diagnostic and masks only",
        "forbidden in state",
    )
for _n, _d in (
    ("win_team_id", "Winning team"),
    ("result", "Result text"),
    ("result_status", "Result status"),
    ("winning_margin", "Winning margin"),
    ("man_of_the_match", "Player of the match"),
):
    _f(
        _n,
        "post-match",
        POST_MATCH,
        _d,
        "matches table field",
        ["matches"],
        "varies",
        ["match_outcome_label"] if _n != "man_of_the_match" else ["player_match_of_match_label"],
        "never a feature",
        "forbidden (spec 5.4)",
        "RULE_MOM_SENTINEL for man_of_the_match = 0" if _n == "man_of_the_match" else "",
    )


def rules_for_feature(feature: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    """Rule ids whose applies_to_metrics intersect the feature's register metrics."""
    ms = set(feature["register_metrics"])
    return [r["rule_id"] for r in cfg["restrictions"] if ms & set(r["applies_to_metrics"])]


def build_dictionary(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for f in FEATURE_REGISTRY:
        rules = rules_for_feature(f, cfg)
        out.append(
            {
                **f,
                "pre_delivery": f["availability"] == PRE,
                "restriction_rules": rules,
                "restriction_effects": {
                    r["rule_id"]: r["effect"] for r in cfg["restrictions"] if r["rule_id"] in rules
                },
            }
        )
    return out
