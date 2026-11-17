# Phase 5 sensitivity report

Status: EXPERIMENTAL_NOT_VALIDATED. PROVISIONAL and descriptive. Not an official ranking, no ML model, nothing here is validated. TEST outcomes: not used. Cricsheet: not used.

Reference run: definition `any|q0.75` (PROVISIONAL rule winner), shrinkage `shrink_tau4`, baseline B0, frozen working-pool ball thresholds (IPL batter 20, T20I batter 16, IPL bowler 49, T20I bowler 29; NOT validated, every cell is `THRESHOLD_NOT_VALIDATED`). Data: TRAIN + VALIDATION only. Code version `0061c9d62abd2c99`. Overlap and Spearman measure how far a choice moves the ordering. They do not say which choice is right.

## 0. Preconditions
- Phase 4 scores reproduced: max abs difference 0.00e+00 over 1345 players (reproduces = True).
- When a pool has 10 or fewer players the Top 10 is the whole pool and overlap is trivially high (`trivial` column). Pools are never padded.

## 1. Definition alternatives (all nine candidates; quantile thresholds 0.75 / 0.9 / 0.95 included)
Same frozen ball thresholds for every definition, so pool size changes with the definition because the pressure sample changes. Compared on players eligible under both.

| definition | named alt | format | role | pool ref | pool alt | common | top-10 overlap | trivial | Spearman | Kendall |
|---|---|---|---|---|---|---|---|---|---|---|
| any\|q0.75 | no | IPL | batter | 132 | 132 | 132 | 10.00 | no | 1.00 | 1.00 |
| any\|q0.9 | yes | IPL | batter | 132 | 81 | 81 | 4.00 | no | 0.84 | 0.67 |
| any\|q0.95 | no | IPL | batter | 132 | 37 | 37 | 3.00 | no | 0.67 | 0.52 |
| chase\|q0.75 | yes | IPL | batter | 132 | 94 | 94 | 4.00 | no | 0.83 | 0.66 |
| chase\|q0.9 | yes | IPL | batter | 132 | 35 | 35 | 4.00 | no | 0.79 | 0.64 |
| chase\|q0.95 | no | IPL | batter | 132 | 9 | 9 | 2.00 | no | 0.83 | 0.72 |
| inn1\|q0.75 | no | IPL | batter | 132 | 87 | 87 | 4.00 | no | 0.64 | 0.47 |
| inn1\|q0.9 | no | IPL | batter | 132 | 40 | 40 | 1.00 | no | 0.64 | 0.47 |
| inn1\|q0.95 | no | IPL | batter | 132 | 16 | 16 | 1.00 | no | 0.47 | 0.35 |
| any\|q0.75 | no | T20I | batter | 243 | 243 | 243 | 10.00 | no | 1.00 | 1.00 |
| any\|q0.9 | yes | T20I | batter | 243 | 117 | 117 | 6.00 | no | 0.88 | 0.71 |
| any\|q0.95 | no | T20I | batter | 243 | 54 | 54 | 4.00 | no | 0.80 | 0.61 |
| chase\|q0.75 | yes | T20I | batter | 243 | 144 | 142 | 6.00 | no | 0.90 | 0.74 |
| chase\|q0.9 | yes | T20I | batter | 243 | 50 | 50 | 6.00 | no | 0.86 | 0.69 |
| chase\|q0.95 | no | T20I | batter | 243 | 19 | 19 | 3.00 | no | 0.90 | 0.75 |
| inn1\|q0.75 | no | T20I | batter | 243 | 136 | 136 | 1.00 | no | 0.76 | 0.60 |
| inn1\|q0.9 | no | T20I | batter | 243 | 54 | 54 | 1.00 | no | 0.61 | 0.45 |
| inn1\|q0.95 | no | T20I | batter | 243 | 25 | 25 | 0.00 | no | 0.27 | 0.18 |
| any\|q0.75 | no | IPL | bowler | 80 | 80 | 80 | 10.00 | no | 1.00 | 1.00 |
| any\|q0.9 | yes | IPL | bowler | 80 | 38 | 38 | 5.00 | no | 0.78 | 0.60 |
| any\|q0.95 | no | IPL | bowler | 80 | 7 | 7 | 1.00 | no | 0.57 | 0.52 |
| chase\|q0.75 | yes | IPL | bowler | 80 | 48 | 48 | 7.00 | no | 0.75 | 0.56 |
| chase\|q0.9 | yes | IPL | bowler | 80 | 14 | 14 | 4.00 | no | 0.71 | 0.56 |
| chase\|q0.95 | no | IPL | bowler | 80 | 2 | 2 | 0.00 | no | n/a | n/a |
| inn1\|q0.75 | no | IPL | bowler | 80 | 47 | 47 | 5.00 | no | 0.73 | 0.55 |
| inn1\|q0.9 | no | IPL | bowler | 80 | 7 | 7 | 2.00 | no | 0.64 | 0.43 |
| inn1\|q0.95 | no | IPL | bowler | 80 | 0 | 0 | n/a | no | n/a | n/a |
| any\|q0.75 | no | T20I | bowler | 141 | 141 | 141 | 10.00 | no | 1.00 | 1.00 |
| any\|q0.9 | yes | T20I | bowler | 141 | 68 | 68 | 8.00 | no | 0.79 | 0.59 |
| any\|q0.95 | no | T20I | bowler | 141 | 20 | 20 | 5.00 | no | 0.78 | 0.63 |
| chase\|q0.75 | yes | T20I | bowler | 141 | 85 | 85 | 6.00 | no | 0.75 | 0.58 |
| chase\|q0.9 | yes | T20I | bowler | 141 | 24 | 24 | 2.00 | no | 0.49 | 0.34 |
| chase\|q0.95 | no | T20I | bowler | 141 | 6 | 6 | 0.00 | no | 0.37 | 0.33 |
| inn1\|q0.75 | no | T20I | bowler | 141 | 79 | 79 | 5.00 | no | 0.71 | 0.55 |
| inn1\|q0.9 | no | T20I | bowler | 141 | 25 | 25 | 4.00 | no | 0.70 | 0.52 |
| inn1\|q0.95 | no | T20I | bowler | 141 | 8 | 8 | 3.00 | no | 0.86 | 0.71 |


Format-combined pools (players eligible in both formats, 70:30):

| definition | role | pool ref | pool alt | common | top-10 overlap | trivial | Spearman |
|---|---|---|---|---|---|---|---|
| any\|q0.75 | batter | 48 | 48 | 48 | 10.00 | no | 1.00 |
| any\|q0.9 | batter | 48 | 13 | 13 | 3.00 | no | 0.87 |
| any\|q0.95 | batter | 48 | 2 | 2 | 0.00 | no | n/a |
| chase\|q0.75 | batter | 48 | 30 | 29 | 8.00 | no | 0.73 |
| chase\|q0.9 | batter | 48 | 5 | 5 | 2.00 | no | 0.90 |
| chase\|q0.95 | batter | 48 | 0 | 0 | n/a | no | n/a |
| inn1\|q0.75 | batter | 48 | 14 | 14 | 4.00 | no | 0.27 |
| inn1\|q0.9 | batter | 48 | 2 | 2 | 0.00 | no | n/a |
| inn1\|q0.95 | batter | 48 | 0 | 0 | n/a | no | n/a |
| any\|q0.75 | bowler | 39 | 39 | 39 | 10.00 | no | 1.00 |
| any\|q0.9 | bowler | 39 | 17 | 17 | 6.00 | no | 0.90 |
| any\|q0.95 | bowler | 39 | 2 | 2 | 0.00 | no | n/a |
| chase\|q0.75 | bowler | 39 | 25 | 25 | 5.00 | no | 0.65 |
| chase\|q0.9 | bowler | 39 | 4 | 4 | 0.00 | no | 0.40 |
| chase\|q0.95 | bowler | 39 | 0 | 0 | n/a | no | n/a |
| inn1\|q0.75 | bowler | 39 | 13 | 13 | 6.00 | no | 0.75 |
| inn1\|q0.9 | bowler | 39 | 5 | 5 | 2.00 | no | 0.90 |
| inn1\|q0.95 | bowler | 39 | 0 | 0 | n/a | no | n/a |


## 2. Eligibility ball thresholds (primary definition, candidates from each cell's TRAIN distribution and ladder)
`marginal data weight` is n_eff / (n_eff + k) of the least-qualified player in the pool. The Phase 4 gate needed 0.5 and no candidate reached it in any cell.

| format | role | threshold | source | frozen pool | pool | common | top-10 overlap | trivial | Spearman | marginal data weight |
|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | 3 | P10 | no | 239 | 132 | 7 | no | 1.00 | 0.04 |
| IPL | batter | 6 | ladder | no | 208 | 132 | 8 | no | 1.00 | 0.04 |
| IPL | batter | 8 | P25 | no | 184 | 132 | 9 | no | 1.00 | 0.04 |
| IPL | batter | 12 | ladder | no | 159 | 132 | 9 | no | 1.00 | 0.04 |
| IPL | batter | 18 | ladder | no | 138 | 132 | 10 | no | 1.00 | 0.06 |
| IPL | batter | 20 | P50 | yes | 132 | 132 | 10 | no | 1.00 | 0.06 |
| IPL | batter | 24 | ladder | no | 122 | 122 | 10 | no | 1.00 | 0.06 |
| IPL | batter | 30 | ladder | no | 116 | 116 | 10 | no | 1.00 | 0.06 |
| IPL | batter | 40 | P60 | no | 89 | 89 | 8 | no | 1.00 | 0.07 |
| IPL | batter | 45 | ladder | no | 82 | 82 | 8 | no | 1.00 | 0.09 |
| IPL | batter | 60 | ladder | no | 67 | 67 | 6 | no | 1.00 | 0.09 |
| IPL | batter | 72 | P75 | no | 54 | 54 | 5 | no | 1.00 | 0.14 |
| IPL | batter | 90 | ladder | no | 43 | 43 | 5 | no | 1.00 | 0.14 |
| IPL | batter | 120 | ladder | no | 29 | 29 | 5 | no | 1.00 | 0.19 |
| T20I | batter | 3 | P10 | no | 448 | 243 | 9 | no | 1.00 | 0.04 |
| T20I | batter | 6 | P25+ladder | no | 386 | 243 | 9 | no | 1.00 | 0.04 |
| T20I | batter | 12 | ladder | no | 291 | 243 | 10 | no | 1.00 | 0.04 |
| T20I | batter | 16 | P50 | yes | 243 | 243 | 10 | no | 1.00 | 0.04 |
| T20I | batter | 18 | ladder | no | 226 | 226 | 10 | no | 1.00 | 0.04 |
| T20I | batter | 23 | P60 | no | 183 | 183 | 9 | no | 1.00 | 0.04 |
| T20I | batter | 24 | ladder | no | 177 | 177 | 9 | no | 1.00 | 0.04 |
| T20I | batter | 30 | ladder | no | 147 | 147 | 8 | no | 1.00 | 0.06 |
| T20I | batter | 41 | P75 | no | 101 | 101 | 7 | no | 1.00 | 0.07 |
| T20I | batter | 45 | ladder | no | 95 | 95 | 7 | no | 1.00 | 0.07 |
| T20I | batter | 60 | ladder | no | 66 | 66 | 4 | no | 1.00 | 0.10 |
| T20I | batter | 90 | ladder | no | 38 | 38 | 3 | no | 1.00 | 0.15 |
| T20I | batter | 120 | ladder | no | 17 | 17 | 1 | no | 1.00 | 0.21 |
| IPL | bowler | 6 | ladder | no | 163 | 80 | 8 | no | 1.00 | 0.04 |
| IPL | bowler | 7 | P10 | no | 160 | 80 | 8 | no | 1.00 | 0.04 |
| IPL | bowler | 12 | ladder | no | 140 | 80 | 8 | no | 1.00 | 0.04 |
| IPL | bowler | 18 | P25+ladder | no | 123 | 80 | 9 | no | 1.00 | 0.04 |
| IPL | bowler | 24 | ladder | no | 106 | 80 | 10 | no | 1.00 | 0.07 |
| IPL | bowler | 36 | ladder | no | 94 | 80 | 10 | no | 1.00 | 0.09 |
| IPL | bowler | 48 | ladder | no | 81 | 80 | 10 | no | 1.00 | 0.12 |
| IPL | bowler | 49 | P50 | yes | 80 | 80 | 10 | no | 1.00 | 0.12 |
| IPL | bowler | 69 | P60 | no | 63 | 63 | 10 | no | 1.00 | 0.15 |
| IPL | bowler | 72 | ladder | no | 60 | 60 | 9 | no | 1.00 | 0.19 |
| IPL | bowler | 96 | ladder | no | 49 | 49 | 9 | no | 1.00 | 0.24 |
| IPL | bowler | 100 | P75 | no | 49 | 49 | 9 | no | 1.00 | 0.24 |
| IPL | bowler | 144 | ladder | no | 32 | 32 | 8 | no | 1.00 | 0.31 |
| T20I | bowler | 6 | P10+ladder | no | 303 | 141 | 10 | no | 1.00 | 0.04 |
| T20I | bowler | 12 | ladder | no | 253 | 141 | 10 | no | 1.00 | 0.04 |
| T20I | bowler | 13 | P25 | no | 234 | 141 | 10 | no | 1.00 | 0.04 |
| T20I | bowler | 18 | ladder | no | 195 | 141 | 10 | no | 1.00 | 0.05 |
| T20I | bowler | 24 | ladder | no | 162 | 141 | 10 | no | 1.00 | 0.06 |
| T20I | bowler | 29 | P50 | yes | 141 | 141 | 10 | no | 1.00 | 0.07 |
| T20I | bowler | 36 | ladder | no | 116 | 116 | 10 | no | 1.00 | 0.10 |
| T20I | bowler | 38 | P60 | no | 113 | 113 | 10 | no | 1.00 | 0.10 |
| T20I | bowler | 48 | ladder | no | 99 | 99 | 10 | no | 1.00 | 0.10 |
| T20I | bowler | 69 | P75 | no | 70 | 70 | 8 | no | 1.00 | 0.15 |
| T20I | bowler | 72 | ladder | no | 64 | 64 | 8 | no | 1.00 | 0.20 |
| T20I | bowler | 96 | ladder | no | 46 | 46 | 7 | no | 1.00 | 0.22 |
| T20I | bowler | 144 | ladder | no | 17 | 17 | 2 | no | 1.00 | 0.32 |


## 3. Shrinkage strength (seven configurations) crossed with the four named definitions
Two references: the primary run (`any|q0.75`, `shrink_tau4`) and the same definition under its own frozen shrinkage. k is the shrinkage strength of the configuration (larger = more shrinkage). `shrink_none` and `shrink_target0` are sensitivity-only and cannot be chosen as primary.

| definition | shrinkage | format | role | k | median data weight | pool | top-10 overlap vs same-definition frozen | trivial | Spearman |
|---|---|---|---|---|---|---|---|---|---|
| any\|q0.75 | shrink_eb | IPL | batter | 100.00 | 0.05 | 132 | 9 | no | 1.00 |
| any\|q0.75 | shrink_floor0.001 | IPL | batter | 1000.00 | 0.0057 | 132 | 3 | no | 0.17 |
| any\|q0.75 | shrink_none | IPL | batter | 0.00 | 1.00 | 132 | 4 | no | 0.97 |
| any\|q0.75 | shrink_target0 | IPL | batter | 100.00 | 0.05 | 132 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau0.5 | IPL | batter | 100.00 | 0.05 | 132 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau2 | IPL | batter | 50.00 | 0.10 | 132 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau4 | IPL | batter | 25.00 | 0.19 | 132 | 10 | no | 1.00 |
| any\|q0.9 | shrink_eb | IPL | batter | 100.00 | 0.04 | 81 | 9 | no | 0.99 |
| any\|q0.9 | shrink_floor0.001 | IPL | batter | 1000.00 | 0.00415 | 81 | 1 | no | -0.65 |
| any\|q0.9 | shrink_none | IPL | batter | 0.00 | 1.00 | 81 | 8 | no | 0.97 |
| any\|q0.9 | shrink_target0 | IPL | batter | 100.00 | 0.04 | 81 | 9 | no | 0.99 |
| any\|q0.9 | shrink_tau0.5 | IPL | batter | 100.00 | 0.04 | 81 | 9 | no | 0.99 |
| any\|q0.9 | shrink_tau2 | IPL | batter | 50.00 | 0.08 | 81 | 10 | no | 1.00 |
| any\|q0.9 | shrink_tau4 | IPL | batter | 25.00 | 0.14 | 81 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_eb | IPL | batter | 100.00 | 0.04 | 94 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_floor0.001 | IPL | batter | 1000.00 | 0.00379 | 94 | 0 | no | -0.62 |
| chase\|q0.75 | shrink_none | IPL | batter | 0.00 | 1.00 | 94 | 3 | no | 0.95 |
| chase\|q0.75 | shrink_target0 | IPL | batter | 100.00 | 0.04 | 94 | 9 | no | 0.96 |
| chase\|q0.75 | shrink_tau0.5 | IPL | batter | 100.00 | 0.04 | 94 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_tau2 | IPL | batter | 50.00 | 0.07 | 94 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_tau4 | IPL | batter | 25.00 | 0.13 | 94 | 10 | no | 1.00 |
| chase\|q0.9 | shrink_eb | IPL | batter | 100.00 | 0.03 | 35 | 7 | no | 0.91 |
| chase\|q0.9 | shrink_floor0.001 | IPL | batter | 1000.00 | 0.00349 | 35 | 0 | no | -0.87 |
| chase\|q0.9 | shrink_none | IPL | batter | 0.00 | 1.00 | 35 | 9 | no | 0.97 |
| chase\|q0.9 | shrink_target0 | IPL | batter | 100.00 | 0.03 | 35 | 9 | no | 0.99 |
| chase\|q0.9 | shrink_tau0.5 | IPL | batter | 100.00 | 0.03 | 35 | 7 | no | 0.91 |
| chase\|q0.9 | shrink_tau2 | IPL | batter | 50.00 | 0.07 | 35 | 8 | no | 0.99 |
| chase\|q0.9 | shrink_tau4 | IPL | batter | 25.00 | 0.12 | 35 | 10 | no | 1.00 |
| any\|q0.75 | shrink_eb | T20I | batter | 100.00 | 0.04 | 243 | 9 | no | 1.00 |
| any\|q0.75 | shrink_floor0.001 | T20I | batter | 1000.00 | 0.00377 | 243 | 3 | no | 0.38 |
| any\|q0.75 | shrink_none | T20I | batter | 0.00 | 1.00 | 243 | 5 | no | 0.95 |
| any\|q0.75 | shrink_target0 | T20I | batter | 100.00 | 0.04 | 243 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau0.5 | T20I | batter | 100.00 | 0.04 | 243 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau2 | T20I | batter | 50.00 | 0.07 | 243 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau4 | T20I | batter | 25.00 | 0.13 | 243 | 10 | no | 1.00 |
| any\|q0.9 | shrink_eb | T20I | batter | 100.00 | 0.03 | 117 | 9 | no | 0.99 |
| any\|q0.9 | shrink_floor0.001 | T20I | batter | 1000.00 | 0.00301 | 117 | 0 | no | -0.43 |
| any\|q0.9 | shrink_none | T20I | batter | 0.00 | 1.00 | 117 | 5 | no | 0.96 |
| any\|q0.9 | shrink_target0 | T20I | batter | 100.00 | 0.03 | 117 | 10 | no | 0.99 |
| any\|q0.9 | shrink_tau0.5 | T20I | batter | 100.00 | 0.03 | 117 | 9 | no | 0.99 |
| any\|q0.9 | shrink_tau2 | T20I | batter | 50.00 | 0.06 | 117 | 10 | no | 1.00 |
| any\|q0.9 | shrink_tau4 | T20I | batter | 25.00 | 0.11 | 117 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_eb | T20I | batter | 100.00 | 0.03 | 144 | 9 | no | 0.99 |
| chase\|q0.75 | shrink_floor0.001 | T20I | batter | 1000.00 | 0.00289 | 144 | 0 | no | -0.30 |
| chase\|q0.75 | shrink_none | T20I | batter | 0.00 | 1.00 | 144 | 4 | no | 0.96 |
| chase\|q0.75 | shrink_target0 | T20I | batter | 100.00 | 0.03 | 144 | 9 | no | 0.99 |
| chase\|q0.75 | shrink_tau0.5 | T20I | batter | 100.00 | 0.03 | 144 | 9 | no | 0.99 |
| chase\|q0.75 | shrink_tau2 | T20I | batter | 50.00 | 0.05 | 144 | 9 | no | 1.00 |
| chase\|q0.75 | shrink_tau4 | T20I | batter | 25.00 | 0.10 | 144 | 10 | no | 1.00 |
| chase\|q0.9 | shrink_eb | T20I | batter | 100.00 | 0.03 | 50 | 9 | no | 0.95 |
| chase\|q0.9 | shrink_floor0.001 | T20I | batter | 1000.00 | 0.00294 | 50 | 1 | no | -0.62 |
| chase\|q0.9 | shrink_none | T20I | batter | 0.00 | 1.00 | 50 | 8 | no | 0.95 |
| chase\|q0.9 | shrink_target0 | T20I | batter | 100.00 | 0.03 | 50 | 10 | no | 1.00 |
| chase\|q0.9 | shrink_tau0.5 | T20I | batter | 100.00 | 0.03 | 50 | 9 | no | 0.95 |
| chase\|q0.9 | shrink_tau2 | T20I | batter | 50.00 | 0.06 | 50 | 10 | no | 1.00 |
| chase\|q0.9 | shrink_tau4 | T20I | batter | 25.00 | 0.11 | 50 | 10 | no | 1.00 |
| any\|q0.75 | shrink_eb | IPL | bowler | 100.00 | 0.09 | 80 | 9 | no | 1.00 |
| any\|q0.75 | shrink_floor0.001 | IPL | bowler | 1000.00 | 0.00998 | 80 | 5 | no | 0.25 |
| any\|q0.75 | shrink_none | IPL | bowler | 0.00 | 1.00 | 80 | 9 | no | 0.98 |
| any\|q0.75 | shrink_target0 | IPL | bowler | 100.00 | 0.09 | 80 | 10 | no | 1.00 |
| any\|q0.75 | shrink_tau0.5 | IPL | bowler | 100.00 | 0.09 | 80 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau2 | IPL | bowler | 50.00 | 0.17 | 80 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau4 | IPL | bowler | 25.00 | 0.29 | 80 | 10 | no | 1.00 |
| any\|q0.9 | shrink_eb | IPL | bowler | 100.00 | 0.08 | 38 | 10 | no | 0.99 |
| any\|q0.9 | shrink_floor0.001 | IPL | bowler | 1000.00 | 0.00887 | 38 | 1 | no | -0.48 |
| any\|q0.9 | shrink_none | IPL | bowler | 0.00 | 1.00 | 38 | 8 | no | 0.98 |
| any\|q0.9 | shrink_target0 | IPL | bowler | 100.00 | 0.08 | 38 | 9 | no | 0.99 |
| any\|q0.9 | shrink_tau0.5 | IPL | bowler | 100.00 | 0.08 | 38 | 10 | no | 0.99 |
| any\|q0.9 | shrink_tau2 | IPL | bowler | 50.00 | 0.15 | 38 | 10 | no | 1.00 |
| any\|q0.9 | shrink_tau4 | IPL | bowler | 25.00 | 0.26 | 38 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_eb | IPL | bowler | 100.00 | 0.07 | 48 | 9 | no | 1.00 |
| chase\|q0.75 | shrink_floor0.001 | IPL | bowler | 1000.00 | 0.0076 | 48 | 1 | no | -0.47 |
| chase\|q0.75 | shrink_none | IPL | bowler | 0.00 | 1.00 | 48 | 9 | no | 0.99 |
| chase\|q0.75 | shrink_target0 | IPL | bowler | 100.00 | 0.07 | 48 | 10 | no | 0.98 |
| chase\|q0.75 | shrink_tau0.5 | IPL | bowler | 100.00 | 0.07 | 48 | 9 | no | 1.00 |
| chase\|q0.75 | shrink_tau2 | IPL | bowler | 50.00 | 0.13 | 48 | 9 | no | 1.00 |
| chase\|q0.75 | shrink_tau4 | IPL | bowler | 25.00 | 0.23 | 48 | 10 | no | 1.00 |
| chase\|q0.9 | shrink_eb | IPL | bowler | 100.00 | 0.07 | 14 | 10 | no | 0.90 |
| chase\|q0.9 | shrink_floor0.001 | IPL | bowler | 1000.00 | 0.00773 | 14 | 6 | no | -0.53 |
| chase\|q0.9 | shrink_none | IPL | bowler | 0.00 | 1.00 | 14 | 10 | no | 0.98 |
| chase\|q0.9 | shrink_target0 | IPL | bowler | 100.00 | 0.07 | 14 | 10 | no | 0.98 |
| chase\|q0.9 | shrink_tau0.5 | IPL | bowler | 100.00 | 0.07 | 14 | 10 | no | 0.90 |
| chase\|q0.9 | shrink_tau2 | IPL | bowler | 50.00 | 0.13 | 14 | 10 | no | 0.99 |
| chase\|q0.9 | shrink_tau4 | IPL | bowler | 25.00 | 0.24 | 14 | 10 | no | 1.00 |
| any\|q0.75 | shrink_eb | T20I | bowler | 100.00 | 0.07 | 141 | 9 | no | 1.00 |
| any\|q0.75 | shrink_floor0.001 | T20I | bowler | 1000.00 | 0.00708 | 141 | 5 | no | 0.54 |
| any\|q0.75 | shrink_none | T20I | bowler | 0.00 | 1.00 | 141 | 4 | no | 0.96 |
| any\|q0.75 | shrink_target0 | T20I | bowler | 100.00 | 0.07 | 141 | 9 | no | 0.99 |
| any\|q0.75 | shrink_tau0.5 | T20I | bowler | 100.00 | 0.07 | 141 | 9 | no | 1.00 |
| any\|q0.75 | shrink_tau2 | T20I | bowler | 50.00 | 0.12 | 141 | 10 | no | 1.00 |
| any\|q0.75 | shrink_tau4 | T20I | bowler | 25.00 | 0.22 | 141 | 10 | no | 1.00 |
| any\|q0.9 | shrink_eb | T20I | bowler | 100.00 | 0.06 | 68 | 10 | no | 0.99 |
| any\|q0.9 | shrink_floor0.001 | T20I | bowler | 1000.00 | 0.00625 | 68 | 3 | no | 0.06 |
| any\|q0.9 | shrink_none | T20I | bowler | 0.00 | 1.00 | 68 | 6 | no | 0.96 |
| any\|q0.9 | shrink_target0 | T20I | bowler | 100.00 | 0.06 | 68 | 9 | no | 0.99 |
| any\|q0.9 | shrink_tau0.5 | T20I | bowler | 100.00 | 0.06 | 68 | 10 | no | 0.99 |
| any\|q0.9 | shrink_tau2 | T20I | bowler | 50.00 | 0.11 | 68 | 10 | no | 1.00 |
| any\|q0.9 | shrink_tau4 | T20I | bowler | 25.00 | 0.20 | 68 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_eb | T20I | bowler | 100.00 | 0.05 | 85 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_floor0.001 | T20I | bowler | 1000.00 | 0.00486 | 85 | 4 | no | -0.33 |
| chase\|q0.75 | shrink_none | T20I | bowler | 0.00 | 1.00 | 85 | 7 | no | 0.97 |
| chase\|q0.75 | shrink_target0 | T20I | bowler | 100.00 | 0.05 | 85 | 9 | no | 0.98 |
| chase\|q0.75 | shrink_tau0.5 | T20I | bowler | 100.00 | 0.05 | 85 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_tau2 | T20I | bowler | 50.00 | 0.09 | 85 | 10 | no | 1.00 |
| chase\|q0.75 | shrink_tau4 | T20I | bowler | 25.00 | 0.16 | 85 | 10 | no | 1.00 |
| chase\|q0.9 | shrink_eb | T20I | bowler | 100.00 | 0.05 | 24 | 9 | no | 0.97 |
| chase\|q0.9 | shrink_floor0.001 | T20I | bowler | 1000.00 | 0.00538 | 24 | 1 | no | -0.56 |
| chase\|q0.9 | shrink_none | T20I | bowler | 0.00 | 1.00 | 24 | 9 | no | 0.96 |
| chase\|q0.9 | shrink_target0 | T20I | bowler | 100.00 | 0.05 | 24 | 10 | no | 0.99 |
| chase\|q0.9 | shrink_tau0.5 | T20I | bowler | 100.00 | 0.05 | 24 | 9 | no | 0.97 |
| chase\|q0.9 | shrink_tau2 | T20I | bowler | 50.00 | 0.10 | 24 | 10 | no | 0.99 |
| chase\|q0.9 | shrink_tau4 | T20I | bowler | 25.00 | 0.18 | 24 | 10 | no | 1.00 |


Against the primary run (all 28 combinations, single-format pools):

| definition | shrinkage | format | role | common | top-10 overlap | Spearman |
|---|---|---|---|---|---|---|
| any\|q0.75 | shrink_eb | IPL | batter | 132 | 9 | 1.00 |
| any\|q0.75 | shrink_floor0.001 | IPL | batter | 132 | 3 | 0.17 |
| any\|q0.75 | shrink_none | IPL | batter | 132 | 4 | 0.97 |
| any\|q0.75 | shrink_target0 | IPL | batter | 132 | 9 | 1.00 |
| any\|q0.75 | shrink_tau0.5 | IPL | batter | 132 | 9 | 1.00 |
| any\|q0.75 | shrink_tau2 | IPL | batter | 132 | 9 | 1.00 |
| any\|q0.75 | shrink_tau4 | IPL | batter | 132 | 10 | 1.00 |
| any\|q0.9 | shrink_eb | IPL | batter | 81 | 4 | 0.83 |
| any\|q0.9 | shrink_floor0.001 | IPL | batter | 81 | 0 | -0.57 |
| any\|q0.9 | shrink_none | IPL | batter | 81 | 4 | 0.85 |
| any\|q0.9 | shrink_target0 | IPL | batter | 81 | 4 | 0.85 |
| any\|q0.9 | shrink_tau0.5 | IPL | batter | 81 | 4 | 0.83 |
| any\|q0.9 | shrink_tau2 | IPL | batter | 81 | 4 | 0.83 |
| any\|q0.9 | shrink_tau4 | IPL | batter | 81 | 4 | 0.84 |
| chase\|q0.75 | shrink_eb | IPL | batter | 94 | 4 | 0.83 |
| chase\|q0.75 | shrink_floor0.001 | IPL | batter | 94 | 0 | -0.51 |
| chase\|q0.75 | shrink_none | IPL | batter | 94 | 2 | 0.80 |
| chase\|q0.75 | shrink_target0 | IPL | batter | 94 | 5 | 0.80 |
| chase\|q0.75 | shrink_tau0.5 | IPL | batter | 94 | 4 | 0.83 |
| chase\|q0.75 | shrink_tau2 | IPL | batter | 94 | 4 | 0.83 |
| chase\|q0.75 | shrink_tau4 | IPL | batter | 94 | 4 | 0.83 |
| chase\|q0.9 | shrink_eb | IPL | batter | 35 | 4 | 0.72 |
| chase\|q0.9 | shrink_floor0.001 | IPL | batter | 35 | 0 | -0.75 |
| chase\|q0.9 | shrink_none | IPL | batter | 35 | 4 | 0.82 |
| chase\|q0.9 | shrink_target0 | IPL | batter | 35 | 4 | 0.78 |
| chase\|q0.9 | shrink_tau0.5 | IPL | batter | 35 | 4 | 0.72 |
| chase\|q0.9 | shrink_tau2 | IPL | batter | 35 | 4 | 0.79 |
| chase\|q0.9 | shrink_tau4 | IPL | batter | 35 | 4 | 0.79 |
| any\|q0.75 | shrink_eb | T20I | batter | 243 | 9 | 1.00 |
| any\|q0.75 | shrink_floor0.001 | T20I | batter | 243 | 3 | 0.38 |
| any\|q0.75 | shrink_none | T20I | batter | 243 | 5 | 0.95 |
| any\|q0.75 | shrink_target0 | T20I | batter | 243 | 9 | 1.00 |
| any\|q0.75 | shrink_tau0.5 | T20I | batter | 243 | 9 | 1.00 |
| any\|q0.75 | shrink_tau2 | T20I | batter | 243 | 9 | 1.00 |
| any\|q0.75 | shrink_tau4 | T20I | batter | 243 | 10 | 1.00 |
| any\|q0.9 | shrink_eb | T20I | batter | 117 | 5 | 0.87 |
| any\|q0.9 | shrink_floor0.001 | T20I | batter | 117 | 0 | -0.40 |
| any\|q0.9 | shrink_none | T20I | batter | 117 | 4 | 0.85 |
| any\|q0.9 | shrink_target0 | T20I | batter | 117 | 6 | 0.89 |
| any\|q0.9 | shrink_tau0.5 | T20I | batter | 117 | 5 | 0.87 |
| any\|q0.9 | shrink_tau2 | T20I | batter | 117 | 6 | 0.87 |
| any\|q0.9 | shrink_tau4 | T20I | batter | 117 | 6 | 0.88 |
| chase\|q0.75 | shrink_eb | T20I | batter | 142 | 7 | 0.88 |
| chase\|q0.75 | shrink_floor0.001 | T20I | batter | 142 | 0 | -0.32 |
| chase\|q0.75 | shrink_none | T20I | batter | 142 | 4 | 0.85 |
| chase\|q0.75 | shrink_target0 | T20I | batter | 142 | 7 | 0.90 |
| chase\|q0.75 | shrink_tau0.5 | T20I | batter | 142 | 7 | 0.88 |
| chase\|q0.75 | shrink_tau2 | T20I | batter | 142 | 7 | 0.89 |
| chase\|q0.75 | shrink_tau4 | T20I | batter | 142 | 6 | 0.90 |
| chase\|q0.9 | shrink_eb | T20I | batter | 50 | 5 | 0.79 |
| chase\|q0.9 | shrink_floor0.001 | T20I | batter | 50 | 0 | -0.69 |
| chase\|q0.9 | shrink_none | T20I | batter | 50 | 5 | 0.86 |
| chase\|q0.9 | shrink_target0 | T20I | batter | 50 | 6 | 0.87 |
| chase\|q0.9 | shrink_tau0.5 | T20I | batter | 50 | 5 | 0.79 |
| chase\|q0.9 | shrink_tau2 | T20I | batter | 50 | 6 | 0.85 |
| chase\|q0.9 | shrink_tau4 | T20I | batter | 50 | 6 | 0.86 |
| any\|q0.75 | shrink_eb | IPL | bowler | 80 | 9 | 1.00 |
| any\|q0.75 | shrink_floor0.001 | IPL | bowler | 80 | 5 | 0.25 |
| any\|q0.75 | shrink_none | IPL | bowler | 80 | 9 | 0.98 |
| any\|q0.75 | shrink_target0 | IPL | bowler | 80 | 10 | 1.00 |
| any\|q0.75 | shrink_tau0.5 | IPL | bowler | 80 | 9 | 1.00 |
| any\|q0.75 | shrink_tau2 | IPL | bowler | 80 | 9 | 1.00 |
| any\|q0.75 | shrink_tau4 | IPL | bowler | 80 | 10 | 1.00 |
| any\|q0.9 | shrink_eb | IPL | bowler | 38 | 5 | 0.78 |
| any\|q0.9 | shrink_floor0.001 | IPL | bowler | 38 | 2 | -0.29 |
| any\|q0.9 | shrink_none | IPL | bowler | 38 | 5 | 0.79 |
| any\|q0.9 | shrink_target0 | IPL | bowler | 38 | 5 | 0.74 |
| any\|q0.9 | shrink_tau0.5 | IPL | bowler | 38 | 5 | 0.78 |
| any\|q0.9 | shrink_tau2 | IPL | bowler | 38 | 5 | 0.77 |
| any\|q0.9 | shrink_tau4 | IPL | bowler | 38 | 5 | 0.78 |
| chase\|q0.75 | shrink_eb | IPL | bowler | 48 | 6 | 0.76 |
| chase\|q0.75 | shrink_floor0.001 | IPL | bowler | 48 | 1 | -0.24 |
| chase\|q0.75 | shrink_none | IPL | bowler | 48 | 7 | 0.75 |
| chase\|q0.75 | shrink_target0 | IPL | bowler | 48 | 7 | 0.77 |
| chase\|q0.75 | shrink_tau0.5 | IPL | bowler | 48 | 6 | 0.76 |
| chase\|q0.75 | shrink_tau2 | IPL | bowler | 48 | 6 | 0.75 |
| chase\|q0.75 | shrink_tau4 | IPL | bowler | 48 | 7 | 0.75 |
| chase\|q0.9 | shrink_eb | IPL | bowler | 14 | 4 | 0.60 |
| chase\|q0.9 | shrink_floor0.001 | IPL | bowler | 14 | 2 | -0.33 |
| chase\|q0.9 | shrink_none | IPL | bowler | 14 | 4 | 0.78 |
| chase\|q0.9 | shrink_target0 | IPL | bowler | 14 | 4 | 0.78 |
| chase\|q0.9 | shrink_tau0.5 | IPL | bowler | 14 | 4 | 0.60 |
| chase\|q0.9 | shrink_tau2 | IPL | bowler | 14 | 4 | 0.67 |
| chase\|q0.9 | shrink_tau4 | IPL | bowler | 14 | 4 | 0.71 |
| any\|q0.75 | shrink_eb | T20I | bowler | 141 | 9 | 1.00 |
| any\|q0.75 | shrink_floor0.001 | T20I | bowler | 141 | 5 | 0.54 |
| any\|q0.75 | shrink_none | T20I | bowler | 141 | 4 | 0.96 |
| any\|q0.75 | shrink_target0 | T20I | bowler | 141 | 9 | 0.99 |
| any\|q0.75 | shrink_tau0.5 | T20I | bowler | 141 | 9 | 1.00 |
| any\|q0.75 | shrink_tau2 | T20I | bowler | 141 | 10 | 1.00 |
| any\|q0.75 | shrink_tau4 | T20I | bowler | 141 | 10 | 1.00 |
| any\|q0.9 | shrink_eb | T20I | bowler | 68 | 8 | 0.77 |
| any\|q0.9 | shrink_floor0.001 | T20I | bowler | 68 | 3 | -0.09 |
| any\|q0.9 | shrink_none | T20I | bowler | 68 | 4 | 0.78 |
| any\|q0.9 | shrink_target0 | T20I | bowler | 68 | 7 | 0.77 |
| any\|q0.9 | shrink_tau0.5 | T20I | bowler | 68 | 8 | 0.77 |
| any\|q0.9 | shrink_tau2 | T20I | bowler | 68 | 8 | 0.78 |
| any\|q0.9 | shrink_tau4 | T20I | bowler | 68 | 8 | 0.79 |
| chase\|q0.75 | shrink_eb | T20I | bowler | 85 | 6 | 0.75 |
| chase\|q0.75 | shrink_floor0.001 | T20I | bowler | 85 | 2 | -0.15 |
| chase\|q0.75 | shrink_none | T20I | bowler | 85 | 5 | 0.75 |
| chase\|q0.75 | shrink_target0 | T20I | bowler | 85 | 5 | 0.74 |
| chase\|q0.75 | shrink_tau0.5 | T20I | bowler | 85 | 6 | 0.75 |
| chase\|q0.75 | shrink_tau2 | T20I | bowler | 85 | 6 | 0.75 |
| chase\|q0.75 | shrink_tau4 | T20I | bowler | 85 | 6 | 0.75 |
| chase\|q0.9 | shrink_eb | T20I | bowler | 24 | 2 | 0.50 |
| chase\|q0.9 | shrink_floor0.001 | T20I | bowler | 24 | 1 | -0.30 |
| chase\|q0.9 | shrink_none | T20I | bowler | 24 | 1 | 0.53 |
| chase\|q0.9 | shrink_target0 | T20I | bowler | 24 | 2 | 0.52 |
| chase\|q0.9 | shrink_tau0.5 | T20I | bowler | 24 | 2 | 0.50 |
| chase\|q0.9 | shrink_tau2 | T20I | bowler | 24 | 2 | 0.49 |
| chase\|q0.9 | shrink_tau4 | T20I | bowler | 24 | 2 | 0.49 |


## 4. Baseline alternatives (fitted on TRAIN only; primary definition)
B0 is the frozen baseline. Alternatives use coarser first cell levels or drop the format offset. VALIDATION RMSE/MAE show fit; overlap and Spearman show ranking movement against B0.

| baseline | format | role | VAL rows | VAL RMSE | VAL MAE | pool B0 | pool variant | common | top-10 overlap | Spearman |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 | IPL | batter | 16,301 | 1.82 | 1.38 | 132 | 132 | 132 | 10 | 1.00 |
| B0 | T20I | batter | 25,439 | 1.71 | 1.27 | 243 | 243 | 243 | 10 | 1.00 |
| B0 | IPL | bowler | 16,992 | 1.79 | 1.35 | 80 | 80 | 80 | 10 | 1.00 |
| B0 | T20I | bowler | 26,384 | 1.68 | 1.24 | 141 | 141 | 141 | 10 | 1.00 |
| B_coarse_L1 | IPL | batter | 16,301 | 1.82 | 1.39 | 132 | 132 | 132 | 9 | 1.00 |
| B_coarse_L1 | T20I | batter | 25,439 | 1.71 | 1.27 | 243 | 243 | 243 | 10 | 1.00 |
| B_coarse_L1 | IPL | bowler | 16,992 | 1.80 | 1.35 | 80 | 80 | 80 | 9 | 1.00 |
| B_coarse_L1 | T20I | bowler | 26,384 | 1.68 | 1.24 | 141 | 141 | 141 | 9 | 0.99 |
| B_coarse_L2 | IPL | batter | 16,301 | 1.83 | 1.39 | 132 | 132 | 132 | 8 | 0.97 |
| B_coarse_L2 | T20I | batter | 25,439 | 1.71 | 1.28 | 243 | 243 | 243 | 10 | 0.98 |
| B_coarse_L2 | IPL | bowler | 16,992 | 1.80 | 1.35 | 80 | 80 | 80 | 8 | 0.96 |
| B_coarse_L2 | T20I | bowler | 26,384 | 1.69 | 1.25 | 141 | 141 | 141 | 7 | 0.96 |
| B_no_format_offset | IPL | batter | 16,301 | 1.82 | 1.38 | 132 | 132 | 132 | 10 | 1.00 |
| B_no_format_offset | T20I | batter | 25,439 | 1.71 | 1.27 | 243 | 243 | 243 | 10 | 1.00 |
| B_no_format_offset | IPL | bowler | 16,992 | 1.79 | 1.35 | 80 | 80 | 80 | 10 | 1.00 |
| B_no_format_offset | T20I | bowler | 26,384 | 1.68 | 1.24 | 141 | 141 | 141 | 10 | 1.00 |


## 5. Format weights (eight configurations; primary definition; same final eligibility rules)
Only players eligible in BOTH formats under the same frozen rules are combined. This axis is independent of the definition axis. The 70:30 default is PROVISIONAL.

| role | config | IPL w | T20I w | pool | top-10 overlap vs w70_30 | trivial | Spearman vs w70_30 | mean abs rank change | bootstrap expected overlap |
|---|---|---|---|---|---|---|---|---|---|
| batter | w100_0 | 1.00 | 0.00 | 48 | 9 | no | 0.95 | 3.00 | 6.28 |
| batter | w85_15 | 0.85 | 0.15 | 48 | 9 | no | 0.98 | 2.12 | 5.86 |
| batter | w80_20 | 0.80 | 0.20 | 48 | 9 | no | 0.99 | 1.38 | 5.82 |
| batter | w70_30 | 0.70 | 0.30 | 48 | 10 | no | 1.00 | 0.00 | 5.78 |
| batter | w60_40 | 0.60 | 0.40 | 48 | 8 | no | 0.99 | 1.58 | 5.71 |
| batter | w55_45 | 0.55 | 0.45 | 48 | 8 | no | 0.97 | 2.38 | 5.62 |
| batter | w50_50 | 0.50 | 0.50 | 48 | 7 | no | 0.95 | 3.21 | 5.69 |
| batter | w0_100 | 0.00 | 1.00 | 48 | 3 | no | 0.46 | 10.58 | 5.88 |
| bowler | w100_0 | 1.00 | 0.00 | 39 | 9 | no | 0.92 | 3.18 | 6.63 |
| bowler | w85_15 | 0.85 | 0.15 | 39 | 10 | no | 0.97 | 1.90 | 6.87 |
| bowler | w80_20 | 0.80 | 0.20 | 39 | 10 | no | 0.99 | 1.33 | 6.95 |
| bowler | w70_30 | 0.70 | 0.30 | 39 | 10 | no | 1.00 | 0.00 | 7.09 |
| bowler | w60_40 | 0.60 | 0.40 | 39 | 9 | no | 0.99 | 1.33 | 7.17 |
| bowler | w55_45 | 0.55 | 0.45 | 39 | 9 | no | 0.98 | 1.79 | 7.18 |
| bowler | w50_50 | 0.50 | 0.50 | 39 | 9 | no | 0.96 | 2.36 | 7.13 |
| bowler | w0_100 | 0.00 | 1.00 | 39 | 5 | no | 0.61 | 7.95 | 6.88 |


## 6. Date-restricted TEST sets (set composition only)
Sets from `phase5_test_set_manifest.json`. TEST stays closed: no outcome, score or metric of any TEST match is computed here, so this section says how much data each rule removes, not how results would change. Phase 4's aggregate TEST evaluation covered all 144 matches including the 42 late T20I matches with unverified dates and is sensitivity-only; a later evaluation is not a pristine hold-out.

Manifest status: `SET_DEFINITIONS_ONLY_NO_TEST_OUTCOMES`.

| set | rule | matches | IPL matches | T20I matches | deliveries | players |
|---|---|---|---|---|---|---|
| PRIMARY_RESTRICTED | OFFICIAL_VERIFIED, or date <= core_end and class DATE_CONSISTENT_ACROSS_SOURCES | 99 | 74 | 25 | 23,039 | 324 |
| STRICT_OFFICIAL_ONLY | match in the user-supplied official verification record with an unchanged date | 0 | 0 | 0 | 0 | 0 |
| SENSITIVITY_ALL | all TEST matches, as Phase 4 evaluated them | 144 | 74 | 70 | 33,086 | 417 |


Excluded from PRIMARY_RESTRICTED: `{'excluded_matches': 45, 'excluded_deliveries': 10047, 'players_in_excluded_matches': 207, 'players_only_in_excluded_matches': 93}`.

## 7. Reading the grids
- Definition axis: over 31 non-trivial single-format comparisons the Top-10 overlap with the primary ranges from 0 to 8 of 10 (median 4.0), Spearman from 0.27 to 0.90. The ordering depends on the pressure definition.
- Shrinkage axis: against the same definition's frozen shrinkage the Top-10 overlap ranges from 0 to 10 (median 9.0); Spearman -0.87 to 1.00.
- Baseline axis: Top-10 overlap with B0 7 to 10; Spearman 0.96 to 1.00.
- Format-weight axis: Top-10 overlap with w70_30 3 to 10; Spearman 0.46 to 0.99. Pools are small (see `pool`), so many rows are trivial or near trivial.
- None of these results selects a setting. Every setting stays PROVISIONAL.

## 8. Unresolved issues
1. No setting is validated. Definition, shrinkage, baseline, thresholds and format weights all stay PROVISIONAL.
2. Eligibility thresholds are the unvalidated TRAIN-median working pools; the marginal data weight gate (0.5) was not met by any candidate in any cell, so pool sizes here are a function of an unvalidated choice.
3. Pools are small. Several overlap figures are trivial (Top 10 equals the whole pool) and carry no information.
4. TEST sensitivity cannot be measured while TEST is closed; only set composition is reported.
5. The Phase 4 noise estimator (see the investigation report) drives the strong shrinkage; a different noise model would change the shrinkage axis and is a methodology decision for review.
6. Date verification, strict classification and the methodology-validation gate remain failing (section 9).

## 9. Gates still failing (from `phase5_publication_gates.json`)
Publication status of any ranking today: `INTERNAL_EXPERIMENTAL_ONLY`.
| gate | passed | applicable | detail |
|---|---|---|---|
| data_weight_gate_passed | no | yes | 4 of 4 cells THRESHOLD_NOT_VALIDATED |
| methodology_validated | no | yes | methodology not validated |
| strict_classification_available | yes | no | not applicable: request uses no strict status filter |
| min_eligible_pool | yes | no | not applicable: evaluated per request with rows |
| date_verification | no | yes | 0 of 42 late T20I matches are official-verified; classes {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}; none verified against an authoritative record unless supplied |


## 10. Preservation
`{'official_data_unchanged': True, 'phase4_report_files_hashed': 56, 'phase4_report_files_changed': [], 'phase4_lock_log_sha256_before': 'cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c', 'phase4_lock_log_sha256_after': 'cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c', 'phase5_lock_log_events': 0, 'test_opened': False, 'all_preserved': True}`
