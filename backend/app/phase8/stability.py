"""Match-cluster bootstrap, rank stability and Top-10 inclusion probability (seeded)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from app.phase8.constants import SEED


def match_count_draws(
    match_ids: np.ndarray, n_draws: int, seed: int = SEED, strata: np.ndarray | None = None
) -> np.ndarray:
    """Resampling counts, shape (n_draws, n_matches): matches drawn with replacement.

    With ``strata`` (one label per match) matches are resampled within each stratum, so the period
    mix is preserved. The draw depends only on ``seed`` and the sorted match ids.
    """
    mids = np.asarray(match_ids)
    if len(np.unique(mids)) != len(mids):
        raise ValueError("match ids must be unique")
    rng = np.random.default_rng(seed)
    counts = np.zeros((n_draws, len(mids)), dtype=np.int32)
    groups = (
        [np.arange(len(mids))]
        if strata is None
        else [np.flatnonzero(strata == s) for s in np.unique(strata)]
    )
    for idx in groups:
        pick = rng.integers(0, len(idx), size=(n_draws, len(idx)))
        for d in range(n_draws):
            counts[d, idx] += np.bincount(pick[d], minlength=len(idx))
    return counts


def bootstrap_weighted_means(
    units: pd.DataFrame, n_draws: int = 1000, seed: int = SEED, strata: pd.Series | None = None
) -> tuple[np.ndarray, pd.Index]:
    """Per-player unshrunk precision-weighted means for each match-cluster draw.

    Returns (draws x players array, player index); NaN where a player has no weight in a draw.
    """
    u = units[["player_id", "match_id", "y", "w"]].dropna()
    mids = np.sort(u["match_id"].unique())
    mpos = np.searchsorted(mids, u["match_id"].to_numpy())
    players, ppos = np.unique(u["player_id"].to_numpy(), return_inverse=True)
    st = None
    if strata is not None:
        st = strata.reindex(mids).to_numpy()
    cnt = match_count_draws(mids, n_draws, seed, st)
    w, wy = u["w"].to_numpy(), (u["w"] * u["y"]).to_numpy()
    out = np.full((n_draws, len(players)), np.nan)
    for d in range(n_draws):
        c = cnt[d, mpos]
        num = np.bincount(ppos, weights=c * wy, minlength=len(players))
        den = np.bincount(ppos, weights=c * w, minlength=len(players))
        ok = den > 0
        out[d, ok] = num[ok] / den[ok]
    return out, pd.Index(players, name="player_id")


def rank_stability(
    draws: np.ndarray, players: pd.Index, top_k: int = 10, higher_is_better: bool = True
) -> pd.DataFrame:
    """Top-k inclusion probability and 95% rank / estimate intervals from bootstrap draws.

    Ranking per draw is descending by estimate with ties broken by ``player_id`` ascending (exact
    ties only matter for identical values). NaN estimates are not ranked in that draw.
    """
    n_draws, n_pl = draws.shape
    ids = np.asarray(players)
    sign = -1.0 if higher_is_better else 1.0
    ranks = np.full((n_draws, n_pl), np.nan)
    order_ids = np.argsort(ids, kind="stable")
    for d in range(n_draws):
        v = draws[d]
        ok = np.isfinite(v)
        idx = order_ids[ok[order_ids]]
        o = idx[np.argsort(sign * v[idx], kind="stable")]
        ranks[d, o] = np.arange(1, len(o) + 1)
    inc = np.nansum(ranks <= top_k, axis=0) / n_draws
    present = np.isfinite(ranks).sum(axis=0)

    def q(a: np.ndarray, p: float) -> np.ndarray:
        with np.errstate(all="ignore"):
            return np.where(np.isfinite(a).sum(0) > 0, np.nanpercentile(a, p, axis=0), np.nan)

    with np.errstate(all="ignore"):
        return pd.DataFrame(
            {"player_id": ids, "top_k_prob": inc, "rank_median": q(ranks, 50),
             "rank_low": q(ranks, 2.5), "rank_high": q(ranks, 97.5),
             "est_low": q(draws, 2.5), "est_high": q(draws, 97.5),
             "draws_present": present}
        )  # fmt: skip


def point_ranking(est: pd.Series, higher_is_better: bool = True, tol: float = 1e-12) -> pd.Series:
    """Deterministic rank 1..n: order by estimate, ties (|diff| < tol) by ``player_id`` ascending."""
    s = est.dropna()
    ids = s.index.to_numpy()
    v = s.to_numpy() * (-1.0 if higher_is_better else 1.0)
    order = np.lexsort((ids, np.round(v / tol) * tol))
    rank = pd.Series(np.arange(1, len(s) + 1), index=s.index[order])
    return rank.reindex(est.index)


def top_k_overlap(a: pd.Series, b: pd.Series, k: int = 10) -> dict[str, Any]:
    """Overlap of two rank series' top-k sets (share and count)."""
    sa = set(a[a <= k].index)
    sb = set(b[b <= k].index)
    inter = len(sa & sb)
    return {"overlap": inter, "share": inter / k, "k": k}


def bootstrap_statistic(
    units: pd.DataFrame,
    statistic: Callable[[pd.DataFrame], float],
    n_draws: int = 200,
    seed: int = SEED,
) -> dict[str, Any]:
    """Percentile interval of any unit-table statistic under the seeded match bootstrap."""
    mids = np.sort(units["match_id"].unique())
    cnt = match_count_draws(mids, n_draws, seed)
    vals = []
    by = {m: g for m, g in units.groupby("match_id")}
    for d in range(n_draws):
        frames = [by[m] for m, c in zip(mids, cnt[d], strict=True) for _ in range(int(c))]
        if frames:
            v = statistic(pd.concat(frames, ignore_index=True))
            if np.isfinite(v):
                vals.append(float(v))
    a = np.asarray(vals)
    return {"n": int(a.size), "low": float(np.percentile(a, 2.5)) if a.size >= 20 else None,
            "high": float(np.percentile(a, 97.5)) if a.size >= 20 else None}  # fmt: skip
