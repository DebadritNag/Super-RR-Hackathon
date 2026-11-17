# Pressure feature distribution report (Phase 3 Stage 3, EXPLORATORY)

Status `EXPLORATORY_NOT_VALIDATED`, official_ranking `False`, not_for_publication `True`. Generated from `exp_pre_delivery_state` (200,999 rows).

## 1. Status: what is exploratory and what is validated

- **Validated numbers in this report: none.** Every figure is an exploratory proxy calculation
  from the official DuckDB through the pre-delivery state table (`pre_delivery_state_v1`).
- Pressure is a state-based proxy (score, wickets, balls, par). It is not a validated measure of
  difficulty. No pressure category, cutoff or score is chosen here, and no player is ranked.
- Quantile thresholds are `FULL_SAMPLE` (computed over every regulation delivery in the data
  window). Par and expected-remaining-runs values are leave-one-match-out (LOMO). Both are
  descriptive and must not be used for predictive claims. A strictly-prior innings-1 par variant is
  reported separately (section 9).
- The quantile grid is a search grid, not a selection. Each candidate below is evaluated for the
  population it would select; the choice is left for the Stage 5 experiment and for approval.
- Innings 3 and 4 (six matches), OTHER_T20 matches, DLS-unreliable rows, chases whose target rests
  on an unverified innings 1 and rows with `Req <= 0` are outside every population shown.
- Official records were not changed. Cricsheet is not used.

## 2. Populations (actual DuckDB figures)

| population | rows | matches | innings |
|---|---|---|---|
| all state rows | 200,999 | 867 | 1,724 |
| regulation in-scope (innings 1/2, IPL/T20I) | 193,988 | 837 | 1,652 |
| base population (no DLS-excluded rows) | 190,584 | 812 | 1,602 |
| innings-1 primary population | 100,425 | 812 | 812 |
| chase primary population | 89,589 | 784 | 784 |

| comp | context | rows | matches | innings |
|---|---|---|---|---|
| IPL | chase | 41,275 | 355 | 355 |
| T20I | chase | 48,314 | 429 | 429 |
| IPL | inn1 | 45,312 | 364 | 364 |
| T20I | inn1 | 55,113 | 448 | 448 |

Rows with a wicket-flag disagreement in the state (`state_wicket_flag_disagreement`) inside the base population: 652. They keep the primary `is_wicket` count; the alternative count is a sensitivity.

Exclusions from the primary populations (rows):

| reason | rows |
|---|---|
| innings 3/4 (restricted, RULE_INNINGS_3_4) | 38 |
| OTHER_T20 (format out of scope) | 6,985 |
| DLS-excluded primary rows (regulation in-scope) | 3,404 |
| chase rows with target_basis_unverified (in base) | 570 |
| chase rows with Req <= 0 (in base) | 0 |
| chase rows with RRR NULL (in base) | 0 |

Distinct matches and innings by season (union of the two primary populations):

| comp | season | rows | innings | matches |
|---|---|---|---|---|
| IPL | 2022 | 17,687 | 146 | 74 |
| IPL | 2023 | 17,769 | 146 | 74 |
| IPL | 2024 | 17,001 | 141 | 71 |
| IPL | 2025 | 16,992 | 143 | 73 |
| IPL | 2026 | 17,138 | 143 | 72 |
| T20I | 2022 | 23,895 | 199 | 101 |
| T20I | 2023 | 14,532 | 123 | 64 |
| T20I | 2024 | 23,837 | 202 | 103 |
| T20I | 2025 | 26,384 | 226 | 115 |
| T20I | 2026 | 14,779 | 127 | 65 |

## 3. Wickets-remaining bins and par/expectation tables

Deterministic global partition (min_cell_innings = 30). Rule: merge the bin with the smallest m with the adjacent bin giving the larger combined m, ties toward Wrem 1. FULL_SAMPLE, descriptive.

| bin (Wrem) | m (min distinct innings over the 12 cells) |
|---|---|
| 10-8 | 54 |
| 7-1 | 64 |

| step | deficient bin | m | merged into | combined m |
|---|---|---|---|---|
| 1 | [1] | 0 | [2, 1] | 0 |
| 2 | [2, 1] | 0 | [3, 2, 1] | 0 |
| 3 | [3, 2, 1] | 0 | [4, 3, 2, 1] | 0 |
| 4 | [4, 3, 2, 1] | 0 | [5, 4, 3, 2, 1] | 3 |
| 5 | [10] | 2 | [10, 9] | 17 |
| 6 | [5, 4, 3, 2, 1] | 3 | [6, 5, 4, 3, 2, 1] | 17 |
| 7 | [6, 5, 4, 3, 2, 1] | 17 | [7, 6, 5, 4, 3, 2, 1] | 64 |
| 8 | [10, 9] | 17 | [10, 9, 8] | 54 |

`wickets_bins_failed`: False. The low-wicket singleton bins are empty in the powerplay cells (no innings reaches Wrem 1-4 in the powerplay), so the minimum over cells forces a coarse two-bin partition. This is reported, not tuned.

Source innings for par (complete 120-ball innings 1): IPL 358, T20I 435 (total 793).

`exp_cell_level_used` over all state rows (LOMO, chain E0 -> E1 -> E2 -> NONE; NONE covers OTHER_T20, innings 3/4 and rows with no balls remaining):

| level | rows |
|---|---|
| E0_BINNED | 192,669 |
| NONE | 7,011 |
| E1_BREM_BIN | 1,319 |

`shrinkage_floor_hit` at E0 rows: 10,093; E1 parents with the tau2 floor binding: 2 of 40.

Innings-1 rows without a strictly-prior par (`par_unavailable_prior`): 7,692 (reported, never filled).

## 4. Required run rate (chase) distributions

Chase population only: innings 2, valid target, `Req > 0`, not DLS-excluded. RRR is shown uncapped; the capped variant uses the observed p99 and is always shown beside it.

| context / signal | n | mean | p5 | p25 | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| chase / IPL / rrr | 41,275 | 11.76 | 4.87 | 8.15 | 10.09 | 12.22 | 15.94 | 21.19 | 50.40 | 468.00 |
| chase / T20I / rrr | 48,314 | 11.11 | 3.86 | 7.35 | 9.31 | 11.75 | 15.75 | 20.57 | 48.00 | 810.00 |
| chase / IPL / rrr / phase=powerplay | 13,280 | 9.47 | 6.16 | 8.18 | 9.54 | 10.81 | 11.86 | 12.70 | 14.20 | 15.81 |
| chase / IPL / rrr / phase=middle | 19,431 | 10.18 | 5.12 | 8.14 | 10.11 | 12.08 | 14.21 | 15.67 | 19.28 | 29.03 |
| chase / IPL / rrr / phase=death | 8,564 | 18.88 | 3.00 | 8.00 | 13.30 | 20.40 | 33.32 | 49.50 | 130.11 | 468.00 |
| chase / T20I / rrr / phase=powerplay | 16,093 | 8.75 | 5.32 | 7.45 | 8.72 | 10.06 | 11.36 | 12.22 | 14.04 | 18.14 |
| chase / T20I / rrr / phase=middle | 23,072 | 9.59 | 3.50 | 7.22 | 9.45 | 11.74 | 14.14 | 15.88 | 20.46 | 32.13 |
| chase / T20I / rrr / phase=death | 9,149 | 19.10 | 2.36 | 7.66 | 13.15 | 20.18 | 33.60 | 50.24 | 138.00 | 810.00 |

| comp | p99 cap | uncapped mean | capped mean | uncapped p90 | capped p90 | rows above cap | rows Brem<6 | p90 RRR (Brem>=6) |
|---|---|---|---|---|---|---|---|---|
| IPL | 50.40 | 11.76 | 11.22 | 15.94 | 15.94 | 412 | 852 | 15.27 |
| T20I | 48.00 | 11.11 | 10.52 | 15.75 | 15.75 | 474 | 870 | 15.12 |
| pooled | 49.50 | 11.41 | 10.85 | 15.82 | 15.82 | 890 | 1,722 | 15.20 |

RRR histogram (chase, both formats):

| RRR from | to | rows | share |
|---|---|---|---|
| 0 | 4 | 3,934 | 0.04 |
| 4 | 6 | 5,999 | 0.07 |
| 6 | 8 | 15,367 | 0.17 |
| 8 | 10 | 22,847 | 0.26 |
| 10 | 12 | 18,764 | 0.21 |
| 12 | 15 | 12,048 | 0.13 |
| 15 | 20 | 5,660 | 0.06 |
| 20 | 30 | 2,764 | 0.03 |
| 30 | 60 | 1,526 | 0.02 |
| 60 | inf | 680 | 0.00759 |

## 5. Balls remaining, wickets remaining and innings phase

| context / signal | n | mean | p5 | p25 | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| chase / IPL / legal_balls_remaining | 41,275 | 63.71 | 10.00 | 36.00 | 64.00 | 93.00 | 109.00 | 115.00 | 119.00 | 120.00 |
| chase / IPL / wickets_remaining | 41,275 | 7.41 | 3.00 | 6.00 | 8.00 | 9.00 | 10.00 | 10.00 | 10.00 | 10.00 |
| chase / T20I / legal_balls_remaining | 48,314 | 65.14 | 11.00 | 38.00 | 66.00 | 94.00 | 110.00 | 115.00 | 119.00 | 120.00 |
| chase / T20I / wickets_remaining | 48,314 | 7.18 | 2.00 | 6.00 | 8.00 | 9.00 | 10.00 | 10.00 | 10.00 | 10.00 |
| inn1 / IPL / legal_balls_remaining | 45,312 | 60.54 | 7.00 | 30.00 | 60.00 | 91.00 | 109.00 | 115.00 | 119.00 | 120.00 |
| inn1 / IPL / wickets_remaining | 45,312 | 7.50 | 4.00 | 6.00 | 8.00 | 9.00 | 10.00 | 10.00 | 10.00 | 10.00 |
| inn1 / T20I / legal_balls_remaining | 55,113 | 60.88 | 7.00 | 31.00 | 61.00 | 91.00 | 109.00 | 115.00 | 119.00 | 120.00 |
| inn1 / T20I / wickets_remaining | 55,113 | 7.22 | 3.00 | 6.00 | 8.00 | 9.00 | 10.00 | 10.00 | 10.00 | 10.00 |

| context | comp | phase | rows | innings | mean Wrem | mean Brem |
|---|---|---|---|---|---|---|
| chase | IPL | death | 8,564 | 332 | 4.87 | 17.23 |
| chase | IPL | middle | 19,431 | 354 | 7.29 | 57.64 |
| chase | IPL | powerplay | 13,280 | 355 | 9.22 | 102.56 |
| chase | T20I | death | 9,149 | 376 | 4.33 | 17.52 |
| chase | T20I | middle | 23,072 | 427 | 6.93 | 57.94 |
| chase | T20I | powerplay | 16,093 | 429 | 9.16 | 102.53 |
| inn1 | IPL | death | 11,357 | 361 | 5.36 | 15.56 |
| inn1 | IPL | middle | 20,311 | 363 | 7.48 | 57.44 |
| inn1 | IPL | powerplay | 13,644 | 364 | 9.33 | 102.60 |
| inn1 | T20I | death | 13,640 | 435 | 4.88 | 15.64 |
| inn1 | T20I | middle | 24,703 | 446 | 7.15 | 57.54 |
| inn1 | T20I | powerplay | 16,770 | 448 | 9.21 | 102.59 |

Wickets remaining histogram (rows, primary populations):

| Wrem | chase rows | innings-1 rows |
|---|---|---|
| 1 | 1,471 | 948 |
| 2 | 2,439 | 1,789 |
| 3 | 3,340 | 2,712 |
| 4 | 4,696 | 5,326 |
| 5 | 7,088 | 9,618 |
| 6 | 9,729 | 12,471 |
| 7 | 13,000 | 14,616 |
| 8 | 14,800 | 16,569 |
| 9 | 16,068 | 17,727 |
| 10 | 16,958 | 18,649 |

Runs required versus balls remaining (chase, every third over-bin):

| comp | Brem from | Brem to | rows | Req p25 | Req p50 | Req p75 | RRR p50 | RRR p90 |
|---|---|---|---|---|---|---|---|---|
| IPL | 1 | 6 | 1,095 | 9.00 | 19.00 | 34.00 | 33.00 | 114.00 |
| IPL | 19 | 24 | 1,965 | 28.00 | 43.00 | 59.00 | 12.00 | 21.65 |
| IPL | 37 | 42 | 2,141 | 53.00 | 70.00 | 88.00 | 10.65 | 15.73 |
| IPL | 55 | 60 | 2,156 | 79.00 | 97.00 | 115.00 | 10.15 | 13.85 |
| IPL | 73 | 78 | 2,180 | 101.00 | 122.00 | 143.00 | 9.71 | 12.72 |
| IPL | 91 | 96 | 2,214 | 126.25 | 149.00 | 170.00 | 9.61 | 12.00 |
| IPL | 109 | 114 | 2,233 | 153.00 | 177.00 | 199.00 | 9.52 | 11.73 |
| T20I | 1 | 6 | 1,102 | 9.00 | 19.00 | 35.00 | 31.75 | 123.90 |
| T20I | 19 | 24 | 2,159 | 26.00 | 42.00 | 60.00 | 11.75 | 22.12 |
| T20I | 37 | 42 | 2,484 | 47.00 | 67.00 | 88.00 | 10.24 | 15.95 |
| T20I | 55 | 60 | 2,575 | 70.00 | 92.00 | 113.00 | 9.56 | 13.68 |
| T20I | 73 | 78 | 2,651 | 91.00 | 113.00 | 136.00 | 8.96 | 12.41 |
| T20I | 91 | 96 | 2,671 | 115.00 | 137.00 | 160.00 | 8.78 | 11.55 |
| T20I | 109 | 114 | 2,708 | 140.00 | 162.00 | 184.00 | 8.73 | 11.21 |

Cell sizes behind the relative view (distinct innings per comp x phase x wickets bin):

| ctx | comp | phase | wbin | rows | innings | matches |
|---|---|---|---|---|---|---|
| chase | IPL | death | 10-8 | 775 | 66 | 66 |
| chase | IPL | death | 7-1 | 7,789 | 306 | 306 |
| chase | IPL | middle | 10-8 | 9,664 | 270 | 270 |
| chase | IPL | middle | 7-1 | 9,767 | 270 | 270 |
| chase | IPL | powerplay | 10-8 | 12,331 | 355 | 355 |
| chase | IPL | powerplay | 7-1 | 949 | 76 | 76 |
| chase | T20I | death | 10-8 | 672 | 54 | 54 |
| chase | T20I | death | 7-1 | 8,477 | 350 | 350 |
| chase | T20I | middle | 10-8 | 9,449 | 307 | 307 |
| chase | T20I | middle | 7-1 | 13,623 | 350 | 350 |
| chase | T20I | powerplay | 10-8 | 14,935 | 429 | 429 |
| chase | T20I | powerplay | 7-1 | 1,158 | 116 | 116 |
| inn1 | IPL | death | 10-8 | 1,271 | 72 | 72 |
| inn1 | IPL | death | 7-1 | 10,086 | 346 | 346 |
| inn1 | IPL | middle | 10-8 | 10,976 | 297 | 297 |
| inn1 | IPL | middle | 7-1 | 9,335 | 288 | 288 |
| inn1 | IPL | powerplay | 10-8 | 12,990 | 364 | 364 |
| inn1 | IPL | powerplay | 7-1 | 654 | 64 | 64 |
| inn1 | T20I | death | 10-8 | 896 | 57 | 57 |
| inn1 | T20I | death | 7-1 | 12,744 | 426 | 426 |
| inn1 | T20I | middle | 10-8 | 11,040 | 342 | 342 |
| inn1 | T20I | middle | 7-1 | 13,663 | 381 | 381 |
| inn1 | T20I | powerplay | 10-8 | 15,772 | 448 | 448 |
| inn1 | T20I | powerplay | 7-1 | 998 | 98 | 98 |

## 6. Score relative to target or par

Chase: `req_to_exp = Req / exp_remaining` (innings-1 LOMO expectation at the same balls bin and wickets bin; near 1 means a balanced chase), `gap = RRR - CRR`, `projected_surplus`. Innings 1: `par_deviation` (LOMO), `projected_total_gap`. Signals prefixed `neg_` carry the sign used for pressure (higher = more pressure).

| context / signal | n | mean | p5 | p25 | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| chase / IPL / req_to_exp | 41,275 | 1.04 | 0.42 | 0.79 | 0.99 | 1.21 | 1.49 | 1.75 | 2.79 | 7.75 |
| chase / IPL / gap | 41,275 | 2.98 | -6.23 | -1.31 | 1.51 | 4.70 | 8.57 | 12.80 | 42.38 | 460.64 |
| chase / IPL / projected_surplus | 41,275 | -13.76 | -103.00 | -38.80 | -13.00 | 11.00 | 40.00 | 65.94 | 146.90 | 887.00 |
| chase / IPL / runs_required | 41,275 | 105.80 | 18.00 | 61.00 | 104.00 | 148.00 | 182.00 | 200.00 | 230.00 | 288.00 |
| chase / IPL / neg_resource_ratio | 41,275 | -0.44 | -0.95 | -0.68 | -0.41 | -0.18 | -0.06 | -0.03 | -0.00667 | -0.000833 |
| chase / T20I / req_to_exp | 48,314 | 1.07 | 0.36 | 0.77 | 1.00 | 1.26 | 1.59 | 1.87 | 3.24 | 12.78 |
| chase / T20I / gap | 48,314 | 3.18 | -6.57 | -1.20 | 1.83 | 5.00 | 8.94 | 13.31 | 40.96 | 801.78 |
| chase / T20I / projected_surplus | 48,314 | -15.68 | -104.00 | -44.00 | -15.98 | 10.46 | 43.29 | 70.00 | 151.00 | 1029.00 |
| chase / T20I / runs_required | 48,314 | 100.94 | 17.00 | 59.00 | 100.00 | 140.00 | 171.00 | 189.00 | 226.00 | 305.00 |
| chase / T20I / neg_resource_ratio | 48,314 | -0.44 | -0.95 | -0.69 | -0.41 | -0.17 | -0.06 | -0.03 | -0.00583 | -0.000833 |
| inn1 / IPL / neg_par_dev | 45,312 | -0.39 | -36.82 | -10.65 | 0.52 | 11.02 | 24.10 | 33.13 | 48.42 | 85.61 |
| inn1 / IPL / neg_proj_gap | 45,312 | -4.25 | -44.21 | -16.65 | -3.80 | 8.42 | 25.80 | 35.00 | 48.85 | 84.15 |
| inn1 / IPL / neg_resource_ratio | 45,312 | -0.42 | -0.95 | -0.68 | -0.38 | -0.15 | -0.05 | -0.02 | -0.005 | -0.000833 |
| inn1 / T20I / neg_par_dev | 55,113 | -0.70 | -37.93 | -9.12 | 0.47 | 10.21 | 23.03 | 31.08 | 46.10 | 78.91 |
| inn1 / T20I / neg_proj_gap | 55,113 | -4.16 | -43.99 | -14.73 | -3.21 | 8.39 | 24.13 | 31.70 | 44.10 | 73.48 |
| inn1 / T20I / neg_resource_ratio | 55,113 | -0.42 | -0.95 | -0.66 | -0.37 | -0.14 | -0.05 | -0.02 | -0.00417 | -0.000833 |

Zero or boundary inflation (share of rows at the signal minimum; config threshold 0.05):

| context / signal | share at min | min | above threshold |
|---|---|---|---|
| chase / IPL / rrr | 4.85e-05 | 0.10 | no |
| chase / IPL / runs_required | 0.00211 | 1.00 | no |
| chase / IPL / gap | 2.44e-05 | -44.72 | no |
| chase / IPL / req_to_exp | 2.42e-05 | 0.00942 | no |
| chase / IPL / neg_resource_ratio | 0.00899 | -1.00 | no |
| chase / IPL / projected_surplus | 2.44e-05 | -287.00 | no |
| chase / T20I / rrr | 2.07e-05 | 0.07 | no |
| chase / T20I / runs_required | 0.00224 | 1.00 | no |
| chase / T20I / gap | 2.09e-05 | -51.88 | no |
| chase / T20I / req_to_exp | 4.14e-05 | 0.00745 | no |
| chase / T20I / neg_resource_ratio | 0.00938 | -1.00 | no |
| chase / T20I / projected_surplus | 2.09e-05 | -305.00 | no |
| inn1 / IPL / neg_par_dev | 2.21e-05 | -102.92 | no |
| inn1 / IPL / neg_proj_gap | 2.21e-05 | -111.34 | no |
| inn1 / IPL / neg_resource_ratio | 0.00867 | -1.00 | no |
| inn1 / IPL / par_deviation_lomo | 2.21e-05 | -85.61 | no |
| inn1 / T20I / neg_par_dev | 1.81e-05 | -133.57 | no |
| inn1 / T20I / neg_proj_gap | 1.81e-05 | -142.14 | no |
| inn1 / T20I / neg_resource_ratio | 0.00885 | -1.00 | no |
| inn1 / T20I / par_deviation_lomo | 1.81e-05 | -78.91 | no |

## 7. Candidate thresholds from the observed distributions

Family (a) absolute thresholds at the quantile grid. Quantiles are per competition type within the context (chase or innings 1). This is the search grid, not a selection.

| ctx | comp | signal | q=0.5 | q=0.6 | q=0.75 | q=0.8 | q=0.85 | q=0.9 | q=0.95 |
|---|---|---|---|---|---|---|---|---|---|
| chase | IPL | gap | 1.51 | 2.62 | 4.70 | 5.64 | 6.86 | 8.57 | 12.80 |
| chase | IPL | neg_resource_ratio | -0.41 | -0.31 | -0.18 | -0.14 | -0.10 | -0.06 | -0.03 |
| chase | IPL | req_to_exp | 0.99 | 1.07 | 1.21 | 1.28 | 1.36 | 1.49 | 1.75 |
| chase | IPL | rrr | 10.09 | 10.80 | 12.22 | 12.99 | 14.08 | 15.94 | 21.19 |
| chase | IPL | runs_required | 104.00 | 120.00 | 148.00 | 158.00 | 169.00 | 182.00 | 200.00 |
| chase | T20I | gap | 1.83 | 2.95 | 5.00 | 5.90 | 7.14 | 8.94 | 13.31 |
| chase | T20I | neg_resource_ratio | -0.41 | -0.31 | -0.17 | -0.14 | -0.10 | -0.06 | -0.03 |
| chase | T20I | req_to_exp | 1.00 | 1.09 | 1.26 | 1.34 | 1.44 | 1.59 | 1.87 |
| chase | T20I | rrr | 9.31 | 10.15 | 11.75 | 12.61 | 13.76 | 15.75 | 20.57 |
| chase | T20I | runs_required | 100.00 | 115.00 | 140.00 | 149.00 | 160.00 | 171.00 | 189.00 |
| inn1 | IPL | neg_par_dev | 0.52 | 3.69 | 11.02 | 14.28 | 18.34 | 24.10 | 33.13 |
| inn1 | IPL | neg_proj_gap | -3.80 | -0.03 | 8.42 | 13.33 | 18.85 | 25.80 | 35.00 |
| inn1 | IPL | neg_resource_ratio | -0.38 | -0.28 | -0.15 | -0.12 | -0.08 | -0.05 | -0.02 |
| inn1 | T20I | neg_par_dev | 0.47 | 3.48 | 10.21 | 13.63 | 17.65 | 23.03 | 31.08 |
| inn1 | T20I | neg_proj_gap | -3.21 | 0.00 | 8.39 | 13.16 | 18.41 | 24.13 | 31.70 |
| inn1 | T20I | neg_resource_ratio | -0.37 | -0.27 | -0.14 | -0.11 | -0.07 | -0.05 | -0.02 |

Family (c) data-derived breaks (knee of the cumulative curve; reproducible only when the quantile positions agree within 0.05):

| ctx | signal | IPL knee value | IPL q-position | T20I knee value | T20I q-position | IPL zero-inflated | T20I zero-inflated | reproduced IPL/T20I | reproduced LOMO/prior | usable |
|---|---|---|---|---|---|---|---|---|---|---|
| chase | rrr | 27.22 | 0.97 | 30.40 | 0.98 | no | no | yes | n/a | yes |
| chase | runs_required | 181.00 | 0.89 | 175.00 | 0.91 | no | no | yes | n/a | yes |
| chase | gap | 19.93 | 0.97 | 24.78 | 0.98 | no | no | yes | n/a | yes |
| chase | req_to_exp | 1.71 | 0.94 | 1.89 | 0.95 | no | no | yes | n/a | yes |
| chase | neg_resource_ratio | -0.42 | 0.48 | -0.42 | 0.48 | no | no | yes | n/a | yes |
| chase | bowl_signal_B | 73.00 | 0.96 | 84.86 | 0.96 | no | no | yes | n/a | yes |
| inn1 | neg_par_dev | -26.83 | 0.09 | -31.79 | 0.07 | no | no | yes | yes | yes |
| inn1 | neg_proj_gap | -34.55 | 0.09 | -34.89 | 0.08 | no | no | yes | n/a | yes |
| inn1 | neg_resource_ratio | -0.33 | 0.55 | -0.34 | 0.53 | no | no | yes | n/a | yes |
| inn1 | bowl_signal_B | 26.83 | 0.91 | 31.79 | 0.93 | no | no | yes | n/a | yes |

## 8. Effect of each candidate on the eligible player population

384 candidate definitions were examined (family a: 280, family b: 84, family c reproducible breaks: 20). Columns: threshold, pressure rows (batter: balls faced; bowler: deliveries including wides and no-balls), distinct matches, distinct innings, Kish effective size over innings, players with at least floor 2 and with floor 2 plus 3 matches. Floors come from the Phase 2.5 ladders (batter balls 30/60, bowler legal balls 24/48, matches 3/5), not invented. They are provisional reference points until Stage 5 recalculates pressure-specific thresholds. The full table (floor 1, 5 matches, per-player n_eff) is in `pressure_distribution_report.json`.

### 8.chase.batter.family-a

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gap | abs | 0.50 | 1.51 | 19,578 | 340 | 340 | 223.40 | 91 | 91 | 1.83 | 23,003 | 412 | 412 | 265.40 | 128 | 128 |
| gap | abs | 0.60 | 2.62 | 15,637 | 332 | 332 | 193.80 | 87 | 86 | 2.95 | 18,376 | 397 | 397 | 232.70 | 101 | 101 |
| gap | abs | 0.75 | 4.70 | 9,725 | 313 | 313 | 146.90 | 57 | 57 | 5.00 | 11,492 | 364 | 364 | 182.00 | 42 | 41 |
| gap | abs | 0.80 | 5.64 | 7,755 | 298 | 298 | 134.30 | 38 | 38 | 5.90 | 9,181 | 346 | 346 | 164.20 | 30 | 29 |
| gap | abs | 0.85 | 6.86 | 5,809 | 274 | 274 | 121.10 | 17 | 17 | 7.14 | 6,864 | 302 | 302 | 143.90 | 17 | 16 |
| gap | abs | 0.90 | 8.57 | 3,856 | 220 | 220 | 109.70 | 10 | 10 | 8.94 | 4,553 | 244 | 244 | 122.10 | 7 | 7 |
| gap | abs | 0.95 | 12.80 | 1,915 | 154 | 154 | 95.20 | 2 | 2 | 13.31 | 2,273 | 189 | 189 | 96.50 | 0 | 0 |
| neg_resource_ratio | abs | 0.50 | -0.41 | 19,675 | 349 | 349 | 328.00 | 93 | 93 | -0.41 | 23,300 | 422 | 422 | 386.40 | 117 | 116 |
| neg_resource_ratio | abs | 0.60 | -0.31 | 15,758 | 344 | 344 | 318.50 | 74 | 74 | -0.31 | 18,605 | 412 | 412 | 369.70 | 97 | 97 |
| neg_resource_ratio | abs | 0.75 | -0.18 | 9,759 | 337 | 337 | 291.70 | 50 | 50 | -0.17 | 11,550 | 384 | 384 | 333.90 | 46 | 46 |
| neg_resource_ratio | abs | 0.80 | -0.14 | 7,814 | 327 | 327 | 274.90 | 36 | 36 | -0.14 | 9,257 | 369 | 369 | 315.30 | 24 | 24 |
| neg_resource_ratio | abs | 0.85 | -0.10 | 5,965 | 309 | 309 | 256.00 | 24 | 24 | -0.10 | 6,899 | 350 | 350 | 290.40 | 13 | 13 |
| neg_resource_ratio | abs | 0.90 | -0.06 | 3,912 | 284 | 284 | 224.30 | 12 | 12 | -0.06 | 4,725 | 327 | 327 | 262.00 | 6 | 6 |
| neg_resource_ratio | abs | 0.95 | -0.03 | 2,024 | 237 | 237 | 187.00 | 2 | 2 | -0.03 | 2,328 | 278 | 278 | 209.90 | 0 | 0 |
| req_to_exp | abs | 0.50 | 0.99 | 19,728 | 259 | 259 | 202.10 | 100 | 100 | 1.00 | 23,204 | 306 | 306 | 239.20 | 131 | 130 |
| req_to_exp | abs | 0.60 | 1.07 | 15,740 | 235 | 235 | 170.90 | 91 | 91 | 1.09 | 18,543 | 272 | 272 | 204.20 | 97 | 96 |
| req_to_exp | abs | 0.75 | 1.21 | 9,799 | 196 | 196 | 123.30 | 58 | 56 | 1.26 | 11,572 | 224 | 224 | 147.90 | 50 | 48 |
| req_to_exp | abs | 0.80 | 1.28 | 7,841 | 185 | 185 | 107.20 | 45 | 44 | 1.34 | 9,254 | 220 | 220 | 131.90 | 39 | 37 |
| req_to_exp | abs | 0.85 | 1.36 | 5,850 | 169 | 169 | 88.60 | 30 | 29 | 1.44 | 6,931 | 205 | 205 | 111.40 | 20 | 19 |
| req_to_exp | abs | 0.90 | 1.49 | 3,892 | 146 | 146 | 70.60 | 14 | 13 | 1.59 | 4,606 | 186 | 186 | 90.70 | 10 | 9 |
| req_to_exp | abs | 0.95 | 1.75 | 1,931 | 121 | 121 | 54.40 | 0 | 0 | 1.87 | 2,291 | 147 | 147 | 66.40 | 0 | 0 |
| rrr | abs | 0.50 | 10.09 | 19,680 | 260 | 260 | 201.10 | 100 | 100 | 9.31 | 23,163 | 306 | 306 | 240.60 | 129 | 128 |
| rrr | abs | 0.60 | 10.80 | 15,746 | 239 | 239 | 175.60 | 90 | 90 | 10.15 | 18,541 | 282 | 282 | 212.60 | 98 | 97 |
| rrr | abs | 0.75 | 12.22 | 9,771 | 206 | 206 | 137.90 | 51 | 50 | 11.75 | 11,560 | 255 | 255 | 168.70 | 47 | 45 |
| rrr | abs | 0.80 | 12.98 | 7,802 | 194 | 194 | 127.20 | 42 | 42 | 12.61 | 9,235 | 237 | 237 | 154.90 | 34 | 32 |
| rrr | abs | 0.85 | 14.08 | 5,833 | 183 | 183 | 117.60 | 29 | 29 | 13.76 | 6,904 | 227 | 227 | 143.80 | 17 | 16 |
| rrr | abs | 0.90 | 15.94 | 3,884 | 175 | 175 | 112.60 | 10 | 10 | 15.75 | 4,592 | 215 | 215 | 128.60 | 7 | 7 |
| rrr | abs | 0.95 | 21.19 | 1,937 | 155 | 155 | 100.30 | 2 | 2 | 20.57 | 2,295 | 190 | 190 | 107.20 | 0 | 0 |
| runs_required | abs | 0.50 | 104.00 | 20,077 | 350 | 350 | 310.50 | 90 | 90 | 100.00 | 23,372 | 420 | 420 | 356.40 | 120 | 120 |
| runs_required | abs | 0.60 | 120.00 | 16,119 | 344 | 344 | 295.30 | 76 | 76 | 115.00 | 18,884 | 409 | 409 | 329.60 | 104 | 104 |
| runs_required | abs | 0.75 | 148.00 | 9,947 | 314 | 314 | 242.20 | 50 | 50 | 140.00 | 11,757 | 354 | 354 | 259.80 | 63 | 63 |
| runs_required | abs | 0.80 | 158.00 | 7,992 | 288 | 288 | 215.70 | 47 | 47 | 149.00 | 9,304 | 318 | 318 | 225.50 | 49 | 49 |
| runs_required | abs | 0.85 | 169.00 | 5,971 | 248 | 248 | 182.70 | 35 | 35 | 160.00 | 6,973 | 273 | 273 | 184.90 | 38 | 38 |
| runs_required | abs | 0.90 | 182.00 | 4,027 | 197 | 197 | 140.10 | 22 | 22 | 171.00 | 4,804 | 225 | 225 | 140.70 | 23 | 23 |
| runs_required | abs | 0.95 | 200.00 | 2,068 | 139 | 139 | 90.10 | 9 | 9 | 189.00 | 2,426 | 132 | 132 | 81.30 | 5 | 5 |
| s_bat | rel | 0.50 | 0.50 | 19,711 | 268 | 268 | 207.20 | 102 | 102 | 0.50 | 23,213 | 324 | 324 | 247.00 | 120 | 119 |
| s_bat | rel | 0.60 | 0.60 | 15,802 | 251 | 251 | 176.40 | 88 | 88 | 0.60 | 18,576 | 300 | 300 | 210.30 | 94 | 93 |
| s_bat | rel | 0.75 | 0.75 | 9,877 | 213 | 213 | 124.00 | 56 | 56 | 0.75 | 11,640 | 250 | 250 | 151.60 | 57 | 56 |
| s_bat | rel | 0.80 | 0.80 | 7,888 | 195 | 195 | 105.80 | 44 | 42 | 0.80 | 9,304 | 238 | 238 | 129.30 | 36 | 36 |
| s_bat | rel | 0.85 | 0.85 | 5,948 | 178 | 178 | 87.20 | 32 | 31 | 0.85 | 7,004 | 217 | 217 | 104.10 | 25 | 24 |
| s_bat | rel | 0.90 | 0.90 | 3,980 | 161 | 161 | 63.70 | 13 | 12 | 0.90 | 4,681 | 186 | 186 | 79.50 | 12 | 12 |
| s_bat | rel | 0.95 | 0.95 | 2,013 | 128 | 128 | 38.10 | 2 | 2 | 0.95 | 2,374 | 143 | 143 | 47.80 | 1 | 1 |

### 8.chase.batter.family-b

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| neg_resource_ratio AND death | abs | 0.50 | -0.405 AND death | 8,058 | 332 | 332 | 301.10 | 41 | 41 | -0.4067 AND death | 8,694 | 376 | 376 | 332.20 | 19 | 19 |
| neg_resource_ratio AND death | abs | 0.60 | -0.3092 AND death | 8,058 | 332 | 332 | 301.10 | 41 | 41 | -0.31 AND death | 8,694 | 376 | 376 | 332.20 | 19 | 19 |
| neg_resource_ratio AND death | abs | 0.75 | -0.1767 AND death | 7,765 | 329 | 329 | 294.00 | 40 | 40 | -0.175 AND death | 8,458 | 370 | 370 | 325.70 | 18 | 18 |
| neg_resource_ratio AND death | abs | 0.80 | -0.1375 AND death | 6,883 | 320 | 320 | 278.00 | 33 | 33 | -0.135 AND death | 7,704 | 359 | 359 | 310.10 | 13 | 13 |
| neg_resource_ratio AND death | abs | 0.85 | -0.1 AND death | 5,675 | 304 | 304 | 256.50 | 23 | 23 | -0.09579 AND death | 6,211 | 340 | 340 | 288.60 | 12 | 12 |
| neg_resource_ratio AND death | abs | 0.90 | -0.06333 AND death | 3,825 | 279 | 279 | 223.50 | 12 | 12 | -0.06 AND death | 4,512 | 317 | 317 | 258.00 | 6 | 6 |
| neg_resource_ratio AND death | abs | 0.95 | -0.03 AND death | 2,008 | 235 | 235 | 186.30 | 2 | 2 | -0.02667 AND death | 2,306 | 277 | 277 | 209.60 | 0 | 0 |
| req_to_exp AND wrem | abs | 0.50 | 0.9925 AND 8.0 | 14,158 | 229 | 229 | 178.90 | 75 | 74 | 1.005 AND 8.0 | 17,305 | 283 | 283 | 223.10 | 91 | 89 |
| req_to_exp AND wrem | abs | 0.60 | 1.074 AND 7.0 | 10,381 | 208 | 208 | 154.50 | 54 | 53 | 1.09 AND 7.0 | 13,064 | 255 | 255 | 193.90 | 61 | 59 |
| req_to_exp AND wrem | abs | 0.75 | 1.208 AND 6.0 | 6,006 | 179 | 179 | 117.50 | 29 | 29 | 1.259 AND 6.0 | 7,871 | 213 | 213 | 147.60 | 26 | 26 |
| req_to_exp AND wrem | abs | 0.80 | 1.276 AND 6.0 | 5,240 | 175 | 175 | 107.90 | 26 | 26 | 1.341 AND 5.0 | 5,462 | 206 | 206 | 136.50 | 12 | 12 |
| req_to_exp AND wrem | abs | 0.85 | 1.365 AND 5.0 | 3,426 | 153 | 153 | 87.50 | 10 | 10 | 1.436 AND 5.0 | 4,544 | 194 | 194 | 123.20 | 8 | 8 |
| req_to_exp AND wrem | abs | 0.90 | 1.49 AND 4.0 | 1,920 | 126 | 126 | 74.10 | 2 | 2 | 1.586 AND 4.0 | 2,767 | 173 | 173 | 98.70 | 4 | 4 |
| req_to_exp AND wrem | abs | 0.95 | 1.754 AND 3.0 | 963 | 93 | 93 | 53.30 | 0 | 0 | 1.874 AND 2.0 | 956 | 104 | 104 | 61.50 | 0 | 0 |
| rrr AND brem | abs | 0.50 | 10.09 AND 64.0 | 11,433 | 245 | 245 | 206.00 | 58 | 58 | 9.309 AND 66.0 | 13,875 | 292 | 292 | 246.80 | 70 | 69 |
| rrr AND brem | abs | 0.60 | 10.8 AND 53.0 | 8,646 | 225 | 225 | 190.10 | 46 | 46 | 10.15 AND 55.0 | 10,466 | 272 | 272 | 226.80 | 38 | 38 |
| rrr AND brem | abs | 0.75 | 12.22 AND 36.0 | 5,159 | 199 | 199 | 165.20 | 25 | 25 | 11.75 AND 38.0 | 6,148 | 244 | 244 | 195.50 | 10 | 10 |
| rrr AND brem | abs | 0.80 | 12.99 AND 30.0 | 4,136 | 188 | 188 | 157.50 | 12 | 12 | 12.61 AND 32.0 | 4,799 | 227 | 227 | 183.80 | 6 | 6 |
| rrr AND brem | abs | 0.85 | 14.08 AND 24.0 | 3,099 | 177 | 177 | 149.10 | 9 | 9 | 13.76 AND 26.0 | 3,621 | 211 | 211 | 170.20 | 2 | 2 |
| rrr AND brem | abs | 0.90 | 15.94 AND 17.0 | 2,057 | 168 | 168 | 138.50 | 3 | 3 | 15.75 AND 19.0 | 2,380 | 191 | 191 | 152.40 | 0 | 0 |
| rrr AND brem | abs | 0.95 | 21.19 AND 10.0 | 1,039 | 143 | 143 | 117.90 | 0 | 0 | 20.57 AND 11.0 | 1,167 | 166 | 166 | 129.80 | 0 | 0 |
| rrr AND wrem | abs | 0.50 | 10.09 AND 8.0 | 14,683 | 238 | 238 | 188.20 | 76 | 75 | 9.309 AND 8.0 | 18,027 | 296 | 296 | 235.50 | 95 | 93 |
| rrr AND wrem | abs | 0.60 | 10.8 AND 7.0 | 10,592 | 223 | 223 | 167.90 | 55 | 54 | 10.15 AND 7.0 | 13,340 | 270 | 270 | 211.10 | 62 | 60 |
| rrr AND wrem | abs | 0.75 | 12.22 AND 6.0 | 6,624 | 197 | 197 | 143.50 | 32 | 32 | 11.75 AND 6.0 | 8,681 | 244 | 244 | 177.00 | 30 | 30 |
| rrr AND wrem | abs | 0.80 | 12.99 AND 6.0 | 5,834 | 188 | 188 | 136.20 | 28 | 28 | 12.61 AND 5.0 | 6,310 | 225 | 225 | 166.90 | 13 | 13 |
| rrr AND wrem | abs | 0.85 | 14.08 AND 5.0 | 4,140 | 172 | 172 | 120.40 | 13 | 13 | 13.76 AND 5.0 | 5,416 | 220 | 220 | 156.40 | 9 | 9 |
| rrr AND wrem | abs | 0.90 | 15.94 AND 4.0 | 2,509 | 151 | 151 | 103.60 | 5 | 5 | 15.75 AND 4.0 | 3,328 | 199 | 199 | 128.90 | 4 | 4 |
| rrr AND wrem | abs | 0.95 | 21.19 AND 3.0 | 1,134 | 116 | 116 | 75.60 | 1 | 1 | 20.57 AND 2.0 | 1,122 | 138 | 138 | 82.10 | 0 | 0 |

### 8.chase.batter.family-c

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gap | abs | knee | 19.93 | 1,064 | 138 | 138 | 88.00 | 0 | 0 | 24.78 | 913 | 140 | 140 | 77.60 | 0 | 0 |
| neg_resource_ratio | abs | knee | -0.42 | 20,397 | 350 | 350 | 329.30 | 95 | 95 | -0.42 | 24,005 | 425 | 425 | 388.50 | 119 | 118 |
| req_to_exp | abs | knee | 1.71 | 2,131 | 123 | 123 | 55.60 | 2 | 2 | 1.89 | 2,181 | 142 | 142 | 63.20 | 0 | 0 |
| rrr | abs | knee | 27.22 | 1,160 | 142 | 142 | 92.00 | 0 | 0 | 30.40 | 1,033 | 142 | 142 | 83.40 | 0 | 0 |
| runs_required | abs | knee | 181.00 | 4,155 | 203 | 203 | 143.10 | 23 | 23 | 175.00 | 4,142 | 198 | 198 | 123.50 | 16 | 16 |

### 8.chase.bowler.family-a

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bowl_rel_A | rel | 0.50 | 0.50 | 20,642 | 294 | 294 | 225.30 | 116 | 116 | 0.50 | 24,154 | 355 | 355 | 268.80 | 135 | 135 |
| bowl_rel_A | rel | 0.60 | 0.60 | 16,566 | 267 | 267 | 189.00 | 103 | 103 | 0.60 | 19,322 | 307 | 307 | 228.50 | 116 | 116 |
| bowl_rel_A | rel | 0.75 | 0.75 | 10,372 | 222 | 222 | 136.60 | 73 | 72 | 0.75 | 12,101 | 246 | 246 | 167.60 | 75 | 75 |
| bowl_rel_A | rel | 0.80 | 0.80 | 8,308 | 207 | 207 | 117.10 | 64 | 64 | 0.80 | 9,729 | 234 | 234 | 144.10 | 59 | 59 |
| bowl_rel_A | rel | 0.85 | 0.85 | 6,238 | 191 | 191 | 91.80 | 49 | 49 | 0.85 | 7,327 | 219 | 219 | 120.20 | 38 | 38 |
| bowl_rel_A | rel | 0.90 | 0.90 | 4,190 | 167 | 167 | 68.40 | 19 | 19 | 0.90 | 4,880 | 196 | 196 | 96.50 | 20 | 20 |
| bowl_rel_A | rel | 0.95 | 0.95 | 2,117 | 138 | 138 | 42.50 | 5 | 5 | 0.95 | 2,452 | 157 | 157 | 61.70 | 6 | 6 |
| bowl_rel_B_all | rel | 0.50 | 0.50 | 20,448 | 329 | 329 | 244.80 | 113 | 113 | 0.50 | 23,939 | 394 | 394 | 297.20 | 141 | 141 |
| bowl_rel_B_all | rel | 0.60 | 0.60 | 16,378 | 321 | 321 | 215.00 | 102 | 102 | 0.60 | 19,154 | 379 | 379 | 263.60 | 119 | 119 |
| bowl_rel_B_all | rel | 0.75 | 0.75 | 10,255 | 281 | 281 | 157.80 | 77 | 77 | 0.75 | 11,985 | 347 | 347 | 200.50 | 72 | 72 |
| bowl_rel_B_all | rel | 0.80 | 0.80 | 8,208 | 261 | 261 | 135.20 | 66 | 66 | 0.80 | 9,611 | 324 | 324 | 172.80 | 55 | 55 |
| bowl_rel_B_all | rel | 0.85 | 0.85 | 6,171 | 240 | 240 | 110.60 | 46 | 46 | 0.85 | 7,222 | 293 | 293 | 142.40 | 35 | 35 |
| bowl_rel_B_all | rel | 0.90 | 0.90 | 4,141 | 204 | 204 | 85.10 | 21 | 21 | 0.90 | 4,826 | 258 | 258 | 106.70 | 22 | 22 |
| bowl_rel_B_all | rel | 0.95 | 0.95 | 2,090 | 158 | 158 | 54.10 | 4 | 4 | 0.95 | 2,434 | 185 | 185 | 67.20 | 5 | 5 |
| bowl_rel_B_noearly | rel | 0.50 | 0.50 | 18,909 | 317 | 317 | 242.00 | 106 | 106 | 0.50 | 21,972 | 379 | 379 | 289.70 | 133 | 133 |
| bowl_rel_B_noearly | rel | 0.60 | 0.60 | 15,081 | 302 | 302 | 211.40 | 96 | 96 | 0.60 | 17,489 | 350 | 350 | 253.70 | 104 | 104 |
| bowl_rel_B_noearly | rel | 0.75 | 0.75 | 9,297 | 255 | 255 | 151.70 | 69 | 69 | 0.75 | 10,786 | 292 | 292 | 188.30 | 67 | 67 |
| bowl_rel_B_noearly | rel | 0.80 | 0.80 | 7,381 | 228 | 228 | 128.40 | 59 | 59 | 0.80 | 8,560 | 263 | 263 | 159.50 | 49 | 49 |
| bowl_rel_B_noearly | rel | 0.85 | 0.85 | 5,461 | 192 | 192 | 102.40 | 34 | 34 | 0.85 | 6,345 | 228 | 228 | 128.80 | 30 | 30 |
| bowl_rel_B_noearly | rel | 0.90 | 0.90 | 3,585 | 150 | 150 | 75.90 | 17 | 17 | 0.90 | 4,160 | 177 | 177 | 93.00 | 14 | 14 |
| bowl_rel_B_noearly | rel | 0.95 | 0.95 | 1,726 | 92 | 92 | 45.00 | 3 | 3 | 0.95 | 2,052 | 106 | 106 | 56.70 | 5 | 5 |
| bowl_signal_B_all | abs | 0.50 | -13.00 | 20,454 | 327 | 327 | 238.60 | 114 | 114 | -15.98 | 23,931 | 385 | 385 | 283.20 | 141 | 140 |
| bowl_signal_B_all | abs | 0.60 | -4.25 | 16,362 | 313 | 313 | 204.10 | 99 | 99 | -6.09 | 19,145 | 372 | 372 | 248.20 | 115 | 115 |
| bowl_signal_B_all | abs | 0.75 | 11.00 | 10,228 | 275 | 275 | 149.20 | 77 | 77 | 10.46 | 11,967 | 326 | 326 | 182.30 | 75 | 75 |
| bowl_signal_B_all | abs | 0.80 | 17.60 | 8,181 | 259 | 259 | 131.60 | 68 | 68 | 18.03 | 9,573 | 311 | 311 | 160.10 | 55 | 55 |
| bowl_signal_B_all | abs | 0.85 | 26.43 | 6,137 | 241 | 241 | 110.90 | 44 | 44 | 28.43 | 7,180 | 285 | 285 | 134.20 | 39 | 39 |
| bowl_signal_B_all | abs | 0.90 | 40.00 | 4,093 | 206 | 206 | 88.30 | 23 | 23 | 43.29 | 4,787 | 257 | 257 | 102.50 | 20 | 20 |
| bowl_signal_B_all | abs | 0.95 | 65.94 | 2,046 | 172 | 172 | 59.50 | 5 | 5 | 70.00 | 2,395 | 203 | 203 | 64.90 | 4 | 4 |
| bowl_signal_B_noearly | abs | 0.50 | -11.88 | 18,403 | 305 | 305 | 229.40 | 107 | 107 | -14.67 | 21,466 | 357 | 357 | 270.20 | 131 | 130 |
| bowl_signal_B_noearly | abs | 0.60 | -3.69 | 14,721 | 286 | 286 | 195.20 | 92 | 92 | -5.61 | 17,174 | 332 | 332 | 234.20 | 105 | 105 |
| bowl_signal_B_noearly | abs | 0.75 | 10.54 | 9,201 | 233 | 233 | 140.20 | 70 | 70 | 9.90 | 10,733 | 266 | 266 | 167.90 | 63 | 63 |
| bowl_signal_B_noearly | abs | 0.80 | 16.62 | 7,361 | 206 | 206 | 122.20 | 57 | 57 | 16.91 | 8,587 | 232 | 232 | 145.60 | 46 | 46 |
| bowl_signal_B_noearly | abs | 0.85 | 24.43 | 5,521 | 183 | 183 | 101.90 | 37 | 37 | 26.27 | 6,440 | 198 | 198 | 120.60 | 33 | 33 |
| bowl_signal_B_noearly | abs | 0.90 | 36.39 | 3,681 | 144 | 144 | 78.90 | 18 | 18 | 39.52 | 4,294 | 160 | 160 | 88.40 | 17 | 17 |
| bowl_signal_B_noearly | abs | 0.95 | 56.89 | 1,841 | 94 | 94 | 50.50 | 4 | 4 | 62.04 | 2,147 | 98 | 98 | 52.20 | 3 | 3 |

### 8.chase.bowler.family-c

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bowl_signal_B | abs | knee | 73.00 | 1,743 | 162 | 162 | 53.20 | 4 | 4 | 84.86 | 1,680 | 185 | 185 | 51.30 | 1 | 1 |

### 8.inn1.batter.family-a

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| neg_par_dev | abs | 0.50 | 0.52 | 21,865 | 343 | 343 | 236.90 | 96 | 96 | 0.47 | 26,669 | 431 | 431 | 295.70 | 135 | 133 |
| neg_par_dev | abs | 0.60 | 3.69 | 17,511 | 296 | 296 | 204.20 | 87 | 87 | 3.48 | 21,351 | 371 | 371 | 251.20 | 104 | 101 |
| neg_par_dev | abs | 0.75 | 11.02 | 10,910 | 208 | 208 | 149.70 | 61 | 61 | 10.21 | 13,359 | 258 | 258 | 179.90 | 64 | 62 |
| neg_par_dev | abs | 0.80 | 14.28 | 8,720 | 185 | 185 | 129.40 | 50 | 50 | 13.63 | 10,696 | 221 | 221 | 155.90 | 47 | 46 |
| neg_par_dev | abs | 0.85 | 18.34 | 6,539 | 156 | 156 | 105.50 | 34 | 34 | 17.64 | 8,003 | 183 | 183 | 130.40 | 32 | 31 |
| neg_par_dev | abs | 0.90 | 24.10 | 4,369 | 118 | 118 | 78.90 | 21 | 21 | 23.04 | 5,330 | 149 | 149 | 102.10 | 17 | 17 |
| neg_par_dev | abs | 0.95 | 33.13 | 2,184 | 82 | 82 | 51.30 | 3 | 3 | 31.08 | 2,663 | 102 | 102 | 60.50 | 3 | 3 |
| neg_proj_gap | abs | 0.50 | -3.80 | 21,829 | 364 | 364 | 242.70 | 99 | 99 | -3.21 | 26,656 | 448 | 448 | 303.10 | 134 | 133 |
| neg_proj_gap | abs | 0.60 | -0.03 | 17,465 | 364 | 364 | 211.70 | 88 | 88 | 0.00 | 21,814 | 442 | 442 | 266.00 | 109 | 107 |
| neg_proj_gap | abs | 0.75 | 8.42 | 10,916 | 217 | 217 | 154.50 | 63 | 63 | 8.39 | 13,365 | 268 | 268 | 183.10 | 62 | 60 |
| neg_proj_gap | abs | 0.80 | 13.33 | 8,746 | 188 | 188 | 132.70 | 49 | 49 | 13.16 | 10,691 | 229 | 229 | 155.60 | 49 | 48 |
| neg_proj_gap | abs | 0.85 | 18.85 | 6,565 | 157 | 157 | 105.20 | 36 | 36 | 18.41 | 8,019 | 194 | 194 | 124.20 | 32 | 31 |
| neg_proj_gap | abs | 0.90 | 25.80 | 4,376 | 126 | 126 | 74.10 | 21 | 21 | 24.13 | 5,342 | 149 | 149 | 90.60 | 20 | 19 |
| neg_proj_gap | abs | 0.95 | 35.00 | 2,188 | 78 | 78 | 43.10 | 4 | 4 | 31.70 | 2,670 | 99 | 99 | 49.90 | 3 | 3 |
| neg_resource_ratio | abs | 0.50 | -0.38 | 21,558 | 362 | 362 | 356.10 | 89 | 89 | -0.37 | 26,454 | 445 | 445 | 433.70 | 132 | 132 |
| neg_resource_ratio | abs | 0.60 | -0.28 | 17,197 | 362 | 362 | 353.50 | 78 | 78 | -0.27 | 21,148 | 443 | 443 | 430.30 | 106 | 106 |
| neg_resource_ratio | abs | 0.75 | -0.15 | 10,720 | 362 | 362 | 348.80 | 57 | 57 | -0.14 | 13,177 | 441 | 441 | 421.70 | 59 | 59 |
| neg_resource_ratio | abs | 0.80 | -0.12 | 8,562 | 362 | 362 | 344.80 | 43 | 43 | -0.11 | 10,618 | 440 | 440 | 416.20 | 42 | 42 |
| neg_resource_ratio | abs | 0.85 | -0.08 | 6,433 | 362 | 362 | 336.50 | 33 | 33 | -0.07 | 7,913 | 440 | 440 | 407.90 | 29 | 29 |
| neg_resource_ratio | abs | 0.90 | -0.05 | 4,407 | 361 | 361 | 322.50 | 16 | 16 | -0.05 | 5,275 | 438 | 438 | 390.10 | 10 | 10 |
| neg_resource_ratio | abs | 0.95 | -0.02 | 2,111 | 359 | 359 | 275.60 | 0 | 0 | -0.02 | 2,676 | 432 | 432 | 353.80 | 0 | 0 |
| s_bat | rel | 0.50 | 0.50 | 21,856 | 349 | 349 | 243.90 | 97 | 97 | 0.50 | 26,514 | 435 | 435 | 299.50 | 130 | 129 |
| s_bat | rel | 0.60 | 0.60 | 17,504 | 316 | 316 | 212.60 | 84 | 84 | 0.60 | 21,359 | 412 | 412 | 262.70 | 108 | 107 |
| s_bat | rel | 0.75 | 0.75 | 10,988 | 268 | 268 | 154.00 | 59 | 59 | 0.75 | 13,377 | 343 | 343 | 195.30 | 67 | 66 |
| s_bat | rel | 0.80 | 0.80 | 8,821 | 240 | 240 | 131.70 | 52 | 52 | 0.80 | 10,733 | 308 | 308 | 169.90 | 45 | 45 |
| s_bat | rel | 0.85 | 0.85 | 6,627 | 207 | 207 | 109.10 | 39 | 39 | 0.85 | 8,067 | 275 | 275 | 142.70 | 32 | 32 |
| s_bat | rel | 0.90 | 0.90 | 4,455 | 167 | 167 | 84.80 | 18 | 18 | 0.90 | 5,401 | 220 | 220 | 105.80 | 13 | 13 |
| s_bat | rel | 0.95 | 0.95 | 2,259 | 119 | 119 | 55.60 | 5 | 5 | 0.95 | 2,739 | 143 | 143 | 64.20 | 0 | 0 |

### 8.inn1.batter.family-b

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| neg_par_dev AND wrem | abs | 0.50 | 0.521 AND 8.0 | 15,035 | 248 | 248 | 195.80 | 76 | 76 | 0.4724 AND 8.0 | 19,720 | 329 | 329 | 249.40 | 97 | 94 |
| neg_par_dev AND wrem | abs | 0.60 | 3.686 AND 7.0 | 10,775 | 214 | 214 | 162.00 | 56 | 56 | 3.479 AND 7.0 | 14,574 | 276 | 276 | 208.20 | 69 | 68 |
| neg_par_dev AND wrem | abs | 0.75 | 11.02 AND 6.0 | 6,553 | 169 | 169 | 122.10 | 33 | 33 | 10.21 AND 6.0 | 9,328 | 219 | 219 | 159.30 | 43 | 42 |
| neg_par_dev AND wrem | abs | 0.80 | 14.28 AND 6.0 | 5,822 | 156 | 156 | 111.30 | 26 | 26 | 13.63 AND 5.0 | 6,263 | 180 | 180 | 132.00 | 21 | 21 |
| neg_par_dev AND wrem | abs | 0.85 | 18.34 AND 5.0 | 3,393 | 129 | 129 | 83.10 | 10 | 10 | 17.65 AND 5.0 | 5,459 | 164 | 164 | 118.80 | 19 | 19 |
| neg_par_dev AND wrem | abs | 0.90 | 24.1 AND 5.0 | 2,634 | 102 | 102 | 63.90 | 6 | 6 | 23.03 AND 4.0 | 2,871 | 120 | 120 | 82.40 | 3 | 3 |
| neg_par_dev AND wrem | abs | 0.95 | 33.13 AND 4.0 | 1,058 | 58 | 58 | 34.20 | 0 | 0 | 31.08 AND 3.0 | 1,220 | 79 | 79 | 51.70 | 0 | 0 |
| neg_resource_ratio AND death | abs | 0.50 | -0.38 AND death | 10,663 | 361 | 361 | 355.10 | 60 | 60 | -0.3675 AND death | 12,929 | 435 | 435 | 431.90 | 59 | 59 |
| neg_resource_ratio AND death | abs | 0.60 | -0.28 AND death | 10,663 | 361 | 361 | 355.10 | 60 | 60 | -0.2733 AND death | 12,929 | 435 | 435 | 431.90 | 59 | 59 |
| neg_resource_ratio AND death | abs | 0.75 | -0.1517 AND death | 9,776 | 361 | 361 | 351.30 | 53 | 53 | -0.145 AND death | 11,914 | 435 | 435 | 427.80 | 50 | 50 |
| neg_resource_ratio AND death | abs | 0.80 | -0.115 AND death | 8,199 | 361 | 361 | 346.00 | 42 | 42 | -0.11 AND death | 10,192 | 435 | 435 | 420.60 | 39 | 39 |
| neg_resource_ratio AND death | abs | 0.85 | -0.08 AND death | 6,270 | 361 | 361 | 337.50 | 33 | 33 | -0.075 AND death | 7,818 | 435 | 435 | 407.70 | 28 | 28 |
| neg_resource_ratio AND death | abs | 0.90 | -0.05 AND death | 4,388 | 360 | 360 | 321.80 | 16 | 16 | -0.04583 AND death | 5,250 | 433 | 433 | 387.60 | 10 | 10 |
| neg_resource_ratio AND death | abs | 0.95 | -0.02213 AND death | 2,111 | 359 | 359 | 275.60 | 0 | 0 | -0.02 AND death | 2,676 | 432 | 432 | 353.80 | 0 | 0 |

### 8.inn1.batter.family-c

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| neg_par_dev | abs | knee | -26.83 | 39,712 | 364 | 364 | 347.50 | 119 | 119 | -31.79 | 49,431 | 448 | 448 | 432.10 | 201 | 200 |
| neg_proj_gap | abs | knee | -34.55 | 39,823 | 364 | 364 | 348.30 | 119 | 119 | -34.89 | 48,766 | 448 | 448 | 429.30 | 199 | 198 |
| neg_resource_ratio | abs | knee | -0.33 | 19,302 | 362 | 362 | 354.90 | 84 | 84 | -0.34 | 25,002 | 444 | 444 | 432.60 | 121 | 121 |

### 8.inn1.bowler.family-a

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bowl_rel_A | rel | 0.50 | 0.50 | 22,644 | 364 | 364 | 239.80 | 118 | 117 | 0.50 | 27,700 | 448 | 448 | 297.20 | 166 | 163 |
| bowl_rel_A | rel | 0.60 | 0.60 | 18,130 | 315 | 315 | 203.00 | 107 | 106 | 0.60 | 22,065 | 383 | 383 | 251.60 | 149 | 147 |
| bowl_rel_A | rel | 0.75 | 0.75 | 11,368 | 256 | 256 | 140.60 | 81 | 81 | 0.75 | 13,819 | 328 | 328 | 176.30 | 101 | 100 |
| bowl_rel_A | rel | 0.80 | 0.80 | 9,104 | 227 | 227 | 118.10 | 67 | 67 | 0.80 | 11,049 | 281 | 281 | 146.80 | 76 | 75 |
| bowl_rel_A | rel | 0.85 | 0.85 | 6,853 | 185 | 185 | 93.00 | 51 | 51 | 0.85 | 8,312 | 234 | 234 | 118.70 | 52 | 52 |
| bowl_rel_A | rel | 0.90 | 0.90 | 4,595 | 132 | 132 | 66.50 | 31 | 31 | 0.90 | 5,569 | 174 | 174 | 86.00 | 29 | 28 |
| bowl_rel_A | rel | 0.95 | 0.95 | 2,315 | 81 | 81 | 37.30 | 7 | 7 | 0.95 | 2,831 | 107 | 107 | 49.90 | 7 | 7 |
| bowl_rel_B_all | rel | 0.50 | 0.50 | 22,644 | 364 | 364 | 239.80 | 118 | 117 | 0.50 | 27,700 | 448 | 448 | 297.20 | 166 | 163 |
| bowl_rel_B_all | rel | 0.60 | 0.60 | 18,130 | 315 | 315 | 203.00 | 107 | 106 | 0.60 | 22,065 | 383 | 383 | 251.60 | 149 | 147 |
| bowl_rel_B_all | rel | 0.75 | 0.75 | 11,368 | 256 | 256 | 140.60 | 81 | 81 | 0.75 | 13,819 | 328 | 328 | 176.30 | 101 | 100 |
| bowl_rel_B_all | rel | 0.80 | 0.80 | 9,104 | 227 | 227 | 118.10 | 67 | 67 | 0.80 | 11,049 | 281 | 281 | 146.80 | 76 | 75 |
| bowl_rel_B_all | rel | 0.85 | 0.85 | 6,853 | 185 | 185 | 93.00 | 51 | 51 | 0.85 | 8,312 | 234 | 234 | 118.70 | 52 | 52 |
| bowl_rel_B_all | rel | 0.90 | 0.90 | 4,595 | 132 | 132 | 66.50 | 31 | 31 | 0.90 | 5,569 | 174 | 174 | 86.00 | 29 | 28 |
| bowl_rel_B_all | rel | 0.95 | 0.95 | 2,315 | 81 | 81 | 37.30 | 7 | 7 | 0.95 | 2,831 | 107 | 107 | 49.90 | 7 | 7 |
| bowl_rel_B_noearly | rel | 0.50 | 0.50 | 20,288 | 322 | 322 | 229.10 | 113 | 112 | 0.50 | 24,860 | 396 | 396 | 282.10 | 154 | 151 |
| bowl_rel_B_noearly | rel | 0.60 | 0.60 | 16,634 | 292 | 292 | 196.60 | 105 | 104 | 0.60 | 20,360 | 364 | 364 | 241.20 | 141 | 139 |
| bowl_rel_B_noearly | rel | 0.75 | 0.75 | 10,784 | 246 | 246 | 138.10 | 76 | 76 | 0.75 | 13,105 | 313 | 313 | 171.30 | 97 | 96 |
| bowl_rel_B_noearly | rel | 0.80 | 0.80 | 8,719 | 221 | 221 | 116.10 | 65 | 65 | 0.80 | 10,598 | 269 | 269 | 143.70 | 72 | 71 |
| bowl_rel_B_noearly | rel | 0.85 | 0.85 | 6,646 | 182 | 182 | 91.90 | 49 | 49 | 0.85 | 8,055 | 230 | 230 | 116.60 | 46 | 46 |
| bowl_rel_B_noearly | rel | 0.90 | 0.90 | 4,510 | 131 | 131 | 66.20 | 31 | 31 | 0.90 | 5,458 | 172 | 172 | 84.80 | 29 | 28 |
| bowl_rel_B_noearly | rel | 0.95 | 0.95 | 2,293 | 81 | 81 | 37.40 | 7 | 7 | 0.95 | 2,808 | 106 | 106 | 49.50 | 7 | 7 |
| bowl_signal_B_all | abs | 0.50 | -0.52 | 22,696 | 364 | 364 | 232.60 | 116 | 115 | -0.47 | 27,587 | 448 | 448 | 290.70 | 172 | 170 |
| bowl_signal_B_all | abs | 0.60 | 2.72 | 18,127 | 297 | 297 | 194.90 | 106 | 105 | 2.35 | 22,052 | 375 | 375 | 246.40 | 152 | 149 |
| bowl_signal_B_all | abs | 0.75 | 10.65 | 11,333 | 207 | 207 | 139.60 | 82 | 82 | 9.12 | 13,787 | 263 | 263 | 166.90 | 99 | 99 |
| bowl_signal_B_all | abs | 0.80 | 14.48 | 9,064 | 176 | 176 | 118.10 | 68 | 68 | 13.01 | 11,023 | 216 | 216 | 140.60 | 71 | 71 |
| bowl_signal_B_all | abs | 0.85 | 18.80 | 6,797 | 157 | 157 | 94.60 | 54 | 54 | 18.06 | 8,270 | 169 | 169 | 113.30 | 49 | 49 |
| bowl_signal_B_all | abs | 0.90 | 24.69 | 4,532 | 115 | 115 | 66.80 | 29 | 29 | 25.72 | 5,517 | 123 | 123 | 86.00 | 28 | 28 |
| bowl_signal_B_all | abs | 0.95 | 36.82 | 2,266 | 59 | 59 | 36.60 | 2 | 2 | 37.93 | 2,758 | 78 | 78 | 48.80 | 5 | 5 |
| bowl_signal_B_noearly | abs | 0.50 | -0.74 | 20,364 | 307 | 307 | 220.70 | 112 | 111 | -0.68 | 24,732 | 386 | 386 | 274.00 | 155 | 153 |
| bowl_signal_B_noearly | abs | 0.60 | 3.77 | 16,289 | 266 | 266 | 184.00 | 102 | 101 | 3.13 | 19,789 | 338 | 338 | 229.70 | 140 | 137 |
| bowl_signal_B_noearly | abs | 0.75 | 12.39 | 10,177 | 193 | 193 | 129.20 | 76 | 76 | 10.90 | 12,378 | 239 | 239 | 153.20 | 85 | 85 |
| bowl_signal_B_noearly | abs | 0.80 | 16.10 | 8,143 | 169 | 169 | 109.20 | 61 | 61 | 14.77 | 9,895 | 195 | 195 | 130.00 | 63 | 63 |
| bowl_signal_B_noearly | abs | 0.85 | 20.30 | 6,109 | 147 | 147 | 86.40 | 51 | 51 | 20.05 | 7,425 | 153 | 153 | 104.60 | 43 | 43 |
| bowl_signal_B_noearly | abs | 0.90 | 26.55 | 4,074 | 102 | 102 | 60.60 | 28 | 28 | 27.77 | 4,950 | 114 | 114 | 80.30 | 24 | 24 |
| bowl_signal_B_noearly | abs | 0.95 | 38.75 | 2,040 | 53 | 53 | 33.10 | 2 | 2 | 40.07 | 2,474 | 71 | 71 | 44.40 | 3 | 3 |

### 8.inn1.bowler.family-c

| signal | view | q | IPL thr | IPL rows | IPL matches | IPL innings | IPL n_eff(inn) | IPL >=f2 | IPL >=f2&m3 | T20I thr | T20I rows | T20I matches | T20I innings | T20I n_eff(inn) | T20I >=f2 | T20I >=f2&m3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bowl_signal_B | abs | knee | 26.83 | 3,977 | 100 | 100 | 59.20 | 26 | 26 | 31.79 | 3,868 | 103 | 103 | 66.40 | 15 | 15 |

### Opportunity counts per player for representative candidates

Mechanical illustration at q = 0.75 and 0.90 of the primary signals, not a candidate selection. Players are counted by `player_id`.

| candidate | role | players | measure p10 | p25 | p50 | p75 | p90 | max | n_eff_kish p50 | n_eff_kish p90 | matches p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a / chase / IPL / batter / rrr / abs / 0.75 | batter | 264 | 3.00 | 7.00 | 18.00 | 48.00 | 111.70 | 210.00 | 2.00 | 6.60 | 3.00 |
| a / chase / IPL / batter / rrr / abs / 0.9 | batter | 211 | 2.00 | 5.00 | 11.00 | 24.00 | 45.00 | 123.00 | 1.80 | 3.98 | 2.00 |
| a / chase / IPL / bowler / bowl_signal_B_all / abs / 0.75 | bowler | 201 | 6.00 | 12.00 | 30.00 | 74.00 | 118.00 | 266.00 | 2.67 | 8.61 | 3.00 |
| a / chase / IPL / bowler / bowl_signal_B_all / abs / 0.9 | bowler | 169 | 2.80 | 7.00 | 16.00 | 32.00 | 54.80 | 106.00 | 1.98 | 5.79 | 2.00 |
| a / inn1 / IPL / batter / neg_par_dev / abs / 0.75 | batter | 233 | 3.00 | 6.00 | 23.00 | 68.00 | 125.00 | 315.00 | 2.25 | 6.48 | 3.00 |
| a / inn1 / IPL / batter / neg_par_dev / abs / 0.9 | batter | 181 | 2.00 | 5.00 | 15.00 | 34.00 | 64.00 | 123.00 | 1.69 | 3.48 | 2.00 |
| a / inn1 / IPL / bowler / bowl_signal_B_all / abs / 0.75 | bowler | 198 | 5.70 | 12.00 | 32.00 | 77.00 | 146.20 | 227.00 | 2.61 | 9.21 | 3.00 |
| a / inn1 / IPL / bowler / bowl_signal_B_all / abs / 0.9 | bowler | 154 | 5.30 | 10.00 | 18.50 | 42.00 | 65.00 | 98.00 | 1.72 | 5.01 | 2.00 |
| a / chase / T20I / batter / rrr / abs / 0.75 | batter | 460 | 2.00 | 6.00 | 15.00 | 32.00 | 60.00 | 248.00 | 1.85 | 4.58 | 2.00 |
| a / chase / T20I / batter / rrr / abs / 0.9 | batter | 334 | 2.00 | 4.00 | 9.00 | 17.75 | 29.70 | 97.00 | 1.33 | 3.49 | 2.00 |
| a / chase / T20I / bowler / bowl_signal_B_all / abs / 0.75 | bowler | 348 | 3.00 | 8.00 | 19.00 | 39.50 | 78.30 | 295.00 | 1.92 | 6.17 | 2.00 |
| a / chase / T20I / bowler / bowl_signal_B_all / abs / 0.9 | bowler | 269 | 2.00 | 5.00 | 10.00 | 21.00 | 41.20 | 146.00 | 1.42 | 4.35 | 2.00 |
| a / inn1 / T20I / batter / neg_par_dev / abs / 0.75 | batter | 459 | 2.00 | 5.00 | 14.00 | 34.00 | 74.20 | 294.00 | 1.34 | 4.72 | 2.00 |
| a / inn1 / T20I / batter / neg_par_dev / abs / 0.9 | batter | 306 | 2.00 | 4.00 | 9.00 | 21.00 | 42.50 | 111.00 | 1.00 | 3.66 | 1.00 |
| a / inn1 / T20I / bowler / bowl_signal_B_all / abs / 0.75 | bowler | 306 | 6.00 | 12.00 | 26.00 | 57.00 | 97.00 | 235.00 | 2.00 | 6.58 | 3.00 |
| a / inn1 / T20I / bowler / bowl_signal_B_all / abs / 0.9 | bowler | 232 | 5.00 | 6.00 | 16.00 | 29.25 | 52.00 | 105.00 | 1.66 | 4.24 | 2.00 |

## 9. Strictly-prior versus LOMO innings-1 par

Strictly prior needs at least 30 earlier source innings. Early-window rows have no value and are never filled.

| comp | q | LOMO thr | LOMO rows | LOMO matches | LOMO innings | prior thr | prior rows | prior matches | prior innings | prior population rows | LOMO population rows |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | 0.50 | 0.52 | 22,663 | 343 | 343 | -3.16 | 20,788 | 334 | 334 | 41,575 | 45,312 |
| IPL | 0.60 | 3.69 | 18,150 | 296 | 296 | 0.00 | 16,761 | 334 | 334 | 41,575 | 45,312 |
| IPL | 0.75 | 11.02 | 11,329 | 208 | 208 | 5.06 | 10,394 | 210 | 210 | 41,575 | 45,312 |
| IPL | 0.80 | 14.28 | 9,063 | 185 | 185 | 7.96 | 8,315 | 173 | 173 | 41,575 | 45,312 |
| IPL | 0.85 | 18.34 | 6,797 | 156 | 156 | 11.69 | 6,237 | 139 | 139 | 41,575 | 45,312 |
| IPL | 0.90 | 24.10 | 4,536 | 118 | 118 | 17.53 | 4,158 | 104 | 104 | 41,575 | 45,312 |
| IPL | 0.95 | 33.13 | 2,267 | 82 | 82 | 26.14 | 2,079 | 67 | 67 | 41,575 | 45,312 |
| T20I | 0.50 | 0.47 | 27,563 | 431 | 431 | -0.56 | 25,631 | 417 | 417 | 51,262 | 55,113 |
| T20I | 0.60 | 3.48 | 22,046 | 371 | 371 | 2.14 | 20,505 | 353 | 353 | 51,262 | 55,113 |
| T20I | 0.75 | 10.21 | 13,780 | 258 | 258 | 8.56 | 12,816 | 243 | 243 | 51,262 | 55,113 |
| T20I | 0.80 | 13.63 | 11,033 | 221 | 221 | 11.96 | 10,253 | 203 | 203 | 51,262 | 55,113 |
| T20I | 0.85 | 17.65 | 8,270 | 183 | 183 | 15.93 | 7,690 | 171 | 171 | 51,262 | 55,113 |
| T20I | 0.90 | 23.03 | 5,513 | 149 | 149 | 21.29 | 5,127 | 142 | 142 | 51,262 | 55,113 |
| T20I | 0.95 | 31.08 | 2,760 | 102 | 102 | 29.20 | 2,564 | 96 | 96 | 51,262 | 55,113 |

## 10. Independent cross-check

Candidate `a / chase / IPL / batter / rrr / abs / 0.9` recomputed with a separate DuckDB SQL implementation (population filter, quantile_cont, counts) and compared with the pandas engine:

| quantity | engine | independent SQL | match |
|---|---|---|---|
| threshold | 15.94 | 15.94 | yes |
| pressure balls faced | 3,884 | 3,884 | yes |
| matches | 175 | 175 | yes |
| innings | 175 | 175 | yes |
| batters with >= floor 2 balls | 10 | 10 | yes |

## 11. Interpretation

- The chase RRR distribution is right-skewed; its upper tail consists of rows with few balls left, so RRR is reported with `Brem` and uncapped/capped. A death-over chase is not high pressure by label alone; the relative view compares it with other death-over chases.
- Candidate populations shrink quickly as q grows. The section 8 tables show where the batter and bowler pools fall below ten players at each floor.
- Nothing here selects a definition. Stage 5 reads these populations, bootstraps by match and states which definitions are defensible.

## 12. Limitations (exploratory)

1. Pressure signals ignore opposition quality, pitch, weather, boundary size and real DLS resources.
2. Quantiles and par tables use the whole data window including later matches (FULL_SAMPLE/LOMO).
   Only the innings-1 par has a strictly-prior variant; strictly-prior `exp_remaining` and
   `req_to_exp` variants are not built in this chunk.
3. Deliveries inside an innings are autocorrelated. Effective sample sizes use innings (population)
   and matches (players) as clusters through the Kish formula.
4. Membership changes under the alternative wicket count `W_alt` are not recomputed per candidate in
   this chunk. The rows affected by the 12 flag disagreements are counted in section 2.
5. Family (b) conjunctions are evaluated for batters only. Bowling convention A is defined through
   the relative view only (it is the mirror of batting relative pressure).
6. Players are identified by `player_id`. No name join is used (RULE_DUPLICATE_NAMES).
