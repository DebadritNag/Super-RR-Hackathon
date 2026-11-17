# Eligibility Threshold Report (Decision 2)

## 1. Interpretation (read first)

Pressure is not defined until Phase 3. Every number in this report is an all-situation descriptive proxy (innings 1 and 2, all match situations), labelled PROXY_NOT_PRESSURE, and is not for publication. The harness is generic and accepts pressure samples unchanged.

Direction of change under pressure samples: a pressure sample is a subset of the all-situation sample, so every player has fewer balls, matches and innings in it. A fixed count threshold will therefore admit fewer players, eligible pools will be smaller, match coverage lower, and bootstrap intervals wider and Top 10 membership less stable than shown here. The figures below are upper bounds in direction only. No pressure-sample numbers are extrapolated.

- proxy_run: true; pressure_status: PENDING_PHASE3; score_label: PROXY_NOT_PRESSURE; not_for_publication: true.
- Seed 20260512, 1000 bootstrap resamples, rules `eligibility_rules_v1`.
- Batter and bowler eligibility are independent. Combined eligibility means eligible in both IPL and T20I.
- Spearman and Top 10 overlap versus neighbours use scores re-estimated inside each eligible pool, because population-level scores would give a trivial Spearman of 1.
- Bootstrap intervals describe shrunk scores. Low-sample players are pulled toward the prior, so their intervals understate uncertainty about true skill and interval width does not fall with the threshold. Width is a diagnostic only.
- Primary recommendation rule: the lowest balls rule at or above the sample size where a player's data outweighs the shrinkage prior (data weight 0.5) and the pool is sufficient. The generic stability checks (Spearman, Top 10 overlap, width plateau) are reported as diagnostics.

## 2. PROVISIONAL recommendation

- PROVISIONAL IPL batter: balls:PR120 (data outweighs the prior from about 107 balls); 129 eligible, match coverage 100.0%, bootstrap expected Top 10 overlap 6.5; the strictest rule with a sufficient pool is balls:P75 (86 eligible); the generic stability checks pass at every step and do not discriminate, so the choice rests on the single data-weight criterion and must be re-confirmed with pressure samples in Phase 3.
- PROVISIONAL IPL bowler: balls:PR192 (data outweighs the prior from about 186 balls); 119 eligible, match coverage 100.0%, bootstrap expected Top 10 overlap 3.9; the strictest rule with a sufficient pool is balls:P75 (65 eligible); the generic stability checks pass at every step and do not discriminate, so the choice rests on the single data-weight criterion and must be re-confirmed with pressure samples in Phase 3; Top 10 membership is unstable under resampling (expected overlap below 5) even though the pool is sufficient.
- PROVISIONAL T20I batter: balls:PR120 (data outweighs the prior from about 87 balls); 205 eligible, match coverage 99.4%, bootstrap expected Top 10 overlap 6.1; the strictest rule with a sufficient pool is balls:PR300 (111 eligible); the generic stability checks pass at every step and do not discriminate, so the choice rests on the single data-weight criterion and must be re-confirmed with pressure samples in Phase 3.
- PROVISIONAL T20I bowler: balls:PR144 (data outweighs the prior from about 138 balls); 191 eligible, match coverage 99.4%, bootstrap expected Top 10 overlap 3.9; the strictest rule with a sufficient pool is balls:P75 (120 eligible); the generic stability checks pass at every step and do not discriminate, so the choice rests on the single data-weight criterion and must be re-confirmed with pressure samples in Phase 3; Top 10 membership is unstable under resampling (expected overlap below 5) even though the pool is sufficient.

These are provisional and rest on all-situation proxies. Pool size, noise and match coverage trade off against each other; the tables in section 4 show how Top 10 stability and interval width change with the threshold. Where a list would have fewer than 10 eligible players it is reported as such and never padded.

## 3. Data window and distributions

| Format | Matches with deliveries | First date | Last date |
|---|---|---|---|
| IPL | 367 | 2022-03-26 | 2026-05-31 |
| OTHER_T20 | 30 | 2024-10-18 | 2025-11-23 |
| T20I | 470 | 2022-01-22 | 2026-11-01 |

Shrinkage prior per format, role and stream (k is the prior strength in the stream's unit; a player's data weight is n/(n+k)):

| Format | Role | Stream | Players | mu0 | sigma2 | tau2 | k |
|---|---|---|---|---|---|---|---|
| IPL | batter | runs | 341 | 1.47 | 3.18 | 0.03 | 106.58 |
| IPL | bowler | econ | 260 | 1.46 | 3.10 | 0.02 | 195.11 |
| IPL | bowler | wkt | 260 | 0.05 | 0.05 | 1.44e-05 | 3157.61 |
| T20I | batter | runs | 665 | 1.34 | 2.87 | 0.03 | 87.25 |
| T20I | bowler | econ | 479 | 1.34 | 2.80 | 0.02 | 143.94 |
| T20I | bowler | wkt | 479 | 0.05 | 0.05 | 4e-06 | 12674.11 |
| OTHER_T20 | batter | runs | 159 | 1.25 | 2.73 | 0.07 | 41.20 |
| OTHER_T20 | bowler | econ | 112 | 1.25 | 2.65 | 0.07 | 35.35 |
| OTHER_T20 | bowler | wkt | 112 | 0.05 | 0.05 | 0.000215 | 227.69 |

### IPL batter: observed players 341

| Measure | n | Mean | Min | p10 | p25 | p50 | p75 | p90 | Max |
|---|---|---|---|---|---|---|---|---|---|
| balls | 341 | 246.69 | 1.00 | 5.00 | 14.00 | 53.00 | 301.00 | 827.00 | 2091.00 |
| matches | 341 | 16.70 | 1.00 | 1.00 | 3.00 | 8.00 | 25.00 | 54.00 | 76.00 |
| innings | 341 | 16.70 | 1.00 | 1.00 | 3.00 | 8.00 | 25.00 | 54.00 | 76.00 |
| n_eff_shrink | 341 | 202.69 | 0.0093 | 0.22 | 1.63 | 17.60 | 222.29 | 732.59 | 1989.59 |
| n_eff_kish | 341 | 10.93 | 1.00 | 1.00 | 1.98 | 4.64 | 15.54 | 33.30 | 53.15 |

Players with at most 5 balls: 45; single-match players: 55 (0.161).

### IPL bowler: observed players 260

| Measure | n | Mean | Min | p10 | p25 | p50 | p75 | p90 | Max |
|---|---|---|---|---|---|---|---|---|---|
| balls | 260 | 322.08 | 1.00 | 18.00 | 36.00 | 162.00 | 452.75 | 962.40 | 1718.00 |
| matches | 260 | 16.67 | 1.00 | 1.00 | 3.00 | 8.00 | 25.00 | 45.00 | 77.00 |
| innings | 260 | 16.67 | 1.00 | 1.00 | 3.00 | 8.00 | 25.00 | 45.00 | 77.00 |
| n_eff_shrink | 260 | 249.85 | 0.0051 | 1.52 | 6.19 | 81.31 | 336.47 | 854.46 | 1581.39 |
| n_eff_kish | 260 | 15.49 | 1.00 | 1.00 | 2.75 | 7.73 | 22.63 | 42.32 | 74.22 |

Players with at most 5 balls: 4; single-match players: 36 (0.138).

### T20I batter: observed players 665

| Measure | n | Mean | Min | p10 | p25 | p50 | p75 | p90 | Max |
|---|---|---|---|---|---|---|---|---|---|
| balls | 665 | 153.98 | 1.00 | 5.00 | 15.00 | 50.00 | 163.00 | 458.20 | 1456.00 |
| matches | 665 | 11.33 | 1.00 | 1.00 | 2.00 | 5.00 | 14.00 | 33.00 | 75.00 |
| innings | 665 | 11.33 | 1.00 | 1.00 | 2.00 | 5.00 | 14.00 | 33.00 | 75.00 |
| n_eff_shrink | 665 | 118.39 | 0.01 | 0.27 | 2.20 | 18.21 | 106.17 | 384.90 | 1373.68 |
| n_eff_kish | 665 | 7.42 | 1.00 | 1.00 | 1.95 | 3.77 | 8.72 | 20.77 | 48.67 |

Players with at most 5 balls: 75; single-match players: 80 (0.120).

### T20I bowler: observed players 479

| Measure | n | Mean | Min | p10 | p25 | p50 | p75 | p90 | Max |
|---|---|---|---|---|---|---|---|---|---|
| balls | 479 | 212.84 | 1.00 | 16.00 | 36.00 | 97.00 | 266.00 | 570.00 | 1627.00 |
| matches | 479 | 11.27 | 1.00 | 1.00 | 2.00 | 6.00 | 15.00 | 29.20 | 75.00 |
| innings | 479 | 11.27 | 1.00 | 1.00 | 2.00 | 6.00 | 15.00 | 29.20 | 75.00 |
| n_eff_shrink | 479 | 159.14 | 0.0069 | 2.00 | 8.31 | 42.30 | 178.75 | 467.56 | 1612.03 |
| n_eff_kish | 479 | 10.40 | 1.00 | 1.00 | 2.00 | 5.00 | 13.17 | 26.95 | 72.12 |

Players with at most 5 balls: 4; single-match players: 69 (0.144).

### OTHER_T20 batter: observed players 159

| Measure | n | Mean | Min | p10 | p25 | p50 | p75 | p90 | Max |
|---|---|---|---|---|---|---|---|---|---|
| balls | 159 | 42.36 | 1.00 | 2.80 | 9.00 | 30.00 | 64.50 | 94.00 | 293.00 |
| matches | 159 | 3.11 | 1.00 | 1.00 | 2.00 | 3.00 | 4.00 | 6.00 | 9.00 |
| innings | 159 | 3.11 | 1.00 | 1.00 | 2.00 | 3.00 | 4.00 | 6.00 | 9.00 |
| n_eff_shrink | 159 | 25.94 | 0.02 | 0.18 | 1.61 | 12.64 | 39.36 | 65.35 | 256.88 |
| n_eff_kish | 159 | 2.35 | 1.00 | 1.00 | 1.18 | 2.00 | 2.84 | 3.96 | 6.92 |

Players with at most 5 balls: 30; single-match players: 38 (0.239).

### OTHER_T20 bowler: observed players 112

| Measure | n | Mean | Min | p10 | p25 | p50 | p75 | p90 | Max |
|---|---|---|---|---|---|---|---|---|---|
| balls | 112 | 60.00 | 2.00 | 12.00 | 24.00 | 54.00 | 78.00 | 119.50 | 192.00 |
| matches | 112 | 3.25 | 1.00 | 1.00 | 2.00 | 3.00 | 4.00 | 6.00 | 8.00 |
| innings | 112 | 3.25 | 1.00 | 1.00 | 2.00 | 3.00 | 4.00 | 6.00 | 8.00 |
| n_eff_shrink | 112 | 42.35 | 0.11 | 4.18 | 10.85 | 33.48 | 59.12 | 93.55 | 169.96 |
| n_eff_kish | 112 | 3.03 | 1.00 | 1.00 | 1.57 | 2.90 | 3.96 | 5.45 | 7.99 |

Players with at most 5 balls: 1; single-match players: 24 (0.214).

## 4. Candidate thresholds and results

### IPL batter

- balls: percentile candidates P10=5, P25=14, P50=53, P75=301.
  - 30 kept: 30 lies at observed percentile 40.5 with 203 of 341 players at or above it (observed p10=5.0, p90=827.0).
  - 60 kept: 60 lies at observed percentile 51.6 with 165 of 341 players at or above it (observed p10=5.0, p90=827.0).
  - 120 kept: 120 lies at observed percentile 62.2 with 129 of 341 players at or above it (observed p10=5.0, p90=827.0).
  - 180 kept: 180 lies at observed percentile 67.7 with 110 of 341 players at or above it (observed p10=5.0, p90=827.0).
  - 240 kept: 240 lies at observed percentile 71.6 with 97 of 341 players at or above it (observed p10=5.0, p90=827.0).
  - 300 dropped (within_5pct_of_P75): 300 lies at observed percentile 74.8 with 86 of 341 players at or above it (observed p10=5.0, p90=827.0).
- matches: percentile candidates P10=1, P25=3, P50=8, P75=25.
  - 3 dropped (within_5pct_of_P25): 3 lies at observed percentile 24.0 with 259 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 5 kept: 5 lies at observed percentile 37.8 with 212 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 8 dropped (within_5pct_of_P50): 8 lies at observed percentile 49.0 with 174 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 10 kept: 10 lies at observed percentile 53.4 with 159 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 15 kept: 15 lies at observed percentile 65.4 with 118 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 20 kept: 20 lies at observed percentile 71.3 with 98 of 341 players at or above it (observed p10=1.0, p90=54.0).
- innings: percentile candidates P10=1, P25=3, P50=8, P75=25.
  - 3 dropped (within_5pct_of_P25): 3 lies at observed percentile 24.0 with 259 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 5 kept: 5 lies at observed percentile 37.8 with 212 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 8 dropped (within_5pct_of_P50): 8 lies at observed percentile 49.0 with 174 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 10 kept: 10 lies at observed percentile 53.4 with 159 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 15 kept: 15 lies at observed percentile 65.4 with 118 of 341 players at or above it (observed p10=1.0, p90=54.0).
  - 20 kept: 20 lies at observed percentile 71.3 with 98 of 341 players at or above it (observed p10=1.0, p90=54.0).
- n_eff_shrink: percentile candidates P10=1, P25=2, P50=18, P75=223.
  - 20 kept: 20 lies at observed percentile 51.3 with 166 of 341 players at or above it (observed p10=0.2, p90=732.6).
  - 40 kept: 40 lies at observed percentile 56.6 with 148 of 341 players at or above it (observed p10=0.2, p90=732.6).
  - 80 kept: 80 lies at observed percentile 63.9 with 123 of 341 players at or above it (observed p10=0.2, p90=732.6).
  - 120 kept: 120 lies at observed percentile 68.0 with 109 of 341 players at or above it (observed p10=0.2, p90=732.6).
- n_eff_kish: percentile candidates P10=1, P25=2, P50=5, P75=16.

#### IPL batter: balls (batter balls faced / bowler legal balls)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | balls>=5 | 307 | 367 | 100.00 | 72.00 | 10 | 1.00 | 10 | 1.00 | 28.84 | 0.63 | 0.81 | SUFFICIENT |
| P25 | balls>=14 | 257 | 367 | 100.00 | 120.00 | 10 | 1.00 | 10 | 1.00 | 30.49 | 0.63 | 0.83 | SUFFICIENT |
| PR30 | balls>=30 | 203 | 367 | 100.00 | 216.00 | 10 | 1.00 | 10 | 1.00 | 30.84 | 0.63 | 0.84 | SUFFICIENT |
| P50 | balls>=53 | 171 | 367 | 100.00 | 301.00 | 10 | 1.00 | 10 | 1.00 | 30.33 | 0.63 | 0.86 | SUFFICIENT |
| PR60 | balls>=60 | 165 | 367 | 100.00 | 334.00 | 9 | 1.00 | 10 | 1.00 | 30.05 | 0.64 | 0.86 | SUFFICIENT |
| PR120 | balls>=120 | 129 | 367 | 100.00 | 471.00 | 9 | 1.00 | 9 | 1.00 | 28.81 | 0.65 | 0.85 | SUFFICIENT |
| PR180 | balls>=180 | 110 | 367 | 100.00 | 560.00 | 9 | 1.00 | 8 | 1.00 | 27.98 | 0.64 | 0.85 | SUFFICIENT |
| PR240 | balls>=240 | 97 | 367 | 100.00 | 647.00 | 9 | 1.00 | 7 | 1.00 | 27.19 | 0.67 | 0.86 | SUFFICIENT |
| P75 | balls>=301 | 86 | 367 | 100.00 | 712.00 | n/a | n/a | 6 | 1.00 | 25.28 | 0.68 | 0.86 | SUFFICIENT |

#### IPL batter: distinct matches

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | matches>=1 | 341 | 367 | 100.00 | 53.00 | 10 | 1.00 | 10 | 1.00 | 27.47 | 0.63 | 0.81 | SUFFICIENT |
| P25 | matches>=3 | 259 | 367 | 100.00 | 118.00 | 10 | 1.00 | 10 | 1.00 | 30.22 | 0.63 | 0.83 | SUFFICIENT |
| PR5 | matches>=5 | 212 | 367 | 100.00 | 194.50 | 10 | 1.00 | 10 | 1.00 | 30.83 | 0.63 | 0.85 | SUFFICIENT |
| P50 | matches>=8 | 174 | 367 | 100.00 | 291.50 | 10 | 1.00 | 10 | 1.00 | 30.89 | 0.64 | 0.86 | SUFFICIENT |
| PR10 | matches>=10 | 159 | 367 | 100.00 | 379.00 | 7 | 1.00 | 10 | 1.00 | 30.81 | 0.64 | 0.87 | SUFFICIENT |
| PR15 | matches>=15 | 118 | 367 | 100.00 | 517.50 | 8 | 1.00 | 7 | 1.00 | 29.30 | 0.62 | 0.87 | SUFFICIENT |
| PR20 | matches>=20 | 98 | 367 | 100.00 | 646.50 | 9 | 1.00 | 6 | 1.00 | 27.34 | 0.66 | 0.87 | SUFFICIENT |
| P75 | matches>=25 | 86 | 367 | 100.00 | 712.00 | n/a | n/a | 5 | 1.00 | 25.28 | 0.66 | 0.86 | SUFFICIENT |

#### IPL batter: innings batted / bowled in

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | innings>=1 | 341 | 367 | 100.00 | 53.00 | 10 | 1.00 | 10 | 1.00 | 27.47 | 0.63 | 0.81 | SUFFICIENT |
| P25 | innings>=3 | 259 | 367 | 100.00 | 118.00 | 10 | 1.00 | 10 | 1.00 | 30.22 | 0.63 | 0.83 | SUFFICIENT |
| PR5 | innings>=5 | 212 | 367 | 100.00 | 194.50 | 10 | 1.00 | 10 | 1.00 | 30.83 | 0.63 | 0.85 | SUFFICIENT |
| P50 | innings>=8 | 174 | 367 | 100.00 | 291.50 | 10 | 1.00 | 10 | 1.00 | 30.89 | 0.64 | 0.86 | SUFFICIENT |
| PR10 | innings>=10 | 159 | 367 | 100.00 | 379.00 | 7 | 1.00 | 10 | 1.00 | 30.81 | 0.64 | 0.87 | SUFFICIENT |
| PR15 | innings>=15 | 118 | 367 | 100.00 | 517.50 | 8 | 1.00 | 7 | 1.00 | 29.30 | 0.62 | 0.87 | SUFFICIENT |
| PR20 | innings>=20 | 98 | 367 | 100.00 | 646.50 | 9 | 1.00 | 6 | 1.00 | 27.34 | 0.66 | 0.87 | SUFFICIENT |
| P75 | innings>=25 | 86 | 367 | 100.00 | 712.00 | n/a | n/a | 5 | 1.00 | 25.28 | 0.66 | 0.86 | SUFFICIENT |

#### IPL batter: effective sample size (shrinkage)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | n_eff_shrink>=1 | 268 | 367 | 100.00 | 104.50 | 10 | 1.00 | 10 | 1.00 | 30.35 | 0.63 | 0.82 | SUFFICIENT |
| P25 | n_eff_shrink>=2 | 246 | 367 | 100.00 | 140.50 | 10 | 1.00 | 10 | 1.00 | 30.67 | 0.63 | 0.83 | SUFFICIENT |
| P50 | n_eff_shrink>=18 | 170 | 367 | 100.00 | 305.50 | 10 | 1.00 | 10 | 1.00 | 30.35 | 0.63 | 0.86 | SUFFICIENT |
| PR20 | n_eff_shrink>=20 | 166 | 367 | 100.00 | 324.00 | 10 | 1.00 | 10 | 1.00 | 30.07 | 0.64 | 0.86 | SUFFICIENT |
| PR40 | n_eff_shrink>=40 | 148 | 367 | 100.00 | 412.50 | 9 | 1.00 | 10 | 1.00 | 29.83 | 0.64 | 0.86 | SUFFICIENT |
| PR80 | n_eff_shrink>=80 | 123 | 367 | 100.00 | 497.00 | 9 | 1.00 | 9 | 1.00 | 28.79 | 0.65 | 0.85 | SUFFICIENT |
| PR120 | n_eff_shrink>=120 | 109 | 367 | 100.00 | 560.00 | 8 | 1.00 | 8 | 1.00 | 27.89 | 0.64 | 0.85 | SUFFICIENT |
| P75 | n_eff_shrink>=223 | 85 | 367 | 100.00 | 721.00 | n/a | n/a | 6 | 1.00 | 24.96 | 0.68 | 0.86 | SUFFICIENT |

#### IPL batter: effective number of matches (Kish)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | n_eff_kish>=1 | 341 | 367 | 100.00 | 53.00 | 10 | 1.00 | 10 | 1.00 | 27.47 | 0.63 | 0.81 | SUFFICIENT |
| P25 | n_eff_kish>=2 | 255 | 367 | 100.00 | 122.00 | 10 | 1.00 | 10 | 1.00 | 30.33 | 0.63 | 0.83 | SUFFICIENT |
| P50 | n_eff_kish>=5 | 168 | 367 | 100.00 | 312.00 | 6 | 1.00 | 10 | 1.00 | 30.67 | 0.64 | 0.86 | SUFFICIENT |
| P75 | n_eff_kish>=16 | 84 | 367 | 100.00 | 723.50 | n/a | n/a | 6 | 1.00 | 25.28 | 0.69 | 0.85 | SUFFICIENT |

#### IPL batter: balls AND matches

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PR30&PR5 | balls>=30 AND matches>=5 | 192 | 367 | 100.00 | 242.00 | 10 | 1.00 | 10 | 1.00 | 30.83 | 0.63 | 0.85 | SUFFICIENT |
| PR60&PR5 | balls>=60 AND matches>=5 | 165 | 367 | 100.00 | 334.00 | 9 | 1.00 | 10 | 1.00 | 30.05 | 0.64 | 0.86 | SUFFICIENT |
| PR30&PR15 | balls>=30 AND matches>=15 | 118 | 367 | 100.00 | 517.50 | 10 | 1.00 | 7 | 1.00 | 29.30 | 0.62 | 0.87 | SUFFICIENT |
| PR120&PR5 | balls>=120 AND matches>=5 | 129 | 367 | 100.00 | 471.00 | 8 | 1.00 | 9 | 1.00 | 28.81 | 0.65 | 0.85 | SUFFICIENT |
| PR60&PR15 | balls>=60 AND matches>=15 | 116 | 367 | 100.00 | 526.50 | 9 | 1.00 | 7 | 1.00 | 29.02 | 0.62 | 0.87 | SUFFICIENT |
| PR180&PR5 | balls>=180 AND matches>=5 | 110 | 367 | 100.00 | 560.00 | 10 | 1.00 | 8 | 1.00 | 27.98 | 0.64 | 0.85 | SUFFICIENT |
| PR60&PR20 | balls>=60 AND matches>=20 | 98 | 367 | 100.00 | 646.50 | 10 | 1.00 | 6 | 1.00 | 27.34 | 0.66 | 0.87 | SUFFICIENT |
| PR180&PR10 | balls>=180 AND matches>=10 | 109 | 367 | 100.00 | 560.00 | 8 | 1.00 | 8 | 1.00 | 27.89 | 0.64 | 0.85 | SUFFICIENT |
| PR120&PR20 | balls>=120 AND matches>=20 | 97 | 367 | 100.00 | 647.00 | 9 | 1.00 | 6 | 1.00 | 27.32 | 0.66 | 0.86 | SUFFICIENT |
| PR240&PR10 | balls>=240 AND matches>=10 | 97 | 367 | 100.00 | 647.00 | 9 | 1.00 | 7 | 1.00 | 27.19 | 0.67 | 0.86 | SUFFICIENT |
| PR180&PR20 | balls>=180 AND matches>=20 | 93 | 367 | 100.00 | 656.00 | 10 | 1.00 | 6 | 1.00 | 27.19 | 0.66 | 0.85 | SUFFICIENT |
| PR240&PR20 | balls>=240 AND matches>=20 | 87 | 367 | 100.00 | 703.00 | n/a | n/a | 6 | 1.00 | 25.60 | 0.69 | 0.86 | SUFFICIENT |

Recommendation inputs (IPL batter, primary family): lowest stable rule balls:P10, strictest sufficient pool balls:P75.

### IPL bowler

- balls: percentile candidates P10=18, P25=36, P50=162, P75=453.
  - 24 kept: 24 lies at observed percentile 14.2 with 223 of 260 players at or above it (observed p10=18.0, p90=962.4).
  - 48 kept: 48 lies at observed percentile 29.2 with 184 of 260 players at or above it (observed p10=18.0, p90=962.4).
  - 96 kept: 96 lies at observed percentile 41.2 with 153 of 260 players at or above it (observed p10=18.0, p90=962.4).
  - 144 kept: 144 lies at observed percentile 47.3 with 137 of 260 players at or above it (observed p10=18.0, p90=962.4).
  - 192 kept: 192 lies at observed percentile 54.2 with 119 of 260 players at or above it (observed p10=18.0, p90=962.4).
  - 240 kept: 240 lies at observed percentile 60.4 with 103 of 260 players at or above it (observed p10=18.0, p90=962.4).
- matches: percentile candidates P10=1, P25=3, P50=8, P75=25.
  - 3 dropped (within_5pct_of_P25): 3 lies at observed percentile 23.8 with 198 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 5 kept: 5 lies at observed percentile 32.7 with 175 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 8 dropped (within_5pct_of_P50): 8 lies at observed percentile 45.8 with 141 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 10 kept: 10 lies at observed percentile 51.9 with 125 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 15 kept: 15 lies at observed percentile 64.2 with 93 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 20 kept: 20 lies at observed percentile 68.5 with 82 of 260 players at or above it (observed p10=1.0, p90=45.0).
- innings: percentile candidates P10=1, P25=3, P50=8, P75=25.
  - 3 dropped (within_5pct_of_P25): 3 lies at observed percentile 23.8 with 198 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 5 kept: 5 lies at observed percentile 32.7 with 175 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 8 dropped (within_5pct_of_P50): 8 lies at observed percentile 45.8 with 141 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 10 kept: 10 lies at observed percentile 51.9 with 125 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 15 kept: 15 lies at observed percentile 64.2 with 93 of 260 players at or above it (observed p10=1.0, p90=45.0).
  - 20 kept: 20 lies at observed percentile 68.5 with 82 of 260 players at or above it (observed p10=1.0, p90=45.0).
- n_eff_shrink: percentile candidates P10=2, P25=7, P50=82, P75=337.
  - 20 kept: 20 lies at observed percentile 36.5 with 165 of 260 players at or above it (observed p10=1.5, p90=854.5).
  - 40 kept: 40 lies at observed percentile 43.5 with 147 of 260 players at or above it (observed p10=1.5, p90=854.5).
  - 80 dropped (within_5pct_of_P50): 80 lies at observed percentile 50.0 with 130 of 260 players at or above it (observed p10=1.5, p90=854.5).
  - 120 kept: 120 lies at observed percentile 57.3 with 111 of 260 players at or above it (observed p10=1.5, p90=854.5).
- n_eff_kish: percentile candidates P10=1, P25=3, P50=8, P75=23.

#### IPL bowler: balls (batter balls faced / bowler legal balls)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | balls>=18 | 236 | 367 | 100.00 | 195.00 | 10 | 1.00 | 10 | 1.00 | 3.82 | 0.32 | 0.71 | SUFFICIENT |
| PR24 | balls>=24 | 223 | 367 | 100.00 | 206.00 | 10 | 1.00 | 10 | 1.00 | 3.87 | 0.32 | 0.71 | SUFFICIENT |
| P25 | balls>=36 | 202 | 367 | 100.00 | 241.00 | 9 | 1.00 | 10 | 1.00 | 3.99 | 0.32 | 0.71 | SUFFICIENT |
| PR48 | balls>=48 | 184 | 367 | 100.00 | 275.50 | 9 | 1.00 | 9 | 1.00 | 4.04 | 0.33 | 0.72 | SUFFICIENT |
| PR96 | balls>=96 | 153 | 367 | 100.00 | 376.00 | 10 | 1.00 | 10 | 1.00 | 4.15 | 0.34 | 0.72 | SUFFICIENT |
| PR144 | balls>=144 | 137 | 367 | 100.00 | 424.00 | 10 | 1.00 | 10 | 1.00 | 4.21 | 0.36 | 0.72 | SUFFICIENT |
| P50 | balls>=162 | 130 | 367 | 100.00 | 456.50 | 10 | 1.00 | 10 | 1.00 | 4.20 | 0.37 | 0.73 | SUFFICIENT |
| PR192 | balls>=192 | 119 | 367 | 100.00 | 491.00 | 10 | 1.00 | 10 | 1.00 | 4.21 | 0.39 | 0.74 | SUFFICIENT |
| PR240 | balls>=240 | 103 | 367 | 100.00 | 571.00 | 9 | 1.00 | 10 | 1.00 | 4.20 | 0.41 | 0.73 | SUFFICIENT |
| P75 | balls>=453 | 65 | 367 | 100.00 | 866.00 | n/a | n/a | 9 | 0.99 | 3.91 | 0.47 | 0.73 | SUFFICIENT |

#### IPL bowler: distinct matches

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | matches>=1 | 260 | 367 | 100.00 | 162.00 | 9 | 1.00 | 10 | 1.00 | 3.72 | 0.32 | 0.70 | SUFFICIENT |
| P25 | matches>=3 | 198 | 367 | 100.00 | 249.00 | 9 | 1.00 | 9 | 1.00 | 4.01 | 0.32 | 0.72 | SUFFICIENT |
| PR5 | matches>=5 | 175 | 367 | 100.00 | 296.00 | 10 | 1.00 | 10 | 1.00 | 4.13 | 0.34 | 0.72 | SUFFICIENT |
| P50 | matches>=8 | 141 | 367 | 100.00 | 421.00 | 10 | 1.00 | 10 | 1.00 | 4.15 | 0.36 | 0.73 | SUFFICIENT |
| PR10 | matches>=10 | 125 | 367 | 100.00 | 467.00 | 10 | 1.00 | 10 | 1.00 | 4.20 | 0.38 | 0.73 | SUFFICIENT |
| PR15 | matches>=15 | 93 | 367 | 100.00 | 610.00 | 10 | 1.00 | 10 | 1.00 | 4.05 | 0.44 | 0.74 | SUFFICIENT |
| PR20 | matches>=20 | 82 | 367 | 100.00 | 660.50 | 10 | 1.00 | 10 | 1.00 | 4.02 | 0.46 | 0.76 | SUFFICIENT |
| P75 | matches>=25 | 67 | 367 | 100.00 | 824.00 | n/a | n/a | 10 | 1.00 | 3.91 | 0.50 | 0.77 | SUFFICIENT |

#### IPL bowler: innings batted / bowled in

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | innings>=1 | 260 | 367 | 100.00 | 162.00 | 9 | 1.00 | 10 | 1.00 | 3.72 | 0.32 | 0.70 | SUFFICIENT |
| P25 | innings>=3 | 198 | 367 | 100.00 | 249.00 | 9 | 1.00 | 9 | 1.00 | 4.01 | 0.32 | 0.72 | SUFFICIENT |
| PR5 | innings>=5 | 175 | 367 | 100.00 | 296.00 | 10 | 1.00 | 10 | 1.00 | 4.13 | 0.34 | 0.72 | SUFFICIENT |
| P50 | innings>=8 | 141 | 367 | 100.00 | 421.00 | 10 | 1.00 | 10 | 1.00 | 4.15 | 0.36 | 0.73 | SUFFICIENT |
| PR10 | innings>=10 | 125 | 367 | 100.00 | 467.00 | 10 | 1.00 | 10 | 1.00 | 4.20 | 0.38 | 0.73 | SUFFICIENT |
| PR15 | innings>=15 | 93 | 367 | 100.00 | 610.00 | 10 | 1.00 | 10 | 1.00 | 4.05 | 0.44 | 0.74 | SUFFICIENT |
| PR20 | innings>=20 | 82 | 367 | 100.00 | 660.50 | 10 | 1.00 | 10 | 1.00 | 4.02 | 0.46 | 0.76 | SUFFICIENT |
| P75 | innings>=25 | 67 | 367 | 100.00 | 824.00 | n/a | n/a | 10 | 1.00 | 3.91 | 0.50 | 0.77 | SUFFICIENT |

#### IPL bowler: effective sample size (shrinkage)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | n_eff_shrink>=2 | 228 | 367 | 100.00 | 204.00 | 10 | 1.00 | 10 | 1.00 | 3.84 | 0.32 | 0.71 | SUFFICIENT |
| P25 | n_eff_shrink>=7 | 194 | 367 | 100.00 | 252.00 | 10 | 1.00 | 10 | 1.00 | 4.01 | 0.32 | 0.72 | SUFFICIENT |
| PR20 | n_eff_shrink>=20 | 165 | 367 | 100.00 | 325.00 | 10 | 1.00 | 10 | 1.00 | 4.13 | 0.34 | 0.72 | SUFFICIENT |
| PR40 | n_eff_shrink>=40 | 147 | 367 | 100.00 | 387.00 | 10 | 1.00 | 10 | 1.00 | 4.15 | 0.35 | 0.72 | SUFFICIENT |
| P50 | n_eff_shrink>=82 | 130 | 367 | 100.00 | 456.50 | 10 | 1.00 | 10 | 1.00 | 4.20 | 0.37 | 0.73 | SUFFICIENT |
| PR120 | n_eff_shrink>=120 | 111 | 367 | 100.00 | 535.00 | 9 | 1.00 | 10 | 1.00 | 4.20 | 0.39 | 0.74 | SUFFICIENT |
| P75 | n_eff_shrink>=337 | 65 | 367 | 100.00 | 866.00 | n/a | n/a | 9 | 1.00 | 3.91 | 0.47 | 0.73 | SUFFICIENT |

#### IPL bowler: effective number of matches (Kish)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | n_eff_kish>=1 | 260 | 367 | 100.00 | 162.00 | 9 | 1.00 | 10 | 1.00 | 3.72 | 0.32 | 0.70 | SUFFICIENT |
| P25 | n_eff_kish>=3 | 188 | 367 | 100.00 | 267.00 | 9 | 1.00 | 9 | 1.00 | 4.02 | 0.33 | 0.72 | SUFFICIENT |
| P50 | n_eff_kish>=8 | 126 | 367 | 100.00 | 466.00 | 10 | 1.00 | 10 | 1.00 | 4.16 | 0.38 | 0.73 | SUFFICIENT |
| P75 | n_eff_kish>=23 | 62 | 367 | 100.00 | 873.50 | n/a | n/a | 10 | 0.99 | 3.89 | 0.50 | 0.74 | SUFFICIENT |

#### IPL bowler: balls AND matches

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PR24&PR5 | balls>=24 AND matches>=5 | 175 | 367 | 100.00 | 296.00 | 10 | 1.00 | 10 | 1.00 | 4.13 | 0.34 | 0.72 | SUFFICIENT |
| PR48&PR5 | balls>=48 AND matches>=5 | 169 | 367 | 100.00 | 312.00 | 10 | 1.00 | 10 | 1.00 | 4.13 | 0.34 | 0.72 | SUFFICIENT |
| PR48&PR10 | balls>=48 AND matches>=10 | 125 | 367 | 100.00 | 467.00 | 10 | 1.00 | 10 | 1.00 | 4.20 | 0.38 | 0.73 | SUFFICIENT |
| PR24&PR20 | balls>=24 AND matches>=20 | 82 | 367 | 100.00 | 660.50 | 10 | 1.00 | 10 | 1.00 | 4.02 | 0.46 | 0.76 | SUFFICIENT |
| PR96&PR10 | balls>=96 AND matches>=10 | 125 | 367 | 100.00 | 467.00 | 10 | 1.00 | 10 | 1.00 | 4.20 | 0.38 | 0.73 | SUFFICIENT |
| PR48&PR20 | balls>=48 AND matches>=20 | 82 | 367 | 100.00 | 660.50 | 10 | 1.00 | 10 | 1.00 | 4.02 | 0.46 | 0.76 | SUFFICIENT |
| PR192&PR5 | balls>=192 AND matches>=5 | 119 | 367 | 100.00 | 491.00 | 10 | 1.00 | 10 | 1.00 | 4.21 | 0.39 | 0.74 | SUFFICIENT |
| PR144&PR15 | balls>=144 AND matches>=15 | 93 | 367 | 100.00 | 610.00 | 10 | 1.00 | 10 | 1.00 | 4.05 | 0.44 | 0.74 | SUFFICIENT |
| PR240&PR5 | balls>=240 AND matches>=5 | 103 | 367 | 100.00 | 571.00 | 10 | 1.00 | 10 | 1.00 | 4.20 | 0.41 | 0.73 | SUFFICIENT |
| PR192&PR15 | balls>=192 AND matches>=15 | 91 | 367 | 100.00 | 611.00 | 10 | 1.00 | 10 | 1.00 | 4.05 | 0.44 | 0.75 | SUFFICIENT |
| PR192&PR20 | balls>=192 AND matches>=20 | 82 | 367 | 100.00 | 660.50 | 10 | 1.00 | 10 | 1.00 | 4.02 | 0.46 | 0.76 | SUFFICIENT |
| PR240&PR20 | balls>=240 AND matches>=20 | 80 | 367 | 100.00 | 688.50 | n/a | n/a | 10 | 1.00 | 4.03 | 0.46 | 0.75 | SUFFICIENT |

Recommendation inputs (IPL bowler, primary family): lowest stable rule balls:P10, strictest sufficient pool balls:P75.

### T20I batter

- balls: percentile candidates P10=5, P25=15, P50=50, P75=163.
  - 30 kept: 30 lies at observed percentile 37.6 with 415 of 665 players at or above it (observed p10=5.0, p90=458.2).
  - 60 kept: 60 lies at observed percentile 55.0 with 299 of 665 players at or above it (observed p10=5.0, p90=458.2).
  - 120 kept: 120 lies at observed percentile 69.2 with 205 of 665 players at or above it (observed p10=5.0, p90=458.2).
  - 180 kept: 180 lies at observed percentile 76.5 with 156 of 665 players at or above it (observed p10=5.0, p90=458.2).
  - 240 kept: 240 lies at observed percentile 80.3 with 131 of 665 players at or above it (observed p10=5.0, p90=458.2).
  - 300 kept: 300 lies at observed percentile 83.3 with 111 of 665 players at or above it (observed p10=5.0, p90=458.2).
- matches: percentile candidates P10=1, P25=2, P50=5, P75=14.
  - 3 kept: 3 lies at observed percentile 27.1 with 485 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 5 dropped (within_5pct_of_P50): 5 lies at observed percentile 43.8 with 374 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 8 kept: 8 lies at observed percentile 58.8 with 274 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 10 kept: 10 lies at observed percentile 65.7 with 228 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 15 kept: 15 lies at observed percentile 75.9 with 160 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 20 kept: 20 lies at observed percentile 81.1 with 126 of 665 players at or above it (observed p10=1.0, p90=33.0).
- innings: percentile candidates P10=1, P25=2, P50=5, P75=14.
  - 3 kept: 3 lies at observed percentile 27.1 with 485 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 5 dropped (within_5pct_of_P50): 5 lies at observed percentile 43.8 with 374 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 8 kept: 8 lies at observed percentile 58.8 with 274 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 10 kept: 10 lies at observed percentile 65.7 with 228 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 15 kept: 15 lies at observed percentile 75.9 with 160 of 665 players at or above it (observed p10=1.0, p90=33.0).
  - 20 kept: 20 lies at observed percentile 81.1 with 126 of 665 players at or above it (observed p10=1.0, p90=33.0).
- n_eff_shrink: percentile candidates P10=1, P25=3, P50=19, P75=107.
  - 20 kept: 20 lies at observed percentile 52.0 with 319 of 665 players at or above it (observed p10=0.3, p90=384.9).
  - 40 kept: 40 lies at observed percentile 62.4 with 250 of 665 players at or above it (observed p10=0.3, p90=384.9).
  - 80 kept: 80 lies at observed percentile 70.5 with 196 of 665 players at or above it (observed p10=0.3, p90=384.9).
  - 120 kept: 120 lies at observed percentile 76.5 with 156 of 665 players at or above it (observed p10=0.3, p90=384.9).
- n_eff_kish: percentile candidates P10=1, P25=2, P50=4, P75=9.

#### T20I batter: balls (batter balls faced / bowler legal balls)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | balls>=5 | 605 | 470 | 100.00 | 59.00 | 10 | 1.00 | 10 | 1.00 | 30.45 | 0.55 | 0.79 | SUFFICIENT |
| P25 | balls>=15 | 506 | 470 | 100.00 | 81.50 | 10 | 1.00 | 10 | 1.00 | 32.28 | 0.56 | 0.80 | SUFFICIENT |
| PR30 | balls>=30 | 415 | 470 | 100.00 | 117.00 | 10 | 1.00 | 10 | 1.00 | 33.37 | 0.57 | 0.81 | SUFFICIENT |
| P50 | balls>=50 | 333 | 470 | 100.00 | 163.00 | 10 | 1.00 | 10 | 1.00 | 33.13 | 0.57 | 0.83 | SUFFICIENT |
| PR60 | balls>=60 | 299 | 470 | 100.00 | 198.00 | 9 | 1.00 | 10 | 1.00 | 33.14 | 0.58 | 0.83 | SUFFICIENT |
| PR120 | balls>=120 | 205 | 467 | 99.36 | 327.00 | 8 | 1.00 | 9 | 1.00 | 32.16 | 0.61 | 0.84 | SUFFICIENT |
| P75 | balls>=163 | 169 | 466 | 99.15 | 394.00 | 9 | 1.00 | 7 | 1.00 | 30.80 | 0.62 | 0.85 | SUFFICIENT |
| PR180 | balls>=180 | 156 | 466 | 99.15 | 409.00 | 10 | 1.00 | 6 | 1.00 | 30.57 | 0.60 | 0.85 | SUFFICIENT |
| PR240 | balls>=240 | 131 | 458 | 97.45 | 470.00 | 10 | 1.00 | 6 | 1.00 | 30.04 | 0.64 | 0.85 | SUFFICIENT |
| PR300 | balls>=300 | 111 | 458 | 97.45 | 517.00 | n/a | n/a | 6 | 1.00 | 29.85 | 0.65 | 0.85 | SUFFICIENT |

#### T20I batter: distinct matches

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | matches>=1 | 665 | 470 | 100.00 | 50.00 | 10 | 1.00 | 10 | 1.00 | 29.40 | 0.55 | 0.78 | SUFFICIENT |
| P25 | matches>=2 | 585 | 470 | 100.00 | 62.00 | 10 | 1.00 | 10 | 1.00 | 30.73 | 0.55 | 0.79 | SUFFICIENT |
| PR3 | matches>=3 | 485 | 470 | 100.00 | 89.00 | 10 | 1.00 | 10 | 1.00 | 32.25 | 0.56 | 0.81 | SUFFICIENT |
| P50 | matches>=5 | 374 | 467 | 99.36 | 140.50 | 10 | 1.00 | 10 | 1.00 | 33.41 | 0.58 | 0.82 | SUFFICIENT |
| PR8 | matches>=8 | 274 | 467 | 99.36 | 221.50 | 7 | 1.00 | 10 | 1.00 | 33.59 | 0.62 | 0.83 | SUFFICIENT |
| PR10 | matches>=10 | 228 | 464 | 98.72 | 291.00 | 9 | 1.00 | 7 | 1.00 | 32.57 | 0.58 | 0.84 | SUFFICIENT |
| P75 | matches>=14 | 169 | 458 | 97.45 | 394.00 | 10 | 1.00 | 6 | 1.00 | 31.93 | 0.60 | 0.85 | SUFFICIENT |
| PR15 | matches>=15 | 160 | 458 | 97.45 | 406.00 | 10 | 1.00 | 6 | 1.00 | 31.59 | 0.62 | 0.86 | SUFFICIENT |
| PR20 | matches>=20 | 126 | 458 | 97.45 | 495.00 | n/a | n/a | 6 | 1.00 | 30.25 | 0.65 | 0.86 | SUFFICIENT |

#### T20I batter: innings batted / bowled in

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | innings>=1 | 665 | 470 | 100.00 | 50.00 | 10 | 1.00 | 10 | 1.00 | 29.40 | 0.55 | 0.78 | SUFFICIENT |
| P25 | innings>=2 | 585 | 470 | 100.00 | 62.00 | 10 | 1.00 | 10 | 1.00 | 30.73 | 0.55 | 0.79 | SUFFICIENT |
| PR3 | innings>=3 | 485 | 470 | 100.00 | 89.00 | 10 | 1.00 | 10 | 1.00 | 32.25 | 0.56 | 0.81 | SUFFICIENT |
| P50 | innings>=5 | 374 | 467 | 99.36 | 140.50 | 10 | 1.00 | 10 | 1.00 | 33.41 | 0.58 | 0.82 | SUFFICIENT |
| PR8 | innings>=8 | 274 | 467 | 99.36 | 221.50 | 7 | 1.00 | 10 | 1.00 | 33.59 | 0.62 | 0.83 | SUFFICIENT |
| PR10 | innings>=10 | 228 | 464 | 98.72 | 291.00 | 9 | 1.00 | 7 | 1.00 | 32.57 | 0.58 | 0.84 | SUFFICIENT |
| P75 | innings>=14 | 169 | 458 | 97.45 | 394.00 | 10 | 1.00 | 6 | 1.00 | 31.93 | 0.60 | 0.85 | SUFFICIENT |
| PR15 | innings>=15 | 160 | 458 | 97.45 | 406.00 | 10 | 1.00 | 6 | 1.00 | 31.59 | 0.62 | 0.86 | SUFFICIENT |
| PR20 | innings>=20 | 126 | 458 | 97.45 | 495.00 | n/a | n/a | 6 | 1.00 | 30.25 | 0.65 | 0.86 | SUFFICIENT |

#### T20I batter: effective sample size (shrinkage)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | n_eff_shrink>=1 | 543 | 470 | 100.00 | 71.00 | 10 | 1.00 | 10 | 1.00 | 31.87 | 0.56 | 0.80 | SUFFICIENT |
| P25 | n_eff_shrink>=3 | 485 | 470 | 100.00 | 89.00 | 10 | 1.00 | 10 | 1.00 | 32.78 | 0.56 | 0.81 | SUFFICIENT |
| P50 | n_eff_shrink>=19 | 324 | 470 | 100.00 | 167.00 | 10 | 1.00 | 10 | 1.00 | 33.17 | 0.57 | 0.83 | SUFFICIENT |
| PR20 | n_eff_shrink>=20 | 319 | 470 | 100.00 | 176.00 | 9 | 1.00 | 10 | 1.00 | 33.20 | 0.57 | 0.83 | SUFFICIENT |
| PR40 | n_eff_shrink>=40 | 250 | 469 | 99.79 | 262.50 | 9 | 1.00 | 9 | 1.00 | 32.57 | 0.60 | 0.84 | SUFFICIENT |
| PR80 | n_eff_shrink>=80 | 196 | 467 | 99.36 | 340.00 | 8 | 1.00 | 8 | 1.00 | 31.90 | 0.62 | 0.85 | SUFFICIENT |
| P75 | n_eff_shrink>=107 | 165 | 466 | 99.15 | 396.00 | 10 | 1.00 | 6 | 1.00 | 30.80 | 0.60 | 0.85 | SUFFICIENT |
| PR120 | n_eff_shrink>=120 | 156 | 466 | 99.15 | 409.00 | n/a | n/a | 6 | 1.00 | 30.57 | 0.60 | 0.85 | SUFFICIENT |

#### T20I batter: effective number of matches (Kish)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | n_eff_kish>=1 | 665 | 470 | 100.00 | 50.00 | 10 | 1.00 | 10 | 1.00 | 29.40 | 0.55 | 0.78 | SUFFICIENT |
| P25 | n_eff_kish>=2 | 475 | 470 | 100.00 | 92.00 | 10 | 1.00 | 10 | 1.00 | 32.12 | 0.56 | 0.81 | SUFFICIENT |
| P50 | n_eff_kish>=4 | 315 | 467 | 99.36 | 176.00 | 7 | 1.00 | 10 | 1.00 | 33.72 | 0.60 | 0.83 | SUFFICIENT |
| P75 | n_eff_kish>=9 | 160 | 458 | 97.45 | 406.00 | n/a | n/a | 7 | 1.00 | 31.73 | 0.64 | 0.86 | SUFFICIENT |

#### T20I batter: balls AND matches

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PR30&PR3 | balls>=30 AND matches>=3 | 401 | 470 | 100.00 | 125.00 | 7 | 1.00 | 10 | 1.00 | 33.32 | 0.57 | 0.82 | SUFFICIENT |
| PR30&PR10 | balls>=30 AND matches>=10 | 228 | 464 | 98.72 | 291.00 | 8 | 1.00 | 7 | 1.00 | 32.57 | 0.58 | 0.84 | SUFFICIENT |
| PR120&PR3 | balls>=120 AND matches>=3 | 205 | 467 | 99.36 | 327.00 | 10 | 1.00 | 9 | 1.00 | 32.16 | 0.61 | 0.84 | SUFFICIENT |
| PR120&PR8 | balls>=120 AND matches>=8 | 195 | 467 | 99.36 | 340.00 | 7 | 1.00 | 9 | 1.00 | 32.21 | 0.62 | 0.84 | SUFFICIENT |
| PR60&PR15 | balls>=60 AND matches>=15 | 158 | 458 | 97.45 | 407.50 | 10 | 1.00 | 6 | 1.00 | 31.43 | 0.62 | 0.86 | SUFFICIENT |
| PR180&PR8 | balls>=180 AND matches>=8 | 155 | 464 | 98.72 | 410.00 | 10 | 1.00 | 6 | 1.00 | 30.69 | 0.60 | 0.84 | SUFFICIENT |
| PR120&PR15 | balls>=120 AND matches>=15 | 148 | 458 | 97.45 | 430.00 | 10 | 1.00 | 6 | 1.00 | 31.15 | 0.62 | 0.85 | SUFFICIENT |
| PR240&PR8 | balls>=240 AND matches>=8 | 131 | 458 | 97.45 | 470.00 | 10 | 1.00 | 6 | 1.00 | 30.04 | 0.64 | 0.85 | SUFFICIENT |
| PR180&PR15 | balls>=180 AND matches>=15 | 139 | 458 | 97.45 | 453.00 | 10 | 1.00 | 6 | 1.00 | 30.45 | 0.62 | 0.85 | SUFFICIENT |
| PR180&PR20 | balls>=180 AND matches>=20 | 119 | 458 | 97.45 | 510.00 | 10 | 1.00 | 6 | 1.00 | 30.13 | 0.65 | 0.85 | SUFFICIENT |
| PR300&PR10 | balls>=300 AND matches>=10 | 111 | 458 | 97.45 | 517.00 | 10 | 1.00 | 6 | 1.00 | 29.85 | 0.65 | 0.85 | SUFFICIENT |
| PR300&PR20 | balls>=300 AND matches>=20 | 106 | 458 | 97.45 | 526.50 | n/a | n/a | 6 | 1.00 | 29.72 | 0.66 | 0.86 | SUFFICIENT |

Recommendation inputs (T20I batter, primary family): lowest stable rule balls:P10, strictest sufficient pool balls:PR300.

### T20I bowler

- balls: percentile candidates P10=17, P25=36, P50=97, P75=266.
  - 24 kept: 24 lies at observed percentile 14.2 with 411 of 479 players at or above it (observed p10=16.0, p90=570.0).
  - 48 kept: 48 lies at observed percentile 29.9 with 336 of 479 players at or above it (observed p10=16.0, p90=570.0).
  - 96 dropped (within_5pct_of_P50): 96 lies at observed percentile 48.4 with 247 of 479 players at or above it (observed p10=16.0, p90=570.0).
  - 144 kept: 144 lies at observed percentile 60.1 with 191 of 479 players at or above it (observed p10=16.0, p90=570.0).
  - 192 kept: 192 lies at observed percentile 67.4 with 156 of 479 players at or above it (observed p10=16.0, p90=570.0).
  - 240 kept: 240 lies at observed percentile 72.7 with 131 of 479 players at or above it (observed p10=16.0, p90=570.0).
- matches: percentile candidates P10=1, P25=2, P50=6, P75=15.
  - 3 kept: 3 lies at observed percentile 27.8 with 346 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 5 kept: 5 lies at observed percentile 44.3 with 267 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 8 kept: 8 lies at observed percentile 57.0 with 206 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 10 kept: 10 lies at observed percentile 63.7 with 174 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 15 dropped (within_5pct_of_P75): 15 lies at observed percentile 74.3 with 123 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 20 kept: 20 lies at observed percentile 80.6 with 93 of 479 players at or above it (observed p10=1.0, p90=29.2).
- innings: percentile candidates P10=1, P25=2, P50=6, P75=15.
  - 3 kept: 3 lies at observed percentile 27.8 with 346 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 5 kept: 5 lies at observed percentile 44.3 with 267 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 8 kept: 8 lies at observed percentile 57.0 with 206 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 10 kept: 10 lies at observed percentile 63.7 with 174 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 15 dropped (within_5pct_of_P75): 15 lies at observed percentile 74.3 with 123 of 479 players at or above it (observed p10=1.0, p90=29.2).
  - 20 kept: 20 lies at observed percentile 80.6 with 93 of 479 players at or above it (observed p10=1.0, p90=29.2).
- n_eff_shrink: percentile candidates P10=3, P25=9, P50=43, P75=179.
  - 20 kept: 20 lies at observed percentile 38.0 with 297 of 479 players at or above it (observed p10=2.0, p90=467.6).
  - 40 kept: 40 lies at observed percentile 48.6 with 246 of 479 players at or above it (observed p10=2.0, p90=467.6).
  - 80 kept: 80 lies at observed percentile 60.8 with 188 of 479 players at or above it (observed p10=2.0, p90=467.6).
  - 120 kept: 120 lies at observed percentile 68.5 with 151 of 479 players at or above it (observed p10=2.0, p90=467.6).
- n_eff_kish: percentile candidates P10=1, P25=2, P50=5, P75=14.

#### T20I bowler: balls (batter balls faced / bowler legal balls)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | balls>=17 | 431 | 470 | 100.00 | 116.00 | 9 | 1.00 | 9 | 1.00 | 3.74 | 0.29 | 0.71 | SUFFICIENT |
| PR24 | balls>=24 | 411 | 470 | 100.00 | 120.00 | 10 | 1.00 | 10 | 1.00 | 3.78 | 0.29 | 0.71 | SUFFICIENT |
| P25 | balls>=36 | 374 | 470 | 100.00 | 149.00 | 10 | 1.00 | 10 | 1.00 | 3.89 | 0.29 | 0.72 | SUFFICIENT |
| PR48 | balls>=48 | 336 | 470 | 100.00 | 183.50 | 10 | 1.00 | 10 | 1.00 | 4.03 | 0.30 | 0.72 | SUFFICIENT |
| P50 | balls>=97 | 240 | 467 | 99.36 | 266.00 | 9 | 1.00 | 10 | 1.00 | 4.16 | 0.37 | 0.71 | SUFFICIENT |
| PR144 | balls>=144 | 191 | 467 | 99.36 | 341.00 | 10 | 1.00 | 9 | 0.99 | 4.19 | 0.39 | 0.72 | SUFFICIENT |
| PR192 | balls>=192 | 156 | 466 | 99.15 | 412.00 | 10 | 1.00 | 9 | 0.99 | 4.21 | 0.41 | 0.72 | SUFFICIENT |
| PR240 | balls>=240 | 131 | 458 | 97.45 | 480.00 | 9 | 1.00 | 9 | 0.99 | 4.16 | 0.45 | 0.73 | SUFFICIENT |
| P75 | balls>=266 | 120 | 458 | 97.45 | 497.00 | n/a | n/a | 9 | 0.98 | 4.11 | 0.46 | 0.73 | SUFFICIENT |

#### T20I bowler: distinct matches

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | matches>=1 | 479 | 470 | 100.00 | 97.00 | 9 | 1.00 | 9 | 1.00 | 3.55 | 0.29 | 0.71 | SUFFICIENT |
| P25 | matches>=2 | 410 | 470 | 100.00 | 120.00 | 10 | 1.00 | 10 | 1.00 | 3.82 | 0.29 | 0.72 | SUFFICIENT |
| PR3 | matches>=3 | 346 | 470 | 100.00 | 171.50 | 10 | 1.00 | 10 | 1.00 | 4.01 | 0.30 | 0.71 | SUFFICIENT |
| PR5 | matches>=5 | 267 | 467 | 99.36 | 228.00 | 10 | 1.00 | 10 | 1.00 | 4.16 | 0.34 | 0.71 | SUFFICIENT |
| P50 | matches>=6 | 244 | 467 | 99.36 | 259.00 | 10 | 1.00 | 10 | 1.00 | 4.18 | 0.36 | 0.71 | SUFFICIENT |
| PR8 | matches>=8 | 206 | 467 | 99.36 | 326.00 | 9 | 1.00 | 10 | 1.00 | 4.19 | 0.38 | 0.71 | SUFFICIENT |
| PR10 | matches>=10 | 174 | 464 | 98.72 | 376.50 | 9 | 1.00 | 9 | 1.00 | 4.17 | 0.40 | 0.72 | SUFFICIENT |
| P75 | matches>=15 | 123 | 458 | 97.45 | 495.00 | 9 | 1.00 | 9 | 0.99 | 4.11 | 0.47 | 0.73 | SUFFICIENT |
| PR20 | matches>=20 | 93 | 453 | 96.38 | 576.00 | n/a | n/a | 8 | 0.98 | 3.98 | 0.54 | 0.74 | SUFFICIENT |

#### T20I bowler: innings batted / bowled in

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | innings>=1 | 479 | 470 | 100.00 | 97.00 | 9 | 1.00 | 9 | 1.00 | 3.55 | 0.29 | 0.71 | SUFFICIENT |
| P25 | innings>=2 | 410 | 470 | 100.00 | 120.00 | 10 | 1.00 | 10 | 1.00 | 3.82 | 0.29 | 0.72 | SUFFICIENT |
| PR3 | innings>=3 | 346 | 470 | 100.00 | 171.50 | 10 | 1.00 | 10 | 1.00 | 4.01 | 0.30 | 0.71 | SUFFICIENT |
| PR5 | innings>=5 | 267 | 467 | 99.36 | 228.00 | 10 | 1.00 | 10 | 1.00 | 4.16 | 0.34 | 0.71 | SUFFICIENT |
| P50 | innings>=6 | 244 | 467 | 99.36 | 259.00 | 10 | 1.00 | 10 | 1.00 | 4.18 | 0.36 | 0.71 | SUFFICIENT |
| PR8 | innings>=8 | 206 | 467 | 99.36 | 326.00 | 9 | 1.00 | 10 | 1.00 | 4.19 | 0.38 | 0.71 | SUFFICIENT |
| PR10 | innings>=10 | 174 | 464 | 98.72 | 376.50 | 9 | 1.00 | 9 | 1.00 | 4.17 | 0.40 | 0.72 | SUFFICIENT |
| P75 | innings>=15 | 123 | 458 | 97.45 | 495.00 | 9 | 1.00 | 9 | 0.99 | 4.11 | 0.47 | 0.73 | SUFFICIENT |
| PR20 | innings>=20 | 93 | 453 | 96.38 | 576.00 | n/a | n/a | 8 | 0.98 | 3.98 | 0.54 | 0.74 | SUFFICIENT |

#### T20I bowler: effective sample size (shrinkage)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | n_eff_shrink>=3 | 413 | 470 | 100.00 | 120.00 | 10 | 1.00 | 10 | 1.00 | 3.75 | 0.29 | 0.71 | SUFFICIENT |
| P25 | n_eff_shrink>=9 | 357 | 470 | 100.00 | 162.00 | 10 | 1.00 | 10 | 1.00 | 3.92 | 0.29 | 0.72 | SUFFICIENT |
| PR20 | n_eff_shrink>=20 | 297 | 470 | 100.00 | 198.00 | 10 | 1.00 | 10 | 1.00 | 4.15 | 0.31 | 0.72 | SUFFICIENT |
| PR40 | n_eff_shrink>=40 | 246 | 467 | 99.36 | 256.50 | 10 | 1.00 | 10 | 1.00 | 4.16 | 0.36 | 0.71 | SUFFICIENT |
| P50 | n_eff_shrink>=43 | 237 | 467 | 99.36 | 270.00 | 9 | 1.00 | 10 | 1.00 | 4.18 | 0.37 | 0.71 | SUFFICIENT |
| PR80 | n_eff_shrink>=80 | 188 | 467 | 99.36 | 343.00 | 10 | 1.00 | 9 | 1.00 | 4.19 | 0.39 | 0.72 | SUFFICIENT |
| PR120 | n_eff_shrink>=120 | 151 | 458 | 97.45 | 422.00 | 9 | 1.00 | 9 | 1.00 | 4.21 | 0.41 | 0.72 | SUFFICIENT |
| P75 | n_eff_shrink>=179 | 119 | 458 | 97.45 | 499.00 | n/a | n/a | 9 | 0.99 | 4.11 | 0.47 | 0.73 | SUFFICIENT |

#### T20I bowler: effective number of matches (Kish)

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P10 | n_eff_kish>=1 | 479 | 470 | 100.00 | 97.00 | 9 | 1.00 | 10 | 1.00 | 3.55 | 0.29 | 0.71 | SUFFICIENT |
| P25 | n_eff_kish>=2 | 358 | 470 | 100.00 | 162.00 | 10 | 1.00 | 9 | 1.00 | 3.96 | 0.30 | 0.71 | SUFFICIENT |
| P50 | n_eff_kish>=5 | 239 | 467 | 99.36 | 268.00 | 9 | 0.99 | 9 | 0.99 | 4.17 | 0.36 | 0.71 | SUFFICIENT |
| P75 | n_eff_kish>=14 | 117 | 458 | 97.45 | 502.00 | n/a | n/a | 8 | 0.97 | 4.03 | 0.48 | 0.74 | SUFFICIENT |

#### T20I bowler: balls AND matches

| Rule | Clauses | Eligible | Matches covered | Coverage % | Median balls | Top10 overlap vs next | Spearman vs next | Top10 overlap vs ref | Spearman vs ref | Median 95% CI width | Top10 mean membership | Boot Spearman | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PR24&PR3 | balls>=24 AND matches>=3 | 346 | 470 | 100.00 | 171.50 | 10 | 1.00 | 10 | 1.00 | 4.01 | 0.30 | 0.71 | SUFFICIENT |
| PR48&PR3 | balls>=48 AND matches>=3 | 327 | 470 | 100.00 | 186.00 | 10 | 1.00 | 10 | 1.00 | 4.07 | 0.30 | 0.71 | SUFFICIENT |
| PR48&PR5 | balls>=48 AND matches>=5 | 262 | 467 | 99.36 | 239.50 | 10 | 1.00 | 10 | 1.00 | 4.17 | 0.34 | 0.71 | SUFFICIENT |
| PR48&PR8 | balls>=48 AND matches>=8 | 206 | 467 | 99.36 | 326.00 | 9 | 1.00 | 10 | 1.00 | 4.19 | 0.38 | 0.71 | SUFFICIENT |
| PR192&PR3 | balls>=192 AND matches>=3 | 156 | 466 | 99.15 | 412.00 | 10 | 1.00 | 9 | 1.00 | 4.21 | 0.41 | 0.72 | SUFFICIENT |
| PR48&PR10 | balls>=48 AND matches>=10 | 174 | 464 | 98.72 | 376.50 | 10 | 1.00 | 9 | 1.00 | 4.17 | 0.40 | 0.72 | SUFFICIENT |
| PR192&PR5 | balls>=192 AND matches>=5 | 156 | 466 | 99.15 | 412.00 | 10 | 1.00 | 9 | 1.00 | 4.21 | 0.41 | 0.72 | SUFFICIENT |
| PR48&PR20 | balls>=48 AND matches>=20 | 93 | 453 | 96.38 | 576.00 | 10 | 1.00 | 8 | 0.98 | 3.98 | 0.54 | 0.74 | SUFFICIENT |
| PR192&PR8 | balls>=192 AND matches>=8 | 156 | 466 | 99.15 | 412.00 | 10 | 1.00 | 9 | 1.00 | 4.21 | 0.41 | 0.72 | SUFFICIENT |
| PR192&PR10 | balls>=192 AND matches>=10 | 150 | 458 | 97.45 | 423.00 | 8 | 0.99 | 9 | 1.00 | 4.20 | 0.42 | 0.73 | SUFFICIENT |
| PR192&PR20 | balls>=192 AND matches>=20 | 93 | 453 | 96.38 | 576.00 | 10 | 1.00 | 8 | 0.98 | 3.98 | 0.54 | 0.74 | SUFFICIENT |
| PR240&PR20 | balls>=240 AND matches>=20 | 91 | 453 | 96.38 | 580.00 | n/a | n/a | 8 | 0.97 | 3.98 | 0.54 | 0.74 | SUFFICIENT |

Recommendation inputs (T20I bowler, primary family): lowest stable rule balls:P10, strictest sufficient pool balls:P75.

## 5. Combined eligibility (eligible in IPL and T20I)

### batter

| Rule | Eligible in both | Pool |
|---|---|---|
| balls+matches:PR180&PR20 | 37 | SUFFICIENT: 37 eligible, at or above the required pool of 30 |
| balls+matches:PR60&PR15 | 51 | SUFFICIENT: 51 eligible, at or above the required pool of 30 |
| balls:P10 | 162 | SUFFICIENT: 162 eligible, at or above the required pool of 30 |
| balls:P25 | 133 | SUFFICIENT: 133 eligible, at or above the required pool of 30 |
| balls:P50 | 94 | SUFFICIENT: 94 eligible, at or above the required pool of 30 |
| balls:P75 | 48 | SUFFICIENT: 48 eligible, at or above the required pool of 30 |
| balls:PR120 | 69 | SUFFICIENT: 69 eligible, at or above the required pool of 30 |
| balls:PR180 | 54 | SUFFICIENT: 54 eligible, at or above the required pool of 30 |
| balls:PR240 | 47 | SUFFICIENT: 47 eligible, at or above the required pool of 30 |
| balls:PR30 | 108 | SUFFICIENT: 108 eligible, at or above the required pool of 30 |
| balls:PR60 | 87 | SUFFICIENT: 87 eligible, at or above the required pool of 30 |
| innings:P10 | 182 | SUFFICIENT: 182 eligible, at or above the required pool of 30 |
| innings:P25 | 146 | SUFFICIENT: 146 eligible, at or above the required pool of 30 |
| innings:P50 | 99 | SUFFICIENT: 99 eligible, at or above the required pool of 30 |
| innings:P75 | 42 | SUFFICIENT: 42 eligible, at or above the required pool of 30 |
| innings:PR10 | 73 | SUFFICIENT: 73 eligible, at or above the required pool of 30 |
| innings:PR15 | 51 | SUFFICIENT: 51 eligible, at or above the required pool of 30 |
| innings:PR20 | 37 | SUFFICIENT: 37 eligible, at or above the required pool of 30 |
| matches:P10 | 182 | SUFFICIENT: 182 eligible, at or above the required pool of 30 |
| matches:P25 | 146 | SUFFICIENT: 146 eligible, at or above the required pool of 30 |
| matches:P50 | 99 | SUFFICIENT: 99 eligible, at or above the required pool of 30 |
| matches:P75 | 42 | SUFFICIENT: 42 eligible, at or above the required pool of 30 |
| matches:PR10 | 73 | SUFFICIENT: 73 eligible, at or above the required pool of 30 |
| matches:PR15 | 51 | SUFFICIENT: 51 eligible, at or above the required pool of 30 |
| matches:PR20 | 37 | SUFFICIENT: 37 eligible, at or above the required pool of 30 |
| n_eff_kish:P10 | 182 | SUFFICIENT: 182 eligible, at or above the required pool of 30 |
| n_eff_kish:P25 | 133 | SUFFICIENT: 133 eligible, at or above the required pool of 30 |
| n_eff_kish:P50 | 90 | SUFFICIENT: 90 eligible, at or above the required pool of 30 |
| n_eff_kish:P75 | 40 | SUFFICIENT: 40 eligible, at or above the required pool of 30 |
| n_eff_shrink:P10 | 140 | SUFFICIENT: 140 eligible, at or above the required pool of 30 |
| n_eff_shrink:P25 | 127 | SUFFICIENT: 127 eligible, at or above the required pool of 30 |
| n_eff_shrink:P50 | 91 | SUFFICIENT: 91 eligible, at or above the required pool of 30 |
| n_eff_shrink:P75 | 47 | SUFFICIENT: 47 eligible, at or above the required pool of 30 |
| n_eff_shrink:PR120 | 53 | SUFFICIENT: 53 eligible, at or above the required pool of 30 |
| n_eff_shrink:PR20 | 89 | SUFFICIENT: 89 eligible, at or above the required pool of 30 |
| n_eff_shrink:PR40 | 76 | SUFFICIENT: 76 eligible, at or above the required pool of 30 |
| n_eff_shrink:PR80 | 64 | SUFFICIENT: 64 eligible, at or above the required pool of 30 |

### bowler

| Rule | Eligible in both | Pool |
|---|---|---|
| balls+matches:PR192&PR20 | 30 | SUFFICIENT: 30 eligible, at or above the required pool of 30 |
| balls+matches:PR192&PR5 | 58 | SUFFICIENT: 58 eligible, at or above the required pool of 30 |
| balls+matches:PR240&PR20 | 28 | INSUFFICIENT: 28 eligible, below the required pool of 30 |
| balls+matches:PR48&PR10 | 58 | SUFFICIENT: 58 eligible, at or above the required pool of 30 |
| balls+matches:PR48&PR20 | 30 | SUFFICIENT: 30 eligible, at or above the required pool of 30 |
| balls+matches:PR48&PR5 | 91 | SUFFICIENT: 91 eligible, at or above the required pool of 30 |
| balls:P10 | 134 | SUFFICIENT: 134 eligible, at or above the required pool of 30 |
| balls:P25 | 114 | SUFFICIENT: 114 eligible, at or above the required pool of 30 |
| balls:P50 | 72 | SUFFICIENT: 72 eligible, at or above the required pool of 30 |
| balls:P75 | 27 | INSUFFICIENT: 27 eligible, below the required pool of 30 |
| balls:PR144 | 75 | SUFFICIENT: 75 eligible, at or above the required pool of 30 |
| balls:PR192 | 58 | SUFFICIENT: 58 eligible, at or above the required pool of 30 |
| balls:PR24 | 126 | SUFFICIENT: 126 eligible, at or above the required pool of 30 |
| balls:PR240 | 48 | SUFFICIENT: 48 eligible, at or above the required pool of 30 |
| balls:PR48 | 102 | SUFFICIENT: 102 eligible, at or above the required pool of 30 |
| innings:P10 | 143 | SUFFICIENT: 143 eligible, at or above the required pool of 30 |
| innings:P25 | 115 | SUFFICIENT: 115 eligible, at or above the required pool of 30 |
| innings:P50 | 75 | SUFFICIENT: 75 eligible, at or above the required pool of 30 |
| innings:P75 | 31 | SUFFICIENT: 31 eligible, at or above the required pool of 30 |
| innings:PR10 | 58 | SUFFICIENT: 58 eligible, at or above the required pool of 30 |
| innings:PR20 | 30 | SUFFICIENT: 30 eligible, at or above the required pool of 30 |
| innings:PR5 | 93 | SUFFICIENT: 93 eligible, at or above the required pool of 30 |
| matches:P10 | 143 | SUFFICIENT: 143 eligible, at or above the required pool of 30 |
| matches:P25 | 115 | SUFFICIENT: 115 eligible, at or above the required pool of 30 |
| matches:P50 | 75 | SUFFICIENT: 75 eligible, at or above the required pool of 30 |
| matches:P75 | 31 | SUFFICIENT: 31 eligible, at or above the required pool of 30 |
| matches:PR10 | 58 | SUFFICIENT: 58 eligible, at or above the required pool of 30 |
| matches:PR20 | 30 | SUFFICIENT: 30 eligible, at or above the required pool of 30 |
| matches:PR5 | 93 | SUFFICIENT: 93 eligible, at or above the required pool of 30 |
| n_eff_kish:P10 | 143 | SUFFICIENT: 143 eligible, at or above the required pool of 30 |
| n_eff_kish:P25 | 103 | SUFFICIENT: 103 eligible, at or above the required pool of 30 |
| n_eff_kish:P50 | 68 | SUFFICIENT: 68 eligible, at or above the required pool of 30 |
| n_eff_kish:P75 | 28 | INSUFFICIENT: 28 eligible, below the required pool of 30 |
| n_eff_shrink:P10 | 129 | SUFFICIENT: 129 eligible, at or above the required pool of 30 |
| n_eff_shrink:P25 | 108 | SUFFICIENT: 108 eligible, at or above the required pool of 30 |
| n_eff_shrink:P50 | 71 | SUFFICIENT: 71 eligible, at or above the required pool of 30 |
| n_eff_shrink:P75 | 27 | INSUFFICIENT: 27 eligible, below the required pool of 30 |
| n_eff_shrink:PR120 | 53 | SUFFICIENT: 53 eligible, at or above the required pool of 30 |
| n_eff_shrink:PR20 | 91 | SUFFICIENT: 91 eligible, at or above the required pool of 30 |
| n_eff_shrink:PR40 | 80 | SUFFICIENT: 80 eligible, at or above the required pool of 30 |

## 6. Technical appendix (proxy, flagged PROXY_NOT_PRESSURE)

Top proxy scores at the reference rule with bootstrap 95% intervals. These are not recommendations and not pressure rankings.

### IPL batter (reference rule balls:PR30)

| player_id | name | proxy score | CI low | CI high | Top10 freq | flag |
|---|---|---|---|---|---|---|
| 50,284 | Vaibhav Sooryavanshi | 213.21 | 190.23 | 239.60 | 1.00 | PROXY_NOT_PRESSURE |
| 4,847 | Finn Allen | 187.54 | 154.33 | 216.69 | 0.84 | PROXY_NOT_PRESSURE |
| 25,669 | Priyansh Arya | 184.49 | 163.77 | 204.19 | 0.88 | PROXY_NOT_PRESSURE |
| 7,341 | Jake McGurk | 180.77 | 141.82 | 223.26 | 0.65 | PROXY_NOT_PRESSURE |
| 6,457 | Urvil Patel | 174.53 | 144.70 | 206.40 | 0.55 | PROXY_NOT_PRESSURE |
| 6,281 | Abhishek Sharma | 173.49 | 156.47 | 188.79 | 0.51 | PROXY_NOT_PRESSURE |
| 6,396 | Tim David | 173.38 | 158.11 | 191.35 | 0.53 | PROXY_NOT_PRESSURE |
| 2,367 | Travis Head | 172.57 | 153.62 | 192.27 | 0.47 | PROXY_NOT_PRESSURE |
| 48,504 | Ayush Mhatre | 172.42 | 158.82 | 185.66 | 0.50 | PROXY_NOT_PRESSURE |
| 5,553 | Phil Salt | 170.93 | 158.38 | 183.98 | 0.38 | PROXY_NOT_PRESSURE |

### IPL bowler (reference rule balls:PR24)

| player_id | name | proxy score | CI low | CI high | Top10 freq | flag |
|---|---|---|---|---|---|---|
| 8,661 | Matheesha Pathirana | 4.05 | 0.72 | 4.57 | 0.47 | PROXY_NOT_PRESSURE |
| 830 | Josh Hazlewood | 3.94 | -0.19 | 4.92 | 0.37 | PROXY_NOT_PRESSURE |
| 1,318 | Andre Russell | 3.79 | 0.23 | 5.17 | 0.49 | PROXY_NOT_PRESSURE |
| 1,612 | Yuzvendra Chahal | 3.65 | -0.01 | 3.75 | 0.20 | PROXY_NOT_PRESSURE |
| 7,967 | Noor Ahmad | 3.23 | 0.16 | 4.06 | 0.26 | PROXY_NOT_PRESSURE |
| 4,900 | Wanindu Hasaranga | 3.21 | -0.09 | 4.31 | 0.28 | PROXY_NOT_PRESSURE |
| 4,489 | Prasidh Krishna | 3.17 | -0.06 | 3.93 | 0.20 | PROXY_NOT_PRESSURE |
| 2,933 | Jasprit Bumrah | 3.12 | 0.02 | 4.84 | 0.38 | PROXY_NOT_PRESSURE |
| 1,596 | Moeen Ali | 3.08 | 0.04 | 4.67 | 0.36 | PROXY_NOT_PRESSURE |
| 6,256 | Varun Chakravarthy | 2.99 | -0.07 | 3.84 | 0.19 | PROXY_NOT_PRESSURE |

### T20I batter (reference rule balls:PR30)

| player_id | name | proxy score | CI low | CI high | Top10 freq | flag |
|---|---|---|---|---|---|---|
| 6,281 | Abhishek Sharma | 194.00 | 177.92 | 211.13 | 1.00 | PROXY_NOT_PRESSURE |
| 37,052 | Naman Dhir | 173.22 | 147.39 | 213.34 | 0.76 | PROXY_NOT_PRESSURE |
| 6,396 | Tim David | 171.88 | 154.19 | 192.21 | 0.68 | PROXY_NOT_PRESSURE |
| 772 | Rilee Rossouw | 168.32 | 145.33 | 188.67 | 0.62 | PROXY_NOT_PRESSURE |
| 6,280 | Harry Brook | 168.22 | 150.41 | 186.58 | 0.55 | PROXY_NOT_PRESSURE |
| 1,318 | Andre Russell | 167.90 | 140.93 | 195.77 | 0.56 | PROXY_NOT_PRESSURE |
| 50,284 | Vaibhav Sooryavanshi | 166.09 | 141.53 | 198.13 | 0.52 | PROXY_NOT_PRESSURE |
| 1,699 | Suryakumar Yadav | 165.64 | 153.31 | 177.81 | 0.35 | PROXY_NOT_PRESSURE |
| 2,367 | Travis Head | 164.98 | 139.94 | 192.43 | 0.44 | PROXY_NOT_PRESSURE |
| 813 | Jos Buttler | 163.09 | 153.05 | 175.93 | 0.20 | PROXY_NOT_PRESSURE |

### T20I bowler (reference rule balls:PR24)

| player_id | name | proxy score | CI low | CI high | Top10 freq | flag |
|---|---|---|---|---|---|---|
| 4,722 | Rashid Khan | 6.25 | 1.68 | 5.16 | 0.56 | PROXY_NOT_PRESSURE |
| 6,256 | Varun Chakravarthy | 6.14 | 1.41 | 5.36 | 0.50 | PROXY_NOT_PRESSURE |
| 3,644 | Kuldeep Yadav | 6.00 | 1.26 | 6.42 | 0.65 | PROXY_NOT_PRESSURE |
| 4,900 | Wanindu Hasaranga | 5.30 | 0.69 | 3.84 | 0.10 | PROXY_NOT_PRESSURE |
| 2,490 | Mohammad Nawaz | 4.61 | 0.37 | 4.56 | 0.21 | PROXY_NOT_PRESSURE |
| 7,364 | Haris Rauf | 4.36 | -0.40 | 3.80 | 0.07 | PROXY_NOT_PRESSURE |
| 7,699 | Abbas Afridi | 4.25 | 1.17 | 5.12 | 0.43 | PROXY_NOT_PRESSURE |
| 6,464 | Arshdeep Singh | 3.73 | -0.48 | 2.51 | 0.001 | PROXY_NOT_PRESSURE |
| 4,823 | Washington Sundar | 3.55 | 0.32 | 5.33 | 0.28 | PROXY_NOT_PRESSURE |
| 5,979 | Abrar Ahmed | 3.49 | 0.12 | 4.23 | 0.14 | PROXY_NOT_PRESSURE |

