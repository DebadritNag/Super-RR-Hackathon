# Phase 4 user summary: experimental pressure scoring and temporal validation

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking and not a validated methodology. No final ML model was trained. Automated tests passing does not validate the methodology.

**Exploratory versus validated.** Everything here is exploratory. No pressure definition, threshold, shrinkage strength or format weight is validated. **Official rankings and final ML model training are not authorised and have not been done; they await your approval.**

## 1. Data split methodology
Chronological, by match date. Matches and their deliveries stay together; there is no random row split. Boundaries were written to `config/phase4_split_v1.json` before any evaluation code ran.
| period | start | end |
|---|---|---|
| TRAIN | n/a | 2024-12-31 |
| VALIDATION | 2025-01-01 | 2025-12-31 |
| TEST | 2026-01-01 | n/a |

| format | period | matches | first date | last date |
|---|---|---|---|---|
| IPL | TEST | 74 | 2026-03-28 | 2026-05-31 |
| IPL | TRAIN | 219 | 2022-03-26 | 2024-05-26 |
| IPL | VALIDATION | 74 | 2025-03-22 | 2025-06-03 |
| OTHER_T20 | TRAIN | 15 | 2024-10-18 | 2024-10-27 |
| OTHER_T20 | VALIDATION | 15 | 2025-11-14 | 2025-11-23 |
| T20I | TEST | 70 | 2026-01-07 | 2026-11-01 |
| T20I | TRAIN | 278 | 2022-01-22 | 2024-12-30 |
| T20I | VALIDATION | 122 | 2025-01-02 | 2025-12-19 |

Baseline cells, wickets bins, shrinkage strength and the shrinkage target use TRAIN only. Pressure thresholds use TRAIN only. VALIDATION chose the shrinkage strength. TEST was opened once, after the choices were frozen.

## 2. Temporal leakage checks
| item | value |
|---|---|
| matches in more than one period | 0 |
| rows whose period differs from the date rule | 0 |
| periods strictly ordered by date | yes |
| par: rows unavailable (insufficient prior matches) | 7,692 |
| par: innings unavailable | 63 |
| par: null pattern identical to the earlier prior-only column | yes |
| phase labels equal a function of (legal balls before, limit) | yes |
| labels unchanged when the last 30% of each innings is removed | yes |
| test lock: FREEZE recorded before OPEN | yes |
| test lock: opened exactly once | yes |
| test lock: hash at open equals hash at freeze | yes |
| test lock: refused reads logged | 0 |
| frozen thresholds reproduced inside the TEST run | yes |

Par uses only matches dated strictly before the evaluated match (same-day matches excluded); with too few prior matches the value is missing and flagged, never zero. Leave-one-match-out par is descriptive only. The lock is a convention-level guard, not a security boundary.

## 3. Baseline calibration
Baseline `p4_baseline_b0_train_frozen_v1`; calibration identity on TRAIN holds: True.
| stream | VALIDATION rows | mean residual | residual sd | TRAIN identity relative diff |
|---|---|---|---|---|
| batter:runs | 41,740 | 0.05 | 1.75 | 0.00 |
| batter:dismissal | 41,740 | 0.00152 | 0.23 | 0.00 |
| bowler:charged | 43,376 | 0.05 | 1.73 | 0.00 |
| bowler:wkt | 43,376 | 0.00159 | 0.22 | 0.00 |

Details by format, phase, wickets remaining, expected decile and year are in `phase4_baseline_calibration_report.md`.

## 4. Pressure definition comparison
Rule file SHA-256 `c8ae7e837f30978dd6e252007a3a42440080ccd53c6be3606745fd28f2bb497f` (written before the metrics). The rule winner is `any|q0.75`, labelled: PROVISIONAL, one of 9 examined (multiplicity not corrected). The Phase 3 leading candidate `chase|q0.9` has status `OK` and is not in the top group (any|q0.75, any|q0.9, chase|q0.75; tie margin 0.055). Eligible population never decides the choice.
| definition | status | Sc | bootstrap SE | selection share | min players per cell |
|---|---|---|---|---|---|
| chase|q0.75 | OK | 0.25 | 0.06 | 0.30 | 93 |
| chase|q0.9 | OK | 0.17 | 0.09 | 0.05 | 41 |
| chase|q0.95 | NOT_RANKABLE | 0.22 | 0.16 | 0.00 | 18 |
| inn1|q0.75 | OK | 0.15 | 0.05 | 0.02 | 92 |
| inn1|q0.9 | OK | 0.10 | 0.11 | 0.05 | 49 |
| inn1|q0.95 | NOT_RANKABLE | -0.25 | 0.27 | 0.00 | 19 |
| any|q0.75 | OK | 0.24 | 0.04 | 0.33 | 123 |
| any|q0.9 | OK | 0.26 | 0.06 | 0.15 | 78 |
| any|q0.95 | OK | 0.15 | 0.09 | 0.09 | 45 |

The winner takes 0.33 of the bootstrap resamples; 3 candidates lie within the tie margin (0.055) of the best score. The choice is therefore weak, and no multiplicity correction is applied. Full table: `phase4_definition_comparison.md`.

## 5. Eligibility thresholds
Thresholds were re-derived per format and role from TRAIN distributions. All 4 format-role cells are THRESHOLD_NOT_VALIDATED: no data-derived threshold passed the pre-declared data-weight gate, so none is validated and none was lowered to reach ten players. A labelled working pool is used downstream.
| format | role | status | working threshold (balls) | window ratio | pool size |
|---|---|---|---|---|---|
| IPL | batter | THRESHOLD_NOT_VALIDATED | 20 | 1.31 | 132 |
| T20I | batter | THRESHOLD_NOT_VALIDATED | 16 | 1.47 | 243 |
| IPL | bowler | THRESHOLD_NOT_VALIDATED | 49 | 1.31 | 80 |
| T20I | bowler | THRESHOLD_NOT_VALIDATED | 29 | 1.47 | 141 |


## 6. Shrinkage
Chosen on VALIDATION: `shrink_tau4` (rule: non-default only if paired loss difference < -1 bootstrap SE; none/target0 never chosen). Zero shrinkage is retained as a sensitivity configuration.
| config | validation loss | difference vs eb | bootstrap SE | choosable |
|---|---|---|---|---|
| shrink_eb | 0.07 | 0.00 | 0.00 | yes |
| shrink_floor0.001 | 0.07 | 0.00123 | 0.000202 | yes |
| shrink_none | 0.15 | 0.08 | 0.02 | no |
| shrink_target0 | 0.07 | 0.00058 | 0.000486 | no |
| shrink_tau0.5 | 0.07 | 0.00 | 0.00 | yes |
| shrink_tau2 | 0.07 | -0.00106 | 0.000196 | yes |
| shrink_tau4 | 0.07 | -0.00252 | 0.000524 | yes |


## 7. Format weighting (independent of the definition comparison)
70:30 stays a provisional default; the evidence does not show it is optimal or validated. Pools are players eligible in both formats under the same frozen rules.
| role | config | pool | Top 10 overlap vs 70:30 | Spearman vs 70:30 | bootstrap Spearman |
|---|---|---|---|---|---|
| batter | w100_0 | 48 | 9 | 0.95 | 0.74 |
| batter | w85_15 | 48 | 9 | 0.98 | 0.73 |
| batter | w80_20 | 48 | 9 | 0.99 | 0.73 |
| batter | w70_30 | 48 | 10 | 1.00 | 0.73 |
| batter | w60_40 | 48 | 8 | 0.99 | 0.72 |
| batter | w55_45 | 48 | 8 | 0.97 | 0.72 |
| batter | w50_50 | 48 | 7 | 0.95 | 0.71 |
| batter | w0_100 | 48 | 3 | 0.46 | 0.74 |
| bowler | w100_0 | 39 | 9 | 0.92 | 0.77 |
| bowler | w85_15 | 39 | 10 | 0.97 | 0.79 |
| bowler | w80_20 | 39 | 10 | 0.99 | 0.79 |
| bowler | w70_30 | 39 | 10 | 1.00 | 0.81 |
| bowler | w60_40 | 39 | 9 | 0.99 | 0.82 |
| bowler | w55_45 | 39 | 9 | 0.98 | 0.83 |
| bowler | w50_50 | 39 | 9 | 0.96 | 0.83 |
| bowler | w0_100 | 39 | 5 | 0.61 | 0.79 |


## 8. Ranking stability (experimental distributions, not rankings)
| format | role | pool | expected Top 10 overlap | mean Spearman | Spearman 2.5% | Spearman 97.5% |
|---|---|---|---|---|---|---|
| IPL | batter | 132 | 5.24 | 0.80 | 0.72 | 0.87 |
| T20I | batter | 243 | 4.88 | 0.82 | 0.76 | 0.87 |
| IPL | bowler | 80 | 6.20 | 0.76 | 0.64 | 0.84 |
| T20I | bowler | 141 | 5.53 | 0.77 | 0.69 | 0.84 |

Pools are never padded; pools smaller than ten are reported as they are.

## 9. Uncertainty
| role | stream | format | eligible | median interval width | share of intervals excluding 0 |
|---|---|---|---|---|---|
| batter | dismissal | COMBINED_w70_30 | 48 | 0.01 | 0.73 |
| batter | dismissal | IPL | 132 | 0.02 | 0.42 |
| batter | dismissal | T20I | 243 | 0.01 | 0.69 |
| batter | runs | COMBINED_w70_30 | 48 | 0.12 | 0.25 |
| batter | runs | IPL | 132 | 0.15 | 0.26 |
| batter | runs | T20I | 243 | 0.12 | 0.39 |
| bowler | charged | COMBINED_w70_30 | 39 | 0.14 | 0.18 |
| bowler | charged | IPL | 80 | 0.18 | 0.17 |
| bowler | charged | T20I | 141 | 0.14 | 0.22 |
| bowler | wkt | COMBINED_w70_30 | 39 | 0.02 | 0.41 |
| bowler | wkt | IPL | 80 | 0.02 | 0.25 |
| bowler | wkt | T20I | 141 | 0.02 | 0.64 |

Median width of the rank interval (95%):

| format | role | median rank-interval width |
|---|---|---|
| IPL | batter | 67.11 |
| IPL | bowler | 48.39 |
| T20I | batter | 101.03 |
| T20I | bowler | 75.00 |


## 10. Final TEST evaluation
The frozen configuration was evaluated once on 144 TEST matches. Population-level pressure effects: 8 cells estimated. Player-level: 4 cells with enough qualifying players, 0 reported as insufficient. Details and intervals: `phase4_test_evaluation.md`.

B0 mean residual on TEST for the run streams ranges from 0.119 to 0.142 runs per ball (VALIDATION values are in section 3); a positive value means the TRAIN-frozen baseline under-predicts scoring in the TEST year.

The shrunk-minus-raw loss interval excludes 0 in 1 of 4 cells; the intervals are not corrected for the number of cells.

| format | role | qualifying | shrunk minus raw loss | ci low | ci high |
|---|---|---|---|---|---|
| IPL | batter | 69 | -0.00588 | -0.03 | 0.02 |
| T20I | batter | 79 | 0.01 | -0.03 | 0.06 |
| IPL | bowler | 39 | -0.02 | -0.04 | 0.00695 |
| T20I | bowler | 75 | -0.04 | -0.06 | -0.00361 |


## 11. Data-quality restrictions applied
Register `data_quality_restrictions_v1` (26 rules, global exclusion False). Innings 3 and 4, DLS rows that cannot be reconstructed, `Penalty` extras, and wicket-flag anomalies are masked per rule; 3404 DLS rows in 50 innings are excluded and no resources are imputed. Details: `phase4_data_quality_report.md`. The T20I dates after 2026-05-31 (42 matches, last 2026-11-01) need your confirmation.

## 12. Classification coverage (uncapped intelligence)
1217 players. Verified Uncapped: 0. Nationality and status are independent fields with per-field verification.
| nationality | status | all players | players with an eligible score |
|---|---|---|---|
| Indian | Capped | 52 | 51 |
| Indian | Uncapped | 0 | 0 |
| Indian | Unknown | 112 | 35 |
| Overseas | Capped | 603 | 288 |
| Overseas | Uncapped | 0 | 0 |
| Overseas | Unknown | 3 | 1 |
| Unknown | Capped | 0 | 0 |
| Unknown | Uncapped | 0 | 0 |
| Unknown | Unknown | 447 | 28 |

Nationality unknown reasons: {"NO_SOURCE_RECORD": 445, "SQUAD_NAME_AMBIGUOUS": 2}. Status unknown reasons: {"NOT_PROVEN_CAPPED_IN_DATA": 498, "FIRST_T20I_AFTER_AS_OF_DATE": 64}. Every uncapped ranking and preset is empty or reports a pool-too-small status until a verified cap source is supplied.

## 13. Known limitations
- For the carried definition, the estimated between-player variance is not above noise (signal-to-noise at or below 0) in 4 of 4 format-role-stream cells. Where it is not above noise, estimates shrink strongly toward the pool and rankings are fragile.
- Bowler pressure uses batter state signals. The primary residual mixes pressure-specific and general skill.
- Shrinkage and eligibility choices rest on small samples; no multiplicity correction.
- The bootstrap holds thresholds, baseline and shrinkage strength fixed.
- 4 of 4 player-level TEST cells had enough qualifying players (cells without enough are reported as insufficient, never relaxed).

## 14. Recommended final methodology (a recommendation that needs your approval)
- Keep the B0 baseline fitted on TRAIN (or on TRAIN plus VALIDATION after approval).
- Treat `any|q0.75` as one of several defensible definitions, not the answer; the rule winner and `chase|q0.9` are not distinguished with confidence.
- Use leave-one-player-out shrinkage toward the pooled mean of other players (`shrink_tau4` here) and always publish intervals and the data weight.
- Do not publish a Top 10 until a threshold passes the data-weight gate or you accept the working-pool label, and until more matches accumulate.
- Keep 70:30 labelled provisional unless you accept it as a policy choice.

## 15. Open decisions for you
1. Accept or change the split boundaries and the TEST period (including the late T20I dates).
2. Choose the pressure definition (rule winner, the Phase 3 leading candidate, or another).
3. Decide whether a working pool below the data-weight gate may support any public output.
4. Decide whether to refit on TRAIN plus VALIDATION for the final model.
5. Supply the classification source below, or confirm that status stays Unknown.
6. Approve (or not) the next stage: official rankings and any ML model training.

## 16. Data request list
- A verified list of capped/uncapped status keyed by `player_id` (or name plus team), from an official board or ICC record or a squad sheet with a capped column.
- `player_id` keys for the 25 unresolved squad names (`phase4_unresolved_players.csv`).
- Nationality for players outside the squad file, if needed.
- Confirmation of the T20I match dates after the TEST core end.

## 17. Reproducibility and preservation
Independent spot checks: 7 of 7 agree (`phase4_spot_checks.json`).

| check | method | ok |
|---|---|---|
| strictly_prior_par_from_raw_csv | csv module on updated_ball_by_ball.csv and matches.csv; prior dates only | yes |
| period_match_counts_from_raw_csv | csv module on matches.csv and matches 2026.csv; boundaries from split config | yes |
| player_pressure_balls_direct_sql | DuckDB SQL on the stored state table, definition rebuilt from frozen thresholds | yes |
| shrunk_estimate_from_stored_components | pandas on the stored frozen-rules score table | yes |
| capped_count_from_playing_eleven_csv | csv module on competitions.csv, matches.csv and playing_eleven.csv | yes |
| top10_inclusion_probability_sums | pandas on the stored ranking distributions | yes |
| official_data_hashes | SHA-256 against phase4_hash_before.txt | yes |

