"""Expected-outcome models for Approach A (pre-delivery information only, player-blind).

Per role and target one learner is chosen in a single pass on VALIDATION from the predeclared grid.
Fitting uses TRAIN only. TRAIN deliveries are scored out of fold (``match_id % 5``) so that no
delivery is scored by a model that saw its match; VALIDATION deliveries are scored by the model
fitted on all of TRAIN. The residual is ``observed - expected`` (undefined, never zero, when the
target or the expected value is missing). Orientation signs make a positive residual mean better.

Declared deviations (see the results report): no early stopping on an internal grouped holdout (the
iteration count is fixed at the declared 200 and regularised by the grid) and no isotonic
recalibration (calibration slope, intercept and decile tables are reported instead).
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from app.phase8.calibration import brier, calibration_slope_intercept, decile_table, log_loss
from app.phase8.constants import MODELS_DIR, N_FOLDS, SEED
from app.phase8.data import FEATURE_COLS, assert_feature_list_clean
from app.phase8.splits import assert_fit_on_train

CATEGORICAL = ["competition_type", "stage", "innings_phase"]
GRID = {
    "max_depth": [3, 5],
    "learning_rate": [0.05, 0.1],
    "l2_regularization": [0.0, 1.0],
}
MAX_ITER = 200
MIN_LEAF = 200


@dataclass(frozen=True)
class TargetSpec:
    """One expected-outcome target: population, label, validity flag and orientation."""

    role: str
    name: str
    kind: str  # "reg" or "clf"
    sign: int  # +1 when a positive residual is good for the player, -1 otherwise
    ok_col: str


SPECS: tuple[TargetSpec, ...] = (
    TargetSpec("batter", "runs", "reg", +1, "ok_run_target"),
    TargetSpec("batter", "wicket", "clf", -1, "ok_wicket_target"),
    TargetSpec("batter", "dot", "clf", -1, "ok_run_target"),
    TargetSpec("batter", "boundary", "clf", +1, "ok_run_target"),
    TargetSpec("bowler", "runs", "reg", -1, "ok_run_target"),
    TargetSpec("bowler", "wicket", "clf", +1, "ok_wicket_target"),
    TargetSpec("bowler", "dot", "clf", +1, "ok_run_target"),
    TargetSpec("bowler", "boundary", "clf", -1, "ok_run_target"),
)


def spec_for(role: str, name: str) -> TargetSpec:
    for s in SPECS:
        if s.role == role and s.name == name:
            return s
    raise KeyError((role, name))


def prepare_features(
    df: pd.DataFrame, codes: dict[str, dict[str, int]] | None = None
) -> pd.DataFrame:
    """Numeric feature matrix from pre-delivery columns only (row-wise: no look-ahead).

    Categorical columns become integer codes (unknown category -> NaN, never 0). The column list is
    checked by ``assert_feature_list_clean``.
    """
    cols = assert_feature_list_clean(list(FEATURE_COLS))
    x = pd.DataFrame(index=df.index)
    for c in cols:
        s = df[c] if c in df.columns else pd.Series(np.nan, index=df.index)
        if c in CATEGORICAL:
            cmap = (codes or {}).get(c) or {v: i for i, v in enumerate(sorted(s.dropna().unique()))}
            x[c] = s.map(cmap).astype("float64")
        elif s.dtype == bool or str(s.dtype) == "boolean":
            x[c] = s.astype("float64")
        else:
            x[c] = pd.to_numeric(s, errors="coerce").astype("float64")
    return x


def category_codes(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Fixed category-to-code maps (depends only on which labels exist, not on outcomes)."""
    return {
        c: {v: i for i, v in enumerate(sorted(df[c].dropna().unique()))}
        for c in CATEGORICAL
        if c in df.columns
    }


def target_frame(df: pd.DataFrame, spec: TargetSpec) -> tuple[pd.Series, pd.Series]:
    """Label ``y`` (NaN outside the population) and the population mask for one target."""
    legal = df["den_legal_inc"] == 1
    faced = df["den_counts_as_ball_faced"] == 1
    ok = df[spec.ok_col].astype(bool)
    if spec.role == "batter":
        pop = faced & ok
        if spec.name == "runs":
            y = df["out_batter_runs"].astype("float64")
        elif spec.name == "wicket":
            y = (df["out_is_wicket"] & (df["out_dismissed_player_id"] == df["striker_id"])).astype(
                "float64"
            )
        elif spec.name == "dot":
            y = (df["out_batter_runs"] == 0).astype("float64")
        else:
            y = (df["out_is_four"] | df["out_is_six"]).astype("float64")
    else:
        if spec.name == "runs":
            pop = ok  # charged runs include wides and no-balls, so all deliveries
            y = df["den_bowler_charged_runs"].astype("float64")
        else:
            pop = legal & ok
            if spec.name == "wicket":
                y = df["den_bowler_credited_wicket"].astype("float64")
            elif spec.name == "dot":
                y = (df["den_bowler_charged_runs"] == 0).astype("float64")
            else:
                y = (df["out_is_four"] | df["out_is_six"]).astype("float64")
    return y.where(pop), pop


def _make(kind: str, params: dict[str, Any]) -> Any:
    cat = [c in CATEGORICAL for c in FEATURE_COLS]
    cls = HistGradientBoostingRegressor if kind == "reg" else HistGradientBoostingClassifier
    return cls(
        max_iter=MAX_ITER,
        min_samples_leaf=MIN_LEAF,
        early_stopping=False,
        random_state=SEED,
        categorical_features=cat,
        **params,
    )


class _Lookup:
    """Mean of the label by (innings phase, wickets remaining); constant fallback."""

    def __init__(self) -> None:
        self.table: pd.Series | None = None
        self.const = float("nan")

    def fit(self, x: pd.DataFrame, y: np.ndarray) -> _Lookup:
        d = pd.DataFrame(
            {"a": x["innings_phase"].to_numpy(), "b": x["wickets_remaining"].to_numpy(), "y": y}
        )
        self.table = d.groupby(["a", "b"])["y"].mean()
        self.const = float(np.mean(y))
        return self

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        idx = pd.MultiIndex.from_arrays(
            [x["innings_phase"].to_numpy(), x["wickets_remaining"].to_numpy()]
        )
        out = self.table.reindex(idx).to_numpy()
        return np.where(np.isfinite(out), out, self.const)


class Predictor:
    """Picklable predictor: probabilities for ``clf``, values for ``reg``."""

    def __init__(self, how: str, kind: str, model: Any) -> None:
        self.how, self.kind, self.model = how, kind, model

    def __call__(self, x: pd.DataFrame) -> np.ndarray:
        if self.how == "const":
            return np.full(len(x), self.model)
        if self.how == "lookup":
            return self.model.predict(x)
        if self.kind == "clf":
            return self.model.predict_proba(x)[:, 1]
        return self.model.predict(x)


def fit_predict(
    kind_model: str, kind: str, params: dict[str, Any], x_fit: pd.DataFrame, y_fit: np.ndarray
) -> Callable[[pd.DataFrame], np.ndarray]:
    """Fit ``gbm``, ``lookup`` or ``const`` and return a predictor (probabilities for ``clf``)."""
    if kind_model == "const":
        return Predictor("const", kind, float(np.mean(y_fit)))
    if kind_model == "lookup":
        return Predictor("lookup", kind, _Lookup().fit(x_fit, y_fit))
    m = _make(kind, params)
    m.fit(x_fit, y_fit.astype(int) if kind == "clf" else y_fit)
    return Predictor("gbm", kind, m)


def _metrics(kind: str, y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    if kind == "reg":
        return {"rmse": float(np.sqrt(np.mean((y - p) ** 2))), "mae": float(np.mean(np.abs(y - p)))}
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"log_loss": log_loss(y, p), "brier": brier(y, p)}


def primary_metric(kind: str) -> str:
    return "rmse" if kind == "reg" else "log_loss"


def grid_points() -> list[dict[str, Any]]:
    keys = sorted(GRID)
    return [dict(zip(keys, v, strict=True)) for v in itertools.product(*(GRID[k] for k in keys))]


def score_target(
    df: pd.DataFrame,
    x: pd.DataFrame,
    spec: TargetSpec,
    fit: Callable[..., Callable[[pd.DataFrame], np.ndarray]] = fit_predict,
) -> dict[str, Any]:
    """Select, fit and score one target. Returns expected values, metrics and the TRAIN model.

    ``expected`` is aligned with ``df`` (NaN outside the target population). The selection pass uses
    VALIDATION once; the OOF scoring then reuses the chosen parameters only.
    """
    y, pop = target_frame(df, spec)
    is_train = (df["period"] == "TRAIN").to_numpy()
    is_val = (df["period"] == "VALIDATION").to_numpy()
    tr = is_train & pop.to_numpy()
    va = is_val & pop.to_numpy()
    yt, yv = y.to_numpy()[tr], y.to_numpy()[va]
    assert_fit_on_train(df.loc[tr, "match_id"], df)
    xt, xv = x[tr], x[va]
    pm = primary_metric(spec.kind)
    rows, best = [], None
    for params in grid_points():
        pred = fit("gbm", spec.kind, params, xt, yt)(xv)
        m = _metrics(spec.kind, yv, pred)
        rows.append({"params": json.dumps(params, sort_keys=True), **m})
        if best is None or m[pm] < best[1][pm]:
            best = (params, m)
    base = {}
    for name in ("const", "lookup"):
        base[name] = _metrics(spec.kind, yv, fit(name, spec.kind, {}, xt, yt)(xv))
    gbm_params, gbm_m = best
    chosen = "gbm" if gbm_m[pm] < base["const"][pm] else min(base, key=lambda k: base[k][pm])
    params_used = gbm_params if chosen == "gbm" else {}
    predictor = fit(chosen, spec.kind, params_used, xt, yt)
    expected = np.full(len(df), np.nan)
    expected[va] = predictor(xv)
    folds = (df["match_id"].astype("int64") % N_FOLDS).to_numpy()
    for f in range(N_FOLDS):
        fit_rows = tr & (folds != f)
        out_rows = tr & (folds == f)
        if not out_rows.any():
            continue
        assert_fit_on_train(df.loc[fit_rows, "match_id"], df)
        if set(df.loc[fit_rows, "match_id"]) & set(df.loc[out_rows, "match_id"]):
            raise ValueError("a TRAIN delivery would be scored by a model that saw its match")
        expected[out_rows] = fit(
            chosen, spec.kind, params_used, x[fit_rows], y.to_numpy()[fit_rows]
        )(x[out_rows])
    metrics: dict[str, Any] = {
        "role": spec.role,
        "target": spec.name,
        "kind": spec.kind,
        "chosen": chosen,
        "params": json.dumps(params_used, sort_keys=True),
        "primary_metric": pm,
        "n_train": int(tr.sum()),
        "n_validation": int(va.sum()),
        "grid": rows,
    }
    for k, v in gbm_m.items():
        metrics[f"gbm_{k}"] = v
    for name, m in base.items():
        for k, v in m.items():
            metrics[f"{name}_{k}"] = v
    metrics["gain_vs_const_pct"] = float(100.0 * (1.0 - gbm_m[pm] / base["const"][pm]))
    final = _metrics(spec.kind, yv, expected[va])
    for k, v in final.items():
        metrics[f"chosen_{k}"] = v
    if spec.kind == "clf":
        metrics.update(
            {f"chosen_{k}": v for k, v in calibration_slope_intercept(yv, expected[va]).items()}
        )
        metrics["deciles"] = decile_table(yv, np.clip(expected[va], 0, 1)).to_dict("records")
    return {"expected": pd.Series(expected, index=df.index), "y": y, "pop": pop, "metrics": metrics,
            "predictor": predictor, "chosen": chosen, "params": params_used}  # fmt: skip


def save_artifact(
    result: dict[str, Any], spec: TargetSpec, codes: dict[str, Any], meta: dict[str, Any],
    models_dir: Path | str = MODELS_DIR,
) -> Path:  # fmt: skip
    """Write the fitted predictor (``.joblib``) and its metadata (``.json``)."""
    d = Path(models_dir)
    d.mkdir(parents=True, exist_ok=True)
    stem = d / f"p8_expected_{spec.role}_{spec.name}_v1"
    joblib.dump({"predictor": result["predictor"], "codes": codes, "features": list(FEATURE_COLS)},
                stem.with_suffix(".joblib"))  # fmt: skip
    m = {k: v for k, v in result["metrics"].items() if k not in ("grid", "deciles")}
    stem.with_suffix(".json").write_text(
        json.dumps({**meta, **m, "features": list(FEATURE_COLS), "target": f"{spec.role}_{spec.name}",
                    "algorithm": result["chosen"]}, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )  # fmt: skip
    return stem.with_suffix(".joblib")


def oriented_residual(result: dict[str, Any], spec: TargetSpec) -> pd.Series:
    """``sign * (observed - expected)`` so that positive is better for the player."""
    return spec.sign * (result["y"] - result["expected"])
