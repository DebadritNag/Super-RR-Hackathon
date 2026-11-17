"""Hand-built delivery frame and reference tables for the Phase 7 descriptive tests."""

from __future__ import annotations

import pandas as pd

from app.phase7 import descriptive as ds

BASE = {
    "format": "IPL",
    "match_id": 1,
    "innings_number": 1,
    "season_label": "2024",
    "match_date": pd.Timestamp("2024-04-01"),
    "striker_id": 1,
    "bowler_id": 100,
    "innings_phase": "powerplay",
    "dls_flag": False,
    "den_wicket_flag_anomaly": False,
    "out_extras_type": "None",
    "den_extras_label_unverified": False,
    "out_batter_runs": 0,
    "out_is_four": False,
    "out_is_six": False,
    "out_is_wicket": False,
    "out_dismissed_player_id": None,
    "out_runs_row": 0,
    "den_legal_inc": 1,
    "den_counts_as_ball_faced": 1,
    "den_bowler_counts_row": 1,
    "den_bowler_charged_runs": 0,
    "den_bowler_credited_wicket": 0,
    "state_version": "test_state",
    "pace_or_spin": "Pace",
    "batting_type": "RHB",
    "bowling_type": "Right-arm Fast",
}


def row(**kw):
    r = dict(BASE)
    r.update(kw)
    return r


def tiny_frame() -> pd.DataFrame:
    """Batter 1 (IPL match 1): 4, dot, wide (1 run), 6, wicket. Bowler 100 bowls all five.
    Batter 2 (match 1, powerplay/middle): 1 and 0, no dismissal. Batter 3 faces only a wide."""
    rows = [
        row(out_batter_runs=4, out_is_four=True, out_runs_row=4, den_bowler_charged_runs=4),
        row(),
        row(
            out_extras_type="wide",
            out_runs_row=1,
            den_legal_inc=0,
            den_counts_as_ball_faced=0,
            den_bowler_charged_runs=1,
        ),
        row(
            out_batter_runs=6,
            out_is_six=True,
            out_runs_row=6,
            den_bowler_charged_runs=6,
            innings_phase="middle",
        ),
        row(
            out_is_wicket=True,
            out_dismissed_player_id=1,
            den_bowler_credited_wicket=1,
            innings_phase="death",
        ),
        row(striker_id=2, out_batter_runs=1, out_runs_row=1, den_bowler_charged_runs=1),
        row(striker_id=2, innings_phase="middle"),
        row(
            striker_id=3,
            out_extras_type="wide",
            out_runs_row=1,
            den_legal_inc=0,
            den_counts_as_ball_faced=0,
            den_bowler_charged_runs=1,
        ),
    ]
    df = pd.DataFrame(rows)
    df["innings_ball_num"] = range(1, len(df) + 1)
    return df


def tiny_ref() -> dict[str, pd.DataFrame]:
    players = pd.DataFrame(
        {
            "player_id": [1, 2, 3, 100],
            "player_name": ["Alpha", "Beta", "Gamma", "Delta"],
            "in_mapping": [True, True, True, False],
            "in_playing_eleven": [True, True, True, True],
            "in_deliveries": [True] * 4,
            "shares_name_with_other_id": [False, False, True, False],
        }
    )
    cls = pd.DataFrame(
        {
            "player_id": [1, 2, 100],
            "squad_role": ["Batter", None, "Bowler"],
            "nationality": ["Indian", "Unknown", "Overseas"],
            "nationality_verification": ["DERIVED", "UNVERIFIED", "DERIVED"],
            "international_status": ["DERIVED_CAPPED", "UNKNOWN", "DERIVED_CAPPED"],
            "international_status_verification": ["X", "UNVERIFIED", "X"],
            "conflict_flag": [False, False, False],
        }
    )
    mp = pd.DataFrame({"player_id": [1, 100], "format": ["IPL", "IPL"], "matches_played": [1, 1]})
    ctx = pd.DataFrame(
        {
            "player_id": [1],
            "format": ["IPL"],
            "role": ["batter"],
            "context_sample_balls": [3.0],
            "context_sample_matches": [1],
        }
    )
    return {"players": players, "classification": cls, "matches_played": mp, "context": ctx}


PROV = {"state_version": "t", "official_db_sha256": "a" * 64, "analytical_store_sha256": "b" * 64}


def tiny_profiles():
    return ds.build_profiles(tiny_frame(), tiny_ref(), ds.load_config(), PROV)


def synthetic_frame() -> pd.DataFrame:
    """Batters 1-12: 8 IPL matches x 10 balls each (80 balls). Runs follow a fixed pattern.
    Batter 21 always scores 6, batter 22 never scores, batters 23 and 24 share one pattern.
    Batter 25 is never dismissed. Bowlers 101-103 bowl every ball in turn."""
    rows = []
    ball = 0

    def add(pid, m, i, runs, wicket=False):
        nonlocal ball
        ball += 1
        phase = "powerplay" if i < 2 else ("middle" if i < 7 else "death")
        bowler = 101 + (pid + m + i) % 3
        rows.append(
            row(
                striker_id=pid,
                bowler_id=bowler,
                match_id=m,
                innings_ball_num=ball,
                innings_phase=phase,
                out_batter_runs=runs,
                out_runs_row=runs,
                out_is_four=runs == 4,
                out_is_six=runs == 6,
                out_is_wicket=wicket,
                out_dismissed_player_id=pid if wicket else None,
                den_bowler_charged_runs=runs,
                den_bowler_credited_wicket=int(wicket),
                match_date=pd.Timestamp("2024-04-01") + pd.Timedelta(days=m),
            )
        )

    for pid in list(range(1, 13)):
        for m in range(1, 9):
            for i in range(10):
                runs = (pid * m + i) % 7
                add(pid, m, i, runs, wicket=(pid + m + i) % 23 == 0)
    for m in range(1, 9):
        for i in range(10):
            add(21, m, i, 6)
            add(22, m, i, 0)
            r = (m * 3 + i * 5) % 7
            add(23, m, i, r)
            add(24, m, i, r)
            add(25, m, i, (m + i) % 5)
    return pd.DataFrame(rows)


def synthetic_ref() -> dict[str, pd.DataFrame]:
    ids = list(range(1, 13)) + [21, 22, 23, 24, 25, 101, 102, 103]
    players = pd.DataFrame(
        {
            "player_id": ids,
            "player_name": [f"Player {i:03d}" for i in ids],
            "in_mapping": True,
            "in_playing_eleven": True,
            "in_deliveries": True,
            "shares_name_with_other_id": False,
        }
    )
    cls = pd.DataFrame(
        {
            "player_id": ids,
            "squad_role": None,
            "nationality": ["Indian" if i % 2 else "Overseas" for i in ids],
            "nationality_verification": "DERIVED",
            "international_status": "UNKNOWN",
            "international_status_verification": "UNVERIFIED",
            "conflict_flag": False,
        }
    )
    mp = pd.DataFrame({"player_id": ids, "format": "IPL", "matches_played": 8})
    ctx = pd.DataFrame(
        {
            "player_id": [1],
            "format": ["IPL"],
            "role": ["batter"],
            "context_sample_balls": [12.0],
            "context_sample_matches": [4],
        }
    )
    return {"players": players, "classification": cls, "matches_played": mp, "context": ctx}


def context_json() -> dict:
    checks = [
        {
            "check_id": "variance_floor",
            "label": "Between-player variance above the shrinkage floor",
            "observed": "at the floor in 48 of 48 contexts",
            "threshold": "above the floor",
            "status": "NOT_MET",
        }
    ]
    return {
        "version": "p7_descriptive_context_v1",
        "overview": {
            "official": {
                "matches_total": 883,
                "delivery_rows_total": 200999,
                "matches_by_competition": [
                    {
                        "competition_type": "IPL",
                        "matches": 371,
                        "matches_with_deliveries": 367,
                        "first_date": "2022-03-26",
                        "last_date": "2026-05-31",
                    }
                ],
                "lineage": [
                    {
                        "file_name": "updated_ball_by_ball.csv",
                        "role": "PRIMARY",
                        "row_count": 200999,
                        "sha256": "0" * 64,
                        "load_status": "LOADED",
                    }
                ],
            },
            "analytical_store": {
                "match_periods": {"TRAIN": 512, "VALIDATION": 211, "TEST": 144},
                "rows_in_innings_3_4_excluded": 38,
                "rows_out_of_scope_competition": 6985,
                "late_t20i_dates_unverified": 42,
            },
            "descriptive_scope": {
                "window": "PRE_TEST",
                "formats": {
                    "IPL": {
                        "matches": 8,
                        "delivery_rows": 100,
                        "batter_profiles": 17,
                        "bowler_profiles": 3,
                    }
                },
                "players_with_any_profile": 20,
            },
            "pending_official_inputs": [
                {
                    "item": "Official IPL retention list",
                    "status": "PENDING",
                    "handling": "none assumed",
                }
            ],
            "reliability_checks": checks,
            "why_no_ordered_lists": ["The between-player variance sits at the floor."],
            "lists_available": False,
            "descriptive_hashes": {"x.csv": "1" * 64},
        },
        "methodology": {
            "sections": [{"title": "What is published", "text": "Descriptive profiles."}],
            "reliability_facts": {"contexts": 48, "contexts_at_variance_floor": 48},
            "primary_definition": {"id": "any|q0.75", "label": "PROVISIONAL, not validated"},
        },
    }


def write_reports(directory) -> dict[str, pd.DataFrame]:
    """Write synthetic profile CSVs and context JSON into ``directory``."""
    import json
    from pathlib import Path

    d = Path(directory)
    out = ds.build_profiles(synthetic_frame(), synthetic_ref(), ds.load_config(), PROV)
    ds.write_csv(out["batters"], d / ds.BATTER_CSV)
    ds.write_csv(out["bowlers"], d / ds.BOWLER_CSV)
    ds.write_csv(out["per_match"], d / ds.PER_MATCH_CSV)
    (d / ds.CONTEXT_JSON).write_text(json.dumps(context_json()), encoding="utf-8")
    return out
