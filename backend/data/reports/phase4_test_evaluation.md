# Phase 4 final TEST-period evaluation

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking and not a validated methodology. No final ML model was trained. Automated tests passing does not validate the methodology.

Frozen definition `any|q0.75`, shrinkage `shrink_tau4`, baseline `p4_baseline_b0_train_frozen_v1`. The configuration was frozen from TRAIN and VALIDATION only. The test lock was opened once by `evaluate_on_test`; nothing was changed after seeing TEST outcomes.

| item | value |
|---|---|
| frozen thresholds reproduced from TRAIN | yes |
| TEST delivery rows | 33,086 |
| TEST matches | 144 |
| TEST_CORE end date | 2026-05-31 |
| players required for a player-level test | 15 |
| TEST pressure balls a qualifying player needs | 6 |


## B0 calibration on TEST (out of period)
| scope | format | role | stream | rows | matches | actual | expected | residual |
|---|---|---|---|---|---|---|---|---|
| TEST | IPL | batter | runs | 16,367 | 72 | 1.56 | 1.42 | 0.14 |
| TEST | T20I | batter | runs | 14,293 | 65 | 1.44 | 1.32 | 0.12 |
| TEST_CORE | IPL | batter | runs | 16,367 | 72 | 1.56 | 1.42 | 0.14 |
| TEST_CORE | T20I | batter | runs | 5,477 | 25 | 1.40 | 1.32 | 0.08 |
| TEST | IPL | batter | dismissal | 16,367 | 72 | 0.05 | 0.05 | -0.000178 |
| TEST | T20I | batter | dismissal | 14,293 | 65 | 0.06 | 0.06 | 0.00235 |
| TEST_CORE | IPL | batter | dismissal | 16,367 | 72 | 0.05 | 0.05 | -0.000178 |
| TEST_CORE | T20I | batter | dismissal | 5,477 | 25 | 0.06 | 0.06 | 0.00309 |
| TEST | IPL | bowler | charged | 17,138 | 72 | 1.54 | 1.41 | 0.13 |
| TEST | T20I | bowler | charged | 14,858 | 65 | 1.43 | 1.32 | 0.12 |
| TEST_CORE | IPL | bowler | charged | 17,138 | 72 | 1.54 | 1.41 | 0.13 |
| TEST_CORE | T20I | bowler | charged | 5,672 | 25 | 1.39 | 1.32 | 0.08 |
| TEST | IPL | bowler | wkt | 17,138 | 72 | 0.05 | 0.05 | -0.000106 |
| TEST | T20I | bowler | wkt | 14,858 | 65 | 0.05 | 0.05 | 0.00219 |
| TEST_CORE | IPL | bowler | wkt | 17,138 | 72 | 0.05 | 0.05 | -0.000106 |
| TEST_CORE | T20I | bowler | wkt | 5,672 | 25 | 0.06 | 0.05 | 0.00379 |


## Pressure effect on TEST (population level)
Mean B0 residual of pressure rows minus non-pressure rows of the same definition population. The interval is a seeded match-cluster bootstrap (2.5 and 97.5 percentiles).
| scope | format | role | stream | pressure rows | other rows | matches | effect | low | high | status |
|---|---|---|---|---|---|---|---|---|---|---|
| TEST | IPL | batter | runs | 3,734 | 12,633 | 72 | -0.16 | -0.23 | -0.08 | OK |
| TEST | T20I | batter | runs | 3,753 | 10,468 | 65 | -0.09 | -0.19 | 0.00762 | OK |
| TEST_CORE | IPL | batter | runs | 3,734 | 12,633 | 72 | -0.16 | -0.23 | -0.08 | OK |
| TEST_CORE | T20I | batter | runs | 1,345 | 4,060 | 25 | -0.07 | -0.21 | 0.04 | OK |
| TEST | IPL | batter | dismissal | 3,734 | 12,633 | 72 | 0.01 | 0.00524 | 0.02 | OK |
| TEST | T20I | batter | dismissal | 3,753 | 10,468 | 65 | 0.02 | 0.0069 | 0.03 | OK |
| TEST_CORE | IPL | batter | dismissal | 3,734 | 12,633 | 72 | 0.01 | 0.00524 | 0.02 | OK |
| TEST_CORE | T20I | batter | dismissal | 1,345 | 4,060 | 25 | 0.02 | 0.00816 | 0.04 | OK |
| TEST | IPL | bowler | charged | 3,914 | 13,224 | 72 | -0.15 | -0.22 | -0.07 | OK |
| TEST | T20I | bowler | charged | 3,877 | 10,902 | 65 | -0.09 | -0.18 | 0.00341 | OK |
| TEST_CORE | IPL | bowler | charged | 3,914 | 13,224 | 72 | -0.15 | -0.22 | -0.07 | OK |
| TEST_CORE | T20I | bowler | charged | 1,369 | 4,224 | 25 | -0.07 | -0.20 | 0.05 | OK |
| TEST | IPL | bowler | wkt | 3,914 | 13,224 | 72 | 0.01 | 0.00487 | 0.02 | OK |
| TEST | T20I | bowler | wkt | 3,877 | 10,902 | 65 | 0.02 | 0.00742 | 0.03 | OK |
| TEST_CORE | IPL | bowler | wkt | 3,914 | 13,224 | 72 | 0.01 | 0.00487 | 0.02 | OK |
| TEST_CORE | T20I | bowler | wkt | 1,369 | 4,224 | 25 | 0.02 | 0.01 | 0.04 | OK |


## Player level (PRE_TEST estimate against TEST outcome)
A cell is evaluated only when enough players qualify (eligible in the frozen working pool and with enough TEST pressure balls). Otherwise it is reported as insufficient and is not relaxed. Loss is the TEST-ball-weighted squared error.
| scope | format | role | eligible with TEST balls | qualifying | status | loss shrunk | loss raw | loss zero | shrunk minus raw | ci low | ci high | Spearman shrunk | Spearman raw |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TEST | IPL | batter | 83 | 69 | OK | 0.11 | 0.11 | 0.12 | -0.00588 | -0.03 | 0.02 | 0.37 | 0.37 |
| TEST | T20I | batter | 101 | 79 | OK | 0.17 | 0.16 | 0.18 | 0.01 | -0.03 | 0.06 | 0.39 | 0.39 |
| TEST_CORE | IPL | batter | 83 | 69 | OK | 0.11 | 0.11 | 0.12 | -0.00588 | -0.03 | 0.02 | 0.37 | 0.37 |
| TEST_CORE | T20I | batter | 52 | 36 | OK | 0.26 | 0.25 | 0.26 | 0.01 | -0.07 | 0.12 | 0.25 | 0.27 |
| TEST | IPL | bowler | 46 | 39 | OK | 0.07 | 0.09 | 0.08 | -0.02 | -0.04 | 0.00695 | 0.25 | 0.21 |
| TEST | T20I | bowler | 76 | 75 | OK | 0.13 | 0.17 | 0.13 | -0.04 | -0.06 | -0.00361 | 0.22 | 0.24 |
| TEST_CORE | IPL | bowler | 46 | 39 | OK | 0.07 | 0.09 | 0.08 | -0.02 | -0.04 | 0.00695 | 0.25 | 0.21 |
| TEST_CORE | T20I | bowler | 45 | 43 | OK | 0.16 | 0.21 | 0.16 | -0.05 | -0.11 | 0.00392 | 0.24 | 0.28 |


## Notes
- TEST par is strictly prior and includes earlier TEST first innings (they precede the evaluated match); the frozen thresholds were fitted on TRAIN only.
- `TEST_CORE` limits TEST to dates up to the configured core end; the later T20I dates are kept as recorded in `TEST`.
- A negative `shrunk minus raw` loss difference favours shrinkage. The interval is descriptive and not corrected for the number of cells.
