# Phase 4 pressure definition comparison

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking. No final ML model.

All nine full-eligibility candidates (`{chase, inn1, any} x q in {0.75, 0.90, 0.95}`) are compared. The full table is retained. The winner is PROVISIONAL, one of nine examined, with no multiplicity correction. `chase|q0.9` was accepted only as the leading provisional candidate; its earlier selection rested on eligible population size, which is not used here.

Rule file: `config/phase4_definition_rule_v1.json` (SHA-256 `c8ae7e837f30978dd6e252007a3a42440080ccd53c6be3606745fd28f2bb497f`), fixed before any metric was computed. Data: TRAIN and VALIDATION only. TEST outcomes: not used. Bootstrap: 1000 match-cluster resamples, seed 20260512. Thresholds are TRAIN-only quantiles of the pre-delivery signal (`rrr` for chase; negative deviation from the STRICTLY PRIOR par for innings 1).

## Selection rule (as written before the run)
- Gate 1 (floor, not an objective): P >= gate1_min_players_P in each of the four cells; failing candidates are excluded and listed.
- A candidate is rankable only if R and S are estimable (>= min_players_for_RS players) in all four cells; otherwise NOT_RANKABLE.
- Sc = 0.5 * (pooled z_R + pooled z_S); z = arctanh(clipped r); pooling weights n - 3 across cells; Sc is reported on the correlation scale tanh(Sc).
- Top group: candidates within max(tie_margin, bootstrap SE of the best Sc) of the best Sc; ties inside the top group go to the lexicographically smallest definition id.
- Eligible population is never a selector or tie-breaker. D is report-only.
- Bootstrap note: Match-cluster bootstrap with TRAIN-only thresholds and the baseline held fixed (thresholds are not refitted per resample; the selection-stability share therefore understates threshold uncertainty).

## Result
Rule winner: **`any|q0.75`** (PROVISIONAL, one of 9 examined (multiplicity not corrected)). Top group (within max(0.02, bootstrap SE of best Sc) = 0.055 of the best): ['any|q0.75', 'any|q0.9', 'chase|q0.75']. Best Sc candidate: `any|q0.9`. Leading candidate `chase|q0.9` status under the rule: OK; in top group: False.
Sample-size check: across the 7 rankable candidates the Spearman correlation between Sc and total TRAIN pressure balls is 0.68. Reliability rises mechanically with the number of balls per player, so Sc is partly a sample-size effect and the rule gives weak evidence about which definition measures pressure better. Members of the top group are not distinguishable, and the winner among them is fixed by the pre-declared lexicographic tie-break, not by merit.

Definition carried into the downstream experiments: `any|q0.75` (PROVISIONAL rule winner).

## Candidate table (population is shown, never used to select)
| definition | status | Sc (corr scale) | Sc boot SE | selection share | min P | total P | TRAIN pressure balls |
|---|---|---|---|---|---|---|---|
| chase|q0.75 | OK | 0.25 | 0.06 | 0.30 | 93 | 427 | 26,535 |
| chase|q0.9 | OK | 0.17 | 0.09 | 0.05 | 41 | 189 | 10,564 |
| chase|q0.95 | NOT_RANKABLE | 0.22 | 0.16 | 0.00 | 18 | 85 | 5,275 |
| inn1|q0.75 | OK | 0.15 | 0.05 | 0.02 | 92 | 438 | 25,947 |
| inn1|q0.9 | OK | 0.10 | 0.11 | 0.05 | 49 | 215 | 10,377 |
| inn1|q0.95 | NOT_RANKABLE | -0.25 | 0.27 | 0.00 | 19 | 91 | 5,184 |
| any|q0.75 | OK | 0.24 | 0.04 | 0.33 | 123 | 666 | 52,482 |
| any|q0.9 | OK | 0.26 | 0.06 | 0.15 | 78 | 371 | 20,941 |
| any|q0.95 | OK | 0.15 | 0.09 | 0.09 | 45 | 200 | 10,459 |

Selection share: share of match-bootstrap resamples in which the candidate has the highest Sc among Gate-1-passing rankable candidates. A low share means it is not distinguishable from the others.

## Cell-level metrics (format x role)
| definition | format | role | P (>=18 balls TRAIN) | R split-half (SB) | n R | S TRAIN->VAL | n S | SNR | D (VAL) | D lo | D hi | D expected direction | expected top-10 overlap | pool | par unavailable share (inn1 TRAIN) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| chase|q0.75 | IPL | batter | 94 | 0.34 | 109 | 0.37 | 44 | -0.74 | -0.02 | -0.09 | 0.04 | yes | 4.75 | 114 | n/a |
| chase|q0.75 | T20I | batter | 126 | 0.43 | 146 | 0.28 | 53 | -0.75 | 0.04 | -0.03 | 0.10 | no | 4.26 | 177 | n/a |
| chase|q0.75 | IPL | bowler | 93 | 0.11 | 95 | 0.05 | 58 | -0.68 | -0.02 | -0.09 | 0.04 | no | 5.66 | 106 | n/a |
| chase|q0.75 | T20I | bowler | 114 | 0.08 | 119 | 0.29 | 59 | -0.75 | 0.03 | -0.03 | 0.10 | yes | 5.15 | 154 | n/a |
| chase|q0.9 | IPL | batter | 41 | 0.000548 | 58 | 0.44 | 15 | -0.67 | -0.09 | -0.21 | 0.01 | yes | 5.25 | 57 | n/a |
| chase|q0.9 | T20I | batter | 46 | 0.33 | 59 | 0.44 | 18 | -0.65 | 0.0069 | -0.09 | 0.09 | no | 5.80 | 65 | n/a |
| chase|q0.9 | IPL | bowler | 48 | 0.15 | 60 | -0.01 | 32 | -0.58 | -0.09 | -0.21 | 0.00976 | no | 5.11 | 63 | n/a |
| chase|q0.9 | T20I | bowler | 54 | 0.19 | 75 | 0.03 | 25 | -0.62 | 0.00843 | -0.09 | 0.09 | yes | 4.46 | 79 | n/a |
| chase|q0.95 | IPL | batter | 18 | 0.55 | 28 | 0.28 | 7 | -0.68 | -0.01 | -0.16 | 0.12 | yes | 6.05 | 27 | n/a |
| chase|q0.95 | T20I | batter | 20 | 0.54 | 30 | 0.05 | 7 | -0.60 | -0.06 | -0.17 | 0.05 | yes | 5.59 | 30 | n/a |
| chase|q0.95 | IPL | bowler | 25 | -0.00672 | 37 | 0.16 | 19 | -0.60 | -0.00958 | -0.15 | 0.12 | no | 5.73 | 33 | n/a |
| chase|q0.95 | T20I | bowler | 22 | 0.10 | 36 | 0.14 | 10 | -0.66 | -0.06 | -0.17 | 0.04 | no | 5.16 | 36 | n/a |
| inn1|q0.75 | IPL | batter | 92 | 0.48 | 99 | 0.31 | 51 | -0.74 | -0.11 | -0.17 | -0.05 | yes | 5.13 | 106 | 0.14 |
| inn1|q0.75 | T20I | batter | 120 | 0.08 | 119 | 0.04 | 56 | -0.61 | -0.12 | -0.17 | -0.08 | yes | 4.75 | 179 | 0.12 |
| inn1|q0.75 | IPL | bowler | 99 | 0.13 | 97 | 0.00671 | 52 | -0.68 | -0.11 | -0.17 | -0.05 | no | 5.30 | 111 | 0.14 |
| inn1|q0.75 | T20I | bowler | 127 | -0.03 | 123 | 0.22 | 63 | -0.67 | -0.12 | -0.16 | -0.08 | no | 5.08 | 170 | 0.12 |
| inn1|q0.9 | IPL | batter | 49 | 0.13 | 51 | -0.04 | 21 | -0.76 | -0.10 | -0.19 | -0.00165 | yes | 4.73 | 62 | 0.14 |
| inn1|q0.9 | T20I | batter | 54 | 0.04 | 51 | 0.22 | 20 | -0.59 | -0.13 | -0.19 | -0.07 | yes | 5.17 | 85 | 0.12 |
| inn1|q0.9 | IPL | bowler | 54 | 0.10 | 57 | 0.01 | 25 | -0.46 | -0.10 | -0.19 | 0.00274 | no | 4.94 | 67 | 0.14 |
| inn1|q0.9 | T20I | bowler | 58 | 0.31 | 67 | 0.03 | 35 | -0.55 | -0.13 | -0.18 | -0.07 | no | 5.38 | 84 | 0.12 |
| inn1|q0.95 | IPL | batter | 19 | -0.34 | 21 | -0.74 | 6 | -0.77 | -0.09 | -0.24 | 0.14 | yes | 5.35 | 28 | 0.14 |
| inn1|q0.95 | T20I | batter | 24 | 0.32 | 23 | -0.22 | 8 | -0.43 | -0.14 | -0.22 | -0.07 | yes | 5.84 | 42 | 0.12 |
| inn1|q0.95 | IPL | bowler | 20 | 0.15 | 31 | 0.40 | 6 | -0.40 | -0.08 | -0.24 | 0.16 | no | 4.30 | 37 | 0.14 |
| inn1|q0.95 | T20I | bowler | 28 | -0.85 | 31 | -0.18 | 17 | -0.42 | -0.14 | -0.22 | -0.07 | no | 5.48 | 46 | 0.12 |
| any|q0.75 | IPL | batter | 133 | 0.53 | 158 | 0.32 | 79 | -0.72 | -0.07 | -0.11 | -0.03 | yes | 5.11 | 149 | 0.14 |
| any|q0.75 | T20I | batter | 211 | 0.31 | 241 | 0.34 | 106 | -0.65 | -0.06 | -0.09 | -0.02 | yes | 4.72 | 291 | 0.12 |
| any|q0.75 | IPL | bowler | 123 | 0.10 | 126 | 0.14 | 74 | -0.74 | -0.06 | -0.11 | -0.02 | no | 5.83 | 136 | 0.14 |
| any|q0.75 | T20I | bowler | 199 | -0.03 | 207 | 0.18 | 101 | -0.71 | -0.05 | -0.09 | -0.02 | no | 5.36 | 253 | 0.12 |
| any|q0.9 | IPL | batter | 78 | 0.34 | 97 | 0.64 | 38 | -0.65 | -0.10 | -0.17 | -0.02 | yes | 5.44 | 101 | 0.14 |
| any|q0.9 | T20I | batter | 103 | 0.44 | 130 | 0.14 | 50 | -0.60 | -0.07 | -0.12 | -0.02 | yes | 5.30 | 144 | 0.12 |
| any|q0.9 | IPL | bowler | 78 | 0.21 | 88 | -0.08 | 51 | -0.41 | -0.09 | -0.16 | -0.02 | no | 4.93 | 90 | 0.14 |
| any|q0.9 | T20I | bowler | 112 | 0.40 | 135 | -0.02 | 62 | -0.55 | -0.07 | -0.12 | -0.02 | no | 5.05 | 149 | 0.12 |
| any|q0.95 | IPL | batter | 46 | 0.30 | 56 | 0.36 | 17 | -0.75 | -0.05 | -0.15 | 0.07 | yes | 5.72 | 60 | 0.14 |
| any|q0.95 | T20I | batter | 55 | 0.51 | 69 | 0.02 | 24 | -0.48 | -0.11 | -0.17 | -0.05 | yes | 5.16 | 82 | 0.12 |
| any|q0.95 | IPL | bowler | 45 | -0.02 | 61 | 0.02 | 31 | -0.64 | -0.04 | -0.15 | 0.08 | no | 4.67 | 60 | 0.14 |
| any|q0.95 | T20I | bowler | 54 | -0.10 | 72 | 0.17 | 33 | -0.63 | -0.11 | -0.17 | -0.05 | no | 5.11 | 80 | 0.12 |


## Pressure samples and performance relative to baseline
| definition | format | role | balls TRAIN | matches TRAIN | players TRAIN | balls VAL | matches VAL | mean residual diff (pressure - other), VAL | lo | hi | secondary stream | secondary diff | lo | hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| chase|q0.75 | IPL | batter | 5,942 | 134 | 210 | 1,855 | 35 | -0.04 | -0.17 | 0.08 | dismissal | 0.02 | 0.00738 | 0.03 |
| chase|q0.75 | T20I | batter | 6,992 | 158 | 347 | 2,749 | 59 | 0.06 | -0.05 | 0.17 | dismissal | 0.03 | 0.02 | 0.04 |
| chase|q0.75 | IPL | bowler | 6,281 | 135 | 135 | 1,943 | 35 | -0.04 | -0.16 | 0.07 | wkt | 0.02 | 0.00964 | 0.03 |
| chase|q0.75 | T20I | bowler | 7,320 | 159 | 220 | 2,882 | 59 | 0.06 | -0.05 | 0.16 | wkt | 0.02 | 0.01 | 0.03 |
| chase|q0.9 | IPL | batter | 2,349 | 115 | 158 | 758 | 31 | -0.17 | -0.39 | 0.02 | dismissal | 0.03 | 0.00733 | 0.05 |
| chase|q0.9 | T20I | batter | 2,781 | 134 | 253 | 1,210 | 53 | 0.01 | -0.15 | 0.16 | dismissal | 0.02 | 0.00376 | 0.04 |
| chase|q0.9 | IPL | bowler | 2,512 | 115 | 105 | 796 | 31 | -0.16 | -0.37 | 0.02 | wkt | 0.03 | 0.00941 | 0.05 |
| chase|q0.9 | T20I | bowler | 2,922 | 134 | 165 | 1,283 | 53 | 0.01 | -0.14 | 0.15 | wkt | 0.02 | 0.00154 | 0.04 |
| chase|q0.95 | IPL | batter | 1,177 | 103 | 127 | 428 | 31 | -0.03 | -0.29 | 0.21 | dismissal | 0.03 | 0.00473 | 0.05 |
| chase|q0.95 | T20I | batter | 1,379 | 117 | 195 | 593 | 47 | -0.10 | -0.29 | 0.08 | dismissal | 0.04 | 0.00796 | 0.07 |
| chase|q0.95 | IPL | bowler | 1,257 | 103 | 91 | 450 | 31 | -0.02 | -0.27 | 0.22 | wkt | 0.03 | 0.00481 | 0.05 |
| chase|q0.95 | T20I | bowler | 1,462 | 117 | 126 | 631 | 48 | -0.10 | -0.29 | 0.06 | wkt | 0.03 | 0.00457 | 0.07 |
| inn1|q0.75 | IPL | batter | 5,676 | 123 | 188 | 1,756 | 35 | -0.21 | -0.31 | -0.10 | dismissal | -0.00153 | -0.01 | 0.0088 |
| inn1|q0.75 | T20I | batter | 7,064 | 141 | 317 | 3,917 | 71 | -0.21 | -0.28 | -0.14 | dismissal | 0.00763 | -2.18e-06 | 0.02 |
| inn1|q0.75 | IPL | bowler | 5,905 | 123 | 137 | 1,810 | 35 | -0.19 | -0.30 | -0.09 | wkt | -0.000505 | -0.00981 | 0.00963 |
| inn1|q0.75 | T20I | bowler | 7,302 | 141 | 240 | 4,040 | 71 | -0.20 | -0.27 | -0.13 | wkt | 0.0091 | 0.00158 | 0.02 |
| inn1|q0.9 | IPL | batter | 2,271 | 60 | 141 | 716 | 21 | -0.18 | -0.35 | -0.00303 | dismissal | -0.00181 | -0.01 | 0.01 |
| inn1|q0.9 | T20I | batter | 2,821 | 84 | 193 | 1,708 | 43 | -0.22 | -0.32 | -0.13 | dismissal | 0.00163 | -0.00985 | 0.01 |
| inn1|q0.9 | IPL | bowler | 2,363 | 60 | 104 | 739 | 21 | -0.17 | -0.34 | 0.00485 | wkt | -0.0013 | -0.01 | 0.01 |
| inn1|q0.9 | T20I | bowler | 2,922 | 85 | 173 | 1,760 | 44 | -0.21 | -0.31 | -0.12 | wkt | 0.0035 | -0.00777 | 0.02 |
| inn1|q0.95 | IPL | batter | 1,140 | 39 | 102 | 355 | 15 | -0.16 | -0.44 | 0.26 | dismissal | -0.00149 | -0.03 | 0.03 |
| inn1|q0.95 | T20I | batter | 1,400 | 55 | 130 | 876 | 31 | -0.24 | -0.38 | -0.11 | dismissal | 0.02 | -0.00113 | 0.04 |
| inn1|q0.95 | IPL | bowler | 1,182 | 39 | 77 | 366 | 15 | -0.14 | -0.43 | 0.28 | wkt | -0.000519 | -0.03 | 0.03 |
| inn1|q0.95 | T20I | bowler | 1,462 | 55 | 120 | 906 | 31 | -0.24 | -0.37 | -0.11 | wkt | 0.02 | -0.000244 | 0.03 |
| any|q0.75 | IPL | batter | 11,618 | 197 | 244 | 3,611 | 63 | -0.12 | -0.20 | -0.05 | dismissal | 0.0087 | 0.000816 | 0.02 |
| any|q0.75 | T20I | batter | 14,056 | 237 | 439 | 6,666 | 103 | -0.09 | -0.15 | -0.03 | dismissal | 0.02 | 0.00902 | 0.02 |
| any|q0.75 | IPL | bowler | 12,186 | 198 | 163 | 3,753 | 63 | -0.11 | -0.19 | -0.04 | wkt | 0.00969 | 0.00213 | 0.02 |
| any|q0.75 | T20I | bowler | 14,622 | 238 | 296 | 6,922 | 103 | -0.09 | -0.15 | -0.03 | wkt | 0.02 | 0.00977 | 0.02 |
| any|q0.9 | IPL | batter | 4,620 | 159 | 199 | 1,474 | 50 | -0.17 | -0.30 | -0.04 | dismissal | 0.01 | 0.000912 | 0.03 |
| any|q0.9 | T20I | batter | 5,602 | 193 | 321 | 2,918 | 89 | -0.12 | -0.21 | -0.04 | dismissal | 0.00953 | 0.00048 | 0.02 |
| any|q0.9 | IPL | bowler | 4,875 | 159 | 134 | 1,535 | 50 | -0.16 | -0.29 | -0.04 | wkt | 0.01 | 0.00197 | 0.03 |
| any|q0.9 | T20I | bowler | 5,844 | 194 | 245 | 3,043 | 90 | -0.12 | -0.20 | -0.04 | wkt | 0.00953 | 0.000217 | 0.02 |
| any|q0.95 | IPL | batter | 2,317 | 135 | 161 | 783 | 45 | -0.08 | -0.28 | 0.13 | dismissal | 0.01 | -0.00368 | 0.03 |
| any|q0.95 | T20I | batter | 2,779 | 167 | 250 | 1,469 | 77 | -0.18 | -0.30 | -0.08 | dismissal | 0.02 | 0.00919 | 0.04 |
| any|q0.95 | IPL | bowler | 2,439 | 135 | 111 | 816 | 45 | -0.07 | -0.26 | 0.14 | wkt | 0.01 | -0.00338 | 0.03 |
| any|q0.95 | T20I | bowler | 2,924 | 167 | 189 | 1,537 | 77 | -0.18 | -0.29 | -0.08 | wkt | 0.02 | 0.00825 | 0.04 |


## Reading the table
- D is report-only. |D| grows with the quantile by construction, so D is compared only within the same quantile. Expected sign: batter residual below baseline and bowler residual (runs conceded) above baseline under pressure.
- R and S measure whether the sample separates players; population does not.
- Format differences: compare the IPL and T20I rows of the same definition and role.
- Threshold sensitivity: the three quantiles of each context are adjacent rows in the candidate table.

## Limitations
- Bowler pressure uses the same pre-delivery state signals as batters; the bowler-specific signal B of the design notes is not implemented, so bowler definitions are not bowler-specific.
- Thresholds are fixed at their TRAIN values in the bootstrap (not refitted per resample).
- Many cells have few players; R and S with fewer than 15 players make a candidate NOT_RANKABLE rather than being guessed.
- Phase 3 population-based selection is context only and is not used.
