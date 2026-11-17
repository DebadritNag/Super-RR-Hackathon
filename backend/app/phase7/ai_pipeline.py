"""Phase 7 chunk 5: verification run of the existing statistical baseline/shrinkage pipeline.
There is no trained machine-learning or deep-learning model in this project (see the audit in
``ai_pipeline_verification.md``). The only predictive machinery is the Phase 4 stratified
empirical-Bayes baseline B0 plus shrinkage of player residuals. This module wraps that existing
code, adds no new model, and labels it ``MODEL_LABEL`` everywhere.
Rules enforced here:
* TRAIN-only fit (baseline cells, thresholds, shrinkage k); VALIDATION used for evaluation only.
* The state table is read with a date filter, so TEST rows (and their outcome columns) are never
  loaded. The TEST lock log is hashed before and after; a change aborts the run.
* No ``TestLock`` is instantiated, no database is written. Outputs are CSV and JSON files.
* Experimental outputs carry no uncertainty (the model has no calibrated uncertainty).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from app.analytics import pressure_features as pf
from app.phase4 import baseline as bl
from app.phase4 import scoring as sc
from app.phase4 import shrink as sh
from app.phase4.baseline import STREAMS, role_frame
from app.phase4.constants import FROZEN_CHOICES, LOCK_LOG, REPORTS_DIR, SCOPE, SEED, SPLIT_CONFIG
from app.phase4.split import Split, attach_period
from app.phase5.lockguard import PHASE5_LOCK_LOG, assert_phase5_lock_not_opened, file_sha256
from app.services.pressure_service import EXPLORATORY_DB, STATE_TABLE

MODEL_LABEL = "statistical baseline/shrinkage model (not machine learning or deep learning)"
MODEL_ID = "p7_stat_baseline_shrinkage_v1"
GATE_STATUS = "INTERNAL_EXPERIMENTAL_ONLY"
PUBLICATION_STATUS = "EXPERIMENTAL_NOT_VALIDATED_INTERNAL_ONLY"
NO_UNCERTAINTY = "not available: model does not produce calibrated uncertainty"
POOLED_RELIABILITY = 0.37
BANNER = (
    "INTERNAL TECHNICAL VERIFICATION (INTERNAL EXPERIMENTAL OUTPUT), NOT A VALIDATED RANKING. Phase 6 found player order unreliable "
    f"(pooled odd/even reliability {POOLED_RELIABILITY}). All publication gates fail. "
    "Not for publication."
)
MODEL_OUTPUT_DEFINITION = {
    "batter": (
        "shrunk mean residual of runs per ball faced under pressure (actual minus calibrated "
        "baseline expectation); positive = more runs per ball than the baseline expects"
    ),
    "bowler": (
        "shrunk mean residual of runs conceded per ball under pressure with the sign flipped "
        "(baseline expectation minus actual); positive = fewer runs conceded per ball than the "
        "baseline expects"
    ),
}
PRIMARY = {"batter": ("runs", 1.0), "bowler": ("charged", -1.0)}
DEFINITION = "any|q0.75"
FORMAT_SCOPE = "IPL"
TOP_N = 10
CSV_NAMES = {
    "batter": "experimental_ai_top10_batters_phase7_aborted.csv",
    "bowler": "experimental_ai_top10_bowlers_phase7_aborted.csv",
}
REGISTRY_NAME = "phase7_model_registry.json"
METRICS_NAME = "phase7_ai_pipeline_metrics.json"
ELIGIBILITY_CSV = "phase4_eligibility_frozen.csv"
CODE_FILES = (
    "app/phase4/baseline.py",
    "app/phase4/shrink.py",
    "app/phase4/scoring.py",
    "app/phase4/engine.py",
    "app/phase7/ai_pipeline.py",
)
CSV_COLUMNS = [
    "model_output_order",
    "player_id",
    "player_name",
    "format_scope",
    "model_output_value",
    "model_output_definition",
    "uncertainty",
    "historical_pressure_balls",
    "historical_pressure_matches",
    "observed_pressure_mean",
    "baseline_expected_pressure_mean",
    "unshrunk_mean_residual",
    "data_weight",
    "observed_total_balls",
    "observed_total_runs",
    "observed_dismissals_or_wickets",
    "observed_total_matches",
    "model_label",
    "model_version",
    "training_data_version",
    "prediction_timestamp_utc",
    "eligibility_flag",
    "data_quality_flags",
    "methodology_gate_status",
    "explanation",
    "experimental_publication_status",
    "banner",
]


class PipelineError(RuntimeError):
    """The verification run cannot proceed or violated a guard."""


def _sha(path: Path | str) -> str:
    return file_sha256(path)


def _frame_digest(df: pd.DataFrame, cols: list[str]) -> str:
    h = pd.util.hash_pandas_object(df[cols], index=False).to_numpy()
    return hashlib.sha256(h.tobytes()).hexdigest()


# ---------------------------------------------------------------- lock evidence
def lock_snapshot(p4: Path | str = LOCK_LOG, p5: Path | str = PHASE5_LOCK_LOG) -> dict[str, Any]:
    p4p, p5p = Path(p4), Path(p5)
    events = json.loads(p4p.read_text(encoding="utf-8")) if p4p.exists() else []
    return {
        "phase4_lock_log_sha256": _sha(p4p) if p4p.exists() else None,
        "phase4_events": [e.get("event") for e in events],
        "phase5_lock_log_sha256": _sha(p5p) if p5p.exists() else None,
        "phase5_open_events": 0 if not p5p.exists() else int(_p5_open_count(p5p)),
    }


def _p5_open_count(p5p: Path) -> int:
    raw = json.loads(p5p.read_text(encoding="utf-8") or "[]")
    return sum(1 for e in raw if isinstance(e, dict) and e.get("event") == "OPEN")


# ---------------------------------------------------------------- data loading (no TEST rows)
def load_pretest_state(store: Path | str, split: Split) -> pd.DataFrame:
    """TRAIN and VALIDATION matches only: the date filter runs in SQL, before any row is read."""
    cols = list(pf.STATE_COLS)
    cutoff = (split.validation_end + pd.Timedelta(days=1)).to_pydatetime()
    con = duckdb.connect(str(store), read_only=True)
    try:
        df = con.execute(
            f"SELECT {', '.join(cols)} FROM {STATE_TABLE} WHERE match_date < ? "
            "ORDER BY match_id, innings_number, innings_ball_num",
            [cutoff],
        ).df()
    finally:
        con.close()
    df["match_date"] = pd.to_datetime(df["match_date"])
    out = attach_period(df, split)
    if bool((out["period"] == "TEST").any()):
        raise PipelineError("TEST rows reached the pipeline frame")
    return out


def test_match_ids(store: Path | str) -> set[int]:
    """Identifiers only (no outcome columns) of TEST matches, used to prove none were loaded."""
    con = duckdb.connect(str(store), read_only=True)
    try:
        rows = con.execute("SELECT match_id FROM p4_match_period WHERE period = 'TEST'").fetchall()
    finally:
        con.close()
    return {int(r[0]) for r in rows}


def read_table(store: Path | str, sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(store), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


# ---------------------------------------------------------------- residual rows (no lock object)
def pressure_rows(
    d: pd.DataFrame, bs: bl.BaselineSet, thr: dict[str, float], role: str, stream: str
) -> pd.DataFrame:
    """Pressure rows of one role/stream with actual, expected and residual (TEST refused)."""
    if bool((d["period"] == "TEST").any()):
        raise PipelineError("TEST rows refused in pressure_rows")
    flag = sc.pressure_flag(d, DEFINITION, thr)
    fr = role_frame(role, d)
    ex = bs.expected(role, stream, fr)
    keep = flag.reindex(fr["_src_index"]).to_numpy()
    t = pd.DataFrame(
        {
            "player_id": fr["player_id"].to_numpy(),
            "match_id": fr["match_id"].to_numpy(),
            "comp": fr["competition_type"].to_numpy(),
            "period": fr["period"].to_numpy(),
            "actual": fr[stream].to_numpy(dtype=float),
            "expected": ex["expected"].to_numpy(),
        }
    )[keep]
    t["resid"] = t["actual"] - t["expected"]
    return t.reset_index(drop=True)


# ---------------------------------------------------------------- diagnostics
def data_checks(raw: pd.DataFrame, d: pd.DataFrame, names: pd.DataFrame) -> dict[str, Any]:
    """Record counts, missing values, player-id consistency and the leakage assertions."""
    key_cols = [
        "match_id", "match_date", "competition_type", "striker_id", "bowler_id", "chase_flag",
        "wickets_remaining", "legal_balls_bowled_before", "innings_phase", "team_runs_before",
        "out_batter_runs", "out_is_wicket", "den_bowler_charged_runs",
    ]  # fmt: skip
    missing = {c: int(raw[c].isna().sum()) for c in key_cols}
    chase = raw[raw["chase_flag"].fillna(False).astype(bool)]
    ids = pd.concat([raw["striker_id"], raw["bowler_id"]]).dropna().astype("int64").unique()
    named = set(names["player_id"].astype("int64"))
    unnamed = [int(i) for i in ids if int(i) not in named]
    same = int((raw["striker_id"] == raw["bowler_id"]).sum())
    per_period = {
        p: {
            "matches": int(g["match_id"].nunique()),
            "deliveries": int(len(g)),
            "players": int(pd.concat([g["striker_id"], g["bowler_id"]]).dropna().nunique()),
        }
        for p, g in raw.groupby("period")
    }
    leak_cols = [c for c in pf.STATE_COLS if c.startswith(("out_", "den_", "post_innings_"))]
    cell_keys = ["competition_type", "role_ctx", "innings_phase", "wbin"]
    return {
        "rows_total": int(len(raw)),
        "per_period": per_period,
        "distinct_players": int(len(ids)),
        "missing_counts_key_columns": missing,
        "rrr_missing_in_chase_rows": int(chase["rrr"].isna().sum()),
        "chase_rows": int(len(chase)),
        "player_ids_without_name_in_classification": len(unnamed),
        "player_ids_without_name_sample": unnamed[:10],
        "rows_striker_equals_bowler": same,
        "baseline_cell_key_columns": cell_keys,
        "baseline_cell_keys_use_outcome_columns": any(
            k.startswith(("out_", "den_")) for k in cell_keys
        ),
        "outcome_columns_in_frame_used_only_as_targets": leak_cols,
        "feature_count_baseline_cell_keys": len(cell_keys),
        "feature_count_pressure_signals": len(sc.SIGNAL_COLUMNS),
        "pressure_signal_columns": list(sc.SIGNAL_COLUMNS),
        "thresholds_fitted_on": "TRAIN rows only",
        "innings1_par": "strictly prior matches only (insufficient prior => not flagged)",
        "baseline_player_term": "none (leave-player-out expectation on TRAIN rows)",
        "rows_in_frame_after_prepare": int(len(d)),
    }


def _stream_metrics(t: pd.DataFrame) -> dict[str, Any]:
    e, y = t["e"].to_numpy(), t["y"].to_numpy()
    r = y - e
    slope = float(np.polyfit(e, y, 1)[0]) if len(t) > 2 and np.ptp(e) > 0 else float("nan")
    qs = np.quantile(r, [0.01, 0.25, 0.5, 0.75, 0.99])
    return {
        "rows": int(len(t)),
        "mean_observed": float(y.mean()),
        "mean_predicted": float(e.mean()),
        "bias": float(r.mean()),
        "mae": float(np.abs(r).mean()),
        "rmse": float(np.sqrt((r**2).mean())),
        "calibration_slope": slope,
        "residual_sd": float(r.std(ddof=1)),
        "residual_skew": float(pd.Series(r).skew()),
        "residual_quantiles_1_25_50_75_99": [float(x) for x in qs],
    }


def delivery_validation(bs: bl.BaselineSet, d: pd.DataFrame) -> dict[str, Any]:
    """Per-delivery baseline accuracy by stream and period, with a constant-mean benchmark."""
    out: dict[str, Any] = {}
    for role, stream, binary in STREAMS:
        fr = role_frame(role, d)
        ex = bs.expected(role, stream, fr)
        t = pd.DataFrame(
            {
                "y": fr[stream].to_numpy(dtype=float),
                "e": ex["expected"].to_numpy(),
                "period": fr["period"].to_numpy(),
                "fmt": fr["competition_type"].to_numpy(),
            }
        )
        train_mean = t[t["period"] == "TRAIN"].groupby("fmt")["y"].mean()
        t["c"] = t["fmt"].map(train_mean)
        blk: dict[str, Any] = {"binary_target": binary, "periods": {}}
        for p in ("TRAIN", "VALIDATION"):
            tp = t[t["period"] == p]
            m = _stream_metrics(tp)
            m["benchmark_constant_format_mean_mae"] = float(np.abs(tp["y"] - tp["c"]).mean())
            m["benchmark_constant_format_mean_rmse"] = float(
                np.sqrt(((tp["y"] - tp["c"]) ** 2).mean())
            )
            if binary:
                m["brier_score"] = float(((tp["y"] - tp["e"]) ** 2).mean())
            blk["periods"][p] = m
            blk["periods"][p]["basis"] = (
                "TRAIN leave-player-out expectation (in-sample)"
                if p == "TRAIN"
                else "frozen TRAIN tables (out-of-period)"
            )
        v = t[t["period"] == "VALIDATION"].copy()
        v["dec"] = pd.qcut(v["e"].rank(method="first"), 10, labels=False)
        g = v.groupby("dec").agg(
            rows=("y", "size"), predicted=("e", "mean"), observed=("y", "mean")
        )
        blk["validation_by_predicted_decile"] = [
            {"decile": int(i), **{k: float(x) for k, x in r.items()}} for i, r in g.iterrows()
        ]
        gf = v.groupby("fmt").agg(
            rows=("y", "size"), predicted=("e", "mean"), observed=("y", "mean")
        )
        blk["validation_by_format"] = [
            {"format": str(i), **{k: float(x) for k, x in r.items()}} for i, r in gf.iterrows()
        ]
        out[f"{role}:{stream}"] = blk
    return out


def _wspearman_like(a: pd.Series, b: pd.Series) -> float:
    return float(a.rank().corr(b.rank())) if len(a) > 2 else float("nan")


def player_validation(rows_by_role: dict[str, pd.DataFrame], cfg: str) -> dict[str, Any]:
    """TRAIN-based player estimates against VALIDATION pressure outcomes (primary streams)."""
    out: dict[str, Any] = {}
    for role in PRIMARY:
        rows = rows_by_role[role]
        for comp in SCOPE:
            r = rows[rows["comp"] == comp]
            tr = r[r["period"] == "TRAIN"]
            va = r[r["period"] == "VALIDATION"]
            tpt = sh.player_table(sh.match_stats(tr))
            if len(tpt) < 2 or va.empty:
                out[f"{role}:{comp}"] = {"status": "INSUFFICIENT_DATA"}
                continue
            fit = sh.fit_cell(tpt)
            est = sh.estimate(tpt, fit, cfg)
            vp = va.groupby("player_id").agg(n=("resid", "size"), vmean=("resid", "mean"))
            common = est.index.intersection(vp.index)
            vp = vp.loc[common]
            e = est.loc[common]
            qual = vp["n"] >= 6
            vp, e = vp[qual], e[qual]
            if len(vp) < 15:
                out[f"{role}:{comp}"] = {
                    "status": "INSUFFICIENT_DATA",
                    "qualifying_players": int(len(vp)),
                }
                continue
            w = vp["n"].to_numpy(float)
            loss = lambda p: float((w * (p - vp["vmean"].to_numpy()) ** 2).sum() / w.sum())  # noqa: E731
            pooled = float(tr["resid"].mean())
            tab = pd.DataFrame(
                {"pred": e["shrunk"].to_numpy(), "obs": vp["vmean"].to_numpy(), "w": w}
            )
            tab["bin"] = pd.qcut(tab["pred"].rank(method="first"), 5, labels=False)
            g = tab.groupby("bin").apply(
                lambda x: pd.Series(
                    {
                        "players": len(x),
                        "mean_predicted": float(np.average(x["pred"], weights=x["w"])),
                        "mean_observed": float(np.average(x["obs"], weights=x["w"])),
                    }
                ),
                include_groups=False,
            )
            slope = (
                float(np.polyfit(tab["pred"], tab["obs"], 1)[0]) if tab["pred"].std() > 0 else None
            )
            out[f"{role}:{comp}"] = {
                "status": "OK",
                "train_players": int(len(tpt)),
                "qualifying_players": int(len(vp)),
                "min_validation_balls": 6,
                "weighted_mse_shrunk": loss(e["shrunk"].to_numpy()),
                "weighted_mse_unshrunk_train_mean": loss(e["mean"].to_numpy()),
                "weighted_mse_zero": loss(np.zeros(len(vp))),
                "weighted_mse_train_pooled_mean": loss(np.full(len(vp), pooled)),
                "spearman_shrunk_vs_validation": _wspearman_like(tab["pred"], tab["obs"]),
                "calibration_slope_observed_on_predicted": slope,
                "by_predicted_quintile": [
                    {"quintile": int(i), **{k: float(v) for k, v in row.items()}}
                    for i, row in g.iterrows()
                ],
                "data_weight_median_train": float(e["B"].median()),
                "shrinkage_k": float(e["k"].iloc[0]),
                "shrinkage_floor_hit": bool(e["floor_hit"].iloc[0]),
            }
    return out


# ---------------------------------------------------------------- prediction
def eligibility_rules(reports: Path | str) -> dict[tuple[str, str], dict[str, Any]]:
    t = pd.read_csv(Path(reports) / ELIGIBILITY_CSV)
    rules = {}
    for _, r in t.iterrows():
        rules[(str(r["format"]), str(r["role"]))] = {
            "threshold_balls": float(r["analysis_threshold_balls"]),
            "wr": float(r["analysis_window_ratio_W"]),
            "label": str(r["analysis_label"]),
        }
    return rules


def predict_role(
    role: str,
    rows: pd.DataFrame,
    cfg: str,
    rules: dict[tuple[str, str], dict[str, Any]],
    names: pd.DataFrame,
    stats: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """IPL player estimates on the TRAIN+VALIDATION window; k and target from TRAIN only."""
    sign = PRIMARY[role][1]
    r = rows[rows["comp"] == FORMAT_SCOPE]
    fit = sh.fit_cell(sh.player_table(sh.match_stats(r[r["period"] == "TRAIN"])))
    pt = sh.player_table(sh.match_stats(r))
    est = sh.estimate(pt, fit, cfg)
    est["observed_pressure_mean"] = r.groupby("player_id")["actual"].mean()
    est["expected_pressure_mean"] = r.groupby("player_id")["expected"].mean()
    est["model_output"] = sign * est["shrunk"]
    rule = rules[(FORMAT_SCOPE, role)]
    est["eligible"] = est["n"] >= rule["threshold_balls"] * rule["wr"]
    est = est.join(names.set_index("player_id")["player_name"], how="left")
    st = stats[stats["format"] == FORMAT_SCOPE].set_index("player_id")
    est = est.join(st, how="left")
    info = {
        "players_with_pressure_rows": int(len(est)),
        "eligible_working_pool": int(est["eligible"].sum()),
        "eligible_without_name": int((est["eligible"] & est["player_name"].isna()).sum()),
        "eligibility_rule": rule,
        "shrinkage_k": float(est["k"].iloc[0]) if len(est) else None,
        "shrinkage_floor_hit": bool(est["floor_hit"].iloc[0]) if len(est) else None,
        "players_data_weight_at_least_0.5": int((est["B"] >= 0.5).sum()),
        "max_data_weight": float(est["B"].max()) if len(est) else None,
    }
    return est, info


def build_output_frame(
    est: pd.DataFrame, role: str, version: str, data_version: str, ts: str
) -> tuple[pd.DataFrame, str]:
    """Top-N eligible and named players by model output. Fewer rows when fewer qualify."""
    ok = est[est["eligible"] & est["player_name"].notna()].copy()
    ok = ok.reset_index().rename(columns={"index": "player_id"})
    if "player_id" not in ok.columns:
        ok = ok.rename(columns={ok.columns[0]: "player_id"})
    ok = ok.sort_values(["model_output", "player_id"], ascending=[False, True], kind="mergesort")
    top = ok.head(TOP_N).reset_index(drop=True)
    if role == "batter":
        runs, outs, balls, matches = "bat_runs", "bat_dismissals", "bat_balls", "bat_matches"
    else:
        runs, outs, balls, matches = "bowl_runs", "bowl_wickets", "bowl_balls", "bowl_matches"

    def _i(v: Any) -> Any:
        return None if pd.isna(v) else int(v)

    rows = []
    for i, r in top.iterrows():
        flags = [
            "pooled_reliability_0.37_player_order_unreliable",
            "eligibility_working_pool_not_validated",
            "pressure_definition_provisional",
        ]
        if r["B"] < 0.5:
            flags.append("data_weight_below_0.5")
        if r["B"] < 0.2:
            flags.append("data_weight_below_0.2")
        if r["floor_hit"]:
            flags.append("shrinkage_floor_hit")
        rows.append(
            {
                "model_output_order": i + 1,
                "player_id": int(r["player_id"]),
                "player_name": r["player_name"],
                "format_scope": FORMAT_SCOPE,
                "model_output_value": round(float(r["model_output"]), 6),
                "model_output_definition": MODEL_OUTPUT_DEFINITION[role],
                "uncertainty": NO_UNCERTAINTY,
                "historical_pressure_balls": int(r["n"]),
                "historical_pressure_matches": int(r["matches"]),
                "observed_pressure_mean": round(float(r["observed_pressure_mean"]), 6),
                "baseline_expected_pressure_mean": round(float(r["expected_pressure_mean"]), 6),
                "unshrunk_mean_residual": round(float(r["mean"]), 6),
                "data_weight": round(float(r["B"]), 6),
                "observed_total_balls": _i(r.get(balls)),
                "observed_total_runs": _i(r.get(runs)),
                "observed_dismissals_or_wickets": _i(r.get(outs)),
                "observed_total_matches": _i(r.get(matches)),
                "model_label": MODEL_LABEL,
                "model_version": version,
                "training_data_version": data_version,
                "prediction_timestamp_utc": ts,
                "eligibility_flag": "ELIGIBLE_WORKING_POOL_NOT_VALIDATED",
                "data_quality_flags": ";".join(flags),
                "methodology_gate_status": GATE_STATUS,
                "explanation": (
                    f"{MODEL_OUTPUT_DEFINITION[role]}. Based on {int(r['n'])} pressure balls in "
                    f"{int(r['matches'])} matches (TRAIN+VALIDATION, definition {DEFINITION}); "
                    f"data weight {r['B']:.3f}, so the value is mostly the pooled mean."
                ),
                "experimental_publication_status": PUBLICATION_STATUS,
                "banner": BANNER,
            }
        )
    note = (
        f"{len(rows)} of {TOP_N} rows written; "
        f"{int(est['eligible'].sum())} players meet the working-pool input rule"
        + ("" if len(rows) == TOP_N else "; fewer than ten qualify, so no padding was applied")
    )
    return pd.DataFrame(rows, columns=CSV_COLUMNS), note


# ---------------------------------------------------------------- stored TEST figures
def stored_test_summary(reports: Path | str) -> dict[str, Any]:
    """Already-reported Phase 4 TEST aggregates, copied from the stored file (TEST not opened)."""
    p = Path(reports) / "phase4_test_evaluation.json"
    j = json.loads(p.read_text(encoding="utf-8"))
    pl = [
        {
            "format": r["format"],
            "role": r["role"],
            "qualifying_players": r["qualifying_players"],
            "loss_weighted_mse": r["loss_weighted_mse"],
            "spearman_shrunk_vs_test": r["spearman_shrunk_vs_test"],
        }
        for r in j["player_level"]
        if r["test_scope"] == "TEST"
    ]
    return {
        "label": "previously accessed, non-pristine TEST (Phase 4, single opening); stored aggregates",
        "source_file": p.name,
        "source_sha256": _sha(p),
        "test_matches": j["test_matches"],
        "test_rows_total": j["test_rows_total"],
        "player_level_primary_streams": pl,
        "opened_in_this_run": False,
        "independent_out_of_sample_validation_claimed": False,
    }


# ---------------------------------------------------------------- run
def run_pipeline(
    store: Path | str = EXPLORATORY_DB,
    reports: Path | str = REPORTS_DIR,
    timestamp: str | None = None,
) -> dict[str, Any]:
    reports = Path(reports)
    lock_before = lock_snapshot(reports / "phase4_lock_log.json", reports / "phase5_lock_log.json")
    assert_phase5_lock_not_opened(reports / "phase5_lock_log.json")
    split = Split.from_config()
    frozen = json.loads(FROZEN_CHOICES.read_text(encoding="utf-8"))
    cfg = frozen["shrinkage"]["config"]
    ts = timestamp or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = load_pretest_state(store, split)
    tests = test_match_ids(store)
    loaded = {int(m) for m in raw["match_id"].unique()}
    leaked = sorted(tests & loaded)
    if leaked:
        raise PipelineError(f"TEST match ids present in the frame: {leaked[:5]}")
    names = read_table(store, "SELECT player_id, player_name FROM p4_player_classification")
    stats = read_table(store, "SELECT * FROM p4_player_stats")
    d, wb = bl.prepare_frame(raw, split)
    d = sc.add_signals(d)
    checks = data_checks(raw, d, names)
    checks["test_match_ids_in_frame"] = len(leaked)
    checks["test_matches_listed_in_p4_match_period"] = len(tests)
    checks["periods_in_frame"] = sorted(d["period"].unique().tolist())
    bs = bl.fit_baseline_set(d)
    train = d[d["period"] == "TRAIN"]
    q = sc.parse_definition(DEFINITION)[1]
    thr = sc.fit_thresholds(train, q)
    frozen_thr = frozen["definition"]["train_only_thresholds"]
    thr_diff = max(abs(thr[k] - float(v)) for k, v in frozen_thr.items())
    delivery = delivery_validation(bs, d)
    rows_by_role = {role: pressure_rows(d, bs, thr, role, PRIMARY[role][0]) for role in PRIMARY}
    player_val = player_validation(rows_by_role, cfg)
    rules = eligibility_rules(reports)
    prediction: dict[str, Any] = {}
    outputs: dict[str, pd.DataFrame] = {}
    data_version = _frame_digest(
        raw,
        ["match_id", "innings_number", "innings_ball_num", "striker_id", "bowler_id",
         "out_batter_runs", "out_is_wicket", "den_bowler_charged_runs"],
    )  # fmt: skip
    code_hashes = {f: _sha(Path(__file__).resolve().parents[2] / f) for f in CODE_FILES}
    version = (
        f"{MODEL_ID}|{bl.BASELINE_VERSION}|{DEFINITION}|{cfg}|"
        f"code:{hashlib.sha256(json.dumps(code_hashes, sort_keys=True).encode()).hexdigest()[:12]}"
    )
    for role in PRIMARY:
        est, info = predict_role(role, rows_by_role[role], cfg, rules, names, stats)
        out, note = build_output_frame(est, role, version, data_version, ts)
        outputs[role] = out
        info["rows_written"] = int(len(out))
        info["note"] = note
        prediction[role] = info
    lock_after = lock_snapshot(reports / "phase4_lock_log.json", reports / "phase5_lock_log.json")
    if lock_before != lock_after:
        raise PipelineError("TEST lock evidence changed during the run")
    metrics = {
        "model_label": MODEL_LABEL,
        "model_version": version,
        "definition": DEFINITION,
        "shrinkage_config": cfg,
        "seed": SEED,
        "randomness": "none: the fit and the predictions are deterministic (no bootstrap, no sampling)",
        "thresholds_train_only": thr,
        "thresholds_max_abs_diff_vs_phase4_frozen": thr_diff,
        "delivery_level_validation": delivery,
        "player_level_validation_train_to_validation": player_val,
        "prediction": prediction,
        "data_checks": checks,
        "restricted_test": stored_test_summary(reports),
        "pooled_reliability_phase6": POOLED_RELIABILITY,
    }
    registry = {
        "model_id": MODEL_ID,
        "model_label": MODEL_LABEL,
        "is_machine_learning": False,
        "is_deep_learning": False,
        "trained_artefact_exists": False,
        "algorithm": (
            "stratified empirical-Bayes baseline B0 (cells comp|role|phase|wickets-bin to comp, "
            "fitted on TRAIN) plus method-of-moments shrinkage of player pressure residuals"
        ),
        "entry_point": "scripts/phase7_ai_pipeline.py -> app.phase7.ai_pipeline.run_pipeline",
        "model_version": version,
        "baseline_version": bl.BASELINE_VERSION,
        "pressure_definition": DEFINITION,
        "pressure_definition_status": "PROVISIONAL (not validated)",
        "shrinkage_config": cfg,
        "seed": SEED,
        "split_config_sha256": _sha(SPLIT_CONFIG),
        "frozen_choices_sha256": _sha(FROZEN_CHOICES),
        "eligibility_sha256": _sha(reports / ELIGIBILITY_CSV),
        "state_store": Path(store).name,
        "state_store_sha256": _sha(store),
        "training_data_version": data_version,
        "training_period": "TRAIN (fit); VALIDATION (evaluation); TEST not loaded",
        "periods": checks["per_period"],
        "code_sha256": code_hashes,
        "target": "per-delivery runs (batter) / runs charged (bowler) residual under pressure",
        "player_id_mapping": "state striker_id/bowler_id -> p4_player_classification.player_name",
        "run_timestamp_utc": ts,
        "lock_before": lock_before,
        "lock_after": lock_after,
        "lock_unchanged": lock_before == lock_after,
        "test_opened": False,
        "methodology_gate_status": GATE_STATUS,
        "publication_status": PUBLICATION_STATUS,
        "outputs": {},
    }
    return {
        "registry": registry,
        "metrics": metrics,
        "outputs": outputs,
        "version": version,
        "timestamp": ts,
    }


def deterministic_digest(result: dict[str, Any]) -> str:
    """Hash of everything except timestamps: two seeded runs must agree."""
    parts = []
    for role in sorted(result["outputs"]):
        df = result["outputs"][role].drop(columns=["prediction_timestamp_utc"])
        parts.append(df.to_csv(index=False))
    m = json.dumps(result["metrics"], sort_keys=True, default=str)
    return hashlib.sha256(("|".join(parts) + m).encode("utf-8")).hexdigest()


def write_outputs(result: dict[str, Any], reports: Path | str = REPORTS_DIR) -> dict[str, str]:
    reports = Path(reports)
    reports.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for role, df in result["outputs"].items():
        p = reports / CSV_NAMES[role]
        df.to_csv(p, index=False, lineterminator="\n")
        hashes[p.name] = _sha(p)
    mp = reports / METRICS_NAME
    mp.write_text(
        json.dumps(result["metrics"], indent=1, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    hashes[mp.name] = _sha(mp)
    reg = dict(result["registry"])
    reg["outputs"] = hashes
    reg["deterministic_digest"] = deterministic_digest(result)
    rp = reports / REGISTRY_NAME
    rp.write_text(json.dumps(reg, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return hashes
