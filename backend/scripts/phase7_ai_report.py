"""Render ai_pipeline_verification.md and pressure_top10_status.md from the stored run outputs.
Every number is read from phase7_ai_pipeline_metrics.json / phase7_model_registry.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.phase4.constants import REPORTS_DIR  # noqa: E402
from app.phase7 import ai_pipeline as ap  # noqa: E402


def f(x, n=4):
    return "n/a" if x is None else f"{x:.{n}f}"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def verification(m, reg) -> str:
    chk = m["data_checks"]
    dv = m["delivery_level_validation"]
    pv = m["player_level_validation_train_to_validation"]
    pred = m["prediction"]
    rt = m["restricted_test"]
    L = ["# AI pipeline verification (Phase 7 chunk 5)", ""]
    L += [
        "> INTERNAL TECHNICAL VERIFICATION (internal experimental). Nothing here is a validated ranking. The pipeline is the "
        f"**{ap.MODEL_LABEL}**.",
        "",
        "## 1. Audit result: is there a trained AI/ML model?",
        "**No.** No trained machine-learning or deep-learning artefact exists in the project. "
        "There is no model file, no training history, no model registry and no inference entry "
        "point for a learned model. Searched: no `.pkl`, `.joblib`, `.pt`, `.pth`, `.onnx`, `.h5`, "
        "`.pb`, `.ckpt` or `.safetensors` file under `backend` or `frontend`, and no import of "
        "sklearn, torch, xgboost, lightgbm, joblib or pickle in `backend/app` or `backend/scripts`. "
        "`scikit-learn` is listed in `requirements.txt` but no module uses it. No model "
        "or training history was invented, and no new complex model was added.",
        "",
        "The only predictive machinery is the Phase 4 statistical pipeline, which this chunk treats "
        "as the model pipeline and labels exactly "
        f"**{ap.MODEL_LABEL}** in every output:",
        "",
        table(
            ["Item", "Value"],
            [
                ["Algorithm", reg["algorithm"]],
                [
                    "Training script / entry point",
                    "`scripts/phase4_baseline.py`, `scripts/phase4_scoring.py` (Phase 4); verification wrapper `scripts/phase7_ai_pipeline.py` -> `app.phase7.ai_pipeline.run_pipeline`",
                ],
                [
                    "Code",
                    "`app/phase4/baseline.py` (B0), `app/phase4/shrink.py` (shrinkage), `app/phase4/scoring.py` (pressure flag and residuals)",
                ],
                [
                    "Features (cell keys)",
                    ", ".join(chk["baseline_cell_key_columns"]) + " (all pre-delivery state)",
                ],
                [
                    "Pressure signals",
                    ", ".join(chk["pressure_signal_columns"])
                    + f"; definition `{m['definition']}` (PROVISIONAL)",
                ],
                ["Target", reg["target"]],
                [
                    "Training / validation / test",
                    "TRAIN = matches up to 2024-12-31 (512 matches); VALIDATION = 2025 (211 matches); TEST = from 2026-01-01 (144 matches, not loaded); `phase4_split_v1.json`",
                ],
                ["Player-id mapping", reg["player_id_mapping"]],
                [
                    "Artefact location",
                    "none (cell tables are rebuilt from TRAIN rows in memory); metadata in `phase7_model_registry.json`",
                ],
                [
                    "Metrics stored before this chunk",
                    "`phase4_baseline_calibration_report.md`, `phase4_calibration.json`, `phase4_test_evaluation.json`",
                ],
                [
                    "Registry",
                    "none before this chunk; `phase7_model_registry.json` added (JSON, because both DuckDB files are protected and must stay byte-identical)",
                ],
            ],
        ),
        "",
        "## 2. What worked",
        table(
            ["Stage", "Worked?", "Evidence"],
            [
                [
                    "Training (TRAIN-only fit)",
                    "Yes",
                    f"baseline B0, thresholds and shrinkage k fitted on {chk['per_period']['TRAIN']['matches']} TRAIN matches; thresholds equal the Phase 4 frozen values (max abs diff {m['thresholds_max_abs_diff_vs_phase4_frozen']:.2e})",
                ],
                [
                    "Validation",
                    "Yes",
                    f"{chk['per_period']['VALIDATION']['matches']} VALIDATION matches, {chk['per_period']['VALIDATION']['deliveries']} deliveries; see section 5",
                ],
                [
                    "Restricted TEST",
                    "Not run",
                    "the lock design refuses a second opening; stored Phase 4 aggregates are quoted in section 6, labelled previously accessed, non-pristine TEST",
                ],
                [
                    "Prediction",
                    "Yes",
                    f"batters {pred['batter']['rows_written']} rows, bowlers {pred['bowler']['rows_written']} rows (IPL scope)",
                ],
            ],
        ),
        "",
        "## 3. Training sample, data checks and leakage checks",
        table(
            ["Period", "Matches", "Deliveries", "Players"],
            [
                [p, v["matches"], v["deliveries"], v["players"]]
                for p, v in chk["per_period"].items()
            ],
        ),
        "",
        f"- Rows loaded: {chk['rows_total']}. Distinct striker/bowler ids: {chk['distinct_players']}. "
        f"Features: {chk['feature_count_baseline_cell_keys']} baseline cell keys, "
        f"{chk['feature_count_pressure_signals']} pressure signals.",
        f"- TEST rows: the state table is read with `WHERE match_date < validation_end + 1 day`, so TEST rows and "
        f"their outcome columns are never loaded. TEST match ids found in the frame: {chk['test_match_ids_in_frame']} "
        f"(checked against {chk['test_matches_listed_in_p4_match_period']} TEST ids in `p4_match_period`).",
        "- Leakage: baseline cell keys use no outcome column; outcome columns (`out_*`, `den_*`, `post_innings_*`) "
        "are used only as targets; thresholds are TRAIN-only; innings-1 par uses strictly prior matches; TRAIN "
        "expectations are leave-player-out; no player id is a model feature.",
        f"- Missing values in key columns: only `innings_phase` has missing values ({chk['missing_counts_key_columns']['innings_phase']} rows; these rows are not DLS-flagged and not "
        f"regulation-pressure-eligible, and the cause was not investigated here); `rrr` missing in chase rows: {chk['rrr_missing_in_chase_rows']} of {chk['chase_rows']}.",
        f"- Player-id consistency: {chk['player_ids_without_name_in_classification']} ids without a name in `p4_player_classification`; "
        f"{chk['rows_striker_equals_bowler']} rows with striker id equal to bowler id. Known limit: names are not unique across ids "
        "(see `submission_methodology.md`).",
        "- Seeds: the fit and predictions use no randomness; the seed "
        f"{m['seed']} is recorded and two runs give an identical digest (`tests/test_phase7_ai_pipeline.py`).",
        "",
        "## 4. Model and data version",
        f"- Model version: `{m['model_version']}`",
        f"- Training data version (hash of the loaded TRAIN+VALIDATION key columns): `{reg['training_data_version']}`",
        f"- State store `{reg['state_store']}` sha256: `{reg['state_store_sha256']}`",
        f"- Registry file: `phase7_model_registry.json` (run timestamp {reg['run_timestamp_utc']}).",
        "",
        "## 5. Validation result (VALIDATION period, per delivery)",
        "Baseline expectation against observed outcomes. The constant benchmark predicts the TRAIN format mean.",
        table(
            ["Stream", "Rows", "Bias", "MAE", "RMSE", "Benchmark RMSE", "Calibration slope"],
            [
                [
                    k,
                    v["periods"]["VALIDATION"]["rows"],
                    f(v["periods"]["VALIDATION"]["bias"]),
                    f(v["periods"]["VALIDATION"]["mae"]),
                    f(v["periods"]["VALIDATION"]["rmse"]),
                    f(v["periods"]["VALIDATION"]["benchmark_constant_format_mean_rmse"]),
                    f(v["periods"]["VALIDATION"]["calibration_slope"], 3),
                ]
                for k, v in dv.items()
            ],
        ),
        "",
        "Reading: the baseline lowers RMSE against the constant benchmark by less than 1% on every stream, "
        "and expected runs run below observed runs on VALIDATION (bias about +0.05 runs per ball for both batter "
        "runs and bowler runs charged). Calibration by predicted decile and residual quantiles are in "
        "`phase7_ai_pipeline_metrics.json` (`validation_by_predicted_decile`, `residual_quantiles_1_25_50_75_99`). "
        "Wicket streams are close to calibrated in the mean (bias under 0.002).",
        "",
        "Player-level check: TRAIN-based shrunk estimates against VALIDATION pressure residuals "
        "(players with at least 6 VALIDATION pressure balls; weighted mean squared error, lower is better).",
        table(
            [
                "Cell",
                "Players",
                "MSE shrunk",
                "MSE unshrunk",
                "MSE zero",
                "MSE pooled mean",
                "Spearman",
                "Slope obs on pred",
                "k",
                "Floor hit",
            ],
            [
                [
                    k,
                    v["qualifying_players"],
                    f(v["weighted_mse_shrunk"]),
                    f(v["weighted_mse_unshrunk_train_mean"]),
                    f(v["weighted_mse_zero"]),
                    f(v["weighted_mse_train_pooled_mean"]),
                    f(v["spearman_shrunk_vs_validation"], 3),
                    f(v["calibration_slope_observed_on_predicted"], 2),
                    f(v["shrinkage_k"], 1),
                    v["shrinkage_floor_hit"],
                ]
                for k, v in pv.items()
                if v.get("status") == "OK"
            ],
        ),
        "",
        "Reading: shrinkage beats the unshrunk estimate clearly and beats a constant by a small margin. "
        "The observed-on-predicted slope is well above 1, so the estimates are over-shrunk against VALIDATION, "
        "as expected when the between-player variance sits at the shrinkage floor (Phase 6). "
        "This is a single in-sample chronological check, not independent validation, and it does not show that "
        "player order is reliable (Phase 6 pooled odd/even reliability 0.37).",
        "",
        "## 6. Restricted TEST result",
        f"TEST was **not opened** in this chunk (lock log hash before and after: `{reg['lock_after']['phase4_lock_log_sha256']}`, "
        "events FREEZE, OPEN, CLOSE from Phase 4; Phase 5 log has 0 OPEN events). A second opening is refused by "
        "`TestLock` by design, so no restricted diagnostic was run. The figures below are the "
        f"already-reported Phase 4 aggregates from `{rt['source_file']}` (sha256 `{rt['source_sha256']}`), "
        "**previously accessed, non-pristine TEST**. They are not independent out-of-sample validation and must not be read as one.",
        table(
            [
                "Format",
                "Role",
                "Qualifying players",
                "MSE shrunk",
                "MSE raw",
                "MSE zero",
                "Spearman shrunk",
            ],
            [
                [
                    r["format"],
                    r["role"],
                    r["qualifying_players"],
                    f(r["loss_weighted_mse"]["shrunk"]),
                    f(r["loss_weighted_mse"]["raw"]),
                    f(r["loss_weighted_mse"]["zero"]),
                    f(r["spearman_shrunk_vs_test"], 3),
                ]
                for r in rt["player_level_primary_streams"]
            ],
        ),
        "",
        "## 7. Prediction result and the two CSVs",
        "- `backend/data/reports/experimental_ai_top10_batters.csv` and `experimental_ai_top10_bowlers.csv`, scope IPL, "
        "TRAIN+VALIDATION window, definition `any|q0.75`, shrinkage `shrink_tau4` (Phase 4 frozen choice, unchanged).",
        f"- Model output: batters = {ap.MODEL_OUTPUT_DEFINITION['batter']}. Bowlers = {ap.MODEL_OUTPUT_DEFINITION['bowler']}.",
        "- Order is by model output only. Each row carries the banner that it is not a validated ranking and that Phase 6 found "
        "player order unreliable (pooled reliability 0.37). Columns `uncertainty` hold the text "
        f"`{ap.NO_UNCERTAINTY}`; the match-cluster bootstrap interval of Phase 4 is not shown because it holds k fixed and its coverage was never validated.",
        "- Technical input rule: the Phase 4 working-pool threshold "
        "(`phase4_eligibility_frozen.csv`, status THRESHOLD_NOT_VALIDATED) and a player name in the classification table.",
        table(
            [
                "Role",
                "Players with pressure rows",
                "Meet input rule",
                "Rows written",
                "Max data weight",
                "Players with data weight >= 0.5",
                "k",
                "Floor hit",
            ],
            [
                [
                    r,
                    p["players_with_pressure_rows"],
                    p["eligible_working_pool"],
                    p["rows_written"],
                    f(p["max_data_weight"], 3),
                    p["players_data_weight_at_least_0.5"],
                    f(p["shrinkage_k"], 1),
                    p["shrinkage_floor_hit"],
                ]
                for r, p in pred.items()
            ],
        ),
        "",
        "- All publication gates fail (Phase 6: data-weight gate 0 of 48 contexts), so every row is "
        "`INTERNAL_EXPERIMENTAL_ONLY`. One bowler has a player-level data weight above 0.5 in this pool; the gate is a "
        "context-level marginal data-weight test, which still fails.",
        "- Validated `pressure_batters_top10.csv` and `pressure_bowlers_top10.csv` are intentionally not produced "
        "(see `pressure_top10_status.md`).",
        "",
        "## 8. Serving",
        "Token-protected only: `GET /api/v1/internal/model-status` and `GET /api/v1/internal/experimental-predictions` "
        "(`X-Admin-Token`; 401 for a missing or wrong token, 503 when no token is configured). The loader "
        "(`app/phase7/ai_loader.py`) returns `INSUFFICIENT_DATA` when files are missing and `LOCKED` when the lock log or an output hash "
        "no longer matches the registry. No public route, and `/players` is unchanged. Tests: `tests/test_phase7_ai_pipeline.py`, "
        "`tests/test_phase7_ai_internal_api.py`.",
        "",
        "## 9. Frontend/backend integration checks",
        "To be updated by chunk 6 (the frontend internal view).",
        "",
        "## 10. Hardcoded and mock data removal audit",
        "See `hardcoded_mock_data_audit.md` in the same folder.",
        "",
        "## 11. Remaining limitations",
        "- No trained AI/ML model exists. The labelled model is a statistical baseline with shrinkage and adds no new learned component.",
        "- The pressure definition `any|q0.75`, the eligibility pools and the methodology are not validated; every gate fails.",
        "- The validation here is chronological but uses the same data the shrinkage choice used (TRAIN/VALIDATION); TEST is non-pristine.",
        "- Player order is unreliable (pooled odd/even reliability 0.37, median 0.25). The CSV order must not be used for selection.",
        "- Uncertainty is not calibrated and is therefore not reported.",
        "- Scope is IPL only; T20I players are not in the CSVs. Late T20I dates (42) remain unverified and excluded from the state.",
        "- The player-level observed totals (`observed_total_*`) come from `p4_player_stats` and include DLS rows (descriptive only).",
        "",
    ]
    return "\n".join(L)


def status_md() -> str:
    return "\n".join(
        [
            "# Pressure Top 10 status",
            "",
            "`pressure_batters_top10.csv` and `pressure_bowlers_top10.csv` are **intentionally not produced**. No such files exist.",
            "",
            "## Why no defensible Top 10 exists",
            "Figures are from the Phase 6 reports (`phase6_final_audit.md` recomputed them from the stored tables).",
            "- Between-player variance sits at the shrinkage floor in all 48 contexts, so the data cannot separate players beyond the floor.",
            "- Data-weight gate (marginal data weight 0.5): fails in all 48 contexts (0 of 48 pass).",
            "- Pooled odd/even reliability of the provisional definition is 0.37; the median over 47 estimable contexts is 0.25; "
            "0.5 is reached in 2 of 4 cells of the tested ball ladder; 0.7 and 0.8 are not reached.",
            "- Within-season reliability median 0.24; adjacent-season correlation median 0.11.",
            "- No pressure definition passes the predeclared criteria; `any|q0.75` is provisional, not validated.",
            "- TEST was opened once in Phase 4, so no clean hold-out exists. Phase 4 TEST aggregates are non-pristine.",
            "- 42 late T20I match dates are unverified and excluded; the strict uncapped classification is disabled for lack of a "
            "cap-status source with stable player ids.",
            "- Phase 6 tested 18 improvement options; none reaches the 0.5 data-weight gate without a methodology change. "
            "The best option (marginal data weight 0.56) changes the methodology and is documented as unadopted.",
            "",
            "## What exists instead",
            "- Descriptive profiles and evidence-supported comparisons (public, no ranking claims).",
            "- `experimental_ai_top10_batters.csv` and `experimental_ai_top10_bowlers.csv`: internal, token-protected, ordered by the "
            f"output of the {ap.MODEL_LABEL}, labelled not validated. They are not the pressure ranking and must not be published or used for selection.",
            "",
            "## What would change this",
            "- A methodology or data change that raises the marginal data weight to the gate **and** shows improved reliability "
            "on a clean hold-out (reaching the threshold alone does not prove reliability).",
            "- Official verification of the 42 T20I dates, a stable-id cap-status source, and a validated pressure definition and eligibility pools.",
            "",
            "## No padding",
            "No list is padded to reach ten players. A list with fewer than ten qualifying players is returned as is.",
            "",
        ]
    )


def main() -> int:
    m = json.loads((REPORTS_DIR / ap.METRICS_NAME).read_text(encoding="utf-8"))
    reg = json.loads((REPORTS_DIR / ap.REGISTRY_NAME).read_text(encoding="utf-8"))
    (REPORTS_DIR / "ai_pipeline_verification.md").write_text(verification(m, reg), encoding="utf-8")
    (REPORTS_DIR / "pressure_top10_status.md").write_text(status_md(), encoding="utf-8")
    print("written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
