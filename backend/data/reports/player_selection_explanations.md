# Player selection explanations

> **Batters: EXPLORATORY.** EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.02 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0.

> **Bowlers: EXPLORATORY.** EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.32 below 0.5; split-half lower bound not above 0.

Each section explains why a player is in the submitted Top 10, what the numbers are, how much evidence stands behind them and how firmly the position is supported. Every figure is read from `p9_rankings` (the same table as the CSV and JSON files). The pressure situation is the P4 resource-scarcity definition, which did not pass the predeclared validity tests. Each row carries the label of its list (see the banners); no row is labelled stronger than its list.

## Batters: EXPLORATORY (approach A)

EXPLORATORY ranking of batters: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: REML_POSTERIOR. Reason: split-half 0.02 below 0.5; split-half lower bound not above 0; out-of-time lower bound not above 0.

### 1. Suryakumar Yadav (player 1699)

**Why selected.** Rank 1 by context-adjusted pressure performance (+0.0345). On pressure deliveries the batter scored 1.85 runs per ball against 1.61 expected for the same match situations; dismissal rate 0.049 against 0.060 expected. Normal-play baseline +0.062, pressure level +0.106, difference +0.044. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 79 pressure innings and 1369 pressure deliveries in 135 matches. Top-10 inclusion 88%, 95% rank interval 1 to 22, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1369 pressure deliveries in 79 innings: phases (powerplay 6, middle 988, death 375), innings 1 612 and innings 2 757; mean intensity 0.50.
- **Actual performance against expectation.** Observed 1.85 runs per ball against 1.61 expected; dismissal rate 0.049 against 0.060.
- **Baseline and difference.** Normal-play baseline 0.062, pressure level (unshrunk) 0.106, difference 0.044 (A-residual units per ball).
- **Score and components.** Score 0.0345 [0.0244, 0.0455] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.066, comp_dot 0.000, comp_runs 0.245, comp_wicket 0.011.
- **Consistency across matches.** 54% of pressure units beat the expectation; between-unit dispersion 0.495; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 135 matches (IPL 63, T20I 72), 2715 deliveries with a defined intensity, effective sample 2399, data weight (reliability of the estimate) 0.20. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 88%, 95% rank interval 1 to 22.
- **Rank under each approach and format.** A 1, B 55, C 12; IPL only 7, T20I only 3, combined 1 (IPL share of matches 47%; IPL score 0.0040, T20I score 0.1296).
- **Why this position.** Relative to neighbours: rank 2 (Tim David) is below: score difference 0.001944, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 2. Tim David (player 6396)

**Why selected.** Rank 2 by context-adjusted pressure performance (+0.0326). On pressure deliveries the batter scored 1.77 runs per ball against 1.56 expected for the same match situations; dismissal rate 0.053 against 0.068 expected. Normal-play baseline +0.223, pressure level +0.109, difference -0.114. The pressure level is below the normal-play baseline: the rank reflects performance above expectation in pressure situations, not an improvement over the player's normal play. Evidence: 91 pressure innings and 1146 pressure deliveries in 94 matches. Top-10 inclusion 87%, 95% rank interval 1 to 30, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1146 pressure deliveries in 91 innings: phases (powerplay 0, middle 528, death 618), innings 1 604 and innings 2 542; mean intensity 0.75.
- **Actual performance against expectation.** Observed 1.77 runs per ball against 1.56 expected; dismissal rate 0.053 against 0.068.
- **Baseline and difference.** Normal-play baseline 0.223, pressure level (unshrunk) 0.109, difference -0.114 (A-residual units per ball).
- **Score and components.** Score 0.0326 [0.0226, 0.0425] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.044, comp_dot 0.010, comp_runs 0.214, comp_wicket 0.015.
- **Consistency across matches.** 56% of pressure units beat the expectation; between-unit dispersion 0.648; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 94 matches (IPL 56, T20I 38), 1167 deliveries with a defined intensity, effective sample 1123, data weight (reliability of the estimate) 0.17. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 87%, 95% rank interval 1 to 30.
- **Rank under each approach and format.** A 2, B 5, C 1; IPL only 2, T20I only 8, combined 2 (IPL share of matches 60%; IPL score 0.0046, T20I score 0.0978).
- **Why this position.** Relative to neighbours: rank 1 (Suryakumar Yadav) is above: score difference 0.001944, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 3 (Heinrich Klaasen) is below: score difference 0.004882, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 3. Heinrich Klaasen (player 4260)

**Why selected.** Rank 3 by context-adjusted pressure performance (+0.0277). On pressure deliveries the batter scored 1.74 runs per ball against 1.60 expected for the same match situations; dismissal rate 0.048 against 0.059 expected. Normal-play baseline +0.075, pressure level +0.078, difference +0.003. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 62 pressure innings and 1181 pressure deliveries in 70 matches. Top-10 inclusion 51%, 95% rank interval 2 to 51, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1181 pressure deliveries in 62 innings: phases (powerplay 14, middle 759, death 408), innings 1 712 and innings 2 469; mean intensity 0.64.
- **Actual performance against expectation.** Observed 1.74 runs per ball against 1.60 expected; dismissal rate 0.048 against 0.059.
- **Baseline and difference.** Normal-play baseline 0.075, pressure level (unshrunk) 0.078, difference 0.003 (A-residual units per ball).
- **Score and components.** Score 0.0277 [0.0205, 0.0360] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.011, comp_dot 0.064, comp_runs 0.137, comp_wicket 0.011.
- **Consistency across matches.** 61% of pressure units beat the expectation; between-unit dispersion 0.421; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 70 matches (IPL 54, T20I 16), 1408 deliveries with a defined intensity, effective sample 1333, data weight (reliability of the estimate) 0.17. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 51%, 95% rank interval 2 to 51.
- **Rank under each approach and format.** A 3, B 27, C 3; IPL only 1, T20I only 16, combined 3 (IPL share of matches 77%; IPL score 0.0048, T20I score 0.0806).
- **Why this position.** Relative to neighbours: rank 2 (Tim David) is above: score difference 0.004882, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 4 (David Miller) is below: score difference 0.001185, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 4. David Miller (player 1077)

**Why selected.** Rank 4 by context-adjusted pressure performance (+0.0265). On pressure deliveries the batter scored 1.56 runs per ball against 1.53 expected for the same match situations; dismissal rate 0.039 against 0.064 expected. Normal-play baseline -0.064, pressure level +0.070, difference +0.134. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 75 pressure innings and 1210 pressure deliveries in 79 matches. Top-10 inclusion 38%, 95% rank interval 2 to 96, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1210 pressure deliveries in 75 innings: phases (powerplay 11, middle 675, death 524), innings 1 463 and innings 2 747; mean intensity 0.69.
- **Actual performance against expectation.** Observed 1.56 runs per ball against 1.53 expected; dismissal rate 0.039 against 0.064.
- **Baseline and difference.** Normal-play baseline -0.064, pressure level (unshrunk) 0.070, difference 0.134 (A-residual units per ball).
- **Score and components.** Score 0.0265 [0.0172, 0.0370] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary -0.004, comp_dot 0.028, comp_runs 0.025, comp_wicket 0.024.
- **Consistency across matches.** 52% of pressure units beat the expectation; between-unit dispersion 0.457; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 79 matches (IPL 58, T20I 21), 1243 deliveries with a defined intensity, effective sample 1203, data weight (reliability of the estimate) 0.18. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 38%, 95% rank interval 2 to 96.
- **Rank under each approach and format.** A 4, B 37, C 15; IPL only 8, T20I only 20, combined 4 (IPL share of matches 73%; IPL score 0.0038, T20I score 0.0780).
- **Why this position.** Relative to neighbours: rank 3 (Heinrich Klaasen) is above: score difference 0.001185, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 5 (Rinku Singh) is below: score difference 2.869e-05, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 5. Rinku Singh (player 4708)

**Why selected.** Rank 5 by context-adjusted pressure performance (+0.0265). On pressure deliveries the batter scored 1.60 runs per ball against 1.56 expected for the same match situations; dismissal rate 0.042 against 0.066 expected. Normal-play baseline +0.031, pressure level +0.069, difference +0.038. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 79 pressure innings and 1242 pressure deliveries in 83 matches. Top-10 inclusion 38%, 95% rank interval 2 to 107, evidence class INCONSISTENT. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1242 pressure deliveries in 79 innings: phases (powerplay 5, middle 595, death 642), innings 1 799 and innings 2 443; mean intensity 0.74.
- **Actual performance against expectation.** Observed 1.60 runs per ball against 1.56 expected; dismissal rate 0.042 against 0.066.
- **Baseline and difference.** Normal-play baseline 0.031, pressure level (unshrunk) 0.069, difference 0.038 (A-residual units per ball).
- **Score and components.** Score 0.0265 [0.0166, 0.0364] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.009, comp_dot 0.020, comp_runs 0.035, comp_wicket 0.024.
- **Consistency across matches.** 48% of pressure units beat the expectation; between-unit dispersion 0.451; evidence class INCONSISTENT.
- **Evidence amount.** 83 matches (IPL 54, T20I 29), 1280 deliveries with a defined intensity, effective sample 1225, data weight (reliability of the estimate) 0.18. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 38%, 95% rank interval 2 to 107.
- **Rank under each approach and format.** A 5, B 25, C 26; IPL only 12, T20I only 15, combined 5 (IPL share of matches 65%; IPL score 0.0035, T20I score 0.0822).
- **Why this position.** Relative to neighbours: rank 4 (David Miller) is above: score difference 2.869e-05, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 6 (Andre Russell) is below: score difference 0.0001817, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5. The declared evidence class is INCONSISTENT (positive-unit share below 0.5, or dispersion above the cohort's 75th percentile with a positive mean), so the position rests on a few large positive units.

### 6. Andre Russell (player 1318)

**Why selected.** Rank 6 by context-adjusted pressure performance (+0.0263). On pressure deliveries the batter scored 1.72 runs per ball against 1.47 expected for the same match situations; dismissal rate 0.061 against 0.065 expected. Evidence: 57 pressure innings and 785 pressure deliveries in 57 matches. Top-10 inclusion 51%, 95% rank interval 1 to 92, evidence class INCONSISTENT. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 785 pressure deliveries in 57 innings: phases (powerplay 0, middle 413, death 372), innings 1 484 and innings 2 301; mean intensity 0.81.
- **Actual performance against expectation.** Observed 1.72 runs per ball against 1.47 expected; dismissal rate 0.061 against 0.065.
- **Baseline and difference.** Normal-play baseline n/a, pressure level (unshrunk) 0.093, difference n/a (A-residual units per ball).
- **Score and components.** Score 0.0263 [0.0174, 0.0359] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.076, comp_dot -0.070, comp_runs 0.248, comp_wicket 0.004.
- **Consistency across matches.** 49% of pressure units beat the expectation; between-unit dispersion 0.682; evidence class INCONSISTENT.
- **Evidence amount.** 57 matches (IPL 45, T20I 12), 732 deliveries with a defined intensity, effective sample 717, data weight (reliability of the estimate) 0.12. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 51%, 95% rank interval 1 to 92.
- **Rank under each approach and format.** A 6, B 105, C 41; IPL only 10, T20I only 2, combined 6 (IPL share of matches 79%; IPL score 0.0036, T20I score 0.1366).
- **Why this position.** Relative to neighbours: rank 5 (Rinku Singh) is above: score difference 0.0001817, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 7 (Romario Shepherd) is below: score difference 0.0001581, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5. The declared evidence class is INCONSISTENT (positive-unit share below 0.5, or dispersion above the cohort's 75th percentile with a positive mean), so the position rests on a few large positive units.

### 7. Romario Shepherd (player 6726)

**Why selected.** Rank 7 by context-adjusted pressure performance (+0.0261). On pressure deliveries the batter scored 1.57 runs per ball against 1.44 expected for the same match situations; dismissal rate 0.059 against 0.080 expected. Normal-play baseline -0.330, pressure level +0.099, difference +0.429. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 64 pressure innings and 696 pressure deliveries in 65 matches. Top-10 inclusion 54%, 95% rank interval 1 to 67, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 696 pressure deliveries in 64 innings: phases (powerplay 1, middle 282, death 413), innings 1 368 and innings 2 328; mean intensity 0.87.
- **Actual performance against expectation.** Observed 1.57 runs per ball against 1.44 expected; dismissal rate 0.059 against 0.080.
- **Baseline and difference.** Normal-play baseline -0.330, pressure level (unshrunk) 0.099, difference 0.429 (A-residual units per ball).
- **Score and components.** Score 0.0261 [0.0186, 0.0344] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.036, comp_dot -0.005, comp_runs 0.139, comp_wicket 0.022.
- **Consistency across matches.** 61% of pressure units beat the expectation; between-unit dispersion 0.719; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 65 matches (IPL 18, T20I 47), 663 deliveries with a defined intensity, effective sample 655, data weight (reliability of the estimate) 0.11. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 54%, 95% rank interval 1 to 67.
- **Rank under each approach and format.** A 7, B 112, C 7; IPL only 24, T20I only 12, combined 7 (IPL share of matches 28%; IPL score 0.0023, T20I score 0.0863).
- **Why this position.** Relative to neighbours: rank 6 (Andre Russell) is above: score difference 0.0001581, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 8 (Tristan Stubbs) is below: score difference 0.0005534, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 8. Tristan Stubbs (player 20702)

**Why selected.** Rank 8 by context-adjusted pressure performance (+0.0256). On pressure deliveries the batter scored 1.59 runs per ball against 1.52 expected for the same match situations; dismissal rate 0.039 against 0.061 expected. Normal-play baseline -0.099, pressure level +0.075, difference +0.174. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 58 pressure innings and 956 pressure deliveries in 65 matches. Top-10 inclusion 38%, 95% rank interval 2 to 84, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 956 pressure deliveries in 58 innings: phases (powerplay 14, middle 560, death 382), innings 1 449 and innings 2 507; mean intensity 0.69.
- **Actual performance against expectation.** Observed 1.59 runs per ball against 1.52 expected; dismissal rate 0.039 against 0.061.
- **Baseline and difference.** Normal-play baseline -0.099, pressure level (unshrunk) 0.075, difference 0.174 (A-residual units per ball).
- **Score and components.** Score 0.0256 [0.0179, 0.0340] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary -0.001, comp_dot 0.072, comp_runs 0.062, comp_wicket 0.022.
- **Consistency across matches.** 59% of pressure units beat the expectation; between-unit dispersion 0.458; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 65 matches (IPL 43, T20I 22), 1040 deliveries with a defined intensity, effective sample 988, data weight (reliability of the estimate) 0.15. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 38%, 95% rank interval 2 to 84.
- **Rank under each approach and format.** A 8, B 63, C 8; IPL only 5, T20I only 45, combined 8 (IPL share of matches 66%; IPL score 0.0040, T20I score 0.0389).
- **Why this position.** Relative to neighbours: rank 7 (Romario Shepherd) is above: score difference 0.0005534, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 9 (Shreyas Iyer) is below: score difference 0.0008119, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 9. Shreyas Iyer (player 3647)

**Why selected.** Rank 9 by context-adjusted pressure performance (+0.0248). On pressure deliveries the batter scored 1.78 runs per ball against 1.66 expected for the same match situations; dismissal rate 0.047 against 0.058 expected. Normal-play baseline +0.010, pressure level +0.069, difference +0.059. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 61 pressure innings and 975 pressure deliveries in 94 matches. Top-10 inclusion 30%, 95% rank interval 2 to 125, evidence class INCONSISTENT. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 975 pressure deliveries in 61 innings: phases (powerplay 0, middle 654, death 321), innings 1 513 and innings 2 462; mean intensity 0.51.
- **Actual performance against expectation.** Observed 1.78 runs per ball against 1.66 expected; dismissal rate 0.047 against 0.058.
- **Baseline and difference.** Normal-play baseline 0.010, pressure level (unshrunk) 0.069, difference 0.059 (A-residual units per ball).
- **Score and components.** Score 0.0248 [0.0161, 0.0342] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.013, comp_dot 0.043, comp_runs 0.124, comp_wicket 0.011.
- **Consistency across matches.** 44% of pressure units beat the expectation; between-unit dispersion 0.296; evidence class INCONSISTENT.
- **Evidence amount.** 94 matches (IPL 57, T20I 37), 1827 deliveries with a defined intensity, effective sample 1601, data weight (reliability of the estimate) 0.15. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 30%, 95% rank interval 2 to 125.
- **Rank under each approach and format.** A 9, B 11, C 28; IPL only 4, T20I only 86, combined 9 (IPL share of matches 61%; IPL score 0.0044, T20I score -0.0018).
- **Why this position.** Relative to neighbours: rank 8 (Tristan Stubbs) is above: score difference 0.0008119, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 10 (Shivam Dube) is below: score difference 0.001008, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5. The declared evidence class is INCONSISTENT (positive-unit share below 0.5, or dispersion above the cohort's 75th percentile with a positive mean), so the position rests on a few large positive units.

### 10. Shivam Dube (player 4755)

**Why selected.** Rank 10 by context-adjusted pressure performance (+0.0238). On pressure deliveries the batter scored 1.55 runs per ball against 1.51 expected for the same match situations; dismissal rate 0.047 against 0.060 expected. Normal-play baseline +0.063, pressure level +0.052, difference -0.011. The pressure level is below the normal-play baseline: the rank reflects performance above expectation in pressure situations, not an improvement over the player's normal play. Evidence: 83 pressure innings and 1343 pressure deliveries in 96 matches. Top-10 inclusion 16%, 95% rank interval 4 to 116, evidence class INCONSISTENT. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1343 pressure deliveries in 83 innings: phases (powerplay 10, middle 829, death 504), innings 1 760 and innings 2 583; mean intensity 0.67.
- **Actual performance against expectation.** Observed 1.55 runs per ball against 1.51 expected; dismissal rate 0.047 against 0.060.
- **Baseline and difference.** Normal-play baseline 0.063, pressure level (unshrunk) 0.052, difference -0.011 (A-residual units per ball).
- **Score and components.** Score 0.0238 [0.0158, 0.0325] (standardised residual per delivery (REML posterior); interval flag OK); components: comp_boundary 0.009, comp_dot 0.008, comp_runs 0.045, comp_wicket 0.013.
- **Consistency across matches.** 48% of pressure units beat the expectation; between-unit dispersion 0.435; evidence class INCONSISTENT.
- **Evidence amount.** 96 matches (IPL 64, T20I 32), 1520 deliveries with a defined intensity, effective sample 1439, data weight (reliability of the estimate) 0.19. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 16%, 95% rank interval 4 to 116.
- **Rank under each approach and format.** A 10, B 118, C 45; IPL only 20, T20I only 14, combined 10 (IPL share of matches 67%; IPL score 0.0026, T20I score 0.0825).
- **Why this position.** Relative to neighbours: rank 9 (Shreyas Iyer) is above: score difference 0.001008, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5. The declared evidence class is INCONSISTENT (positive-unit share below 0.5, or dispersion above the cohort's 75th percentile with a positive mean), so the position rests on a few large positive units.

### Candidate pool, ranks 11 to 20

These players are not in the submitted list. Reasons come from the data; none is a statement that the player performs poorly.

- **Rank 11, Dinesh Karthik**: `INCONSISTENT_ACROSS_MATCHES`: 47% of 59 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0234 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0316; the order between them is within noise.
- **Rank 12, Shashank Singh**: `INCONSISTENT_ACROSS_MATCHES`: 49% of 39 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0234 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0317; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 41 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 13, Mark Chapman**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0234 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0313; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 51 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 14, Glenn Phillips**: `INCONSISTENT_ACROSS_MATCHES`: 48% of 46 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0229 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0297; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 20% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 134).
- **Rank 15, Mahendra Singh Dhoni**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0227 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0295; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 47 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 16, Rovman Powell**: `INCONSISTENT_ACROSS_MATCHES`: 48% of 89 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0226 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0320; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 11% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 5 to 152).
- **Rank 17, Ashutosh Sharma**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0222 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0291; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 24% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 2 to 127); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 26 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 18, Nicholas Pooran**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0221 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0326; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 10% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 184).
- **Rank 19, Matthew Wade**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0220 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0274; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 24% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 3 to 114).
- **Rank 20, Namboori Tilak Varma**: `INCONSISTENT_ACROSS_MATCHES`: 49% of 98 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0218 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0318; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 6% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 7 to 169).

### Raw-statistic standouts (death-overs strike rate, at least 60 balls)

Players at the top of a simple raw statistic, with the reason they are or are not in the list:

- **Jacob Bethell** (death-overs strike rate 221.6 over 74 balls): `INCONSISTENT_ACROSS_MATCHES`: 47% of 15 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0193 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0251; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 8% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 6 to 208).
- **Liam Livingstone** (death-overs strike rate 208.5 over 270 balls): `INCONSISTENT_ACROSS_MATCHES`: 47% of 55 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0201 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0268; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 3% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 10 to 181).
- **Najibullah Zadran** (death-overs strike rate 210.6 over 104 balls): `INCONSISTENT_ACROSS_MATCHES`: 47% of 19 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0195 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0252; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 7% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 6 to 189); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 21 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Phil Salt** (death-overs strike rate 208.4 over 95 balls): `INCONSISTENT_ACROSS_MATCHES`: 44% of 18 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0188 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0238; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 3% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 10 to 206).
- **Quinton de Kock** (death-overs strike rate 232.0 over 75 balls): `INCONSISTENT_ACROSS_MATCHES`: 36% of 11 pressure units beat the expectation; the declared INCONSISTENT rule applies; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 2% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 12 to 204).
- **Rajat Patidar** (death-overs strike rate 215.3 over 124 balls): `INCONSISTENT_ACROSS_MATCHES`: 28% of 32 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.0179 is below the tenth-ranked score +0.0238, although the 95% interval reaches +0.0255; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 4% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 7 to 244); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 46 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rilee Rossouw** (death-overs strike rate 209.5 over 63 balls): `INCONSISTENT_ACROSS_MATCHES`: 56% of 9 pressure units beat the expectation; the declared INCONSISTENT rule applies; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 1% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 15 to 175).
- **Sai Sudharsan** (death-overs strike rate 206.7 over 149 balls): `INCONSISTENT_ACROSS_MATCHES`: 38% of 21 pressure units beat the expectation; the declared INCONSISTENT rule applies; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 0% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 28 to 233); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 56 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Suryakumar Yadav** (death-overs strike rate 217.2 over 361 balls): `SELECTED`: also in the submitted Top 10.
- **William Jacks** (death-overs strike rate 216.4 over 61 balls): `HIGH_RAW_BUT_NEGATIVE_AFTER_CONTEXT_ADJUSTMENT`: high on the raw death-overs statistic, but at or below the model expectation once the match situation is accounted for; `INCONSISTENT_ACROSS_MATCHES`: 35% of 23 pressure units beat the expectation; the declared INCONSISTENT rule applies; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 0% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 140 to 256).

## Bowlers: EXPLORATORY (approach C)

EXPLORATORY ranking of bowlers: this is the best-supported ordering of the available data, not a validated ranking. The order is not shown to separate players beyond noise. Ranking basis: PRI_REML_POSTERIOR_COMPONENTS. Reason: split-half 0.32 below 0.5; split-half lower bound not above 0.

### 1. Sunil Narine (player 781)

**Why selected.** Rank 1 by the Pressure Response Index (+3.65, 0 is the typical eligible bowler): in 74% of 61 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.01 runs per ball against 1.33 expected for the same match situations; wicket rate 0.059 against 0.050 expected. Normal-play baseline +0.012, pressure level +0.119, difference +0.097. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 61 pressure spells and 849 pressure deliveries in 67 matches. Top-10 inclusion 98%, 95% rank interval 1 to 10, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 849 pressure deliveries in 61 spells: phases (powerplay 0, middle 637, death 212), innings 1 430 and innings 2 419; mean intensity 0.51.
- **Actual performance against expectation.** Observed 1.01 runs per ball against 1.33 expected; wicket rate 0.059 against 0.050.
- **Baseline and difference.** Normal-play baseline 0.012, pressure level (unshrunk) 0.119, difference 0.097 (A-residual units per ball).
- **Score and components.** Score 3.6470 [3.4355, 7.9420] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 3.588, z_B 1.758, z_CONS 3.706.
- **Consistency across matches.** 74% of pressure units beat the expectation; between-unit dispersion 0.190; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 67 matches (IPL 67, T20I 0), 1530 deliveries with a defined intensity, effective sample 1257, data weight (reliability of the estimate) 0.46. MEETS_ALL_DECLARED_FLOORS;ONE_FORMAT_BELOW_HALF_FLOOR.
- **Stability.** Top-10 inclusion 98%, 95% rank interval 1 to 10.
- **Rank under each approach and format.** A 1, B 5, C 1; IPL only 1, T20I only n/a, combined 1 (IPL share of matches 100%; IPL score 3.8543, T20I score n/a).
- **Why this position.** Relative to neighbours: rank 2 (Matheesha Pathirana) is below: score difference 0.7285, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 2. Matheesha Pathirana (player 8661)

**Why selected.** Rank 2 by the Pressure Response Index (+2.92, 0 is the typical eligible bowler): in 73% of 48 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.26 runs per ball against 1.47 expected for the same match situations; wicket rate 0.079 against 0.071 expected. Normal-play baseline +0.012, pressure level +0.088, difference +0.066. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 48 pressure spells and 958 pressure deliveries in 51 matches. Top-10 inclusion 86%, 95% rank interval 1 to 22, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 958 pressure deliveries in 48 spells: phases (powerplay 2, middle 370, death 586), innings 1 470 and innings 2 488; mean intensity 0.70.
- **Actual performance against expectation.** Observed 1.26 runs per ball against 1.47 expected; wicket rate 0.079 against 0.071.
- **Baseline and difference.** Normal-play baseline 0.012, pressure level (unshrunk) 0.088, difference 0.066 (A-residual units per ball).
- **Score and components.** Score 2.9185 [2.2140, 7.0689] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 2.743, z_B 0.445, z_CONS 3.094.
- **Consistency across matches.** 73% of pressure units beat the expectation; between-unit dispersion 0.271; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 51 matches (IPL 33, T20I 18), 1075 deliveries with a defined intensity, effective sample 1083, data weight (reliability of the estimate) 0.44. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 86%, 95% rank interval 1 to 22.
- **Rank under each approach and format.** A 5, B 48, C 2; IPL only 3, T20I only n/a, combined 2 (IPL share of matches 65%; IPL score 2.5051, T20I score n/a).
- **Why this position.** Relative to neighbours: rank 1 (Sunil Narine) is above: score difference 0.7285, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 3 (Kuldeep Yadav) is below: score difference 0.2409, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 3. Kuldeep Yadav (player 3644)

**Why selected.** Rank 3 by the Pressure Response Index (+2.68, 0 is the typical eligible bowler): in 63% of 78 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.22 runs per ball against 1.34 expected for the same match situations; wicket rate 0.075 against 0.053 expected. Normal-play baseline +0.018, pressure level +0.084, difference +0.056. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 78 pressure spells and 1173 pressure deliveries in 88 matches. Top-10 inclusion 64%, 95% rank interval 1 to 41, evidence class INCONSISTENT. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1173 pressure deliveries in 78 spells: phases (powerplay 0, middle 882, death 291), innings 1 705 and innings 2 468; mean intensity 0.55.
- **Actual performance against expectation.** Observed 1.22 runs per ball against 1.34 expected; wicket rate 0.075 against 0.053.
- **Baseline and difference.** Normal-play baseline 0.018, pressure level (unshrunk) 0.084, difference 0.056 (A-residual units per ball).
- **Score and components.** Score 2.6776 [1.3149, 6.5073] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 2.896, z_B 0.616, z_CONS 2.460.
- **Consistency across matches.** 63% of pressure units beat the expectation; between-unit dispersion 0.311; evidence class INCONSISTENT.
- **Evidence amount.** 88 matches (IPL 64, T20I 24), 1896 deliveries with a defined intensity, effective sample 1649, data weight (reliability of the estimate) 0.53. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 64%, 95% rank interval 1 to 41.
- **Rank under each approach and format.** A 2, B 38, C 3; IPL only 5, T20I only 2, combined 3 (IPL share of matches 73%; IPL score 1.6511, T20I score 2.2384).
- **Why this position.** Relative to neighbours: rank 2 (Matheesha Pathirana) is above: score difference 0.2409, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 4 (Jasprit Bumrah) is below: score difference 0.01427, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED. The declared evidence class is INCONSISTENT (positive-unit share below 0.5, or dispersion above the cohort's 75th percentile with a positive mean), so the position rests on a few large positive units.

### 4. Jasprit Bumrah (player 2933)

**Why selected.** Rank 4 by the Pressure Response Index (+2.66, 0 is the typical eligible bowler): in 64% of 69 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.15 runs per ball against 1.48 expected for the same match situations; wicket rate 0.067 against 0.071 expected. Normal-play baseline +0.049, pressure level +0.096, difference +0.037. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 69 pressure spells and 866 pressure deliveries in 72 matches. Top-10 inclusion 70%, 95% rank interval 1 to 35, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 866 pressure deliveries in 69 spells: phases (powerplay 4, middle 308, death 554), innings 1 498 and innings 2 368; mean intensity 0.51.
- **Actual performance against expectation.** Observed 1.15 runs per ball against 1.48 expected; wicket rate 0.067 against 0.071.
- **Baseline and difference.** Normal-play baseline 0.049, pressure level (unshrunk) 0.096, difference 0.037 (A-residual units per ball).
- **Score and components.** Score 2.6634 [1.5215, 6.7617] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 2.873, z_B 0.901, z_CONS 2.454.
- **Consistency across matches.** 64% of pressure units beat the expectation; between-unit dispersion 0.285; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 72 matches (IPL 50, T20I 22), 1654 deliveries with a defined intensity, effective sample 1242, data weight (reliability of the estimate) 0.48. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 70%, 95% rank interval 1 to 35.
- **Rank under each approach and format.** A 3, B 23, C 4; IPL only 2, T20I only 22, combined 4 (IPL share of matches 69%; IPL score 2.6969, T20I score 0.6305).
- **Why this position.** Relative to neighbours: rank 3 (Kuldeep Yadav) is above: score difference 0.01427, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 5 (Varun Chakravarthy) is below: score difference 0.2581, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 5. Varun Chakravarthy (player 6256)

**Why selected.** Rank 5 by the Pressure Response Index (+2.41, 0 is the typical eligible bowler): in 60% of 85 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.20 runs per ball against 1.32 expected for the same match situations; wicket rate 0.075 against 0.056 expected. Normal-play baseline +0.024, pressure level +0.078, difference +0.044. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 85 pressure spells and 1224 pressure deliveries in 95 matches. Top-10 inclusion 51%, 95% rank interval 2 to 47, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1224 pressure deliveries in 85 spells: phases (powerplay 5, middle 907, death 312), innings 1 569 and innings 2 655; mean intensity 0.54.
- **Actual performance against expectation.** Observed 1.20 runs per ball against 1.32 expected; wicket rate 0.075 against 0.056.
- **Baseline and difference.** Normal-play baseline 0.024, pressure level (unshrunk) 0.078, difference 0.044 (A-residual units per ball).
- **Score and components.** Score 2.4053 [0.9899, 5.8373] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 2.720, z_B 2.213, z_CONS 2.091.
- **Consistency across matches.** 60% of pressure units beat the expectation; between-unit dispersion 0.254; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 95 matches (IPL 63, T20I 32), 2128 deliveries with a defined intensity, effective sample 1815, data weight (reliability of the estimate) 0.55. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 51%, 95% rank interval 2 to 47.
- **Rank under each approach and format.** A 4, B 4, C 5; IPL only 4, T20I only 5, combined 5 (IPL share of matches 66%; IPL score 1.6521, T20I score 1.7379).
- **Why this position.** Relative to neighbours: rank 4 (Jasprit Bumrah) is above: score difference 0.2581, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 6 (Abrar Ahmed) is below: score difference 0.5647, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED.

### 6. Abrar Ahmed (player 5979)

**Why selected.** Rank 6 by the Pressure Response Index (+1.84, 0 is the typical eligible bowler): in 62% of 34 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 0.92 runs per ball against 1.19 expected for the same match situations; wicket rate 0.075 against 0.062 expected. Normal-play baseline -0.013, pressure level +0.117, difference +0.118. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 34 pressure spells and 447 pressure deliveries in 35 matches. Top-10 inclusion 48%, 95% rank interval 1 to 53, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 447 pressure deliveries in 34 spells: phases (powerplay 0, middle 334, death 113), innings 1 216 and innings 2 231; mean intensity 0.57.
- **Actual performance against expectation.** Observed 0.92 runs per ball against 1.19 expected; wicket rate 0.075 against 0.062.
- **Baseline and difference.** Normal-play baseline -0.013, pressure level (unshrunk) 0.117, difference 0.118 (A-residual units per ball).
- **Score and components.** Score 1.8407 [0.6667, 6.2021] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 2.324, z_B 0.667, z_CONS 1.357.
- **Consistency across matches.** 62% of pressure units beat the expectation; between-unit dispersion 0.245; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 35 matches (IPL 0, T20I 35), 764 deliveries with a defined intensity, effective sample 634, data weight (reliability of the estimate) 0.32. MEETS_ALL_DECLARED_FLOORS;ONE_FORMAT_BELOW_HALF_FLOOR.
- **Stability.** Top-10 inclusion 48%, 95% rank interval 1 to 53.
- **Rank under each approach and format.** A 6, B 37, C 6; IPL only n/a, T20I only 4, combined 6 (IPL share of matches 0%; IPL score n/a, T20I score 1.9021).
- **Why this position.** Relative to neighbours: rank 5 (Varun Chakravarthy) is above: score difference 0.5647, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 7 (Rashid Khan) is below: score difference 0.0771, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 7. Rashid Khan (player 4722)

**Why selected.** Rank 7 by the Pressure Response Index (+1.76, 0 is the typical eligible bowler): in 57% of 114 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.25 runs per ball against 1.32 expected for the same match situations; wicket rate 0.065 against 0.057 expected. Normal-play baseline +0.071, pressure level +0.046, difference -0.035. The pressure level is below the normal-play baseline: the rank reflects performance above expectation in pressure situations, not an improvement over the player's normal play. Evidence: 114 pressure spells and 1707 pressure deliveries in 119 matches. Top-10 inclusion 17%, 95% rank interval 5 to 66, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1707 pressure deliveries in 114 spells: phases (powerplay 8, middle 1181, death 518), innings 1 881 and innings 2 826; mean intensity 0.57.
- **Actual performance against expectation.** Observed 1.25 runs per ball against 1.32 expected; wicket rate 0.065 against 0.057.
- **Baseline and difference.** Normal-play baseline 0.071, pressure level (unshrunk) 0.046, difference -0.035 (A-residual units per ball).
- **Score and components.** Score 1.7636 [0.3329, 4.3898] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag OK); components: z_A 1.706, z_B 3.443, z_CONS 1.821.
- **Consistency across matches.** 57% of pressure units beat the expectation; between-unit dispersion 0.256; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 119 matches (IPL 76, T20I 43), 2699 deliveries with a defined intensity, effective sample 2324, data weight (reliability of the estimate) 0.62. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 17%, 95% rank interval 5 to 66.
- **Rank under each approach and format.** A 7, B 1, C 7; IPL only 28, T20I only 1, combined 7 (IPL share of matches 64%; IPL score 0.3063, T20I score 2.4990).
- **Why this position.** Relative to neighbours: rank 6 (Abrar Ahmed) is above: score difference 0.0771, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 8 (Akeal Hosein) is below: score difference 0.01641, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED.

### 8. Akeal Hosein (player 2417)

**Why selected.** Rank 8 by the Pressure Response Index (+1.75, 0 is the typical eligible bowler): in 61% of 57 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.12 runs per ball against 1.32 expected for the same match situations; wicket rate 0.064 against 0.057 expected. Normal-play baseline -0.022, pressure level +0.074, difference +0.085. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 57 pressure spells and 568 pressure deliveries in 75 matches. Top-10 inclusion 35%, 95% rank interval 2 to 66, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 568 pressure deliveries in 57 spells: phases (powerplay 0, middle 458, death 110), innings 1 306 and innings 2 262; mean intensity 0.38.
- **Actual performance against expectation.** Observed 1.12 runs per ball against 1.32 expected; wicket rate 0.064 against 0.057.
- **Baseline and difference.** Normal-play baseline -0.022, pressure level (unshrunk) 0.074, difference 0.085 (A-residual units per ball).
- **Score and components.** Score 1.7472 [0.2056, 5.6218] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 1.664, z_B -0.330, z_CONS 1.830.
- **Consistency across matches.** 61% of pressure units beat the expectation; between-unit dispersion 0.268; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 75 matches (IPL 8, T20I 67), 1632 deliveries with a defined intensity, effective sample 1133, data weight (reliability of the estimate) 0.40. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 35%, 95% rank interval 2 to 66.
- **Rank under each approach and format.** A 11, B 106, C 8; IPL only n/a, T20I only 6, combined 8 (IPL share of matches 11%; IPL score n/a, T20I score 1.7059).
- **Why this position.** Relative to neighbours: rank 7 (Rashid Khan) is above: score difference 0.01641, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 9 (Wanindu Hasaranga) is below: score difference 0.09779, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### 9. Wanindu Hasaranga (player 4900)

**Why selected.** Rank 9 by the Pressure Response Index (+1.65, 0 is the typical eligible bowler): in 58% of 77 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.31 runs per ball against 1.28 expected for the same match situations; wicket rate 0.078 against 0.054 expected. Normal-play baseline +0.055, pressure level +0.050, difference -0.016. The pressure level is below the normal-play baseline: the rank reflects performance above expectation in pressure situations, not an improvement over the player's normal play. Evidence: 77 pressure spells and 1152 pressure deliveries in 88 matches. Top-10 inclusion 20%, 95% rank interval 4 to 70, evidence class STRONG_SUBSTANTIAL. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 1152 pressure deliveries in 77 spells: phases (powerplay 11, middle 868, death 273), innings 1 580 and innings 2 572; mean intensity 0.54.
- **Actual performance against expectation.** Observed 1.31 runs per ball against 1.28 expected; wicket rate 0.078 against 0.054.
- **Baseline and difference.** Normal-play baseline 0.055, pressure level (unshrunk) 0.050, difference -0.016 (A-residual units per ball).
- **Score and components.** Score 1.6494 [0.1234, 4.7273] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 1.576, z_B 1.101, z_CONS 1.723.
- **Consistency across matches.** 58% of pressure units beat the expectation; between-unit dispersion 0.224; evidence class STRONG_SUBSTANTIAL.
- **Evidence amount.** 88 matches (IPL 35, T20I 53), 1974 deliveries with a defined intensity, effective sample 1711, data weight (reliability of the estimate) 0.53. MEETS_ALL_DECLARED_FLOORS.
- **Stability.** Top-10 inclusion 20%, 95% rank interval 4 to 70.
- **Rank under each approach and format.** A 12, B 17, C 9; IPL only 33, T20I only 3, combined 9 (IPL share of matches 40%; IPL score 0.2101, T20I score 1.9044).
- **Why this position.** Relative to neighbours: rank 8 (Akeal Hosein) is above: score difference 0.09779, 95% intervals overlap, so the order of the two is not distinguishable from noise; rank 10 (Mohammad Nawaz) is below: score difference 0.01576, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED.

### 10. Mohammad Nawaz (player 2490)

**Why selected.** Rank 10 by the Pressure Response Index (+1.63, 0 is the typical eligible bowler): in 61% of 44 pressure spells the bowler did better than the model expected. On pressure deliveries the bowler conceded 1.07 runs per ball against 1.15 expected for the same match situations; wicket rate 0.078 against 0.055 expected. Normal-play baseline +0.016, pressure level +0.078, difference +0.052. The pressure level is above the normal-play baseline, so the result is not only overall quality. Evidence: 44 pressure spells and 540 pressure deliveries in 52 matches. Top-10 inclusion 36%, 95% rank interval 2 to 73, evidence class STRONG_LIMITED. Status EXPLORATORY: the order is not shown to separate players beyond noise.

- **Pressure situations faced.** 540 pressure deliveries in 44 spells: phases (powerplay 3, middle 492, death 45), innings 1 226 and innings 2 314; mean intensity 0.50.
- **Actual performance against expectation.** Observed 1.07 runs per ball against 1.15 expected; wicket rate 0.078 against 0.055.
- **Baseline and difference.** Normal-play baseline 0.016, pressure level (unshrunk) 0.078, difference 0.052 (A-residual units per ball).
- **Score and components.** Score 1.6336 [-0.0238, 5.8135] (PRI (cohort standard deviations; 0 is the typical eligible player); interval flag ASYMMETRIC_UPPER_TAIL); components: z_A 1.711, z_B 1.147, z_CONS 1.556.
- **Consistency across matches.** 61% of pressure units beat the expectation; between-unit dispersion 0.275; evidence class STRONG_LIMITED.
- **Evidence amount.** 52 matches (IPL 0, T20I 52), 1004 deliveries with a defined intensity, effective sample 837, data weight (reliability of the estimate) 0.37. MEETS_ALL_DECLARED_FLOORS;ONE_FORMAT_BELOW_HALF_FLOOR.
- **Stability.** Top-10 inclusion 36%, 95% rank interval 2 to 73.
- **Rank under each approach and format.** A 9, B 15, C 10; IPL only n/a, T20I only 7, combined 10 (IPL share of matches 0%; IPL score n/a, T20I score 1.6705).
- **Why this position.** Relative to neighbours: rank 9 (Wanindu Hasaranga) is above: score difference 0.01576, 95% intervals overlap, so the order of the two is not distinguishable from noise.
- **Limitations.** The pressure definition is unvalidated; the estimate contains the player's overall quality as well as pressure effects; the data weight is low, so the estimate is shrunk strongly; format scores are on each format's own scale and are not comparable with the combined score; flags: INTENSITY_DEFINITION_NOT_VALIDATED;FORMAT_COMBINATION_UNSUPPORTED;DATA_WEIGHT_BELOW_0_5.

### Candidate pool, ranks 11 to 20

These players are not in the submitted list. Reasons come from the data; none is a statement that the player performs poorly.

- **Rank 11, Abbas Afridi**: `INCONSISTENT_ACROSS_MATCHES`: 68% of 19 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.4892 is below the tenth-ranked score +1.6336, although the 95% interval reaches +6.3061; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 21 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 12, Matthew Humphreys**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.4161 is below the tenth-ranked score +1.6336, although the 95% interval reaches +6.6145; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 13 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 13, Sufiyan Muqeem**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.3913 is below the tenth-ranked score +1.6336, although the 95% interval reaches +6.9919; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 17 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 14, Craig Young**: `INCONSISTENT_ACROSS_MATCHES`: 72% of 18 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.3323 is below the tenth-ranked score +1.6336, although the 95% interval reaches +5.6816; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 21 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 15, Noor Ahmad**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.2816 is below the tenth-ranked score +1.6336, although the 95% interval reaches +4.5700; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 14% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 95).
- **Rank 16, Mitchell Santner**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.2763 is below the tenth-ranked score +1.6336, although the 95% interval reaches +4.5922; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 12% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 5 to 89).
- **Rank 17, Mark Wood**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.0828 is below the tenth-ranked score +1.6336, although the 95% interval reaches +5.1842; the order between them is within noise.
- **Rank 18, Haris Rauf**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.0570 is below the tenth-ranked score +1.6336, although the 95% interval reaches +4.9633; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 16% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 113); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 46 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 19, Sai Kishore**: `INCONSISTENT_ACROSS_MATCHES`: 67% of 21 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.9539 is below the tenth-ranked score +1.6336, although the 95% interval reaches +4.8884; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 16% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 103); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 27 matches in IPL and 0 in the other format; the cross-format check cannot be applied to this player.
- **Rank 20, Nathan Ellis**: `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.8902 is below the tenth-ranked score +1.6336, although the 95% interval reaches +4.2674; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 9% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 6 to 104).

### Raw-statistic standouts (death-overs economy, at least 60 balls)

Players at the top of a simple raw statistic, with the reason they are or are not in the list:

- **Abrar Ahmed** (death-overs economy 6.7 over 109 balls): `SELECTED`: also in the submitted Top 10.
- **Akeal Hosein** (death-overs economy 7.5 over 102 balls): `SELECTED`: also in the submitted Top 10.
- **Gareth Delany** (death-overs economy 7.2 over 78 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.1301 is below the tenth-ranked score +1.6336, although the 95% interval reaches +2.6722; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 0% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 17 to 133); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 31 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Jasprit Bumrah** (death-overs economy 7.2 over 544 balls): `SELECTED`: also in the submitted Top 10.
- **Kane Richardson** (death-overs economy 7.5 over 78 balls): `NO_PRESSURE_ESTIMATE`: no delivery with a defined pressure intensity and a residual was found in the pre-test window; the value is missing, not zero.
- **Noor Ahmad** (death-overs economy 7.6 over 217 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.2816 is below the tenth-ranked score +1.6336, although the 95% interval reaches +4.5700; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 14% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 4 to 95).
- **Shadab Khan** (death-overs economy 6.5 over 66 balls): `HIGH_RAW_BUT_NEGATIVE_AFTER_CONTEXT_ADJUSTMENT`: high on the raw death-overs statistic, but at or below the model expectation once the match situation is accounted for; `INCONSISTENT_ACROSS_MATCHES`: 35% of 37 pressure units beat the expectation; the declared INCONSISTENT rule applies; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 0% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 35 to 152); `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 41 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Sikandar Raza** (death-overs economy 7.5 over 108 balls): `INCONSISTENT_ACROSS_MATCHES`: 49% of 43 pressure units beat the expectation; the declared INCONSISTENT rule applies; `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +0.1151 is below the tenth-ranked score +1.6336, although the 95% interval reaches +2.9617; the order between them is within noise; `LOW_TOP10_INCLUSION_PROBABILITY`: inclusion probability 1% across the match-cluster bootstrap draws (selected players need 25% for a PROVISIONAL row; rank interval 15 to 132).
- **Sufiyan Muqeem** (death-overs economy 6.8 over 70 balls): `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`: score +1.3913 is below the tenth-ranked score +1.6336, although the 95% interval reaches +6.9919; the order between them is within noise; `ONE_FORMAT_ONLY_LOW_EVIDENCE`: 17 matches in T20I and 0 in the other format; the cross-format check cannot be applied to this player.
- **Sunil Narine** (death-overs economy 5.9 over 216 balls): `SELECTED`: also in the submitted Top 10.

