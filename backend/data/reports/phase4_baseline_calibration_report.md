# Phase 4 baseline calibration report

Status: EXPERIMENTAL_NOT_VALIDATED. Baseline `p4_baseline_b0_train_frozen_v1`, fitted on TRAIN only.

Method: stratified empirical-Bayes cells (`comp|role|phase|wickets-bin` down to `comp`), shrinkage strength from TRAIN, wickets-remaining bins from TRAIN, one additive offset per format fitted on TRAIN. TRAIN rows use leave-player-out expectations; VALIDATION rows use the frozen tables. TEST rows were not loaded. B0 has no pressure term.

Wickets-remaining bins (TRAIN): {10: '10-8', 9: '10-8', 8: '10-8', 7: '7-1', 6: '7-1', 5: '7-1', 4: '7-1', 3: '7-1', 2: '7-1', 1: '7-1'}

## Calibration identity (TRAIN, pooled expectation)
| stream | format | sum actual | sum expected | relative diff |
|---|---|---|---|---|
| batter:runs | IPL | 71967.00 | 71967.00 | 0.00 |
| batter:runs | T20I | 79413.00 | 79413.00 | 1.83e-16 |
| batter:dismissal | IPL | 2609.00 | 2609.00 | 1.74e-16 |
| batter:dismissal | T20I | 3356.00 | 3356.00 | 0.00 |
| bowler:charged | IPL | 74662.00 | 74662.00 | 0.00 |
| bowler:charged | T20I | 82398.00 | 82398.00 | 0.00 |
| bowler:wkt | IPL | 2531.00 | 2531.00 | 1.8e-16 |
| bowler:wkt | T20I | 3261.00 | 3261.00 | 0.00 |


## Residuals and coverage by period
| stream | period | rows | mean residual | sd | finest cell unseen | levels |
|---|---|---|---|---|---|---|
| batter:runs | TRAIN | 110,851 | 0.000662 | 1.71 | 0 | {'0': 110851} |
| batter:runs | VALIDATION | 41,740 | 0.05 | 1.75 | 0 | {'0': 41740} |
| batter:dismissal | TRAIN | 110,851 | -0.000112 | 0.23 | 0 | {'0': 110851} |
| batter:dismissal | VALIDATION | 41,740 | 0.00152 | 0.23 | 0 | {'0': 41740} |
| bowler:charged | TRAIN | 115,212 | -0.000564 | 1.68 | 0 | {'0': 115212} |
| bowler:charged | VALIDATION | 43,376 | 0.05 | 1.73 | 0 | {'0': 43376} |
| bowler:wkt | TRAIN | 115,212 | 4.95e-06 | 0.22 | 0 | {'0': 115212} |
| bowler:wkt | VALIDATION | 43,376 | 0.00159 | 0.22 | 0 | {'0': 43376} |


## Out-of-period (VALIDATION) by format
| stream | period | group | rows | actual | expected | residual |
|---|---|---|---|---|---|---|
| batter:runs | VALIDATION | IPL | 16301.00 | 1.53 | 1.42 | 0.11 |
| batter:runs | VALIDATION | T20I | 25439.00 | 1.32 | 1.32 | 0.00415 |
| batter:dismissal | VALIDATION | IPL | 16301.00 | 0.05 | 0.05 | -0.000461 |
| batter:dismissal | VALIDATION | T20I | 25439.00 | 0.06 | 0.06 | 0.00279 |
| bowler:charged | VALIDATION | IPL | 16992.00 | 1.52 | 1.41 | 0.11 |
| bowler:charged | VALIDATION | T20I | 26384.00 | 1.32 | 1.32 | 0.00548 |
| bowler:wkt | VALIDATION | IPL | 16992.00 | 0.05 | 0.05 | 2.02e-05 |
| bowler:wkt | VALIDATION | T20I | 26384.00 | 0.05 | 0.05 | 0.0026 |


## Out-of-period (VALIDATION) by phase
| stream | period | group | rows | actual | expected | residual |
|---|---|---|---|---|---|---|
| batter:runs | VALIDATION | ('IPL', 'death') | 3579.00 | 1.72 | 1.63 | 0.09 |
| batter:runs | VALIDATION | ('IPL', 'middle') | 7579.00 | 1.45 | 1.35 | 0.09 |
| batter:runs | VALIDATION | ('IPL', 'powerplay') | 5143.00 | 1.53 | 1.37 | 0.16 |
| batter:runs | VALIDATION | ('T20I', 'death') | 5402.00 | 1.49 | 1.51 | -0.02 |
| batter:runs | VALIDATION | ('T20I', 'middle') | 11885.00 | 1.26 | 1.27 | -0.01 |
| batter:runs | VALIDATION | ('T20I', 'powerplay') | 8152.00 | 1.31 | 1.26 | 0.05 |
| batter:dismissal | VALIDATION | ('IPL', 'death') | 3579.00 | 0.08 | 0.07 | 0.0073 |
| batter:dismissal | VALIDATION | ('IPL', 'middle') | 7579.00 | 0.04 | 0.05 | -0.00206 |
| batter:dismissal | VALIDATION | ('IPL', 'powerplay') | 5143.00 | 0.04 | 0.04 | -0.0035 |
| batter:dismissal | VALIDATION | ('T20I', 'death') | 5402.00 | 0.09 | 0.08 | 0.01 |
| batter:dismissal | VALIDATION | ('T20I', 'middle') | 11885.00 | 0.05 | 0.05 | 0.00312 |
| batter:dismissal | VALIDATION | ('T20I', 'powerplay') | 8152.00 | 0.05 | 0.05 | -0.00262 |
| bowler:charged | VALIDATION | ('IPL', 'death') | 3800.00 | 1.69 | 1.60 | 0.09 |
| bowler:charged | VALIDATION | ('IPL', 'middle') | 7850.00 | 1.44 | 1.35 | 0.09 |
| bowler:charged | VALIDATION | ('IPL', 'powerplay') | 5342.00 | 1.52 | 1.37 | 0.15 |
| bowler:charged | VALIDATION | ('T20I', 'death') | 5691.00 | 1.47 | 1.50 | -0.02 |
| bowler:charged | VALIDATION | ('T20I', 'middle') | 12261.00 | 1.26 | 1.27 | -0.00976 |
| bowler:charged | VALIDATION | ('T20I', 'powerplay') | 8432.00 | 1.31 | 1.27 | 0.05 |
| bowler:wkt | VALIDATION | ('IPL', 'death') | 3800.00 | 0.07 | 0.07 | 0.00755 |
| bowler:wkt | VALIDATION | ('IPL', 'middle') | 7850.00 | 0.04 | 0.04 | -0.00149 |
| bowler:wkt | VALIDATION | ('IPL', 'powerplay') | 5342.00 | 0.04 | 0.04 | -0.00312 |
| bowler:wkt | VALIDATION | ('T20I', 'death') | 5691.00 | 0.08 | 0.07 | 0.00769 |
| bowler:wkt | VALIDATION | ('T20I', 'middle') | 12261.00 | 0.05 | 0.05 | 0.00388 |
| bowler:wkt | VALIDATION | ('T20I', 'powerplay') | 8432.00 | 0.04 | 0.05 | -0.00271 |


## Out-of-period (VALIDATION) by wickets-remaining bin
| stream | period | group | rows | actual | expected | residual |
|---|---|---|---|---|---|---|
| batter:runs | VALIDATION | ('IPL', '10-8') | 9416.00 | 1.57 | 1.40 | 0.17 |
| batter:runs | VALIDATION | ('IPL', '7-1') | 6885.00 | 1.49 | 1.45 | 0.04 |
| batter:runs | VALIDATION | ('T20I', '10-8') | 13217.00 | 1.35 | 1.30 | 0.05 |
| batter:runs | VALIDATION | ('T20I', '7-1') | 12222.00 | 1.30 | 1.34 | -0.04 |
| batter:dismissal | VALIDATION | ('IPL', '10-8') | 9416.00 | 0.04 | 0.05 | -0.00275 |
| batter:dismissal | VALIDATION | ('IPL', '7-1') | 6885.00 | 0.06 | 0.06 | 0.00268 |
| batter:dismissal | VALIDATION | ('T20I', '10-8') | 13217.00 | 0.05 | 0.05 | -0.00131 |
| batter:dismissal | VALIDATION | ('T20I', '7-1') | 12222.00 | 0.07 | 0.06 | 0.00723 |
| bowler:charged | VALIDATION | ('IPL', '10-8') | 9784.00 | 1.55 | 1.40 | 0.16 |
| bowler:charged | VALIDATION | ('IPL', '7-1') | 7208.00 | 1.48 | 1.44 | 0.04 |
| bowler:charged | VALIDATION | ('T20I', '10-8') | 13687.00 | 1.35 | 1.30 | 0.05 |
| bowler:charged | VALIDATION | ('T20I', '7-1') | 12697.00 | 1.30 | 1.34 | -0.04 |
| bowler:wkt | VALIDATION | ('IPL', '10-8') | 9784.00 | 0.04 | 0.04 | -0.00233 |
| bowler:wkt | VALIDATION | ('IPL', '7-1') | 7208.00 | 0.06 | 0.05 | 0.00321 |
| bowler:wkt | VALIDATION | ('T20I', '10-8') | 13687.00 | 0.05 | 0.05 | -0.00118 |
| bowler:wkt | VALIDATION | ('T20I', '7-1') | 12697.00 | 0.06 | 0.06 | 0.00667 |


## Out-of-period (VALIDATION) by expected decile
| stream | period | group | rows | actual | expected | residual |
|---|---|---|---|---|---|---|
| batter:runs | VALIDATION | 0 | 4174.00 | 1.17 | 1.21 | -0.04 |
| batter:runs | VALIDATION | 1 | 4174.00 | 1.26 | 1.24 | 0.02 |
| batter:runs | VALIDATION | 2 | 4174.00 | 1.24 | 1.26 | -0.03 |
| batter:runs | VALIDATION | 3 | 4174.00 | 1.34 | 1.27 | 0.07 |
| batter:runs | VALIDATION | 4 | 4174.00 | 1.37 | 1.32 | 0.05 |
| batter:runs | VALIDATION | 5 | 4174.00 | 1.50 | 1.36 | 0.13 |
| batter:runs | VALIDATION | 6 | 4174.00 | 1.48 | 1.37 | 0.10 |
| batter:runs | VALIDATION | 7 | 4174.00 | 1.52 | 1.41 | 0.12 |
| batter:runs | VALIDATION | 8 | 4174.00 | 1.50 | 1.51 | -0.01 |
| batter:runs | VALIDATION | 9 | 4174.00 | 1.68 | 1.62 | 0.06 |
| batter:dismissal | VALIDATION | 0 | 4174.00 | 0.04 | 0.04 | -0.00158 |
| batter:dismissal | VALIDATION | 1 | 4174.00 | 0.04 | 0.04 | -0.000103 |
| batter:dismissal | VALIDATION | 2 | 4174.00 | 0.05 | 0.05 | 0.000667 |
| batter:dismissal | VALIDATION | 3 | 4174.00 | 0.05 | 0.05 | -0.000379 |
| batter:dismissal | VALIDATION | 4 | 4174.00 | 0.05 | 0.05 | 1.44e-05 |
| batter:dismissal | VALIDATION | 5 | 4174.00 | 0.04 | 0.05 | -0.00568 |
| batter:dismissal | VALIDATION | 6 | 4174.00 | 0.05 | 0.05 | -0.00356 |
| batter:dismissal | VALIDATION | 7 | 4174.00 | 0.06 | 0.06 | 0.00515 |
| batter:dismissal | VALIDATION | 8 | 4174.00 | 0.09 | 0.08 | 0.00943 |
| batter:dismissal | VALIDATION | 9 | 4174.00 | 0.09 | 0.08 | 0.01 |
| bowler:charged | VALIDATION | 0 | 4338.00 | 1.17 | 1.21 | -0.04 |
| bowler:charged | VALIDATION | 1 | 4338.00 | 1.27 | 1.24 | 0.03 |
| bowler:charged | VALIDATION | 2 | 4337.00 | 1.24 | 1.27 | -0.03 |
| bowler:charged | VALIDATION | 3 | 4338.00 | 1.36 | 1.28 | 0.08 |
| bowler:charged | VALIDATION | 4 | 4337.00 | 1.36 | 1.32 | 0.05 |
| bowler:charged | VALIDATION | 5 | 4338.00 | 1.48 | 1.37 | 0.11 |
| bowler:charged | VALIDATION | 6 | 4337.00 | 1.48 | 1.37 | 0.10 |
| bowler:charged | VALIDATION | 7 | 4338.00 | 1.51 | 1.41 | 0.11 |
| bowler:charged | VALIDATION | 8 | 4337.00 | 1.52 | 1.50 | 0.02 |
| bowler:charged | VALIDATION | 9 | 4338.00 | 1.63 | 1.60 | 0.03 |
| bowler:wkt | VALIDATION | 0 | 4338.00 | 0.04 | 0.04 | -0.00111 |
| bowler:wkt | VALIDATION | 1 | 4338.00 | 0.04 | 0.04 | 0.00227 |
| bowler:wkt | VALIDATION | 2 | 4337.00 | 0.04 | 0.04 | -0.00034 |
| bowler:wkt | VALIDATION | 3 | 4338.00 | 0.04 | 0.04 | -0.0031 |
| bowler:wkt | VALIDATION | 4 | 4337.00 | 0.05 | 0.05 | -0.000155 |
| bowler:wkt | VALIDATION | 5 | 4338.00 | 0.05 | 0.05 | -0.00129 |
| bowler:wkt | VALIDATION | 6 | 4337.00 | 0.04 | 0.05 | -0.00429 |
| bowler:wkt | VALIDATION | 7 | 4338.00 | 0.06 | 0.05 | 0.01 |
| bowler:wkt | VALIDATION | 8 | 4337.00 | 0.07 | 0.07 | 0.00641 |
| bowler:wkt | VALIDATION | 9 | 4338.00 | 0.08 | 0.07 | 0.00635 |


## Stability over time (all fitted periods) by year
| stream | period | group | rows | actual | expected | residual |
|---|---|---|---|---|---|---|
| batter:runs | TRAIN | ('IPL', 2022) | 17207.00 | 1.34 | 1.42 | -0.08 |
| batter:runs | TRAIN | ('IPL', 2023) | 17147.00 | 1.41 | 1.42 | -0.00475 |
| batter:runs | TRAIN | ('IPL', 2024) | 16374.00 | 1.51 | 1.41 | 0.09 |
| batter:runs | TRAIN | ('T20I', 2022) | 23069.00 | 1.31 | 1.32 | -0.02 |
| batter:runs | TRAIN | ('T20I', 2023) | 14109.00 | 1.34 | 1.32 | 0.02 |
| batter:runs | TRAIN | ('T20I', 2024) | 22945.00 | 1.33 | 1.32 | 0.007 |
| batter:runs | VALIDATION | ('IPL', 2025) | 16301.00 | 1.53 | 1.42 | 0.11 |
| batter:runs | VALIDATION | ('T20I', 2025) | 25439.00 | 1.32 | 1.32 | 0.00415 |
| batter:dismissal | TRAIN | ('IPL', 2022) | 17207.00 | 0.05 | 0.05 | -0.000672 |
| batter:dismissal | TRAIN | ('IPL', 2023) | 17147.00 | 0.05 | 0.05 | -0.000262 |
| batter:dismissal | TRAIN | ('IPL', 2024) | 16374.00 | 0.05 | 0.05 | 0.000538 |
| batter:dismissal | TRAIN | ('T20I', 2022) | 23069.00 | 0.05 | 0.06 | -0.00289 |
| batter:dismissal | TRAIN | ('T20I', 2023) | 14109.00 | 0.06 | 0.06 | -0.000631 |
| batter:dismissal | TRAIN | ('T20I', 2024) | 22945.00 | 0.06 | 0.06 | 0.00307 |
| batter:dismissal | VALIDATION | ('IPL', 2025) | 16301.00 | 0.05 | 0.05 | -0.000461 |
| batter:dismissal | VALIDATION | ('T20I', 2025) | 25439.00 | 0.06 | 0.06 | 0.00279 |
| bowler:charged | TRAIN | ('IPL', 2022) | 17909.00 | 1.34 | 1.42 | -0.08 |
| bowler:charged | TRAIN | ('IPL', 2023) | 17769.00 | 1.41 | 1.42 | -0.00444 |
| bowler:charged | TRAIN | ('IPL', 2024) | 17103.00 | 1.50 | 1.41 | 0.08 |
| bowler:charged | TRAIN | ('T20I', 2022) | 23959.00 | 1.31 | 1.32 | -0.02 |
| bowler:charged | TRAIN | ('T20I', 2023) | 14635.00 | 1.33 | 1.32 | 0.02 |
| bowler:charged | TRAIN | ('T20I', 2024) | 23837.00 | 1.33 | 1.32 | 0.00724 |
| bowler:charged | VALIDATION | ('IPL', 2025) | 16992.00 | 1.52 | 1.41 | 0.11 |
| bowler:charged | VALIDATION | ('T20I', 2025) | 26384.00 | 1.32 | 1.32 | 0.00548 |
| bowler:wkt | TRAIN | ('IPL', 2022) | 17909.00 | 0.05 | 0.05 | -0.000551 |
| bowler:wkt | TRAIN | ('IPL', 2023) | 17769.00 | 0.05 | 0.05 | -7.85e-05 |
| bowler:wkt | TRAIN | ('IPL', 2024) | 17103.00 | 0.05 | 0.05 | 0.000696 |
| bowler:wkt | TRAIN | ('T20I', 2022) | 23959.00 | 0.05 | 0.05 | -0.00299 |
| bowler:wkt | TRAIN | ('T20I', 2023) | 14635.00 | 0.05 | 0.05 | -0.000242 |
| bowler:wkt | TRAIN | ('T20I', 2024) | 23837.00 | 0.06 | 0.05 | 0.00316 |
| bowler:wkt | VALIDATION | ('IPL', 2025) | 16992.00 | 0.05 | 0.05 | 2.02e-05 |
| bowler:wkt | VALIDATION | ('T20I', 2025) | 26384.00 | 0.05 | 0.05 | 0.0026 |


## Limitations
- The offset makes the identity hold by construction on TRAIN; VALIDATION is the genuine check.
- Binary streams use a beta-binomial shrink; expectations are clipped to [0, 1].
- DLS-affected innings are excluded by mask (not imputed); no delivery rows are deleted.
