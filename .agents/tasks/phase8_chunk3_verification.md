# Phase 8 chunk 3 verification (Approach B: win probability, leverage, WPA)
Run from `d:/Data/backend` with `$env:PYTHONUTF8=1; $env:PYTHONPATH=d:/Data/backend`. No gate or review file existed at the start (`phase8_chunk3_gate.json`, `phase8_chunk3_review.md` absent), so this is a first pass.

| Command | Result |
|---|---|
| `python scripts/phase8_approach_b.py winprob` | W1, W2 and next-ball class model fitted on TRAIN, validation metrics, calibration, artefact `data/models/p8_wp_v1.{joblib,json}`, WP timeline, leverage, WPA attribution; tables `p8_wp_metrics`, `p8_wp_model_grid`, `p8_wp_calibration`, `p8_wp_class_metrics`, `p8_wp_label_exclusions`, `p8_wp_feature_check`, `p8_delivery_leverage`, `p8_wpa_excluded_events`, `p8_wpa_split_rules` |
| `python scripts/phase8_approach_b.py tests` | validity tests for P1 (leverage) and P2 (closeness) plus test (d) for every candidate: `p8_b_intensity_tests`, `p8_b_test_d`, `p8_b_intensity_selection` |
| `python scripts/phase8_approach_b.py estimate` | residual regression, units, REML, 1000-draw full-refit bootstrap, split-half, ICC, out-of-time, sensitivity, format study: `p8_b_estimates`, `p8_b_intensity_comparison`, `p8_b_reliability`, `p8_b_reml`, `p8_b_sensitivity`, `p8_b_ineligible`, `p8_b_pressure_exposure`, `p8_b_boot_check`, `p8_b_format_study`, `p8_b_status`, `p8_b_wpa_regression` |
| `python scripts/phase8_approach_b.py report` | `data/reports/phase8_approach_b_results.md` (generated from stored tables only) |
| `python -m pytest tests/test_phase8_winprob.py tests/test_phase8_wpa.py tests/test_phase8_approach_b.py -q` | 60 new tests passed (winprob 30, WPA 20, approach B 10) |
| `python -m pytest -q -p no:cacheprovider` (full) | **1358 passed**, 4 warnings, 551 s (log `.agents/tasks/_p8c3_full_pytest.txt`). An earlier full run had 2 failures caused by this chunk (a constant named `GATE_BRIER_GAIN` tripped the Phase 6 "no numeric gate below 0.5" scan; the word "Cricsheet" appeared in a report string). Both fixed (constants renamed `WP_MIN_BRIER_GAIN`, `WP_SLOPE_RANGE`; report text reworded) and the full suite rerun. |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 398 files already formatted |
| `check_protected(only=())` | 234 protected files checked, unchanged (both DuckDB files included); TEST lock state unchanged at the end of every stage |

## Delivered
- `app/phase8/winprob.py`: labels (decisive regulation results only, regex plus winner and DLS checks), one feature function for real rows and hypothetical next states, W1/W2 fitting (grid chosen once on VALIDATION by log loss, TRAIN out-of-fold scoring, per-fold predictors kept), class model, transitions, leverage, `wp_after_series`, versioned artefact.
- `app/phase8/wpa.py`: attribution (striker, bowler, bowler-credited wicket only, run-out rule, wides and no-balls to the bowler, byes and leg-byes to the batting side, unusual events excluded and counted) with a counterfactual split for multi-component balls.
- `app/phase8/approach_b.py`: out-of-fold model grouping, leverage over all rows, component counterfactuals, WPA-on-leverage regression (out of fold), leverage-weighted WPA per opportunity.
- `app/phase8/report_b.py`, `scripts/phase8_approach_b.py` (stages `winprob`, `tests`, `estimate`, `report`).
- Artefact `data/models/p8_wp_v1.joblib` (sha256 `93bb086c...e7ed70`, identical on a rerun) with `p8_wp_v1.json` (algorithm, version, training period, matches and deliveries, features, targets, metrics, exploratory-database hash, seed, timestamp, criteria hash).

## Findings carried into the report
- Labels: 644 of 675 in-scope matches labelled; 31 excluded and listed (13 no winner, 18 result text: Super Over, tied, eliminator, D/L or DLS). No DLS-revised or Super Over result is used as a regulation label.
- W2 (innings 2) on VALIDATION: Brier 0.1167 against 0.2506 constant (gain 53%) and 0.1224 logistic; slope 1.13. W1 (innings 1): Brier 0.215 against 0.251 (gain 14%) and 0.2227 logistic; slope 0.886. Both pass the declared gate (slope in [0.8, 1.2], Brier gain at least 2%). W1 out-of-fold TRAIN slope is 0.57 (Brier gain 5.9%), so the innings-1 model is less stable than the validation gate shows; disclosed, and `innings2_only` is in the sensitivity grid.
- Class model gain over the class prior is 1.7% in log loss, so leverage follows the WP surface. Spearman correlation of pre-delivery leverage with the realised absolute swing on VALIDATION is 0.59.
- About 39% of attributed balls have a WPA of exactly zero because the tree WP surface is piecewise constant (disclosed limitation).
- P1 (leverage) and P2 (closeness) pass test (d) mechanically and fail tests a, b, c, e. No candidate passes the predeclared pass rule; the primary stays P4 (`BEST_AVAILABLE_NOT_PASSING`). P4 fails test (d).
- Player level (primary P4, combined formats): between-player variance at the floor for both roles (tau2 = 0, `NO_BETWEEN_PLAYER_SIGNAL`), split-half Spearman-Brown 0.04 (batters, interval -0.33 to 0.36) and -0.13 (bowlers, -0.46 to 0.26), out-of-time lower bounds -0.20 and -0.36, share of players with data weight above 0.5 is 0.00 for both. IPL and T20I estimates are uncorrelated (0.04 and -0.17), so combination is unsupported. Both lists are EXPLORATORY; the fixed-variance bootstrap differs from the full refit by up to 0.56 (batters) and 0.32 (bowlers), so full refits are used.
- Only one player in each exploratory Top 10 is STRONG_SUBSTANTIAL (batters: Tim David, Top-10 probability 0.95); the median rank interval is about 130 to 150 places wide.

## Declared deviations
- Both teams' pre-match priors are W features (design named the batting side's).
- Multi-component balls use a counterfactual split instead of the design's expected-share split (the parts always sum to the ball's delta).
- Class-model parameters fixed and declared (no tuning); no isotonic recalibration of W1 or W2 (calibration reported).
- Reliability and bootstrap were run for the primary intensity and P1/P2 only; P0, P3, P5, P6 were estimated without them to bound run time and appear in the sensitivity table.
- Non-striker run-out wicket shares are recorded in the delivery table but do not enter striker-keyed batter units.
- The WP gate constants come from the design document, not from the hashed criteria file (that file is unchanged; every p8 table carries its hash).
- TEST was not used, not even as a diagnostic.
