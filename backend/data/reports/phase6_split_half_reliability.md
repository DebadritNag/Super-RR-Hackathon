# Phase 6 split-half reliability

Status: EXPERIMENTAL_NOT_VALIDATED. INTERNAL, `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. TEST outcomes: not used. Cricsheet: not used. Seed 20260512, 1000 bootstrap draws, 200 random splits, at least 6 pressure balls per half, at least 10 players. Code version `0061c9d62abd2c99`. Criteria SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851` (declared before this run, run-log seq 89 for this step).

## 1. How to read this
- Reliability is the Spearman-Brown corrected correlation `2r / (1 + r)` between the mean residual of two halves of each player's matches. It is reported unclipped: a negative value means the halves disagree.
- Odd/even uses alternate matches. Early/late splits in time and so also measures drift (the halves are not parallel). Random splits repeat random match partitions; the value is the median over repeats and the SD across splits is shown.
- Intervals: bootstrap over players, match-cluster bootstrap (all modes), and bootstrap of the per-repeat median (random, split noise only; the table also holds player and match intervals on the repeat closest to the median). An interval that includes 0 gives no evidence of reliability above 0.
- In-sample diagnostics. The baseline and pressure thresholds were fitted on TRAIN, so these figures are not out-of-sample validation.

## 2. Preconditions
- Odd/even and early/late rows reproduce the stored Phase 5 table: 128/128 rows matched, max abs difference in r 9.71e-17, players equal = True, reproduces = True.

## 3. Counts
- Rows: 432; estimable: 428; units not estimable (fewer than 10 players with enough balls per half): 4.
- PRE_TEST, primary streams, odd_even: 36 estimable units over 9 definitions; Spearman-Brown median 0.301 (min -0.500, max 0.685); interval lower bound above 0 in 16/36 units.
- PRE_TEST, primary streams, early_late: 36 estimable units over 9 definitions; Spearman-Brown median 0.258 (min -0.480, max 0.556); interval lower bound above 0 in 5/36 units.
- PRE_TEST, primary streams, random: 36 estimable units over 9 definitions; Spearman-Brown median 0.276 (min -0.385, max 0.599); interval lower bound above 0 in 9/36 units.

## 4. Provisional definition `any|q0.75`, all streams

| format | role | stream | mode | players | r | SB | SB lo (players) | SB hi | SB lo (matches) | SB hi (matches) |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | runs | odd_even | 144 | 0.24 | 0.39 | 0.12 | 0.59 | 0.18 | 0.59 |
| IPL | batter | runs | early_late | 138 | 0.19 | 0.33 | 0.06 | 0.54 | 0.10 | 0.54 |
| IPL | batter | runs | random | 140 | 0.21 | 0.35 | 0.05 | 0.56 | 0.11 | 0.54 |
| T20I | batter | runs | odd_even | 247 | 0.26 | 0.42 | 0.22 | 0.56 | 0.18 | 0.49 |
| T20I | batter | runs | early_late | 227 | 0.32 | 0.48 | 0.31 | 0.62 | 0.20 | 0.55 |
| T20I | batter | runs | random | 231 | 0.28 | 0.44 | 0.25 | 0.59 | 0.18 | 0.54 |
| IPL | batter | dismissal | odd_even | 144 | 0.20 | 0.34 | 0.10 | 0.54 | -0.08 | 0.50 |
| IPL | batter | dismissal | early_late | 138 | 0.14 | 0.25 | 0.02 | 0.49 | -0.18 | 0.45 |
| IPL | batter | dismissal | random | 140 | 0.17 | 0.29 | -0.02 | 0.51 | -0.14 | 0.51 |
| T20I | batter | dismissal | odd_even | 247 | 0.06 | 0.11 | -0.21 | 0.34 | -0.16 | 0.40 |
| T20I | batter | dismissal | early_late | 227 | 0.14 | 0.24 | 0.00328 | 0.42 | -0.21 | 0.39 |
| T20I | batter | dismissal | random | 231 | 0.12 | 0.22 | -0.08 | 0.47 | -0.19 | 0.40 |
| IPL | bowler | charged | odd_even | 135 | 0.26 | 0.41 | 0.16 | 0.60 | -0.10 | 0.49 |
| IPL | bowler | charged | early_late | 125 | 0.09 | 0.17 | -0.31 | 0.45 | -0.35 | 0.39 |
| IPL | bowler | charged | random | 127 | 0.13 | 0.23 | -0.15 | 0.50 | -0.22 | 0.41 |
| T20I | bowler | charged | odd_even | 231 | 0.15 | 0.25 | 0.00437 | 0.45 | -0.08 | 0.42 |
| T20I | bowler | charged | early_late | 227 | 0.10 | 0.18 | -0.09 | 0.40 | -0.09 | 0.39 |
| T20I | bowler | charged | random | 226 | 0.10 | 0.19 | -0.08 | 0.40 | -0.10 | 0.42 |
| IPL | bowler | wkt | odd_even | 135 | 0.14 | 0.25 | -0.13 | 0.51 | -0.19 | 0.44 |
| IPL | bowler | wkt | early_late | 125 | -0.05 | -0.10 | -0.49 | 0.28 | -0.38 | 0.29 |
| IPL | bowler | wkt | random | 127 | 0.04 | 0.08 | -0.43 | 0.47 | -0.26 | 0.39 |
| T20I | bowler | wkt | odd_even | 231 | 0.10 | 0.19 | -0.03 | 0.38 | -0.10 | 0.36 |
| T20I | bowler | wkt | early_late | 227 | 0.07 | 0.13 | -0.15 | 0.36 | -0.26 | 0.25 |
| T20I | bowler | wkt | random | 226 | 0.09 | 0.17 | -0.09 | 0.38 | -0.20 | 0.29 |


## 5. Pooled over format x role cells (Fisher z, weights n-3, clip 0.99)
Primary streams, all nine definitions, PRE_TEST.

| definition | mode | cells | players | pooled r | pooled SB |
|---|---|---|---|---|---|
| any\|q0.75 | early_late | 4 | 717 | 0.19 | 0.32 |
| any\|q0.75 | odd_even | 4 | 757 | 0.22 | 0.37 |
| any\|q0.75 | random | 4 | 724 | 0.19 | 0.32 |
| any\|q0.9 | early_late | 4 | 429 | 0.10 | 0.18 |
| any\|q0.9 | odd_even | 4 | 460 | 0.21 | 0.35 |
| any\|q0.9 | random | 4 | 434 | 0.15 | 0.26 |
| any\|q0.95 | early_late | 4 | 241 | 0.06 | 0.11 |
| any\|q0.95 | odd_even | 4 | 262 | 0.15 | 0.26 |
| any\|q0.95 | random | 4 | 247 | 0.12 | 0.21 |
| chase\|q0.75 | early_late | 4 | 475 | 0.16 | 0.28 |
| chase\|q0.75 | odd_even | 4 | 495 | 0.23 | 0.37 |
| chase\|q0.75 | random | 4 | 477 | 0.18 | 0.30 |
| chase\|q0.9 | early_late | 4 | 238 | 0.10 | 0.19 |
| chase\|q0.9 | odd_even | 4 | 252 | 0.16 | 0.28 |
| chase\|q0.9 | random | 4 | 239 | 0.10 | 0.18 |
| chase\|q0.95 | early_late | 4 | 119 | 0.16 | 0.28 |
| chase\|q0.95 | odd_even | 4 | 135 | 0.21 | 0.35 |
| chase\|q0.95 | random | 4 | 125 | 0.19 | 0.31 |
| inn1\|q0.75 | early_late | 4 | 435 | 0.15 | 0.27 |
| inn1\|q0.75 | odd_even | 4 | 458 | 0.21 | 0.35 |
| inn1\|q0.75 | random | 4 | 440 | 0.16 | 0.27 |
| inn1\|q0.9 | early_late | 4 | 225 | 0.05 | 0.10 |
| inn1\|q0.9 | odd_even | 4 | 239 | 0.15 | 0.26 |
| inn1\|q0.9 | random | 4 | 226 | 0.13 | 0.22 |
| inn1\|q0.95 | early_late | 4 | 106 | 0.03 | 0.06 |
| inn1\|q0.95 | odd_even | 4 | 120 | -0.001 | -0.00201 |
| inn1\|q0.95 | random | 4 | 109 | 0.12 | 0.22 |


## 6. TRAIN window versus PRE_TEST (primary streams, provisional definition)
| format | role | mode | window | players | SB |
|---|---|---|---|---|---|
| IPL | batter | early_late | PRE_TEST | 138 | 0.33 |
| IPL | batter | early_late | TRAIN | 122 | 0.16 |
| IPL | batter | odd_even | PRE_TEST | 144 | 0.39 |
| IPL | batter | odd_even | TRAIN | 125 | 0.27 |
| IPL | batter | random | PRE_TEST | 140 | 0.35 |
| IPL | batter | random | TRAIN | 124 | 0.29 |
| IPL | bowler | early_late | PRE_TEST | 125 | 0.17 |
| IPL | bowler | early_late | TRAIN | 111 | -0.16 |
| IPL | bowler | odd_even | PRE_TEST | 135 | 0.41 |
| IPL | bowler | odd_even | TRAIN | 119 | 0.14 |
| IPL | bowler | random | PRE_TEST | 127 | 0.23 |
| IPL | bowler | random | TRAIN | 113 | -0.06 |
| T20I | batter | early_late | PRE_TEST | 227 | 0.48 |
| T20I | batter | early_late | TRAIN | 164 | 0.36 |
| T20I | batter | odd_even | PRE_TEST | 247 | 0.42 |
| T20I | batter | odd_even | TRAIN | 169 | 0.40 |
| T20I | batter | random | PRE_TEST | 231 | 0.44 |
| T20I | batter | random | TRAIN | 161 | 0.38 |
| T20I | bowler | early_late | PRE_TEST | 227 | 0.18 |
| T20I | bowler | early_late | TRAIN | 177 | -0.06 |
| T20I | bowler | odd_even | PRE_TEST | 231 | 0.25 |
| T20I | bowler | odd_even | TRAIN | 186 | 0.18 |
| T20I | bowler | random | PRE_TEST | 226 | 0.19 |
| T20I | bowler | random | TRAIN | 178 | 0.12 |


## 7. Limits
- Spearman-Brown assumes parallel halves; early/late violates stationarity.
- The nine definitions are examined side by side without multiplicity correction. Higher reliability of one definition is not evidence that it measures pressure skill.
- Players with at least 6 balls in each half are a selected, more active subset.
- Bootstrap over players and over matches answer different questions; both are shown. Each match-bootstrap draw drops about 37% of the matches, which adds noise to the half means, so the match-bootstrap interval is not centred on the point estimate: the interval midpoint is below the point estimate in 250/286 odd/even and early/late units and the point estimate is above the interval upper bound in 0/286. It is a conservative check for reliability above 0.
- Consistency between odd/even, early/late and random splits is a robustness check, not independent validation.
