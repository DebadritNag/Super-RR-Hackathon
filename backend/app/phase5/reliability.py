"""Phase 5 reliability investigation: variance decomposition, split-half reliability, projections.

Everything here is DESCRIPTIVE and EXPERIMENTAL_NOT_VALIDATED. It works on player x match matrices
of residual sufficient statistics (balls ``N``, residual sums ``S``, squared residual sums ``S2``)
built from PRE_TEST rows (TRAIN and VALIDATION). Nothing here reads TEST rows or Cricsheet.

Three noise bases are reported side by side because the choice decides whether a between-player
variance is detectable at all:

* ``phase4_kish``: sigma2_within / n_eff_kish, the Phase 4 estimator as implemented. n_eff_kish is
  an equal-weight MATCH count, so this divides a per-ball variance by a per-match count.
* ``ball_independent``: sigma2_within / n_balls, which assumes independent balls.
* ``match_cluster``: cluster-robust variance of the player mean with matches as clusters, which
  keeps within-match dependence.

Where an estimate cannot be supported the value is ``NOT_ESTIMABLE`` or a status string; nothing
is fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.phase4 import engine as en

NOT_ESTIMABLE = "NOT_ESTIMABLE"
BETWEEN_NOT_POSITIVE = "BETWEEN_VARIANCE_NOT_POSITIVE"
ESTIMATED = "ESTIMATED"
BASES = ("phase4_kish", "ball_independent", "match_cluster")
LABEL = "DESCRIPTIVE_EXPERIMENTAL_NOT_VALIDATED"


# ---------------------------------------------------------------- data container
@dataclass
class CellData:
    """Player x match matrices of one (format, role, stream) pressure cell, matches by date."""

    players: np.ndarray
    match_ids: np.ndarray
    dates: np.ndarray
    period: np.ndarray
    N: np.ndarray
    S: np.ndarray
    S2: np.ndarray

    def select_cols(self, cols: np.ndarray) -> CellData:
        return CellData(self.players, self.match_ids[cols], self.dates[cols], self.period[cols],
                        self.N[:, cols], self.S[:, cols], self.S2[:, cols])  # fmt: skip

    def select_players(self, rows: np.ndarray) -> CellData:
        return CellData(self.players[rows], self.match_ids, self.dates, self.period,
                        self.N[rows], self.S[rows], self.S2[rows])  # fmt: skip

    @property
    def total_balls(self) -> np.ndarray:
        return self.N.sum(1)


def from_cell(cell: en.Cell) -> CellData:
    """Matrices of a Phase 4 ``Cell`` including the squared-residual sums ``S2``."""
    ms = cell.ms
    pi = pd.Index(cell.players).get_indexer(ms["player_id"])
    mi = pd.Index(cell.matches).get_indexer(ms["match_id"])
    S2 = np.zeros_like(cell.N)
    np.add.at(S2, (pi, mi), ms["s2"].to_numpy(float))
    dates = cell.rows.groupby("match_id")["date"].first().reindex(cell.matches).to_numpy()
    return CellData(cell.players, cell.matches, dates, cell.match_period, cell.N.copy(),
                    cell.S.copy(), S2)  # fmt: skip


def window_cols(cd: CellData, window: str) -> np.ndarray:
    if window == "TRAIN":
        return cd.period == "TRAIN"
    if window == "PRE_TEST":
        return np.isin(cd.period, ["TRAIN", "VALIDATION"])
    raise ValueError(f"unknown window '{window}'")


# ---------------------------------------------------------------- moments and decomposition
@dataclass
class Moments:
    n: np.ndarray
    mean: np.ndarray
    ssw: np.ndarray
    n2: np.ndarray
    m: np.ndarray
    c2: np.ndarray


def boot_moments(cd: CellData, w: np.ndarray) -> Moments:
    """Weighted player statistics for match weights ``w`` of shape (matches, draws)."""
    N, S, S2 = cd.N, cd.S, cd.S2
    n, s, ss, n2 = N @ w, S @ w, S2 @ w, (N * N) @ w
    m = (N > 0).astype(float) @ w
    cross, s2m = (S * N) @ w, (S * S) @ w
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n > 0, s / np.where(n > 0, n, 1.0), np.nan)
        ssw = np.maximum(ss - np.where(n > 0, s * s / np.where(n > 0, n, 1.0), 0.0), 0.0)
        c2 = s2m - 2.0 * mean * cross + mean**2 * n2
    return Moments(n, mean, ssw, n2, m, c2)


def _masked_mean_var(x: np.ndarray, ok: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p = ok.sum(0).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = np.where(p > 0, np.where(ok, x, 0.0).sum(0) / np.where(p > 0, p, 1.0), np.nan)
        dev = np.where(ok, x - mu, 0.0)
        var = np.where(p > 1, (dev**2).sum(0) / np.where(p > 1, p - 1.0, 1.0), np.nan)
    return p, mu, var


def decompose_moments(mo: Moments, min_balls: int) -> dict[str, np.ndarray]:
    """Between-player variance, noise, SNR and ICC per draw for the three noise bases."""
    valid = (mo.n >= max(1, min_balls)) & np.isfinite(mo.mean)
    with np.errstate(invalid="ignore", divide="ignore"):
        neff = np.where(mo.n2 > 0, mo.n**2 / np.where(mo.n2 > 0, mo.n2, 1.0), 0.0)
        dof = (mo.n * valid).sum(0) - valid.sum(0)
        sigma2 = np.where(dof > 0, (mo.ssw * valid).sum(0) / np.where(dof > 0, dof, 1.0), np.nan)
        nz = {
            "phase4_kish": np.where(neff > 0, sigma2 / np.where(neff > 0, neff, 1.0), np.nan),
            "ball_independent": np.where(mo.n > 0, sigma2 / np.where(mo.n > 0, mo.n, 1.0), np.nan),
            "match_cluster": np.where(
                mo.m >= 2,
                mo.m
                / np.where(mo.m >= 2, mo.m - 1.0, 1.0)
                * np.maximum(mo.c2, 0.0)
                / np.where(mo.n > 0, mo.n**2, 1.0),
                np.nan,
            ),
        }
    out: dict[str, np.ndarray] = {"sigma2": sigma2, "players_valid": valid.sum(0), "mean": mo.mean}
    for b, noise in nz.items():
        ok = valid & np.isfinite(noise)
        p, _, var = _masked_mean_var(mo.mean, ok)
        with np.errstate(invalid="ignore", divide="ignore"):
            nm = np.where(p > 0, np.where(ok, noise, 0.0).sum(0) / np.where(p > 0, p, 1.0), np.nan)
            tau2 = var - nm
            snr = np.where(nm > 0, tau2 / np.where(nm > 0, nm, 1.0), np.nan)
            tpos = np.where(np.isfinite(tau2), np.maximum(tau2, 0.0), np.nan)
            icc = np.where(nm + tpos > 0, tpos / np.where(nm + tpos > 0, nm + tpos, 1.0), np.nan)
            sig_eff = np.where(ok, noise * mo.n, 0.0).sum(0) / np.where(p > 0, p, 1.0)
        sig_eff = sig_eff if b == "match_cluster" else sigma2
        out.update({f"{b}_players": p, f"{b}_var_means": var, f"{b}_noise_mean": nm,
                    f"{b}_tau2": tau2, f"{b}_snr": snr, f"{b}_icc": icc,
                    f"{b}_sigma_eff": sig_eff, f"{b}_noise_i": noise, f"{b}_ok": ok})  # fmt: skip
    return out


def reml_tau2(
    y: np.ndarray, v0: np.ndarray, max_iter: int = 500, tol: float = 1e-8
) -> dict[str, Any]:
    """REML estimate of the between-player variance with known per-player noise ``v0``.

    Fisher scoring with the boundary at zero. ``converged`` is False when ``max_iter`` is hit.
    """
    y, v0 = np.asarray(y, float), np.asarray(v0, float)
    ok = np.isfinite(y) & np.isfinite(v0) & (v0 > 0)
    y, v0 = y[ok], v0[ok]
    if len(y) < 3:
        return {"tau2": float("nan"), "converged": False, "iterations": 0, "players": int(len(y))}
    vy = float(np.var(y, ddof=1))
    tau2 = max(vy - float(v0.mean()), 0.0) + 1e-3 * vy
    cap = 10.0 * max(vy, 1e-12)
    for it in range(1, max_iter + 1):
        w = 1.0 / (tau2 + v0)
        sw = w.sum()
        mu = float((w * y).sum() / sw)
        score = -0.5 * (sw - (w**2).sum() / sw) + 0.5 * float(((w * (y - mu)) ** 2).sum())
        info = 0.5 * ((w**2).sum() - 2.0 * (w**3).sum() / sw + (w**2).sum() ** 2 / sw**2)
        if not info > 0:
            return {"tau2": float(tau2), "converged": False, "iterations": it, "players": len(y)}
        new = min(max(tau2 + score / info, 0.0), cap)
        done = abs(new - tau2) <= tol * (1.0 + tau2)
        tau2 = new
        if done:
            return {"tau2": float(tau2), "converged": True, "iterations": it, "players": len(y)}
    return {"tau2": float(tau2), "converged": False, "iterations": max_iter, "players": len(y)}


def _ci(x: np.ndarray) -> tuple[float | None, float | None]:
    x = x[np.isfinite(x)]
    if x.size < 20:
        return None, None
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def _f(x: Any) -> float | None:
    x = float(x)
    return x if np.isfinite(x) else None


def variance_rows(
    cd: CellData, w: np.ndarray, window: str, min_balls_list: list[int]
) -> list[dict[str, Any]]:
    """One row per (min_balls, noise basis): point estimate, REML cross-check, bootstrap CIs."""
    cols = window_cols(cd, window)
    sub, ws = cd.select_cols(cols), w[cols]
    if sub.N.shape[1] == 0 or sub.N.shape[0] == 0:
        return []
    pt = boot_moments(sub, np.ones((sub.N.shape[1], 1)))
    bt = boot_moments(sub, ws)
    rows: list[dict[str, Any]] = []
    for mb in min_balls_list:
        dp, db = decompose_moments(pt, mb), decompose_moments(bt, mb)
        for b in BASES:
            tau2 = float(dp[f"{b}_tau2"][0])
            nm = float(dp[f"{b}_noise_mean"][0])
            ok = dp[f"{b}_ok"][:, 0]
            reml = reml_tau2(dp["mean"][ok, 0], dp[f"{b}_noise_i"][ok, 0])
            t_lo, t_hi = _ci(db[f"{b}_tau2"])
            s_lo, s_hi = _ci(db[f"{b}_snr"])
            i_lo, i_hi = _ci(db[f"{b}_icc"])
            fin = db[f"{b}_tau2"][np.isfinite(db[f"{b}_tau2"])]
            if not np.isfinite(tau2):
                status = NOT_ESTIMABLE
            elif tau2 <= 0:
                status = BETWEEN_NOT_POSITIVE
            else:
                status = ESTIMATED
            rows.append(
                {
                    "window": window, "min_balls": mb, "noise_basis": b,
                    "players": int(dp[f"{b}_players"][0]),
                    "sigma2_within": _f(dp["sigma2"][0]),
                    "var_of_player_means": _f(dp[f"{b}_var_means"][0]),
                    "mean_noise_variance": _f(nm),
                    "tau2_moment": _f(tau2), "snr": _f(dp[f"{b}_snr"][0]),
                    "icc_truncated_at_0": _f(dp[f"{b}_icc"][0]), "status": status,
                    "sigma_eff_for_projection": _f(dp[f"{b}_sigma_eff"][0]),
                    "tau2_reml": _f(reml["tau2"]), "reml_converged": bool(reml["converged"]),
                    "reml_iterations": int(reml["iterations"]),
                    "tau2_boot_lo": t_lo, "tau2_boot_hi": t_hi,
                    "tau2_boot_p90": float(np.percentile(fin, 90)) if fin.size >= 20 else None,
                    "snr_boot_lo": s_lo, "snr_boot_hi": s_hi,
                    "icc_boot_lo": i_lo, "icc_boot_hi": i_hi,
                    "boot_share_tau2_positive": float((fin > 0).mean()) if fin.size else None,
                    "label": LABEL,
                }
            )  # fmt: skip
    return rows


def _split_cov_stats(h: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Signal and noise implied by the covariance of odd/even half means (no noise model)."""
    tau2 = h["cov"]
    noise_half = 0.5 * (h["var1"] + h["var2"]) - h["cov"]
    with np.errstate(invalid="ignore", divide="ignore"):
        snr = np.where(noise_half > 0, tau2 / np.where(noise_half > 0, noise_half, 1.0), np.nan)
        tpos = np.where(np.isfinite(tau2), np.maximum(tau2, 0.0), np.nan)
        full_noise = noise_half / 2.0
        icc = np.where(
            full_noise + tpos > 0,
            tpos / np.where(full_noise + tpos > 0, full_noise + tpos, 1.0),
            np.nan,
        )
    return {"tau2": tau2, "noise_half": noise_half, "snr": snr, "icc": icc,
            "sigma_eff": noise_half * h["n_half"]}  # fmt: skip


def split_cov_rows(
    cd: CellData, w: np.ndarray, window: str, min_balls_list: list[int]
) -> list[dict[str, Any]]:
    """Fourth noise basis: tau2 = covariance of odd/even half means (model-free, no sigma2).

    SNR here is signal over the noise variance of a HALF-window mean; ICC refers to the full
    window mean (noise halves when the sample doubles). ``sigma_eff_for_projection`` is the
    approximate per-ball noise scale (half-mean noise times the mean half sample size).
    """
    cols = window_cols(cd, window)
    sub, ws = cd.select_cols(cols), w[cols]
    if sub.N.shape[0] == 0 or sub.N.shape[1] == 0:
        return []
    A, B = half_masks(sub.N > 0, "odd_even")
    one = np.ones((sub.N.shape[1], 1))
    rows = []
    for mb in min_balls_list:
        half_min = max(1, mb // 2)
        pt = _split_cov_stats(half_stats(sub.N, sub.S, A, B, one, half_min))
        hb = half_stats(sub.N, sub.S, A, B, ws, half_min)
        bt = _split_cov_stats(hb)
        n_pl = int(half_stats(sub.N, sub.S, A, B, one, half_min)["n"][0])
        tau2 = float(pt["tau2"][0])
        t_lo, t_hi = _ci(bt["tau2"])
        s_lo, s_hi = _ci(bt["snr"])
        i_lo, i_hi = _ci(bt["icc"])
        fin = bt["tau2"][np.isfinite(bt["tau2"])]
        status = NOT_ESTIMABLE if not np.isfinite(tau2) or n_pl < 10 else (
            BETWEEN_NOT_POSITIVE if tau2 <= 0 else ESTIMATED
        )  # fmt: skip
        rows.append(
            {
                "window": window, "min_balls": mb, "noise_basis": "split_half_covariance",
                "players": n_pl, "sigma2_within": None, "var_of_player_means": None,
                "mean_noise_variance": _f(pt["noise_half"][0]), "tau2_moment": _f(tau2),
                "snr": _f(pt["snr"][0]), "icc_truncated_at_0": _f(pt["icc"][0]), "status": status,
                "sigma_eff_for_projection": _f(pt["sigma_eff"][0]), "tau2_reml": None,
                "reml_converged": None, "reml_iterations": None,
                "tau2_boot_lo": t_lo, "tau2_boot_hi": t_hi,
                "tau2_boot_p90": float(np.percentile(fin, 90)) if fin.size >= 20 else None,
                "snr_boot_lo": s_lo, "snr_boot_hi": s_hi, "icc_boot_lo": i_lo, "icc_boot_hi": i_hi,
                "boot_share_tau2_positive": float((fin > 0).mean()) if fin.size else None,
                "label": LABEL,
            }
        )  # fmt: skip
    return rows


# ---------------------------------------------------------------- split-half reliability
def half_masks(
    present: np.ndarray, mode: str, rng: np.random.Generator | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Two disjoint half masks over each player's present matches (chronological columns)."""
    cs = np.cumsum(present, axis=1)
    m = present.sum(1, keepdims=True)
    if mode == "odd_even":
        return present & (cs % 2 == 1), present & (cs % 2 == 0)
    if mode == "early_late":
        h = m // 2
        return present & (cs <= h), present & (cs > m - h)
    if mode == "random":
        if rng is None:
            raise ValueError("random mode needs a generator")
        u = np.where(present, rng.random(present.shape), np.inf)
        rank = np.argsort(np.argsort(u, axis=1, kind="stable"), axis=1, kind="stable")
        h = m // 2
        return present & (rank < h), present & (rank >= h) & (rank < 2 * h)
    raise ValueError(f"unknown split mode '{mode}'")


def sb(r: np.ndarray | float) -> np.ndarray:
    """Spearman-Brown corrected correlation 2r / (1 + r)."""
    r = np.asarray(r, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(r > -1.0, 2.0 * r / (1.0 + r), np.nan)


def half_stats(
    N: np.ndarray, S: np.ndarray, A: np.ndarray, B: np.ndarray, w: np.ndarray, min_balls: int
) -> dict[str, np.ndarray]:
    """Half means and the correlations between them for weights ``w`` (matches, draws)."""
    n1, s1, n2, s2 = (N * A) @ w, (S * A) @ w, (N * B) @ w, (S * B) @ w
    ok = (n1 >= min_balls) & (n2 >= min_balls) & (n1 > 0) & (n2 > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        m1 = np.where(n1 > 0, s1 / np.where(n1 > 0, n1, 1.0), np.nan)
        m2 = np.where(n2 > 0, s2 / np.where(n2 > 0, n2, 1.0), np.nan)
    p = ok.sum(0).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        q = np.where(p > 1, p - 1.0, np.nan)
        mu1 = np.where(ok, m1, 0.0).sum(0) / np.where(p > 0, p, np.nan)
        mu2 = np.where(ok, m2, 0.0).sum(0) / np.where(p > 0, p, np.nan)
        d1, d2 = np.where(ok, m1 - mu1, 0.0), np.where(ok, m2 - mu2, 0.0)
        cov, v1, v2 = (d1 * d2).sum(0) / q, (d1**2).sum(0) / q, (d2**2).sum(0) / q
        n_half = (np.where(ok, 0.5 * (n1 + n2), 0.0).sum(0)) / np.where(p > 0, p, np.nan)
    return {"m1": m1, "m2": m2, "ok": ok, "pearson": en.masked_pearson(m1, m2, ok),
            "spearman": en.masked_spearman(m1, m2, ok), "n": ok.sum(0),
            "cov": cov, "var1": v1, "var2": v2, "n_half": n_half}  # fmt: skip


def split_half(
    cd: CellData,
    window: str,
    mode: str,
    min_balls_per_half: int,
    w: np.ndarray | None,
    seed: int,
    n_random: int = 200,
    min_players: int = 10,
) -> dict[str, Any]:
    """Split-half reliability of the player mean residual (Spearman-Brown corrected).

    ``odd_even`` and ``early_late`` get match-bootstrap intervals from ``w`` (matches of ``cd`` by
    draws, full-width); ``random`` averages ``n_random`` seeded random splits and reports their SD.
    """
    cols = window_cols(cd, window)
    sub = cd.select_cols(cols)
    row: dict[str, Any] = {"window": window, "mode": mode, "min_balls_per_half": min_balls_per_half,
                           "label": LABEL}  # fmt: skip
    if sub.N.shape[0] == 0 or sub.N.shape[1] == 0:
        return {**row, "players": 0, "status": NOT_ESTIMABLE}
    present = sub.N > 0
    one = np.ones((sub.N.shape[1], 1))
    if mode == "random":
        rng = np.random.default_rng(seed)
        pe, sp, ns = [], [], []
        for _ in range(n_random):
            A, B = half_masks(present, mode, rng)
            h = half_stats(sub.N, sub.S, A, B, one, min_balls_per_half)
            pe.append(h["pearson"][0])
            sp.append(h["spearman"][0])
            ns.append(h["n"][0])
        pe, sp = np.asarray(pe), np.asarray(sp)
        good = np.isfinite(pe)
        n_pl = int(np.median(ns))
        est = bool(good.any() and n_pl >= min_players)
        return {**row, "players": n_pl, "status": ESTIMATED if est else NOT_ESTIMABLE,
                "r_pearson": _f(np.nanmean(pe)) if est else None,
                "r_spearman": _f(np.nanmean(sp)) if est else None,
                "sb_pearson": _f(sb(np.nanmean(pe))) if est else None,
                "sb_spearman": _f(sb(np.nanmean(sp))) if est else None,
                "sb_lo": None, "sb_hi": None, "split_sd_sb_pearson": _f(np.nanstd(sb(pe))) if est else None,
                "ci_note": "random mode: no bootstrap interval; SD across splits shown"}  # fmt: skip
    A, B = half_masks(present, mode)
    h = half_stats(sub.N, sub.S, A, B, one, min_balls_per_half)
    n_pl = int(h["n"][0])
    est = n_pl >= min_players and np.isfinite(h["pearson"][0])
    out = {**row, "players": n_pl, "status": ESTIMATED if est else NOT_ESTIMABLE}
    if not est:
        return {**out, "r_pearson": None, "r_spearman": None, "sb_pearson": None,
                "sb_spearman": None, "sb_lo": None, "sb_hi": None}  # fmt: skip
    out.update({"r_pearson": _f(h["pearson"][0]), "r_spearman": _f(h["spearman"][0]),
                "sb_pearson": _f(sb(h["pearson"][0])), "sb_spearman": _f(sb(h["spearman"][0]))})  # fmt: skip
    if w is not None:
        hb = half_stats(sub.N, sub.S, A, B, w[cols], min_balls_per_half)
        lo, hi = _ci(sb(hb["pearson"]))
        out.update({"sb_lo": lo, "sb_hi": hi})
    else:
        out.update({"sb_lo": None, "sb_hi": None})
    return out


def reliability_by_opportunity(
    cd: CellData,
    window: str,
    ladder: list[int],
    min_balls_per_half: int,
    w: np.ndarray | None,
    min_players: int = 10,
) -> list[dict[str, Any]]:
    """Odd/even reliability and cluster-basis SNR/ICC among players with at least ``t`` balls."""
    cols = window_cols(cd, window)
    sub = cd.select_cols(cols)
    rows = []
    for t in ladder:
        if t < 2 * min_balls_per_half:
            continue
        keep = sub.total_balls >= t
        row: dict[str, Any] = {"window": window, "min_total_balls": t, "players_ge_t": int(keep.sum()),
                               "label": LABEL}  # fmt: skip
        if keep.sum() < min_players:
            rows.append({**row, "status": NOT_ESTIMABLE})
            continue
        pl = sub.select_players(keep)
        full = CellData(pl.players, pl.match_ids, pl.dates, pl.period, pl.N, pl.S, pl.S2)
        res = split_half(full, "PRE_TEST" if window == "PRE_TEST" else "TRAIN", "odd_even",
                         min_balls_per_half, w[cols] if w is not None else None, 0, min_players=min_players)  # fmt: skip
        # split_half re-applies the window mask; the sub frame already holds window columns only
        mo = boot_moments(pl, np.ones((pl.N.shape[1], 1)))
        dec = decompose_moments(mo, t)
        rows.append(
            {**row, "status": res["status"], "players_split": res.get("players"),
             "sb_odd_even": res.get("sb_pearson"), "sb_lo": res.get("sb_lo"), "sb_hi": res.get("sb_hi"),
             "snr_match_cluster": _f(dec["match_cluster_snr"][0]),
             "icc_match_cluster": _f(dec["match_cluster_icc"][0]),
             "tau2_match_cluster": _f(dec["match_cluster_tau2"][0]),
             "snr_phase4_kish": _f(dec["phase4_kish_snr"][0])}
        )  # fmt: skip
    return rows


# ---------------------------------------------------------------- projections and simulation
def required_sample(
    tau2: float | None, sigma_eff: float | None, targets: tuple[float, ...], unit: str
) -> list[dict[str, Any]]:
    """n* = R / (1 - R) * sigma_eff / tau2. ``NOT_ESTIMABLE`` when tau2 is not positive."""
    out = []
    for r in targets:
        ok = tau2 is not None and sigma_eff is not None and np.isfinite(tau2) and tau2 > 0
        ok = bool(ok and np.isfinite(sigma_eff) and sigma_eff > 0)
        out.append(
            {
                "target_reliability": r,
                "unit": unit,
                "label": "DESCRIPTIVE_PROJECTION",
                "required_n": float(r / (1.0 - r) * sigma_eff / tau2) if ok else NOT_ESTIMABLE,
            }  # fmt: skip
        )
    return out


def simulate_detectability(
    noise: np.ndarray, sigma2: float, ratios: list[float], reps: int, seed: int
) -> list[dict[str, Any]]:
    """Could samples like the observed ones detect a between-player variance of a given size?

    For each true ratio tau2/sigma2, players get a true effect ~ N(0, tau2) plus noise with the
    OBSERVED per-player noise variance; the moment estimator is applied ``reps`` times.
    """
    noise = np.asarray(noise, float)
    noise = noise[np.isfinite(noise) & (noise > 0)]
    if noise.size < 5 or not np.isfinite(sigma2) or sigma2 <= 0:
        return [{"tau2_over_sigma2": r, "status": NOT_ESTIMABLE} for r in ratios]
    rng = np.random.default_rng(seed)
    out = []
    for r in ratios:
        tau2 = r * sigma2
        y = rng.normal(0.0, np.sqrt(tau2), (reps, noise.size)) + rng.normal(
            0.0, 1.0, (reps, noise.size)
        ) * np.sqrt(noise)
        est = y.var(axis=1, ddof=1) - noise.mean()
        out.append(
            {"tau2_over_sigma2": r, "true_tau2": float(tau2), "players": int(noise.size),
             "mean_noise_variance": float(noise.mean()),
             "true_icc": float(tau2 / (tau2 + noise.mean())),
             "share_estimate_positive": float((est > 0).mean()),
             "share_estimate_within_50pct_of_truth": float((np.abs(est - tau2) <= 0.5 * tau2).mean()),
             "mean_estimate": float(est.mean()), "reps": reps, "status": ESTIMATED,
             "label": "PARAMETRIC_SIMULATION_DESCRIPTIVE"}
        )  # fmt: skip
    return out


# ---------------------------------------------------------------- multi-format pooling
def pool_cells(
    a: CellData, b: CellData, window: str
) -> tuple[CellData, CellData, CellData, np.ndarray]:
    """Restrict two cells of the same role to players with balls in both formats and pool them.

    Returns (a_sub, b_sub, pooled, order) where ``order`` indexes the column-concatenation of the
    window columns of ``a`` then ``b`` into chronological order (use it to reorder weights).
    """
    ca, cb = window_cols(a, window), window_cols(b, window)
    a, b = a.select_cols(ca), b.select_cols(cb)
    common = np.intersect1d(a.players[a.total_balls > 0], b.players[b.total_balls > 0])
    a = a.select_players(np.isin(a.players, common))
    b = b.select_players(np.isin(b.players, common))
    ib = pd.Index(b.players).get_indexer(a.players)
    b = b.select_players(ib)
    dates = np.concatenate([a.dates, b.dates])
    mids = np.concatenate([a.match_ids, b.match_ids])
    order = np.lexsort((mids, dates))
    pooled = CellData(a.players, mids[order], dates[order],
                      np.concatenate([a.period, b.period])[order],
                      np.hstack([a.N, b.N])[:, order], np.hstack([a.S, b.S])[:, order],
                      np.hstack([a.S2, b.S2])[:, order])  # fmt: skip
    return a, b, pooled, order


def multi_format_pooling(
    a: CellData, b: CellData, window: str, min_balls_per_half: int, min_players: int = 10
) -> dict[str, Any]:
    """Pooled versus single-format odd/even reliability on the SAME players (descriptive)."""
    a_s, b_s, pooled, _ = pool_cells(a, b, window)
    row: dict[str, Any] = {"window": window, "players_in_both_formats": int(len(pooled.players)),
                           "label": LABEL}  # fmt: skip
    if len(pooled.players) < min_players:
        return {**row, "status": NOT_ESTIMABLE}
    halves = {}
    for name, cd in (("first_format", a_s), ("second_format", b_s), ("pooled", pooled)):
        A, B = half_masks(cd.N > 0, "odd_even")
        halves[name] = half_stats(cd.N, cd.S, A, B, np.ones((cd.N.shape[1], 1)), min_balls_per_half)
    common = np.logical_and.reduce([halves[k]["ok"][:, 0] for k in halves])
    row["players_qualifying_in_all_three"] = int(common.sum())
    if common.sum() < min_players:
        return {**row, "status": NOT_ESTIMABLE}
    for name, h in halves.items():
        r = en.masked_pearson(h["m1"], h["m2"], common[:, None])[0]
        row[f"sb_{name}"] = _f(sb(r))
    cd_sets = {"first_format": a_s, "second_format": b_s, "pooled": pooled}
    for name, cd in cd_sets.items():
        sub = cd.select_players(common)
        dec = decompose_moments(boot_moments(sub, np.ones((sub.N.shape[1], 1))), 1)
        row[f"snr_cluster_{name}"] = _f(dec["match_cluster_snr"][0])
        row[f"icc_cluster_{name}"] = _f(dec["match_cluster_icc"][0])
        row[f"snr_phase4_{name}"] = _f(dec["phase4_kish_snr"][0])
    return {**row, "status": ESTIMATED}
