# Player selection explanations

> **Batters: EXPLORATORY.** EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.06 below 0.5; split-half lower bound not above 0.

> **Bowlers: EXPLORATORY.** EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.27 below 0.5; split-half lower bound not above 0.

Each section explains why a player is in the submitted Top 10, what the numbers are, how much evidence stands behind them and how firmly the position is supported. Every figure is read from `p8_rankings` (the same table as the CSV and JSON files). The pressure situation is the P4 resource-scarcity definition, which did not pass the predeclared validity tests, so every row is EXPLORATORY.

## Batters: EXPLORATORY (approach A)

EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.06 below 0.5; split-half lower bound not above 0.

### 1. Suryakumar Yadav (player 1699)

**Why selected.** Rank 1 by context-adjusted pressure performance (+0.0440). On pressure deliveries the batter scored 1.87 runs per ball against 1.61 expected for the same match situations; dismissal rate 0.048 against 0.060 expected. Normal-play baseline +0.064, pressure level +0.118, difference +0.054. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 72 pressure innings and 1247 pressure deliveries in 118 matches. Top-10 inclusion 91%, 95% rank interval 1 to 17, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1247 pressure deliveries in 72 innings: phases (powerplay 4, middle 884, death 359), innings 1 578 and innings 2 669; mean intensity 0.50.
- **Actual performance against expectation.** Observed 1.87 runs per ball against 1.61 expected; dismissal rate 0.048 against 0.060.
- **Baseline and difference.** Normal-play baseline 0.064, pressure level (unshrunk) 0.118, difference 0.054 (A-residual units per ball).
- **Score and components.** Score 0.0440 [0.0306, 0.0590] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.072, comp_dot 0.001, comp_runs 0.265, comp_wicket 0.012.
- **Consistency across matches.** 57% of pressure units beat the expectation; between-unit dispersion 0.511; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 118 matches (IPL 51, T20I 67), 2413 deliveries with a defined intensity, effective sample 2130, data weight (reliability of the estimate) 0.25. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 91%, 95% rank interval 1 to 17.
- **Rank under each approach and format.** A 1, B 33, C 8; IPL only 3, T20I only 3, combined 1 (IPL share of matches 43%; IPL score 0.0185, T20I score 0.1165).
- **Why this position.** Relative to neighbours: rank 2 (Tim David) is below: score difference 0.005354, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 2. Tim David (player 6396)

**Why selected.** Rank 2 by context-adjusted pressure performance (+0.0386). On pressure deliveries the batter scored 1.76 runs per ball against 1.56 expected for the same match situations; dismissal rate 0.052 against 0.069 expected. Normal-play baseline +0.223, pressure level +0.115, difference -0.107. The pressure level is below the normal-play baseline: the rank reflects performance above expectation in pressure situations, not an improvement over the player's normal play. Evidence: 74 pressure innings and 961 pressure deliveries in 77 matches. Top-10 inclusion 83%, 95% rank interval 1 to 33, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 961 pressure deliveries in 74 innings: phases (powerplay 0, middle 423, death 538), innings 1 486 and innings 2 475; mean intensity 0.76.
- **Actual performance against expectation.** Observed 1.76 runs per ball against 1.56 expected; dismissal rate 0.052 against 0.069.
- **Baseline and difference.** Normal-play baseline 0.223, pressure level (unshrunk) 0.115, difference -0.107 (A-residual units per ball).
- **Score and components.** Score 0.0386 [0.0255, 0.0517] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.041, comp_dot 0.007, comp_runs 0.200, comp_wicket 0.017.
- **Consistency across matches.** 55% of pressure units beat the expectation; between-unit dispersion 0.637; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 77 matches (IPL 42, T20I 35), 979 deliveries with a defined intensity, effective sample 942, data weight (reliability of the estimate) 0.20. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 83%, 95% rank interval 1 to 33.
- **Rank under each approach and format.** A 2, B 3, C 2; IPL only 4, T20I only 6, combined 2 (IPL share of matches 55%; IPL score 0.0168, T20I score 0.0935).
- **Why this position.** Relative to neighbours: rank 1 (Suryakumar Yadav) is above: score difference 0.005354, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 3 (Heinrich Klaasen) is below: score difference 0.005024, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 3. Heinrich Klaasen (player 4260)

**Why selected.** Rank 3 by context-adjusted pressure performance (+0.0336). On pressure deliveries the batter scored 1.74 runs per ball against 1.54 expected for the same match situations; dismissal rate 0.049 against 0.059 expected. Normal-play baseline +0.095, pressure level +0.096, difference +0.001. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 48 pressure innings and 870 pressure deliveries in 55 matches. Top-10 inclusion 60%, 95% rank interval 2 to 42, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 870 pressure deliveries in 48 innings: phases (powerplay 11, middle 560, death 299), innings 1 487 and innings 2 383; mean intensity 0.65.
- **Actual performance against expectation.** Observed 1.74 runs per ball against 1.54 expected; dismissal rate 0.049 against 0.059.
- **Baseline and difference.** Normal-play baseline 0.095, pressure level (unshrunk) 0.096, difference 0.001 (A-residual units per ball).
- **Score and components.** Score 0.0336 [0.0243, 0.0436] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.021, comp_dot 0.074, comp_runs 0.193, comp_wicket 0.010.
- **Consistency across matches.** 67% of pressure units beat the expectation; between-unit dispersion 0.464; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 55 matches (IPL 39, T20I 16), 1018 deliveries with a defined intensity, effective sample 962, data weight (reliability of the estimate) 0.19. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 60%, 95% rank interval 2 to 42.
- **Rank under each approach and format.** A 3, B 41, C 1; IPL only 2, T20I only 13, combined 3 (IPL share of matches 71%; IPL score 0.0186, T20I score 0.0739).
- **Why this position.** Relative to neighbours: rank 2 (Tim David) is above: score difference 0.005024, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 4 (Romario Shepherd) is below: score difference 0.0008208, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 4. Romario Shepherd (player 6726)

**Why selected.** Rank 4 by context-adjusted pressure performance (+0.0328). On pressure deliveries the batter scored 1.59 runs per ball against 1.44 expected for the same match situations; dismissal rate 0.056 against 0.081 expected. Normal-play baseline -0.326, pressure level +0.116, difference +0.442. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 53 pressure innings and 613 pressure deliveries in 54 matches. Top-10 inclusion 63%, 95% rank interval 1 to 58, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 613 pressure deliveries in 53 innings: phases (powerplay 1, middle 239, death 373), innings 1 320 and innings 2 293; mean intensity 0.87.
- **Actual performance against expectation.** Observed 1.59 runs per ball against 1.44 expected; dismissal rate 0.056 against 0.081.
- **Baseline and difference.** Normal-play baseline -0.326, pressure level (unshrunk) 0.116, difference 0.442 (A-residual units per ball).
- **Score and components.** Score 0.0328 [0.0220, 0.0438] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.036, comp_dot -0.009, comp_runs 0.148, comp_wicket 0.025.
- **Consistency across matches.** 62% of pressure units beat the expectation; between-unit dispersion 0.710; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 54 matches (IPL 12, T20I 42), 582 deliveries with a defined intensity, effective sample 575, data weight (reliability of the estimate) 0.14. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 63%, 95% rank interval 1 to 58.
- **Rank under each approach and format.** A 4, B 126, C 3; IPL only 21, T20I only 10, combined 4 (IPL share of matches 22%; IPL score 0.0086, T20I score 0.0797).
- **Why this position.** Relative to neighbours: rank 3 (Heinrich Klaasen) is above: score difference 0.0008208, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 5 (Andre Russell) is below: score difference 0.0004909, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 5. Andre Russell (player 1318)

**Why selected.** Rank 5 by context-adjusted pressure performance (+0.0323). On pressure deliveries the batter scored 1.72 runs per ball against 1.47 expected for the same match situations; dismissal rate 0.061 against 0.064 expected. Evidence: 57 pressure innings and 785 pressure deliveries in 57 matches. Top-10 inclusion 52%, 95% rank interval 1 to 80, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 785 pressure deliveries in 57 innings: phases (powerplay 0, middle 413, death 372), innings 1 484 and innings 2 301; mean intensity 0.81.
- **Actual performance against expectation.** Observed 1.72 runs per ball against 1.47 expected; dismissal rate 0.061 against 0.064.
- **Baseline and difference.** Normal-play baseline n/a, pressure level (unshrunk) 0.096, difference n/a (A-residual units per ball).
- **Score and components.** Score 0.0323 [0.0202, 0.0450] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.076, comp_dot -0.074, comp_runs 0.253, comp_wicket 0.003.
- **Consistency across matches.** 53% of pressure units beat the expectation; between-unit dispersion 0.671; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 57 matches (IPL 45, T20I 12), 732 deliveries with a defined intensity, effective sample 717, data weight (reliability of the estimate) 0.17. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 52%, 95% rank interval 1 to 80.
- **Rank under each approach and format.** A 5, B 58, C 16; IPL only 8, T20I only 1, combined 5 (IPL share of matches 79%; IPL score 0.0142, T20I score 0.1246).
- **Why this position.** Relative to neighbours: rank 4 (Romario Shepherd) is above: score difference 0.0004909, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 6 (Tristan Stubbs) is below: score difference 0.001561, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 6. Tristan Stubbs (player 20702)

**Why selected.** Rank 6 by context-adjusted pressure performance (+0.0307). On pressure deliveries the batter scored 1.65 runs per ball against 1.53 expected for the same match situations; dismissal rate 0.042 against 0.060 expected. Normal-play baseline -0.128, pressure level +0.086, difference +0.215. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 46 pressure innings and 763 pressure deliveries in 52 matches. Top-10 inclusion 42%, 95% rank interval 2 to 86, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 763 pressure deliveries in 46 innings: phases (powerplay 12, middle 450, death 301), innings 1 411 and innings 2 352; mean intensity 0.69.
- **Actual performance against expectation.** Observed 1.65 runs per ball against 1.53 expected; dismissal rate 0.042 against 0.060.
- **Baseline and difference.** Normal-play baseline -0.128, pressure level (unshrunk) 0.086, difference 0.215 (A-residual units per ball).
- **Score and components.** Score 0.0307 [0.0199, 0.0426] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.016, comp_dot 0.074, comp_runs 0.119, comp_wicket 0.018.
- **Consistency across matches.** 59% of pressure units beat the expectation; between-unit dispersion 0.497; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 52 matches (IPL 30, T20I 22), 824 deliveries with a defined intensity, effective sample 783, data weight (reliability of the estimate) 0.17. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 42%, 95% rank interval 2 to 86.
- **Rank under each approach and format.** A 6, B 65, C 5; IPL only 5, T20I only 36, combined 6 (IPL share of matches 58%; IPL score 0.0158, T20I score 0.0296).
- **Why this position.** Relative to neighbours: rank 5 (Andre Russell) is above: score difference 0.001561, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 7 (David Miller) is below: score difference 0.0001629, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 7. David Miller (player 1077)

**Why selected.** Rank 7 by context-adjusted pressure performance (+0.0305). On pressure deliveries the batter scored 1.55 runs per ball against 1.54 expected for the same match situations; dismissal rate 0.038 against 0.063 expected. Normal-play baseline -0.062, pressure level +0.070, difference +0.132. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 65 pressure innings and 1068 pressure deliveries in 69 matches. Top-10 inclusion 33%, 95% rank interval 2 to 110, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1068 pressure deliveries in 65 innings: phases (powerplay 3, middle 606, death 459), innings 1 421 and innings 2 647; mean intensity 0.68.
- **Actual performance against expectation.** Observed 1.55 runs per ball against 1.54 expected; dismissal rate 0.038 against 0.063.
- **Baseline and difference.** Normal-play baseline -0.062, pressure level (unshrunk) 0.070, difference 0.132 (A-residual units per ball).
- **Score and components.** Score 0.0305 [0.0178, 0.0446] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary -0.009, comp_dot 0.030, comp_runs 0.007, comp_wicket 0.025.
- **Consistency across matches.** 54% of pressure units beat the expectation; between-unit dispersion 0.379; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 69 matches (IPL 48, T20I 21), 1106 deliveries with a defined intensity, effective sample 1070, data weight (reliability of the estimate) 0.22. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 33%, 95% rank interval 2 to 110.
- **Rank under each approach and format.** A 7, B 56, C 9; IPL only 11, T20I only 15, combined 7 (IPL share of matches 70%; IPL score 0.0124, T20I score 0.0653).
- **Why this position.** Relative to neighbours: rank 6 (Tristan Stubbs) is above: score difference 0.0001629, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 8 (Rinku Singh) is below: score difference 0.0004823, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 8. Rinku Singh (player 4708)

**Why selected.** Rank 8 by context-adjusted pressure performance (+0.0301). On pressure deliveries the batter scored 1.60 runs per ball against 1.55 expected for the same match situations; dismissal rate 0.045 against 0.066 expected. Normal-play baseline +0.025, pressure level +0.072, difference +0.047. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 63 pressure innings and 966 pressure deliveries in 67 matches. Top-10 inclusion 31%, 95% rank interval 2 to 108, evidence class INCONSISTENT. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 966 pressure deliveries in 63 innings: phases (powerplay 5, middle 472, death 489), innings 1 628 and innings 2 338; mean intensity 0.73.
- **Actual performance against expectation.** Observed 1.60 runs per ball against 1.55 expected; dismissal rate 0.045 against 0.066.
- **Baseline and difference.** Normal-play baseline 0.025, pressure level (unshrunk) 0.072, difference 0.047 (A-residual units per ball).
- **Score and components.** Score 0.0301 [0.0180, 0.0422] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.013, comp_dot 0.020, comp_runs 0.048, comp_wicket 0.021.
- **Consistency across matches.** 48% of pressure units beat the expectation; between-unit dispersion 0.353; evidence class INCONSISTENT.
- **Evidence amount.** 67 matches (IPL 43, T20I 24), 1003 deliveries with a defined intensity, effective sample 961, data weight (reliability of the estimate) 0.20. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 31%, 95% rank interval 2 to 108.
- **Rank under each approach and format.** A 8, B 72, C 39; IPL only 14, T20I only 9, combined 8 (IPL share of matches 64%; IPL score 0.0103, T20I score 0.0823).
- **Why this position.** Relative to neighbours: rank 7 (David Miller) is above: score difference 0.0004823, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 9 (Nicholas Pooran) is below: score difference 0.0001957, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5. The declared evidence class is INCONSISTENT (positive-unit share below 0.5, or dispersion above the cohort's 75th percentile with a positive mean), so the position rests on a few large positive units.

### 9. Nicholas Pooran (player 3125)

**Why selected.** Rank 9 by context-adjusted pressure performance (+0.0299). On pressure deliveries the batter scored 1.65 runs per ball against 1.55 expected for the same match situations; dismissal rate 0.048 against 0.060 expected. Normal-play baseline +0.083, pressure level +0.066, difference -0.018. The pressure level is below the normal-play baseline: the rank reflects performance above expectation in pressure situations, not an improvement over the player's normal play. Evidence: 70 pressure innings and 1130 pressure deliveries in 99 matches. Top-10 inclusion 23%, 95% rank interval 2 to 123, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1130 pressure deliveries in 70 innings: phases (powerplay 7, middle 680, death 443), innings 1 598 and innings 2 532; mean intensity 0.56.
- **Actual performance against expectation.** Observed 1.65 runs per ball against 1.55 expected; dismissal rate 0.048 against 0.060.
- **Baseline and difference.** Normal-play baseline 0.083, pressure level (unshrunk) 0.066, difference -0.018 (A-residual units per ball).
- **Score and components.** Score 0.0299 [0.0166, 0.0432] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.023, comp_dot -0.016, comp_runs 0.100, comp_wicket 0.012.
- **Consistency across matches.** 54% of pressure units beat the expectation; between-unit dispersion 0.639; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 99 matches (IPL 56, T20I 43), 1766 deliveries with a defined intensity, effective sample 1563, data weight (reliability of the estimate) 0.23. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 23%, 95% rank interval 2 to 123.
- **Rank under each approach and format.** A 9, B 42, C 4; IPL only 1, T20I only 105, combined 9 (IPL share of matches 57%; IPL score 0.0224, T20I score -0.0614).
- **Why this position.** Relative to neighbours: rank 8 (Rinku Singh) is above: score difference 0.0001957, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 10 (Mark Chapman) is below: score difference 0.0006859, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 10. Mark Chapman (player 3374)

**Why selected.** Rank 10 by context-adjusted pressure performance (+0.0292). On pressure deliveries the batter scored 1.70 runs per ball against 1.51 expected for the same match situations; dismissal rate 0.049 against 0.061 expected. Normal-play baseline -0.038, pressure level +0.103, difference +0.141. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 32 pressure innings and 503 pressure deliveries in 47 matches. Top-10 inclusion 41%, 95% rank interval 1 to 114, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 503 pressure deliveries in 32 innings: phases (powerplay 3, middle 323, death 177), innings 1 296 and innings 2 207; mean intensity 0.56.
- **Actual performance against expectation.** Observed 1.70 runs per ball against 1.51 expected; dismissal rate 0.049 against 0.061.
- **Baseline and difference.** Normal-play baseline -0.038, pressure level (unshrunk) 0.103, difference 0.141 (A-residual units per ball).
- **Score and components.** Score 0.0292 [0.0182, 0.0408] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.043, comp_dot 0.026, comp_runs 0.191, comp_wicket 0.011.
- **Consistency across matches.** 53% of pressure units beat the expectation; between-unit dispersion 0.579; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 47 matches (IPL 0, T20I 47), 784 deliveries with a defined intensity, effective sample 707, data weight (reliability of the estimate) 0.12. MEETS_ALL_DECLARED_FLOORS;ONE_FORMAT_BELOW_HALF_FLOOR.
- **Stability.** Top-10 inclusion 41%, 95% rank interval 1 to 114.
- **Rank under each approach and format.** A 10, B 38, C 19; IPL only n/a, T20I only 12, combined 10 (IPL share of matches 0%; IPL score n/a, T20I score 0.0758).
- **Why this position.** Relative to neighbours: rank 9 (Nicholas Pooran) is above: score difference 0.0006859, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### Candidate pool, ranks 11 to 20

These players are not in the submitted list. Reasons come from the data; none is a statement that the player performs poorly.

- **Rank 11, Shashank Singh**: `INCONSISTENT_ACROSS_MATCHES`: 47% of 30 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0286 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0388; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 32 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 12, Dinesh Karthik**: `INCONSISTENT_ACROSS_MATCHES`: 47% of 59 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0278 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0386; the order between them is within noise.
- **Rank 13, Mahendra Singh Dhoni**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0274 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0369; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 47 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 14, Matthew Wade**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0269 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0347; the order between them is within noise.
- **Rank 15, Rovman Powell**: `INCONSISTENT_ACROSS_MATCHES`: 43% of 77 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0266 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0392; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 12% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 5 to 143).
- **Rank 16, Ruturaj Gaikwad**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0251 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0355; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 20% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 2 to 130).
- **Rank 17, Shubman Gill**: `INCONSISTENT_ACROSS_MATCHES`: 48% of 21 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0246 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0349; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 17% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 3 to 152).
- **Rank 18, Rashid Khan**: `INCONSISTENT_ACROSS_MATCHES`: 53% of 57 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0245 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0354; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 16% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 3 to 185).
- **Rank 19, Patrick Cummins**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0245 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0340; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 19% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 2 to 161).
- **Rank 20, Shreyas Iyer**: `INCONSISTENT_ACROSS_MATCHES`: 44% of 36 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0242 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0330; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 9% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 6 to 148).

### Raw-statistic standouts (death-overs strike rate, at least 60 balls)

Players at the top of a simple raw statistic, with the reason they are or are not in the list:

- **Asif Khan** (death-overs strike rate 206.1 over 66 balls): `INCONSISTENT_ACROSS_MATCHES`: 45% of 11 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0224 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0300; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 8% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 7 to 183); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 13 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Heinrich Klaasen** (death-overs strike rate 205.2 over 289 balls): `SELECTED`: also in the submitted Top 10.
- **Jacob Bethell** (death-overs strike rate 208.3 over 60 balls): `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 5% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 8 to 163); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 17 matches in T20I and 2 in the other format; the cross-format check cannot be applied to this player.
- **Liam Livingstone** (death-overs strike rate 212.1 over 265 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0239 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0326; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 5% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 8 to 151).
- **Najibullah Zadran** (death-overs strike rate 210.6 over 104 balls): `INCONSISTENT_ACROSS_MATCHES`: 42% of 19 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0234 is below the tenth-ranked score +0.0292, although the 95% interval reaches +0.0319; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 11% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 5 to 164); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 21 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Phil Salt** (death-overs strike rate 208.8 over 91 balls): `INCONSISTENT_ACROSS_MATCHES`: 41% of 17 pressure units beat the expectation; the declared INCONSISTENT rule applies; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 4% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 10 to 183).
- **Quinton de Kock** (death-overs strike rate 232.3 over 62 balls): `INCONSISTENT_ACROSS_MATCHES`: 30% of 10 pressure units beat the expectation; the declared INCONSISTENT rule applies; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 1% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 17 to 188).
- **Rilee Rossouw** (death-overs strike rate 209.5 over 63 balls): `INCONSISTENT_ACROSS_MATCHES`: 56% of 9 pressure units beat the expectation; the declared INCONSISTENT rule applies; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 1% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 14 to 153).
- **Suryakumar Yadav** (death-overs strike rate 221.3 over 348 balls): `SELECTED`: also in the submitted Top 10.
- **Tristan Stubbs** (death-overs strike rate 211.0 over 292 balls): `SELECTED`: also in the submitted Top 10.

## Bowlers: EXPLORATORY (approach C)

EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.27 below 0.5; split-half lower bound not above 0.

### 1. Matheesha Pathirana (player 8661)

**Why selected.** Rank 1 by the Pressure Response Index (+3.61, 0 is the typical eligible bowler): in 74% of 46 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.27 runs per ball against 1.48 expected for the same match situations; wicket rate 0.080 against 0.072 expected. Normal-play baseline -0.015, pressure level +0.089, difference +0.096. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 46 pressure spells and 930 pressure deliveries in 48 matches. Top-10 inclusion 86%, 95% rank interval 1 to 26, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 930 pressure deliveries in 46 spells: phases (powerplay 0, middle 351, death 579), innings 1 455 and innings 2 475; mean intensity 0.70.
- **Actual performance against expectation.** Observed 1.27 runs per ball against 1.48 expected; wicket rate 0.080 against 0.072.
- **Baseline and difference.** Normal-play baseline -0.015, pressure level (unshrunk) 0.089, difference 0.096 (A-residual units per ball).
- **Score and components.** Score 3.6132 [3.0641, 9.2850] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 3.077, z_B 0.027, z_CONS 3.613.
- **Consistency across matches.** 74% of pressure units beat the expectation; between-unit dispersion 0.270; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 48 matches (IPL 32, T20I 16), 1025 deliveries with a defined intensity, effective sample 1043, data weight (reliability of the estimate) 0.42. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 86%, 95% rank interval 1 to 26.
- **Rank under each approach and format.** A 5, B 119, C 1; IPL only 2, T20I only 12, combined 1 (IPL share of matches 67%; IPL score 3.2455, T20I score 1.6336).
- **Why this position.** Relative to neighbours: rank 2 (Kuldeep Yadav) is below: score difference 0.5861, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 2. Kuldeep Yadav (player 3644)

**Why selected.** Rank 2 by the Pressure Response Index (+3.03, 0 is the typical eligible bowler): in 67% of 64 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.11 runs per ball against 1.32 expected for the same match situations; wicket rate 0.079 against 0.052 expected. Normal-play baseline +0.024, pressure level +0.121, difference +0.089. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 64 pressure spells and 973 pressure deliveries in 72 matches. Top-10 inclusion 56%, 95% rank interval 1 to 51, evidence class INCONSISTENT. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 973 pressure deliveries in 64 spells: phases (powerplay 0, middle 728, death 245), innings 1 587 and innings 2 386; mean intensity 0.55.
- **Actual performance against expectation.** Observed 1.11 runs per ball against 1.32 expected; wicket rate 0.079 against 0.052.
- **Baseline and difference.** Normal-play baseline 0.024, pressure level (unshrunk) 0.121, difference 0.089 (A-residual units per ball).
- **Score and components.** Score 3.0271 [1.8085, 7.5369] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 4.360, z_B 0.794, z_CONS 3.027.
- **Consistency across matches.** 67% of pressure units beat the expectation; between-unit dispersion 0.305; evidence class INCONSISTENT.
- **Evidence amount.** 72 matches (IPL 53, T20I 19), 1560 deliveries with a defined intensity, effective sample 1343, data weight (reliability of the estimate) 0.50. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 56%, 95% rank interval 1 to 51.
- **Rank under each approach and format.** A 1, B 31, C 2; IPL only 4, T20I only 7, combined 2 (IPL share of matches 74%; IPL score 2.5152, T20I score 2.0115).
- **Why this position.** Relative to neighbours: rank 1 (Matheesha Pathirana) is above: score difference 0.5861, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 3 (Jasprit Bumrah) is below: score difference 0.1982, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED. The declared evidence class is INCONSISTENT (positive-unit share below 0.5, or dispersion above the cohort's 75th percentile with a positive mean), so the position rests on a few large positive units.

### 3. Jasprit Bumrah (player 2933)

**Why selected.** Rank 3 by the Pressure Response Index (+2.83, 0 is the typical eligible bowler): in 67% of 51 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.09 runs per ball against 1.46 expected for the same match situations; wicket rate 0.081 against 0.070 expected. Normal-play baseline +0.054, pressure level +0.142, difference +0.080. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 51 pressure spells and 636 pressure deliveries in 53 matches. Top-10 inclusion 56%, 95% rank interval 1 to 56, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 636 pressure deliveries in 51 spells: phases (powerplay 4, middle 217, death 415), innings 1 369 and innings 2 267; mean intensity 0.52.
- **Actual performance against expectation.** Observed 1.09 runs per ball against 1.46 expected; wicket rate 0.081 against 0.070.
- **Baseline and difference.** Normal-play baseline 0.054, pressure level (unshrunk) 0.142, difference 0.080 (A-residual units per ball).
- **Score and components.** Score 2.8289 [1.5024, 7.6972] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 4.142, z_B 0.814, z_CONS 2.829.
- **Consistency across matches.** 67% of pressure units beat the expectation; between-unit dispersion 0.294; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 53 matches (IPL 38, T20I 15), 1228 deliveries with a defined intensity, effective sample 918, data weight (reliability of the estimate) 0.44. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 56%, 95% rank interval 1 to 56.
- **Rank under each approach and format.** A 2, B 29, C 3; IPL only 3, T20I only 24, combined 3 (IPL share of matches 72%; IPL score 2.8676, T20I score 1.0007).
- **Why this position.** Relative to neighbours: rank 2 (Kuldeep Yadav) is above: score difference 0.1982, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 4 (Varun Chakravarthy) is below: score difference 0.01372, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 4. Varun Chakravarthy (player 6256)

**Why selected.** Rank 4 by the Pressure Response Index (+2.82, 0 is the typical eligible bowler): in 64% of 69 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.19 runs per ball against 1.30 expected for the same match situations; wicket rate 0.080 against 0.055 expected. Normal-play baseline +0.039, pressure level +0.093, difference +0.045. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 69 pressure spells and 999 pressure deliveries in 77 matches. Top-10 inclusion 45%, 95% rank interval 1 to 64, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 999 pressure deliveries in 69 spells: phases (powerplay 5, middle 721, death 273), innings 1 436 and innings 2 563; mean intensity 0.55.
- **Actual performance against expectation.** Observed 1.19 runs per ball against 1.30 expected; wicket rate 0.080 against 0.055.
- **Baseline and difference.** Normal-play baseline 0.039, pressure level (unshrunk) 0.093, difference 0.045 (A-residual units per ball).
- **Score and components.** Score 2.8151 [1.3280, 7.1786] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 3.320, z_B 0.708, z_CONS 2.815.
- **Consistency across matches.** 64% of pressure units beat the expectation; between-unit dispersion 0.257; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 77 matches (IPL 52, T20I 25), 1720 deliveries with a defined intensity, effective sample 1456, data weight (reliability of the estimate) 0.52. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 45%, 95% rank interval 1 to 64.
- **Rank under each approach and format.** A 3, B 39, C 4; IPL only 9, T20I only 1, combined 4 (IPL share of matches 68%; IPL score 1.2393, T20I score 2.9404).
- **Why this position.** Relative to neighbours: rank 3 (Jasprit Bumrah) is above: score difference 0.01372, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 5 (Sunil Narine) is below: score difference 0.02957, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED.

### 5. Sunil Narine (player 781)

**Why selected.** Rank 5 by the Pressure Response Index (+2.79, 0 is the typical eligible bowler): in 69% of 48 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.04 runs per ball against 1.31 expected for the same match situations; wicket rate 0.055 against 0.049 expected. Normal-play baseline +0.008, pressure level +0.103, difference +0.087. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 48 pressure spells and 713 pressure deliveries in 54 matches. Top-10 inclusion 57%, 95% rank interval 1 to 58, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 713 pressure deliveries in 48 spells: phases (powerplay 0, middle 553, death 160), innings 1 345 and innings 2 368; mean intensity 0.52.
- **Actual performance against expectation.** Observed 1.04 runs per ball against 1.31 expected; wicket rate 0.055 against 0.049.
- **Baseline and difference.** Normal-play baseline 0.008, pressure level (unshrunk) 0.103, difference 0.087 (A-residual units per ball).
- **Score and components.** Score 2.7856 [1.4815, 7.8043] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 3.132, z_B 0.914, z_CONS 2.786.
- **Consistency across matches.** 69% of pressure units beat the expectation; between-unit dispersion 0.184; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 54 matches (IPL 54, T20I 0), 1224 deliveries with a defined intensity, effective sample 1022, data weight (reliability of the estimate) 0.43. MEETS_ALL_DECLARED_FLOORS;ONE_FORMAT_BELOW_HALF_FLOOR.
- **Stability.** Top-10 inclusion 57%, 95% rank interval 1 to 58.
- **Rank under each approach and format.** A 4, B 26, C 5; IPL only 1, T20I only n/a, combined 5 (IPL share of matches 100%; IPL score 3.4104, T20I score n/a).
- **Why this position.** Relative to neighbours: rank 4 (Varun Chakravarthy) is above: score difference 0.02957, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 6 (Akeal Hosein) is below: score difference 0.02653, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 6. Akeal Hosein (player 2417)

**Why selected.** Rank 6 by the Pressure Response Index (+2.76, 0 is the typical eligible bowler): in 68% of 47 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.09 runs per ball against 1.32 expected for the same match situations; wicket rate 0.066 against 0.057 expected. Normal-play baseline -0.017, pressure level +0.083, difference +0.092. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 47 pressure spells and 486 pressure deliveries in 61 matches. Top-10 inclusion 54%, 95% rank interval 1 to 56, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 486 pressure deliveries in 47 spells: phases (powerplay 0, middle 391, death 95), innings 1 270 and innings 2 216; mean intensity 0.39.
- **Actual performance against expectation.** Observed 1.09 runs per ball against 1.32 expected; wicket rate 0.066 against 0.057.
- **Baseline and difference.** Normal-play baseline -0.017, pressure level (unshrunk) 0.083, difference 0.092 (A-residual units per ball).
- **Score and components.** Score 2.7590 [1.4790, 7.5519] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 1.976, z_B 0.228, z_CONS 2.759.
- **Consistency across matches.** 68% of pressure units beat the expectation; between-unit dispersion 0.255; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 61 matches (IPL 1, T20I 60), 1346 deliveries with a defined intensity, effective sample 939, data weight (reliability of the estimate) 0.42. MEETS_ALL_DECLARED_FLOORS;ONE_FORMAT_BELOW_HALF_FLOOR.
- **Stability.** Top-10 inclusion 54%, 95% rank interval 1 to 56.
- **Rank under each approach and format.** A 9, B 95, C 6; IPL only n/a, T20I only 2, combined 6 (IPL share of matches 2%; IPL score n/a, T20I score 2.5270).
- **Why this position.** Relative to neighbours: rank 5 (Sunil Narine) is above: score difference 0.02653, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 7 (Rashid Khan) is below: score difference 0.2698, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 7. Rashid Khan (player 4722)

**Why selected.** Rank 7 by the Pressure Response Index (+2.49, 0 is the typical eligible bowler): in 60% of 88 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.21 runs per ball against 1.30 expected for the same match situations; wicket rate 0.066 against 0.055 expected. Normal-play baseline +0.066, pressure level +0.055, difference -0.018. The pressure level is below the normal-play baseline: the rank reflects performance above expectation in pressure situations, not an improvement over the player's normal play. Evidence: 88 pressure spells and 1340 pressure deliveries in 93 matches. Top-10 inclusion 27%, 95% rank interval 2 to 75, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1340 pressure deliveries in 88 spells: phases (powerplay 8, middle 893, death 439), innings 1 684 and innings 2 656; mean intensity 0.57.
- **Actual performance against expectation.** Observed 1.21 runs per ball against 1.30 expected; wicket rate 0.066 against 0.055.
- **Baseline and difference.** Normal-play baseline 0.066, pressure level (unshrunk) 0.055, difference -0.018 (A-residual units per ball).
- **Score and components.** Score 2.4892 [0.9857, 6.2976] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 2.140, z_B 0.670, z_CONS 2.489.
- **Consistency across matches.** 60% of pressure units beat the expectation; between-unit dispersion 0.235; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 93 matches (IPL 59, T20I 34), 2157 deliveries with a defined intensity, effective sample 1846, data weight (reliability of the estimate) 0.58. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 27%, 95% rank interval 2 to 75.
- **Rank under each approach and format.** A 7, B 46, C 7; IPL only 5, T20I only 5, combined 7 (IPL share of matches 63%; IPL score 1.6551, T20I score 2.1813).
- **Why this position.** Relative to neighbours: rank 6 (Akeal Hosein) is above: score difference 0.2698, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 8 (Mohammad Nawaz) is below: score difference 0.05751, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED.

### 8. Mohammad Nawaz (player 2490)

**Why selected.** Rank 8 by the Pressure Response Index (+2.43, 0 is the typical eligible bowler): in 65% of 40 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.05 runs per ball against 1.16 expected for the same match situations; wicket rate 0.080 against 0.051 expected. Normal-play baseline +0.004, pressure level +0.088, difference +0.075. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 40 pressure spells and 467 pressure deliveries in 47 matches. Top-10 inclusion 49%, 95% rank interval 1 to 69, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 467 pressure deliveries in 40 spells: phases (powerplay 3, middle 431, death 33), innings 1 202 and innings 2 265; mean intensity 0.48.
- **Actual performance against expectation.** Observed 1.05 runs per ball against 1.16 expected; wicket rate 0.080 against 0.051.
- **Baseline and difference.** Normal-play baseline 0.004, pressure level (unshrunk) 0.088, difference 0.075 (A-residual units per ball).
- **Score and components.** Score 2.4317 [1.0627, 7.5332] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 2.037, z_B 0.989, z_CONS 2.432.
- **Consistency across matches.** 65% of pressure units beat the expectation; between-unit dispersion 0.273; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 47 matches (IPL 0, T20I 47), 914 deliveries with a defined intensity, effective sample 759, data weight (reliability of the estimate) 0.38. MEETS_ALL_DECLARED_FLOORS;ONE_FORMAT_BELOW_HALF_FLOOR.
- **Stability.** Top-10 inclusion 49%, 95% rank interval 1 to 69.
- **Rank under each approach and format.** A 8, B 23, C 8; IPL only n/a, T20I only 3, combined 8 (IPL share of matches 0%; IPL score n/a, T20I score 2.3664).
- **Why this position.** Relative to neighbours: rank 7 (Rashid Khan) is above: score difference 0.05751, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 9 (Wanindu Hasaranga) is below: score difference 0.5008, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 9. Wanindu Hasaranga (player 4900)

**Why selected.** Rank 9 by the Pressure Response Index (+1.93, 0 is the typical eligible bowler): in 59% of 70 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.31 runs per ball against 1.29 expected for the same match situations; wicket rate 0.077 against 0.053 expected. Normal-play baseline +0.042, pressure level +0.051, difference +0.001. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 70 pressure spells and 1069 pressure deliveries in 80 matches. Top-10 inclusion 14%, 95% rank interval 3 to 107, evidence class STRONG_LIMITED. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1069 pressure deliveries in 70 spells: phases (powerplay 11, middle 791, death 267), innings 1 575 and innings 2 494; mean intensity 0.55.
- **Actual performance against expectation.** Observed 1.31 runs per ball against 1.29 expected; wicket rate 0.077 against 0.053.
- **Baseline and difference.** Normal-play baseline 0.042, pressure level (unshrunk) 0.051, difference 0.001 (A-residual units per ball).
- **Score and components.** Score 1.9309 [-0.0333, 5.8102] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag OK); components: z_A 1.777, z_B 0.504, z_CONS 1.931.
- **Consistency across matches.** 59% of pressure units beat the expectation; between-unit dispersion 0.232; evidence class STRONG_LIMITED.
- **Evidence amount.** 80 matches (IPL 35, T20I 45), 1806 deliveries with a defined intensity, effective sample 1564, data weight (reliability of the estimate) 0.52. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 14%, 95% rank interval 3 to 107.
- **Rank under each approach and format.** A 13, B 61, C 9; IPL only 46, T20I only 4, combined 9 (IPL share of matches 44%; IPL score -0.0133, T20I score 2.3664).
- **Why this position.** Relative to neighbours: rank 8 (Mohammad Nawaz) is above: score difference 0.5008, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 10 (Abbas Afridi) is below: score difference 0.0372, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED.

### 10. Abbas Afridi (player 7699)

**Why selected.** Rank 10 by the Pressure Response Index (+1.89, 0 is the typical eligible bowler): in 74% of 19 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.36 runs per ball against 1.41 expected for the same match situations; wicket rate 0.120 against 0.068 expected. Normal-play baseline +0.022, pressure level +0.139, difference +0.108. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 19 pressure spells and 223 pressure deliveries in 21 matches. Top-10 inclusion 44%, 95% rank interval 1 to 81, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 223 pressure deliveries in 19 spells: phases (powerplay 0, middle 101, death 122), innings 1 144 and innings 2 79; mean intensity 0.56.
- **Actual performance against expectation.** Observed 1.36 runs per ball against 1.41 expected; wicket rate 0.120 against 0.068.
- **Baseline and difference.** Normal-play baseline 0.022, pressure level (unshrunk) 0.139, difference 0.108 (A-residual units per ball).
- **Score and components.** Score 1.8937 [0.7330, 7.6883] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 1.907, z_B -1.005, z_CONS 1.894.
- **Consistency across matches.** 74% of pressure units beat the expectation; between-unit dispersion 0.294; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 21 matches (IPL 0, T20I 21), 393 deliveries with a defined intensity, effective sample 340, data weight (reliability of the estimate) 0.23. MEETS_ALL_DECLARED_FLOORS;ONE_FORMAT_BELOW_HALF_FLOOR.
- **Stability.** Top-10 inclusion 44%, 95% rank interval 1 to 81.
- **Rank under each approach and format.** A 11, B 197, C 10; IPL only n/a, T20I only 8, combined 10 (IPL share of matches 0%; IPL score n/a, T20I score 1.9656).
- **Why this position.** Relative to neighbours: rank 9 (Wanindu Hasaranga) is above: score difference 0.0372, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### Candidate pool, ranks 11 to 20

These players are not in the submitted list. Reasons come from the data; none is a statement that the player performs poorly.

- **Rank 11, Abrar Ahmed**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.7980 is below the tenth-ranked score +1.8937, although the 95% interval reaches +7.2525; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 28 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 12, Craig Young**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.7147 is below the tenth-ranked score +1.8937, although the 95% interval reaches +7.3374; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 21 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 13, Sai Kishore**: `INCONSISTENT_ACROSS_MATCHES`: 68% of 19 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.6146 is below the tenth-ranked score +1.8937, although the 95% interval reaches +6.8523; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 25 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 14, Mark Wood**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.5919 is below the tenth-ranked score +1.8937, although the 95% interval reaches +7.3736; the order between them is within noise.
- **Rank 15, Sufiyan Muqeem**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.5691 is below the tenth-ranked score +1.8937, although the 95% interval reaches +7.2906; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 16 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 16, Harshit Rana**: `INCONSISTENT_ACROSS_MATCHES`: 62% of 29 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.5560 is below the tenth-ranked score +1.8937, although the 95% interval reaches +6.4887; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 21% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 3 to 122).
- **Rank 17, Nathan Ellis**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.4572 is below the tenth-ranked score +1.8937, although the 95% interval reaches +6.2205; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 16% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 3 to 134).
- **Rank 18, Axar Patel**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.4364 is below the tenth-ranked score +1.8937, although the 95% interval reaches +4.6103; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 4% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 9 to 129).
- **Rank 19, Khaleel Ahmed**: `INCONSISTENT_ACROSS_MATCHES`: 57% of 40 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.3759 is below the tenth-ranked score +1.8937, although the 95% interval reaches +5.7986; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 11% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 140).
- **Rank 20, Sikandar Raza**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.2579 is below the tenth-ranked score +1.8937, although the 95% interval reaches +5.5953; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 10% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 146).

### Raw-statistic standouts (death-overs economy, at least 60 balls)

Players at the top of a simple raw statistic, with the reason they are or are not in the list:

- **Abrar Ahmed** (death-overs economy 7.4 over 73 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.7980 is below the tenth-ranked score +1.8937, although the 95% interval reaches +7.2525; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 28 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Akeal Hosein** (death-overs economy 7.5 over 86 balls): `SELECTED`: also in the submitted Top 10.
- **Axar Patel** (death-overs economy 7.5 over 161 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.4364 is below the tenth-ranked score +1.8937, although the 95% interval reaches +4.6103; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 4% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 9 to 129).
- **Gareth Delany** (death-overs economy 7.5 over 72 balls): `HIGH_RAW_BUT_NEGATIVE_AFTER_CONTEXT_ADJUSTMENT`: high on the raw death-overs statistic, but at or below the model expectation once the match situation is accounted for; `INCONSISTENT_ACROSS_MATCHES`: 46% of 24 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.2199 is below the tenth-ranked score +1.8937, although the 95% interval reaches +3.7564; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 1% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 17 to 194); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 28 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Jasprit Bumrah** (death-overs economy 7.0 over 412 balls): `SELECTED`: also in the submitted Top 10.
- **Kuldeep Yadav** (death-overs economy 7.1 over 244 balls): `SELECTED`: also in the submitted Top 10.
- **Noor Ahmad** (death-overs economy 7.2 over 187 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.0422 is below the tenth-ranked score +1.8937, although the 95% interval reaches +5.1149; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 5% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 7 to 154).
- **Sikandar Raza** (death-overs economy 6.7 over 90 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.2579 is below the tenth-ranked score +1.8937, although the 95% interval reaches +5.5953; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 10% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 146).
- **Sufiyan Muqeem** (death-overs economy 6.8 over 70 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.5691 is below the tenth-ranked score +1.8937, although the 95% interval reaches +7.2906; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 16 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Sunil Narine** (death-overs economy 6.1 over 162 balls): `SELECTED`: also in the submitted Top 10.

