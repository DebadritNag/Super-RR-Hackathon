"""Context-adjusted baselines and actual-versus-expected (Phase 3 prep, Stage 4). EXPLORATORY.

Transparent hierarchical empirical-Bayes cell baselines. No model is trained. The expected value of
a delivery is the (shrunk) mean outcome of comparable deliveries in the same context cell, with the
player's own deliveries (leave-player-out) or the match's deliveries (leave-match-out) removed.

Levels (finest to coarsest): [pressure membership x] comp|role|phase|wickets-bin -> comp|role|phase
-> comp|role -> comp. The reference baseline B0 has no pressure term; the per-candidate sensitivity
baselines add pressure membership as the finest level. A raw death-over rate is never compared with
an ordinary-over rate: expectations are taken inside the phase cell, so the phase effect is part of
the expectation and not of the player residual.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics.shrinkage import (
    beta_binomial_shrink,
    eb_shrink,
    k_from_children,
    pooled_other_mean,
    shrink_to_parent,
)

BATTER_STREAMS = {"runs": False, "dot": True, "boundary": True, "dismissal": True}
BOWLER_STREAMS = {"charged": False, "wkt": True, "dot": True, "boundary": True}
LEVEL_NAMES = ["L0 comp|role|phase|wbin", "L1 comp|role|phase", "L2 comp|role", "L3 comp"]


# ---------------------------------------------------------------- observation frames
def batter_frame(df: pd.DataFrame) -> pd.DataFrame:
    """One row per ball faced in the base population (BATTER_SQL definition via the den flag)."""
    m = df["base_pop"] & (df["den_counts_as_ball_faced"] == 1) & df["striker_id"].notna()
    d = df.loc[m].copy()
    d["player_id"] = d["striker_id"].astype("int64")
    d["runs"] = d["out_batter_runs"].astype(float)
    d["dot"] = (d["out_batter_runs"] == 0).astype(float)
    d["boundary"] = (d["out_is_four"].fillna(False) | d["out_is_six"].fillna(False)).astype(float)
    dis = (
        d["out_is_wicket"].fillna(False).astype(bool)
        & (d["out_dismissed_player_id"] == d["striker_id"]).fillna(False).astype(bool)
        & (d["out_dismissal_type"] != "Retire Out").fillna(True).astype(bool)
    )
    d["dismissal"] = dis.astype(float)
    d["_src_index"] = d.index
    return d


def bowler_frame(df: pd.DataFrame) -> pd.DataFrame:
    """One row per delivery charged to the bowler (all rows except Penalty; wides included)."""
    m = df["base_pop"] & (df["den_bowler_counts_row"] == 1) & df["bowler_id"].notna()
    d = df.loc[m].copy()
    d["player_id"] = d["bowler_id"].astype("int64")
    d["charged"] = d["den_bowler_charged_runs"].astype(float)
    d["wkt"] = d["den_bowler_credited_wicket"].astype(float)
    legal = d["den_legal_inc"] == 1
    d["dot"] = (legal & (d["out_runs_row"] == 0)).astype(float)
    d["boundary"] = (d["out_is_four"].fillna(False) | d["out_is_six"].fillna(False)).astype(float)
    d["_src_index"] = d.index
    return d


def _codes(*cols: pd.Series) -> np.ndarray:
    key = cols[0].astype(str)
    for c in cols[1:]:
        key = key + "|" + c.astype(str)
    return pd.factorize(key, sort=True)[0]


def level_codes(d: pd.DataFrame, pressure: np.ndarray | None = None) -> list[np.ndarray]:
    comp, role, ph, wb = d["competition_type"], d["role_ctx"], d["innings_phase"], d["wbin"]
    levels = [_codes(comp, role, ph, wb), _codes(comp, role, ph), _codes(comp, role), _codes(comp)]
    if pressure is not None:
        levels = [_codes(comp, role, ph, wb, pd.Series(pressure, index=d.index))] + levels
    return levels


# ---------------------------------------------------------------- core estimator
def _kish_per_cell(c: np.ndarray, inn: np.ndarray, K: int) -> tuple[np.ndarray, np.ndarray]:
    """Per cell: Kish effective number of innings and number of distinct innings."""
    NI = int(inn.max()) + 1
    pair = np.bincount(c.astype(np.int64) * NI + inn, minlength=K * NI).reshape(K, NI)
    pair = pair.astype(float)
    tot = pair.sum(1)
    sq = (pair**2).sum(1)
    kish = np.where(sq > 0, tot**2 / np.where(sq > 0, sq, 1), 0.0)
    return kish, (pair > 0).sum(1).astype(float)


def expected_values(
    y: np.ndarray,
    levels: list[np.ndarray],
    inn: np.ndarray,
    excl: np.ndarray | None,
    binary: bool,
    min_cell_innings: int = 30,
    tau2_floor: float = 0.01,
) -> dict[str, Any]:
    """Hierarchical shrunk cell expectation for every row.

    excl: group code left out of every cell sum (player code or match code), or None (pooled).
    Returns expected, level_used (index into `levels`), floor_hit (at the level used),
    raw_cell_mean (unshrunk pooled finest-cell mean), parent diagnostics and median k per level.
    NULL handling: a cell left empty by the leave-out takes its parent value (n_eff = 0).
    """
    y = np.asarray(y, dtype=float)
    nL = len(levels)
    N = len(y)
    stats = []
    for c in levels:
        K = int(c.max()) + 1
        n = np.bincount(c, minlength=K).astype(float)
        s = np.bincount(c, weights=y, minlength=K)
        s2 = np.bincount(c, weights=y * y, minlength=K)
        kish, distinct = _kish_per_cell(c, inn, K)
        if excl is not None:
            G = int(excl.max()) + 1
            pair = c.astype(np.int64) * G + excl
            ng = np.bincount(pair, minlength=K * G).astype(float)[pair]
            sg = np.bincount(pair, weights=y, minlength=K * G)[pair]
        else:
            ng = np.zeros(N)
            sg = np.zeros(N)
        n_loo = n[c] - ng
        s_loo = s[c] - sg
        with np.errstate(invalid="ignore", divide="ignore"):
            mean_loo = np.where(n_loo > 0, s_loo / np.where(n_loo > 0, n_loo, 1), np.nan)
            neff_loo = np.where(n[c] > 0, kish[c] * n_loo / np.where(n[c] > 0, n[c], 1), 0.0)
        stats.append({"c": c, "K": K, "n": n, "s": s, "s2": s2, "kish": kish,
                      "distinct": distinct, "n_loo": n_loo, "mean_loo": mean_loo,
                      "neff_loo": neff_loo})  # fmt: skip
    # k per child cell from its parent's children (FULL_SAMPLE hyperparameter)
    ks, floor_hits, parents_info = [], [], []
    for li in range(nL):
        st = stats[li]
        if li == nL - 1:
            ks.append(np.zeros(st["K"]))
            floor_hits.append(np.zeros(st["K"], dtype=bool))
            parents_info.append({"parents": 0, "floor_hit_parents": 0})
            continue
        par = np.zeros(st["K"], dtype=np.int64)
        par[st["c"]] = stats[li + 1]["c"]
        k_arr = np.full(st["K"], 1.0 / tau2_floor)
        hit = np.zeros(st["K"], dtype=bool)
        n_parents = hit_parents = 0
        for p in np.unique(par[st["n"] > 0]):
            ch = np.where((par == p) & (st["n"] > 0))[0]
            mean = st["s"][ch] / st["n"][ch]
            ss = st["s2"][ch] - st["s"][ch] ** 2 / st["n"][ch]
            kk = k_from_children(st["n"][ch], st["kish"][ch], mean, ss, tau2_floor)
            k_arr[ch] = kk["k"]
            hit[ch] = kk["shrinkage_floor_hit"]
            n_parents += 1
            hit_parents += int(kk["shrinkage_floor_hit"])
        ks.append(k_arr)
        floor_hits.append(hit)
        parents_info.append({"parents": n_parents, "floor_hit_parents": hit_parents})
    # recursion from the coarsest level
    v: list[np.ndarray] = [np.empty(0)] * nL
    v[-1] = stats[-1]["mean_loo"]
    for li in range(nL - 2, -1, -1):
        st = stats[li]
        k = ks[li][st["c"]]
        if binary:
            sc = np.where(np.isfinite(st["mean_loo"]), st["mean_loo"], 0.0)
            v[li] = beta_binomial_shrink(
                sc * st["n_loo"], st["n_loo"], st["neff_loo"], v[li + 1], k
            )
        else:
            v[li] = shrink_to_parent(st["neff_loo"], st["mean_loo"], v[li + 1], k)
    # level used: finest level whose cell has at least min_cell_innings distinct innings
    chosen = np.full(N, nL - 1)
    done = np.zeros(N, dtype=bool)
    for li in range(nL):
        ok = stats[li]["distinct"][stats[li]["c"]] >= min_cell_innings
        take = ok & ~done
        chosen[take] = li
        done |= take
    exp = np.choose(chosen, v)
    fl = np.choose(chosen, [floor_hits[li][stats[li]["c"]] for li in range(nL)])
    n0 = stats[0]["n"][stats[0]["c"]]
    raw = stats[0]["s"][stats[0]["c"]] / np.where(n0 > 0, n0, 1)
    kmed = [float(np.median(k[k > 0])) if (k > 0).any() else float("nan") for k in ks]
    return {"expected": exp, "level_used": chosen, "floor_hit": fl.astype(bool),
            "raw_cell_mean": raw, "parents_info": parents_info, "k_by_level": kmed}  # fmt: skip


def build_stream(
    d: pd.DataFrame, stream: str, binary: bool, params: dict, pressure: np.ndarray | None = None
) -> dict[str, Any]:
    """Pooled, leave-player-out and leave-match-out expectations for one outcome stream."""
    y = d[stream].to_numpy(dtype=float)
    lv = level_codes(d, pressure)
    inn = pd.factorize(d["inn_key"])[0]
    pl = pd.factorize(d["competition_type"] + "|" + d["player_id"].astype(str))[0]
    mt = pd.factorize(d["match_id"])[0]
    kw = {"min_cell_innings": params["min_cell_innings"], "tau2_floor": params["tau2_floor"]}
    return {
        "pooled": expected_values(y, lv, inn, None, binary, **kw),
        "leave_player_out": expected_values(y, lv, inn, pl, binary, **kw),
        "leave_match_out": expected_values(y, lv, inn, mt, binary, **kw),
        "y": y,
        "levels": lv,
        "n_levels": len(lv),
    }


# ---------------------------------------------------------------- diagnostics
def calibration(y: np.ndarray, raw_cell_mean: np.ndarray, level0: np.ndarray) -> dict[str, float]:
    """Calibration identity: inside every finest cell sum(actual) == sum(raw cell mean)."""
    K = int(level0.max()) + 1
    diff = np.bincount(level0, weights=y - raw_cell_mean, minlength=K)
    return {"max_abs_cell_residual": float(np.abs(diff).max()), "cells": int(K),
            "total_residual": float(diff.sum())}  # fmt: skip


def stream_summary(res: dict[str, Any], names: list[str]) -> dict[str, Any]:
    y = res["y"]
    out: dict[str, Any] = {"n": int(len(y)), "actual_mean": float(y.mean())}
    out["calibration_identity"] = calibration(y, res["pooled"]["raw_cell_mean"], res["levels"][0])
    for tag in ("pooled", "leave_player_out", "leave_match_out"):
        e = res[tag]["expected"]
        lvl = res[tag]["level_used"]
        counts = {names[i] if i < len(names) else str(i): int((lvl == i).sum())
                  for i in range(res["n_levels"])}  # fmt: skip
        out[tag] = {
            "expected_mean": float(np.nanmean(e)), "expected_min": float(np.nanmin(e)),
            "expected_max": float(np.nanmax(e)), "n_nan": int(np.isnan(e).sum()),
            "total_actual_minus_expected": float(np.nansum(y - e)),
            "mean_abs_diff_vs_pooled": float(np.nanmean(np.abs(e - res["pooled"]["expected"]))),
            "exp_cell_level_used": counts,
            "shrinkage_floor_hit_rows": int(res[tag]["floor_hit"].sum()),
            "parents_info": res[tag]["parents_info"],
            "k_median_by_level": res[tag]["k_by_level"],
        }  # fmt: skip
    return out


# ---------------------------------------------------------------- players
def player_match_stats(d: pd.DataFrame, resid: np.ndarray, mask: np.ndarray) -> pd.DataFrame:
    """Per (comp, player, match) sufficient statistics of residuals in the masked rows."""
    t = pd.DataFrame({"comp": d["competition_type"].to_numpy()[mask],
                      "player_id": d["player_id"].to_numpy()[mask],
                      "match_id": d["match_id"].to_numpy()[mask], "r": resid[mask]})  # fmt: skip
    t["r2"] = t["r"] ** 2
    t["n"] = 1
    return t.groupby(["comp", "player_id", "match_id"], as_index=False).agg(
        n=("n", "sum"), s=("r", "sum"), s2=("r2", "sum")
    )


def shrink_players(
    n: np.ndarray, s: np.ndarray, s2: np.ndarray, target: str = "pooled_other"
) -> dict[str, np.ndarray]:
    """Shrunk mean residual per player.

    Target 'pooled_other': pooled mean residual of all OTHER players (FULL_SAMPLE, descriptive;
    strictly prior when used predictively). Target 'zero': the named sensitivity. k comes from the
    method-of-moments prior of eb_shrink. Players with n = 0 get NaN (never a fabricated value).
    """
    n = np.asarray(n, float)
    s = np.asarray(s, float)
    eb = eb_shrink(n, s, np.asarray(s2, float))
    k = float(eb["k"])
    raw = np.where(n > 0, s / np.where(n > 0, n, 1), np.nan)
    if target == "zero":
        tgt = np.zeros_like(n)
    else:
        tgt = pooled_other_mean(float(s.sum()), float(n.sum()), s, n)
    est = shrink_to_parent(n, np.nan_to_num(raw), tgt, k)
    return {"raw": raw, "shrunk": np.where(n > 0, est, np.nan), "target": tgt, "k": k}


def bootstrap_by_match(ps: pd.DataFrame, n_boot: int, seed: int) -> dict[str, Any]:
    """Bootstrap matches (stratified by format, fixed seed) with the baseline held fixed.

    ps: per (comp, player, match) sufficient statistics (n, s, s2). Players are keyed by
    (comp, player_id). The shrinkage prior is re-estimated in each resample.
    """
    rng = np.random.default_rng(seed)
    pid, plabels = pd.factorize(ps["comp"] + "|" + ps["player_id"].astype(str), sort=True)
    mid, mlabels = pd.factorize(ps["comp"] + "|" + ps["match_id"].astype(str), sort=True)
    P, M = len(plabels), len(mlabels)
    N, S, S2 = np.zeros((P, M)), np.zeros((P, M)), np.zeros((P, M))
    np.add.at(N, (pid, mid), ps["n"].to_numpy(float))
    np.add.at(S, (pid, mid), ps["s"].to_numpy(float))
    np.add.at(S2, (pid, mid), ps["s2"].to_numpy(float))
    comp_of_m = np.array([x.split("|")[0] for x in mlabels])
    comp_of_p = np.array([x.split("|")[0] for x in plabels])
    W = np.zeros((n_boot, M))
    for comp in np.unique(comp_of_m):
        idx = np.where(comp_of_m == comp)[0]
        draws = rng.integers(0, len(idx), size=(n_boot, len(idx)))
        for b in range(n_boot):
            W[b, idx] = np.bincount(draws[b], minlength=len(idx))
    est = np.full((P, n_boot), np.nan)
    full = np.full(P, np.nan)
    for comp in np.unique(comp_of_p):
        rows = np.where(comp_of_p == comp)[0]
        nb, sb, s2b = N[rows] @ W.T, S[rows] @ W.T, S2[rows] @ W.T
        for b in range(n_boot):
            est[rows, b] = shrink_players(nb[:, b], sb[:, b], s2b[:, b])["shrunk"]
        full[rows] = shrink_players(N[rows].sum(1), S[rows].sum(1), S2[rows].sum(1))["shrunk"]
    with np.errstate(all="ignore"):
        lo = np.nanpercentile(est, 2.5, axis=1)
        hi = np.nanpercentile(est, 97.5, axis=1)
    return {"players": plabels, "n": N.sum(1), "matches": (N > 0).sum(1), "shrunk": full,
            "lo": lo, "hi": hi, "n_boot": n_boot, "seed": seed,
            "present_share": np.isfinite(est).mean(1), "draws": est}  # fmt: skip
