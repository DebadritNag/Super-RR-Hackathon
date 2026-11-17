# Phase 8 chunk 2 verification (Approach A)

Run from `d:/Data/backend` with `$env:PYTHONUTF8=1; $env:PYTHONPATH=d:/Data/backend`.

| Command | Result |
|---|---|
| `python scripts/phase8_approach_a.py models` | 8 expected-outcome models (batter and bowler: runs, wicket, dot, boundary) fitted on TRAIN, OOF residuals cached, artefacts in `data/models/p8_expected_*_v1.{joblib,json}`; tables `p8_a_model_metrics`, `p8_a_model_grid`, `p8_a_model_deciles`, `p8_a_component_defs` |
| `python scripts/phase8_approach_a.py tests` | predeclared intensity validity tests: `p8_intensity_tests`, `p8_intensity_selection` (no candidate passes; primary P4 with basis `BEST_AVAILABLE_NOT_PASSING`) |
| `python scripts/phase8_approach_a.py estimate` | pressure units, REML (COMBINED, IPL, T20I), reliability, 1000-draw full-refit bootstrap, sensitivity, format study: `p8_a_estimates`, `p8_a_intensity_comparison`, `p8_a_reliability`, `p8_a_reml`, `p8_a_sensitivity`, `p8_a_ineligible`, `p8_a_pressure_exposure`, `p8_a_boot_check`, `p8_a_format_study`, `p8_a_status` |
| `python scripts/phase8_approach_a.py report` | `data/reports/phase8_approach_a_results.md` |
| `python -m pytest <phase8 tests> -q` | 109 passed (81 from chunk 1, 28 new: REML 6, validity 4, expected 5, approach A 8, stored outputs 5) |
| `python -m pytest -q -p no:cacheprovider` (full) | 1298 passed, 3 warnings, 1222 s (log `.agents/tasks/_p8c2_full_pytest.txt`) |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 389 files already formatted |
| `check_protected(only=())` | 234 protected files checked, unchanged (both DuckDB files included); TEST lock state unchanged at the end of each stage |

## Delivered
- `app/phase8/expected.py`: player-blind expected-outcome models, grid chosen once on VALIDATION, TRAIN scored out of fold (`match_id % 5`), VALIDATION by the TRAIN model, orientation signs, artefacts.
- `app/phase8/reml.py`: REML with analytic profile of `mu` and `sigma2`, no imposed floor, `FLOOR` flag when `tau2 = 0` is indistinguishable, bootstrap multiplicity support.
- `app/phase8/intensity_validity.py`: predeclared tests a, b, c, e, pass rule, primary choice (reference P0 never primary; basis stated when none passes).
- `app/phase8/approach_a.py`: residuals, units, eligibility, baseline and delta, bootstrap (full REML refit per draw), reliability block, evidence classes, indicative list status, sensitivity helpers.
- `app/phase8/report_a.py` and `scripts/phase8_approach_a.py` (stages models, tests, estimate, report).

## Findings carried into the report
- Expected-outcome models beat the constant by 1.5% to 3.1% on VALIDATION, calibration slope 0.94 to 0.98.
- No intensity candidate passes the predeclared pass rule (trend test e fails on TRAIN for all). P4 was used as the best available definition; this is stated and caps lists at EXPLORATORY.
- Primary cell: batter split-half Spearman-Brown 0.06 (interval -0.22 to 0.36), bowler 0.22 (-0.23 to 0.33). Out-of-time lower bound 0.02 (batter) and -0.07 (bowler). Both lists EXPLORATORY.
- Share of eligible players with data weight above 0.5 (Phase 6 gate quantity): batter 0.00, bowler 0.06.
- IPL and T20I estimates are uncorrelated (Spearman 0.10 batters, 0.06 bowlers); the combination rule is not met, so the combined list is flagged `FORMAT_COMBINATION_UNSUPPORTED_PRECISION_WEIGHTED`.
- Batter combined ordering shows exposure correlation 0.34 (flag `volume_bias_flag`).
- Fixed-variance bootstrap differs from the full refit by up to 0.21 (batters) and 0.27 (bowlers) in Top-10 inclusion, so the full refit is used for all rank statistics.

## Declared deviations and gaps
- No early stopping on an internal grouped holdout and no isotonic recalibration (calibration is reported instead).
- Candidates P1, P2 and validity test (d) need the win-probability model (Approach B); marked NOT_AVAILABLE.
- Fairness strata beyond IPL/T20I, innings and phase (batting-order group, pace or spin, opposition tercile) are deferred to the comparison chunk.
- Unit variance uses the Kish form `sigma2 * sum(w^2) / (sum w)^2` instead of `sigma2 / sum w` in the design text; it is the exact variance of an intensity-weighted mean of independent balls.
- Cross-format correlation interval uses player resampling, not match resampling.
- Thresholds, gates and the shrinkage method were not changed. Criteria file hash unchanged; every p8 table carries it.
