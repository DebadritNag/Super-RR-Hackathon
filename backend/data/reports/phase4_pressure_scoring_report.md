# Phase 4 pressure scoring report (Stage C)

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking and not a validated methodology. No final ML model was trained. Automated tests passing does not validate the methodology.

These are experimental player estimates, not rankings. All 4 format-role cells are THRESHOLD_NOT_VALIDATED: no data-derived threshold passed the pre-declared data-weight gate, so none is validated and none was lowered to reach ten players. A labelled working pool is used downstream. Players in the working pool are labelled by their eligibility status below.

## Configuration (frozen before the TEST period was opened)
| item | value |
|---|---|
| carried definition | any|q0.75 (PROVISIONAL rule winner) |
| leading provisional (Phase 3, not validated) | chase|q0.9 |
| pressure definition version | p4_pressure_def_v1 |
| baseline version | p4_baseline_b0_train_frozen_v1 |
| shrinkage configuration | shrink_tau4 |
| shrinkage rule | non-default only if paired loss difference < -1 bootstrap SE; none/target0 never chosen |
| seed | 20260512 |
| bootstrap resamples | 1,000 |
| window | PRE_TEST |
| TRAIN-only thresholds | {"chase|IPL": 12.28125, "chase|T20I": 11.625, "inn1|IPL": 5.9512195122, "inn1|T20I": 8.4745762712} |


Zero shrinkage (`shrink_none`) is kept as a sensitivity configuration for the carried definition. All nine candidate definitions are scored under the frozen shrinkage configuration; the carried definition is flagged `is_carried_definition` and `chase|q0.9` is flagged `is_leading_provisional` so the choice can be reviewed.

## Record schema
Each record holds: `status`, `official_ranking`, `player_id`, `role`, `stream`, `format`, `window`, `definition_id`, `definition_version`, `baseline_version`, `shrinkage_config`, `raw_pressure_outcome`, `expected_baseline_outcome`, `residual`, `shrunk_estimate`, `interval_low`, `interval_high`, `posterior_sd`, `data_weight`, `shrinkage_k`, `shrinkage_floor_hit`, `pressure_opportunities`, `distinct_matches`, `effective_sample_size`, `eligibility_status`, `eligibility_basis`, `applied_restrictions`.

## Records and eligible players by definition (all shrinkage configurations scored)
| definition | records | eligible |
|---|---|---|
| any|q0.75 | 5,728 | 2,732 |
| any|q0.9 | 2,204 | 676 |
| any|q0.95 | 1,750 | 254 |
| chase|q0.75 | 2,246 | 832 |
| chase|q0.9 | 1,674 | 254 |
| chase|q0.95 | 1,352 | 76 |
| inn1|q0.75 | 2,184 | 768 |
| inn1|q0.9 | 1,528 | 296 |
| inn1|q0.95 | 1,096 | 116 |


## Cells of the carried definition (frozen shrinkage, eligible = working pool)
| role | stream | format | records | eligible | median_pressure_balls_eligible | median_data_weight | median_interval_width | share_interval_excludes_0 | floor_hit_share |
|---|---|---|---|---|---|---|---|---|---|
| batter | dismissal | COMBINED_w70_30 | 48 | 48 | 213.50 | n/a | 0.01 | 0.73 | 0.00 |
| batter | dismissal | IPL | 267 | 132 | 80.50 | 0.19 | 0.02 | 0.42 | 1.00 |
| batter | dismissal | T20I | 537 | 243 | 51.00 | 0.13 | 0.01 | 0.69 | 1.00 |
| batter | runs | COMBINED_w70_30 | 48 | 48 | 213.50 | n/a | 0.12 | 0.25 | 0.00 |
| batter | runs | IPL | 267 | 132 | 80.50 | 0.19 | 0.15 | 0.26 | 1.00 |
| batter | runs | T20I | 537 | 243 | 51.00 | 0.13 | 0.12 | 0.39 | 1.00 |
| bowler | charged | COMBINED_w70_30 | 39 | 39 | 356.00 | n/a | 0.14 | 0.18 | 0.00 |
| bowler | charged | IPL | 182 | 80 | 149.00 | 0.29 | 0.18 | 0.17 | 1.00 |
| bowler | charged | T20I | 359 | 141 | 100.00 | 0.22 | 0.14 | 0.22 | 1.00 |
| bowler | wkt | COMBINED_w70_30 | 39 | 39 | 356.00 | n/a | 0.02 | 0.41 | 0.00 |
| bowler | wkt | IPL | 182 | 80 | 149.00 | 0.29 | 0.02 | 0.25 | 1.00 |
| bowler | wkt | T20I | 359 | 141 | 100.00 | 0.22 | 0.02 | 0.64 | 1.00 |


## Eligible pools: carried definition versus the leading provisional
| role | stream | format | eligible_any|q0.75 | eligible_chase|q0.9 |
|---|---|---|---|---|
| batter | dismissal | COMBINED_w70_30 | 48 | 5 |
| batter | dismissal | IPL | 132 | 35 |
| batter | dismissal | T20I | 243 | 48 |
| batter | runs | COMBINED_w70_30 | 48 | 5 |
| batter | runs | IPL | 132 | 35 |
| batter | runs | T20I | 243 | 48 |
| bowler | charged | COMBINED_w70_30 | 39 | 3 |
| bowler | charged | IPL | 80 | 14 |
| bowler | charged | T20I | 141 | 22 |
| bowler | wkt | COMBINED_w70_30 | 39 | 3 |
| bowler | wkt | IPL | 80 | 14 |
| bowler | wkt | T20I | 141 | 22 |


## Shrinkage effect on the carried definition
Mean absolute difference between the shrunk estimates under the frozen configuration and under zero shrinkage, and the median interval width of each.
| role | stream | format | players | mean abs diff | median width (frozen) | median width (zero) |
|---|---|---|---|---|---|---|
| batter | dismissal | COMBINED_w70_30 | 48 | 0.01 | 0.01 | 0.09 |
| batter | dismissal | IPL | 267 | 0.07 | 0.01 | 0.08 |
| batter | dismissal | T20I | 537 | 0.08 | 0.01 | 0.11 |
| batter | runs | COMBINED_w70_30 | 48 | 0.19 | 0.12 | 0.68 |
| batter | runs | IPL | 267 | 0.47 | 0.14 | 0.67 |
| batter | runs | T20I | 537 | 0.46 | 0.10 | 0.61 |
| bowler | charged | COMBINED_w70_30 | 39 | 0.10 | 0.14 | 0.45 |
| bowler | charged | IPL | 182 | 0.33 | 0.13 | 0.66 |
| bowler | charged | T20I | 359 | 0.36 | 0.10 | 0.55 |
| bowler | wkt | COMBINED_w70_30 | 39 | 0.00894 | 0.02 | 0.05 |
| bowler | wkt | IPL | 182 | 0.03 | 0.01 | 0.06 |
| bowler | wkt | T20I | 359 | 0.04 | 0.01 | 0.07 |


## Eligibility status values
| status | records |
|---|---|
| NOT_ELIGIBLE | 2,996 |
| ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 2,384 |
| ELIGIBLE_WORKING_POOL_NOT_VALIDATED|ELIGIBLE_WORKING_POOL_NOT_VALIDATED | 348 |


## Applied data restrictions
innings 1-2 only; IPL/T20I only; DLS-affected innings excluded (not imputed); innings-1 par strictly prior (insufficient prior => not flagged); thresholds TRAIN-only; TEST excluded

## Final TEST evaluation
See `phase4_test_evaluation.md`. It uses this frozen configuration and changes no value in this report.

## Limitations
- The primary residual mixes pressure-specific skill and general skill (B0 has no player term). A within-player differential is not reported.
- Bowler pressure uses the batter state signals (the bowler-specific signal is not implemented).
- Intervals hold the shrinkage strength and target fixed; between-player variance uncertainty is not propagated.
- Combined records exist only for players eligible in both formats under the same frozen rules. The 70:30 weight is a provisional default, not an optimised weight.
- A shrinkage strength was chosen on VALIDATION; compare the differences between candidate strengths with their bootstrap error in the shrinkage report.
- `shrinkage_floor_hit` true means the fitted between-player variance fell below the floor, so the strength is capped by the floor (see the floor-hit share above).
- For the carried definition, the estimated between-player variance is not above noise (signal-to-noise at or below 0) in 4 of 4 format-role-stream cells. Where it is not above noise, estimates shrink strongly toward the pool and rankings are fragile.
