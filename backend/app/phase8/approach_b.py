"""Approach B glue: out-of-fold WP timeline, leverage, component counterfactuals, WPA residuals.

Every TRAIN delivery is scored by models fitted on the other four folds (``match_id % 5``);
VALIDATION deliveries by the models fitted on all of TRAIN. The same grouping is used for the
win-probability models, the class model and the leverage transitions, so no delivery sees a model
that was fitted on its own match.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase8.constants import N_FOLDS
from app.phase8.splits import fit_group
from app.phase8.winprob import (
    CLIP,
    N_CLASS,
    WPFit,
    leverage_and_components,
    next_state_wp,
)

STATE_COLS = [
    "innings_number", "team_runs_before", "team_wickets_before", "legal_balls_bowled_before",
    "legal_balls_remaining", "innings_limit_balls", "competition_type", "target", "bat_team_prior",
    "bowl_team_prior", "par_prior", "innings_phase",
]  # fmt: skip


def combine_wp_before(df: pd.DataFrame, w1: WPFit, w2: WPFit) -> pd.Series:
    """WP before each delivery: W2 for innings 2, W1 for innings 1 (NaN when undefined)."""
    out = np.where(
        df["innings_number"] == 2, w2.pred, np.where(df["innings_number"] == 1, w1.pred, np.nan)
    )
    return pd.Series(np.clip(out, *CLIP), index=df.index)


def model_groups(df: pd.DataFrame) -> list[tuple[str, np.ndarray, int | None]]:
    """(label, row positions, fold) with fold ``None`` for VALIDATION."""
    pos = np.arange(len(df))
    folds = (df["match_id"].astype("int64") % N_FOLDS).to_numpy()
    out: list[tuple[str, np.ndarray, int | None]] = []
    grp = fit_group(df)
    val = (grp == "VALIDATION").to_numpy()
    out.append(("VALIDATION", pos[val], None))
    tr = (grp == "TRAIN").to_numpy()
    for f in range(N_FOLDS):
        out.append((f"TRAIN_FOLD_{f}", pos[tr & (folds == f)], f))
    return out


def _models(fold: int | None, w1: WPFit, w2: WPFit, cls_full: Any, cls_fold: dict[int, Any]):
    if fold is None:
        return w1.predictor, w2.predictor, cls_full
    return w1.fold_predictors[fold], w2.fold_predictors[fold], cls_fold[fold]


def leverage_all(
    df: pd.DataFrame, wp_before: pd.Series, w1: WPFit, w2: WPFit, cls_full: Any,
    cls_fold: dict[int, Any],
) -> tuple[pd.Series, np.ndarray]:  # fmt: skip
    """Leverage per delivery and the class probabilities (rows of NaN where WP is undefined)."""
    lev = np.full(len(df), np.nan)
    probs = np.full((len(df), N_CLASS), np.nan)
    wpb = wp_before.to_numpy()
    for _label, pos, fold in model_groups(df):
        if len(pos) == 0:
            continue
        m1, m2, mc = _models(fold, w1, w2, cls_full, cls_fold)
        d = df.iloc[pos][STATE_COLS]
        lev[pos], probs[pos] = leverage_and_components(m1, m2, mc, d, wpb[pos])
    return pd.Series(lev, index=df.index), probs


def component_counterfactuals(
    df: pd.DataFrame, w1: WPFit, w2: WPFit, cls_full: Any, cls_fold: dict[int, Any]
) -> pd.DataFrame:  # fmt: skip
    """WP of the state after each single component of a ball (only rows with 2+ components).

    ``cf_bat`` = bat runs only, ``cf_ext`` and ``cf_team`` = the extra runs only, ``cf_wkt`` = the
    wicket only; the ball is consumed exactly when the real ball was a legal delivery.
    """
    from app.phase8.wpa import component_flags

    flags = component_flags(df)
    multi = flags.sum(axis=1) > 1
    bat_runs = df["out_batter_runs"].fillna(0).to_numpy(dtype="float64")
    extra_runs = df["out_extras_primary_runs"].fillna(0).to_numpy(dtype="float64")
    consume = (df["den_legal_inc"] == 1).to_numpy(dtype="float64")
    out = pd.DataFrame(np.nan, index=df.index, columns=["cf_bat", "cf_ext", "cf_team", "cf_wkt"])
    spec = {
        "cf_bat": (bat_runs, np.zeros(len(df))),
        "cf_ext": (extra_runs, np.zeros(len(df))),
        "cf_team": (extra_runs, np.zeros(len(df))),
        "cf_wkt": (np.zeros(len(df)), np.ones(len(df))),
    }
    mm = multi.to_numpy()
    for _label, pos, fold in model_groups(df):
        sel = pos[mm[pos]]
        if len(sel) == 0:
            continue
        m1, m2, _ = _models(fold, w1, w2, cls_full, cls_fold)
        d = df.iloc[sel][STATE_COLS]
        for col, (runs, wkt) in spec.items():
            out.iloc[sel, out.columns.get_loc(col)] = next_state_wp(
                m1, m2, d, runs[sel], wkt[sel], consume[sel]
            )
    return out


def design_matrix(df: pd.DataFrame, lev: pd.Series, exp_runs: pd.Series) -> pd.DataFrame:
    """Covariates for the WPA-on-leverage regression: L, L^2, phase, innings, expected runs."""
    x = pd.DataFrame(index=df.index)
    x["const"] = 1.0
    x["L"] = lev
    x["L2"] = lev**2
    x["middle"] = (df["innings_phase"] == "middle").astype("float64")
    x["death"] = (df["innings_phase"] == "death").astype("float64")
    x["innings2"] = (df["innings_number"] == 2).astype("float64")
    x["exp_runs"] = exp_runs
    return x


def _ols(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    return beta


def wpa_residuals(
    df: pd.DataFrame, credit: pd.Series, x: pd.DataFrame
) -> tuple[pd.Series, pd.DataFrame]:  # fmt: skip
    """WPA above the leverage expectation: ``credit - fitted`` with a TRAIN-only OLS.

    TRAIN rows use the fit of the other four folds, VALIDATION rows the fit on all TRAIN. Rows with
    a missing credit or covariate get NaN (never zero). Returns the residual and the coefficients.
    """
    ok = credit.notna() & x.notna().all(axis=1)
    folds = (df["match_id"].astype("int64") % N_FOLDS).to_numpy()
    grp = fit_group(df)
    tr = ((grp == "TRAIN") & ok).to_numpy()
    va = ((grp == "VALIDATION") & ok).to_numpy()
    xv, yv = x.to_numpy(dtype="float64"), credit.to_numpy(dtype="float64")
    fitted = np.full(len(df), np.nan)
    coefs = []
    beta = _ols(xv[tr], yv[tr])
    coefs.append({"fit": "TRAIN_ALL", **dict(zip(x.columns, beta, strict=True))})
    fitted[va] = xv[va] @ beta
    for f in range(N_FOLDS):
        b = _ols(xv[tr & (folds != f)], yv[tr & (folds != f)])
        rows = tr & (folds == f)
        fitted[rows] = xv[rows] @ b
        coefs.append({"fit": f"FOLD_{f}", **dict(zip(x.columns, b, strict=True))})
    res = pd.Series(yv - fitted, index=df.index)
    return res.where(ok), pd.DataFrame(coefs)


def leverage_weighted(
    df: pd.DataFrame, role_col: str, credit: pd.Series, lev: pd.Series
) -> pd.DataFrame:  # fmt: skip
    """Leverage-weighted WPA per opportunity ``sum(L * credit) / sum(L)`` per player."""
    ok = credit.notna() & lev.notna()
    d = pd.DataFrame(
        {"player_id": df.loc[ok, role_col].to_numpy(), "lw": (lev[ok] * credit[ok]).to_numpy(),
         "l": lev[ok].to_numpy(), "c": credit[ok].to_numpy()}
    )  # fmt: skip
    g = d.groupby("player_id")
    return pd.DataFrame(
        {"lw_wpa_per_opp": g["lw"].sum() / g["l"].sum(), "mean_wpa": g["c"].mean(),
         "sum_wpa": g["c"].sum(), "mean_leverage": g["l"].mean(), "n_wpa_balls": g.size()}
    )  # fmt: skip
