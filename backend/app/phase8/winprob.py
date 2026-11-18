"""Win-probability models (Approach B): pre-delivery information only, chronological split.

* ``W2`` innings 2 (chasing side wins) and ``W1`` innings 1 (batting side eventually wins) are
  HistGradientBoosting classifiers fitted on TRAIN only. One pass over the declared grid on
  VALIDATION picks the parameters by log loss. TRAIN deliveries are scored out of fold
  (``match_id % 5``); VALIDATION deliveries by the model fitted on all of TRAIN.
* Labels come from decisive, regulation, non-DLS results only. Every other match is listed with its
  reason and never imputed (a Super Over winner is never a regulation winner).
* ``CLS`` is a seven-class next-ball outcome model (dot, 1, 2, 3, 4, 6, wicket) on situation
  features only. It feeds leverage ``L = sum_k p_k |WP(state_k) - WP_before|``.
* ``WP_after`` of a ball is ``WP_before`` of the next ball of the same innings; the last ball of an
  innings 2 uses the result label, the last ball of an innings 1 uses ``1 - WP2`` of the first ball
  of the chase (a pre-delivery model output). ``WP_before`` never reads a result or a later row.
"""

from __future__ import annotations

import itertools
import json
import re
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from app.phase8.calibration import (
    brier,
    calibration_report,
    log_loss,
)
from app.phase8.constants import MODELS_DIR, N_FOLDS, SEED, active_prefix
from app.phase8.splits import assert_fit_on_train, fit_group

CLIP = (0.005, 0.995)
WP_SLOPE_RANGE = (0.8, 1.2)
WP_MIN_BRIER_GAIN = 0.02
GRID = {"max_depth": [3, 5], "learning_rate": [0.05, 0.1], "l2_regularization": [0.0, 1.0]}
MAX_ITER = 200
MIN_LEAF = 200
COMP_CODE = {"IPL": 0.0, "T20I": 1.0}

W2_COLS = [
    "runs_required", "legal_balls_remaining", "wickets_remaining", "rrr", "crr", "gap",
    "resource_ratio", "innings_limit_balls", "competition_code", "bat_team_prior",
    "bowl_team_prior",
]  # fmt: skip
W1_COLS = [
    "team_runs_before", "wickets_remaining", "legal_balls_remaining", "crr", "projected_total",
    "par_prior", "par_deviation_prior", "innings_limit_balls", "competition_code",
    "bat_team_prior", "bowl_team_prior",
]  # fmt: skip
CLS_COLS = [
    "innings_number", "team_runs_before", "team_wickets_before", "wickets_remaining",
    "legal_balls_bowled_before", "innings_limit_balls", "legal_balls_remaining", "crr",
    "innings_phase_code", "runs_required", "rrr", "gap", "resource_ratio", "projected_total",
    "competition_code", "bat_team_prior", "bowl_team_prior",
]  # fmt: skip
# Outcome classes of the next legal ball: runs off the bat 0,1,2,3,4,6 and "wicket".
CLASS_RUNS = np.array([0, 1, 2, 3, 4, 6, 0])
CLASS_WICKET = np.array([False] * 6 + [True])
N_CLASS = 7
PHASE_CODE = {"powerplay": 0.0, "middle": 1.0, "death": 2.0}

# ---------------------------------------------------------------------------------------------
# labels
# ---------------------------------------------------------------------------------------------
_EXCLUDE = re.compile(
    r"super\s*over|eliminator|\btied\b|\btie\b|no result|abandon|\bd/?l\b|\bdls\b", re.IGNORECASE
)


def exclusion_reason(result: Any, win_team_id: Any, revised_target: Any) -> str | None:
    """Reason a match gives no regulation label, or ``None`` when it is a clean decisive result."""
    if pd.isna(win_team_id):
        return "NO_WINNER"
    m = _EXCLUDE.search("" if pd.isna(result) else str(result))
    if m:
        return f"RESULT_TEXT:{m.group(0).lower()}"
    if not pd.isna(revised_target):
        return "DLS_REVISED_TARGET"
    return None


def match_labels(matches: pd.DataFrame) -> pd.DataFrame:
    """``match_id, win_team_id, label_ok, reason`` for every match (never imputed)."""
    rows = [
        {
            "match_id": int(r.match_id),
            "win_team_id": r.win_team_id,
            "reason": exclusion_reason(r.result, r.win_team_id, r.revised_target),
        }
        for r in matches.itertuples(index=False)
    ]
    out = pd.DataFrame(rows)
    out["label_ok"] = out["reason"].isna()
    return out


# ---------------------------------------------------------------------------------------------
# features (one function for real rows and for hypothetical next states)
# ---------------------------------------------------------------------------------------------
def state_features(
    *, team_runs, team_wickets, balls_bowled, balls_rem, limit, target, comp_code, bat_prior,
    bowl_prior, par_prior, phase_code=None, innings=None,
) -> pd.DataFrame:  # fmt: skip
    """All WP and class-model columns from a raw state. NaN where an input is undefined."""
    f = lambda a: np.asarray(a, dtype="float64")  # noqa: E731
    runs, wk, bb, br, lim = f(team_runs), f(team_wickets), f(balls_bowled), f(balls_rem), f(limit)
    tgt = f(target)
    with np.errstate(divide="ignore", invalid="ignore"):
        crr = np.where(bb > 0, 6.0 * runs / bb, np.nan)
        req = tgt - runs
        rrr = np.where(br > 0, 6.0 * req / br, np.nan)
        proj = np.where(bb > 0, runs + crr * br / 6.0, np.nan)
        res = np.where(lim > 0, br / lim * (10.0 - wk) / 10.0, np.nan)
    par = f(par_prior)
    out = pd.DataFrame(
        {
            "team_runs_before": runs,
            "team_wickets_before": wk,
            "wickets_remaining": 10.0 - wk,
            "legal_balls_bowled_before": bb,
            "legal_balls_remaining": br,
            "innings_limit_balls": lim,
            "runs_required": np.where(np.isnan(tgt), np.nan, req),
            "rrr": np.where(np.isnan(tgt), np.nan, rrr),
            "crr": crr,
            "gap": np.where(np.isnan(tgt), np.nan, rrr - crr),
            "resource_ratio": res,
            "projected_total": proj,
            "par_prior": par,
            "par_deviation_prior": proj - par,
            "competition_code": f(comp_code),
            "bat_team_prior": f(bat_prior),
            "bowl_team_prior": f(bowl_prior),
            "innings_phase_code": np.nan if phase_code is None else f(phase_code),
            "innings_number": np.nan if innings is None else f(innings),
        }
    )
    return out


def frame_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature columns of real deliveries (pre-delivery columns only)."""
    chase = df["innings_number"] == 2
    ok_chase = (
        chase
        & ~df["target_basis_unverified"].fillna(False).astype(bool)
        & ~df["req_nonpositive_flag"].fillna(False).astype(bool)
    )
    target = np.where(ok_chase, df["target"].astype("float64"), np.nan)
    f = state_features(
        team_runs=df["team_runs_before"], team_wickets=df["team_wickets_before"],
        balls_bowled=df["legal_balls_bowled_before"], balls_rem=df["legal_balls_remaining"],
        limit=df["innings_limit_balls"], target=target,
        comp_code=df["competition_type"].map(COMP_CODE), bat_prior=df["bat_team_prior"],
        bowl_prior=df["bowl_team_prior"], par_prior=df["par_prior"],
        phase_code=df["innings_phase"].map(PHASE_CODE), innings=df["innings_number"],
    )  # fmt: skip
    f.index = df.index
    return f


# ---------------------------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------------------------
class Predictor:
    """Picklable probability predictor over a fixed column list."""

    def __init__(self, how: str, cols: list[str], model: Any, fill: dict[str, float] | None = None):
        self.how, self.cols, self.model, self.fill = how, cols, model, fill or {}

    def __call__(self, x: pd.DataFrame) -> np.ndarray:
        m = x[self.cols]
        if self.how == "const":
            return np.full(len(m), self.model)
        if self.how == "logit":
            z = m.copy()
            for c, v in self.fill.items():
                z[c] = z[c].fillna(v)
            return self.model.predict_proba(z.to_numpy())[:, 1]
        return self.model.predict_proba(m)[:, 1]

    def proba(self, x: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(x[self.cols])


def _hgb(cols: list[str], params: dict[str, Any]) -> HistGradientBoostingClassifier:
    cat = [c in ("competition_code", "innings_phase_code") for c in cols]
    return HistGradientBoostingClassifier(
        max_iter=MAX_ITER, min_samples_leaf=MIN_LEAF, early_stopping=False, random_state=SEED,
        categorical_features=cat, **params,
    )  # fmt: skip


def fit_binary(
    how: str, cols: list[str], x: pd.DataFrame, y: np.ndarray, params: dict[str, Any]
) -> Predictor:
    """Fit ``gbm``, ``logit`` (standardised, median-filled) or ``const`` on the rows given."""
    if how == "const":
        return Predictor("const", cols, float(np.mean(y)))
    if how == "logit":
        fill = {c: float(np.nanmedian(x[c])) for c in cols}
        z = x[cols].copy()
        for c, v in fill.items():
            z[c] = z[c].fillna(v)
        mu, sd = z.mean(), z.std(ddof=0).replace(0, 1.0)
        m = _Scaled(LogisticRegression(max_iter=1000), mu.to_numpy(), sd.to_numpy())
        m.fit(z.to_numpy(), y.astype(int))
        return Predictor("logit", cols, m, fill)
    m = _hgb(cols, params)
    m.fit(x[cols], y.astype(int))
    return Predictor("gbm", cols, m)


class _Scaled:
    def __init__(self, lr: LogisticRegression, mu: np.ndarray, sd: np.ndarray) -> None:
        self.lr, self.mu, self.sd = lr, mu, sd

    def fit(self, x: np.ndarray, y: np.ndarray) -> _Scaled:
        self.lr.fit((x - self.mu) / self.sd, y)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.lr.predict_proba((x - self.mu) / self.sd)


def grid_points() -> list[dict[str, Any]]:
    keys = sorted(GRID)
    return [dict(zip(keys, v, strict=True)) for v in itertools.product(*(GRID[k] for k in keys))]


@dataclass
class WPFit:
    """Result of fitting one WP model: OOF/validation predictions, metrics, chosen predictor."""

    name: str
    chosen_params: dict[str, Any]
    predictor: Predictor
    pred: pd.Series
    metrics: dict[str, Any]
    grid: list[dict[str, Any]]
    deciles: list[dict[str, Any]]
    n_train: int
    n_validation: int
    train_matches: int
    train_deliveries: int
    fold_predictors: dict[int, Predictor]


def fit_wp(
    name: str, df: pd.DataFrame, x: pd.DataFrame, y: pd.Series, pop: pd.Series, cols: list[str],
    baseline_cols: list[str], score: pd.Series, fixed_params: dict[str, Any] | None = None,
) -> WPFit:  # fmt: skip
    """Select on VALIDATION once, then score TRAIN out of fold and VALIDATION out of sample.

    With ``fixed_params`` (Phase 9) nothing is selected: the Phase 8 parameters are applied and the
    VALIDATION group (calendar 2026) only provides the out-of-time metrics. Groups follow
    ``fit_group`` (Phase 9) or ``period`` (Phase 8).

    ``pop`` (labelled rows) is used for fitting and metrics; ``score`` (every row with valid
    features, labelled or not) receives a prediction from a model that never saw its match.
    """
    grp = fit_group(df)
    train = (grp == "TRAIN").to_numpy() & pop.to_numpy()
    val = (grp == "VALIDATION").to_numpy() & pop.to_numpy()
    assert_fit_on_train(df.loc[train, "match_id"], df)
    yt, yv = y.to_numpy()[train], y.to_numpy()[val]
    grid, best = [], None
    for params in grid_points() if fixed_params is None else []:
        p = fit_binary("gbm", cols, x[train], yt, params)(x[val])
        pc = np.clip(p, 1e-6, 1 - 1e-6)
        ll = log_loss(yv, pc)
        grid.append({"params": json.dumps(params, sort_keys=True), "log_loss": ll,
                     "brier": brier(yv, pc)})  # fmt: skip
        if best is None or ll < best[1]:
            best = (params, ll)
    params = dict(fixed_params) if fixed_params is not None else best[0]
    predictor = fit_binary("gbm", cols, x[train], yt, params)
    pred = np.full(len(df), np.nan)
    sc = score.to_numpy()
    in_val = (grp == "VALIDATION").to_numpy()
    in_train = (grp == "TRAIN").to_numpy()
    pred[in_val & sc] = predictor(x[in_val & sc])
    fold_pred: dict[int, Predictor] = {}
    folds = (df["match_id"].astype("int64") % N_FOLDS).to_numpy()
    for f in range(N_FOLDS):
        fit_rows, out_rows = train & (folds != f), in_train & sc & (folds == f)
        if not out_rows.any():
            continue
        assert_fit_on_train(df.loc[fit_rows, "match_id"], df)
        if set(df.loc[fit_rows, "match_id"]) & set(df.loc[out_rows, "match_id"]):
            raise ValueError("a TRAIN delivery would be scored by a model that saw its match")
        fold_pred[f] = fit_binary("gbm", cols, x[fit_rows], y.to_numpy()[fit_rows], params)
        pred[out_rows] = fold_pred[f](x[out_rows])
    pv = np.clip(pred[val], 1e-6, 1 - 1e-6)
    rep = calibration_report(yv, pv)
    const = fit_binary("const", cols, x[train], yt, {})(x[val])
    logit = fit_binary("logit", baseline_cols, x[train], yt, {})(x[val])
    ptr = pred[train]
    rep_tr = calibration_report(yt, np.clip(ptr, 1e-6, 1 - 1e-6))
    metrics = {
        "model": name, "n_validation": int(rep["n"]), "brier": rep["brier"],
        "brier_const": brier(yv, const), "brier_logit": brier(yv, np.clip(logit, 1e-6, 1 - 1e-6)),
        "brier_gain_vs_const": 1.0 - rep["brier"] / brier(yv, const),
        "brier_gain_vs_logit": 1.0 - rep["brier"] / brier(yv, np.clip(logit, 1e-6, 1 - 1e-6)),
        "log_loss": rep["log_loss"], "log_loss_const": log_loss(yv, const),
        "log_loss_logit": log_loss(yv, np.clip(logit, 1e-6, 1 - 1e-6)),
        "slope": rep["slope"], "intercept": rep["intercept"],
        "train_oof_brier": rep_tr["brier"], "train_oof_slope": rep_tr["slope"],
        "train_oof_brier_gain_vs_const": rep_tr["brier_gain"],
        "params": json.dumps(params, sort_keys=True),
    }  # fmt: skip
    return WPFit(
        name, params, predictor, pd.Series(pred, index=df.index), metrics, grid,
        rep["deciles"].to_dict("records"), int(train.sum()), int(val.sum()),
        int(df.loc[train, "match_id"].nunique()), int(train.sum()), fold_pred,
    )  # fmt: skip


def innings_gate(metrics: dict[str, Any]) -> dict[str, Any]:
    """Predeclared gate (design 7.2): slope in [0.8, 1.2] and Brier gain >= 2% over constant."""
    ok_slope = bool(WP_SLOPE_RANGE[0] <= metrics["slope"] <= WP_SLOPE_RANGE[1])
    ok_gain = bool(metrics["brier_gain_vs_const"] >= WP_MIN_BRIER_GAIN)
    return {"slope_ok": ok_slope, "brier_gain_ok": ok_gain, "passed": ok_slope and ok_gain}


def wp_labels(df: pd.DataFrame, labels: pd.DataFrame, innings: int) -> tuple[pd.Series, pd.Series]:
    """Batting-side-wins label and the labelled population for an innings (never imputed)."""
    lab = labels.set_index("match_id")
    ok = df["match_id"].map(lab["label_ok"]).fillna(False).astype(bool)
    win = df["match_id"].map(lab["win_team_id"])
    y = (win == df["batting_team_id"]).astype("float64")
    pop = (df["innings_number"] == innings) & ok
    return y.where(pop), pop


# ---------------------------------------------------------------------------------------------
# class model and leverage
# ---------------------------------------------------------------------------------------------
def class_target(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Next-ball class (0-6) for legal balls with trustworthy labels; NaN elsewhere."""
    legal = df["den_legal_inc"] == 1
    ok = df["ok_run_target"].astype(bool) & df["ok_wicket_target"].astype(bool)
    runs = df["out_batter_runs"]
    cls = pd.Series(np.nan, index=df.index)
    for k, r in enumerate([0, 1, 2, 3, 4, 6]):
        cls[(runs == r) & ~df["out_is_wicket"].astype(bool)] = k
    cls[df["out_is_wicket"].astype(bool)] = 6
    pop = legal & ok & cls.notna()
    return cls.where(pop), pop


def fit_class_model(x: pd.DataFrame, y: np.ndarray, params: dict[str, Any]) -> Predictor:
    m = _hgb(CLS_COLS, params)
    m.fit(x[CLS_COLS], y.astype(int))
    return Predictor("gbm", CLS_COLS, m)


CLS_PARAMS = {"max_depth": 5, "learning_rate": 0.1, "l2_regularization": 1.0}


def fit_class_oof(
    df: pd.DataFrame, x: pd.DataFrame, y: pd.Series, pop: pd.Series
) -> tuple[Predictor, dict[int, Predictor], dict[str, Any]]:
    """Fit the class model on TRAIN (declared fixed parameters, no tuning) with fold predictors."""
    grp = fit_group(df)
    train = (grp == "TRAIN").to_numpy() & pop.to_numpy()
    val = (grp == "VALIDATION").to_numpy() & pop.to_numpy()
    assert_fit_on_train(df.loc[train, "match_id"], df)
    full = fit_class_model(x[train], y.to_numpy()[train], CLS_PARAMS)
    folds = (df["match_id"].astype("int64") % N_FOLDS).to_numpy()
    fold_pred = {}
    for f in range(N_FOLDS):
        fit_rows = train & (folds != f)
        if set(df.loc[fit_rows, "match_id"]) & set(df.loc[train & (folds == f), "match_id"]):
            raise ValueError("class model fold shares a match with its fitting rows")
        fold_pred[f] = fit_class_model(x[fit_rows], y.to_numpy()[fit_rows], CLS_PARAMS)
    yv = y.to_numpy()[val].astype(int)
    pv = np.clip(_full_proba(full, x[val]), 1e-9, 1.0)
    prior = np.bincount(y.to_numpy()[train].astype(int), minlength=N_CLASS) / train.sum()
    ll = float(-np.mean(np.log(pv[np.arange(len(yv)), yv] / pv.sum(axis=1))))
    ll0 = float(-np.mean(np.log(np.clip(prior[yv], 1e-9, 1.0))))
    pw = pv[:, 6] / pv.sum(axis=1)
    metrics = {
        "n_train": int(train.sum()),
        "n_validation": int(val.sum()),
        "log_loss": ll,
        "log_loss_const": ll0,
        "log_loss_gain": 1.0 - ll / ll0,
        "wicket_brier": brier((yv == 6).astype(float), np.clip(pw, 0, 1)),
        "wicket_brier_const": brier((yv == 6).astype(float), np.full(len(yv), prior[6])),
        "params": json.dumps(CLS_PARAMS, sort_keys=True),
    }
    return full, fold_pred, metrics


def _full_proba(pred: Predictor, x: pd.DataFrame) -> np.ndarray:
    """Probabilities over all seven classes (a class absent from training gets probability 0)."""
    p = pred.proba(x)
    out = np.zeros((len(x), N_CLASS))
    out[:, pred.model.classes_.astype(int)] = p
    return out


def apply_wp(
    wp1: Predictor, wp2: Predictor, f: pd.DataFrame, innings: np.ndarray
) -> np.ndarray:  # fmt: skip
    """WP of the batting side per row (W2 for innings 2, W1 for innings 1), clipped."""
    out = np.full(len(f), np.nan)
    i2, i1 = innings == 2, innings == 1
    ok2 = i2 & f[W2_COLS].notna()[["runs_required", "rrr"]].all(axis=1).to_numpy()
    ok1 = i1 & f["legal_balls_remaining"].notna().to_numpy()
    if ok2.any():
        out[ok2] = wp2(f[ok2])
    if ok1.any():
        out[ok1] = wp1(f[ok1])
    return np.clip(out, *CLIP)


def next_state_wp(
    wp1: Predictor, wp2: Predictor, d: pd.DataFrame, runs: np.ndarray, wicket: np.ndarray,
    consume: np.ndarray,
) -> np.ndarray:  # fmt: skip
    """WP (batting side) after a hypothetical ball: ``runs`` added, ``wicket`` lost.

    ``d`` carries the pre-delivery state columns of the real rows. A chase that is won or lost is
    terminal (clip bound). The end of innings 1 maps to ``1 - WP2`` of the first chase ball.
    """
    innings = d["innings_number"].to_numpy()
    runs_t = d["team_runs_before"].to_numpy(dtype="float64") + runs
    wk = d["team_wickets_before"].to_numpy(dtype="float64") + wicket
    bb = d["legal_balls_bowled_before"].to_numpy(dtype="float64") + consume
    br = d["legal_balls_remaining"].to_numpy(dtype="float64") - consume
    lim = d["innings_limit_balls"].to_numpy(dtype="float64")
    comp = d["competition_type"].map(COMP_CODE).to_numpy(dtype="float64")
    chase = innings == 2
    tgt = np.where(chase, d["target"].to_numpy(dtype="float64"), np.nan)
    f = state_features(
        team_runs=runs_t, team_wickets=wk, balls_bowled=bb, balls_rem=br, limit=lim, target=tgt,
        comp_code=comp, bat_prior=d["bat_team_prior"], bowl_prior=d["bowl_team_prior"],
        par_prior=d["par_prior"],
    )  # fmt: skip
    out = apply_wp(wp1, wp2, f, innings)
    ended = (wk >= 10) | (br <= 0)
    won = chase & (tgt - runs_t <= 0)
    out = np.where(chase & won, CLIP[1], out)
    out = np.where(chase & ~won & ended, CLIP[0], out)
    inn1_end = (innings == 1) & ended
    if inn1_end.any():
        start = state_features(
            team_runs=np.zeros(len(d)), team_wickets=np.zeros(len(d)),
            balls_bowled=np.zeros(len(d)), balls_rem=lim, limit=lim, target=runs_t + 1.0,
            comp_code=comp, bat_prior=d["bowl_team_prior"], bowl_prior=d["bat_team_prior"],
            par_prior=np.full(len(d), np.nan),
        )  # fmt: skip
        chase_wp = apply_wp(wp1, wp2, start, np.full(len(d), 2))
        out = np.where(inn1_end, 1.0 - chase_wp, out)
    return np.clip(out, *CLIP)


def leverage_and_components(
    wp1: Predictor, wp2: Predictor, cls: Predictor, d: pd.DataFrame, wp_before: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Leverage ``sum_k p_k |WP_k - WP_before|`` and the class probabilities (N x 7)."""
    x = state_features(
        team_runs=d["team_runs_before"], team_wickets=d["team_wickets_before"],
        balls_bowled=d["legal_balls_bowled_before"], balls_rem=d["legal_balls_remaining"],
        limit=d["innings_limit_balls"], target=np.where(d["innings_number"] == 2, d["target"], np.nan),
        comp_code=d["competition_type"].map(COMP_CODE), bat_prior=d["bat_team_prior"],
        bowl_prior=d["bowl_team_prior"], par_prior=d["par_prior"],
        phase_code=d["innings_phase"].map(PHASE_CODE), innings=d["innings_number"],
    )  # fmt: skip
    p = _full_proba(cls, x)
    swing = np.zeros_like(p)
    ones = np.ones(len(d))
    for k in range(N_CLASS):
        wpk = next_state_wp(wp1, wp2, d, CLASS_RUNS[k] * ones, float(CLASS_WICKET[k]) * ones, ones)
        swing[:, k] = np.abs(wpk - wp_before)
    lev = (p * swing).sum(axis=1)
    return np.where(np.isfinite(wp_before), lev, np.nan), p


# ---------------------------------------------------------------------------------------------
# WP timeline
# ---------------------------------------------------------------------------------------------
def wp_after_series(
    df: pd.DataFrame, wp_before: pd.Series, labels: pd.DataFrame
) -> pd.Series:  # fmt: skip
    """``WP_after`` of each delivery from the next row of the same innings (never a future outcome
    except the terminal ball, which takes the result label of its own match)."""
    d = pd.DataFrame(
        {
            "m": df["match_id"].to_numpy(), "i": df["innings_number"].to_numpy(),
            "n": df["innings_ball_num"].to_numpy(), "wp": wp_before.to_numpy(),
            "bat": df["batting_team_id"].to_numpy(),
        }
    )  # fmt: skip
    d["pos"] = np.arange(len(d))
    d = d.sort_values(["m", "i", "n"], kind="stable")
    nxt_wp = d.groupby(["m", "i"])["wp"].shift(-1)
    nxt_n = d.groupby(["m", "i"])["n"].shift(-1)
    contiguous = (nxt_n - d["n"]) == 1
    after = nxt_wp.where(contiguous)
    last = nxt_n.isna()
    lab = labels.set_index("match_id")
    ok = d["m"].map(lab["label_ok"]).fillna(False).astype(bool)
    win = d["m"].map(lab["win_team_id"])
    term_label = np.where(ok, np.where(win == d["bat"], CLIP[1], CLIP[0]), np.nan)
    inn2_last = last & (d["i"] == 2)
    after = after.where(~inn2_last, pd.Series(term_label, index=d.index))
    first2 = d[d["i"] == 2].groupby("m").first()["wp"]
    inn1_last = last & (d["i"] == 1)
    chase = d["m"].map(first2)
    after = after.where(~inn1_last, 1.0 - chase)
    res = pd.Series(np.nan, index=df.index)
    res.iloc[d["pos"].to_numpy()] = after.clip(*CLIP).to_numpy()
    return res


def save_wp_artifact(
    fits: dict[str, WPFit], cls: Predictor, meta: dict[str, Any], models_dir: Any = MODELS_DIR
) -> Any:  # fmt: skip
    """Versioned artefact ``p8_wp_v1.joblib`` plus metadata ``p8_wp_v1.json``."""
    from pathlib import Path

    d = Path(models_dir)
    d.mkdir(parents=True, exist_ok=True)
    stem = d / f"{active_prefix()}wp_v1"
    joblib.dump(
        {"w1": fits["W1"].predictor, "w2": fits["W2"].predictor, "cls": cls,
         "w1_cols": W1_COLS, "w2_cols": W2_COLS, "cls_cols": CLS_COLS},
        stem.with_suffix(".joblib"),
    )  # fmt: skip
    body = {
        **meta, "algorithm": "HistGradientBoostingClassifier",
        "version": f"{active_prefix()}wp_v1", "targets": {"W2": "chasing side wins", "W1": "batting side wins",
                                           "CLS": "next legal ball class (0,1,2,3,4,6,wicket)"},
        "features": {"W1": W1_COLS, "W2": W2_COLS, "CLS": CLS_COLS},
        "metrics": {k: {a: b for a, b in v.metrics.items()} for k, v in fits.items()},
        "training": {k: {"train_matches": v.train_matches, "train_deliveries": v.n_train,
                         "validation_deliveries": v.n_validation, "params": v.chosen_params}
                     for k, v in fits.items()},
    }  # fmt: skip
    stem.with_suffix(".json").write_text(
        json.dumps(body, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return stem.with_suffix(".joblib")
