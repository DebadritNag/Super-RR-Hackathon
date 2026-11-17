"""Phase 8 chunk 6: independent audit of the trained models and the experimental AI output.

The experimental AI list is the out-of-sample (VALIDATION, calendar 2025) mean difference between
what a player achieved on high-pressure deliveries and what the saved gradient-boosting artefact
expected for the same pre-delivery state. It is NOT the submitted ranking and is NOT validated.
No TEST row is loaded (``load_pre_test_deliveries`` filters them). Nothing is hardcoded: every
value comes from the artefacts and the stored deliveries.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.phase8.constants import MODELS_DIR, SEED
from app.phase8.expected import SPECS, prepare_features, spec_for, target_frame

ARTEFACT_STEMS = [f"p8_expected_{s.role}_{s.name}_v1" for s in SPECS] + ["p8_wp_v1"]
HIGH_CUT = 0.5
MIN_PRESSURE_BALLS = 40
MIN_PRESSURE_MATCHES = 8
LABEL = "EXPERIMENTAL_NOT_VALIDATED"
STATUS_TEXT = (
    "EXPERIMENTAL AI OUTPUT. NOT the submitted ranking and NOT validated. One calendar year of "
    "out-of-sample deliveries (2025); interval uses match clusters; no shrinkage is applied."
)
SCORE_DEF = {
    "batter": "mean of (actual runs off the bat minus artefact-expected runs) per pressure ball",
    "bowler": "mean of (artefact-expected minus actual runs charged) per pressure delivery",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_artefact(stem: str, models_dir: Path | str = MODELS_DIR) -> dict[str, Any]:
    d = Path(models_dir)
    obj = joblib.load(d / f"{stem}.joblib")
    meta = json.loads((d / f"{stem}.json").read_text(encoding="utf-8"))
    return {"obj": obj, "meta": meta, "sha256": sha256_file(d / f"{stem}.joblib")}


def artefact_inventory(models_dir: Path | str = MODELS_DIR) -> list[dict[str, Any]]:
    rows = []
    for stem in ARTEFACT_STEMS:
        p = Path(models_dir) / f"{stem}.joblib"
        j = Path(models_dir) / f"{stem}.json"
        row: dict[str, Any] = {"artefact": stem, "exists": p.exists() and j.exists()}
        if row["exists"]:
            a = load_artefact(stem, models_dir)
            m = a["meta"]
            row.update(
                {
                    "bytes": p.stat().st_size,
                    "sha256": a["sha256"],
                    "algorithm": m.get("algorithm"),
                    "trained_on": m.get("trained_on", "TRAIN"),
                    "seed": m.get("seed"),
                    "version": m.get("version"),
                }
            )
        rows.append(row)
    return rows


def expected_from_artefact(df: pd.DataFrame, role: str, name: str, models_dir: Any = MODELS_DIR):
    """Prediction made by the stored predictor object (the only source of the expectation)."""
    a = load_artefact(f"p8_expected_{role}_{name}_v1", models_dir)
    x = prepare_features(df, a["obj"]["codes"])
    x = x[a["obj"]["features"]]
    return pd.Series(a["obj"]["predictor"](x), index=df.index), a


def _cluster_mean(res: pd.Series, match_id: pd.Series) -> tuple[float, float, int]:
    """Mean residual with a match-cluster standard error (ratio estimator)."""
    d = pd.DataFrame({"r": res.to_numpy(), "m": match_id.to_numpy()})
    g = d.groupby("m")["r"].agg(["sum", "count"])
    n = float(g["count"].sum())
    mean = float(g["sum"].sum() / n)
    k = len(g)
    if k < 2:
        return mean, float("nan"), k
    e = g["sum"] - mean * g["count"]
    se = float(np.sqrt(k / (k - 1) * float((e**2).sum())) / n)
    return mean, se, k


def experimental_scores(
    df: pd.DataFrame, w: pd.Series, role: str, names: pd.Series, models_dir: Any = MODELS_DIR
) -> pd.DataFrame:
    """Per-player out-of-sample pressure residual from the saved runs and wicket artefacts."""
    runs_spec = spec_for(role, "runs")
    wk_spec = spec_for(role, "wicket")
    exp_runs, a_runs = expected_from_artefact(df, role, "runs", models_dir)
    exp_wk, a_wk = expected_from_artefact(df, role, "wicket", models_dir)
    y_runs, pop_r = target_frame(df, runs_spec)
    y_wk, pop_w = target_frame(df, wk_spec)
    col = "striker_id" if role == "batter" else "bowler_id"
    use = (df["period"] == "VALIDATION") & (w >= HIGH_CUT) & pop_r
    res_r = runs_spec.sign * (y_runs - exp_runs)
    res_w = wk_spec.sign * (y_wk - exp_wk)
    out = []
    for pid, idx in df[use].groupby(col).groups.items():
        d = df.loc[idx]
        mean, se, k = _cluster_mean(res_r.loc[idx], d["match_id"])
        wk_idx = [i for i in idx if bool(pop_w.loc[i])]
        wk_mean = float(res_w.loc[wk_idx].mean()) if wk_idx else float("nan")
        out.append(
            {
                "player_id": int(pid),
                "pressure_balls": int(len(idx)),
                "pressure_matches": int(k),
                "mean_runs_residual": mean,
                "se_match_cluster": se,
                "mean_wicket_residual": wk_mean,
                "actual_runs_per_ball": float(y_runs.loc[idx].mean()),
                "expected_runs_per_ball": float(exp_runs.loc[idx].mean()),
                "mean_intensity": float(w.loc[idx].mean()),
                "ipl_balls": int((d["competition_type"] == "IPL").sum()),
                "t20i_balls": int((d["competition_type"] == "T20I").sum()),
            }
        )
    t = pd.DataFrame(out)
    if t.empty:
        return t
    t["player_name"] = t["player_id"].map(names)
    t["ci_low"] = t["mean_runs_residual"] - 1.96 * t["se_match_cluster"]
    t["ci_high"] = t["mean_runs_residual"] + 1.96 * t["se_match_cluster"]
    t["eligible"] = (t["pressure_balls"] >= MIN_PRESSURE_BALLS) & (
        t["pressure_matches"] >= MIN_PRESSURE_MATCHES
    )
    t["role"] = role
    t["model_artefact_runs_sha256"] = a_runs["sha256"]
    t["model_artefact_wicket_sha256"] = a_wk["sha256"]
    return t


def top10(scores: pd.DataFrame) -> pd.DataFrame:
    """Order by the model output; ties broken by player_id; only eligible rows; at most ten."""
    e = scores[scores["eligible"]].sort_values(
        ["mean_runs_residual", "player_id"], ascending=[False, True], kind="mergesort"
    )
    e = e.head(10).copy()
    e.insert(0, "model_output_order", range(1, len(e) + 1))
    e["interval_excludes_zero"] = (e["ci_low"] > 0) | (e["ci_high"] < 0)
    e["model_output_definition"] = SCORE_DEF[scores["role"].iloc[0]] if len(scores) else ""
    e["status_label"] = LABEL
    e["banner"] = STATUS_TEXT
    e["eligibility_rule"] = (
        f">= {MIN_PRESSURE_BALLS} validation-year pressure balls in >= {MIN_PRESSURE_MATCHES} matches"
    )
    return e


def retrain_check(df: pd.DataFrame, role: str, name: str, models_dir: Any = MODELS_DIR) -> dict:
    """Refit the chosen configuration on TRAIN only and compare with the stored artefact."""
    from app.phase8.expected import fit_predict

    spec = spec_for(role, name)
    a = load_artefact(f"p8_expected_{role}_{name}_v1", models_dir)
    y, pop = target_frame(df, spec)
    x = prepare_features(df, a["obj"]["codes"])
    tr = ((df["period"] == "TRAIN") & pop).to_numpy()
    va = ((df["period"] == "VALIDATION") & pop).to_numpy()
    params = json.loads(a["meta"]["params"]) if isinstance(a["meta"]["params"], str) else {}
    pred = fit_predict(a["meta"]["algorithm"], spec.kind, params, x[tr], y.to_numpy()[tr])
    new = pred(x[va])
    old = a["obj"]["predictor"](x[a["obj"]["features"]][va])
    yv = y.to_numpy()[va]
    if spec.kind == "reg":
        rm_new = float(np.sqrt(np.mean((yv - new) ** 2)))
        rm_old = float(np.sqrt(np.mean((yv - old) ** 2)))
        rm_const = float(np.sqrt(np.mean((yv - y.to_numpy()[tr].mean()) ** 2)))
        key = "rmse"
    else:
        p = np.clip(new, 1e-6, 1 - 1e-6)
        po = np.clip(old, 1e-6, 1 - 1e-6)
        pc = float(y.to_numpy()[tr].mean())
        rm_new = float(-np.mean(yv * np.log(p) + (1 - yv) * np.log(1 - p)))
        rm_old = float(-np.mean(yv * np.log(po) + (1 - yv) * np.log(1 - po)))
        rm_const = float(-np.mean(yv * np.log(pc) + (1 - yv) * np.log(1 - pc)))
        key = "log_loss"
    return {
        "artefact": f"p8_expected_{role}_{name}_v1",
        "metric": key,
        "retrained": rm_new,
        "stored_artefact": rm_old,
        "constant_baseline": rm_const,
        "stored_json_metric": a["meta"].get(f"chosen_{key}"),
        "max_abs_prediction_diff": float(np.max(np.abs(new - old))),
        "n_train": int(tr.sum()),
        "n_validation": int(va.sum()),
        "seed": SEED,
    }
