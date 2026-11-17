"""REML random-effects estimation for player-match units.

Model: ``y_ij = mu + u_i + e_ij`` with ``u_i ~ N(0, tau2)`` and ``e_ij ~ N(0, sigma2 / prec_ij)``,
where ``y_ij`` is a unit's weighted mean residual and ``prec_ij = (sum w)^2 / sum w^2`` is its Kish
effective count (the variance of a weighted mean of independent balls is ``s2 * sum w^2 / (sum w)^2``).

The restricted likelihood is profiled over ``mu`` and ``sigma2`` analytically; only the ratio
``lam = tau2 / sigma2`` is searched (grid, then bounded refinement). No floor is imposed on ``tau2``.
When ``lam = 0`` is statistically indistinguishable from the optimum the cell is flagged ``FLOOR``,
``tau2`` is reported as 0 and the posterior collapses to ``mu`` (``NO_BETWEEN_PLAYER_SIGNAL``).
Reliability is always computed on the unshrunk means, never on these posterior values.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

FLOOR_RATIO = 1e-8
LOG_LAM_RANGE = (-16.0, 8.0)
NLL_FLOOR_TOL = 1e-6


class RemlError(ValueError):
    """The unit table cannot identify the variance components."""


def player_summary(units: pd.DataFrame) -> pd.DataFrame:
    """Per player: precision ``P``, precision-weighted mean ``ybar``, within SS ``S``, units ``n``."""
    need = {"player_id", "y", "prec"}
    if not need <= set(units.columns):
        raise RemlError(f"unit table needs {sorted(need)}")
    u = units.dropna(subset=["player_id", "y", "prec"])
    if (u["prec"] <= 0).any():
        raise RemlError("precisions must be positive")
    # Optional multiplicity (bootstrap replicate counts); units with multiplicity 0 drop out.
    mult = u["mult"] if "mult" in u.columns else pd.Series(1.0, index=u.index)
    u = u.assign(m=mult.astype("float64"))
    u = u[u["m"] > 0]
    u = u.assign(pm=u["prec"] * u["m"])
    u = u.assign(py=u["pm"] * u["y"])
    g = u.groupby("player_id", sort=True)
    out = pd.DataFrame({"P": g["pm"].sum(), "n": g["m"].sum(), "py": g["py"].sum()})
    out["ybar"] = out["py"] / out["P"]
    u = u.join(out["ybar"], on="player_id")
    out["S"] = (u["pm"] * (u["y"] - u["ybar"]) ** 2).groupby(u["player_id"]).sum()
    return out.drop(columns="py")


def _profile(
    lam: float, ybar: np.ndarray, P: np.ndarray, S: float, nw: int
) -> tuple[float, float, float]:
    """Profile REML negative log likelihood (up to a constant), ``mu`` and ``sigma2`` at ``lam``."""
    v = lam + 1.0 / P
    inv = 1.0 / v
    mu = float((inv * ybar).sum() / inv.sum())
    q = float((inv * (ybar - mu) ** 2).sum())
    m = len(ybar)
    dof = nw + m - 1
    sigma2 = (S + q) / dof
    nll = 0.5 * (dof * np.log(sigma2) + np.log(v).sum() + np.log(inv.sum()))
    return nll, mu, sigma2


def fit_reml(units: pd.DataFrame) -> dict[str, Any]:
    """Estimate ``(mu, tau2, sigma2)`` and the per-player posterior.

    Returns a dict with ``mu, tau2, sigma2, floor`` (bool), ``label`` and ``players`` (a frame with
    ``ybar, P, n, B, theta, se``). Raises ``RemlError`` when ``sigma2`` is not identifiable.
    """
    ps = player_summary(units)
    if len(ps) < 3:
        raise RemlError("fewer than three players")
    nw = int((ps["n"] - 1).sum())
    if nw < 1:
        raise RemlError("no player has two units: within-player variance is not identifiable")
    ybar, P, S = ps["ybar"].to_numpy(), ps["P"].to_numpy(), float(ps["S"].sum())
    grid = np.linspace(*LOG_LAM_RANGE, 49)
    vals = [_profile(float(np.exp(g)), ybar, P, S, nw)[0] for g in grid]
    k = int(np.argmin(vals))
    lo, hi = grid[max(k - 1, 0)], grid[min(k + 1, len(grid) - 1)]
    res = minimize_scalar(
        lambda t: _profile(float(np.exp(t)), ybar, P, S, nw)[0], bounds=(lo, hi), method="bounded"
    )
    best_t = float(res.x) if res.fun <= vals[k] else float(grid[k])
    nll_best, mu, sigma2 = _profile(float(np.exp(best_t)), ybar, P, S, nw)
    nll0, mu0, sigma20 = _profile(0.0, ybar, P, S, nw)
    floor = (np.exp(best_t) < FLOOR_RATIO) or (nll0 - nll_best < NLL_FLOOR_TOL)
    if floor:
        lam, mu, sigma2 = 0.0, mu0, sigma20
    else:
        lam = float(np.exp(best_t))
    tau2 = lam * sigma2
    var_e = sigma2 / P
    B = tau2 / (tau2 + var_e) if tau2 > 0 else np.zeros_like(P)
    ps["B"] = B
    ps["theta"] = mu + B * (ybar - mu)
    ps["se"] = np.sqrt(B * var_e)
    return {
        "mu": float(mu),
        "tau2": float(tau2),
        "sigma2": float(sigma2),
        "lambda": float(lam),
        "floor": bool(floor),
        "label": "NO_BETWEEN_PLAYER_SIGNAL" if floor else "BETWEEN_PLAYER_SIGNAL",
        "mean_B": float(np.mean(B)),
        "n_players": int(len(ps)),
        "n_units": int(ps["n"].sum()),
        "players": ps,
    }


def posterior(ybar: np.ndarray, P: np.ndarray, mu: float, tau2: float, sigma2: float) -> np.ndarray:
    """Posterior means for fixed variance components (used in bootstrap draws)."""
    if tau2 <= 0:
        return np.full(np.shape(ybar), mu, dtype="float64")
    b = tau2 / (tau2 + sigma2 / P)
    return mu + b * (ybar - mu)
