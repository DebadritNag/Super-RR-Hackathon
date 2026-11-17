"""Continuous pressure-intensity candidates in [0, 1] (pre-delivery information only).

Each candidate has a raw value per delivery; the raw value is mapped to [0, 1] by the empirical CDF
fitted on TRAIN, so the candidates share one scale and VALIDATION never influences the mapping.
TRAIN deliveries use the CDF of the other four folds (``match_id % 5``) so that no delivery is
mapped by a CDF that saw its own match. An undefined raw value gives NaN, never zero.

Candidates implemented here (P1 and P2 need the win-probability model of the next chunk and enter
through ``intensity_from_wp``):

* P0 reference: 1 when any of P3 or P4 is above its TRAIN 0.75 quantile, else 0 (the Phase 6 idea,
  re-implemented; not the stored Phase 6 set).
* P3 chase difficulty (innings 2): runs required per unit of remaining batting resource.
* P4 resource scarcity (both innings): share of wickets lost times share of the innings used.
* P5 defending difficulty (innings 2, bowler side): batting side's projected surplus.
* P6 composite: first principal component of the standardised P3 and P4 (innings 2). P5 has the
  defending side's orientation and is left out.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.phase8.constants import N_FOLDS

GRID_POINTS = 1001
RAW = ("P3", "P4", "P5")
# P5 is oriented to the defending side, so it is not mixed into the batter-side composite.
COMPOSITE_INPUTS = ("w_P3", "w_P4")
CANDIDATES = ("P0", "P3", "P4", "P5", "P6")
COVERAGE_INNINGS = (1, 2)


def raw_values(df: pd.DataFrame) -> pd.DataFrame:
    """Raw (unscaled) candidate values; NaN where the input is missing or the rule is undefined."""
    out = pd.DataFrame(index=df.index)
    chase = df["chase_flag"].fillna(False).astype(bool) & (df["innings_number"] == 2)
    valid_chase = (
        chase
        & ~df["target_basis_unverified"].fillna(False).astype(bool)
        & ~df["req_nonpositive_flag"].fillna(False).astype(bool)
        & df["runs_required"].notna()
        & (df["resource_ratio"] > 0)
    )
    p3 = df["runs_required"].astype("float64") / df["resource_ratio"].where(
        df["resource_ratio"] > 0
    )
    out["raw_P3"] = p3.where(valid_chase)
    limit = df["innings_limit_balls"].astype("float64").where(df["innings_limit_balls"] > 0)
    wick_lost = 1.0 - df["wickets_remaining"].astype("float64") / 10.0
    progress = df["legal_balls_bowled_before"].astype("float64") / limit
    out["raw_P4"] = (wick_lost * progress).where(df["innings_number"].isin([1, 2]))
    out["raw_P5"] = df["projected_surplus"].astype("float64").where(valid_chase)
    return out


def fit_cdf(values: np.ndarray, points: int = GRID_POINTS) -> np.ndarray | None:
    """Quantile grid of the finite values (None when fewer than 50 values are available)."""
    v = np.asarray(values, dtype="float64")
    v = v[np.isfinite(v)]
    if v.size < 50:
        return None
    return np.quantile(v, np.linspace(0.0, 1.0, points))


def apply_cdf(grid: np.ndarray | None, values: np.ndarray) -> np.ndarray:
    """Map values to [0, 1] with the fitted grid (mid-rank for ties); NaN stays NaN."""
    x = np.asarray(values, dtype="float64")
    if grid is None:
        return np.full(x.shape, np.nan)
    lo = np.searchsorted(grid, x, side="left")
    hi = np.searchsorted(grid, x, side="right")
    n = len(grid) - 1
    out = ((lo + hi) / 2.0 - 0.5) / n
    out = np.clip(out, 0.0, 1.0)
    return np.where(np.isfinite(x), out, np.nan)


def _fold(df: pd.DataFrame) -> np.ndarray:
    return (df["match_id"].astype("int64") % N_FOLDS).to_numpy()


def scaled(df: pd.DataFrame, raw: pd.DataFrame, col: str) -> tuple[np.ndarray, dict[str, Any]]:
    """Intensity in [0, 1] for one raw column, per innings, with TRAIN-only OOF scaling.

    Returns (values, info) where info holds the number of TRAIN values used per innings.
    """
    out = np.full(len(df), np.nan)
    info: dict[str, Any] = {}
    fold = _fold(df)
    is_train = (df["period"] == "TRAIN").to_numpy()
    r = raw[col].to_numpy()
    for inn in COVERAGE_INNINGS:
        sel = (df["innings_number"] == inn).to_numpy()
        tr = sel & is_train
        info[f"train_n_inn{inn}"] = int(np.isfinite(r[tr]).sum())
        full = fit_cdf(r[tr])
        out[sel & ~is_train] = apply_cdf(full, r[sel & ~is_train])
        for f in range(N_FOLDS):
            m = tr & (fold == f)
            if not m.any():
                continue
            g = fit_cdf(r[tr & (fold != f)])
            out[m] = apply_cdf(g, r[m])
    return out, info


def fit_composite(z: pd.DataFrame, train_mask: pd.Series) -> dict[str, Any] | None:
    """First principal component of standardised candidates fitted on complete TRAIN rows."""
    cols = list(z.columns)
    sub = z.loc[train_mask].dropna()
    if len(sub) < 200 or len(cols) < 2:
        return None
    mu, sd = sub.mean(), sub.std(ddof=0).replace(0, np.nan)
    if sd.isna().any():
        return None
    x = ((sub - mu) / sd).to_numpy()
    cov = np.cov(x, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    load = vecs[:, int(np.argmax(vals))]
    if load.sum() < 0:
        load = -load
    return {"cols": cols, "mean": mu.to_dict(), "sd": sd.to_dict(), "loadings": load.tolist(),
            "explained": float(vals.max() / vals.sum())}  # fmt: skip


def uniform_composite(z: pd.DataFrame) -> np.ndarray:
    """First principal component of CDF-scaled inputs, free of fitted parameters.

    CDF-scaled inputs are uniform on [0, 1] (mean 1/2, variance 1/12), so standardising with those
    constants needs no fit. For two standardised inputs the first principal component has equal
    loadings (algebraic identity), so the score is the equal-loading sum. Because nothing is fitted
    on the data, a delivery's composite depends only on its own pre-delivery state and the
    TRAIN-only scaling of the inputs. NaN when any input is missing.
    """
    k = z.shape[1]
    s = ((z.to_numpy(dtype="float64") - 0.5) / np.sqrt(1.0 / 12.0)).sum(axis=1)
    return s / np.sqrt(k)


def apply_composite(z: pd.DataFrame, fit: dict[str, Any] | None) -> np.ndarray:
    """Composite score (NaN when any input is missing or no fit exists)."""
    if fit is None:
        return np.full(len(z), np.nan)
    x = np.column_stack([(z[c].to_numpy() - fit["mean"][c]) / fit["sd"][c] for c in fit["cols"]])
    return x @ np.asarray(fit["loadings"])


def build_intensity(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Intensity columns ``w_P0, w_P3, w_P4, w_P5, w_P6`` (aligned with ``df``) and fit info.

    ``df`` must carry ``period`` (TRAIN or VALIDATION) and the state columns. Fitting uses TRAIN
    only; no outcome column is read.
    """
    if not set(df["period"].unique()) <= {"TRAIN", "VALIDATION"}:
        raise ValueError("intensity is defined for TRAIN and VALIDATION frames only")
    raw = raw_values(df)
    w = pd.DataFrame(index=df.index)
    info: dict[str, Any] = {}
    for cand in RAW:
        w[f"w_{cand}"], info[cand] = scaled(df, raw, f"raw_{cand}")
    # P0 reference: any scaled signal above the TRAIN 0.75 quantile.
    sig = w[["w_P3", "w_P4"]]
    any_hi = (sig >= 0.75).any(axis=1)
    w["w_P0"] = np.where(sig.notna().any(axis=1), any_hi.astype(float), np.nan)
    # P6 composite (innings 2): PCA on the TRAIN rows, then the same CDF scaling.
    z = w[list(COMPOSITE_INPUTS)]
    fit = fit_composite(z, df["period"] == "TRAIN")
    info["P6"] = None if fit is None else {k: fit[k] for k in ("cols", "loadings", "explained")}
    comp = pd.DataFrame({"raw_P6": uniform_composite(z)}, index=df.index)
    w["w_P6"], info["P6_scale"] = scaled(df, comp, "raw_P6")
    return w[[f"w_{c}" for c in CANDIDATES]], info


def intensity_from_wp(
    df: pd.DataFrame, wp_before: pd.Series, leverage: pd.Series | None = None
) -> pd.DataFrame:
    """P2 (decision closeness) and, when given, P1 (leverage) from win-probability columns.

    The WP and leverage inputs must be out-of-fold pre-delivery values; the scaling is the same
    TRAIN-only CDF as for the other candidates.
    """
    out = pd.DataFrame(index=df.index)
    closeness = 1.0 - 2.0 * (wp_before.astype("float64") - 0.5).abs()
    raw = pd.DataFrame({"raw_P2": closeness})
    if leverage is not None:
        raw["raw_P1"] = leverage.astype("float64")
    for c in raw.columns:
        out["w_" + c[4:]], _ = scaled(df, raw, c)
    return out


def coverage(df: pd.DataFrame, w: pd.DataFrame) -> pd.DataFrame:
    """Share of deliveries with a defined intensity per candidate, innings and period."""
    rows = []
    for c in w.columns:
        for (inn, per), idx in df.groupby(["innings_number", "period"]).groups.items():
            s = w.loc[idx, c]
            rows.append({"candidate": c[2:], "innings": int(inn), "period": per,
                         "rows": int(len(s)), "defined": int(s.notna().sum()),
                         "defined_share": float(s.notna().mean())})  # fmt: skip
    return pd.DataFrame(rows)


def high_intensity(w: pd.Series, cut: float = 0.5) -> pd.Series:
    """Boolean flag ``w >= cut`` (False where undefined; the unit builder treats NaN separately)."""
    return (w >= cut).fillna(False)
