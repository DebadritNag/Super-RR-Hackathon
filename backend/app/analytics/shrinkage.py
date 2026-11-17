"""Empirical-Bayes shrinkage of per-player rates and effective sample sizes."""

from __future__ import annotations

import numpy as np

TAU2_FLOOR = 1e-12


def eb_shrink(n, sum_x, sum_x2) -> dict:
    """Method-of-moments (DerSimonian-Laird form) shrinkage toward the pooled rate.

    Inputs are per-player arrays (players with n == 0 are ignored when estimating the prior and
    receive the pooled rate). Returns the prior parameters and per-player shrunk rate, n_eff and
    posterior sd. When the data cannot identify the prior (fewer than two players, no residual
    degrees of freedom), k = 0 and rates are left unshrunk.
    """
    n = np.asarray(n, dtype=float)
    sx = np.asarray(sum_x, dtype=float)
    sx2 = np.asarray(sum_x2, dtype=float)
    obs = n > 0
    P = int(obs.sum())
    N = float(n[obs].sum())
    out = {"players": P, "total_n": N, "mu0": float("nan"), "sigma2": float("nan")}
    if P == 0 or N <= 0:
        out.update(tau2=float("nan"), k=0.0, rate=np.full(n.shape, np.nan), n_eff=n * 0.0)
        out["post_sd"] = np.full(n.shape, np.nan)
        return out
    mu0 = float(sx[obs].sum() / N)
    r = np.zeros_like(n)
    r[obs] = sx[obs] / n[obs]
    dof = N - P
    if P >= 2 and dof > 0:
        sigma2 = max(0.0, float((sx2[obs].sum() - (n[obs] * r[obs] ** 2).sum()) / dof))
        q = float((n[obs] * (r[obs] - mu0) ** 2).sum())
        c = N - float((n[obs] ** 2).sum()) / N
        tau2 = max(TAU2_FLOOR, (q - (P - 1) * sigma2) / c) if c > 0 else TAU2_FLOOR
        k = sigma2 / tau2
    else:
        sigma2, tau2, k = (0.0 if dof <= 0 else float("nan")), float("nan"), 0.0
    rate = np.where(obs, (n * r + k * mu0) / np.where(n + k > 0, n + k, 1.0), mu0)
    out.update(mu0=mu0, sigma2=float(sigma2), tau2=float(tau2), k=float(k), rate=rate)
    out["n_eff"] = n_eff_shrink(n, k)
    out["post_sd"] = np.sqrt(max(sigma2, 0.0) if sigma2 == sigma2 else 0.0) / np.sqrt(
        np.where(n + k > 0, n + k, np.nan)
    )
    return out


def n_eff_shrink(n, k: float):
    """Data weight B = n/(n+k) times n, i.e. n^2/(n+k)."""
    n = np.asarray(n, dtype=float)
    denom = n + k
    return np.where(denom > 0, n * n / np.where(denom > 0, denom, 1.0), 0.0)


def n_eff_kish(per_match_n) -> float:
    """(sum n)^2 / sum n^2 over a player's matches (number of equally contributing matches)."""
    a = np.asarray(per_match_n, dtype=float)
    a = a[a > 0]
    if a.size == 0:
        return 0.0
    return float(a.sum() ** 2 / (a**2).sum())


def zscore_within(values) -> np.ndarray:
    """Population z-score (ddof=0); all zeros when the spread is zero or empty."""
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return v
    sd = v.std()
    if not np.isfinite(sd) or sd == 0:
        return np.zeros_like(v)
    return (v - v.mean()) / sd


def k_from_children(n, n_eff, mean, ss_within, tau2_floor: float = 0.01) -> dict:
    """Shrinkage strength k for children of one parent cell (method of moments).

    n: deliveries per child; n_eff: effective size per child; mean: child means;
    ss_within: within-child sums of squares. sigma2_within = sum(ss) / (sum(n) - children).
    between_moment = var(child means) - mean(sigma2_within / n_eff_child);
    tau2 = max(between_moment, tau2_floor * sigma2_within); k = sigma2_within / tau2, so k is at most
    1 / tau2_floor and a zero or negative moment gives the strongest shrinkage, never k = 0.
    """
    n = np.asarray(n, dtype=float)
    ne = np.asarray(n_eff, dtype=float)
    mu = np.asarray(mean, dtype=float)
    ss = np.asarray(ss_within, dtype=float)
    ok = (n > 0) & (ne > 0) & np.isfinite(mu)
    n, ne, mu, ss = n[ok], ne[ok], mu[ok], ss[ok]
    c = int(n.size)
    dof = float(n.sum()) - c
    sigma2 = float(ss.sum() / dof) if c > 0 and dof > 0 else 0.0
    if c < 2 or sigma2 <= 0:
        return {"k": 1.0 / tau2_floor, "tau2": float("nan"), "sigma2_within": sigma2,
                "between_moment": float("nan"), "children": c, "shrinkage_floor_hit": True}  # fmt: skip
    between = float(mu.var(ddof=1) - np.mean(sigma2 / ne))
    floor_abs = tau2_floor * sigma2
    tau2 = max(between, floor_abs)
    return {"k": float(sigma2 / tau2), "tau2": float(tau2), "sigma2_within": sigma2,
            "between_moment": between, "children": c, "shrinkage_floor_hit": bool(tau2 <= floor_abs)}  # fmt: skip


def shrink_to_parent(n_eff, cell_mean, parent_mean, k):
    """(n_eff * cell_mean + k * parent_mean) / (n_eff + k); equals the parent at n_eff = 0."""
    n_eff = np.asarray(n_eff, dtype=float)
    cm = np.asarray(cell_mean, dtype=float)
    pm = np.asarray(parent_mean, dtype=float)
    den = n_eff + k
    safe = np.where(den > 0, den, 1.0)
    cm0 = np.where(np.isfinite(cm), cm, 0.0)
    return np.where(den > 0, (n_eff * cm0 + k * pm) / safe, pm)


def beta_binomial_shrink(x, n, n_eff, parent_p, k):
    """Binary outcomes: counts scaled by the design effect n_eff / n, shrunk to the parent rate."""
    x = np.asarray(x, dtype=float)
    n = np.asarray(n, dtype=float)
    ne = np.asarray(n_eff, dtype=float)
    scale = np.where(n > 0, ne / np.where(n > 0, n, 1.0), 0.0)
    p = (x * scale + k * np.asarray(parent_p, dtype=float)) / np.where(ne + k > 0, ne + k, 1.0)
    return np.clip(p, 0.0, 1.0)


def pooled_other_mean(total_sum: float, total_n: float, own_sum, own_n):
    """Pooled mean of all OTHER players' observations (shrink target, FULL_SAMPLE descriptive)."""
    own_sum = np.asarray(own_sum, dtype=float)
    own_n = np.asarray(own_n, dtype=float)
    den = total_n - own_n
    return np.where(den > 0, (total_sum - own_sum) / np.where(den > 0, den, 1.0), np.nan)
