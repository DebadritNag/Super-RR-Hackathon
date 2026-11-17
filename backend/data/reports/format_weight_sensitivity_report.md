# Format weight sensitivity report (Decision 1)

## 1. Status and interpretation

- proxy_run: yes
- pressure_status: PENDING_PHASE3
- score_label: PROXY_NOT_PRESSURE
- not_for_publication: yes
- default configuration: w70_30 (PROVISIONAL_NOT_VALIDATED, config status PROVISIONAL)
- config version: format_weights_v1, hash `a77cb111d1efe20e2637fed21f528bb5ee2d4e627e0963338b73d64ef1ec7417`
- eligibility level for the primary run: P25

Pressure is not defined until Phase 3. Every number in this report is an all-situation descriptive proxy (innings 1 and 2, all match situations), labelled PROXY_NOT_PRESSURE, and is not for publication. The harness is generic and accepts pressure samples unchanged.

The 70:30 weighting is a provisional default, not a validated choice. Format scores are computed independently. A combined score exists only for players eligible in both formats; missing format observations are never replaced by zero.

## 2. Configurations

| id | IPL weight | T20I weight |
|---|---|---|
| w100_0 | 1.00 | 0.00 |
| w85_15 | 0.85 | 0.15 |
| w80_20 | 0.80 | 0.20 |
| w70_30 | 0.70 | 0.30 |
| w60_40 | 0.60 | 0.40 |
| w55_45 | 0.55 | 0.45 |
| w50_50 | 0.50 | 0.50 |
| w0_100 | 0.00 | 1.00 |

## 3. Method notes

- **eligibility**: Weight independent: percentile rule on the balls measure per format and role (batter balls faced, bowler legal balls), recomputed from the data.
- **format_scores**: Independent per format; z-score within the format's eligible pool.
- **combined**: Only BOTH_FORMATS_VALID players; others NULL with an explicit status.
- **missing_formats**: Never zero-filled and never imputed.
- **degenerate**: 100:0 and 0:100 use the same combined population as every other configuration, so their ranks equal the IPL or T20I z-score ranks within that population.

Format eligibility thresholds (balls, percentile rule):

| role | IPL | T20I |
|---|---|---|
| batter | 14 | 15 |
| bowler | 36 | 36 |

## 4. Batters

Players seen in either format: 824.

| combined status | players |
|---|---|
| BOTH_FORMATS_VALID | 133 |
| SINGLE_FORMAT_IPL_ONLY | 124 |
| SINGLE_FORMAT_T20I_ONLY | 373 |
| NO_VALID_FORMAT | 194 |

| format | ELIGIBLE | OBSERVED_NOT_ELIGIBLE | NOT_OBSERVED |
|---|---|---|---|
| IPL | 257 | 84 | 483 |
| T20I | 506 | 159 | 159 |

Combined population: 133 players, identical across configurations: yes. Single-format players are ranked only in their own format list and excluded from the combined ranking.

### Sensitivity versus the default configuration

| config | n ranked | Top 10 overlap | Spearman | mean abs rank change | max abs rank change | entering Top 10 | leaving Top 10 |
|---|---|---|---|---|---|---|---|
| w100_0 | 133 | 7 | 0.93 | 10.14 | 51 | 3 | 3 |
| w85_15 | 133 | 8 | 0.98 | 5.38 | 28 | 2 | 2 |
| w80_20 | 133 | 9 | 0.99 | 3.74 | 19 | 1 | 1 |
| w70_30 | 133 | 10 | 1.00 | 0.00 | 0 | 0 | 0 |
| w60_40 | 133 | 9 | 0.99 | 3.76 | 18 | 1 | 1 |
| w55_45 | 133 | 9 | 0.98 | 5.38 | 24 | 1 | 1 |
| w50_50 | 133 | 9 | 0.97 | 6.92 | 29 | 1 | 1 |
| w0_100 | 133 | 7 | 0.75 | 20.74 | 75 | 3 | 3 |

### Pairwise Top 10 overlap

|  | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 10 | 9 | 8 | 7 | 6 | 6 | 6 | 4 |
| w85_15 | 9 | 10 | 9 | 8 | 7 | 7 | 7 | 5 |
| w80_20 | 8 | 9 | 10 | 9 | 8 | 8 | 8 | 6 |
| w70_30 | 7 | 8 | 9 | 10 | 9 | 9 | 9 | 7 |
| w60_40 | 6 | 7 | 8 | 9 | 10 | 10 | 10 | 8 |
| w55_45 | 6 | 7 | 8 | 9 | 10 | 10 | 10 | 8 |
| w50_50 | 6 | 7 | 8 | 9 | 10 | 10 | 10 | 8 |
| w0_100 | 4 | 5 | 6 | 7 | 8 | 8 | 8 | 10 |

### Pairwise Spearman (n = 133 in every cell)

|  | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 1.00 | 0.98 | 0.97 | 0.93 | 0.88 | 0.85 | 0.82 | 0.50 |
| w85_15 | 0.98 | 1.00 | 1.00 | 0.98 | 0.95 | 0.92 | 0.90 | 0.62 |
| w80_20 | 0.97 | 1.00 | 1.00 | 0.99 | 0.97 | 0.95 | 0.93 | 0.67 |
| w70_30 | 0.93 | 0.98 | 0.99 | 1.00 | 0.99 | 0.98 | 0.97 | 0.75 |
| w60_40 | 0.88 | 0.95 | 0.97 | 0.99 | 1.00 | 1.00 | 0.99 | 0.83 |
| w55_45 | 0.85 | 0.92 | 0.95 | 0.98 | 1.00 | 1.00 | 1.00 | 0.86 |
| w50_50 | 0.82 | 0.90 | 0.93 | 0.97 | 0.99 | 1.00 | 1.00 | 0.88 |
| w0_100 | 0.50 | 0.62 | 0.67 | 0.75 | 0.83 | 0.86 | 0.88 | 1.00 |

### Degenerate configurations

- w100_0: ranks equal single-format z-score ranks within the same population of 133: yes
- w0_100: ranks equal single-format z-score ranks within the same population of 133: yes

### Biggest movers versus default

| config | player_id | default rank | config rank | change |
|---|---|---|---|---|
| w100_0 | 6,280 | 60 | 111 | 51 |
| w100_0 | 1,187 | 86 | 41 | -45 |
| w100_0 | 479 | 97 | 59 | -38 |
| w85_15 | 6,280 | 60 | 88 | 28 |
| w85_15 | 1,187 | 86 | 59 | -27 |
| w85_15 | 3,629 | 79 | 58 | -21 |
| w80_20 | 6,280 | 60 | 79 | 19 |
| w80_20 | 1,187 | 86 | 69 | -17 |
| w80_20 | 7,260 | 69 | 53 | -16 |
| w70_30 | 47 | 59 | 59 | 0 |
| w70_30 | 126 | 62 | 62 | 0 |
| w70_30 | 143 | 13 | 13 | 0 |
| w60_40 | 6,280 | 60 | 42 | -18 |
| w60_40 | 3,629 | 79 | 95 | 16 |
| w60_40 | 3,727 | 92 | 76 | -16 |
| w55_45 | 6,280 | 60 | 36 | -24 |
| w55_45 | 3,629 | 79 | 102 | 23 |
| w55_45 | 796 | 108 | 87 | -21 |
| w50_50 | 6,280 | 60 | 31 | -29 |
| w50_50 | 7,260 | 69 | 98 | 29 |
| w50_50 | 3,629 | 79 | 107 | 28 |
| w0_100 | 7,341 | 7 | 82 | 75 |
| w0_100 | 796 | 108 | 34 | -74 |
| w0_100 | 8,654 | 33 | 103 | 70 |

### ADJUSTED_ESTIMATE (separate section)

Weights renormalised over the eligible formats of each player. Not a combined score, not used in the default ranking, and not comparable across single-format and two-format players. Players with an estimate: 630.

## 5. Bowlers

Players seen in either format: 596.

| combined status | players |
|---|---|
| BOTH_FORMATS_VALID | 114 |
| SINGLE_FORMAT_IPL_ONLY | 88 |
| SINGLE_FORMAT_T20I_ONLY | 260 |
| NO_VALID_FORMAT | 134 |

| format | ELIGIBLE | OBSERVED_NOT_ELIGIBLE | NOT_OBSERVED |
|---|---|---|---|
| IPL | 202 | 58 | 336 |
| T20I | 374 | 105 | 117 |

Combined population: 114 players, identical across configurations: yes. Single-format players are ranked only in their own format list and excluded from the combined ranking.

### Sensitivity versus the default configuration

| config | n ranked | Top 10 overlap | Spearman | mean abs rank change | max abs rank change | entering Top 10 | leaving Top 10 |
|---|---|---|---|---|---|---|---|
| w100_0 | 114 | 7 | 0.94 | 8.95 | 33 | 3 | 3 |
| w85_15 | 114 | 9 | 0.98 | 5.21 | 21 | 1 | 1 |
| w80_20 | 114 | 10 | 0.99 | 3.65 | 15 | 0 | 0 |
| w70_30 | 114 | 10 | 1.00 | 0.00 | 0 | 0 | 0 |
| w60_40 | 114 | 10 | 0.98 | 4.37 | 20 | 0 | 0 |
| w55_45 | 114 | 10 | 0.97 | 5.98 | 28 | 0 | 0 |
| w50_50 | 114 | 9 | 0.94 | 8.40 | 42 | 1 | 1 |
| w0_100 | 114 | 5 | 0.49 | 24.81 | 99 | 5 | 5 |

### Pairwise Top 10 overlap

|  | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 10 | 8 | 7 | 7 | 7 | 7 | 6 | 3 |
| w85_15 | 8 | 10 | 9 | 9 | 9 | 9 | 8 | 4 |
| w80_20 | 7 | 9 | 10 | 10 | 10 | 10 | 9 | 5 |
| w70_30 | 7 | 9 | 10 | 10 | 10 | 10 | 9 | 5 |
| w60_40 | 7 | 9 | 10 | 10 | 10 | 10 | 9 | 5 |
| w55_45 | 7 | 9 | 10 | 10 | 10 | 10 | 9 | 5 |
| w50_50 | 6 | 8 | 9 | 9 | 9 | 9 | 10 | 5 |
| w0_100 | 3 | 4 | 5 | 5 | 5 | 5 | 5 | 10 |

### Pairwise Spearman (n = 114 in every cell)

|  | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 1.00 | 0.99 | 0.97 | 0.94 | 0.87 | 0.83 | 0.77 | 0.20 |
| w85_15 | 0.99 | 1.00 | 1.00 | 0.98 | 0.93 | 0.90 | 0.85 | 0.34 |
| w80_20 | 0.97 | 1.00 | 1.00 | 0.99 | 0.95 | 0.93 | 0.88 | 0.39 |
| w70_30 | 0.94 | 0.98 | 0.99 | 1.00 | 0.98 | 0.97 | 0.94 | 0.49 |
| w60_40 | 0.87 | 0.93 | 0.95 | 0.98 | 1.00 | 1.00 | 0.98 | 0.62 |
| w55_45 | 0.83 | 0.90 | 0.93 | 0.97 | 1.00 | 1.00 | 0.99 | 0.67 |
| w50_50 | 0.77 | 0.85 | 0.88 | 0.94 | 0.98 | 0.99 | 1.00 | 0.75 |
| w0_100 | 0.20 | 0.34 | 0.39 | 0.49 | 0.62 | 0.67 | 0.75 | 1.00 |

### Degenerate configurations

- w100_0: ranks equal single-format z-score ranks within the same population of 114: yes
- w0_100: ranks equal single-format z-score ranks within the same population of 114: yes

### Biggest movers versus default

| config | player_id | default rank | config rank | change |
|---|---|---|---|---|
| w100_0 | 3,648 | 40 | 73 | 33 |
| w100_0 | 22,920 | 43 | 76 | 33 |
| w100_0 | 19,316 | 88 | 56 | -32 |
| w85_15 | 838 | 47 | 26 | -21 |
| w85_15 | 4,823 | 74 | 94 | 20 |
| w85_15 | 19,316 | 88 | 71 | -17 |
| w80_20 | 4,692 | 70 | 85 | 15 |
| w80_20 | 4,823 | 74 | 88 | 14 |
| w80_20 | 838 | 47 | 34 | -13 |
| w70_30 | 152 | 50 | 50 | 0 |
| w70_30 | 278 | 12 | 12 | 0 |
| w70_30 | 295 | 55 | 55 | 0 |
| w60_40 | 4,823 | 74 | 54 | -20 |
| w60_40 | 1,318 | 15 | 31 | 16 |
| w60_40 | 3,648 | 40 | 24 | -16 |
| w55_45 | 1,318 | 15 | 43 | 28 |
| w55_45 | 4,823 | 74 | 49 | -25 |
| w55_45 | 838 | 47 | 68 | 21 |
| w50_50 | 4,823 | 74 | 32 | -42 |
| w50_50 | 1,318 | 15 | 54 | 39 |
| w50_50 | 838 | 47 | 79 | 32 |
| w0_100 | 1,318 | 15 | 114 | 99 |
| w0_100 | 4,489 | 18 | 108 | 90 |
| w0_100 | 3,628 | 22 | 105 | 83 |

### ADJUSTED_ESTIMATE (separate section)

Weights renormalised over the eligible formats of each player. Not a combined score, not used in the default ranking, and not comparable across single-format and two-format players. Players with an estimate: 462.

## 6. Robustness to the eligibility level

### Level P10

| role | IPL threshold | T20I threshold | combined pop | pop at primary | entering | leaving | min Top 10 overlap vs default | min Spearman vs default |
|---|---|---|---|---|---|---|---|---|
| batter | 5 | 5 | 162 | 133 | 29 | 0 | 7 | 0.74 |
| bowler | 18 | 17 | 134 | 114 | 20 | 0 | 5 | 0.47 |

### Level P50

| role | IPL threshold | T20I threshold | combined pop | pop at primary | entering | leaving | min Top 10 overlap vs default | min Spearman vs default |
|---|---|---|---|---|---|---|---|---|
| batter | 53 | 50 | 94 | 133 | 0 | 39 | 7 | 0.66 |
| bowler | 162 | 97 | 72 | 114 | 0 | 42 | 5 | 0.50 |

## 7. Technical appendix (PROXY_NOT_PRESSURE, not for publication)

Batter default-configuration Top 10 (proxy):

| player_id | name |
|---|---|
| 50,284 | Vaibhav Sooryavanshi |
| 6,281 | Abhishek Sharma |
| 4,847 | Finn Allen |
| 6,396 | Tim David |
| 2,367 | Travis Head |
| 5,553 | Phil Salt |
| 7,341 | Jake McGurk |
| 1,318 | Andre Russell |
| 37,052 | Naman Dhir |
| 1,699 | Suryakumar Yadav |

Bowler default-configuration Top 10 (proxy):

| player_id | name |
|---|---|
| 6,256 | Varun Chakravarthy |
| 4,900 | Wanindu Hasaranga |
| 830 | Josh Hazlewood |
| 8,661 | Matheesha Pathirana |
| 3,644 | Kuldeep Yadav |
| 4,722 | Rashid Khan |
| 7,967 | Noor Ahmad |
| 1,612 | Yuzvendra Chahal |
| 2,933 | Jasprit Bumrah |
| 2,985 | Mark Wood |

