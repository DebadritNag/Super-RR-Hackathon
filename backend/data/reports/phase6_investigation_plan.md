# Phase 6 investigation plan: pressure definition and reliability validation

Status: EXPERIMENTAL_NOT_VALIDATED. INTERNAL. No official Top 10, no public experimental ranking, no official ML training. TEST outcomes are not used. Cricsheet is not used. The 0.5 data-weight gate is not changed.

## 1. What was declared before any result
- Criteria file: `config/phase6_selection_criteria_v1.json`, SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851`.
- Git blob hash of the same bytes (`git hash-object` value): `191889ffa36278a4ac6ab9aaabb5058375b2c0ee`. The workspace is not a git repository; the value is computed from the bytes so it can be checked later.
- Investigation config: `config/phase6_investigation_v1.json`, SHA-256 `29ec41e89153ff114f86a38bee8976e39e90aac65379a8ad4b87ffd80372509c`.
- Run order is enforced by the append-only table `p6_run_log` in `exploratory.duckdb`: row `seq = 1` (step `plan`) carries the criteria hash. Every later step verifies that the criteria file on disk still has that hash before it writes anything, and appends its own row. A rewritten criteria file therefore makes every later step fail.
- The criteria contain no individual identity, ordering, score level or Top-10 membership as an input (`forbidden_inputs`). A hash-time scan rejects the words `player`, `rank`, `top10` and `promot` outside that list.

## 2. Questions
1. Between-player variance of pressure residuals sits at the shrinkage floor in all 48 contexts. Is the true value about zero, is the noise model misspecified, or are the samples too small to tell?
2. How reliable are the pressure streams under odd/even, early/late and repeated random match splits, per stream, format, role and definition, with Spearman-Brown correction and bootstrap intervals?

## 3. Data and windows
- Primary window `PRE_TEST` = TRAIN + VALIDATION (723 matches, 2022-01-22 to 2025-12-19). TEST rows are not loaded. The 42 late-dated T20I matches are TEST by date and stay excluded.
- `TRAIN` (512 matches) is run next to it because the Phase 4 floor was fitted on TRAIN.
- In-sample diagnostics only. The label on every row is `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`.
- Seed 20260512, 1000 match-cluster bootstrap draws, 200 random splits.
- Definitions examined (nine, multiplicity not corrected): `chase|q0.75`, `chase|q0.9`, `chase|q0.95`, `inn1|q0.75`, `inn1|q0.9`, `inn1|q0.95`, `any|q0.75`, `any|q0.9`, `any|q0.95`. `any|q0.75` stays PROVISIONAL.

## 4. Variance estimators
E1 moments with floor (Phase 4 basis), E1b moments with independent-ball noise, E1c moments with match-cluster noise, E2 REML, E3 ML, E4 beta-binomial (binary streams), E5 gamma-Poisson (count streams, flagged `MISSPECIFIED_FOR_RUNS` on runs), E6 match-cluster bootstrap of E1c, E7 split-half covariance (model-free). E4 and E5 are sensitivity only and never enter a verdict.

Identification rule:

| class | condition |
|---|---|
| identified_positive | E7 split-covariance bootstrap 95% lower bound > 0 and E1c match-cluster moment estimate positive in at least 90% of E6 bootstrap draws |
| not_identified | E7 interval contains 0 and the E6 share of positive draws is below 90% |
| otherwise | weakly_identified |


## 5. Flags and verdict (thresholds fixed in the criteria file)

| threshold | value |
|---|---|
| hb_overall_requires_hb_ii | yes |
| icc_min | 0.05 |
| kish_ratio_to_balls_per_match_hi | 1.25 |
| kish_ratio_to_balls_per_match_lo | 0.75 |
| min_supported_of_hb_i_to_iv | 2 |
| pearson_dispersion_min | 1.50 |
| positive_draw_share_min | 0.90 |
| power_min | 0.80 |
| power_ratio | 0.01 |
| tercile_variance_ratio_hi | 1.50 |
| tercile_variance_ratio_lo | 0.67 |


| flag | supported when |
|---|---|
| H-A_null | E7 bootstrap 95% interval contains 0 and the E6 share of draws with a positive match-cluster estimate is below positive_draw_share_min |
| H-A_power | detectability simulation share of positive estimates at tau2/sigma2 = power_ratio is at least power_min |
| H-B(i) | mean(sigma2/n_eff_kish) / mean(sigma2/n_i), divided by the mean balls per match, lies in [kish_ratio_to_balls_per_match_lo, ..._hi] |
| H-B(ii) | the sign of the between variance differs between the Kish basis (E1) and the match-cluster basis (E1c) |
| H-B(iii) | residual-variance ratio of the lowest versus highest tercile of ball counts is above tercile_variance_ratio_hi or below tercile_variance_ratio_lo |
| H-B(iv) | ICC of ball residuals within match or within individual-match cluster above icc_min, or Pearson dispersion of the moment fit above pearson_dispersion_min |
| H-B_overall | at least min_supported_of_hb_i_to_iv of H-B(i) to H-B(iv) supported, including H-B(ii) |
| H-C | E7 or E6 lower bound > 0 and the required-sample projection for R = 0.5 is finite and larger than the observed median ball count |


Verdict table, evaluated in this order:

| condition | verdict |
|---|---|
| H-A_null and H-A_power and not H-B_overall | H-A_SUPPORTED |
| H-A_null and not H-A_power | UNIDENTIFIED |
| H-B_overall and H-C | MIXED |
| H-B_overall only | H-B_SUPPORTED |
| H-C only | H-C_SUPPORTED |
| any other combination | UNIDENTIFIED |


Sparse contexts: fewer than 8 TRAIN individuals or fewer than 10 per half is NOT_ESTIMABLE with a reason.

## 6. Floor arithmetic
`k_for` computes `floor_abs = floor * sigma2`, `tau2 = max(max(between, floor_abs) * mult, floor_abs)`, `k = sigma2 / tau2`. On a floor hit `shrink_tau4` therefore gives `k = 1 / (4 * 0.01) = 25`. The investigation recomputes this from the code and from a hand formula, and compares it with the stored `p5_context_fit` values.

## 7. Split-half reliability
Modes odd_even, early_late, random; minimum 6 pressure balls per half; at least 10 individuals; Spearman-Brown 2r/(1+r), reported unclipped; a negative r gives a negative value; pooling Fisher z with weights n-3, correlation clipped at 0.99; intervals from a bootstrap over individuals and a match-cluster bootstrap (odd/even, early/late) and a bootstrap of the per-repeat median (random).

## 8. Selection criteria for the definition comparison (a later step)

| metric | definition |
|---|---|
| M1 | Fisher-z pooled R over the four cells (weights n-3, correlation clipped at 0.99); SE1 is the SD over bootstrap draws of the pooled value |
| M2 | split-covariance signal share: cov(half1, half2) / var(individual means); descriptive only |
| M3 | share of individuals whose match-cluster bootstrap 95% interval of the raw mean residual excludes the pooled cell mean; descriptive only |
| M4 | median over individuals of pressure-ball counts, pooled over the four cells |
| M5 | median over 1000 match-cluster resamples of the Spearman correlation between the resample ordering and the full-window ordering, per cell, then medianed over cells |
| M6 | control reliability of a non-pressure ball sample matched on balls per individual; descriptive only, never a selection input |
| R | odd/even split-half Spearman-Brown reliability of definition d in cell c, primary stream, PRE_TEST, at least 6 pressure balls per half, at least 10 individuals; match-cluster bootstrap with 1000 draws; lo is the 2.5th percentile of the draws |


Rule: PASS(d) iff R(d,c) is estimable in all four cells and lo(d,c) > 0 in at least three cells. TOP(d) iff PASS(d) and M1(d) >= max M1 over passing definitions minus SE1 of the best. Order inside TOP: M4 descending, then M5 descending, then id ascending. The output is a pass list and a top group, not a selection.

Stability: if the TOP set on TRAIN only differs from the PRE_TEST TOP set the report states DEFINITION_ORDER_NOT_STABLE and names no top group.

Confound control: M1, M2 and M5 are recomputed on the intersection of individuals eligible under all nine definitions per cell; the rule uses the intersection version when it has at least 30 individuals in every cell, otherwise COMPARISON_CONFOUNDED and only the pass list is reported.

Multiplicity: nine candidates examined, no correction applied; any top group is PROVISIONAL and does not replace any|q0.75.

## 9. What counts as evidence
- Between-variance is called identified and positive only if the model-free split covariance has a bootstrap lower bound above 0 and the match-cluster estimate is positive in at least 90% of bootstrap draws.
- A split-half reliability counts as above zero only if its bootstrap interval excludes 0.
- Agreement between sources inside the same data is a consistency check, not validation.

## 10. What the data cannot show
- Out-of-sample validity: every number is computed on the same TRAIN and VALIDATION matches used to build the baseline and thresholds.
- TEST was opened once in Phase 4 and is not pristine; it is not used here at all.
- The noise model cannot be tested with these data alone; the bases bracket the truth.
- Within-innings dependence cannot be separated because stored context rows hold match-level sums.
- A definition passing a reliability criterion is not shown to measure pressure skill.

## 11. Not done in this plan
No threshold, gate, methodology lock or Phase 4/5 artifact is edited. The 0.5 data-weight gate stays at 0.5. No result is published.
