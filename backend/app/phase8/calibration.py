"""Calibration utilities: reliability curve, Brier, log loss, calibration slope and intercept.

Pure functions on arrays of outcomes ``y`` in {0, 1} and probabilities ``p``. They are tested on
synthetic data with known calibration. Nothing here reads a database.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

EPS = 1e-12


def _check(y: np.ndarray, p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype="float64")
    p = np.asarray(p, dtype="float64")
    if y.shape != p.shape or y.ndim != 1:
        raise ValueError("y and p must be one-dimensional arrays of the same length")
    ok = np.isfinite(y) & np.isfinite(p)
    y, p = y[ok], p[ok]
    if len(y) == 0:
        raise ValueError("no finite observations")
    if not np.isin(y, [0.0, 1.0]).all():
        raise ValueError("y must contain only 0 and 1")
    if ((p < 0) | (p > 1)).any():
        raise ValueError("p must lie in [0, 1]")
    return y, p


def brier(y: np.ndarray, p: np.ndarray) -> float:
    y, p = _check(y, p)
    return float(np.mean((p - y) ** 2))


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    y, p = _check(y, p)
    q = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))


def decile_table(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    """Equal-count bins of ``p`` with the mean prediction, observed rate and count per bin."""
    y, p = _check(y, p)
    order = np.argsort(p, kind="stable")
    parts = np.array_split(order, min(bins, len(y)))
    rows = [
        {"bin": i + 1, "n": int(len(ix)), "mean_pred": float(p[ix].mean()),
         "mean_obs": float(y[ix].mean())}
        for i, ix in enumerate(parts)
        if len(ix)
    ]  # fmt: skip
    return pd.DataFrame(rows)


def calibration_slope_intercept(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    """Logistic recalibration ``logit P(y=1) = a + b * logit(p)``. A perfect model has a=0, b=1."""
    y, p = _check(y, p)
    x = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    if np.ptp(x) < 1e-9:
        return {"intercept": float("nan"), "slope": float("nan")}

    def nll(b: np.ndarray) -> float:
        z = b[0] + b[1] * x
        return float(np.sum(np.logaddexp(0.0, z) - y * z))

    def grad(b: np.ndarray) -> np.ndarray:
        e = 1.0 / (1.0 + np.exp(-(b[0] + b[1] * x))) - y
        return np.array([e.sum(), (e * x).sum()])

    res = minimize(nll, np.array([0.0, 1.0]), jac=grad, method="BFGS")
    return {"intercept": float(res.x[0]), "slope": float(res.x[1])}


def calibration_report(y: np.ndarray, p: np.ndarray, bins: int = 10) -> dict[str, Any]:
    """Brier, log loss, slope, intercept, decile table and the constant-prior baselines."""
    y, p = _check(y, p)
    base = float(y.mean())
    const = np.full_like(p, base)
    rec = calibration_slope_intercept(y, p)
    b, b0 = brier(y, p), brier(y, const)
    return {
        "n": int(len(y)),
        "brier": b,
        "brier_baseline": b0,
        "brier_gain": float(1.0 - b / b0) if b0 > 0 else float("nan"),
        "log_loss": log_loss(y, p),
        "log_loss_baseline": log_loss(y, const),
        **rec,
        "deciles": decile_table(y, p, bins),
    }
