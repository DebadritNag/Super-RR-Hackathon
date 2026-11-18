# Pressure methodology research: a candid account

> **Batters: EXPLORATORY.** EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.06 below 0.5; split-half lower bound not above 0.

> **Bowlers: EXPLORATORY.** EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.27 below 0.5; split-half lower bound not above 0.

## 1. The baseline: Phases 3 to 6

Phases 3 to 6 defined pressure as a percentile slice of the match situation (the `any|q0.75` definition: the top quarter of a pressure signal), compared each player with a cell baseline built from four coarse keys (competition, role, phase, wickets), and shrank the player's residual toward the cohort mean. Phase 6 tested whether this could separate players and reported:

- Between-player variance sits at the shrinkage floor in all 48 contexts.
- Pooled odd/even reliability is 0.37 (0.3656); the median over the 47 estimable contexts is 0.25.
- No context passes the 0.5 data-weight gate (0 of 48).
- No pressure definition passed the predeclared criteria; rankings are sensitive to definitions and resampling.

Causes found in the audit: the slice kept about a quarter of the balls (a median player had 26 to 55 pressure balls per cell); ball-level residuals are very noisy (RMSE about 1.75, the baseline cut it by under 1%); the between-player variance estimate collapsed to the floor so every estimate was shrunk toward the mean; and independent-ball weights overstated the precision. Phase 6 tried 18 improvement options and none reached the 0.5 data-weight gate without changing the methodology.

## 2. What Phase 8 did differently

1. **Continuous intensity instead of a slice.** Every delivery gets an intensity between 0 and 1 (empirical CDF of the raw value on TRAIN), so every delivery contributes in proportion to how difficult the situation was. Seven definitions were declared (P0 to P6).
2. **A richer, player-blind expected outcome.** Gradient boosting on the pre-delivery situation (runs, wickets, dots, boundaries), trained on TRAIN only, scored out of fold.
3. **Match-level units and REML.** The unit is one player in one innings, which gives honest clustering and a bootstrap by match. Shrinkage was kept; no floor was imposed.
4. **Three approaches, one comparison.** A (observed against expected), B (win probability added with explicit attribution) and C (a data-weighted index), compared under criteria declared and hashed before any result existed.
5. **Honest labels.** A status system (VALIDATED, PROVISIONAL, EXPLORATORY, INSUFFICIENT_EVIDENCE) tied to declared reliability thresholds, with the submitted ranking status kept apart from the model validation status.

## 3. What worked

- The win-probability models are calibrated on 2025 matches: Brier 0.117 for the chase (constant 0.251, slope 1.13) and 0.215 for the first innings (constant 0.251, slope 0.89). Both passed the declared gates.
- The WPA attribution rules are unit-tested (striker, bowler, wicket, run-out, extras) and no bowler credit is given for a run-out.
- Leakage tests show pre-delivery values do not change when later rows are truncated or outcomes are mutated; the TEST period was never opened and the protected databases were byte-identical before and after every stage.
- The approach selection, status labels and ranking are deterministic and reproducible from the stored tables (two runs give identical output hashes).

## 4. What failed, and why

- **No pressure definition passed.** The monotonic trend across intensity deciles failed for every candidate. Pressure raises wicket probability and lowers scoring in the expected direction (tests a, b and c pass for P0, P3 and P4), but not smoothly enough to meet the predeclared trend criterion. The win-probability definitions (P1 leverage, P2 closeness) failed the direction tests outright, and the defender-side definition (P5) points the wrong way for runs.

| candidate | pass | test_a | test_b | test_c | test_e | n_tests_passed | runs_diff_pooled_train | wkt_diff_pooled_train |
|---|---|---|---|---|---|---|---|---|
| P0 | no | yes | yes | yes | no | 3 | -0.059 | 0.029 |
| P1 | no | no | no | no | no | 0 | 0.005 | 0.000 |
| P2 | no | no | no | no | no | 0 | -0.010 | -0.016 |
| P3 | no | yes | yes | yes | no | 3 | -0.110 | 0.047 |
| P4 | no | yes | yes | yes | no | 3 | -0.192 | 0.057 |
| P5 | no | no | no | yes | no | 1 | 0.233 | -0.003 |
| P6 | no | no | yes | yes | no | 2 | -0.070 | 0.053 |

- **The signal is small compared with the noise.** The expected-outcome models improve on a constant by 1.5% to 3.1% (RMSE or log loss); between-player variance over noise of the A component was 0.08 for batters and 0.36 for bowlers, and the REML variance sat at the floor for Approach B in most cells and for Approach A in the T20I batter cell.
- **Split-half reliability stayed far below the thresholds.** The submitted batters' split-half figure is 0.06 (interval -0.22 to 0.36) and the bowlers' 0.27 (interval -0.08 to 0.39); both intervals include 0.
- **Approach C collapsed.** The data-derived weights gave components A and B zero weight (floor or non-positive reliability on FIT matches), so the PRI is the consistency of pressure units: how often a player beats the expectation, whatever the size. It is not independent of A, because it is built from the same residuals.

| role | component | split_half_sb | floor_fit | status | final_weight |
|---|---|---|---|---|---|
| batter | A | 0.0695 | yes | NO_SIGNAL_FLOOR | 0.0000 |
| batter | B | -0.2256 | yes | NO_SIGNAL_FLOOR | 0.0000 |
| batter | CONS | 0.1875 | no | ACTIVE | 1.0000 |
| bowler | A | -0.2329 | no | NO_SIGNAL_NONPOSITIVE_RELIABILITY | 0.0000 |
| bowler | B | -0.1001 | yes | NO_SIGNAL_FLOOR | 0.0000 |
| bowler | CONS | 0.1754 | no | ACTIVE | 1.0000 |

- **IPL and T20I do not agree.** Cross-format Spearman correlations of player estimates were between -0.17 and 0.22 across approaches and roles, with intervals that include 0, so no combination was supported.

## 5. How the thinking evolved

The first intuition was that pressure is a property of the match (a close chase, the death overs), so the task was to find the right definition and then rank. The Phase 6 failure showed the problem was not only the definition: even a generous definition leaves too few pressure balls per player, and ball outcomes carry too much luck. Phase 8 therefore moved from asking which slice is pressure to asking how much each delivery tells us, then tested whether anything could be separated. Win probability added looked like the most cricket-faithful measure, but the credit assigned to one player in one delivery is mostly the match state, and it was the least reliable of the three. The simplest measure, observed against expected, did about as well as the most elaborate. The result is a transparent ordering with honest labels, not a validated ranking.

## 6. Data handling facts

| reason | competition_type | rows | matches |
|---|---|---|---|
| OUT_OF_SCOPE_COMPETITION | OTHER_T20 | 6985 | 30 |
| RESTRICTED_INNINGS_3_4_SUPER_OVER | IPL | 10 | 1 |
| RESTRICTED_INNINGS_3_4_SUPER_OVER | T20I | 12 | 2 |
| DLS_NOT_RECONSTRUCTABLE | IPL | 377 | 3 |
| DLS_NOT_RECONSTRUCTABLE | T20I | 1941 | 23 |
| METRIC_WICKET_FLAG_ANOMALY | ALL | 11 | 11 |
| METRIC_EXTRAS_LABEL_UNVERIFIED | ALL | 205 | 166 |

Official data only; the authoritative ball-by-ball file; confirmed Super Over innings and the unverified innings 3 and 4 excluded; the 42 late-dated T20I matches excluded from primary evaluation; restriction register applied at metric level; the 2026 (TEST) matches were not used (they were opened once in Phase 4 and are not a clean hold-out).

## 7. Open decisions for the owner

- Confirm the wording of the status labels (`config/phase8_status_labels_v1.json`).
- Decide whether a labelled, non-pristine application to the 2026 matches is wanted.
- Optional: official verification of the 42 late-dated T20I matches.
- `phase8.duckdb` holds the new tables so that the protected databases stay byte-identical (deviation from the brief wording).

## 8. Selection record

- Batters: Chosen approach A by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects A and the point-estimate path selects A: the two paths agree.
- Bowlers: Chosen approach C by rule path NO_POSITIVE_LOWER_BOUND_HIGHEST_POINT_ESTIMATE. No approach has a split-half lower bound above 0, so the list is EXPLORATORY. The lower-bound path (with the 0.05 contender margin and out-of-time tie-break) selects C and the point-estimate path selects C: the two paths agree.
