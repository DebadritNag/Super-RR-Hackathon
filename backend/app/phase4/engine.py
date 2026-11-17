"""Phase 4 Stage D/E engine: pressure-row tables, player x match matrices, bootstrap ranking.

Everything here works on PRE_TEST rows only (TRAIN + VALIDATION). Row tables are built through
``guard_frame`` so TEST rows are refused while the test lock is closed. The bootstrap resamples
MATCHES (clusters) with one global multinomial weight matrix, so cells and roles that share a
match share its resample weight. Baseline expectations, TRAIN-fitted thresholds and shrinkage
parameters (k, target) are held fixed across resamples.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import scoring as sc
from app.phase4 import shrink as sh
from app.phase4.baseline import BaselineSet, role_frame
from app.phase4.lockguard import guard_frame
from app.phase4.split import TestLock

PRIMARY = {"batter": ("runs", 1.0), "bowler": ("charged", -1.0)}
SECONDARY = {"batter": "dismissal", "bowler": "wkt"}
TOP_K = 10


# ---------------------------------------------------------------- row tables
def base_rows(
    d: pd.DataFrame, bs: BaselineSet, role: str, stream: str, lock: TestLock
) -> pd.DataFrame:
    """All primary-population delivery rows of one role/stream with the B0 residual."""
    guard_frame(d, lock, "engine.base_rows")
    fr = role_frame(role, d)
    ex = bs.expected(role, stream, fr)
    t = pd.DataFrame(
        {
            "src": fr["_src_index"].to_numpy(),
            "player_id": fr["player_id"].to_numpy(),
            "match_id": fr["match_id"].to_numpy(),
            "comp": fr["competition_type"].to_numpy(),
            "period": fr["period"].to_numpy(),
            "date": fr["match_date"].to_numpy(),
            "actual": fr[stream].to_numpy(dtype=float),
            "expected": ex["expected"].to_numpy(),
        }
    )
    t["resid"] = t["actual"] - t["expected"]
    return t


def population(d: pd.DataFrame, ctx: str) -> pd.Series:
    """Comparison population of a context. Innings-1 rows without a prior par are excluded."""
    unavail = d["par_unavailable_insufficient_prior"].fillna(False).astype(bool)
    chase = d["chase_pop"].astype(bool)
    inn1 = d["inn1_pop"].astype(bool) & ~unavail
    return chase if ctx == "chase" else inn1 if ctx == "inn1" else (chase | inn1)


def tag_rows(rows: pd.DataFrame, d: pd.DataFrame, defn: str, thr: dict[str, float]) -> pd.DataFrame:
    """Add ``in_pop`` (definition population) and ``press`` (pressure flag) to a row table."""
    ctx, _ = sc.parse_definition(defn)
    pop = population(d, ctx).reindex(rows["src"]).to_numpy()
    flag = sc.pressure_flag(d, defn, thr).reindex(rows["src"]).to_numpy()
    out = rows.copy()
    out["in_pop"] = pop
    out["press"] = flag & pop
    return out


# ---------------------------------------------------------------- cells and matrices
@dataclass
class Cell:
    """Pressure rows of one (format, role, stream) as player x match matrices."""

    comp: str
    role: str
    stream: str
    rows: pd.DataFrame
    ms: pd.DataFrame
    players: np.ndarray
    matches: np.ndarray
    match_period: np.ndarray
    N: np.ndarray
    S: np.ndarray

    def train_pt(self) -> pd.DataFrame:
        r = self.rows[self.rows["period"] == "TRAIN"]
        return sh.player_table(sh.match_stats(r))

    def fit(self) -> dict[str, Any]:
        return sh.fit_cell(self.train_pt())


def build_cell(press_rows: pd.DataFrame, comp: str, role: str, stream: str) -> Cell | None:
    r = press_rows[press_rows["comp"] == comp]
    if r.empty:
        return None
    ms = sh.match_stats(r)
    md = r.groupby("match_id").agg(date=("date", "first"), period=("period", "first"))
    md = md.reset_index().sort_values(["date", "match_id"], kind="mergesort")
    matches = md["match_id"].to_numpy()
    players = np.sort(ms["player_id"].unique())
    pi = pd.Index(players).get_indexer(ms["player_id"])
    mi = pd.Index(matches).get_indexer(ms["match_id"])
    N = np.zeros((len(players), len(matches)))
    S = np.zeros_like(N)
    np.add.at(N, (pi, mi), ms["n"].to_numpy(float))
    np.add.at(S, (pi, mi), ms["s"].to_numpy(float))
    return Cell(comp, role, stream, r.reset_index(drop=True), ms, players, matches,
                md["period"].to_numpy(), N, S)  # fmt: skip


def global_weights(match_ids: np.ndarray, n_boot: int, seed: int) -> tuple[pd.Index, np.ndarray]:
    """One seeded multinomial match-resample weight matrix over all pre-test matches."""
    gm = pd.Index(np.sort(np.unique(match_ids)))
    rng = np.random.default_rng(seed)
    w = rng.multinomial(len(gm), np.full(len(gm), 1.0 / len(gm)), size=n_boot)
    return gm, w.astype(float)


def cell_weights(cell: Cell, gm: pd.Index, W: np.ndarray) -> np.ndarray:
    """Resample weights for a cell's matches, shape (n_cell_matches, n_boot)."""
    return W[:, gm.get_indexer(cell.matches)].T


def point_estimates(cell: Cell, fit: dict[str, Any], config: str) -> pd.DataFrame:
    """Shrunk estimate per player on the PRE_TEST window (TRAIN-fitted k and target)."""
    pt = sh.player_table(cell.ms)
    return sh.estimate(pt, fit, config).reindex(cell.players)


def draws(cell: Cell, est: pd.DataFrame, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap ball counts and shrunk-estimate draws, shape (players, n_boot)."""
    nb, sb = cell.N @ w, cell.S @ w
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(nb > 0, sb / np.where(nb > 0, nb, 1), np.nan)
    ne = est["n_eff"].to_numpy()[:, None] * nb / np.maximum(cell.N.sum(1)[:, None], 1.0)
    k = float(est["k"].iloc[0]) if len(est) else 0.0
    den = ne + k
    B = np.where(den > 0, ne / np.where(den > 0, den, 1.0), 0.0)
    tgt = est["target"].to_numpy()[:, None]
    return nb, np.where(nb > 0, tgt + B * (r - tgt), np.nan)


# ---------------------------------------------------------------- rank utilities
def col_ranks(X: np.ndarray, present: np.ndarray) -> np.ndarray:
    """Descending ranks 1..m among present entries of each column; NaN where absent."""
    x = np.where(present, X, -np.inf)
    order = np.argsort(-x, axis=0, kind="stable")
    n = X.shape[0]
    base = np.broadcast_to(np.arange(1, n + 1, dtype=float)[:, None], X.shape).copy()
    ranks = np.empty(X.shape)
    np.put_along_axis(ranks, order, base, axis=0)
    return np.where(present, ranks, np.nan)


def masked_pearson(A: np.ndarray, B: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Column-wise Pearson correlation over masked rows; NaN when fewer than 3 rows or no spread."""
    m = mask.sum(0).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        a0, b0 = np.where(mask, A, 0.0), np.where(mask, B, 0.0)
        da = np.where(mask, A - a0.sum(0) / m, 0.0)
        db = np.where(mask, B - b0.sum(0) / m, 0.0)
        r = (da * db).sum(0) / np.sqrt((da**2).sum(0) * (db**2).sum(0))
    return np.where(m >= 3, r, np.nan)


def masked_spearman(A: np.ndarray, B: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return masked_pearson(col_ranks(A, mask), col_ranks(B, mask), mask)


def rank_summary(
    score_draws: np.ndarray, point_score: np.ndarray, point_present: np.ndarray, k: int = TOP_K
) -> dict[str, Any]:
    """Ranking distribution from bootstrap score draws (NaN = absent or ineligible in a draw).

    Players absent at the point estimate are excluded entirely. The pool is never padded: with
    fewer than ``k`` present players the Top-k is everyone present.
    """
    present = np.isfinite(score_draws) & point_present[:, None]
    ranks = col_ranks(score_draws, present)
    pr = col_ranks(point_score[:, None], point_present[:, None])[:, 0]
    top_pt = pr <= k
    incl = ranks <= k
    inter = (incl & top_pt[:, None]).sum(0).astype(float)
    union = (incl | top_pt[:, None]).sum(0).astype(float)
    pt_sub = col_ranks(np.broadcast_to(point_score[:, None], score_draws.shape), present)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        lo, med, hi = (np.nanpercentile(ranks, q, axis=1) for q in (2.5, 50, 97.5))
        mean_rank = np.nanmean(ranks, axis=1)
    rho = masked_pearson(ranks, pt_sub, present)
    return {
        "inclusion_prob": incl.mean(1),
        "present_prob": present.mean(1),
        "rank_lo": lo,
        "rank_med": med,
        "rank_hi": hi,
        "mean_rank": mean_rank,
        "point_rank": pr,
        "overlap": inter,
        "jaccard": np.where(union > 0, inter / np.where(union > 0, union, 1), np.nan),
        "spearman": rho,
        "pool_size": present.sum(0),
        "point_pool": int(point_present.sum()),
        "max_overlap": int(min(k, point_present.sum())),
    }


def summarize_ranking(rs: dict[str, Any]) -> dict[str, Any]:
    """Scalar summary of a ``rank_summary`` result."""
    sp = rs["spearman"][np.isfinite(rs["spearman"])]
    ps = rs["pool_size"]
    return {
        "pool_size": rs["point_pool"],
        "top10_size": rs["max_overlap"],
        "trivial_full_pool": bool(rs["point_pool"] <= TOP_K),
        "expected_top10_overlap": float(np.mean(rs["overlap"])) if len(ps) else None,
        "mean_jaccard": float(np.nanmean(rs["jaccard"])) if len(ps) else None,
        "mean_spearman": float(sp.mean()) if sp.size else None,
        "spearman_p2_5": float(np.percentile(sp, 2.5)) if sp.size else None,
        "spearman_p97_5": float(np.percentile(sp, 97.5)) if sp.size else None,
        "pool_size_p2_5": float(np.percentile(ps, 2.5)) if len(ps) else None,
        "pool_size_p97_5": float(np.percentile(ps, 97.5)) if len(ps) else None,
    }


def player_ranking_table(
    cell: Cell, est: pd.DataFrame, rs: dict[str, Any], sign: float, point_present: np.ndarray
) -> pd.DataFrame:
    """Per-player ranking distribution (eligible players only; never padded)."""
    t = pd.DataFrame(
        {
            "player_id": cell.players,
            "point_score": sign * est["shrunk"].to_numpy(),
            "point_rank": rs["point_rank"],
            "top10_inclusion_prob": rs["inclusion_prob"],
            "present_prob": rs["present_prob"],
            "rank_lo": rs["rank_lo"],
            "rank_median": rs["rank_med"],
            "rank_hi": rs["rank_hi"],
            "mean_rank": rs["mean_rank"],
            "pressure_opportunities": est["n"].to_numpy(),
            "distinct_matches": est["matches"].to_numpy(),
            "effective_sample_size": est["n_eff"].to_numpy(),
        }
    )
    t = t[point_present].sort_values(["point_rank", "player_id"], kind="mergesort")
    return t.reset_index(drop=True)
