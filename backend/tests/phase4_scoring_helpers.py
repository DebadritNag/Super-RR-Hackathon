"""Synthetic prepared state frames for the Phase 4 baseline, shrinkage and scoring tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRAIN_DATES = pd.date_range("2023-01-01", periods=40, freq="D")
VALID_DATES = pd.date_range("2025-03-01", periods=20, freq="D")
TEST_DATES = pd.date_range("2026-02-01", periods=6, freq="D")
BATTERS = [1, 2, 3, 4]
BOWLERS = [11, 12, 13]


def synth_frame(seed: int = 0, with_test: bool = False, comps=("IPL", "T20I")) -> pd.DataFrame:
    """Prepared delivery frame (period, populations, role context and role columns)."""
    rng = np.random.default_rng(seed)
    parts = []
    mid = 0
    for comp in comps:
        dates = [("TRAIN", x) for x in TRAIN_DATES] + [("VALIDATION", x) for x in VALID_DATES]
        if with_test:
            dates += [("TEST", x) for x in TEST_DATES]
        for period, date in dates:
            mid += 1
            for inn in (1, 2):
                n = 12
                b = np.arange(n)
                runs = rng.integers(0, 5, n).astype(float)
                wkt = (rng.random(n) < 0.08).astype(bool)
                df = pd.DataFrame(
                    {
                        "match_id": mid,
                        "innings_number": inn,
                        "innings_ball_num": b + 1,
                        "match_date": date,
                        "period": period,
                        "competition_type": comp,
                        "chase_flag": inn == 2,
                        "role_ctx": "chase" if inn == 2 else "inn1",
                        "inn_key": mid * 10 + inn,
                        "base_pop": True,
                        "chase_pop": inn == 2,
                        "inn1_pop": inn == 1,
                        "rrr": np.where(inn == 2, rng.uniform(4, 20, n), np.nan),
                        "neg_par_dev_prior": np.where(inn == 1, rng.uniform(-10, 10, n), np.nan),
                        "innings_phase": np.where(b < 4, "powerplay", "middle"),
                        "wbin": "10-8",
                        "wickets_remaining": 10,
                        "striker_id": rng.choice(BATTERS, n),
                        "bowler_id": rng.choice(BOWLERS, n),
                        "den_counts_as_ball_faced": 1,
                        "out_batter_runs": runs,
                        "out_is_four": runs == 4,
                        "out_is_six": False,
                        "out_is_wicket": wkt,
                        "out_dismissed_player_id": np.where(wkt, 1, np.nan),
                        "out_dismissal_type": np.where(wkt, "Bowled", None),
                        "den_bowler_counts_row": 1,
                        "den_bowler_charged_runs": runs,
                        "den_bowler_credited_wicket": wkt.astype(float),
                        "den_legal_inc": 1,
                        "out_runs_row": runs,
                    }
                )
                df["out_dismissed_player_id"] = df["striker_id"].where(wkt)
                parts.append(df)
    return pd.concat(parts, ignore_index=True)
