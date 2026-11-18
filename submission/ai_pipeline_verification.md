# AI pipeline verification (Phase 9)

Generated 2026-11-18T07:27:50+00:00. The p9 models are fitted on matches to 2025-12-31 with the Phase 8 hyperparameters and score the calendar-2026 deliveries out of sample (2026 released by owner decision D1). They are internal diagnostics; the experimental Top 10 files are not the submitted ranking and are not validated.

## 1. Artefacts

| artefact | exists | algorithm | trained_on | seed | version | sha256 |
|---|---|---|---|---|---|---|
| p9_expected_batter_runs_v1 | yes | gbm | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_expected_v1 | e9f1495d6a65148b4354262afe498fc70ace90eba66dad34ac546a69486d76c6 |
| p9_expected_batter_wicket_v1 | yes | gbm | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_expected_v1 | 975e55c9ade26ca3b822073d803fc4dcbcbc1d7f2347c8e2a4c914b87a83801f |
| p9_expected_batter_dot_v1 | yes | gbm | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_expected_v1 | 361c39d0756bd80c34fa7aa78822fbba753f7b9ea2e0df4f06c4f78d205a7bfe |
| p9_expected_batter_boundary_v1 | yes | gbm | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_expected_v1 | 5d90844355d7097b417f910304c0d096ea9e9a1dba083c99997289bef736c9f5 |
| p9_expected_bowler_runs_v1 | yes | gbm | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_expected_v1 | bdb59bf2ef71ae0c5445b7490c60e13555919bdd836d1d5168262c07a1eb2a77 |
| p9_expected_bowler_wicket_v1 | yes | gbm | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_expected_v1 | e2a855cec49801c1e69ff27c4434349de50ba08b1221d5271151dd726352b607 |
| p9_expected_bowler_dot_v1 | yes | gbm | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_expected_v1 | 7fbbd00d5bce887ea22cef4aee06813bb4a705b2f94fc7067eaa646a05879f27 |
| p9_expected_bowler_boundary_v1 | yes | gbm | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_expected_v1 | 90a13fc9cd712190e89d3856d7f1f750a3a96fa05f791cee8d69b3b542b356be |
| p9_wp_v1 | yes | HistGradientBoostingClassifier | TRAIN+VALIDATION (matches to 2025-12-31) | 20260512 | p9_wp_v1 | 653070883f5379b33d36c31f5f4586294e71f9d3bad08dbd7a9c303f99ed0c0b |

## 2. Reproducibility (retrain from scratch, same seed and parameters)

| model | learner | rows_compared | max_abs_diff | identical |
|---|---|---|---|---|
| p9_expected_batter_runs_v1 | gbm | 30610 | 0.000 | yes |
| p9_expected_batter_wicket_v1 | gbm | 30660 | 0.000 | yes |
| p9_expected_batter_dot_v1 | gbm | 30610 | 0.000 | yes |
| p9_expected_batter_boundary_v1 | gbm | 30610 | 0.000 | yes |
| p9_expected_bowler_runs_v1 | gbm | 31946 | 0.000 | yes |
| p9_expected_bowler_wicket_v1 | gbm | 30527 | 0.000 | yes |
| p9_expected_bowler_dot_v1 | gbm | 30527 | 0.000 | yes |
| p9_expected_bowler_boundary_v1 | gbm | 30527 | 0.000 | yes |
| p9_wp_v1:W1 | gbm | 16541 | 0.000 | yes |
| p9_wp_v1:W2 | gbm | 14853 | 0.000 | yes |

All 10 models reproduce their stored predictions exactly: True. The AI-verify script additionally retrained the batter-runs and bowler-wicket models and compared them with the stored artefacts.

## 3. Out-of-time check on 2026 (2026 out-of-time check; data previously held out, released by owner decision)

| model | metric | model_value_2026 | constant_value_2026 | gain_vs_constant_pct | n_2026 | slope | label |
|---|---|---|---|---|---|---|---|
| batter_runs | rmse | 1.794 | 1.825 | 1.706 | 30610 | n/a | 2026 out-of-time check; data previously held out, released by owner decision |
| batter_wicket | log_loss | 0.207 | 0.210 | 1.677 | 30660 | 0.940 | 2026 out-of-time check; data previously held out, released by owner decision |
| batter_dot | log_loss | 0.629 | 0.650 | 3.220 | 30610 | 0.984 | 2026 out-of-time check; data previously held out, released by owner decision |
| batter_boundary | log_loss | 0.500 | 0.516 | 3.118 | 30610 | 0.907 | 2026 out-of-time check; data previously held out, released by owner decision |
| bowler_runs | rmse | 1.767 | 1.794 | 1.552 | 31946 | n/a | 2026 out-of-time check; data previously held out, released by owner decision |
| bowler_wicket | log_loss | 0.204 | 0.207 | 1.477 | 30527 | 0.938 | 2026 out-of-time check; data previously held out, released by owner decision |
| bowler_dot | log_loss | 0.629 | 0.650 | 3.219 | 30527 | 0.985 | 2026 out-of-time check; data previously held out, released by owner decision |
| bowler_boundary | log_loss | 0.499 | 0.516 | 3.143 | 30527 | 0.906 | 2026 out-of-time check; data previously held out, released by owner decision |
| W1 | brier | 0.239 | 0.252 | 5.130 | 16541 | 0.621 | 2026 out-of-time check; data previously held out, released by owner decision |
| W2 | brier | 0.123 | 0.254 | 51.533 | 14853 | 1.076 | 2026 out-of-time check; data previously held out, released by owner decision |

Nothing was tuned on 2026. There is no pristine hold-out left after the release.

## 4. Leakage controls

Features are pre-delivery columns only (checked by `assert_feature_list_clean`); no player identifier or outcome column. Scoring is out of fold: no delivery is scored by a model fitted with its match (checked in code and by tests). Team priors use strictly earlier matches.

## 4b. Hardcoded values and retained files

No player names, scores or random numbers are hardcoded in the AI modules (checked by tests). The earlier outputs are retained: the Phase 7 aborted files as `*_phase7_aborted.*` and the Phase 8 files as `*_phase8.*`.

## 5. Experimental AI lists (internal)

- batter: 334 players with 2026 pressure balls, 51 eligible, 10 listed; split-half Spearman-Brown 0.001 over 51 players; 3 of the listed intervals exclude zero.
- bowler: 254 players with 2026 pressure balls, 61 eligible, 10 listed; split-half Spearman-Brown 0.272 over 61 players; 2 of the listed intervals exclude zero.

Win-probability check: W2 (chasing side wins), stored p9 artefact applied to calendar-2026 deliveries; Brier 0.1229 against 0.2535 for a constant (gain 51.5%), n = 14853.

Technical success is not reliability: the experimental lists are labelled EXPERIMENTAL_NOT_VALIDATED and are served only by the token-protected route.
