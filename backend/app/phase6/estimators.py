"""Between-player variance estimators and floor diagnostics (EXPERIMENTAL_NOT_VALIDATED).

Pure functions on arrays or on a Phase 5 ``CellData``. Every estimator returns a dict with
``value``, ``status``, ``converged`` and ``method``; statuses reuse the Phase 5 constants.
Nothing here reads TEST rows, Cricsheet or any file.

E1  moments with floor (Phase 4)            E4  beta-binomial (binary streams, sensitivity)
E1b moments, independent-ball noise         E5  gamma-Poisson (count streams, sensitivity)
E1c moments, match-cluster noise            E6  match-cluster bootstrap of E1c (``cluster_bootstrap``)
E2  REML normal-normal                      E7  split covariance (Phase 5 ``split_cov_rows``)
E3  ML normal-normal
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import optimize
from scipy.special import betaln, gammaln

from app.phase5 import reliability as rb
from app.phase5.reliability import BETWEEN_NOT_POSITIVE, ESTIMATED, NOT_ESTIMABLE

NOT_APPLICABLE = "NOT_APPLICABLE"
FLOOR = 0.01  # Phase 4 tau2 floor as a share of sigma2 (``k_from_children`` default)


def _res(value: float | None, status: str, converged: bool, method: str, **extra: Any) -> dict:
    v = None if value is None or not np.isfinite(value) else float(value)
    return {"value": v, "status": status, "converged": bool(converged), "method": method, **extra}


def _clean(y: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y, v = np.asarray(y, float), np.asarray(v, float)
    ok = np.isfinite(y) & np.isfinite(v) & (v > 0)
    return y[ok], v[ok]


# ---------------------------------------------------------------- E1: moments with floor
def tau2_moments_floor(
    mean: np.ndarray, noise: np.ndarray, sigma2: float, floor: float = FLOOR
) -> dict[str, Any]:
    """``between = var(mean) - mean(noise)``; ``tau2 = max(between, floor * sigma2)``.

    ``noise`` is the per-player sampling variance of a player mean on the chosen basis. With the
    Kish basis (noise = sigma2 / n_eff) this is the Phase 4 estimator. ``value`` is the floored
    tau2, ``between`` the raw moment (negative when the data show less spread than the noise).
    """
    y, v = _clean(mean, noise)
    if len(y) < 3 or not np.isfinite(sigma2) or sigma2 <= 0:
        return _res(None, NOT_ESTIMABLE, False, "moments_floor", between=None, floor_hit=None)
    between = float(np.var(y, ddof=1) - v.mean())
    floor_abs = floor * float(sigma2)
    tau2 = max(between, floor_abs)
    status = ESTIMATED if between > 0 else BETWEEN_NOT_POSITIVE
    return _res(tau2, status, True, "moments_floor", between=between,
                floor_hit=bool(between <= floor_abs), floor_abs=floor_abs)  # fmt: skip


# ---------------------------------------------------------------- E2 / E3: normal-normal
def tau2_reml(y: np.ndarray, v0: np.ndarray) -> dict[str, Any]:
    """REML estimate (delegates to the Phase 5 Fisher-scoring routine)."""
    r = rb.reml_tau2(y, v0)
    t = r["tau2"]
    if not np.isfinite(t):
        return _res(None, NOT_ESTIMABLE, False, "reml")
    status = ESTIMATED if t > 1e-12 else BETWEEN_NOT_POSITIVE
    return _res(t, status, r["converged"], "reml", iterations=int(r["iterations"]))


def tau2_ml(
    y: np.ndarray, v0: np.ndarray, max_iter: int = 500, tol: float = 1e-8
) -> dict[str, Any]:
    """Maximum-likelihood estimate of tau2 with known noise ``v0``, boundary at zero.

    Same Fisher scoring as REML without the ``sum(w)`` correction term, so it is biased
    downwards in small samples; it is shown next to REML, not instead of it.
    """
    y, v0 = _clean(y, v0)
    if len(y) < 3:
        return _res(None, NOT_ESTIMABLE, False, "ml", iterations=0)
    vy = float(np.var(y, ddof=1))
    tau2 = max(vy - float(v0.mean()), 0.0) + 1e-3 * vy
    cap = 10.0 * max(vy, 1e-12)
    for it in range(1, max_iter + 1):
        w = 1.0 / (tau2 + v0)
        mu = float((w * y).sum() / w.sum())
        score = -0.5 * float(w.sum()) + 0.5 * float(((w * (y - mu)) ** 2).sum())
        info = 0.5 * float((w**2).sum())
        new = min(max(tau2 + score / info, 0.0), cap)
        done = abs(new - tau2) <= tol * (1.0 + tau2)
        tau2 = new
        if done:
            status = ESTIMATED if tau2 > 1e-12 else BETWEEN_NOT_POSITIVE
            return _res(tau2, status, True, "ml", iterations=it)
    return _res(tau2, ESTIMATED if tau2 > 1e-12 else BETWEEN_NOT_POSITIVE, False, "ml",
                iterations=max_iter)  # fmt: skip


# ---------------------------------------------------------------- E4: beta-binomial
def _bb_nll(theta: np.ndarray, x: np.ndarray, n: np.ndarray) -> float:
    a, b = np.exp(theta[0]), np.exp(theta[1])
    ll = betaln(x + a, n - x + b) - betaln(a, b)  # binomial coefficient is constant in (a, b)
    return -float(ll.sum())


def tau2_beta_binomial(successes: np.ndarray, trials: np.ndarray) -> dict[str, Any]:
    """Marginal-likelihood fit of Beta(a, b); ``value`` is the variance of the success
    probability, ``a*b / ((a+b)^2 (a+b+1))``. Sensitivity only: it ignores within-match
    dependence, so it cannot be a verdict input.
    """
    x, n = np.asarray(successes, float), np.asarray(trials, float)
    ok = np.isfinite(x) & np.isfinite(n) & (n > 0) & (x >= 0) & (x <= n)
    x, n = x[ok], n[ok]
    if len(x) < 10 or x.sum() <= 0 or x.sum() >= n.sum():
        return _res(None, NOT_ESTIMABLE, False, "beta_binomial")
    p = x.sum() / n.sum()
    # start with a moderate overdispersion (a + b = 50) and let the likelihood decide
    start = np.log([p * 50.0, (1.0 - p) * 50.0])
    opt = optimize.minimize(_bb_nll, start, args=(x, n), method="L-BFGS-B",
                            bounds=[(-8.0, 22.0), (-8.0, 22.0)])  # fmt: skip
    a, b = float(np.exp(opt.x[0])), float(np.exp(opt.x[1]))
    tau2 = a * b / ((a + b) ** 2 * (a + b + 1.0))
    icc = 1.0 / (a + b + 1.0)
    at_bound = bool(opt.x.max() >= 21.9)
    # an a + b at the upper bound means the likelihood sees no overdispersion
    status = BETWEEN_NOT_POSITIVE if at_bound or icc < 1e-6 else ESTIMATED
    return _res(tau2, status, bool(opt.success), "beta_binomial", a=a, b=b,
                icc_between=icc, mean_p=a / (a + b))  # fmt: skip


# ---------------------------------------------------------------- E5: gamma-Poisson
def _gp_nll(theta: np.ndarray, c: np.ndarray, e: np.ndarray) -> float:
    a, th = np.exp(theta[0]), np.exp(theta[1])
    z = th * e
    ll = gammaln(c + a) - gammaln(a) - a * np.log1p(z) + c * (np.log(z) - np.log1p(z))
    return -float(ll.sum())


def tau2_gamma_poisson(counts: np.ndarray, exposure: np.ndarray) -> dict[str, Any]:
    """Marginal-likelihood fit of Poisson counts with a Gamma(shape a, scale theta) rate.

    ``value`` is the variance of the rate, ``a * theta^2``. Runs per ball are bounded and not
    Poisson, so on the runs streams the caller labels the result ``MISSPECIFIED_FOR_RUNS``.
    """
    c, e = np.asarray(counts, float), np.asarray(exposure, float)
    ok = np.isfinite(c) & np.isfinite(e) & (e > 0) & (c >= 0)
    c, e = c[ok], e[ok]
    if len(c) < 10 or c.sum() <= 0:
        return _res(None, NOT_ESTIMABLE, False, "gamma_poisson")
    rate = c.sum() / e.sum()
    start = np.log([4.0, rate / 4.0])
    opt = optimize.minimize(_gp_nll, start, args=(c, e), method="L-BFGS-B",
                            bounds=[(-8.0, 22.0), (-25.0, 8.0)])  # fmt: skip
    a, th = float(np.exp(opt.x[0])), float(np.exp(opt.x[1]))
    tau2 = a * th * th
    no_spread = opt.x[0] >= 21.9 or tau2 / max(rate * rate, 1e-300) < 1e-6
    status = BETWEEN_NOT_POSITIVE if no_spread else ESTIMATED
    return _res(tau2, status, bool(opt.success), "gamma_poisson", shape=a, scale=th,
                mean_rate=a * th)  # fmt: skip


# ---------------------------------------------------------------- E6: match-cluster bootstrap
def cluster_bootstrap(cd: rb.CellData, w: np.ndarray, min_balls: int = 1) -> dict[str, Any]:
    """Match-cluster bootstrap of the moment estimate on the Kish and match-cluster bases.

    ``w`` has shape (matches of ``cd``, draws). Returns median, 95% interval and the share of
    draws with a positive between variance for each basis.
    """
    if cd.N.shape[0] < 3 or cd.N.shape[1] < 2:
        return {b: _res(None, NOT_ESTIMABLE, False, "cluster_bootstrap") for b in rb.BASES}
    dec = rb.decompose_moments(rb.boot_moments(cd, w), min_balls)
    out = {}
    for b in rb.BASES:
        t = dec[f"{b}_tau2"]
        fin = t[np.isfinite(t)]
        if fin.size < 20:
            out[b] = _res(None, NOT_ESTIMABLE, False, "cluster_bootstrap", draws=int(fin.size))
            continue
        out[b] = _res(float(np.median(fin)), ESTIMATED, True, "cluster_bootstrap",
                      lo=float(np.percentile(fin, 2.5)), hi=float(np.percentile(fin, 97.5)),
                      share_positive=float((fin > 0).mean()), draws=int(fin.size))  # fmt: skip
    return out


# ---------------------------------------------------------------- diagnostics
def icc_oneway(n_g: np.ndarray, s_g: np.ndarray, ss_g: np.ndarray) -> float:
    """One-way ANOVA ICC(1) for unbalanced groups from group balls, sums and sums of squares."""
    n_g, s_g, ss_g = (np.asarray(a, float) for a in (n_g, s_g, ss_g))
    keep = n_g > 0
    n_g, s_g, ss_g = n_g[keep], s_g[keep], ss_g[keep]
    g, N = len(n_g), float(n_g.sum())
    if g < 2 or N - g <= 0:
        return float("nan")
    grand = float(s_g.sum())
    sum_g = float((s_g**2 / n_g).sum())
    msb = (sum_g - grand**2 / N) / (g - 1)
    msw = (float(ss_g.sum()) - sum_g) / (N - g)
    n0 = (N - float((n_g**2).sum()) / N) / (g - 1)
    den = msb + (n0 - 1.0) * msw
    return float((msb - msw) / den) if den > 0 and n0 > 0 else float("nan")


def icc_player_match(cd: rb.CellData) -> float:
    """ICC of residuals within player-match clusters after removing each player's own mean.

    A positive value means balls of one player in one match resemble each other more than balls
    of the same player in different matches, which breaks the independent-ball noise model and
    inflates the true sampling variance of a player mean.
    """
    N, S, S2 = cd.N, cd.S, cd.S2
    pm = N > 0
    n_c, s_c, ss_c = N[pm], S[pm], S2[pm]
    n_i, s_i = N.sum(1), S.sum(1)
    keep_i = n_i > 0
    P, g, tot = int(keep_i.sum()), int(pm.sum()), float(n_c.sum())
    if g - P < 1 or tot - g <= 0:
        return float("nan")
    ss_between = float((s_c**2 / n_c).sum() - (s_i[keep_i] ** 2 / n_i[keep_i]).sum())
    ss_within = float(ss_c.sum() - (s_c**2 / n_c).sum())
    msb, msw = ss_between / (g - P), ss_within / (tot - g)
    n_i_rows = np.broadcast_to(n_i[:, None], N.shape)[pm]
    n0 = (tot - float((n_c**2 / n_i_rows).sum())) / (g - P)
    den = msb + (n0 - 1.0) * msw
    return float((msb - msw) / den) if den > 0 and n0 > 0 else float("nan")


def tercile_variance_ratio(n: np.ndarray, ssw: np.ndarray) -> float:
    """Pooled residual variance of the lowest over the highest tercile of player ball counts."""
    n, ssw = np.asarray(n, float), np.asarray(ssw, float)
    ok = (n >= 2) & np.isfinite(ssw)
    n, ssw = n[ok], ssw[ok]
    if len(n) < 9:
        return float("nan")
    lo_c, hi_c = np.quantile(n, [1 / 3, 2 / 3])
    low, high = n <= lo_c, n > hi_c
    if low.sum() < 3 or high.sum() < 3:
        return float("nan")
    v_low = ssw[low].sum() / (n[low] - 1).sum()
    v_high = ssw[high].sum() / (n[high] - 1).sum()
    return float(v_low / v_high) if v_high > 0 else float("nan")


def pearson_dispersion(y: np.ndarray, noise: np.ndarray, tau2: float) -> float:
    """Pearson chi-square over its degrees of freedom for the model ``y_i ~ N(mu, tau2 + v_i)``."""
    y, v = _clean(y, noise)
    if len(y) < 3 or not np.isfinite(tau2) or tau2 < 0:
        return float("nan")
    w = 1.0 / (tau2 + v)
    mu = float((w * y).sum() / w.sum())
    return float((w * (y - mu) ** 2).sum() / (len(y) - 1))


def dispersion_diagnostics(cd: rb.CellData, min_balls: int = 1) -> dict[str, Any]:
    """H-B diagnostics of one cell: Kish arithmetic, tercile variance ratio, ICC, dispersion."""
    one = np.ones((cd.N.shape[1], 1))
    mo = rb.boot_moments(cd, one)
    dec = rb.decompose_moments(mo, min_balls)
    valid = (mo.n >= max(1, min_balls)) & np.isfinite(mo.mean)
    out: dict[str, Any] = {"players_valid": int(valid.sum())}
    if valid.sum() < 3 or cd.N.shape[1] < 2:
        return {**out, "status": NOT_ESTIMABLE}
    sigma2 = float(dec["sigma2"][0])
    with np.errstate(invalid="ignore", divide="ignore"):
        neff = np.where(mo.n2 > 0, mo.n**2 / np.where(mo.n2 > 0, mo.n2, 1.0), np.nan)
        kish_noise = sigma2 / neff
        ball_noise = sigma2 / np.where(mo.n > 0, mo.n, np.nan)
    ok = valid & np.isfinite(kish_noise) & np.isfinite(ball_noise)
    ratio = float(kish_noise[ok].mean() / ball_noise[ok].mean()) if ok.any() else float("nan")
    bpm = float(mo.n[valid].sum() / mo.m[valid].sum())
    e1 = tau2_moments_floor(mo.mean[valid], kish_noise[valid], sigma2)
    kish_between = e1.get("between")
    nsum = cd.N.sum(0)
    return {
        **out, "status": ESTIMATED, "sigma2": sigma2,
        "kish_noise_over_ball_noise": ratio, "balls_per_player_match": bpm,
        "kish_ratio_over_balls_per_match": ratio / bpm if bpm > 0 else float("nan"),
        "tercile_variance_ratio": tercile_variance_ratio(mo.n[valid], mo.ssw[valid]),
        "icc_match": icc_oneway(nsum, cd.S.sum(0), cd.S2.sum(0)),
        "icc_player_match": icc_player_match(cd),
        "pearson_dispersion": pearson_dispersion(
            mo.mean[valid], kish_noise[valid], e1["value"] if e1["value"] is not None else np.nan
        ),
        "kish_between_moment": kish_between,
        "median_balls": float(np.median(mo.n[valid])),
    }  # fmt: skip
