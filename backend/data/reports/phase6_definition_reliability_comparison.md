# Phase 6 definition reliability comparison

Status: EXPERIMENTAL_NOT_VALIDATED. INTERNAL, `IN_SAMPLE_DIAGNOSTIC_TRAIN_VALIDATION`. TEST outcomes: not used. Cricsheet: not used. No gate, threshold or Phase 4/5 artifact was changed. Code version `0061c9d62abd2c99`, seed 20260512, 1000 match-cluster bootstrap draws. Criteria SHA-256 `72b08a76afaafb7dae259b05e843459871ba08c3a4fe246e470b1b1e242d3851` (declared before any estimator output; run-log seq 90 for this step).

**This report names no player and selects nothing.** The comparison uses only the metrics and the rule in the criteria file. The provisional definition `any|q0.75` stays provisional whatever the table says; a change needs a user decision. Nine candidates were examined side by side and no multiplicity correction was applied, so any top group is provisional.

## 1. Result
- Final status: **NO_DEFINITION_PASSES**.
- Pass list (PRE_TEST): none.
- Top group named: none.
- PRE_TEST status NO_DEFINITION_PASSES; TRAIN-only status NO_DEFINITION_PASSES; stability: TOP_SETS_EQUAL (TRAIN top group none).
- Individuals eligible under all nine definitions (PRE_TEST odd/even, at least 6 balls per half), per format and role: {'IPL|batter': 3, 'IPL|bowler': 19, 'T20I|batter': 2, 'T20I|bowler': 11}. The rule needs at least 30 in every cell to use the intersection versions of M1 and M5; otherwise it reports `COMPARISON_CONFOUNDED` and the pass list only. Confounded: True. The intersection versions (M1 int., M5 int.) pool only the cells that keep at least 10 individuals and are not interpretable when the intersection is this small; they are shown for completeness.

## 2. Rule and metrics (from the criteria file, not edited here)
- R: odd/even split-half Spearman-Brown reliability of definition d in cell c, primary stream, PRE_TEST, at least 6 pressure balls per half, at least 10 individuals; match-cluster bootstrap with 1000 draws; lo is the 2.5th percentile of the draws.
- Rule: PASS(d) iff R(d,c) is estimable in all four cells and lo(d,c) > 0 in at least three cells. TOP(d) iff PASS(d) and M1(d) >= max M1 over passing definitions minus SE1 of the best. Order inside TOP: M4 descending, then M5 descending, then id ascending. The output is a pass list and a top group, not a selection.
- Stability: if the TOP set on TRAIN only differs from the PRE_TEST TOP set the report states DEFINITION_ORDER_NOT_STABLE and names no top group.
- Confound control: M1, M2 and M5 are recomputed on the intersection of individuals eligible under all nine definitions per cell; the rule uses the intersection version when it has at least 30 individuals in every cell, otherwise COMPARISON_CONFOUNDED and only the pass list is reported.
- M1 is the Spearman-Brown corrected value of the Fisher-z pooled Pearson correlation of the four cells (weights n - 3, clip 0.99). SE1 is the SD over bootstrap draws of that pooled value. M4 uses individuals estimable for the odd/even split; the same median over all individuals with pressure balls is in the cell table. M2, M3 and M6 are descriptive and never enter the rule.

## 3. Definition summary, PRE_TEST (primary streams, four format x role cells)

| definition | cells est. | cells lo>0 | passes | M1 | SE1 | M1 int. | SE1 int. | cells int. | M4 balls | M5 | M5 int. | M2 mean | M3 mean | M6 mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| any\|q0.75 | 4 | 2 | no | 0.37 | 0.06 | 0.43 | 0.28 | 2 | 59.00 | 0.78 | 0.75 | 0.39 | 0.23 | 0.03 |
| any\|q0.9 | 4 | 2 | no | 0.35 | 0.07 | -0.07 | 0.41 | 2 | 42.00 | 0.78 | 0.72 | 0.32 | 0.25 | 0.10 |
| any\|q0.95 | 4 | 0 | no | 0.26 | 0.10 | 0.24 | 0.33 | 2 | 34.50 | 0.75 | 0.75 | 0.25 | 0.28 | 0.00381 |
| chase\|q0.75 | 4 | 2 | no | 0.37 | 0.07 | 0.66 | 0.30 | 2 | 47.00 | 0.78 | 0.76 | 0.39 | 0.28 | -0.05 |
| chase\|q0.9 | 4 | 1 | no | 0.28 | 0.11 | 0.63 | 0.26 | 2 | 31.00 | 0.76 | 0.77 | 0.23 | 0.27 | 0.13 |
| chase\|q0.95 | 4 | 0 | no | 0.35 | 0.15 | 0.32 | 0.44 | 2 | 26.00 | 0.79 | 0.80 | 0.34 | 0.36 | 0.08 |
| inn1\|q0.75 | 4 | 0 | no | 0.35 | 0.08 | 0.17 | 0.32 | 2 | 55.00 | 0.77 | 0.79 | 0.39 | 0.24 | -0.03 |
| inn1\|q0.9 | 4 | 0 | no | 0.26 | 0.12 | 0.000523 | 0.57 | 2 | 38.00 | 0.77 | 0.75 | 0.25 | 0.25 | 0.04 |
| inn1\|q0.95 | 4 | 0 | no | -0.00201 | 0.27 | 0.32 | 1.43 | 2 | 30.00 | 0.71 | 0.74 | 0.03 | 0.28 | 0.24 |


## 3b. Where the interval lower bound is above 0 (PRE_TEST, nine definitions)

| format | role | definitions with lo > 0 | definitions estimable |
|---|---|---|---|
| IPL | batter | 3 | 9 |
| IPL | bowler | 0 | 9 |
| T20I | batter | 4 | 9 |
| T20I | bowler | 0 | 9 |


## 4. Cells, PRE_TEST (odd/even Spearman-Brown R and its match-cluster bootstrap interval)

| definition | format | role | status | individuals | R (SB) | lo | hi | share draws <= 0 | M2 | M3 | M4 balls | M5 median | M5 p5 | M6 control SB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| any\|q0.75 | IPL | batter | ESTIMATED | 144 | 0.39 | 0.18 | 0.59 | 0.002 | 0.38 | 0.20 | 70.00 | 0.78 | 0.70 | -0.08 |
| any\|q0.75 | IPL | bowler | ESTIMATED | 135 | 0.41 | -0.10 | 0.49 | 0.07 | 0.46 | 0.19 | 85.00 | 0.77 | 0.68 | 0.06 |
| any\|q0.75 | T20I | batter | ESTIMATED | 247 | 0.42 | 0.18 | 0.49 | 0.00 | 0.42 | 0.28 | 48.00 | 0.80 | 0.74 | -0.11 |
| any\|q0.75 | T20I | bowler | ESTIMATED | 231 | 0.25 | -0.08 | 0.42 | 0.09 | 0.28 | 0.24 | 54.00 | 0.78 | 0.72 | 0.26 |
| any\|q0.9 | IPL | batter | ESTIMATED | 90 | 0.37 | 0.03 | 0.60 | 0.02 | 0.35 | 0.30 | 40.00 | 0.80 | 0.70 | 0.36 |
| any\|q0.9 | IPL | bowler | ESTIMATED | 90 | 0.04 | -0.42 | 0.42 | 0.40 | 0.04 | 0.16 | 52.00 | 0.72 | 0.61 | 0.05 |
| any\|q0.9 | T20I | batter | ESTIMATED | 132 | 0.51 | 0.08 | 0.59 | 0.007 | 0.55 | 0.32 | 37.00 | 0.81 | 0.74 | -0.22 |
| any\|q0.9 | T20I | bowler | ESTIMATED | 148 | 0.31 | -0.15 | 0.44 | 0.13 | 0.36 | 0.24 | 40.50 | 0.76 | 0.69 | 0.23 |
| any\|q0.95 | IPL | batter | ESTIMATED | 49 | 0.27 | -0.16 | 0.66 | 0.06 | 0.28 | 0.33 | 36.00 | 0.74 | 0.62 | -0.22 |
| any\|q0.95 | IPL | bowler | ESTIMATED | 65 | 0.03 | -0.44 | 0.41 | 0.41 | 0.04 | 0.23 | 38.00 | 0.75 | 0.63 | -0.48 |
| any\|q0.95 | T20I | batter | ESTIMATED | 68 | 0.57 | -0.00607 | 0.66 | 0.03 | 0.60 | 0.32 | 31.50 | 0.81 | 0.69 | 0.51 |
| any\|q0.95 | T20I | bowler | ESTIMATED | 80 | 0.06 | -0.35 | 0.47 | 0.35 | 0.06 | 0.23 | 32.50 | 0.73 | 0.62 | 0.21 |
| chase\|q0.75 | IPL | batter | ESTIMATED | 103 | 0.45 | 0.11 | 0.63 | 0.004 | 0.44 | 0.30 | 48.00 | 0.82 | 0.74 | -0.32 |
| chase\|q0.75 | IPL | bowler | ESTIMATED | 107 | 0.39 | -0.08 | 0.49 | 0.06 | 0.43 | 0.26 | 54.00 | 0.75 | 0.64 | 0.22 |
| chase\|q0.75 | T20I | batter | ESTIMATED | 140 | 0.41 | 0.17 | 0.56 | 0.001 | 0.45 | 0.31 | 39.00 | 0.80 | 0.72 | -0.53 |
| chase\|q0.75 | T20I | bowler | ESTIMATED | 145 | 0.23 | -0.31 | 0.43 | 0.24 | 0.25 | 0.23 | 48.00 | 0.76 | 0.68 | 0.44 |
| chase\|q0.9 | IPL | batter | ESTIMATED | 48 | 0.13 | -0.34 | 0.61 | 0.17 | 0.11 | 0.27 | 30.00 | 0.78 | 0.63 | 0.45 |
| chase\|q0.9 | IPL | bowler | ESTIMATED | 66 | -0.20 | -0.72 | 0.40 | 0.58 | -0.22 | 0.21 | 35.00 | 0.69 | 0.54 | -0.73 |
| chase\|q0.9 | T20I | batter | ESTIMATED | 52 | 0.68 | 0.05 | 0.72 | 0.02 | 0.73 | 0.35 | 32.00 | 0.83 | 0.69 | 0.33 |
| chase\|q0.9 | T20I | bowler | ESTIMATED | 86 | 0.29 | -0.38 | 0.49 | 0.20 | 0.30 | 0.23 | 28.50 | 0.75 | 0.64 | 0.47 |
| chase\|q0.95 | IPL | batter | ESTIMATED | 21 | 0.24 | -0.25 | 0.75 | 0.10 | 0.22 | 0.38 | 27.00 | 0.79 | 0.62 | n/a |
| chase\|q0.95 | IPL | bowler | ESTIMATED | 45 | 0.24 | -0.77 | 0.53 | 0.38 | 0.24 | 0.27 | 26.00 | 0.78 | 0.64 | 0.12 |
| chase\|q0.95 | T20I | batter | ESTIMATED | 25 | 0.59 | -0.36 | 0.81 | 0.11 | 0.56 | 0.44 | 29.00 | 0.81 | 0.58 | 0.02 |
| chase\|q0.95 | T20I | bowler | ESTIMATED | 44 | 0.33 | -0.63 | 0.62 | 0.31 | 0.34 | 0.36 | 24.00 | 0.78 | 0.64 | 0.09 |
| inn1\|q0.75 | IPL | batter | ESTIMATED | 96 | 0.52 | -0.03 | 0.63 | 0.03 | 0.55 | 0.30 | 56.00 | 0.79 | 0.70 | -0.13 |
| inn1\|q0.75 | IPL | bowler | ESTIMATED | 96 | 0.36 | -0.16 | 0.48 | 0.14 | 0.42 | 0.21 | 60.00 | 0.77 | 0.68 | -0.34 |
| inn1\|q0.75 | T20I | batter | ESTIMATED | 126 | 0.31 | -0.29 | 0.46 | 0.19 | 0.33 | 0.22 | 52.00 | 0.75 | 0.67 | 0.05 |
| inn1\|q0.75 | T20I | bowler | ESTIMATED | 140 | 0.24 | -0.12 | 0.45 | 0.12 | 0.27 | 0.24 | 55.00 | 0.78 | 0.70 | 0.31 |
| inn1\|q0.9 | IPL | batter | ESTIMATED | 52 | 0.07 | -0.90 | 0.55 | 0.42 | 0.06 | 0.21 | 36.00 | 0.70 | 0.54 | 0.69 |
| inn1\|q0.9 | IPL | bowler | ESTIMATED | 51 | 0.02 | -0.65 | 0.48 | 0.44 | 0.02 | 0.22 | 42.00 | 0.75 | 0.61 | -0.65 |
| inn1\|q0.9 | T20I | batter | ESTIMATED | 59 | 0.51 | -0.19 | 0.67 | 0.08 | 0.58 | 0.29 | 37.00 | 0.79 | 0.67 | -0.04 |
| inn1\|q0.9 | T20I | bowler | ESTIMATED | 77 | 0.28 | -0.23 | 0.53 | 0.15 | 0.32 | 0.29 | 38.00 | 0.78 | 0.70 | 0.15 |
| inn1\|q0.95 | IPL | batter | ESTIMATED | 22 | 0.30 | -2.37 | 0.73 | 0.46 | 0.32 | 0.36 | 29.00 | 0.74 | 0.50 | n/a |
| inn1\|q0.95 | IPL | bowler | ESTIMATED | 33 | 0.00313 | -1.86 | 0.61 | 0.46 | 0.00293 | 0.27 | 28.00 | 0.69 | 0.43 | 0.10 |
| inn1\|q0.95 | T20I | batter | ESTIMATED | 25 | 0.30 | -0.78 | 0.68 | 0.23 | 0.34 | 0.28 | 37.00 | 0.76 | 0.55 | 0.14 |
| inn1\|q0.95 | T20I | bowler | ESTIMATED | 40 | -0.50 | -1.97 | 0.47 | 0.69 | -0.56 | 0.20 | 30.00 | 0.69 | 0.54 | 0.48 |


## 5. Resampling instability (M5)
For each of the bootstrap resamples of matches the per-individual mean residual is recomputed and its Spearman correlation with the full-window ordering is taken over the individuals estimable for the split. M5 is the median over resamples; the 5th percentile shows the bad end. Values are in the cell table above and in `p6_definition_resampling`. A low M5 means a different set of matches would reorder individuals markedly.

| definition | M5 (median over cells) | M5 intersection | M4 balls |
|---|---|---|---|
| any\|q0.75 | 0.78 | 0.75 | 59.00 |
| any\|q0.9 | 0.78 | 0.72 | 42.00 |
| any\|q0.95 | 0.75 | 0.75 | 34.50 |
| chase\|q0.75 | 0.78 | 0.76 | 47.00 |
| chase\|q0.9 | 0.76 | 0.77 | 31.00 |
| chase\|q0.95 | 0.79 | 0.80 | 26.00 |
| inn1\|q0.75 | 0.77 | 0.79 | 55.00 |
| inn1\|q0.9 | 0.77 | 0.75 | 38.00 |
| inn1\|q0.95 | 0.71 | 0.74 | 30.00 |


## 6. TRAIN-only repeat (stability check)

| definition | cells est. | cells lo>0 | passes | M1 | SE1 | M1 int. | M5 |
|---|---|---|---|---|---|---|---|
| any\|q0.75 | 4 | 2 | no | 0.26 | 0.07 | 0.31 | 0.75 |
| any\|q0.9 | 4 | 1 | no | 0.34 | 0.09 | 0.20 | 0.76 |
| any\|q0.95 | 4 | 0 | no | 0.24 | 0.12 | 0.44 | 0.76 |
| chase\|q0.75 | 4 | 1 | no | 0.28 | 0.09 | 0.62 | 0.76 |
| chase\|q0.9 | 4 | 0 | no | 0.28 | 0.14 | 0.80 | 0.75 |
| chase\|q0.95 | 4 | 0 | no | 0.46 | 0.19 | 0.60 | 0.81 |
| inn1\|q0.75 | 4 | 0 | no | 0.26 | 0.10 | 0.29 | 0.77 |
| inn1\|q0.9 | 4 | 0 | no | 0.25 | 0.17 | 0.57 | 0.77 |
| inn1\|q0.95 | 4 | 0 | no | -0.23 | 0.56 | 0.65 | 0.74 |


## 7. Limits
- In-sample. Thresholds, baseline and pressure flags were fitted on TRAIN; this is a diagnostic of measurement reliability, not validation, and a definition that passes is not shown to measure pressure skill.
- The definitions differ in how many balls each individual contributes (M4). Higher reliability can come from more balls rather than a better definition; the intersection versions control for the set of individuals, not for the ball count.
- The match-cluster bootstrap interval is not centred on the point estimate (midpoint below the point estimate in 33/36 PRE_TEST cells). Counts of 'lower bound above 0' are therefore conservative or inconsistent and must be read with that in mind.
- Individuals with at least 6 balls in each half are a selected, more active subset.
- The M6 control draws, for every player-match of the pressure sample, the same number of non-pressure balls (or all of them when fewer exist). It shows reliability that ordinary balls give at a comparable sample size and is never a selection input.
- No player identity, score level, rank or Top-10 membership entered the rule; the output tables have no player column.
- Cross-checks inside the same data (TRAIN versus PRE_TEST, intersection versus all individuals) are consistency checks, not independent validation.
