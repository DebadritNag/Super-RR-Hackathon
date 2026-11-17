"""WPA attribution: striker, bowler, wicket, extras, run-out, exclusions and the split identity."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.phase8.wpa import attribute, component_flags, exclusion_codes

BASE = {
    "wp_before": 0.50, "wp_after": 0.60, "out_batter_runs": 0, "out_extras_type": "None",
    "out_is_wicket": False, "out_dismissal_type": "None", "out_dismissed_player_id": np.nan,
    "den_bowler_credited_wicket": 0, "striker_id": 1, "non_striker_id": 2,
    "ok_run_target": True, "ok_wicket_target": True,
    "cf_bat": np.nan, "cf_ext": np.nan, "cf_team": np.nan, "cf_wkt": np.nan,
}  # fmt: skip


def _row(**kw):
    return {**BASE, **kw}


def _att(*rows):
    return attribute(pd.DataFrame(list(rows)))


def test_runs_off_the_bat_credit_striker_and_charge_bowler():
    a = _att(_row(out_batter_runs=4, wp_after=0.58)).iloc[0]
    assert a["striker_wpa"] == pytest.approx(0.08)
    assert a["bowler_wpa"] == pytest.approx(-0.08)
    assert np.isnan(a["team_only_wpa"]) and a["split_rule"] == "SINGLE"


def test_dot_ball_that_lowers_wp_credits_bowler():
    a = _att(_row(wp_after=0.47)).iloc[0]
    assert a["striker_wpa"] == pytest.approx(-0.03)
    assert a["bowler_wpa"] == pytest.approx(0.03)


def test_wide_is_charged_to_bowler_and_gives_striker_nothing():
    a = _att(_row(out_extras_type="wide", wp_after=0.53)).iloc[0]
    assert a["bowler_wpa"] == pytest.approx(-0.03)
    assert np.isnan(a["striker_wpa"]) and np.isnan(a["team_only_wpa"])


def test_no_ball_with_bat_runs_splits_between_striker_and_bowler_and_adds_up():
    a = _att(
        _row(out_extras_type="Overstep", out_batter_runs=4, wp_after=0.70, cf_bat=0.66, cf_ext=0.52)
    ).iloc[0]
    d = 0.20
    d_bat = 0.16  # counterfactual deltas 0.16 and 0.02 sum to 0.18; the remainder is shared
    assert a["striker_wpa"] == pytest.approx(d_bat + (d - 0.18) * d_bat / 0.18)
    assert a["bowler_wpa"] == pytest.approx(-d)  # bowler pays for the whole ball
    assert a["split_rule"] == "COUNTERFACTUAL"


@pytest.mark.parametrize("kind", ["byes", "legbyes"])
def test_byes_and_leg_byes_go_to_the_batting_side_only(kind):
    a = _att(_row(out_extras_type=kind, wp_after=0.54)).iloc[0]
    assert a["team_only_wpa"] == pytest.approx(0.04)
    assert np.isnan(a["striker_wpa"]) and np.isnan(a["bowler_wpa"])


def test_bowler_credited_wicket_gives_bowler_the_whole_ball():
    a = _att(
        _row(out_is_wicket=True, out_dismissal_type="Bowled", out_dismissed_player_id=1,
             den_bowler_credited_wicket=1, wp_after=0.35, cf_bat=0.49, cf_wkt=0.36)
    ).iloc[0]  # fmt: skip
    assert a["bowler_wpa"] == pytest.approx(0.15)  # -(d) with d = -0.15
    assert a["striker_wpa"] == pytest.approx(-0.15)
    assert a["dismissed_player_id"] == 1
    assert a["dismissed_wpa"] < 0 and not a["dismissed_non_striker"]


def test_run_out_gives_the_bowler_no_credit_for_the_wicket_share():
    a = _att(
        _row(out_is_wicket=True, out_dismissal_type="RunOut", out_dismissed_player_id=1,
             den_bowler_credited_wicket=0, wp_after=0.35, cf_bat=0.49, cf_wkt=0.36)
    ).iloc[0]  # fmt: skip
    d_bat = a["striker_wpa"] - a["dismissed_wpa"]  # striker total = bat share + own wicket share
    assert a["bowler_wpa"] == pytest.approx(-d_bat)
    assert abs(a["bowler_wpa"]) < abs(a["d"])


def test_run_out_of_the_non_striker_keeps_the_runs_with_the_striker():
    a = _att(
        _row(out_batter_runs=1, out_is_wicket=True, out_dismissal_type="RunOut",
             out_dismissed_player_id=2, den_bowler_credited_wicket=0, wp_after=0.47,
             cf_bat=0.53, cf_wkt=0.44)
    ).iloc[0]  # fmt: skip
    assert a["dismissed_non_striker"] and a["dismissed_player_id"] == 2
    assert a["striker_wpa"] > 0  # the run off the bat is still the striker's
    assert a["dismissed_wpa"] < 0
    assert a["striker_wpa"] + a["dismissed_wpa"] == pytest.approx(a["d"])


def test_stumping_on_a_wide_charges_bowler_for_wide_and_credits_wicket():
    a = _att(
        _row(out_extras_type="wide", out_is_wicket=True, out_dismissal_type="Stump",
             out_dismissed_player_id=1, den_bowler_credited_wicket=1, wp_after=0.40,
             cf_ext=0.51, cf_wkt=0.41)
    ).iloc[0]  # fmt: skip
    assert a["bowler_wpa"] == pytest.approx(-a["d"])
    assert a["striker_wpa"] < 0  # striker takes his own wicket share only


@pytest.mark.parametrize(
    ("kw", "code"),
    [
        ({"out_is_wicket": True, "out_dismissal_type": "Retire Out"}, "UNUSUAL_EVENT"),
        ({"out_is_wicket": True, "out_dismissal_type": "Obstructing the field"}, "UNUSUAL_EVENT"),
        ({"out_extras_type": "other"}, "EXTRAS_OTHER_OR_PENALTY"),
        ({"out_extras_type": "Penalty"}, "EXTRAS_OTHER_OR_PENALTY"),
        ({"ok_wicket_target": False}, "METRIC_FLAG_ANOMALY"),
        ({"wp_after": np.nan}, "WP_UNAVAILABLE"),
    ],
)
def test_unusual_and_undefined_balls_are_excluded_not_zeroed(kw, code):
    df = pd.DataFrame([_row(**kw)])
    assert exclusion_codes(df).iloc[0] == code
    a = attribute(df).iloc[0]
    assert a["excluded_reason"] == code
    for c in ("d", "striker_wpa", "bowler_wpa", "team_only_wpa", "dismissed_wpa"):
        assert np.isnan(a[c])


def test_literal_none_extras_label_means_no_extra():
    f = component_flags(pd.DataFrame([_row(out_extras_type="None")]))
    assert f.iloc[0].to_dict() == {"bat": True, "ext": False, "team": False, "wkt": False}


def test_missing_counterfactual_falls_back_to_equal_split_and_is_labelled():
    a = _att(_row(out_extras_type="Overstep", out_batter_runs=2, wp_after=0.62)).iloc[
        0
    ]  # no cf columns given
    assert a["split_rule"] == "EQUAL_FALLBACK"
    assert a["bowler_wpa"] == pytest.approx(-0.12)


def test_flat_wp_gives_zero_delta_label():
    a = _att(_row(out_extras_type="Overstep", wp_after=0.5, cf_bat=0.5, cf_ext=0.5)).iloc[0]
    assert a["split_rule"] == "ZERO_DELTA" and a["bowler_wpa"] == pytest.approx(0.0)


def test_components_always_add_up_to_the_ball():
    rng = np.random.default_rng(3)
    rows = []
    for _ in range(300):
        wb = rng.uniform(0.05, 0.95)
        rows.append(
            _row(wp_before=wb, wp_after=float(np.clip(wb + rng.normal(0, 0.1), 0.005, 0.995)),
                 out_is_wicket=True, out_dismissal_type="Bowled", out_dismissed_player_id=1,
                 den_bowler_credited_wicket=1, out_batter_runs=int(rng.integers(0, 2)),
                 cf_bat=float(np.clip(wb + rng.normal(0, 0.05), 0.005, 0.995)),
                 cf_wkt=float(np.clip(wb - abs(rng.normal(0, 0.1)), 0.005, 0.995)))
        )  # fmt: skip
    a = _att(*rows)
    assert np.allclose(a["striker_wpa"], a["d"])  # bat + own wicket = whole ball
    assert np.allclose(a["bowler_wpa"], -a["d"])  # credited wicket: bowler gets the whole ball
