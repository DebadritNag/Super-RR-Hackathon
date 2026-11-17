# Pressure-specific eligibility report (Phase 3, Stage 5, EXPLORATORY)

Status `EXPLORATORY_NOT_VALIDATED`, official_ranking `False`, not_for_publication `True`. Source numbers: `pressure_threshold_experiment.json` (same directory).

## 1. Status: exploratory proxy versus validated

- **Validated numbers in this report: none.** Every figure is an exploratory calculation on the official DuckDB through the pre-delivery state table.
- The measured stream is actual minus expected (AvE) under the Stage 4 baseline, labelled `PROXY_ACTUAL_MINUS_EXPECTED_NOT_A_PRESSURE_SCORE`. It exists to measure sample sufficiency, interval width and ranking stability, not to rank players.
- No player is listed, no Top 10 is published, no model is trained, official data is unchanged. 70:30 stays a provisional default.
- Thresholds below are provisional recommendations; approval is required before full pressure scoring.

## 2. Method

1. **Pressure sample.** For each pre-declared definition (context x quantile) the Stage 3 candidate flags of IPL and T20I (each with its own per-format quantile threshold) select pressure deliveries from the base population: innings 1/2 only, no OTHER_T20, no DLS-excluded rows, no innings 3/4 (Super Over), no unverified chase targets. Batters count balls faced (wides and Penalty excluded); bowlers count deliveries bowled (Penalty excluded), threshold measure = legal balls.
2. **Grid.** Contexts ['chase', 'inn1', 'any'] x quantiles [0.75, 0.9, 0.95] (view `abs`; batter signal {'chase': 'rrr', 'inn1': 'neg_par_dev'}, bowler signal `bowl_signal_B_all`). `any` = chase flag OR innings-1 flag at the same quantile. The grid is a search grid, not a chosen cutoff.
3. **Baseline.** Primary: per-candidate baseline (pressure membership as the finest cell level), leave-player-out, so expectations come from peers in the same pressure band and phase/wickets/competition cell. Sensitivity: B0 without a pressure term.
4. **Harness.** The Phase 2.5 `confidence_engine` is reused unchanged: per-(format, player, match) sufficient statistics, percentile and nominal ladders (rescaled for pressure sample sizes, `pressure_eligibility_rules_v1.json`), single-measure and balls+matches rules, bootstrap by match (1000 resamples, seed 20260512), pool rule max(30, 3 x 10).
5. **Data-weight rule.** The primary rule is the lowest ladder rung at or above the number of pressure balls at which the player's data outweighs the EB prior (weight 0.5), with a sufficient pool. Batter and bowler, IPL and T20I are evaluated independently.
6. **Selection of the provisional definition.** Population-level quantities only. A definition is viable when, for IPL and T20I and for batters and bowlers, a data-weight rule with a sufficient pool exists. Among viable definitions choose the highest q; ties go to the larger pressure population (sum of pressure unit rows over the four format-role cells). Player scores and rankings are never used; ranking stability is reported, not used.

## 3. Definitions examined and selection

Stage 3 candidates recomputed here: 364 (families a and b; the Stage 3 report lists 384 including 20 family-(c) break rows). Definitions run through the full harness: 9. Blank (`n/a`) means no rule reaches the data-weight floor with a sufficient pool.

| Definition | Pressure unit rows (4 cells) | Cells with a rule | IPL batter elig. | IPL bowler elig. | T20I batter elig. | T20I bowler elig. | Both formats batter | Both formats bowler | Viable | Provisional |
|---|---|---|---|---|---|---|---|---|---|---|
| chase|q0.75 | 43,526 | 4 | 70 | 30 | 47 | 43 | 14 | 5 | yes | no |
| inn1|q0.75 | 49,389 | 1 | n/a | 51 | n/a | n/a | n/a | n/a | no | no |
| any|q0.75 | 92,915 | 4 | 101 | 58 | 122 | 42 | 28 | 8 | yes | no |
| chase|q0.9 | 17,356 | 4 | 56 | 43 | 61 | 32 | 8 | 6 | yes | yes |
| inn1|q0.9 | 19,748 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | no | no |
| any|q0.9 | 37,104 | 3 | 63 | 38 | 102 | n/a | 10 | n/a | no | no |
| chase|q0.95 | 8,673 | 1 | 32 | n/a | n/a | n/a | n/a | n/a | no | no |
| inn1|q0.95 | 9,871 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | no | no |
| any|q0.95 | 18,544 | 2 | 54 | n/a | n/a | 37 | n/a | n/a | no | no |

Viable definitions: 3. Selected: `chase|q0.9` (one of the definitions examined; not validated).

## 4. Pressure sample sizes by definition

Observed players = players with at least one pressure delivery.

| Definition | Format | Role | Observed players | Pressure deliveries | Distinct matches | Balls for data weight | Data-weight rule | Strictest sufficient-pool rule |
|---|---|---|---|---|---|---|---|---|
| chase|q0.75 | IPL | batter | 264 | 9,771 | 204 | 37.62 | balls:PR45 | balls:PR90 |
| chase|q0.75 | IPL | bowler | 201 | 10,228 | 275 | 77.69 | balls:PR96 | balls:PR96 |
| chase|q0.75 | T20I | batter | 460 | 11,560 | 254 | 45.29 | balls:PR60 | balls:PR60 |
| chase|q0.75 | T20I | bowler | 348 | 11,967 | 326 | 60.09 | balls:PR72 | balls:PR72 |
| inn1|q0.75 | IPL | batter | 233 | 10,910 | 208 | 94.92 | n/a | balls:PR90 |
| inn1|q0.75 | IPL | bowler | 198 | 11,333 | 207 | 74.83 | balls:P75 | balls:PR96 |
| inn1|q0.75 | T20I | batter | 459 | 13,359 | 258 | 77.55 | n/a | balls:PR60 |
| inn1|q0.75 | T20I | bowler | 306 | 13,787 | 263 | 99.49 | n/a | balls:PR96 |
| any|q0.75 | IPL | batter | 299 | 20,681 | 327 | 56.57 | balls:PR60 | balls:PR120 |
| any|q0.75 | IPL | bowler | 230 | 21,561 | 333 | 127.18 | balls:P75 | balls:PR144 |
| any|q0.75 | T20I | batter | 584 | 24,919 | 403 | 53.40 | balls:PR60 | balls:PR90 |
| any|q0.75 | T20I | bowler | 405 | 25,754 | 409 | 105.07 | balls:PR144 | balls:PR144 |
| chase|q0.9 | IPL | batter | 211 | 3,884 | 175 | 20.94 | balls:P75 | balls:PR30 |
| chase|q0.9 | IPL | bowler | 169 | 4,093 | 206 | 30.26 | balls:P75 | balls:PR36 |
| chase|q0.9 | T20I | batter | 334 | 4,592 | 215 | 22.00 | balls:PR24 | balls:PR24 |
| chase|q0.9 | T20I | bowler | 269 | 4,787 | 257 | 33.64 | balls:PR36 | balls:PR36 |
| inn1|q0.9 | IPL | batter | 181 | 4,369 | 118 | 66.72 | n/a | balls:P75 |
| inn1|q0.9 | IPL | bowler | 154 | 4,532 | 115 | 54.17 | n/a | balls:P75 |
| inn1|q0.9 | T20I | batter | 306 | 5,330 | 148 | 42.75 | n/a | balls:PR30 |
| inn1|q0.9 | T20I | bowler | 232 | 5,517 | 123 | 41.96 | n/a | balls:PR36 |
| any|q0.9 | IPL | batter | 248 | 8,253 | 270 | 32.97 | balls:P75 | balls:PR60 |
| any|q0.9 | IPL | bowler | 195 | 8,625 | 262 | 63.47 | balls:PR72 | balls:PR72 |
| any|q0.9 | T20I | batter | 446 | 9,922 | 328 | 29.52 | balls:PR30 | balls:PR45 |
| any|q0.9 | T20I | bowler | 334 | 10,304 | 318 | 49.91 | n/a | balls:PR48 |
| chase|q0.95 | IPL | batter | 174 | 1,937 | 155 | 15.31 | balls:PR18 | balls:PR18 |
| chase|q0.95 | IPL | bowler | 133 | 2,046 | 172 | 31.30 | n/a | balls:PR24 |
| chase|q0.95 | T20I | batter | 268 | 2,295 | 189 | 28.45 | n/a | balls:PR18 |
| chase|q0.95 | T20I | bowler | 206 | 2,395 | 203 | 22.42 | n/a | balls:PR18 |
| inn1|q0.95 | IPL | batter | 143 | 2,184 | 81 | 30.72 | n/a | balls:PR24 |
| inn1|q0.95 | IPL | bowler | 115 | 2,266 | 59 | 35.80 | n/a | balls:P75 |
| inn1|q0.95 | T20I | batter | 203 | 2,663 | 102 | 39.64 | n/a | balls:PR24 |
| inn1|q0.95 | T20I | bowler | 169 | 2,758 | 78 | 37.23 | n/a | balls:PR24 |
| any|q0.95 | IPL | batter | 213 | 4,121 | 225 | 24.19 | balls:P75 | balls:PR30 |
| any|q0.95 | IPL | bowler | 165 | 4,312 | 202 | 46.44 | n/a | balls:P75 |
| any|q0.95 | T20I | batter | 350 | 4,958 | 282 | 37.59 | n/a | balls:PR30 |
| any|q0.95 | T20I | bowler | 265 | 5,153 | 249 | 27.28 | balls:PR36 | balls:PR36 |

## 5. Candidate thresholds for the provisional definition `chase|q0.9`

Balls family (batter balls faced, bowler legal balls). Percentile rungs `P` come from the observed pressure distribution; `PR` rungs are nominal and kept only between the observed p10 and p90. Eligible counts, match coverage, bootstrap Top 10 overlap and median 95% interval width (score units) per rung; `Spearman/Overlap vs next` compares neighbouring rungs.

### IPL batter

| Rule | Min | Eligible | Pool ok | Match coverage % | Exp. Top 10 overlap | Median CI width | Spearman vs next | Overlap vs next | Data-weight rule |
|---|---|---|---|---|---|---|---|---|---|
| balls:P10 | 2 | 197 | yes | 49.30 | 5.73 | 66.77 | 1.00 | 10 | no |
| balls:P25 | 5 | 164 | yes | 49.30 | 6.00 | 68.05 | 1.00 | 9 | no |
| balls:PR6 | 6 | 155 | yes | 49.30 | 5.85 | 68.63 | 1.00 | 10 | no |
| balls:P50 | 11 | 114 | yes | 48.45 | 6.01 | 70.44 | 1.00 | 10 | no |
| balls:PR12 | 12 | 105 | yes | 48.45 | 6.10 | 70.38 | 1.00 | 9 | no |
| balls:PR18 | 18 | 71 | yes | 47.04 | 6.33 | 78.95 | 1.00 | 7 | no |
| balls:P75 | 24 | 56 | yes | 43.38 | 6.61 | 75.02 | 1.00 | 8 | yes |
| balls:PR30 | 30 | 37 | yes | 40.00 | 6.99 | 78.98 | 1.00 | 9 | no |
| balls:PR45 | 45 | 23 | no | 34.08 | 7.72 | 78.95 | n/a | n/a | no |

### IPL bowler

| Rule | Min | Eligible | Pool ok | Match coverage % | Exp. Top 10 overlap | Median CI width | Spearman vs next | Overlap vs next | Data-weight rule |
|---|---|---|---|---|---|---|---|---|---|
| balls:P10 | 3 | 152 | yes | 57.46 | 4.14 | 3.22 | 1.00 | 9 | no |
| balls:PR6 | 6 | 142 | yes | 57.18 | 4.31 | 3.23 | 1.00 | 10 | no |
| balls:P25 | 7 | 128 | yes | 56.90 | 4.46 | 3.27 | 1.00 | 9 | no |
| balls:PR12 | 12 | 106 | yes | 56.62 | 4.78 | 3.36 | 1.00 | 9 | no |
| balls:P50 | 16 | 86 | yes | 54.08 | 4.79 | 3.52 | 1.00 | 9 | no |
| balls:PR18 | 18 | 78 | yes | 52.96 | 5.22 | 3.55 | 1.00 | 9 | no |
| balls:PR24 | 24 | 65 | yes | 51.55 | 5.21 | 3.57 | 0.99 | 5 | no |
| balls:P75 | 32 | 43 | yes | 45.92 | 5.18 | 3.56 | 1.00 | 9 | yes |
| balls:PR36 | 36 | 34 | yes | 44.51 | 5.42 | 3.62 | 1.00 | 9 | no |
| balls:PR48 | 48 | 23 | no | 34.65 | 6.78 | 3.56 | n/a | n/a | no |

### T20I batter

| Rule | Min | Eligible | Pool ok | Match coverage % | Exp. Top 10 overlap | Median CI width | Spearman vs next | Overlap vs next | Data-weight rule |
|---|---|---|---|---|---|---|---|---|---|
| balls:P10 | 2 | 312 | yes | 50.12 | 5.73 | 57.01 | 1.00 | 10 | no |
| balls:P25 | 4 | 265 | yes | 49.88 | 6.03 | 58.50 | 1.00 | 10 | no |
| balls:PR6 | 6 | 219 | yes | 48.48 | 6.15 | 58.50 | 1.00 | 10 | no |
| balls:P50 | 9 | 174 | yes | 47.55 | 6.16 | 61.36 | 1.00 | 9 | no |
| balls:PR12 | 12 | 134 | yes | 46.15 | 6.39 | 64.74 | 1.00 | 8 | no |
| balls:P75 | 18 | 84 | yes | 40.09 | 6.79 | 70.69 | 1.00 | 10 | no |
| balls:PR24 | 24 | 61 | yes | 36.36 | 7.01 | 79.48 | n/a | n/a | yes |

### T20I bowler

| Rule | Min | Eligible | Pool ok | Match coverage % | Exp. Top 10 overlap | Median CI width | Spearman vs next | Overlap vs next | Data-weight rule |
|---|---|---|---|---|---|---|---|---|---|
| balls:P10 | 2 | 249 | yes | 58.74 | 3.81 | 2.60 | 1.00 | 9 | no |
| balls:P25 | 5 | 208 | yes | 56.18 | 3.79 | 2.83 | 1.00 | 10 | no |
| balls:PR6 | 6 | 198 | yes | 55.24 | 3.95 | 2.85 | 1.00 | 10 | no |
| balls:P50 | 10 | 138 | yes | 53.85 | 4.17 | 3.31 | 1.00 | 8 | no |
| balls:PR12 | 12 | 125 | yes | 52.45 | 4.58 | 3.34 | 1.00 | 8 | no |
| balls:PR18 | 18 | 86 | yes | 47.09 | 5.15 | 3.48 | 1.00 | 9 | no |
| balls:P75 | 21 | 69 | yes | 43.12 | 5.59 | 3.67 | 1.00 | 7 | no |
| balls:PR24 | 24 | 56 | yes | 40.09 | 5.80 | 3.62 | 1.00 | 6 | no |
| balls:PR36 | 36 | 32 | yes | 31.70 | 6.55 | 3.69 | n/a | n/a | yes |

## 6. Eligible populations at the recommended rules

| Format | Role | Rule | Min balls | Eligible players | Pressure deliveries | Distinct matches | Median n_eff (shrink) | Total n_eff (shrink) | Median n_eff (Kish, innings-level) | Pool verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | balls:P75 | 24 | 56 | 2,531 | 154 | 22.33 | 1767.88 | 3.26 | SUFFICIENT: 56 eligible, at or above the required pool of 30 |
| IPL | bowler | balls:P75 | 32 | 43 | 2,425 | 163 | 29.79 | 1577.78 | 4.61 | SUFFICIENT: 43 eligible, at or above the required pool of 30 |
| T20I | batter | balls:PR24 | 24 | 61 | 2,371 | 156 | 18.13 | 1542.89 | 2.89 | SUFFICIENT: 61 eligible, at or above the required pool of 30 |
| T20I | bowler | balls:PR36 | 36 | 32 | 2,077 | 136 | 34.00 | 1369.18 | 4.86 | SUFFICIENT: 32 eligible, at or above the required pool of 30 |

### Ranking stability and uncertainty (bootstrap by match)

The Top 10 columns describe how often the original Top 10 stays in the Top 10 under resampling; no player is named. Interval widths are in score units (batter: 100 x runs per ball, actual minus expected; bowler: z-composite). `Excludes zero` is the share of eligible batters whose 95% interval excludes 0.

| Format | Role | Expected Top 10 overlap | Mean Top 10 membership freq. | Spearman vs original (mean) | Spearman vs original (p5) | Median 95% CI width | p90 CI width | Excludes zero (batter) |
|---|---|---|---|---|---|---|---|---|
| IPL | batter | 6.61 | 0.66 | 0.81 | 0.72 | 74.33 | 116.17 | 0.27 |
| IPL | bowler | 5.18 | 0.52 | 0.62 | 0.44 | 3.62 | 5.40 | n/a |
| T20I | batter | 7.01 | 0.70 | 0.80 | 0.69 | 74.94 | 115.01 | 0.15 |
| T20I | bowler | 6.55 | 0.66 | 0.69 | 0.52 | 3.67 | 5.78 | n/a |

## 7. Comparison with the Phase 2.5 all-situation thresholds

The Phase 2.5 thresholds were not reused: they are checked here against the pressure samples. A pressure sample is a small slice of a player's deliveries, so the all-situation floor leaves almost no player eligible.

| Format | Role | Phase 2.5 rule | Phase 2.5 min balls | Phase 2.5 eligible (all situations) | Phase 2.5 balls for data weight | Players with a pressure sample | Pass Phase 2.5 min on pressure samples | Pressure balls for data weight | Pressure-specific min balls | Pressure-specific eligible |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | balls:PR120 | 120 | 129 | 106.58 | 211 | 1 | 20.94 | 24 | 56 |
| IPL | bowler | balls:PR192 | 192 | 119 | 186.37 | 169 | 0 | 30.26 | 32 | 43 |
| T20I | batter | balls:PR120 | 120 | 205 | 87.25 | 334 | 0 | 22.00 | 24 | 61 |
| T20I | bowler | balls:PR144 | 144 | 191 | 138.03 | 269 | 1 | 33.64 | 36 | 32 |

### Baseline sensitivity (B0 versus per-candidate baseline)

Spearman correlation of eligible-player scores computed from B0 residuals and from the per-candidate baseline residuals.

| Format | Role | Eligible | Spearman B0 vs candidate |
|---|---|---|---|
| IPL | batter | 56 | 1.00 |
| IPL | bowler | 43 | 0.99 |
| T20I | batter | 61 | 1.00 |
| T20I | bowler | 32 | 1.00 |

## 8. Provisional recommendation (written after reading the results)

- PROVISIONAL, not validated: definition chase|q0.9 (context chase, quantile 0.9) is one of 9 definitions run through the threshold harness, drawn from 364 Stage 3 candidate definitions of families (a) and (b). It was chosen by the pre-declared population-level rule only (highest quantile with a sufficient pool in all four cells).
- IPL batter: at least 24 pressure balls faced (balls:P75; data outweighs the prior from about 21); 56 eligible, 154 distinct matches (43% of the 355 chase matches), bootstrap expected Top 10 overlap 6.6, Spearman versus original 0.81.
- IPL bowler: at least 32 pressure legal balls bowled (balls:P75; data outweighs the prior from about 30); 43 eligible, 163 distinct matches (46% of the 355 chase matches), bootstrap expected Top 10 overlap 5.2, Spearman versus original 0.62.
- T20I batter: at least 24 pressure balls faced (balls:PR24; data outweighs the prior from about 22); 61 eligible, 156 distinct matches (36% of the 429 chase matches), bootstrap expected Top 10 overlap 7.0, Spearman versus original 0.80.
- T20I bowler: at least 36 pressure legal balls bowled (balls:PR36; data outweighs the prior from about 34); 32 eligible, 136 distinct matches (32% of the 429 chase matches), bootstrap expected Top 10 overlap 6.6, Spearman versus original 0.69.
- Eligible in both formats (batter): 8, fewer than the list size of 10: the combined list is short and is not padded. Single-format lists are reported separately in Stage 6.
- Eligible in both formats (bowler): 6, fewer than the list size of 10: the combined list is short and is not padded. Single-format lists are reported separately in Stage 6.
- These thresholds are a floor at which the player's own pressure data outweighs the empirical-Bayes prior. They are necessary, not sufficient: interval widths and Top 10 membership frequencies above show that individual pressure residuals remain very uncertain at this sample size.

Caveats:

- Selected from population-level quantities only; player scores and rankings were not used.
- Ranking stability is reported, not used to choose.
- Nominal ladder rungs are placeholders scaled for pressure sample sizes, not validated.
- The score is actual minus expected under a FULL_SAMPLE baseline; it is not a pressure score.
- Eligibility is held fixed inside the bootstrap; its own sampling variability is not modelled.

No list of ten is forced: wherever fewer than ten players satisfy a rule the cell is reported as insufficient and none is padded. Fewer than ten players qualify in: both formats batter, both formats bowler; no list is padded there. The expected Top 10 overlap above shows that even a full list of ten would not be stable.


## 9. Reproduce

```
python scripts/run_pressure_eligibility.py
```
Config `pressure_eligibility_rules_v1.json`, seed 20260512, 1000 bootstrap resamples. Official data preservation: unchanged = yes.
