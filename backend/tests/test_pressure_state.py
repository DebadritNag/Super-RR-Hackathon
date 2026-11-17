"""Pre-delivery match-state engine: hand-checkable synthetic innings plus real-data facts.

EXPLORATORY: nothing here validates a pressure score.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import pytest

from app.analytics import pressure_engine as pe
from app.analytics.phase_engine import phase_bounds, phase_label
from app.core.config import BACKEND_ROOT, get_settings
from tests.pressure_helpers import (
    deliveries,
    match,
    matches,
    number,
    row,
    rows_n,
    simple_two_innings,
)  # fmt: skip

RULES = pe.load_rules()


def state(d, m, cs=None):
    return pe.compute_pre_delivery_state(d, m, RULES, cricsheet_total_innings=cs)


def inn(s, n, match_id=1):
    return s[(s.match_id == match_id) & (s.innings_number == n)].reset_index(drop=True)


# ---------------------------------------------------------------- counters, legal balls, extras
def test_hand_checked_innings1_counters():
    d, m = simple_two_innings()
    s = inn(state(d, m), 1)
    assert s.legal_balls_bowled_before.tolist() == [0, 1, 1, 2, 3, 3, 4]
    assert s.team_runs_before.tolist() == [0, 4, 5, 11, 11, 14, 15]
    assert s.team_wickets_before.tolist() == [0, 0, 0, 0, 1, 1, 1]
    assert s.wickets_remaining.tolist() == [10, 10, 10, 10, 9, 9, 9]
    assert s.legal_balls_remaining.tolist() == [120, 119, 119, 118, 117, 117, 116]


def test_crr_is_null_not_zero_at_zero_legal_balls():
    d, m = simple_two_innings()
    s = inn(state(d, m), 1)
    assert np.isnan(s.crr.iloc[0])
    assert s.crr.iloc[1] == pytest.approx(24.0)  # 4 runs from 1 legal ball
    assert s.crr.iloc[6] == pytest.approx(15 / 4 * 6)


def test_first_ball_of_wide_has_zero_legal_balls_so_crr_stays_null():
    rows = number([row(extras="wide", prim=1), row(bat=1)])
    s = state(deliveries(rows), matches(match()))
    assert s.legal_balls_bowled_before.tolist() == [0, 0]
    assert s.crr.isna().all()


@pytest.mark.parametrize(
    ("extras", "legal", "faced", "bowler_counts"),
    [
        ("None", 1, 1, 1), ("wide", 0, 0, 1), ("Overstep", 0, 1, 1), ("other", 0, 1, 1),
        ("byes", 1, 1, 1), ("legbyes", 1, 1, 1), ("Penalty", 0, 0, 0),
    ],
)  # fmt: skip
def test_legal_ball_faced_and_bowler_flags_per_extras_type(extras, legal, faced, bowler_counts):
    legal_db = extras not in ("wide", "Overstep", "other")  # DB flag; Penalty is flagged legal
    rows = number([row(extras=extras, prim=1 if extras != "None" else 0, legal=legal_db)])
    s = state(deliveries(rows), matches(match()))
    assert int(s.den_legal_inc.iloc[0]) == legal
    assert int(s.den_counts_as_ball_faced.iloc[0]) == faced
    assert int(s.den_bowler_counts_row.iloc[0]) == bowler_counts


def test_penalty_is_zero_legal_balls_but_runs_count_for_the_team():
    rows = number([row(extras="Penalty", prim=5, legal=True), row(bat=1)])
    s = state(deliveries(rows), matches(match()))
    assert s.legal_balls_bowled_before.tolist() == [0, 0]
    assert s.team_runs_before.tolist() == [0, 5]
    assert bool(s.den_extras_label_unverified.iloc[0])


def test_other_is_a_separate_unverified_flag_not_merged_into_overstep():
    rows = number([row(extras="other", prim=1), row(extras="Overstep", prim=1)])
    s = state(deliveries(rows), matches(match()))
    assert s.den_extras_label_unverified.tolist() == [True, False]
    assert s.out_extras_type.tolist() == ["other", "Overstep"]
    assert s.den_legal_inc.tolist() == [0, 0]


def test_unknown_extras_category_is_preserved_and_runs_not_zeroed():
    rows = number([row(extras="Mystery", prim=2, legal=True), row(bat=1)])
    s = state(deliveries(rows), matches(match()))
    assert s.den_extras_category_known.tolist() == [False, True]
    assert s.out_extras_type.iloc[0] == "Mystery"
    assert s.team_runs_before.tolist() == [0, 2]
    assert s.legal_balls_bowled_before.tolist() == [0, 1]  # follows the DB legal flag, not a guess


def test_null_runs_are_rejected_rather_than_coerced_to_zero():
    rows = number([row(bat=1), row(bat=1)])
    d = deliveries(rows)
    d["extras_primary_runs"] = d["extras_primary_runs"].astype("float64")
    d.loc[1, "extras_primary_runs"] = np.nan
    with pytest.raises(pe.StateEngineError):
        state(d, matches(match()))


def test_none_type_with_runs_is_kept_in_the_total_and_flagged():
    rows = number([row(extras="None", sec=1), row(bat=0)])
    s = state(deliveries(rows), matches(match()))
    assert s.team_runs_before.tolist() == [0, 1]
    assert s.den_extras_runs_with_none_type.tolist() == [True, False]


def test_over_and_ball_in_over_use_legal_balls_not_row_counters():
    rows = [row(bat=0), row(extras="wide", prim=1)] + [row(bat=0) for _ in range(7)]
    s = state(deliveries(number(rows)), matches(match()))
    assert s.legal_balls_bowled_before.tolist() == [0, 1, 1, 2, 3, 4, 5, 6, 7]
    assert s.over_k.tolist() == [1, 1, 1, 1, 1, 1, 1, 2, 2]
    assert s.ball_in_over_k.tolist() == [1, 2, 2, 3, 4, 5, 6, 1, 2]


# ---------------------------------------------------------------- wickets
def test_wickets_remaining_and_wicket_flag_disagreement_sensitivity():
    rows = number([
        row(bat=0), row(bat=0, dismissed=11),  # dismissed id but is_wicket false
        row(bat=0), row(wicket=True, dtype="Bowled", dismissed=12), row(bat=0),
    ])  # fmt: skip
    s = state(deliveries(rows), matches(match()))
    assert s.wickets_remaining.tolist() == [10, 10, 10, 10, 9]
    assert s.wickets_remaining_alt.tolist() == [10, 10, 9, 9, 8]
    assert s.state_wicket_flag_disagreement.tolist() == [False, False, True, True, True]
    assert s.den_wicket_flag_anomaly.tolist() == [False, True, False, False, False]


def test_wicket_without_dismissed_player_still_counts_for_the_team_and_is_flagged():
    rows = number([row(wicket=True, dtype="Retire Out", dismissed=None), row(bat=0)])
    s = state(deliveries(rows), matches(match()))
    assert s.wickets_remaining.tolist() == [10, 9]
    assert s.den_wicket_without_dismissed.tolist() == [True, False]


# ---------------------------------------------------------------- target, runs required, RRR
def test_innings1_has_no_target_and_no_required_rate():
    d, m = simple_two_innings()
    s = inn(state(d, m), 1)
    assert s.target.isna().all() and s.runs_required.isna().all() and s.rrr.isna().all()
    assert not s.chase_flag.any()


def test_chase_target_runs_required_and_rrr():
    d, m = simple_two_innings()
    s = inn(state(d, m), 2)
    assert s.target.tolist() == [16] * 6  # innings-1 total 15 + 1
    assert (s.target_source == "INNINGS1_TOTAL_PLUS_1").all()
    assert s.team_runs_before.tolist() == [0, 1, 1, 5, 5, 7]
    assert s.runs_required.tolist() == [16, 15, 15, 11, 11, 9]
    assert s.legal_balls_remaining.tolist() == [120, 119, 118, 117, 116, 115]
    assert s.rrr.iloc[0] == pytest.approx(16 / 120 * 6)
    assert s.rrr.iloc[3] == pytest.approx(11 / 117 * 6)
    assert s.gap.iloc[3] == pytest.approx(11 / 117 * 6 - 5 / 3 * 6)
    assert s.projected_surplus.iloc[3] == pytest.approx((5 / 3 * 6 - 11 / 117 * 6) * 117 / 6)
    assert s.resource_ratio.iloc[0] == pytest.approx(1.0)
    assert s.chase_flag.all()


def test_runs_required_nonpositive_gives_null_rrr_and_a_flag():
    inn1 = number([row(bat=1), row(bat=0)])  # total 1, target 2
    inn2 = number([row(bat=1), row(bat=1), row(bat=1), row(bat=0)], innings=2)
    s = inn(state(deliveries(inn1 + inn2), matches(match())), 2)
    assert s.runs_required.tolist() == [2, 1, 0, -1]
    assert s.req_nonpositive_flag.tolist() == [False, False, True, True]
    assert s.rrr.iloc[:2].notna().all() and s.rrr.iloc[2:].isna().all()


def test_innings2_without_innings1_has_no_target():
    inn2 = number([row(bat=1), row(bat=1)], innings=2)
    s = state(deliveries(inn2), matches(match()))
    assert s.target.isna().all() and s.rrr.isna().all()
    assert (s.target_source == "NO_INNINGS_1_TARGET").all()


def test_target_basis_unverified_flags_incomplete_innings1_without_revision():
    inn1 = number(rows_n(6, bat=1))  # 6 legal balls, 0 wickets, no revised field
    inn2 = number(rows_n(3, bat=1), innings=2)
    s = state(deliveries(inn1 + inn2), matches(match()))
    assert inn(s, 2).target_basis_unverified.all()
    assert not inn(s, 1).target_basis_unverified.any()


def test_target_basis_is_verified_when_innings1_completes_120_balls():
    inn1 = number(rows_n(120, bat=1))
    inn2 = number(rows_n(3, bat=1), innings=2)
    s = inn(state(deliveries(inn1 + inn2), matches(match())), 2)
    assert not s.target_basis_unverified.any() and (s.target == 121).all()


# ---------------------------------------------------------------- DLS and revised limits
def _dls_inputs(first=60.0, second=48.0, target=40.0):
    inn1 = number(rows_n(60, bat=1))
    inn2 = number(rows_n(20, bat=1), innings=2)
    return deliveries(inn1 + inn2), matches(match(first=first, second=second, target=target))


def test_dls_revised_limits_target_and_resource_status():
    d, m = _dls_inputs()
    s = state(d, m)
    a, b = inn(s, 1), inn(s, 2)
    assert (a.innings_limit_balls == 60).all() and (b.innings_limit_balls == 48).all()
    assert (b.target == 40).all() and (b.target_source == "REVISED_TARGET").all()
    assert a.legal_balls_remaining.iloc[0] == 60 and b.legal_balls_remaining.iloc[0] == 48
    assert a.dls_flag.all() and b.dls_flag.all() and a.dls_match_flag.all()
    assert (a.resource_status == "NOT_RECONSTRUCTED").all()
    assert (b.resource_status == "NOT_RECONSTRUCTED").all()
    assert a.limit_applied_from_start_assumed.all() and b.dls_exclude_primary.all()
    assert b.rrr.iloc[0] == pytest.approx(40 / 48 * 6)


def test_revised_target_differs_from_innings1_total_plus_one_and_is_used():
    d, m = _dls_inputs(target=45.0)
    s = inn(state(d, m), 2)
    assert (s.target == 45).all()  # innings-1 total + 1 would be 61


def test_non_dls_match_has_no_dls_state_and_resource_not_applicable():
    d, m = simple_two_innings()
    s = state(d, m)
    assert not s.dls_flag.any() and not s.dls_match_flag.any() and not s.dls_exclude_primary.any()
    assert (s.resource_status == "NOT_APPLICABLE").all()
    assert (s.phase_rule == "FULL_120").all()
    assert s.post_dls_state_reliable.isna().all()


def test_innings_limit_unstated_carries_first_innings_limit_and_is_unreliable():
    inn1 = number(rows_n(60, bat=1))
    inn2 = number(rows_n(5, bat=1), innings=2)
    s = inn(state(deliveries(inn1 + inn2), matches(match(first=60.0))), 2)
    assert (s.innings_limit_balls == 60).all()
    assert (s.limit_source == "CARRIED_FROM_FIRST_INNINGS_UNVERIFIED").all()
    assert s.innings_limit_unstated.all() and s.dls_exclude_primary.all()
    assert not s.dls_flag.any()
    assert (s.post_dls_state_reliable == False).all()  # noqa: E712


def test_innings_ended_short_of_stated_limit_makes_dls_state_unreliable():
    inn1 = number(rows_n(40, bat=1))  # limit 60, 40 legal balls, no all-out
    inn2 = number(rows_n(41, bat=1), innings=2)  # reaches target 41 -> chase done, not short
    s = state(deliveries(inn1 + inn2), matches(match(first=60.0, second=60.0, target=41.0)))
    a, b = inn(s, 1), inn(s, 2)
    assert a.post_innings_ended_short_of_stated_limit.all()
    assert (a.post_dls_state_reliable == False).all()  # noqa: E712
    assert not b.post_innings_ended_short_of_stated_limit.any()
    assert (b.post_dls_state_reliable == True).all()  # noqa: E712


def test_all_out_innings_is_not_ended_short():
    rows = [row(bat=0, wicket=True, dtype="Bowled", dismissed=11) for _ in range(10)]
    s = state(deliveries(number(rows)), matches(match(first=60.0)))
    assert not s.post_innings_ended_short_of_stated_limit.any()
    assert (s.post_dls_state_reliable == True).all()  # noqa: E712


def test_revised_overs_must_be_whole_overs_in_balls():
    rows = number([row(bat=1)])
    with pytest.raises(pe.StateEngineError):
        state(deliveries(rows), matches(match(first=7.0)))


def test_more_legal_balls_than_the_limit_fails_the_build():
    rows = number(rows_n(7, bat=1))
    with pytest.raises(pe.StateEngineError):
        state(deliveries(rows), matches(match(first=6.0)))


# ---------------------------------------------------------------- phases
SPEC_PHASE_TABLE = {  # L: (pp_end, death_start) from the specification section 7.6
    30: (9, 23), 42: (12, 32), 48: (14, 36), 54: (16, 41), 60: (18, 45), 66: (19, 50),
    72: (21, 54), 78: (23, 59), 84: (25, 63), 90: (27, 68), 102: (30, 77), 108: (32, 81),
    114: (34, 86), 120: (36, 90),
}  # fmt: skip


@pytest.mark.parametrize(("limit", "expected"), sorted(SPEC_PHASE_TABLE.items()))
def test_phase_boundaries_reproduce_the_specification_table(limit, expected):
    fractions = RULES["parameters"]["phase_fractions"]["value"]
    assert phase_bounds(limit, fractions) == expected


def test_phase_labels_for_full_innings_use_ball_boundaries():
    b = pd.Series([0, 35, 36, 89, 90, 119])
    lim = pd.Series([120] * 6)
    got = phase_label(b, lim, RULES["parameters"]["phase_fractions"]["value"]).tolist()
    assert got == ["powerplay", "powerplay", "middle", "middle", "death", "death"]


def test_phase_is_null_without_a_limit_and_dls_uses_proportional_rule():
    d, m = _dls_inputs()
    s = inn(state(d, m), 2)
    assert (s.phase_rule == "PROPORTIONAL_DLS").all()
    assert s.innings_phase.iloc[0] == "powerplay" and s.innings_phase.iloc[-1] == "middle"
    assert phase_label(pd.Series([0]), pd.Series([np.nan])).isna().all()


# ---------------------------------------------------------------- Super Over exclusion
def _so_inputs():
    parts = []
    for mid in (34429, 40725, 77777):
        base = number(rows_n(3, bat=1), match_id=mid)
        base += number(rows_n(3, bat=1), match_id=mid, innings=2)
        base += number(rows_n(2, bat=1), match_id=mid, innings=3)
        base += number(rows_n(2, bat=1), match_id=mid, innings=4)
        parts += base
    ms = matches(*[match(match_id=i) for i in (34429, 40725, 77777)])
    return deliveries(parts), ms


def test_innings_3_and_4_are_excluded_with_the_two_reason_codes():
    d, m = _so_inputs()
    s = state(d, m)
    r = s[s.restricted_innings_flag]
    assert len(r) == 12 and set(r.innings_number) == {3, 4}
    by = r.groupby("match_id").exclusion_reason_code.first().to_dict()
    assert by == {
        34429: "CONFIRMED_SUPER_OVER_BY_CRICSHEET",
        40725: "UNVERIFIED_INNINGS_ROLE",
        77777: "UNVERIFIED_INNINGS_ROLE",  # any other match with innings >= 3 defaults to unverified
    }
    assert (r.exclusion_rule_id == "RULE_INNINGS_3_4").all()
    assert not r.regulation_pressure_eligible.any() and not r.regulation_flag.any()
    reg = s[~s.restricted_innings_flag]
    assert reg.regulation_pressure_eligible.all() and reg.exclusion_reason_code.isna().all()


def test_super_over_rows_are_preserved_and_carry_no_pressure_state():
    d, m = _so_inputs()
    s = state(d, m)
    assert len(s) == len(d)  # source deliveries preserved, none dropped
    r = s[s.restricted_innings_flag]
    for col in ("innings_limit_balls", "legal_balls_remaining", "target", "rrr", "innings_phase",
                "resource_ratio", "crr"):  # fmt: skip
        assert r[col].isna().all(), col


def test_config_reason_codes_match_the_approved_decisions():
    codes = RULES["restricted_innings"]["reason_codes"]
    assert sorted(codes["CONFIRMED_SUPER_OVER_BY_CRICSHEET"]) == [34429, 45512, 50359]
    assert sorted(codes["UNVERIFIED_INNINGS_ROLE"]) == [40725, 48027, 48029]


# ---------------------------------------------------------------- context
def test_season_label_ipl_uses_competition_season_others_use_calendar_year():
    c = pd.Series(["IPL", "T20I", "T20I", "OTHER_T20"])
    src = pd.Series(["2023", "2022/23", "2024", "2025"])
    dt = pd.Series(pd.to_datetime(["2023-04-01", "2022-11-05", "2024-06-01", "2025-02-02"]))
    assert pe.season_label(c, src, dt).tolist() == ["2023", "2022", "2024", "2025"]


def test_other_t20_keeps_state_but_is_out_of_scope():
    rows = number(rows_n(2, bat=1))
    s = state(deliveries(rows), matches(match(ctype="OTHER_T20")))
    assert s.format_out_of_scope.all() and not s.regulation_pressure_eligible.any()
    assert s.team_runs_before.tolist() == [0, 1]


def test_knock_out_and_competition_context_present_before_the_delivery():
    s = state(deliveries(number([row(bat=1)])), matches(match(knock=True, ctype="T20I")))
    assert bool(s.knock_out.iloc[0]) and s.competition_type.iloc[0] == "T20I"
    assert s.season_label.iloc[0] == "2024"


def test_batter_and_bowler_before_state():
    rows = number([
        row(bat=4, striker=11, bowler=21),
        row(extras="wide", prim=1, striker=11, bowler=21),
        row(bat=2, striker=11, bowler=21),
        row(bat=1, striker=12, bowler=21),
        row(wicket=True, dtype="RunOut", dismissed=11, striker=11, bowler=21),
        row(wicket=True, dtype="Bowled", dismissed=11, striker=11, bowler=22),
        row(bat=1, striker=11, bowler=21),
    ])  # fmt: skip
    s = state(deliveries(rows), matches(match()))
    assert s.batter_balls_faced_before.tolist() == [0, 1, 1, 0, 2, 3, 4]  # wide not faced
    assert s.batter_runs_before.tolist() == [0, 4, 4, 0, 6, 6, 6]
    assert s.bowler_legal_balls_before.tolist() == [0, 1, 1, 2, 3, 0, 4]
    assert s.bowler_deliveries_before.tolist() == [0, 1, 2, 3, 4, 0, 5]
    assert s.bowler_runs_charged_before.tolist() == [0, 4, 5, 7, 8, 0, 8]
    # a RunOut is a team wicket, not a bowler wicket (row 4 is the RunOut)
    assert s.bowler_wickets_credited_before.tolist() == [0, 0, 0, 0, 0, 0, 0]
    assert s.den_bowler_credited_wicket.tolist() == [0, 0, 0, 0, 0, 1, 0]
    assert s.bowler_overs_completed_before.tolist() == [0] * 7


# ---------------------------------------------------------------- column groups, config parity
def test_outcome_columns_are_prefixed_and_state_columns_are_separate():
    d, m = simple_two_innings()
    s = state(d, m)
    out = [c for c in s.columns if c.startswith("out_")]
    for must in ("out_batter_runs", "out_is_wicket", "out_extras_type", "out_is_legal_ball"):
        assert must in out
    sc = pe.state_columns(s)
    assert not any(c.startswith(("out_", "den_")) for c in sc)
    assert "legal_balls_bowled_before" in sc and "post_innings_legal_balls" in sc
    assert "post_innings_legal_balls" not in pe.pre_delivery_columns(s)


def test_pressure_rules_parameters_match_the_specification_table():
    text = (BACKEND_ROOT / "docs" / "pressure_framework_v1.md").read_text(encoding="utf-8")
    block = text.split("| Parameter | Initial value", 1)[1].split("Configuration parity", 1)[0]
    names = set(re.findall(r"^\| `([a-zA-Z0-9_]+)`(?: \(L < 120\))? \|", block, re.M))
    params = RULES["parameters"]
    assert names == set(params)
    assert all(v["basis"] in {"EXISTING_RULE", "EXTERNAL_CONVENTION", "DATA_DERIVED",
                              "ARBITRARY_PLACEHOLDER"} for v in params.values())  # fmt: skip
    assert all({"value", "basis", "sensitivity"} <= set(v) for v in params.values())


def test_status_fields_say_exploratory_not_ranking():
    assert pe.STATUS_FIELDS == {
        "status": "EXPLORATORY_NOT_VALIDATED", "official_ranking": False, "not_for_publication": True,
    }  # fmt: skip
    assert RULES["status"] == "EXPLORATORY_NOT_VALIDATED" and RULES["official_ranking"] is False


# ---------------------------------------------------------------- real data (read-only)
@pytest.fixture(scope="module")
def real():
    s = get_settings()
    if not s.duckdb_path.exists():
        pytest.skip("official DuckDB not present")
    d, m = pe.load_inputs(s.duckdb_path)
    return d, m, pe.compute_pre_delivery_state(d, m, RULES)


def test_real_state_row_counts_and_innings_split(real):
    d, m, s = real
    assert len(s) == len(d) == 200_999
    assert s.innings_number.value_counts().sort_index().to_dict() == {
        1: 105_727,
        2: 95_234,
        3: 25,
        4: 13,
    }
    assert s.regulation_flag.sum() == 200_961 and s.restricted_innings_flag.sum() == 38
    # the key is preserved exactly, in order, with no rows invented or dropped
    key = d.sort_values(pe.KEY)[pe.KEY].reset_index(drop=True)
    assert s[pe.KEY].equals(key)


def test_real_restricted_matches_and_reason_codes(real):
    s = real[2]
    r = s[s.restricted_innings_flag].groupby("exclusion_reason_code").match_id.unique()
    assert sorted(r["CONFIRMED_SUPER_OVER_BY_CRICSHEET"]) == [34429, 45512, 50359]
    assert sorted(r["UNVERIFIED_INNINGS_ROLE"]) == [40725, 48027, 48029]


def test_real_verified_data_facts_are_reproduced(real):
    d, m, s = real
    reg = s[s.regulation_flag]
    assert int(s.den_legal_inc.sum()) == 192_444
    assert int(reg.req_nonpositive_flag.sum()) == 12 and set(
        reg[reg.req_nonpositive_flag].match_id
    ) == {48610}
    assert (
        int(s.den_wicket_flag_anomaly.sum()) == 12
        and int(s.den_wicket_without_dismissed.sum()) == 1
    )
    assert int(s.state_wicket_flag_disagreement.sum()) == 739
    assert int((reg.legal_balls_bowled_before >= 90).sum()) == 44_452
    # legal over index 16+ (spec section 2); the L = 120 death label is a subset of those rows
    assert int((reg.innings_phase.eq("death") & reg.innings_limit_balls.eq(120)).sum()) == 44_285
    assert int((s.out_extras_type == "other").sum()) == 264
    assert int((~s.den_extras_category_known).sum()) == 0
    one = reg.drop_duplicates(["match_id", "innings_number"])
    assert int(one.dls_flag.sum()) == 48 and int(one.innings_limit_unstated.sum()) == 2
    assert int(one.dls_exclude_primary.sum()) == 50
    ended = one[one.post_innings_ended_short_of_stated_limit & (one.innings_number == 1)]
    assert sorted(ended.match_id) == [15410, 15546, 31707, 36208, 41975, 46311, 46749, 50408]
    m3 = m[["first_inn_revised_overs", "second_inn_revised_overs", "revised_target"]].notna()
    assert (int(m3.any(axis=1).sum()), int(m3.iloc[:, 0].sum()), int(m3.iloc[:, 1].sum()),
            int(m3.iloc[:, 2].sum())) == (34, 25, 25, 23)  # fmt: skip


def test_real_state_never_has_negative_balls_or_more_wickets_than_ten(real):
    reg = real[2].query("regulation_flag")
    assert reg.legal_balls_remaining.min() >= 0  # never negative
    assert reg.wickets_remaining.between(0, 10).all()
    assert reg.crr.isna().sum() == (reg.legal_balls_bowled_before == 0).sum()


def test_real_innings2_target_is_innings1_total_plus_one_when_not_revised(real):
    d, m, s = real
    tot = d.assign(r=d.batter_runs + d.extras_primary_runs + d.extras_secondary_runs)
    t1 = tot[tot.innings_number == 1].groupby("match_id").r.sum() + 1
    c = s[(s.innings_number == 2) & (s.target_source == "INNINGS1_TOTAL_PLUS_1")]
    first = c.drop_duplicates("match_id").set_index("match_id").target
    assert (first == t1.reindex(first.index)).all() and len(first) > 700


def test_manifest_if_built_records_provenance_and_preservation():
    path = get_settings().phase25_reports_dir / pe_manifest_name()
    if not path.exists():
        pytest.skip("manifest not built yet")
    man = json.loads(path.read_text(encoding="utf-8"))
    assert man["status"] == "EXPLORATORY_NOT_VALIDATED" and man["official_ranking"] is False
    assert man["not_for_publication"] is True
    assert man["inputs"]["cricsheet_files_opened"] == 0
    assert man["preservation"]["official_data_unchanged"] is True
    assert man["inputs"]["official_db_sha256"] and man["code_version"]["engine_sha256"]


def pe_manifest_name():
    from app.services.pressure_service import MANIFEST_NAME

    return MANIFEST_NAME
