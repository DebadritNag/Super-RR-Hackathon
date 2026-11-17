# Phase 5 ranking stability

Status: EXPERIMENTAL_NOT_VALIDATED. PROVISIONAL and descriptive. Not an official ranking and not a published Top 10; nothing here is validated. TEST outcomes: not used. Cricsheet: not used.

Primary definition `any|q0.75` is PROVISIONAL. Bootstrap: 1000 match-cluster resamples, seed 20260512, baseline, TRAIN-fitted thresholds and shrinkage parameters held fixed. Shrinkage `shrink_tau4`. Pools use the frozen unvalidated working-pool ball thresholds. Code version `0061c9d62abd2c99`. Reading guide: 'inclusion' is the share of resamples in which a player is in the Top 10 of the pool; 'rank interval' is the 2.5% to 97.5% range of the player's rank. Phase 4's own report `phase4_ranking_stability.md` is untouched.

## 0. Preconditions
- Phase 4 scores reproduced: max abs difference 0.00e+00 over 1345 players (reproduces = True).

## 1. Format x role cells, all four definitions
'expected overlap (point)' is the mean number of the point-estimate Top 10 that are in the Top 10 of a resample. 'expected overlap (two resamples)' is the mean overlap between two independent resamples' Top 10. Both are out of `top-10 size`; rows marked trivial have a pool of 10 or fewer, where the Top 10 is the whole pool.

| definition | format | role | status | pool | top-10 size | trivial | overlap (point) | overlap (two resamples) | mean Spearman | point Top 10 with inclusion >= 0.5 | players with inclusion 0.2 to 0.8 | median rank-interval width (point Top 10) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| any\|q0.75 | IPL | batter | ESTIMATED | 132 | 10 | no | 5.24 | 3.81 | 0.80 | 4 | 16 | 54.24 |
| any\|q0.9 | IPL | batter | ESTIMATED | 81 | 10 | no | 6.08 | 4.90 | 0.82 | 6 | 16 | 31.00 |
| chase\|q0.75 | IPL | batter | ESTIMATED | 94 | 10 | no | 5.29 | 3.85 | 0.81 | 5 | 19 | 39.00 |
| chase\|q0.9 | IPL | batter | ESTIMATED | 35 | 10 | no | 6.47 | 5.58 | 0.80 | 7 | 17 | 14.32 |
| any\|q0.75 | T20I | batter | ESTIMATED | 243 | 10 | no | 4.88 | 3.11 | 0.82 | 5 | 13 | 51.85 |
| any\|q0.9 | T20I | batter | ESTIMATED | 117 | 10 | no | 5.70 | 4.43 | 0.84 | 6 | 18 | 25.00 |
| chase\|q0.75 | T20I | batter | ESTIMATED | 144 | 10 | no | 4.61 | 3.20 | 0.82 | 3 | 19 | 55.27 |
| chase\|q0.9 | T20I | batter | ESTIMATED | 50 | 10 | no | 6.41 | 5.13 | 0.84 | 10 | 18 | 14.50 |
| any\|q0.75 | IPL | bowler | ESTIMATED | 80 | 10 | no | 6.20 | 5.29 | 0.76 | 5 | 12 | 24.00 |
| any\|q0.9 | IPL | bowler | ESTIMATED | 38 | 10 | no | 5.79 | 4.71 | 0.72 | 6 | 19 | 19.00 |
| chase\|q0.75 | IPL | bowler | ESTIMATED | 48 | 10 | no | 6.64 | 5.56 | 0.77 | 8 | 11 | 18.93 |
| chase\|q0.9 | IPL | bowler | ESTIMATED | 14 | 10 | no | 6.80 | 5.96 | 0.68 | 10 | 12 | 8.30 |
| any\|q0.75 | T20I | bowler | ESTIMATED | 141 | 10 | no | 5.53 | 4.18 | 0.77 | 5 | 13 | 53.54 |
| any\|q0.9 | T20I | bowler | ESTIMATED | 68 | 10 | no | 5.68 | 4.37 | 0.76 | 6 | 16 | 25.50 |
| chase\|q0.75 | T20I | bowler | ESTIMATED | 85 | 10 | no | 5.95 | 4.52 | 0.74 | 6 | 16 | 32.50 |
| chase\|q0.9 | T20I | bowler | ESTIMATED | 24 | 10 | no | 6.07 | 5.48 | 0.63 | 6 | 18 | 15.50 |


### Point-estimate Top 10 of the primary definition with inclusion probabilities (internal diagnostic, not a ranking)

| format | role | player_id | point rank | Top-10 inclusion | rank lo | rank median | rank hi | pressure balls | matches | n_eff |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | 167 | 1.00 | 0.84 | 1.00 | 3.00 | 32.35 | 75.00 | 13 | 9.30 |
| IPL | batter | 4,821 | 2.00 | 0.64 | 1.00 | 4.00 | 28.98 | 40.00 | 7 | 4.65 |
| IPL | batter | 1,699 | 3.00 | 0.73 | 1.00 | 7.00 | 33.00 | 215.00 | 18 | 12.07 |
| IPL | batter | 4,722 | 4.00 | 0.50 | 1.00 | 11.00 | 70.00 | 158.00 | 19 | 9.62 |
| IPL | batter | 2,639 | 5.00 | 0.52 | 2.00 | 10.00 | 50.02 | 292.00 | 24 | 13.28 |
| IPL | batter | 4,708 | 6.00 | 0.49 | 1.00 | 11.00 | 74.00 | 224.00 | 17 | 11.96 |
| IPL | batter | 20,006 | 7.00 | 0.41 | 1.00 | 10.00 | 54.00 | 41.00 | 6 | 4.96 |
| IPL | batter | 6,281 | 8.00 | 0.42 | 2.00 | 12.50 | 57.48 | 87.00 | 13 | 6.39 |
| IPL | batter | 6,396 | 9.00 | 0.38 | 2.00 | 15.00 | 86.02 | 219.00 | 20 | 14.05 |
| IPL | batter | 7,216 | 10.00 | 0.33 | 1.00 | 16.00 | 94.00 | 72.00 | 7 | 4.73 |
| T20I | batter | 3,672 | 1.00 | 0.55 | 1.00 | 2.00 | 51.00 | 31.00 | 8 | 4.98 |
| T20I | batter | 6,396 | 2.00 | 0.60 | 1.00 | 6.00 | 48.00 | 70.00 | 8 | 4.68 |
| T20I | batter | 4,986 | 3.00 | 0.66 | 1.00 | 7.00 | 42.00 | 402.00 | 30 | 17.62 |
| T20I | batter | 2,633 | 4.00 | 0.56 | 1.00 | 9.00 | 52.00 | 164.00 | 19 | 12.14 |
| T20I | batter | 6,574 | 5.00 | 0.51 | 1.00 | 7.00 | 30.00 | 43.00 | 5 | 3.46 |
| T20I | batter | 2,436 | 6.00 | 0.45 | 1.00 | 13.00 | 126.25 | 163.00 | 16 | 10.01 |
| T20I | batter | 5,553 | 7.00 | 0.45 | 1.00 | 11.00 | 63.00 | 72.00 | 4 | 3.16 |
| T20I | batter | 7,808 | 8.00 | 0.40 | 1.00 | 16.00 | 159.32 | 82.00 | 8 | 6.52 |
| T20I | batter | 1,596 | 9.00 | 0.35 | 2.00 | 16.00 | 80.00 | 95.00 | 11 | 7.05 |
| T20I | batter | 1,318 | 10.00 | 0.35 | 1.30 | 13.00 | 54.00 | 54.00 | 5 | 3.04 |
| IPL | bowler | 781 | 1.00 | 0.98 | 1.00 | 1.50 | 10.00 | 273.00 | 21 | 16.03 |
| IPL | bowler | 5,944 | 2.00 | 0.91 | 1.00 | 3.00 | 18.00 | 235.00 | 26 | 18.38 |
| IPL | bowler | 4,489 | 3.00 | 0.84 | 1.00 | 4.00 | 23.00 | 219.00 | 17 | 13.71 |
| IPL | bowler | 2,933 | 4.00 | 0.85 | 1.00 | 5.00 | 22.00 | 190.00 | 19 | 13.18 |
| IPL | bowler | 8,661 | 5.00 | 0.84 | 1.00 | 5.00 | 20.02 | 323.00 | 16 | 14.33 |
| IPL | bowler | 4,101 | 6.00 | 0.46 | 2.00 | 9.00 | 29.00 | 92.00 | 11 | 6.30 |
| IPL | bowler | 3,644 | 7.00 | 0.44 | 2.00 | 12.00 | 44.02 | 343.00 | 21 | 18.47 |
| IPL | bowler | 2,878 | 8.00 | 0.41 | 3.00 | 12.00 | 38.07 | 239.00 | 18 | 13.70 |
| IPL | bowler | 5,577 | 9.00 | 0.21 | 6.00 | 15.00 | 32.00 | 151.00 | 10 | 7.83 |
| IPL | bowler | 305 | 10.00 | 0.25 | 4.00 | 17.00 | 47.00 | 287.00 | 22 | 17.06 |
| T20I | bowler | 4,373 | 1.00 | 0.96 | 1.00 | 2.00 | 13.00 | 379.00 | 26 | 19.60 |
| T20I | bowler | 5,979 | 2.00 | 0.92 | 1.00 | 2.00 | 17.00 | 161.00 | 14 | 10.41 |
| T20I | bowler | 4,722 | 3.00 | 0.65 | 1.00 | 7.00 | 57.02 | 256.00 | 18 | 14.28 |
| T20I | bowler | 6,355 | 4.00 | 0.63 | 1.00 | 8.00 | 52.05 | 148.00 | 18 | 12.88 |
| T20I | bowler | 2,933 | 5.00 | 0.50 | 1.00 | 9.00 | 63.00 | 81.00 | 9 | 6.54 |
| T20I | bowler | 4,823 | 6.00 | 0.46 | 2.00 | 11.00 | 43.02 | 200.00 | 15 | 12.29 |
| T20I | bowler | 20,704 | 7.00 | 0.40 | 2.62 | 12.50 | 52.38 | 97.00 | 9 | 7.49 |
| T20I | bowler | 7,240 | 8.00 | 0.42 | 1.00 | 14.00 | 86.20 | 154.00 | 16 | 13.95 |
| T20I | bowler | 5,837 | 9.00 | 0.27 | 3.00 | 18.00 | 60.00 | 176.00 | 17 | 12.77 |
| T20I | bowler | 360 | 10.00 | 0.32 | 2.00 | 19.00 | 87.23 | 107.00 | 14 | 10.34 |


## 2. Format-combined pools (players eligible in both formats, 70:30)

| format | role | status | pool | trivial | overlap (point) | mean Jaccard | mean Spearman |
|---|---|---|---|---|---|---|---|
| COMBINED_w70_30 | batter | ESTIMATED | 48 | no | 5.78 | 0.42 | 0.73 |
| COMBINED_w70_30 | bowler | ESTIMATED | 39 | no | 7.09 | 0.56 | 0.81 |


## 3. Phase x situation contexts of the primary definition
Each context re-aggregates the same stored residuals (no new model), refits the between-player variance on that context's TRAIN rows and uses that context's OWN working-pool threshold (P50 of its TRAIN ball counts; not validated, never borrowed from the overall cell). Contexts with fewer than 8 TRAIN players are `CONTEXT_NOT_ESTIMABLE`, with a pool below 5 `POOL_TOO_SMALL`. Filters cannot create reliability: a context that is thin stays thin.

| format | role | phase | situation | status | TRAIN players | pressure balls | pool | threshold balls | floor hit | overlap (point) | mean Spearman |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | ALL | ALL | ESTIMATED | 244 | 15,229 | 132 | 20 | yes | 5.24 | 0.80 |
| IPL | batter | ALL | chase | ESTIMATED | 210 | 7,797 | 111 | 14 | yes | 5.03 | 0.82 |
| IPL | batter | ALL | first_innings | ESTIMATED | 188 | 7,432 | 94 | 17 | yes | 5.57 | 0.79 |
| IPL | batter | death | ALL | ESTIMATED | 208 | 6,181 | 103 | 12 | yes | 5.21 | 0.83 |
| IPL | batter | death | chase | ESTIMATED | 169 | 3,726 | 89 | 10 | yes | 5.86 | 0.84 |
| IPL | batter | death | first_innings | ESTIMATED | 144 | 2,455 | 69 | 7 | yes | 5.82 | 0.77 |
| IPL | batter | middle | ALL | ESTIMATED | 175 | 7,301 | 91 | 18 | yes | 4.55 | 0.75 |
| IPL | batter | middle | chase | ESTIMATED | 140 | 3,453 | 68 | 13 | yes | 4.77 | 0.71 |
| IPL | batter | middle | first_innings | ESTIMATED | 131 | 3,848 | 64 | 17 | yes | 5.90 | 0.75 |
| IPL | batter | powerplay | ALL | ESTIMATED | 90 | 1,747 | 42 | 10 | yes | 5.96 | 0.75 |
| IPL | batter | powerplay | chase | ESTIMATED | 40 | 618 | 19 | 9 | yes | 6.15 | 0.61 |
| IPL | batter | powerplay | first_innings | ESTIMATED | 76 | 1,129 | 38 | 8 | yes | 7.28 | 0.82 |
| T20I | batter | ALL | ALL | ESTIMATED | 439 | 20,722 | 243 | 16 | yes | 4.88 | 0.82 |
| T20I | batter | ALL | chase | ESTIMATED | 347 | 9,741 | 199 | 11 | yes | 4.34 | 0.83 |
| T20I | batter | ALL | first_innings | ESTIMATED | 317 | 10,981 | 172 | 12 | yes | 4.70 | 0.78 |
| T20I | batter | death | ALL | ESTIMATED | 340 | 8,007 | 171 | 11 | yes | 5.37 | 0.84 |
| T20I | batter | death | chase | ESTIMATED | 275 | 4,158 | 159 | 7 | yes | 5.33 | 0.86 |
| T20I | batter | death | first_innings | ESTIMATED | 219 | 3,849 | 105 | 8 | yes | 5.33 | 0.80 |
| T20I | batter | middle | ALL | ESTIMATED | 309 | 10,546 | 179 | 12 | yes | 4.38 | 0.78 |
| T20I | batter | middle | chase | ESTIMATED | 223 | 4,679 | 122 | 9 | yes | 4.41 | 0.76 |
| T20I | batter | middle | first_innings | ESTIMATED | 202 | 5,867 | 114 | 11 | yes | 4.75 | 0.74 |
| T20I | batter | powerplay | ALL | ESTIMATED | 149 | 2,169 | 64 | 7 | yes | 6.08 | 0.76 |
| T20I | batter | powerplay | chase | ESTIMATED | 77 | 904 | 36 | 7 | yes | 5.89 | 0.72 |
| T20I | batter | powerplay | first_innings | ESTIMATED | 108 | 1,265 | 48 | 6 | yes | 4.97 | 0.75 |
| IPL | bowler | ALL | ALL | ESTIMATED | 163 | 15,939 | 80 | 49 | yes | 6.20 | 0.76 |
| IPL | bowler | ALL | chase | ESTIMATED | 135 | 8,224 | 74 | 32 | yes | 6.14 | 0.76 |
| IPL | bowler | ALL | first_innings | ESTIMATED | 137 | 7,715 | 68 | 30 | yes | 6.19 | 0.76 |
| IPL | bowler | death | ALL | ESTIMATED | 131 | 6,573 | 70 | 19 | yes | 5.85 | 0.73 |
| IPL | bowler | death | chase | ESTIMATED | 109 | 3,980 | 60 | 16 | yes | 5.74 | 0.74 |
| IPL | bowler | death | first_innings | ESTIMATED | 99 | 2,593 | 52 | 15 | yes | 5.98 | 0.73 |
| IPL | bowler | middle | ALL | ESTIMATED | 143 | 7,554 | 69 | 26 | yes | 6.10 | 0.74 |
| IPL | bowler | middle | chase | ESTIMATED | 116 | 3,598 | 67 | 14 | yes | 6.18 | 0.76 |
| IPL | bowler | middle | first_innings | ESTIMATED | 114 | 3,956 | 57 | 18 | yes | 5.28 | 0.77 |
| IPL | bowler | powerplay | ALL | ESTIMATED | 92 | 1,812 | 42 | 11 | yes | 5.66 | 0.72 |
| IPL | bowler | powerplay | chase | ESTIMATED | 45 | 646 | 21 | 9 | yes | 5.89 | 0.63 |
| IPL | bowler | powerplay | first_innings | ESTIMATED | 84 | 1,166 | 41 | 8 | yes | 5.26 | 0.70 |
| T20I | bowler | ALL | ALL | ESTIMATED | 296 | 21,544 | 141 | 29 | yes | 5.53 | 0.77 |
| T20I | bowler | ALL | chase | ESTIMATED | 220 | 10,202 | 121 | 18 | yes | 5.72 | 0.75 |
| T20I | bowler | ALL | first_innings | ESTIMATED | 240 | 11,342 | 121 | 18 | yes | 5.45 | 0.78 |
| T20I | bowler | death | ALL | ESTIMATED | 230 | 8,425 | 110 | 15 | yes | 4.60 | 0.74 |
| T20I | bowler | death | chase | ESTIMATED | 175 | 4,402 | 92 | 12 | yes | 4.73 | 0.76 |
| T20I | bowler | death | first_innings | ESTIMATED | 157 | 4,023 | 68 | 12 | yes | 4.81 | 0.74 |
| T20I | bowler | middle | ALL | ESTIMATED | 235 | 10,863 | 113 | 18 | yes | 5.23 | 0.75 |
| T20I | bowler | middle | chase | ESTIMATED | 158 | 4,860 | 72 | 13 | yes | 5.52 | 0.71 |
| T20I | bowler | middle | first_innings | ESTIMATED | 176 | 6,003 | 85 | 14 | yes | 5.82 | 0.79 |
| T20I | bowler | powerplay | ALL | ESTIMATED | 121 | 2,256 | 61 | 9 | yes | 5.68 | 0.77 |
| T20I | bowler | powerplay | chase | ESTIMATED | 53 | 940 | 19 | 11 | yes | 5.80 | 0.68 |
| T20I | bowler | powerplay | first_innings | ESTIMATED | 96 | 1,316 | 48 | 6 | yes | 5.81 | 0.75 |


### Spearman across contexts (same players, same format and role; at least 8 common players)

| format | role | context A | context B | common | Spearman | top-10 overlap share |
|---|---|---|---|---|---|---|
| IPL | batter | ALL\|ALL | ALL\|chase | 110 | 0.85 | 0.50 |
| IPL | batter | ALL\|ALL | ALL\|first_innings | 93 | 0.63 | 0.40 |
| IPL | batter | ALL\|ALL | death\|ALL | 92 | 0.87 | 0.50 |
| IPL | batter | ALL\|ALL | death\|chase | 80 | 0.78 | 0.30 |
| IPL | batter | ALL\|ALL | death\|first_innings | 67 | 0.62 | 0.10 |
| IPL | batter | ALL\|ALL | middle\|ALL | 91 | 0.56 | 0.30 |
| IPL | batter | ALL\|ALL | middle\|chase | 68 | 0.58 | 0.10 |
| IPL | batter | ALL\|ALL | middle\|first_innings | 64 | 0.34 | 0.10 |
| IPL | batter | ALL\|ALL | powerplay\|ALL | 41 | 0.53 | 0.40 |
| IPL | batter | ALL\|ALL | powerplay\|chase | 18 | 0.44 | 0.10 |
| IPL | batter | ALL\|ALL | powerplay\|first_innings | 38 | 0.53 | 0.40 |
| IPL | batter | ALL\|chase | ALL\|first_innings | 75 | 0.04 | 0.00 |
| IPL | batter | ALL\|chase | death\|ALL | 83 | 0.75 | 0.50 |
| IPL | batter | ALL\|chase | death\|chase | 77 | 0.86 | 0.70 |
| IPL | batter | ALL\|chase | death\|first_innings | 55 | 0.21 | 0.00 |
| IPL | batter | ALL\|chase | middle\|ALL | 81 | 0.40 | 0.20 |
| IPL | batter | ALL\|chase | middle\|chase | 68 | 0.69 | 0.20 |
| IPL | batter | ALL\|chase | middle\|first_innings | 55 | -0.00671 | 0.10 |
| IPL | batter | ALL\|chase | powerplay\|ALL | 34 | 0.34 | 0.10 |
| IPL | batter | ALL\|chase | powerplay\|chase | 18 | 0.74 | 0.20 |
| IPL | batter | ALL\|chase | powerplay\|first_innings | 31 | 0.49 | 0.10 |
| IPL | batter | ALL\|first_innings | death\|ALL | 66 | 0.43 | 0.10 |
| IPL | batter | ALL\|first_innings | death\|chase | 53 | -0.03 | 0.00 |
| IPL | batter | ALL\|first_innings | death\|first_innings | 59 | 0.78 | 0.40 |
| IPL | batter | ALL\|first_innings | middle\|ALL | 78 | 0.39 | 0.30 |
| IPL | batter | ALL\|first_innings | middle\|chase | 54 | 0.15 | 0.10 |
| IPL | batter | ALL\|first_innings | middle\|first_innings | 64 | 0.63 | 0.10 |
| IPL | batter | ALL\|first_innings | powerplay\|ALL | 35 | 0.52 | 0.50 |
| IPL | batter | ALL\|first_innings | powerplay\|chase | 12 | -0.44 | 0.00 |
| IPL | batter | ALL\|first_innings | powerplay\|first_innings | 36 | 0.60 | 0.60 |
| IPL | batter | death\|ALL | death\|chase | 82 | 0.89 | 0.50 |
| IPL | batter | death\|ALL | death\|first_innings | 65 | 0.68 | 0.30 |
| IPL | batter | death\|ALL | middle\|ALL | 58 | -0.15 | 0.10 |
| IPL | batter | death\|ALL | middle\|chase | 48 | 0.02 | 0.00 |
| IPL | batter | death\|ALL | middle\|first_innings | 47 | -0.17 | 0.10 |
| IPL | batter | death\|ALL | powerplay\|ALL | 18 | 0.22 | 0.10 |
| IPL | batter | death\|ALL | powerplay\|first_innings | 19 | 0.45 | 0.10 |
| IPL | batter | death\|chase | death\|first_innings | 51 | 0.26 | 0.10 |
| IPL | batter | death\|chase | middle\|ALL | 49 | -0.17 | 0.10 |
| IPL | batter | death\|chase | middle\|chase | 42 | 0.11 | 0.10 |
| IPL | batter | death\|chase | middle\|first_innings | 39 | -0.24 | 0.10 |
| IPL | batter | death\|chase | powerplay\|ALL | 13 | 0.05 | 0.00 |
| IPL | batter | death\|chase | powerplay\|first_innings | 13 | 0.34 | 0.00 |
| IPL | batter | death\|first_innings | middle\|ALL | 47 | 0.12 | 0.10 |
| IPL | batter | death\|first_innings | middle\|chase | 38 | 0.17 | 0.10 |
| IPL | batter | death\|first_innings | middle\|first_innings | 41 | 0.22 | 0.00 |
| IPL | batter | death\|first_innings | powerplay\|ALL | 13 | 0.13 | 0.10 |
| IPL | batter | death\|first_innings | powerplay\|first_innings | 15 | 0.20 | 0.10 |
| IPL | batter | middle\|ALL | middle\|chase | 67 | 0.83 | 0.40 |
| IPL | batter | middle\|ALL | middle\|first_innings | 64 | 0.73 | 0.40 |
| IPL | batter | middle\|ALL | powerplay\|ALL | 36 | -0.13 | 0.20 |
| IPL | batter | middle\|ALL | powerplay\|chase | 15 | 0.03 | 0.10 |
| IPL | batter | middle\|ALL | powerplay\|first_innings | 34 | -0.09 | 0.30 |
| IPL | batter | middle\|chase | middle\|first_innings | 45 | 0.29 | 0.20 |
| IPL | batter | middle\|chase | powerplay\|ALL | 27 | -0.06 | 0.10 |
| IPL | batter | middle\|chase | powerplay\|chase | 12 | 0.43 | 0.30 |
| IPL | batter | middle\|chase | powerplay\|first_innings | 25 | 0.18 | 0.10 |
| IPL | batter | middle\|first_innings | powerplay\|ALL | 27 | -0.24 | 0.00 |
| IPL | batter | middle\|first_innings | powerplay\|chase | 10 | -0.39 | 0.00 |
| IPL | batter | middle\|first_innings | powerplay\|first_innings | 27 | -0.12 | 0.10 |
| IPL | batter | powerplay\|ALL | powerplay\|chase | 18 | 0.57 | 0.30 |
| IPL | batter | powerplay\|ALL | powerplay\|first_innings | 31 | 0.91 | 0.90 |
| IPL | batter | powerplay\|chase | powerplay\|first_innings | 11 | 0.44 | 0.30 |
| T20I | batter | ALL\|ALL | ALL\|chase | 173 | 0.86 | 0.50 |
| T20I | batter | ALL\|ALL | ALL\|first_innings | 164 | 0.76 | 0.30 |
| T20I | batter | ALL\|ALL | death\|ALL | 150 | 0.85 | 0.60 |
| T20I | batter | ALL\|ALL | death\|chase | 125 | 0.76 | 0.60 |
| T20I | batter | ALL\|ALL | death\|first_innings | 99 | 0.66 | 0.10 |
| T20I | batter | ALL\|ALL | middle\|ALL | 173 | 0.77 | 0.20 |
| T20I | batter | ALL\|ALL | middle\|chase | 116 | 0.65 | 0.00 |
| T20I | batter | ALL\|ALL | middle\|first_innings | 112 | 0.59 | 0.10 |
| T20I | batter | ALL\|ALL | powerplay\|ALL | 57 | 0.57 | 0.30 |
| T20I | batter | ALL\|ALL | powerplay\|chase | 34 | 0.58 | 0.30 |
| T20I | batter | ALL\|ALL | powerplay\|first_innings | 41 | 0.47 | 0.20 |
| T20I | batter | ALL\|chase | ALL\|first_innings | 101 | 0.30 | 0.10 |
| T20I | batter | ALL\|chase | death\|ALL | 131 | 0.79 | 0.50 |
| T20I | batter | ALL\|chase | death\|chase | 134 | 0.87 | 0.60 |
| T20I | batter | ALL\|chase | death\|first_innings | 72 | 0.34 | 0.10 |
| T20I | batter | ALL\|chase | middle\|ALL | 128 | 0.60 | 0.00 |
| T20I | batter | ALL\|chase | middle\|chase | 120 | 0.76 | 0.20 |
| T20I | batter | ALL\|chase | middle\|first_innings | 70 | 0.24 | 0.00 |
| T20I | batter | ALL\|chase | powerplay\|ALL | 43 | 0.49 | 0.20 |
| T20I | batter | ALL\|chase | powerplay\|chase | 32 | 0.64 | 0.20 |
| T20I | batter | ALL\|chase | powerplay\|first_innings | 27 | 0.10 | 0.10 |
| T20I | batter | ALL\|first_innings | death\|ALL | 106 | 0.60 | 0.20 |
| T20I | batter | ALL\|first_innings | death\|chase | 74 | 0.10 | 0.10 |
| T20I | batter | ALL\|first_innings | death\|first_innings | 91 | 0.82 | 0.20 |
| T20I | batter | ALL\|first_innings | middle\|ALL | 134 | 0.62 | 0.10 |
| T20I | batter | ALL\|first_innings | middle\|chase | 70 | 0.36 | 0.20 |
| T20I | batter | ALL\|first_innings | middle\|first_innings | 113 | 0.74 | 0.30 |
| T20I | batter | ALL\|first_innings | powerplay\|ALL | 48 | 0.38 | 0.20 |
| T20I | batter | ALL\|first_innings | powerplay\|chase | 23 | -0.04 | 0.20 |
| T20I | batter | ALL\|first_innings | powerplay\|first_innings | 40 | 0.65 | 0.30 |
| T20I | batter | death\|ALL | death\|chase | 129 | 0.88 | 0.80 |
| T20I | batter | death\|ALL | death\|first_innings | 97 | 0.80 | 0.20 |
| T20I | batter | death\|ALL | middle\|ALL | 101 | 0.36 | 0.00 |
| T20I | batter | death\|ALL | middle\|chase | 76 | 0.37 | 0.10 |
| T20I | batter | death\|ALL | middle\|first_innings | 67 | 0.18 | 0.10 |
| T20I | batter | death\|ALL | powerplay\|ALL | 26 | -0.14 | 0.10 |
| T20I | batter | death\|ALL | powerplay\|chase | 16 | -0.43 | 0.10 |
| T20I | batter | death\|ALL | powerplay\|first_innings | 18 | 0.10 | 0.00 |
| T20I | batter | death\|chase | death\|first_innings | 61 | 0.26 | 0.10 |
| T20I | batter | death\|chase | middle\|ALL | 83 | 0.34 | 0.00 |
| T20I | batter | death\|chase | middle\|chase | 72 | 0.30 | 0.00 |
| T20I | batter | death\|chase | middle\|first_innings | 48 | 0.13 | 0.10 |
| T20I | batter | death\|chase | powerplay\|ALL | 19 | -0.22 | 0.10 |
| T20I | batter | death\|chase | powerplay\|chase | 17 | -0.14 | 0.10 |
| T20I | batter | death\|chase | powerplay\|first_innings | 12 | -0.24 | 0.00 |
| T20I | batter | death\|first_innings | middle\|ALL | 71 | 0.25 | 0.00 |
| T20I | batter | death\|first_innings | middle\|chase | 44 | 0.32 | 0.20 |
| T20I | batter | death\|first_innings | middle\|first_innings | 59 | 0.20 | 0.10 |
| T20I | batter | death\|first_innings | powerplay\|ALL | 18 | -0.03 | 0.00 |
| T20I | batter | death\|first_innings | powerplay\|chase | 8 | -0.24 | 0.00 |
| T20I | batter | death\|first_innings | powerplay\|first_innings | 16 | 0.21 | 0.10 |
| T20I | batter | middle\|ALL | middle\|chase | 107 | 0.79 | 0.40 |
| T20I | batter | middle\|ALL | middle\|first_innings | 114 | 0.79 | 0.10 |
| T20I | batter | middle\|ALL | powerplay\|ALL | 47 | 0.12 | 0.00 |
| T20I | batter | middle\|ALL | powerplay\|chase | 27 | 0.17 | 0.00 |
| T20I | batter | middle\|ALL | powerplay\|first_innings | 34 | -0.04 | 0.00 |
| T20I | batter | middle\|chase | middle\|first_innings | 53 | 0.28 | 0.00 |
| T20I | batter | middle\|chase | powerplay\|ALL | 35 | 0.10 | 0.10 |
| T20I | batter | middle\|chase | powerplay\|chase | 24 | 0.19 | 0.10 |
| T20I | batter | middle\|chase | powerplay\|first_innings | 23 | 0.24 | 0.10 |
| T20I | batter | middle\|first_innings | powerplay\|ALL | 38 | 0.02 | 0.10 |
| T20I | batter | middle\|first_innings | powerplay\|chase | 18 | -0.10 | 0.10 |
| T20I | batter | middle\|first_innings | powerplay\|first_innings | 32 | 0.19 | 0.10 |
| T20I | batter | powerplay\|ALL | powerplay\|chase | 34 | 0.86 | 0.90 |
| T20I | batter | powerplay\|ALL | powerplay\|first_innings | 44 | 0.75 | 0.40 |
| T20I | batter | powerplay\|chase | powerplay\|first_innings | 16 | -0.09 | 0.30 |
| IPL | bowler | ALL\|ALL | ALL\|chase | 68 | 0.72 | 0.60 |
| IPL | bowler | ALL\|ALL | ALL\|first_innings | 66 | 0.70 | 0.50 |
| IPL | bowler | ALL\|ALL | death\|ALL | 62 | 0.82 | 0.60 |
| IPL | bowler | ALL\|ALL | death\|chase | 54 | 0.75 | 0.50 |
| IPL | bowler | ALL\|ALL | death\|first_innings | 50 | 0.55 | 0.40 |
| IPL | bowler | ALL\|ALL | middle\|ALL | 65 | 0.80 | 0.70 |
| IPL | bowler | ALL\|ALL | middle\|chase | 59 | 0.48 | 0.60 |
| IPL | bowler | ALL\|ALL | middle\|first_innings | 51 | 0.63 | 0.60 |
| IPL | bowler | ALL\|ALL | powerplay\|ALL | 36 | 0.41 | 0.20 |
| IPL | bowler | ALL\|ALL | powerplay\|chase | 18 | 0.55 | 0.00 |
| IPL | bowler | ALL\|ALL | powerplay\|first_innings | 36 | 0.19 | 0.20 |
| IPL | bowler | ALL\|chase | ALL\|first_innings | 56 | 0.01 | 0.30 |
| IPL | bowler | ALL\|chase | death\|ALL | 63 | 0.69 | 0.50 |
| IPL | bowler | ALL\|chase | death\|chase | 55 | 0.85 | 0.50 |
| IPL | bowler | ALL\|chase | death\|first_innings | 49 | 0.12 | 0.30 |
| IPL | bowler | ALL\|chase | middle\|ALL | 57 | 0.59 | 0.50 |
| IPL | bowler | ALL\|chase | middle\|chase | 62 | 0.67 | 0.60 |
| IPL | bowler | ALL\|chase | middle\|first_innings | 40 | 0.12 | 0.40 |
| IPL | bowler | ALL\|chase | powerplay\|ALL | 35 | 0.37 | 0.40 |
| IPL | bowler | ALL\|chase | powerplay\|chase | 17 | 0.46 | 0.20 |
| IPL | bowler | ALL\|chase | powerplay\|first_innings | 33 | -0.06 | 0.30 |
| IPL | bowler | ALL\|first_innings | death\|ALL | 53 | 0.53 | 0.60 |
| IPL | bowler | ALL\|first_innings | death\|chase | 46 | 0.20 | 0.40 |
| IPL | bowler | ALL\|first_innings | death\|first_innings | 45 | 0.78 | 0.80 |
| IPL | bowler | ALL\|first_innings | middle\|ALL | 57 | 0.55 | 0.30 |
| IPL | bowler | ALL\|first_innings | middle\|chase | 50 | 0.05 | 0.20 |
| IPL | bowler | ALL\|first_innings | middle\|first_innings | 50 | 0.79 | 0.40 |
| IPL | bowler | ALL\|first_innings | powerplay\|ALL | 32 | 0.19 | 0.20 |
| IPL | bowler | ALL\|first_innings | powerplay\|chase | 13 | -0.06 | 0.00 |
| IPL | bowler | ALL\|first_innings | powerplay\|first_innings | 35 | 0.35 | 0.20 |
| IPL | bowler | death\|ALL | death\|chase | 57 | 0.87 | 0.70 |
| IPL | bowler | death\|ALL | death\|first_innings | 51 | 0.63 | 0.70 |
| IPL | bowler | death\|ALL | middle\|ALL | 49 | 0.41 | 0.40 |
| IPL | bowler | death\|ALL | middle\|chase | 52 | 0.35 | 0.40 |
| IPL | bowler | death\|ALL | middle\|first_innings | 36 | 0.40 | 0.40 |
| IPL | bowler | death\|ALL | powerplay\|ALL | 31 | 0.09 | 0.10 |
| IPL | bowler | death\|ALL | powerplay\|chase | 14 | 0.27 | 0.00 |
| IPL | bowler | death\|ALL | powerplay\|first_innings | 31 | -0.02 | 0.10 |
| IPL | bowler | death\|chase | death\|first_innings | 45 | 0.22 | 0.50 |
| IPL | bowler | death\|chase | middle\|ALL | 41 | 0.34 | 0.30 |
| IPL | bowler | death\|chase | middle\|chase | 44 | 0.31 | 0.30 |
| IPL | bowler | death\|chase | middle\|first_innings | 30 | 0.14 | 0.40 |
| IPL | bowler | death\|chase | powerplay\|ALL | 31 | 0.21 | 0.20 |
| IPL | bowler | death\|chase | powerplay\|chase | 15 | 0.59 | 0.10 |
| IPL | bowler | death\|chase | powerplay\|first_innings | 29 | -0.000493 | 0.20 |
| IPL | bowler | death\|first_innings | middle\|ALL | 38 | 0.35 | 0.20 |
| IPL | bowler | death\|first_innings | middle\|chase | 41 | 0.24 | 0.20 |
| IPL | bowler | death\|first_innings | middle\|first_innings | 30 | 0.46 | 0.30 |
| IPL | bowler | death\|first_innings | powerplay\|ALL | 26 | -0.11 | 0.20 |
| IPL | bowler | death\|first_innings | powerplay\|chase | 12 | -0.41 | 0.00 |
| IPL | bowler | death\|first_innings | powerplay\|first_innings | 26 | 0.06 | 0.20 |
| IPL | bowler | middle\|ALL | middle\|chase | 58 | 0.68 | 0.50 |
| IPL | bowler | middle\|ALL | middle\|first_innings | 51 | 0.76 | 0.60 |
| IPL | bowler | middle\|ALL | powerplay\|ALL | 27 | 0.03 | 0.10 |
| IPL | bowler | middle\|ALL | powerplay\|chase | 12 | 0.10 | 0.00 |
| IPL | bowler | middle\|ALL | powerplay\|first_innings | 29 | -0.21 | 0.10 |
| IPL | bowler | middle\|chase | middle\|first_innings | 40 | 0.09 | 0.40 |
| IPL | bowler | middle\|chase | powerplay\|ALL | 27 | 0.11 | 0.20 |
| IPL | bowler | middle\|chase | powerplay\|chase | 12 | -0.06 | 0.10 |
| IPL | bowler | middle\|chase | powerplay\|first_innings | 28 | -0.06 | 0.10 |
| IPL | bowler | middle\|first_innings | powerplay\|ALL | 22 | -0.10 | 0.10 |
| IPL | bowler | middle\|first_innings | powerplay\|chase | 8 | 0.40 | 0.00 |
| IPL | bowler | middle\|first_innings | powerplay\|first_innings | 23 | -0.23 | 0.10 |
| IPL | bowler | powerplay\|ALL | powerplay\|chase | 18 | 0.89 | 0.30 |
| IPL | bowler | powerplay\|ALL | powerplay\|first_innings | 35 | 0.75 | 0.70 |
| IPL | bowler | powerplay\|chase | powerplay\|first_innings | 14 | 0.03 | 0.20 |
| T20I | bowler | ALL\|ALL | ALL\|chase | 105 | 0.75 | 0.60 |
| T20I | bowler | ALL\|ALL | ALL\|first_innings | 102 | 0.70 | 0.50 |
| T20I | bowler | ALL\|ALL | death\|ALL | 100 | 0.76 | 0.50 |
| T20I | bowler | ALL\|ALL | death\|chase | 80 | 0.61 | 0.50 |
| T20I | bowler | ALL\|ALL | death\|first_innings | 62 | 0.57 | 0.30 |
| T20I | bowler | ALL\|ALL | middle\|ALL | 100 | 0.83 | 0.50 |
| T20I | bowler | ALL\|ALL | middle\|chase | 64 | 0.50 | 0.30 |
| T20I | bowler | ALL\|ALL | middle\|first_innings | 73 | 0.64 | 0.40 |
| T20I | bowler | ALL\|ALL | powerplay\|ALL | 56 | 0.58 | 0.20 |
| T20I | bowler | ALL\|ALL | powerplay\|chase | 19 | 0.50 | 0.10 |
| T20I | bowler | ALL\|ALL | powerplay\|first_innings | 42 | 0.46 | 0.20 |
| T20I | bowler | ALL\|chase | ALL\|first_innings | 70 | 0.04 | 0.20 |
| T20I | bowler | ALL\|chase | death\|ALL | 84 | 0.62 | 0.40 |
| T20I | bowler | ALL\|chase | death\|chase | 82 | 0.69 | 0.40 |
| T20I | bowler | ALL\|chase | death\|first_innings | 48 | 0.07 | 0.10 |
| T20I | bowler | ALL\|chase | middle\|ALL | 75 | 0.51 | 0.30 |
| T20I | bowler | ALL\|chase | middle\|chase | 69 | 0.67 | 0.60 |
| T20I | bowler | ALL\|chase | middle\|first_innings | 48 | -0.00608 | 0.20 |
| T20I | bowler | ALL\|chase | powerplay\|ALL | 45 | 0.46 | 0.00 |
| T20I | bowler | ALL\|chase | powerplay\|chase | 19 | 0.52 | 0.20 |
| T20I | bowler | ALL\|chase | powerplay\|first_innings | 28 | -0.02 | 0.00 |
| T20I | bowler | ALL\|first_innings | death\|ALL | 80 | 0.49 | 0.50 |
| T20I | bowler | ALL\|first_innings | death\|chase | 58 | 0.03 | 0.30 |
| T20I | bowler | ALL\|first_innings | death\|first_innings | 66 | 0.80 | 0.30 |
| T20I | bowler | ALL\|first_innings | middle\|ALL | 86 | 0.63 | 0.30 |
| T20I | bowler | ALL\|first_innings | middle\|chase | 45 | 0.08 | 0.10 |
| T20I | bowler | ALL\|first_innings | middle\|first_innings | 79 | 0.85 | 0.70 |
| T20I | bowler | ALL\|first_innings | powerplay\|ALL | 46 | 0.29 | 0.10 |
| T20I | bowler | ALL\|first_innings | powerplay\|chase | 12 | -0.07 | 0.20 |
| T20I | bowler | ALL\|first_innings | powerplay\|first_innings | 42 | 0.49 | 0.10 |
| T20I | bowler | death\|ALL | death\|chase | 79 | 0.83 | 0.50 |
| T20I | bowler | death\|ALL | death\|first_innings | 64 | 0.68 | 0.50 |
| T20I | bowler | death\|ALL | middle\|ALL | 65 | 0.36 | 0.30 |
| T20I | bowler | death\|ALL | middle\|chase | 46 | 0.09 | 0.10 |
| T20I | bowler | death\|ALL | middle\|first_innings | 49 | 0.36 | 0.50 |
| T20I | bowler | death\|ALL | powerplay\|ALL | 48 | 0.12 | 0.00 |
| T20I | bowler | death\|ALL | powerplay\|chase | 16 | 0.18 | 0.00 |
| T20I | bowler | death\|ALL | powerplay\|first_innings | 39 | -0.01 | 0.00 |
| T20I | bowler | death\|chase | death\|first_innings | 45 | 0.06 | 0.20 |
| T20I | bowler | death\|chase | middle\|ALL | 52 | 0.22 | 0.30 |
| T20I | bowler | death\|chase | middle\|chase | 40 | -0.08 | 0.10 |
| T20I | bowler | death\|chase | middle\|first_innings | 35 | 0.19 | 0.30 |
| T20I | bowler | death\|chase | powerplay\|ALL | 41 | 0.08 | 0.00 |
| T20I | bowler | death\|chase | powerplay\|chase | 16 | 0.15 | 0.10 |
| T20I | bowler | death\|chase | powerplay\|first_innings | 29 | -0.06 | 0.00 |
| T20I | bowler | death\|first_innings | middle\|ALL | 42 | 0.28 | 0.30 |
| T20I | bowler | death\|first_innings | middle\|chase | 26 | 0.18 | 0.10 |
| T20I | bowler | death\|first_innings | middle\|first_innings | 36 | 0.44 | 0.20 |
| T20I | bowler | death\|first_innings | powerplay\|ALL | 31 | 0.05 | 0.10 |
| T20I | bowler | death\|first_innings | powerplay\|chase | 10 | 0.02 | 0.00 |
| T20I | bowler | death\|first_innings | powerplay\|first_innings | 26 | 0.11 | 0.10 |
| T20I | bowler | middle\|ALL | middle\|chase | 63 | 0.62 | 0.30 |
| T20I | bowler | middle\|ALL | middle\|first_innings | 79 | 0.77 | 0.60 |
| T20I | bowler | middle\|ALL | powerplay\|ALL | 35 | 0.15 | 0.10 |
| T20I | bowler | middle\|ALL | powerplay\|chase | 12 | 0.21 | 0.10 |
| T20I | bowler | middle\|ALL | powerplay\|first_innings | 28 | 0.11 | 0.20 |
| T20I | bowler | middle\|chase | middle\|first_innings | 37 | -0.05 | 0.10 |
| T20I | bowler | middle\|chase | powerplay\|ALL | 22 | 0.11 | 0.10 |
| T20I | bowler | middle\|chase | powerplay\|chase | 14 | 0.31 | 0.30 |
| T20I | bowler | middle\|chase | powerplay\|first_innings | 11 | 0.10 | 0.00 |
| T20I | bowler | middle\|first_innings | powerplay\|ALL | 28 | -0.02 | 0.10 |
| T20I | bowler | middle\|first_innings | powerplay\|chase | 9 | -0.37 | 0.20 |
| T20I | bowler | middle\|first_innings | powerplay\|first_innings | 25 | 0.07 | 0.20 |
| T20I | bowler | powerplay\|ALL | powerplay\|chase | 19 | 0.87 | 0.10 |
| T20I | bowler | powerplay\|ALL | powerplay\|first_innings | 40 | 0.84 | 0.80 |


Pairs not estimable (fewer than 8 common players): 4.

## 4. Across definitions (point rankings, same cell)

| definition A | definition B | format | role | common | top-10 overlap | trivial | Spearman |
|---|---|---|---|---|---|---|---|
| any\|q0.75 | any\|q0.9 | IPL | batter | 81 | 4 | no | 0.84 |
| any\|q0.75 | chase\|q0.75 | IPL | batter | 94 | 4 | no | 0.83 |
| any\|q0.75 | chase\|q0.9 | IPL | batter | 35 | 4 | no | 0.79 |
| any\|q0.75 | any\|q0.9 | T20I | batter | 117 | 6 | no | 0.88 |
| any\|q0.75 | chase\|q0.75 | T20I | batter | 142 | 6 | no | 0.90 |
| any\|q0.75 | chase\|q0.9 | T20I | batter | 50 | 6 | no | 0.86 |
| any\|q0.75 | any\|q0.9 | IPL | bowler | 38 | 5 | no | 0.78 |
| any\|q0.75 | chase\|q0.75 | IPL | bowler | 48 | 7 | no | 0.75 |
| any\|q0.75 | chase\|q0.9 | IPL | bowler | 14 | 4 | no | 0.71 |
| any\|q0.75 | any\|q0.9 | T20I | bowler | 68 | 8 | no | 0.79 |
| any\|q0.75 | chase\|q0.75 | T20I | bowler | 85 | 6 | no | 0.75 |
| any\|q0.75 | chase\|q0.9 | T20I | bowler | 24 | 2 | no | 0.49 |


## 5. Reading
- Primary definition, non-trivial cells (4): the point Top 10 keeps on average 4.9 to 6.2 of its 10 members in a resampled Top 10; two independent resamples agree on 3.1 to 5.3 of 10. Fewer than 10 means the membership of the Top 10 depends on which matches happen to be in the sample.
- 21 of the 40 point-Top-10 slots in these cells have a Top-10 inclusion probability below 0.5.
- Phase x situation contexts by status: {'ESTIMATED': 48}. Thin contexts are reported as such, never padded.
- Because the between-player variance is not identified (investigation report), this instability should be read as a lower bound on the problem: filters change which players are compared, they do not add information about each player.
- No ranking is validated and none may be published while the gates below fail.

## 6. Unresolved issues
1. Rankings are unstable where pools are non-trivial (section 1); the ordering is not reliable enough for any selection use, and no ranking is validated.
2. Context pools use per-context working thresholds that are not validated; many contexts are thin or not estimable.
3. Between-player variance is unidentified (see the investigation report), so the shrinkage that stabilises these rankings is itself provisional.
4. Bootstrap holds baseline, thresholds and shrinkage parameters fixed, so it understates total uncertainty.
5. Date verification, strict classification and the methodology-validation gate remain failing (section 7).

## 7. Gates still failing (from `phase5_publication_gates.json`)
Publication status of any ranking today: `INTERNAL_EXPERIMENTAL_ONLY`.
| gate | passed | applicable | detail |
|---|---|---|---|
| data_weight_gate_passed | no | yes | 4 of 4 cells THRESHOLD_NOT_VALIDATED |
| methodology_validated | no | yes | methodology not validated |
| strict_classification_available | yes | no | not applicable: request uses no strict status filter |
| min_eligible_pool | yes | no | not applicable: evaluated per request with rows |
| date_verification | no | yes | 0 of 42 late T20I matches are official-verified; classes {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}; none verified against an authoritative record unless supplied |


## 8. Preservation
`{'official_data_unchanged': True, 'phase4_report_files_hashed': 56, 'phase4_report_files_changed': [], 'phase4_lock_log_sha256_before': 'cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c', 'phase4_lock_log_sha256_after': 'cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c', 'phase5_lock_log_events': 0, 'test_opened': False, 'all_preserved': True}`
