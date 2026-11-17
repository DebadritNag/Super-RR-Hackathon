"""Synthetic state frames for the Phase 4 tests (innings-1 par, phases, split)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def innings_rows(
    match_id: int,
    date: str,
    comp: str = "IPL",
    runs_per_ball: float = 1.0,
    limit: int = 120,
    innings: int = 1,
    balls: int | None = None,
    **extra,
) -> pd.DataFrame:
    """One complete innings: ball b scores ``runs_per_ball`` so runs before ball b = rpb * b."""
    n = limit if balls is None else balls
    b = np.arange(n)
    df = pd.DataFrame(
        {
            "match_id": match_id,
            "innings_number": innings,
            "innings_ball_num": b + 1,
            "match_date": pd.Timestamp(date),
            "competition_type": comp,
            "legal_balls_bowled_before": b,
            "team_runs_before": runs_per_ball * b,
            "out_runs_row": runs_per_ball,
            "innings_limit_balls": limit,
            "post_innings_legal_balls": n,
            "post_innings_wickets": 3,
            "regulation_pressure_eligible": True,
            "format_out_of_scope": False,
            "dls_exclude_primary": limit != 120,
            "chase_flag": innings == 2,
            "target_basis_unverified": False,
            "req_nonpositive_flag": False,
            "rrr": 8.0,
            "out_is_wicket": False,
        }
    )
    for k, v in extra.items():
        df[k] = v
    return df


def many_matches(specs: list[tuple[int, str, str, float]]) -> pd.DataFrame:
    """specs: (match_id, date, comp, runs_per_ball)."""
    return pd.concat(
        [innings_rows(m, d, c, r) for m, d, c, r in specs], ignore_index=True
    ).reset_index(drop=True)


def brute_force_prior(df: pd.DataFrame, min_prior: int) -> np.ndarray:
    """Slow reference: for each innings-1 row, mean runs-before at the same ball over matches
    with a strictly earlier date in the same competition (NaN when fewer than min_prior)."""
    inn1 = df[df["innings_number"] == 1]
    out = np.full(len(df), np.nan)
    pos = {idx: i for i, idx in enumerate(df.index)}
    for idx, r in inn1.iterrows():
        prior = inn1[
            (inn1["competition_type"] == r["competition_type"])
            & (inn1["match_date"] < r["match_date"])
            & (inn1["legal_balls_bowled_before"] == r["legal_balls_bowled_before"])
        ]
        if len(prior) >= min_prior:
            out[pos[idx]] = prior["team_runs_before"].mean()
    return out
