"""Reliability utilities for player-match units: split-half (parity and time), Spearman-Brown, ICC.

A *unit table* has one row per player-match with columns ``player_id``, ``match_id``,
``match_date``, ``y`` (the unit's weighted mean residual) and ``w`` (its weight). Estimates are the
UNSHRUNK precision-weighted means, so the correlation is defined even when the between-player
variance sits at the floor. The match-cluster bootstrap resamples matches, never rows or balls.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase6.split_half import fisher_pool  # noqa: F401  (re-exported)

UNIT_COLS = ["player_id", "match_id", "match_date", "y", "w"]


def spearman_brown(r: float | np.ndarray) -> float | np.ndarray:
    """Step-up of a half-test correlation, ``2r/(1+r)``; negative r stays negative (not clipped)."""
    r = np.asarray(r, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(r > -1.0, 2.0 * r / (1.0 + r), np.nan)
    return float(out) if out.ndim == 0 else out


def _check_units(units: pd.DataFrame) -> pd.DataFrame:
    miss = [c for c in UNIT_COLS if c not in units.columns]
    if miss:
        raise ValueError(f"unit table is missing {miss}")
    u = units[UNIT_COLS].dropna(subset=["player_id", "match_id", "y", "w"])
    if (u["w"] <= 0).any():
        raise ValueError("unit weights must be positive (a unit with no weight is not created)")
    return u


def assign_halves(units: pd.DataFrame, mode: str = "parity") -> pd.Series:
    """Half label (0/1) per unit: ``parity`` alternates a player's matches in date order, ``time``
    puts the first half of the player's matches in 0 and the rest in 1."""
    if mode not in ("parity", "time"):
        raise ValueError("mode must be 'parity' or 'time'")
    u = _check_units(units)
    u = u.sort_values(["player_id", "match_date", "match_id"])
    pos = u.groupby("player_id").cumcount()
    if mode == "parity":
        half = (pos % 2).astype(int)
    else:
        n = u.groupby("player_id")["match_id"].transform("size")
        half = (pos >= (n / 2.0)).astype(int)
    return half.reindex(units.index) if units.index.is_unique else half


def _half_means(
    u: pd.DataFrame, half: pd.Series, counts: pd.Series | None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    c = np.ones(len(u)) if counts is None else u["match_id"].map(counts).fillna(0).to_numpy()
    w = u["w"].to_numpy() * c
    out = []
    for h in (0, 1):
        m = (half.to_numpy() == h) & (w > 0)
        g = (
            pd.DataFrame({"player_id": u["player_id"].to_numpy()[m],
                          "wy": (w * u["y"].to_numpy())[m], "w": w[m],
                          "n": (c > 0)[m].astype(int)})
            .groupby("player_id")
            .sum()
        )  # fmt: skip
        g["mean"] = g["wy"] / g["w"]
        out.append(g)
    return out[0], out[1]


def split_half(
    units: pd.DataFrame,
    mode: str = "parity",
    min_matches_per_half: int = 2,
    n_boot: int = 0,
    seed: int = 20260512,
) -> dict[str, Any]:
    """Split-half correlation and Spearman-Brown value (optional match-cluster bootstrap)."""
    u = _check_units(units).reset_index(drop=True)
    half = assign_halves(u, mode).reset_index(drop=True)

    def one(counts: pd.Series | None) -> tuple[float, int]:
        a, b = _half_means(u, half, counts)
        j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
        j = j[(j["n_a"] >= min_matches_per_half) & (j["n_b"] >= min_matches_per_half)]
        if len(j) < 3 or j["mean_a"].std() == 0 or j["mean_b"].std() == 0:
            return float("nan"), int(len(j))
        return float(np.corrcoef(j["mean_a"], j["mean_b"])[0, 1]), int(len(j))

    r, n = one(None)
    res: dict[str, Any] = {"mode": mode, "n_players": n, "r": r,
                           "spearman_brown": float(spearman_brown(r)) if np.isfinite(r) else float("nan")}  # fmt: skip
    if n_boot > 0 and np.isfinite(r):
        mids = np.sort(u["match_id"].unique())
        rng = np.random.default_rng(seed)
        draws = []
        for _ in range(n_boot):
            cnt = pd.Series(np.bincount(rng.integers(0, len(mids), len(mids)), minlength=len(mids)),
                            index=mids)  # fmt: skip
            rb, _ = one(cnt)
            if np.isfinite(rb):
                draws.append(float(spearman_brown(rb)))
        d = np.asarray(draws)
        res["sb_low"] = float(np.percentile(d, 2.5)) if d.size >= 20 else None
        res["sb_high"] = float(np.percentile(d, 97.5)) if d.size >= 20 else None
        res["boot_draws"] = int(d.size)
    return res


def icc1(units: pd.DataFrame, min_units: int = 2) -> dict[str, Any]:
    """One-way random-effects ICC(1) of unit means over players with at least ``min_units`` units."""
    u = _check_units(units)
    n = u.groupby("player_id")["y"].transform("size")
    u = u[n >= min_units]
    if u["player_id"].nunique() < 3:
        return {"icc": float("nan"), "n_players": int(u["player_id"].nunique()), "n_units": len(u)}
    g = u.groupby("player_id")["y"]
    k = g.size().to_numpy().astype(float)
    means = g.mean().to_numpy()
    grand = u["y"].mean()
    a, N = len(k), k.sum()
    msb = float((k * (means - grand) ** 2).sum() / (a - 1))
    ssw = float(((u["y"] - g.transform("mean")) ** 2).sum())
    msw = ssw / (N - a)
    k0 = (N - (k**2).sum() / N) / (a - 1)
    denom = msb + (k0 - 1.0) * msw
    icc = float((msb - msw) / denom) if denom > 0 else float("nan")
    return {
        "icc": icc,
        "n_players": int(a),
        "n_units": int(N),
        "msb": msb,
        "msw": msw,
        "k0": float(k0),
    }


def precision_weighted_means(units: pd.DataFrame) -> pd.DataFrame:
    """Unshrunk per-player estimate ``sum(w y)/sum(w)`` with matches, weight and Kish n_eff."""
    u = _check_units(units)
    g = u.assign(wy=u["w"] * u["y"], w2=u["w"] ** 2).groupby("player_id")
    out = pd.DataFrame(
        {"ybar": g["wy"].sum() / g["w"].sum(), "sum_w": g["w"].sum(), "n_matches": g["match_id"].nunique(),
         "w_eff": g["w"].sum() ** 2 / g["w2"].sum()}
    )  # fmt: skip
    return out.reset_index()


def out_of_time_correlation(
    early: pd.DataFrame, late: pd.DataFrame, min_players: int = 30
) -> dict[str, Any]:
    """Spearman correlation between early-window and late-window unshrunk estimates."""
    j = (
        early.set_index("player_id")["ybar"]
        .to_frame("a")
        .join(late.set_index("player_id")["ybar"].to_frame("b"), how="inner")
    )
    if len(j) < min_players:
        return {"status": "NOT_ESTIMABLE", "n_players": int(len(j)), "spearman": None}
    rho = float(j["a"].rank().corr(j["b"].rank()))
    return {"status": "ESTIMATED", "n_players": int(len(j)), "spearman": rho}
