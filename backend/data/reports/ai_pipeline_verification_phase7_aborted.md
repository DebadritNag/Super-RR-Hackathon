# AI pipeline verification (Phase 7 chunk 5)

> INTERNAL TECHNICAL VERIFICATION (internal experimental). Nothing here is a validated ranking. The pipeline is the **statistical baseline/shrinkage model (not machine learning or deep learning)**.

## 1. Audit result: is there a trained AI/ML model?
**No.** No trained machine-learning or deep-learning artefact exists in the project. There is no model file, no training history, no model registry and no inference entry point for a learned model. Searched: no `.pkl`, `.joblib`, `.pt`, `.pth`, `.onnx`, `.h5`, `.pb`, `.ckpt` or `.safetensors` file under `backend` or `frontend`, and no import of sklearn, torch, xgboost, lightgbm, joblib or pickle in `backend/app` or `backend/scripts`. `scikit-learn` is listed in `requirements.txt` but no module uses it. No model or training history was invented, and no new complex model was added.

The only predictive machinery is the Phase 4 statistical pipeline, which this chunk treats as the model pipeline and labels exactly **statistical baseline/shrinkage model (not machine learning or deep learning)** in every output:

| Item | Value |
|---|---|
| Algorithm | stratified empirical-Bayes baseline B0 (cells comp|role|phase|wickets-bin to comp, fitted on TRAIN) plus method-of-moments shrinkage of player pressure residuals |
| Training script / entry point | `scripts/phase4_baseline.py`, `scripts/phase4_scoring.py` (Phase 4); verification wrapper `scripts/phase7_ai_pipeline.py` -> `app.phase7.ai_pipeline.run_pipeline` |
| Code | `app/phase4/baseline.py` (B0), `app/phase4/shrink.py` (shrinkage), `app/phase4/scoring.py` (pressure flag and residuals) |
| Features (cell keys) | competition_type, role_ctx, innings_phase, wbin (all pre-delivery state) |
| Pressure signals | rrr, neg_par_dev_prior; definition `any|q0.75` (PROVISIONAL) |
| Target | per-delivery runs (batter) / runs charged (bowler) residual under pressure |
| Training / validation / test | TRAIN = matches up to 2024-12-31 (512 matches); VALIDATION = 2025 (211 matches); TEST = from 2026-01-01 (144 matches, not loaded); `phase4_split_v1.json` |
| Player-id mapping | state striker_id/bowler_id -> p4_player_classification.player_name |
| Artefact location | none (cell tables are rebuilt from TRAIN rows in memory); metadata in `phase7_model_registry.json` |
| Metrics stored before this chunk | `phase4_baseline_calibration_report.md`, `phase4_calibration.json`, `phase4_test_evaluation.json` |
| Registry | none before this chunk; `phase7_model_registry.json` added (JSON, because both DuckDB files are protected and must stay byte-identical) |

## 2. What worked
| Stage | Worked? | Evidence |
|---|---|---|
| Training (TRAIN-only fit) | Yes | baseline B0, thresholds and shrinkage k fitted on 512 TRAIN matches; thresholds equal the Phase 4 frozen values (max abs diff 1.36e-11) |
| Validation | Yes | 211 VALIDATION matches, 47665 deliveries; see section 5 |
| Restricted TEST | Not run | the lock design refuses a second opening; stored Phase 4 aggregates are quoted in section 6, labelled previously accessed, non-pristine TEST |
| Prediction | Yes | batters 10 rows, bowlers 10 rows (IPL scope) |

## 3. Training sample, data checks and leakage checks
| Period | Matches | Deliveries | Players |
|---|---|---|---|
| TRAIN | 512 | 120248 | 763 |
| VALIDATION | 211 | 47665 | 535 |

- Rows loaded: 167913. Distinct striker/bowler ids: 890. Features: 4 baseline cell keys, 2 pressure signals.
- TEST rows: the state table is read with `WHERE match_date < validation_end + 1 day`, so TEST rows and their outcome columns are never loaded. TEST match ids found in the frame: 0 (checked against 144 TEST ids in `p4_match_period`).
- Leakage: baseline cell keys use no outcome column; outcome columns (`out_*`, `den_*`, `post_innings_*`) are used only as targets; thresholds are TRAIN-only; innings-1 par uses strictly prior matches; TRAIN expectations are leave-player-out; no player id is a model feature.
- Missing values in key columns: only `innings_phase` has missing values (34 rows; these rows are not DLS-flagged and not regulation-pressure-eligible, and the cause was not investigated here); `rrr` missing in chase rows: 0 of 79620.
- Player-id consistency: 0 ids without a name in `p4_player_classification`; 0 rows with striker id equal to bowler id. Known limit: names are not unique across ids (see `submission_methodology.md`).
- Seeds: the fit and predictions use no randomness; the seed 20260512 is recorded and two runs give an identical digest (`tests/test_phase7_ai_pipeline.py`).

## 4. Model and data version
- Model version: `p7_stat_baseline_shrinkage_v1|p4_baseline_b0_train_frozen_v1|any|q0.75|shrink_tau4|code:96594020e2df`
- Training data version (hash of the loaded TRAIN+VALIDATION key columns): `457ea51f939f6928cdba617aa638df71e64a8a301ed0e5372c7de2e073919f0c`
- State store `exploratory.duckdb` sha256: `7b396e42a2acb281fd5ffd64051064d7ac48e82bdfad23dd229bd20b9ca6277d`
- Registry file: `phase7_model_registry.json` (run timestamp 2026-11-17T10:29:56Z).

## 5. Validation result (VALIDATION period, per delivery)
Baseline expectation against observed outcomes. The constant benchmark predicts the TRAIN format mean.
| Stream | Rows | Bias | MAE | RMSE | Benchmark RMSE | Calibration slope |
|---|---|---|---|---|---|---|
| batter:dismissal | 41740 | 0.0015 | 0.1027 | 0.2279 | 0.2285 | 1.311 |
| batter:runs | 41740 | 0.0470 | 1.3143 | 1.7527 | 1.7563 | 1.152 |
| bowler:charged | 43376 | 0.0454 | 1.2825 | 1.7278 | 1.7311 | 1.149 |
| bowler:wkt | 43376 | 0.0016 | 0.0966 | 0.2213 | 0.2217 | 1.305 |

Reading: the baseline lowers RMSE against the constant benchmark by less than 1% on every stream, and expected runs run below observed runs on VALIDATION (bias about +0.05 runs per ball for both batter runs and bowler runs charged). Calibration by predicted decile and residual quantiles are in `phase7_ai_pipeline_metrics.json` (`validation_by_predicted_decile`, `residual_quantiles_1_25_50_75_99`). Wicket streams are close to calibrated in the mean (bias under 0.002).

Player-level check: TRAIN-based shrunk estimates against VALIDATION pressure residuals (players with at least 6 VALIDATION pressure balls; weighted mean squared error, lower is better).
| Cell | Players | MSE shrunk | MSE unshrunk | MSE zero | MSE pooled mean | Spearman | Slope obs on pred | k | Floor hit |
|---|---|---|---|---|---|---|---|---|---|
| batter:IPL | 92 | 0.1286 | 0.2022 | 0.1384 | 0.1375 | 0.346 | 3.42 | 25.0 | True |
| batter:T20I | 153 | 0.1340 | 0.5557 | 0.1445 | 0.1435 | 0.404 | 2.93 | 25.0 | True |
| bowler:IPL | 78 | 0.1419 | 0.1850 | 0.1466 | 0.1465 | 0.222 | 1.86 | 25.0 | True |
| bowler:T20I | 113 | 0.0992 | 0.1703 | 0.1064 | 0.1038 | 0.183 | 1.97 | 25.0 | True |

Reading: shrinkage beats the unshrunk estimate clearly and beats a constant by a small margin. The observed-on-predicted slope is well above 1, so the estimates are over-shrunk against VALIDATION, as expected when the between-player variance sits at the shrinkage floor (Phase 6). This is a single in-sample chronological check, not independent validation, and it does not show that player order is reliable (Phase 6 pooled odd/even reliability 0.37).

## 6. Restricted TEST result
TEST was **not opened** in this chunk (lock log hash before and after: `cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c`, events FREEZE, OPEN, CLOSE from Phase 4; Phase 5 log has 0 OPEN events). A second opening is refused by `TestLock` by design, so no restricted diagnostic was run. The figures below are the already-reported Phase 4 aggregates from `phase4_test_evaluation.json` (sha256 `27b3c0846a8b3c50617f16ca429ea5af6f8ed84976bca8860aa345cb7d1b90c5`), **previously accessed, non-pristine TEST**. They are not independent out-of-sample validation and must not be read as one.
| Format | Role | Qualifying players | MSE shrunk | MSE raw | MSE zero | Spearman shrunk |
|---|---|---|---|---|---|---|
| IPL | batter | 69 | 0.1070 | 0.1129 | 0.1217 | 0.373 |
| T20I | batter | 79 | 0.1689 | 0.1574 | 0.1775 | 0.392 |
| IPL | bowler | 39 | 0.0745 | 0.0934 | 0.0800 | 0.246 |
| T20I | bowler | 75 | 0.1315 | 0.1676 | 0.1307 | 0.225 |

## 7. Prediction result and the two CSVs
- `backend/data/reports/experimental_ai_top10_batters.csv` and `experimental_ai_top10_bowlers.csv`, scope IPL, TRAIN+VALIDATION window, definition `any|q0.75`, shrinkage `shrink_tau4` (Phase 4 frozen choice, unchanged).
- Model output: batters = shrunk mean residual of runs per ball faced under pressure (actual minus calibrated baseline expectation); positive = more runs per ball than the baseline expects. Bowlers = shrunk mean residual of runs conceded per ball under pressure with the sign flipped (baseline expectation minus actual); positive = fewer runs conceded per ball than the baseline expects.
- Order is by model output only. Each row carries the banner that it is not a validated ranking and that Phase 6 found player order unreliable (pooled reliability 0.37). Columns `uncertainty` hold the text `not available: model does not produce calibrated uncertainty`; the match-cluster bootstrap interval of Phase 4 is not shown because it holds k fixed and its coverage was never validated.
- Technical input rule: the Phase 4 working-pool threshold (`phase4_eligibility_frozen.csv`, status THRESHOLD_NOT_VALIDATED) and a player name in the classification table.
| Role | Players with pressure rows | Meet input rule | Rows written | Max data weight | Players with data weight >= 0.5 | k | Floor hit |
|---|---|---|---|---|---|---|---|
| batter | 267 | 132 | 10 | 0.400 | 0 | 25.0 | True |
| bowler | 182 | 80 | 10 | 0.504 | 1 | 25.0 | True |

- All publication gates fail (Phase 6: data-weight gate 0 of 48 contexts), so every row is `INTERNAL_EXPERIMENTAL_ONLY`. One bowler has a player-level data weight above 0.5 in this pool; the gate is a context-level marginal data-weight test, which still fails.
- Validated `pressure_batters_top10.csv` and `pressure_bowlers_top10.csv` are intentionally not produced (see `pressure_top10_status.md`).

## 8. Serving
Token-protected only: `GET /api/v1/internal/model-status` and `GET /api/v1/internal/experimental-predictions` (`X-Admin-Token`; 401 for a missing or wrong token, 503 when no token is configured). The loader (`app/phase7/ai_loader.py`) returns `INSUFFICIENT_DATA` when files are missing and `LOCKED` when the lock log or an output hash no longer matches the registry. No public route, and `/players` is unchanged. Tests: `tests/test_phase7_ai_pipeline.py`, `tests/test_phase7_ai_internal_api.py`.

## 9. Frontend/backend integration checks
To be updated by chunk 6 (the frontend internal view).

## 10. Hardcoded and mock data removal audit
See `hardcoded_mock_data_audit.md` in the same folder.

## 11. Remaining limitations
- No trained AI/ML model exists. The labelled model is a statistical baseline with shrinkage and adds no new learned component.
- The pressure definition `any|q0.75`, the eligibility pools and the methodology are not validated; every gate fails.
- The validation here is chronological but uses the same data the shrinkage choice used (TRAIN/VALIDATION); TEST is non-pristine.
- Player order is unreliable (pooled odd/even reliability 0.37, median 0.25). The CSV order must not be used for selection.
- Uncertainty is not calibrated and is therefore not reported.
- Scope is IPL only; T20I players are not in the CSVs. Late T20I dates (42) remain unverified and excluded from the state.
- The player-level observed totals (`observed_total_*`) come from `p4_player_stats` and include DLS rows (descriptive only).
