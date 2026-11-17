"""Player-match units: intensity-weighted sums of residuals per (role, player, match, innings).

A unit exists only when at least one delivery has both a defined intensity and a defined residual
(never zero-filled). ``y`` is the weighted mean residual and ``w`` the sum of intensities.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ROLE_COL = {"batter": "striker_id", "bowler": "bowler_id"}


def build_units(
    df: pd.DataFrame, role: str, intensity: pd.Series, residual: pd.Series, high_cut: float = 0.5
) -> pd.DataFrame:
    """One row per (player, match, innings) with ``y``, ``w``, ``n_balls`` and high-intensity balls."""
    if role not in ROLE_COL:
        raise ValueError("role must be 'batter' or 'bowler'")
    w = intensity.astype("float64")
    r = residual.astype("float64")
    ok = w.notna() & r.notna() & (w > 0)
    d = pd.DataFrame(
        {
            "player_id": df.loc[ok, ROLE_COL[role]].to_numpy(),
            "match_id": df.loc[ok, "match_id"].to_numpy(),
            "innings": df.loc[ok, "innings_number"].to_numpy(),
            "match_date": df.loc[ok, "match_date"].to_numpy(),
            "competition_type": df.loc[ok, "competition_type"].to_numpy(),
            "period": df.loc[ok, "period"].to_numpy(),
            "w": w[ok].to_numpy(),
            "wr": (w[ok] * r[ok]).to_numpy(),
            "w2": (w[ok] ** 2).to_numpy(),
            "hi": (w[ok] >= high_cut).to_numpy().astype(int),
        }
    )
    keys = ["player_id", "match_id", "innings", "match_date", "competition_type", "period"]
    g = d.groupby(keys, sort=True).agg(
        w=("w", "sum"),
        wr=("wr", "sum"),
        w2=("w2", "sum"),
        n_balls=("w", "size"),
        hi_balls=("hi", "sum"),
    )
    g["y"] = g["wr"] / g["w"]
    g["mean_intensity"] = g["w"] / g["n_balls"]
    out = g.reset_index()
    out.insert(0, "role", role)
    return out.drop(columns=["wr"])


def effective_n(units: pd.DataFrame) -> pd.Series:
    """Kish effective count per player ``(sum w)^2 / sum w^2`` over the player's deliveries."""
    g = units.groupby("player_id")
    return g["w"].sum() ** 2 / g["w2"].sum().replace(0, np.nan)
