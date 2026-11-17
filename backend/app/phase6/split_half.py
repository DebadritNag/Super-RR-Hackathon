"""Split-half reliability of pressure-stream player means (EXPERIMENTAL_NOT_VALIDATED).

Wraps the Phase 5 split machinery (``half_masks``, ``half_stats``, ``sb``) and adds repeated
random match splits, bootstrap intervals over players and over matches, a window mask by period
or date, and Fisher-z pooling across cells. The results are in-sample diagnostics on TRAIN and
VALIDATION; TEST rows cannot enter (``Study`` drops them and every frame is guarded).

Spearman-Brown ``2r / (1 + r)`` assumes parallel halves. Odd/even is the closest to that;
early/late splits in time and so also measures drift; random splits mix both. A negative ``r``
gives a negative corrected value, which is reported as is: clipping would hide the absence of
signal.
"""

from __future__ import annotations

import zlib
from typing import Any

import numpy as np
import pandas as pd

from app.phase5 import reliability as rb
from app.phase5.reliability import ESTIMATED, NOT_ESTIMABLE
from app.phase6.constants import IN_SAMPLE_LABEL

MODES = ("odd_even", "early_late", "random")
PERIOD_WINDOWS = {"TRAIN": ("TRAIN",), "PRE_TEST": ("TRAIN", "VALIDATION")}


def unit_seed(base: int, *key: Any) -> int:
    """Stable per-unit seed from a base seed and a key (no Python hash randomisation)."""
    return int((int(base) + zlib.crc32("|".join(str(k) for k in key).encode())) % (2**32))


def window_mask(
    cd: rb.CellData, window: str | None = None, start: str | None = None, end: str | None = None
) -> np.ndarray:
    """Boolean mask over the matches of ``cd``: by period name and/or ``[start, end]`` dates."""
    m = np.ones(cd.N.shape[1], dtype=bool)
    if window is not None:
        if window not in PERIOD_WINDOWS:
            raise ValueError(f"unknown window '{window}'")
        m &= np.isin(cd.period, PERIOD_WINDOWS[window])
    dates = pd.to_datetime(pd.Series(cd.dates)).dt.strftime("%Y-%m-%d").to_numpy()
    if start is not None:
        m &= dates >= start
    if end is not None:
        m &= dates <= end
    return m


def fisher_pool(r: np.ndarray, n: np.ndarray, clip: float = 0.99) -> dict[str, float]:
    """Pool correlations on the Fisher-z scale with weights ``n - 3`` (correlation clipped)."""
    r, n = np.asarray(r, float), np.asarray(n, float)
    ok = np.isfinite(r) & np.isfinite(n) & (n > 3)
    if not ok.any():
        return {"r": float("nan"), "se": float("nan"), "cells": 0}
    z = np.arctanh(np.clip(r[ok], -clip, clip))
    wt = n[ok] - 3.0
    return {"r": float(np.tanh((wt * z).sum() / wt.sum())), "se": float(1.0 / np.sqrt(wt.sum())),
            "cells": int(ok.sum())}  # fmt: skip


def _pearson_rows(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Row-wise Pearson correlation of two (draws, players) arrays."""
    xc = x - x.mean(1, keepdims=True)
    yc = y - y.mean(1, keepdims=True)
    den = np.sqrt((xc**2).sum(1) * (yc**2).sum(1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, (xc * yc).sum(1) / np.where(den > 0, den, 1.0), np.nan)


def bootstrap_players(m1: np.ndarray, m2: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    """Spearman-Brown draws from resampling players with replacement (half means given)."""
    p = len(m1)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, p, size=(n_boot, p))
    return rb.sb(_pearson_rows(m1[idx], m2[idx]))


def _interval(x: np.ndarray) -> tuple[float | None, float | None, int, float | None]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 20:
        return None, None, int(x.size), None
    return (float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5)), int(x.size),
            float((x <= 0).mean()))  # fmt: skip


def _num(x: Any) -> float | None:
    x = float(x)
    return x if np.isfinite(x) else None


def split_half_unit(
    cd: rb.CellData,
    w: np.ndarray | None,
    mask: np.ndarray,
    mode: str,
    min_balls_per_half: int,
    seed: int,
    n_random: int = 200,
    n_boot: int = 1000,
    min_players: int = 10,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """One split-half row and its interval rows for the matches selected by ``mask``.

    ``w`` are full-width match-bootstrap weights (matches of ``cd`` by draws) or None.
    """
    if mode not in MODES:
        raise ValueError(f"unknown split mode '{mode}'")
    sub = cd.select_cols(mask)
    row: dict[str, Any] = {"mode": mode, "min_balls_per_half": min_balls_per_half,
                           "matches": int(sub.N.shape[1]), "label": IN_SAMPLE_LABEL}  # fmt: skip
    empty = {"players": 0, "status": NOT_ESTIMABLE, "r_pearson": None, "r_spearman": None,
             "sb_pearson": None, "sb_spearman": None, "split_sd_sb": None}  # fmt: skip
    if sub.N.shape[0] == 0 or sub.N.shape[1] < 2:
        return {**row, **empty}, []
    ws = None if w is None else w[mask]
    present = sub.N > 0
    one = np.ones((sub.N.shape[1], 1))
    cis: list[dict[str, Any]] = []

    if mode == "random":
        pe, sp, ns = [], [], []
        for rep in range(n_random):
            rng = np.random.default_rng(seed + rep)
            A, B = rb.half_masks(present, "random", rng)
            h = rb.half_stats(sub.N, sub.S, A, B, one, min_balls_per_half)
            pe.append(float(h["pearson"][0]))
            sp.append(float(h["spearman"][0]))
            ns.append(int(h["n"][0]))
        pe, sp = np.asarray(pe), np.asarray(sp)
        n_pl = int(np.median(ns))
        good = np.isfinite(pe)
        if not good.any() or n_pl < min_players:
            return {**row, **empty, "players": n_pl}, []
        sbs = rb.sb(pe[good])
        out = {**row, "players": n_pl, "status": ESTIMATED,
               "r_pearson": _num(np.median(pe[good])), "r_spearman": _num(np.nanmedian(sp)),
               "sb_pearson": _num(rb.sb(np.median(pe[good]))),
               "sb_spearman": _num(rb.sb(np.nanmedian(sp))),
               "split_sd_sb": _num(np.std(sbs, ddof=1)) if sbs.size > 1 else None,
               "repeats": int(good.sum())}  # fmt: skip
        rng = np.random.default_rng(seed + 10_000)
        meds = np.median(rng.choice(pe[good], size=(n_boot, int(good.sum()))), axis=1)
        lo, hi, nd, pn = _interval(rb.sb(meds))
        cis.append({"ci_method": "repeat_bootstrap_of_median", "lo": lo, "hi": hi,
                    "draws": nd, "share_draws_nonpositive": pn})  # fmt: skip
        # the repeat bootstrap shows split noise only; player sampling noise comes from a
        # player bootstrap on the repeat whose r is closest to the median r
        j = int(np.nanargmin(np.abs(np.where(good, pe, np.inf) - np.median(pe[good]))))
        A, B = rb.half_masks(present, "random", np.random.default_rng(seed + j))
        hj = rb.half_stats(sub.N, sub.S, A, B, one, min_balls_per_half)
        okj = hj["ok"][:, 0]
        lo, hi, nd, pn = _interval(
            bootstrap_players(hj["m1"][okj, 0], hj["m2"][okj, 0], n_boot, seed + 20_000)
        )
        cis.append({"ci_method": "player_bootstrap_median_split", "lo": lo, "hi": hi,
                    "draws": nd, "share_draws_nonpositive": pn})  # fmt: skip
        if ws is not None:
            hb = rb.half_stats(sub.N, sub.S, A, B, ws, min_balls_per_half)
            lo, hi, nd, pn = _interval(rb.sb(hb["pearson"]))
            cis.append({"ci_method": "match_bootstrap_median_split", "lo": lo, "hi": hi,
                        "draws": nd, "share_draws_nonpositive": pn})  # fmt: skip
        return out, cis

    A, B = rb.half_masks(present, mode)
    h = rb.half_stats(sub.N, sub.S, A, B, one, min_balls_per_half)
    n_pl = int(h["n"][0])
    r = float(h["pearson"][0])
    if n_pl < min_players or not np.isfinite(r):
        return {**row, **empty, "players": n_pl}, []
    out = {**row, "players": n_pl, "status": ESTIMATED, "r_pearson": _num(r),
           "r_spearman": _num(h["spearman"][0]), "sb_pearson": _num(rb.sb(r)),
           "sb_spearman": _num(rb.sb(h["spearman"][0])), "split_sd_sb": None}  # fmt: skip
    ok = h["ok"][:, 0]
    lo, hi, nd, pn = _interval(bootstrap_players(h["m1"][ok, 0], h["m2"][ok, 0], n_boot, seed))
    cis.append({"ci_method": "player_bootstrap", "lo": lo, "hi": hi, "draws": nd,
                "share_draws_nonpositive": pn})  # fmt: skip
    if ws is not None:
        hb = rb.half_stats(sub.N, sub.S, A, B, ws, min_balls_per_half)
        lo, hi, nd, pn = _interval(rb.sb(hb["pearson"]))
        cis.append({"ci_method": "match_bootstrap", "lo": lo, "hi": hi, "draws": nd,
                    "share_draws_nonpositive": pn})  # fmt: skip
    return out, cis


def pool_rows(df: pd.DataFrame, clip: float = 0.99) -> pd.DataFrame:
    """Fisher-z pooling over format x role cells per definition, stream group, window, mode."""
    d = df[df["status"] == ESTIMATED].copy()
    d["stream_group"] = np.where(d["is_primary_stream"], "primary", "secondary")
    out = []
    for (defn, grp, window, mode), g in d.groupby(["definition", "stream_group", "window", "mode"]):
        p = fisher_pool(g["r_pearson"].to_numpy(), g["players"].to_numpy(), clip)
        out.append(
            {
                "definition": defn, "stream_group": grp, "window": window, "mode": mode,
                "cells": p["cells"], "players_total": int(g["players"].sum()),
                "pooled_r": _num(p["r"]), "pooled_sb": _num(rb.sb(p["r"])), "z_se": _num(p["se"]),
                "label": IN_SAMPLE_LABEL,
            }
        )  # fmt: skip
    return pd.DataFrame(out)
