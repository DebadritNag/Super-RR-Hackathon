"""Deterministic ranking and ranking-comparison helpers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def rank_players(df: pd.DataFrame, score_col: str = "score", id_col: str = "player_id"):
    """Stable ordinal ranking: score descending, ties by ascending player id. Rank starts at 1."""
    out = df.sort_values([score_col, id_col], ascending=[False, True], kind="mergesort")
    out = out.reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    return out


def top_k(df: pd.DataFrame, k: int = 10, score_col: str = "score", id_col: str = "player_id"):
    return [int(x) for x in rank_players(df, score_col, id_col)[id_col].head(k)]


def topk_overlap(ids_a: Iterable, ids_b: Iterable, k: int = 10) -> int:
    """Size of the intersection of the first k ids of two ordered id lists."""
    return len(set(list(ids_a)[:k]) & set(list(ids_b)[:k]))


def spearman_common(
    a: pd.DataFrame, b: pd.DataFrame, score_col: str = "score", id_col: str = "player_id"
) -> dict:
    """Spearman correlation of ranks on players present in both tables.

    Returns {'rho': None, 'n': n} when fewer than 3 common players or no rank variation.
    """
    m = a[[id_col, score_col]].merge(b[[id_col, score_col]], on=id_col, suffixes=("_a", "_b"))
    n = len(m)
    if n < 3:
        return {"rho": None, "n": n}
    ra = rank_players(m.rename(columns={f"{score_col}_a": "score"})[[id_col, "score"]])
    rb = rank_players(m.rename(columns={f"{score_col}_b": "score"})[[id_col, "score"]])
    j = ra[[id_col, "rank"]].merge(rb[[id_col, "rank"]], on=id_col, suffixes=("_a", "_b"))
    if j["rank_a"].nunique() < 2 or j["rank_b"].nunique() < 2:
        return {"rho": None, "n": n}
    rho = float(spearmanr(j["rank_a"], j["rank_b"]).statistic)
    return {"rho": None if rho != rho else rho, "n": n}


def movement(
    a: pd.DataFrame,
    b: pd.DataFrame,
    k: int = 10,
    score_col: str = "score",
    id_col: str = "player_id",
    n_movers: int = 5,
) -> dict:
    """Rank movement of common players from ranking a to ranking b (own-list ranks)."""
    ra, rb = rank_players(a, score_col, id_col), rank_players(b, score_col, id_col)
    m = ra[[id_col, "rank"]].merge(rb[[id_col, "rank"]], on=id_col, suffixes=("_a", "_b"))
    m["change"] = m["rank_b"] - m["rank_a"]
    absc = m["change"].abs()
    movers = m.assign(abs_change=absc).sort_values(
        ["abs_change", id_col], ascending=[False, True], kind="mergesort"
    )
    ta, tb = set(ra[id_col].head(k)), set(rb[id_col].head(k))
    return {
        "n_common": int(len(m)),
        "mean_abs_change": float(absc.mean()) if len(m) else None,
        "max_abs_change": int(absc.max()) if len(m) else None,
        "entering_top_k": sorted(int(x) for x in tb - ta),
        "leaving_top_k": sorted(int(x) for x in ta - tb),
        "biggest_movers": [
            {
                "player_id": int(r[id_col]),
                "rank_a": int(r["rank_a"]),
                "rank_b": int(r["rank_b"]),
                "change": int(r["change"]),
            }
            for _, r in movers.head(n_movers).iterrows()
        ],
    }


def percentile_summary(values: Sequence[float], probs: Sequence[float]) -> dict:
    a = np.asarray(list(values), dtype=float)
    if a.size == 0:
        return {f"p{int(p)}": None for p in probs}
    return {f"p{int(p)}": float(np.percentile(a, p)) for p in probs}
