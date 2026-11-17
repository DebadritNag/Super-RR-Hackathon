"""Phase 7 descriptive builder: hand-checkable formulas, edge cases, scope and determinism."""

from __future__ import annotations

import math

import duckdb
import numpy as np
import pandas as pd
import pytest

from app.phase6.cleanup_scans import FORBIDDEN_PUBLIC_FIELD
from app.phase7 import descriptive as ds
from tests.phase7_desc_helpers import BASE, PROV, row, tiny_frame, tiny_profiles, tiny_ref


def bat(out, pid, fmt="IPL"):
    t = out["batters"]
    return t[(t["player_id"] == pid) & (t["format"] == fmt)].iloc[0]


def bowl(out, pid, fmt="IPL"):
    t = out["bowlers"]
    return t[(t["player_id"] == pid) & (t["format"] == fmt)].iloc[0]


def test_batter_totals_match_hand_calculation():
    r = bat(tiny_profiles(), 1)
    assert (r["balls_faced"], r["runs"], r["dismissals"]) == (4, 10, 1)
    assert r["strike_rate"] == pytest.approx(250.0)
    assert r["average"] == pytest.approx(10.0)
    assert (r["fours"], r["sixes"], r["boundary_runs"]) == (1, 1, 10)
    assert r["boundary_run_share"] == pytest.approx(1.0)
    assert r["boundary_ball_share"] == pytest.approx(0.5)
    assert (r["dot_balls"], r["dot_ball_share"]) == (2, pytest.approx(0.5))
    assert r["balls_per_dismissal"] == pytest.approx(4.0)


def test_wide_is_not_a_ball_faced_and_adds_no_batter_runs():
    r = bat(tiny_profiles(), 1)
    assert r["balls_faced"] == 4  # five rows, one of them a wide
    assert r["runs"] == 10


def test_batter_phase_and_innings_splits():
    r = bat(tiny_profiles(), 1)
    assert (r["pp_balls"], r["pp_runs"], r["pp_strike_rate"]) == (2, 4, pytest.approx(200.0))
    assert (r["mid_balls"], r["mid_runs"], r["mid_strike_rate"]) == (1, 6, pytest.approx(600.0))
    # a real zero: one ball, no runs, one dismissal
    assert (r["death_balls"], r["death_runs"], r["death_dismissals"]) == (1, 0, 1)
    assert r["death_strike_rate"] == 0.0
    assert r["inn1_balls"] == 4
    assert r["vs_pace_balls"] == 4


def test_empty_splits_are_missing_not_zero():
    r = bat(tiny_profiles(), 1)
    assert r["chase_balls"] == 0  # a true count
    assert math.isnan(r["chase_runs"]) and math.isnan(r["chase_strike_rate"])
    assert math.isnan(r["vs_spin_runs"]) and math.isnan(r["vs_spin_dismissals"])
    assert "chase:NO_BALLS_IN_SPLIT" in r["missing_value_notes"]


def test_zero_dismissals_leave_average_empty_with_a_reason():
    r = bat(tiny_profiles(), 2)
    assert (r["balls_faced"], r["runs"], r["dismissals"]) == (2, 1, 0)
    assert r["strike_rate"] == pytest.approx(50.0)
    assert math.isnan(r["average"]) and math.isnan(r["balls_per_dismissal"])
    assert "average:NO_DISMISSALS" in r["missing_value_notes"]


def test_zero_balls_faced_leaves_rates_empty():
    r = bat(tiny_profiles(), 3)
    assert r["balls_faced"] == 0
    assert math.isnan(r["strike_rate"]) and math.isnan(r["dot_ball_share"])
    assert r["sample_sufficiency"] == "NO_BALLS"
    assert "rates:NO_BALLS_OBSERVED" in r["missing_value_notes"]
    assert r["participation_role"] == "NO_BALLS_FACED_OR_BOWLED"


def test_bowler_totals_match_hand_calculation():
    r = bowl(tiny_profiles(), 100)
    assert r["legal_balls"] == 6 and r["overs"] == "1.0"
    assert (r["runs_conceded"], r["wickets"]) == (13, 1)
    assert r["economy"] == pytest.approx(13.0)
    assert r["balls_per_wicket"] == pytest.approx(6.0)
    assert (r["dot_balls"], r["dot_ball_share"]) == (3, pytest.approx(0.5))
    assert (r["fours"], r["sixes"]) == (1, 1)
    assert r["boundary_conceded_share"] == pytest.approx(2 / 6)
    assert (r["wides"], r["no_balls"], r["extras_charged_runs"]) == (2, 0, 2)
    assert r["participation_role"] == "BOWLS_ONLY"


def test_bowler_wicket_is_bowler_credit_only():
    f = tiny_frame()
    # a run-out: wicket flag set but no bowler credit
    f = pd.concat(
        [
            f,
            pd.DataFrame([row(out_is_wicket=True, out_dismissed_player_id=2, innings_ball_num=99)]),
        ],
        ignore_index=True,
    )
    out = ds.build_profiles(f, tiny_ref(), ds.load_config(), PROV)
    assert bowl(out, 100)["wickets"] == 1
    assert bat(out, 1)["dismissals"] == 1  # dismissed player 2 is not the striker 1
    assert bat(out, 2)["dismissals"] == 0  # striker 1 faced; player 2 was dismissed elsewhere


def test_dismissal_counts_only_for_the_dismissed_striker():
    f = pd.DataFrame(
        [
            row(out_is_wicket=True, out_dismissed_player_id=2, striker_id=1, innings_ball_num=1),
            row(out_is_wicket=True, out_dismissed_player_id=2, striker_id=2, innings_ball_num=2),
        ]
    )
    out = ds.build_profiles(f, tiny_ref(), ds.load_config(), PROV)
    assert bat(out, 1)["dismissals"] == 0
    assert bat(out, 2)["dismissals"] == 1


def test_small_samples_are_flagged_not_hidden():
    out = tiny_profiles()
    assert len(out["batters"]) == 3  # every batter row is kept
    assert bat(out, 1)["sample_sufficiency"] == "LOW_SAMPLE"
    assert "display flag only" in bat(out, 1)["sample_note"]


def test_context_sample_is_a_count_with_a_descriptive_label():
    r = bat(tiny_profiles(), 1)
    assert r["context_sample_balls"] == 3
    assert r["context_sample_label"] == "DESCRIPTIVE_EXPERIMENTAL_COUNT_ONLY"
    assert r["context_definition"] == "any|q0.75 PROVISIONAL"
    assert bat(tiny_profiles(), 2)["context_sample_balls"] == 0  # no context rows: a real count


def test_mapping_warnings_and_classification_labels():
    out = tiny_profiles()
    assert pd.isna(bat(out, 1)["mapping_warnings"])
    w = bat(out, 3)["mapping_warnings"]
    assert "NAME_SHARED_WITH_OTHER_PLAYER_ID" in w and "NO_CLASSIFICATION_ROW" in w
    w2 = bat(out, 2)["mapping_warnings"]
    assert "NATIONALITY_UNKNOWN" in w2 and "INTERNATIONAL_STATUS_UNKNOWN" in w2
    assert "NOT_IN_COMPETITION_MAPPING" in bowl(out, 100)["mapping_warnings"]
    assert bat(out, 1)["nationality_verification"] == "DERIVED"
    assert bat(out, 2)["international_status_verification"] == "UNVERIFIED"


def test_player_not_in_players_table_is_flagged_and_not_dropped():
    f = pd.DataFrame([row(striker_id=777, innings_ball_num=1)])
    out = ds.build_profiles(f, tiny_ref(), ds.load_config(), PROV)
    r = bat(out, 777)
    assert "PLAYER_ID_NOT_IN_PLAYERS_TABLE" in r["mapping_warnings"]
    assert pd.isna(r["player_name"])


def test_formats_are_kept_separate():
    f = pd.DataFrame(
        [
            row(format="IPL", out_batter_runs=2, out_runs_row=2, innings_ball_num=1),
            row(format="T20I", match_id=2, out_batter_runs=3, out_runs_row=3, innings_ball_num=1),
        ]
    )
    out = ds.build_profiles(f, tiny_ref(), ds.load_config(), PROV)
    assert bat(out, 1, "IPL")["runs"] == 2
    assert bat(out, 1, "T20I")["runs"] == 3
    assert set(out["batters"]["format"]) == {"IPL", "T20I"}


def test_outputs_sorted_by_player_id_and_no_rank_or_score_columns():
    out = tiny_profiles()
    for key in ("batters", "bowlers"):
        ids = list(out[key]["player_id"])
        assert ids == sorted(ids)
        assert [c for c in out[key].columns if FORBIDDEN_PUBLIC_FIELD.search(c)] == []
    assert [c for c in out["per_match"].columns if FORBIDDEN_PUBLIC_FIELD.search(c)] == []


def test_build_is_deterministic():
    a, b = tiny_profiles(), tiny_profiles()
    for k in a:
        pd.testing.assert_frame_equal(a[k], b[k])


def test_per_match_table_rows():
    pm = tiny_profiles()["per_match"]
    r = pm[(pm["side"] == "batter") & (pm["player_id"] == 1)].iloc[0]
    assert (r["balls"], r["runs"], r["outs"], r["fours"], r["sixes"], r["dots"]) == (
        4,
        10,
        1,
        1,
        1,
        2,
    )
    assert r["match_date"] == "2024-04-01"


# ----------------------------------------------------------------------------- bootstrap
def test_bootstrap_of_identical_matches_collapses_to_the_ratio():
    lo, hi, why = ds.bootstrap_ratio(
        np.array([10.0] * 6), np.array([5.0] * 6), (1, 2, 3), 200, 0.95, 100.0
    )
    assert why is None and lo == pytest.approx(200.0) and hi == pytest.approx(200.0)


def test_bootstrap_is_seeded_and_seed_sensitive():
    num, den = np.array([3.0, 9, 1, 12, 6, 0]), np.array([4.0, 6, 3, 8, 5, 2])
    a = ds.bootstrap_ratio(num, den, (7, 1), 300, 0.95, 100.0)
    b = ds.bootstrap_ratio(num, den, (7, 1), 300, 0.95, 100.0)
    c = ds.bootstrap_ratio(num, den, (8, 1), 300, 0.95, 100.0)
    assert a == b and a != c
    assert a[0] < 100.0 * num.sum() / den.sum() < a[1]


def test_bootstrap_reports_a_reason_instead_of_a_fake_interval():
    assert ds.bootstrap_ratio(np.array([1.0]), np.array([1.0]), (1,), 50, 0.95)[2] == (
        "FEWER_THAN_2_MATCHES"
    )
    z = ds.bootstrap_ratio(np.zeros(5), np.zeros(5), (1,), 50, 0.95)
    assert z[0] is None and z[2] == "UNDEFINED_IN_MANY_RESAMPLES"


def test_interval_needs_five_matches():
    r = bat(tiny_profiles(), 1)
    assert math.isnan(r["strike_rate_ci_low"])
    assert r["strike_rate_ci_unavailable_reason"] == "FEWER_THAN_5_MATCHES"


def test_interval_present_with_enough_matches():
    rows = []
    for m in range(1, 9):
        for i in range(3):
            rows.append(
                row(
                    match_id=m,
                    innings_ball_num=i + 1,
                    out_batter_runs=(m + i) % 5,
                    out_runs_row=(m + i) % 5,
                )
            )
    out = ds.build_profiles(pd.DataFrame(rows), tiny_ref(), ds.load_config(), PROV)
    r = bat(out, 1)
    assert r["strike_rate_ci_low"] < r["strike_rate"] < r["strike_rate_ci_high"]
    assert pd.isna(r["strike_rate_ci_unavailable_reason"])


# ----------------------------------------------------------------------------- scope (SQL)
@pytest.fixture()
def tiny_dbs(tmp_path):
    cols = list(ds.FRAME_SQL.split("SELECT")[1].split("FROM")[0].split(","))
    assert cols  # the select list is parsed below by building the table from BASE keys
    store, official = tmp_path / "x.duckdb", tmp_path / "o.duckdb"
    rows = [
        # match 1 TRAIN IPL ok; match 2 TEST IPL; match 3 VALIDATION OTHER_T20 out of scope;
        # match 1 innings 3 (super over); match 4 T20I ok
        dict(match_id=1, innings_number=1, innings_ball_num=1, comp="IPL", oos=False),
        dict(match_id=1, innings_number=3, innings_ball_num=1, comp="IPL", oos=False),
        dict(match_id=2, innings_number=1, innings_ball_num=1, comp="IPL", oos=False),
        dict(match_id=3, innings_number=1, innings_ball_num=1, comp="OTHER_T20", oos=True),
        dict(match_id=4, innings_number=2, innings_ball_num=1, comp="T20I", oos=False),
    ]
    recs = []
    for r in rows:
        b = dict(BASE)
        b.update(
            match_id=r["match_id"],
            innings_number=r["innings_number"],
            innings_ball_num=r["innings_ball_num"],
            competition_type=r["comp"],
            format_out_of_scope=r["oos"],
        )
        b.pop("format")
        b.pop("pace_or_spin")
        b.pop("batting_type")
        b.pop("bowling_type")
        recs.append(b)
    state = pd.DataFrame(recs)
    periods = pd.DataFrame(
        {
            "match_id": [1, 2, 3, 4],
            "period": ["TRAIN", "TEST", "VALIDATION", "VALIDATION"],
        }
    )
    e = duckdb.connect(str(store))
    e.register("s", state)
    e.register("p", periods)
    e.execute("CREATE TABLE exp_pre_delivery_state AS SELECT * FROM s")
    e.execute("CREATE TABLE p4_match_period AS SELECT * FROM p")
    e.close()
    dl = pd.DataFrame(
        {
            "match_id": [1, 1, 2, 3, 4],
            "innings_number": [1, 3, 1, 1, 2],
            "innings_ball_num": [1, 1, 1, 1, 1],
            "pace_or_spin": ["Pace"] * 5,
            "batting_type": ["RHB"] * 5,
            "bowling_type": ["Right-arm Fast"] * 5,
        }
    )
    o = duckdb.connect(str(official))
    o.register("d", dl)
    o.execute("CREATE TABLE deliveries AS SELECT * FROM d")
    o.close()
    return store, official


def test_scope_excludes_test_super_overs_and_other_t20(tiny_dbs):
    store, official = tiny_dbs
    f = ds.load_frame(store, official)
    assert sorted(zip(f["match_id"], f["innings_number"], f["format"], strict=True)) == [
        (1, 1, "IPL"),
        (4, 2, "T20I"),
    ]
    assert (f["pace_or_spin"] == "Pace").all()


def test_frame_query_never_selects_test_rows():
    assert "p.period <> 'TEST'" in ds.FRAME_SQL
    assert "innings_number IN (1, 2)" in ds.FRAME_SQL
    assert "format_out_of_scope = FALSE" in ds.FRAME_SQL
    assert "competition_type IN ('IPL', 'T20I')" in ds.FRAME_SQL
