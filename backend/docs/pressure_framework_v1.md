# Pressure framework specification v1 (Phase 3, Stage 1)

Version: `pressure_framework_v1` (revision 4, after the third design review `phase3prep_design_review.json`; its 9 findings are answered in Appendix A, section "Revision 4"; the 12 findings of the second review are in section "Revision 3"). Date context: November 2026. Written before any pressure calculation. No code is part of this document.

## 1. Status: exploratory versus validated (read first)

| Item | Status |
|---|---|
| Every definition, formula, band and candidate in this document | SPECIFICATION. Nothing here has been run as a pressure score. |
| Every number that Stages 2 to 6 will produce from this specification | EXPLORATORY PROXY CALCULATION (`status: EXPLORATORY_NOT_VALIDATED`). |
| Validated pressure results | NONE. No pressure score, band, baseline or ranking is validated. |
| Official Top 10 rankings | NOT PUBLISHED. `official_ranking: false`, `not_for_publication: true`. |
| 70:30 IPL/T20I weighting | PROVISIONAL default, not a validated optimum. Eight configurations preserved: 100:0, 85:15, 80:20, 70:30, 60:40, 55:45, 50:50, 0:100. |
| Pressure thresholds | NOT CHOSEN here. Candidates come from observed distributions in Stage 3. |
| Data facts quoted in section 2 | VERIFIED by read-only DuckDB queries on `superr.duckdb` while writing this revision. They are facts about the data, not pressure results. Stage 2 must recompute and assert them. |
| Cricsheet | Validation only. Never a feature, baseline, training row or ranking input (section 5.4 item 10, section 12). |
| ML models | None trained. Gradient boosting and logistic models appear only as design options (section 13). |

Approved decisions carried unchanged: zero BLOCKING issues; `config/data_quality_restrictions_v1.json` is the metric-level register (26 issues, `global_exclusion: false` everywhere); innings 3 and 4 are excluded from regulation-pressure metrics for all six matches (34429, 45512, 50359 confirmed Super Over by Cricsheet; 40725, 48027, 48029 unverified); source deliveries are preserved.

## 2. Verified data facts the definitions rely on

All figures come from read-only DuckDB queries on the official tables (`deliveries`, `matches`).

| Fact | Value |
|---|---|
| Deliveries | 200,999 rows in 867 matches (IPL 367, T20I 470, OTHER_T20 30). Data window 2022-01-22 to 2026-11-01. |
| Innings 1 / 2 / 3 / 4 rows | 105,727 / 95,234 / 25 / 13. Innings 3 and 4 occur only in 6 matches (38 rows). |
| Regulation rows (innings 1 and 2) | 200,961 in 1,712 innings. |
| Regulation innings by format (innings 1 + innings 2) | IPL 367 + 363, T20I 470 + 452, OTHER_T20 30 + 30. OTHER_T20 is excluded from IPL and T20I scores. |
| Contiguity | `innings_ball_num` runs 1..n with no gaps in every regulation innings. |
| `overid` | 1 to 20 in regulation innings; never above 20. Innings 3 and 4 have `overid` 1 only. |
| Legal balls per regulation innings | 2 to 120 (legal = `is_legal_ball` with the Penalty row counted as 0). No innings has more than 10 wicket rows. |
| Overs touched per regulation innings (ceil legal balls / 6) | 1:2, 3:1, 4:4, 5:6, 6:2, 7:7, 8:7, 9:4, 10:12, 11:21, 12:8, 13:12, 14:30, 15:25, 16:47, 17:65, 18:74, 19:154, 20:1,231 innings. 1,011 innings have 120 legal balls, 264 end with 10 wickets. |
| Rows in overs 16 to 20 | 44,452 of 200,961 (22.1%) by legal-ball over index; 44,454 by `overid`. 33 rows in 5 innings of 4 matches disagree between `overid` and the legal-ball over index: 14130 (innings 1: 6 rows, innings 2: 8), 14164 (innings 1: 6), 16753 (innings 2: 5, contains the Penalty row), 41509 (innings 1: 8). |
| `over_ball_num` | Row counter, not a legal-ball counter. It exceeds 6 on thousands of rows. Neither it nor `overid` is used as an over index. |
| Over index anomalies | One `overid` over has 7 rows flagged legal with `extras_type = 'None'`: match 41509, innings 1, `overid` 12 (innings ball 68 to 74). Under the cumulative legal-ball rule the 7th legal ball is ball 1 of the next legal over, so `ball_in_over_k` stays within 1 to 6 and `over_k` advances one ball earlier than `overid` for the rest of that innings. By legal-ball index no over has more than 6 legal balls. One legal-index over has 0 legal balls (match 24353, innings 2, legal over index 18, which holds only non-legal rows). Overs with fewer than 6 legal balls: 580 by `overid` grouping with the DB flag, 581 by legal-ball index. The reason for the difference of one is not determined; Stage 2 reports both counts and lists the over. |
| Legal flags | 192,445 rows are flagged `is_legal_ball` in the DB (None 189,167, legbyes 2,748, byes 529, Penalty 1). 192,444 are counted as legal balls after the Penalty rule. 8,554 are not legal (wide 7,714, Overstep 576, other 264). |
| `first_inn_revised_overs`, `second_inn_revised_overs` | Stored as DOUBLE. Values: 30, 42, 48, 54, 60, 66, 72, 78, 84, 90, 102, 108, 114. All are multiples of 6, so they are BALLS despite the column name. No fractional values. No innings has more legal balls than its stated value. Innings counts by value (regulation innings, `L`): 30:4, 42:3, 48:4, 54:4, 60:3, 66:4, 72:2, 78:2, 84:4, 90:7, 102:4, 108:2, 114:5, 120:1,664. 14 distinct `L` values; 48 innings have `L` < 120 (innings 1: 25, innings 2: 23). |
| Matches with any revised field | 34 (union). `first_inn_revised_overs` non-null: 25. `second_inn_revised_overs` non-null: 25. `revised_target` non-null: 23. Truth table in section 7.6. |
| Revised targets | 23, every one with `second_inn_revised_overs` non-null. 8 equal innings-1 total + 1. 15 differ (6 with a revised innings-1 limit, 9 with an unrevised innings 1). |
| Revised-target meaning | Of the 22 COMPLETED matches with a revised target, 22 agree with `chasing score >= revised_target` versus chaser win. Of the 811 COMPLETED chases without a revised target, 809 agree with `score >= innings-1 total + 1`. The 2 that do not agree are matches 24822 and 28334, whose `result` text says "DLS method" while no revised field is recorded (section 7.6, open decision 13). `result` is used here only to verify the data, never as a feature. |
| Chases | 845 innings 2: 822 without a revised target, 23 with. 164 ended all out. 833 are in COMPLETED matches. |
| Incomplete innings 1 without any revised field | 42 IPL/T20I innings 1 end with fewer than 120 legal balls and fewer than 10 wickets (reviewer read-only check, to be recomputed by Stage 2). 23 of them carry `first_inn_revised_overs`. 19 carry none; these are the 19 "not complete" innings-1 sources above (match 23674 is one; its `result` text mentions DLS). The innings-2 target of such a match is innings-1 total + 1 with unverified validity; see `target_basis_unverified` (section 3, 7.2). The number of affected chases (at most 19, fewer where no innings 2 exists) is a Stage 2 build count. |
| `result` text mentioning DLS or D/L | 19 matches. 15 of them have a revised field. 4 have none: 20182, 23674, 24822, 28334. |
| `Req <= 0` before a delivery | 12 rows, all in match 48610 innings 2 (revised target 115, revised limit 90, innings-1 total 133). Cause not determined by the data. Reported by the Stage 2 build as an assertion count, not assumed to be impossible. |
| `dismissal_type` with `is_wicket` true | Caught 7,557; Bowled 1,775; LBW 709; RunOut 600; Stump 214; Hit Wicket 17; Retire Out 6; Obstracting the field 2; Obstructing the field 1. Total 10,881. Null on every non-wicket row. |
| Bowler-credited wickets | 10,272 (Caught, Bowled, LBW, Stump, Hit Wicket). Not bowler-credited: 609 (RunOut, Retire Out, both Obstructing spellings). |
| `extras_type` | None (literal string) 189,167; wide 7,714; legbyes 2,748; Overstep 576; byes 529; other 264; Penalty 1 (match 16753, innings 2, ball 34). |
| Rows with `extras_type = 'None'` but nonzero extras runs | 2: match 17555 innings 1 ball 29 (secondary 1), match 36097 innings 2 ball 49 (primary 1). |
| Wicket-flag disagreements | 12 rows with `dismissed_player_id` set and `is_wicket` false (matches 14114, 15610, 16064, 20188, 20243, 20880, 28964, 29926, 31709, 37094, 40725, 40763). 1 row `is_wicket` true with no dismissed player (match 40709, Retire Out). The 12 rows precede 739 later rows of their innings (section 3, `W_alt`). |
| Knockout matches | 31 (all have deliveries). |
| Complete innings-1 source for par (section 6) | Innings 1 of IPL and T20I with `L` = 120: 364 + 448 = 812. Complete (10 wickets or 120 legal balls): IPL 358, T20I 435 = 793. Not complete: IPL 6, T20I 13 = 19. Innings 1 with `L` < 120: IPL 3, T20I 22. |
| Innings ending early | All-out innings: innings 1 = 100, innings 2 = 164. Of these, ending before their stated limit in legal balls: innings 1 = 81, innings 2 = 153 (includes shortened innings). So early-ended innings are common (verified read-only) and the par-curve rule in section 6 must define them. |
| Season labels | `competitions.season` for IPL is the single year 2022 to 2026. For T20I it is `2022` (94 matches), `2022/23` (12), `2023` (63), `2023/24` (3), `2024` (109), `2024/25` (3), `2025` (126), `2026` (72). OTHER_T20 is `2024` (15) or `2025` (15). `matches` has no season column; season comes from `competitions` through `comp_id`. Calendar year of `match_date` for the 18 split-year T20I matches (12 + 3 + 2 + 1): 2022 (the 12 `2022/23` matches), 2023 (3 `2023/24`), 2024 (2 `2024/25`) and 2025 (1 `2024/25`). Section 3 defines `season_label`. |
| Cricsheet total disagreements | 10 innings in 6 matches. List read from `data/reports/data_quality_impact_report.json`, full key path `issue_register.cricsheet_total_disagreements` (a list of 10 entries; the register holds descriptive text only). |

Phase boundaries for a full 120-ball innings: overs 1 to 6 are legal balls 0 to 35 before the delivery (powerplay), overs 7 to 15 are balls 36 to 89 (middle), overs 16 to 20 are balls 90 to 119 (death).

## 3. Core definitions and notation

All state is computed immediately BEFORE a delivery from rows strictly earlier in the same innings, plus match-level information that was knowable before that delivery (section 5).

| Symbol | Definition | Source columns |
|---|---|---|
| `row_k` | k-th row of an innings ordered by `innings_ball_num` | `innings_ball_num` |
| `R_k` | Team runs before row k = sum over earlier rows of `batter_runs + extras_primary_runs + extras_secondary_runs`. Only the sum is used; the secondary split is unverified. | `batter_runs`, `extras_primary_runs`, `extras_secondary_runs` |
| `W_k` | PRIMARY wickets fallen before row k = count of earlier rows with `is_wicket` true (every dismissal type, including Retire Out, counts for the team) | `is_wicket` |
| `W_alt_k` | SENSITIVITY wickets fallen = count of earlier rows with `is_wicket` true OR `dismissed_player_id` not null | `is_wicket`, `dismissed_player_id` |
| `Wrem_k`, `Wrem_alt_k` | `10 - W_k`, `10 - W_alt_k` | derived |
| `legal_inc` | (For row k, an outcome-conditioned denominator flag, section 5.3; `B_k` sums it over EARLIER rows only.) 1 if `is_legal_ball` and `extras_type <> 'Penalty'`, else 0. Wide, Overstep, other add 0. Byes, legbyes, 'None' add 1. Penalty adds 0 (RULE_EXTRAS_PENALTY). | `is_legal_ball`, `extras_type` |
| `B_k` | Legal balls bowled before row k = sum of earlier `legal_inc` | derived |
| `L` | Innings ball limit: 120 by default; the innings' own revised value (in balls) when stated (section 7.6) | `matches.first_inn_revised_overs`, `second_inn_revised_overs` |
| `Brem_k` | `L - B_k` (never negative; the build fails if any innings exceeds its limit) | derived |
| `over_k` | Legal over index, 1-based = floor(`B_k` / 6) + 1. Advances on the 7th legal ball of an `overid` over, as in match 41509. | derived, not `overid` |
| `ball_in_over_k` | `B_k` mod 6 + 1 (always 1 to 6) | derived |
| `CRR_k` | `R_k / B_k * 6`; NULL (not 0) when `B_k = 0` | derived |
| `T` | Target, innings 2 only (section 7.2) | `matches`, innings 1 total |
| `Req_k` | `T - R_k`. The build counts rows with `Req_k <= 0` and sets `req_nonpositive_flag`; such rows stay in the table and are excluded from chase pressure populations (12 rows in match 48610 were seen in the read-only check). | derived |
| `RRR_k` | `Req_k / Brem_k * 6`; NULL when `Brem_k = 0` or no target | derived |
| `gap_k` | `RRR_k - CRR_k`; NULL when either is NULL | derived |
| `season_label` | IPL: `competitions.season` (year, 2022 to 2026). T20I and OTHER_T20: calendar year of `matches.match_date`. The original `competitions.season` is kept beside it as `season_source`. Fixed before the match starts, so it is a pre-delivery context variable. Joined `matches.comp_id` to `competitions.comp_id`. | `competitions.season`, `matches.match_date`, `matches.comp_id` |
| `target_basis_unverified` | Innings 2 only. True when innings 1 of the same match has `W < 10` AND legal balls `< L1` AND no `first_inn_revised_overs` AND the match has no `revised_target`. Innings-1 completeness is known when innings 2 starts, so the flag is a legitimate pre-delivery context column. It says the target `innings-1 total + 1` rests on an incomplete innings 1 with no recorded reason, so its validity is unverified. `result` text is NOT used. | innings-1 rows, `matches` revised fields |
| `counts_as_ball_faced` | Striker not null and `extras_type` not in (wide, Penalty), innings 1 and 2. A no-ball (Overstep, other) is a ball faced but not a legal ball. This is the Phase 2.5 `BATTER_SQL` definition, reused unchanged. For row k it is an OUTCOME-CONDITIONED DENOMINATOR FLAG (section 5.3): it may select rows for a per-ball-faced rate and never enters a state, par or rank cell. | `striker_id`, `extras_type` |

Not every row is a legal delivery. Counters are never taken from `innings_ball_num`, `over_ball_num` or `overid`.

`W_k` is primary. The 12 disagreement rows would, if they are real dismissals, leave `Wrem_k` too high for every later row of the same innings (739 rows). That changes `resource_ratio`, wickets bins, phase-by-wickets cells and the baseline cell for those rows, not only dismissal rates. Therefore the state engine writes both `Wrem_k` and `Wrem_alt_k`, and sets `state_wicket_flag_disagreement` on every later row of the 12 affected innings. Stage 3 reports, per candidate pressure definition, how many deliveries change membership or band under `W_alt`. The state-level variant is a sensitivity; the primary stays `is_wicket`. The Retire Out row in match 40709 has `is_wicket` true and counts in both `W_k` and `W_alt_k`.

## 4. Absolute and relative pressure

Pressure is a property of the match state before a delivery. Two views are defined. Neither is a validated measure of difficulty.

**Absolute pressure.** A signal value taken as is (`RRR`, `Req`, `Brem`, `Wrem`, `par_deviation`). It is compared with quantiles of the whole regulation population of the relevant context (chase or first innings). Those quantiles are `FULL_SAMPLE` quantities: they are computed over every regulation delivery in the data window, which includes the row's own match and matches played later. They are descriptive only and are not allowed in a predictive or strictly-prior claim (section 5.3, section 14). It answers: how demanding is this state in raw terms.

**Relative pressure.** The same signal expressed as the percentile rank among similar historical situations. The peer cell is `competition_type x innings role x phase x wickets-remaining bin`. Relative pressure removes the effect of phase (a required rate of 10 in over 18 is not the same as in over 4) and format scoring environment. It answers: how unusual is this state for its situation.

Exact definition of the relative percentile (applies everywhere in this document):

```
rank_pct(x ; cell, match M) =
    ( count(v in V where v <  x) + 0.5 * count(v in V where v == x) ) / count(V)
V = signal values of DELIVERIES in `cell` that belong to matches other than M
```

- Ties use the mid-rank rule above. Result lies in [0, 1].
- Own match M is excluded completely (all its innings). This also removes the correlated rows of the same innings.
- Direction: signals are oriented so that a higher value is more batting pressure: `RRR`, `Req`, `-par_deviation`, `-projected_total_gap`, `-resource_ratio`, `req_to_exp`. `Wrem` and `Brem` enter only through `resource_ratio` and as cell variables.
- Fallback: if the cell has fewer than `min_cell_innings` distinct innings (section 8), use the parent cell (drop the wickets bin, then drop phase, then `competition_type` only). The row records `cell_level_used` (L0 to L3).
- NULL handling. NULL signals are excluded from `V` and from `count(V)`. `rank_pct` is NULL when the row's own signal is NULL (for example `RRR` with `Brem = 0`, `Req <= 0` rows, `par_unavailable`, `exp_unavailable`). `req_to_exp` is NULL when `exp_remaining` is NULL or `<= 0`. The build manifest counts each exclusion by signal and cell level: `n_null_signal_excluded_from_V`, `n_rank_pct_null_own_signal`, `n_req_to_exp_null`.
- Clustering unit: deliveries inside one innings are autocorrelated, so the cell count that governs fallback is distinct innings, and effective sample sizes are computed with innings as the clustering unit (Kish `n_eff_kish`, with innings-level weights).

| Property | Absolute | Relative |
|---|---|---|
| Formula | signal value `x` | `rank_pct(x ; cell, M)` as above |
| Strength | Transparent, no cell estimation | Controls phase and format; does not call every death-over chase "high pressure" |
| Weakness | Confounded with phase and format | Depends on cell definitions and sizes; sparse cells need fallback |
| Use in Stage 3 | Distributions and candidate thresholds | Same |
| Primary choice | OPEN DECISION 1 | OPEN DECISION 1 |

No cutoff is chosen. Stage 3 reports quantile candidates from the search grid in section 8 and the population each selects. The grid is a search grid, not a selection.

## 5. Pre-delivery information boundary

### 5.1 What is known before delivery k

- Every earlier row of the same innings.
- Match context fixed before the match: competition type, season, venue, stage, knockout flag, teams, toss, players on the field (striker, non-striker, bowler IDs).
- For innings 2: the target derived from innings 1, because innings 1 is complete before innings 2 starts. DLS targets are the exception (see availability matrix).
- Nothing from later innings-2 rows.

### 5.2 What is not known before delivery k

- The outcome of delivery k (runs, wicket, extras, boundary flags, dismissal).
- Any later delivery in the same innings.
- For innings 1 rows: the innings-1 final total, anything from innings 2, the match result.
- Final winning margin, `win_team_id`, `result`, `result_status`, `man_of_the_match`.
- Future player statistics: any statistic computed from deliveries after delivery k, including career or season totals that include later matches.
- Post-match and post-innings counts: `innings.delivery_count`, `legal_ball_count`, `source_total_runs`, `wicket_rows`, `max_overid` of the same innings.

### 5.3 Feature availability matrix

"Pre-delivery" values: `yes` (computable from information known before delivery k), `PARTIAL` (computed with information that was not all known at delivery k; descriptive use only), `NO`. `par_basis` records how an expectation was built: `LOMO` (leave-one-match-out: uses all other matches, including matches played after the row's match), `STRICTLY_PRIOR` (only matches dated before the row's match date), `FULL_SAMPLE` (computed over every regulation delivery in the data window, including the row's own match and later matches; descriptive only, never used in a predictive or strictly-prior claim), or `n/a`. "State label" means the variable may enter a pressure-state definition. "Outcome label" means it may be the quantity predicted or compared with expectation.

| Variable | Pre-delivery | par_basis | Reason | State label | Outcome label |
|---|---|---|---|---|---|
| `R_k`, `W_k`, `Wrem_k`, `B_k`, `Brem_k`, `over_k`, `ball_in_over_k`, `CRR_k` | yes | n/a | Exclusive cumulative sums of earlier rows | yes | no |
| `W_alt_k`, `Wrem_alt_k` | yes | n/a | Earlier rows only; sensitivity variant | sensitivity only | no |
| Innings limit `L` = 120 | yes | n/a | Fixed by format | yes | no |
| Revised limit `L` (DLS) | PARTIAL | n/a | The revision is announced at an unknown ball; the data hold no interruption ball. Applying it from ball 1 uses hindsight for rows before the interruption. Flag `limit_applied_from_start_assumed`. | yes, with flag; excluded from primary population | no |
| Target `T`, innings 2, no revision | yes | n/a | Innings-1 total is complete before innings 2 | yes | no |
| `target_basis_unverified` (innings 2) | yes | n/a | Innings-1 completeness (`W`, legal balls, revised fields) is known before innings 2 starts. The `result` text is not an input. | context flag; selects the primary chase population | no |
| `exp_cell_level_used`, `exp_cell_level_used_prior` | yes for the prior variant; PARTIAL for LOMO | LOMO / STRICTLY_PRIOR | Records which fallback level produced `exp_remaining` (section 6) | context only | no |
| Revised target `T` | PARTIAL | n/a | Official `revised_target` is the final target, not the target at each ball. Same hindsight issue. | yes, with flag; excluded from primary population | no |
| `Req_k`, `RRR_k`, `gap_k` | yes for unrevised `T`; PARTIAL for revised `T` | n/a | Derived from `T` and earlier rows | yes (see `T`) | no |
| Innings-1 total, in an innings-1 row | NO | n/a | Future information | no | no |
| `par_runs`, `par_deviation`, `par_total`, `projected_total_gap` (LOMO) | PARTIAL | LOMO | Uses other matches including later ones. Descriptive of the historical distribution; NOT valid for predictive claims. Own match always excluded. | yes (descriptive) | no |
| Same quantities, strictly-prior variant | yes | STRICTLY_PRIOR | Only matches dated before the row's match date, at least `min_prior_innings` prior complete innings in the cell; else NULL and the row is reported as `par_unavailable` | yes | no |
| `exp_remaining`, `req_to_exp` (LOMO) | PARTIAL | LOMO | As above | yes (descriptive) | no |
| `exp_remaining`, `req_to_exp` (strictly prior) | yes | STRICTLY_PRIOR | As above | yes | no |
| Season or venue run-environment ratio (LOMO, by `season_label`) | PARTIAL | LOMO | Other matches including later ones. Sensitivity only (open decision 10). | no (not primary) | no |
| `rank_pct` using LOMO cells | PARTIAL | LOMO | Cell values come from other matches including later ones | yes (descriptive) | no |
| `rank_pct` using strictly-prior cells | yes | STRICTLY_PRIOR | As above | yes | no |
| Batter balls faced before, batter runs before | yes | n/a | Earlier rows only | yes | no |
| Bowler legal balls, runs, wickets before in this innings; overs completed before | yes | n/a | Earlier rows only | yes | no |
| `competition_type`, `season_label`, `venue_id`, `stage`, `knock_out`, team ids, `toss_*` | yes | n/a | Fixed before the match (`season_label` defined in section 3) | yes (context) | no |
| Absolute-pressure quantile cutoffs (Stage 3 candidate cut points) | PARTIAL | FULL_SAMPLE | Quantiles of the whole regulation population, own match and later matches included | descriptive only | no |
| `wickets_bins` partition (section 8) | PARTIAL | FULL_SAMPLE | The merge algorithm reads distinct-innings counts over all matches | descriptive only | no |
| `rrr_cap` (observed p99 of chase RRR) | PARTIAL | FULL_SAMPLE | p99 over all regulation chase rows | descriptive only (reported variant, never silent) | no |
| Baseline cell means and shrunk cell estimates (B0, with own match inside the cell) | PARTIAL | FULL_SAMPLE | Cell means include the delivery's own match and later matches | descriptive only | no (they are expectations, not outcomes) |
| Baseline `leave_match_out` variant | PARTIAL | LOMO | Cell means without the row's own match; still uses later matches. Always reported next to leave-player-out (design notes D) | descriptive only | no |
| Baseline leave-player-out expected values | PARTIAL | FULL_SAMPLE | Removes only the player's own deliveries from the cell; the same match's other deliveries and all later matches remain, so a player's own match still influences his expectation through teammates and opponents | descriptive only | no |
| Baseline `strictly_prior` variant | yes | STRICTLY_PRIOR | Cell means from matches dated before the row's match date only; cells below `min_prior_innings` return NULL. Required for any predictive claim (section 14) | yes | no |
| Per-player empirical-Bayes prior (between-player variance of residuals, shrinkage target) | NO for any delivery of the player's earlier matches | FULL_SAMPLE | Estimated on all matches including deliveries after the one concerned. It is a future player statistic if used predictively, so it is descriptive only and is not allowed in a strictly-prior validation claim | descriptive only | no |
| Striker, non-striker, bowler IDs | yes | n/a | Known at the crease | context only | no |
| Season or career player statistics | NO unless computed from matches strictly before the match date | n/a | Future player statistics forbidden. Not used in v1. | no | no |
| Outcome of delivery k: `batter_runs`, `is_four`, `is_six`, `is_wicket`, `dismissal_type`, `dismissed_player_id`, extras on delivery k, `is_legal_ball` of delivery k | NO | n/a | They define the delivery's result | no | yes |
| `extras_type` of delivery k | NO | n/a | Wide or no-ball is part of the outcome | no | yes |
| `counts_as_ball_faced` of delivery k | NO | n/a | Depends on `extras_type` of row k. Outcome-conditioned denominator flag: may select rows for a per-ball-faced rate, never enters a state, par or rank cell | no | no (denominator flag only) |
| `legal_inc` of delivery k | NO | n/a | Depends on `is_legal_ball` and `extras_type` of row k. Outcome-conditioned denominator flag: may select rows for a per-legal-ball rate, never enters a state, par or rank cell. Its cumulative sum over EARLIER rows (`B_k`) is allowed | no | no (denominator flag only) |
| `win_team_id`, `result`, `result_status`, winning margin, `man_of_the_match` | NO | n/a | Post-match. `result` text is used only to verify data (section 2) and to list DLS-suspected matches for sensitivity reporting, never in a state. | no | no |
| `innings.source_total_runs`, `legal_ball_count`, `wicket_rows`, `delivery_count`, `max_overid` of the same innings | NO | n/a | Post-innings totals | no | no |
| `delivery_ts`, `delivery_time_raw`, `delivery_time_is_midnight` | NO | n/a | RULE_UTC_SUFFIX, RULE_MIDNIGHT_TIMES | no | no |
| `match_squads` fields | not used | n/a | RULE_XI_DUPLICATES, RULE_XI_COUNT, RULE_NO_XI_MATCHES | no | no |
| `bowl_speed`, `stroke`, `delivery_style`, `on_or_off`, `over_or_around`, `pace_or_spin` of the current delivery | NO | n/a | Describe how the delivery was bowled or played | no | no (not in v1) |

### 5.4 Forbidden-variable list

A variable on this list may not appear in any pressure-state definition, state feature, par or expectation input for the row concerned:

1. Outcome of the delivery being predicted or compared (`batter_runs`, `is_four`, `is_six`, `is_wicket`, `dismissal_type_id`, `dismissal_type`, `dismissed_player_id`, `extras_*` of that row, `is_legal_ball` of that row).
2. Final match result: `win_team_id`, `result`, `result_status`.
3. Final winning margin (parsed from `result` or any other field).
4. `man_of_the_match`.
5. Any later delivery in the same innings.
6. Innings-1 total in innings-1 rows. Innings-1 total in innings-2 rows is allowed only as the target.
7. Own-match data in par curves, expected remaining runs and relative-percentile cells for that match.
8. Future player statistics: any player aggregate that includes deliveries after the delivery being processed.
9. Post-innings totals from the `innings` table.
10. Cricsheet-derived values of any kind as feature, baseline or label. Cricsheet-derived lists (the ten disagreeing innings, the three confirmed Super Over match ids) are used only as row masks and reason codes, never to replace a value. They are read from the Phase 2.5 reports in `data/reports/`, never from Cricsheet files, and no Cricsheet delivery is loaded. A test asserts that Phase 3 code opens no Cricsheet path.
11. Any column derived from items 1 to 10.

Outcome columns are kept in a separate column group prefixed `out_` in the exploratory state table so a feature function cannot receive them by accident. Leakage tests (Stage 8): recompute each row's state from a copy of the innings truncated to earlier rows and require equality; mutate later rows or the match result and require unchanged earlier state. Denominator-flag test: mutate `extras_type` and `is_legal_ball` of row k (for example wide to None) and require that every state, par and rank column of row k is identical (only rows after k may change, through `B`, `R` and `W`).

Selection rule for outcome-conditioned flags. Pressure membership of a delivery is decided from the pre-delivery state only. `counts_as_ball_faced` and `legal_inc` of row k are applied afterwards, and only to choose the denominator of a rate: batter outcomes per ball faced use `counts_as_ball_faced`; bowler outcomes per legal ball use `legal_inc`. Bowler pressure membership is evaluated on ALL deliveries by the bowler in the state, including wide, Overstep and other, so a bowler's wides and no-balls are not removed from his pressure opportunities by their own outcome. Extras rates (wide, Overstep, other, charged runs) are computed over all his pressure deliveries.

## 6. Par-curve leakage control

Innings 1 has no target. A defensible context uses expectations estimated from OTHER matches. Two variants are built and both are reported in Stage 3.

**Variant LOMO (leave-one-match-out cross-fitting, official data only).** For a row in match M, innings 1, format c, legal balls before b, wickets remaining w:

- `par_runs(c, b)` = mean team runs `R` at EXACTLY b legal balls bowled (`B = b`) over source innings of format c, with all rows of match M removed: (cell sum minus M's contribution) / (cell count minus M's count). One observation per source innings per b. A source innings that ended before b legal balls (all out) contributes its FINAL total at b (carry-forward), because the team's score does not change after the innings ends. Source innings are complete by rule 3, so the only early endings are all-out innings (81 innings 1 end all out before their limit; section 2). The drop variant (an early-ended innings contributes nothing at b > its length) is computed as a named sensitivity `par_drop_early_ended` and reported beside the primary; it has a survivorship bias towards teams that kept wickets in hand.
- `exp_remaining(c, Brem, Wrem)` is defined on BINNED cells, never on exact `(Brem, Wrem)` pairs (with 793 source innings an innings visits only its own path, so exact cells are almost all below `min_cell_innings`). Cell = competition type c x `Brem` bin x global `Wrem` bin (section 8 `wickets_bins`). `Brem` bin index = `(Brem - 1) // exp_brem_bin` with `exp_brem_bin` = 6 (so `Brem` 1 to 6 is bin 0, the last over). Value = mean runs scored from this state to the end of the innings among source innings that pass through the binned cell, with match M removed. Observation unit: each source innings contributes ONE observation per binned cell, taken from its FIRST row in that bin: `final_total - R` at that row. Innings is the clustering unit, so the repeated rows of one innings in the same binned cell are never counted separately. Exact `(Brem, Wrem)` cells are a diagnostic only: Stage 3 reports how many exact cells reach the threshold, and they are never used for a value.
- `exp_remaining` fallback chain (ordered, same chain for LOMO and strictly-prior). Level E0: the binned cell, used when it has at least `min_cell_innings` distinct source innings (LOMO, after removing M) or `min_prior_innings` (strictly prior), and then shrunk towards its E1 parent with `shrink_to_parent` (rule 6). Level E1: the `Brem` bin only (all `Wrem`), used entire when E0 is below the threshold and E1 reaches it. Level E2: `competition_type` pooled over all states, used entire when E1 is also below the threshold. If E2 is below the threshold (possible only in the strictly-prior variant in early 2022) the value is NULL and the row is counted as `exp_unavailable`. Every row records `exp_cell_level_used` in {`E0_BINNED`, `E1_BREM_BIN`, `E2_COMP_TYPE`, `NONE`} and the strictly-prior variant records its own `exp_cell_level_used_prior`. The `Wrem` partition is `FULL_SAMPLE` (section 8) even in the strictly-prior variant, so that variant is future-clean in its cell means but not in its bin edges; a predictive claim re-derives the partition from matches before the cut date.
- Exact ball versus bin: `par_runs` and `par_deviation` are read at the exact `B_k`. `par_ball_bin` (section 8) is used only for smoothing in the sparse-cell fallback and for reporting tables, never to replace the exact-ball value in the primary variant.
- `par_deviation_k = R_k - par_runs(c, B_k)`.
- `projected_total_gap_k = R_k + exp_remaining - par_total(c)`, where `par_total(c)` is the LOMO mean innings-1 total.

**Variant STRICTLY_PRIOR.** Same quantities, built only from source innings of matches with `match_date` strictly before the row's `match_date` (same-day matches excluded; the data carry no reliable time of day, RULE_MIDNIGHT_TIMES). A cell needs at least `min_prior_innings` prior source innings (section 8) or the value is NULL and the row is counted as `par_unavailable`. Early-window rows (2022) will have more NULLs; this is reported, never filled. Stage 3 MUST compute this variant for innings-1 par and report how the innings-1 pressure population (deliveries, matches, innings) differs from the LOMO population under each candidate. It is not deferred to the validation plan.

Rules fixed by this specification:

1. Own match is removed completely, including its innings 2 and result. A test changes any value in match M (final total, result) and requires unchanged par and state for M.
2. Source innings come from innings 1 only. Innings 2 is censored by the target (the chase stops when the target is reached) and would bias remaining-run expectations downward. Chase context (`req_to_exp`) also uses innings-1 expectations.
3. Source innings must be COMPLETE, defined from the data as `W == 10` or `legal_ball_count == L`, and must have `L = 120`. Anything else (421 L=120 innings end before 120 legal balls with fewer than 10 wickets, of which 19 are innings 1 and 402 are chases that ended before 120 legal balls without all out; the data do not record why) is non-complete and excluded from par. There is no rain field in the data, so no stopped-by-rain detection is attempted beyond this rule.
4. The completeness rule uses the final outcome of the SOURCE innings, so it is applied to other matches only. The row's own match is excluded regardless of its completeness.
5. DLS-limited innings (`L` < 120) are not source innings. They still receive par context from the 120-ball cells, flagged `par_not_comparable`.
6. Sparse cells fall back to a coarser parent cell (section 8, `min_cell_innings`; for `exp_remaining` the chain above). A cell below the threshold takes its parent value entirely; a cell at or above it is shrunk towards its parent with the NEW helper `shrink_to_parent(n_eff, cell_mean, parent_mean, k)` in `app/analytics/shrinkage.py`, result `(n_eff * cell_mean + k * parent_mean) / (n_eff + k)`. `k` comes from a second new helper `k_from_children(children, tau2_floor)` and is defined as follows. `sigma2_within` = pooled per-delivery variance of the parent's children (sum of within-child sums of squares over total deliveries minus number of children). `between_moment` = variance of the child means minus the mean of `sigma2_within / n_eff_child` (method of moments). `tau2 = max(between_moment, tau2_floor_abs)` where `tau2_floor_abs = tau2_floor * sigma2_within` and `tau2_floor` is the section 8 config value (ARBITRARY_PLACEHOLDER, scale-free so one value serves every outcome stream; sensitivity 10x each way). `k = sigma2_within / tau2`, so `k` is finite and at most `1 / tau2_floor`; a zero or negative moment estimate therefore gives the largest `k` (strongest shrinkage), never `k = 0`. When `tau2` equals the floor the parent is reported with `shrinkage_floor_hit = true`. `n_eff` is `n_eff_kish` of the cell (innings clustering) in `shrink_to_parent` and in `shrink_player`. Binary outcomes (boundary, dot, dismissal, wicket) never use `shrink_to_parent`; they use `beta_binomial_shrink`, whose counts are scaled by the design effect `n_eff / n` so the same effective sample size drives both helpers. The existing `eb_shrink` shrinks each entity towards the pooled mean of its own input array and takes no parent mean, so it is NOT used for parent-cell shrinkage. Unit tests: result equals the parent mean at n_eff = 0, equals the cell mean as n_eff grows, is monotone between the two; a parent whose children have zero between-child variance gives `k = 1 / tau2_floor`, a finite result and `shrinkage_floor_hit = true`; a negative moment estimate behaves the same.
7. No venue, season or team adjustment in v1. Run-environment adjustments are a LOMO sensitivity (open decision 10).

Source-innings counts (verified): 793 complete 120-ball innings 1 (IPL 358, T20I 435) in the LOMO variant.

Stated limits of LOMO: it uses matches played after the row's match date. That is acceptable for describing the historical distribution of pressure states. It is NOT acceptable for validated predictive claims; those require the strictly-prior variant and the temporal split in section 14. Leave-one-out means are slightly anti-correlated with the removed observation; the Stage 4 checks report its size.

## 7. Pressure definitions by context

Common to every context: only innings 1 and 2 enter regulation-pressure metrics; innings 3 and 4 are excluded by RULE_INNINGS_3_4 with reason codes `CONFIRMED_SUPER_OVER_BY_CRICSHEET` (34429, 45512, 50359) and `UNVERIFIED_INNINGS_ROLE` (40725, 48027, 48029). Phase labels use the legal over index (section 8). Signals are numeric. Cutoffs are not defined here.

### 7.1 First innings (no target)

| Item | Specification |
|---|---|
| State variables | `R_k`, `W_k`, `Wrem_k`, `B_k`, `Brem_k`, `CRR_k`, phase, `knock_out`, format, `par_runs`, `exp_remaining` (both par variants) |
| Pressure signals | `par_deviation` (negative = behind par); `projected_total_gap`; `Wrem`; `Brem`; `resource_ratio = Brem * Wrem / (L * 10)` |
| Batting signal (higher = more pressure) | `s_bat1 = -par_deviation` |
| Absolute | Raw `par_deviation`, `projected_total_gap`, `resource_ratio` against population quantiles |
| Relative | `rank_pct(s_bat1 ; cell)` with cell `format x innings 1 x phase x Wrem bin` |
| Caveat | Pressure in innings 1 is weak: no explicit target. All of it is inferred from par and labelled "par-relative", never "required-rate pressure". |

### 7.2 Chasing innings (innings 2)

| Item | Specification |
|---|---|
| Target | `T = revised_target` when not null, else innings-1 `source_total_runs + 1`. A match with innings 2 rows but no innings 1 rows gets `target_source = NO_INNINGS_1_TARGET` and no target (none occurs in the data). |
| Target basis | `target_basis_unverified` (section 3) marks innings 2 whose target rests on an incomplete innings 1 with no revised field. The PRIMARY chase population excludes these innings. A named sensitivity variant includes them. The number of excluded innings and rows is reported. `dls_suspected_unrecorded` (the four `result`-text matches) stays report-only and is never a state column or a primary filter. |
| State variables | `R_k`, `W_k`, `Wrem_k`, `B_k`, `Brem_k`, `Req_k`, `CRR_k`, `RRR_k`, `gap_k`, phase, `knock_out`, format |
| Pressure signals | `RRR`; `Req`; `Brem`; `Wrem`; `gap = RRR - CRR`; `req_to_exp = Req / exp_remaining` (innings-1 expectation at the same `Brem`, `Wrem`; both par variants); `resource_ratio`; `knock_out` |
| Batting signal (higher = more pressure) | `s_bat2 = RRR` |
| Closeness | `req_to_exp` near 1 means a balanced chase. Context only, not a result prediction. |
| Absolute / relative | Absolute: raw signal. Relative: `rank_pct(s_bat2 ; cell)` with cell `format x chase x phase x Wrem bin`. |
| Edge cases | `Brem = 0` or `Req <= 0`: `RRR` NULL or non-pressure and the row is flagged; `CRR` NULL on ball 1. |

### 7.3 Batting pressure

Pressure faced by the batter on strike, from the batting team's state before the delivery.

| Item | Specification |
|---|---|
| Opportunity unit | One delivery whose pre-delivery state satisfies a candidate pressure definition. For rates per ball faced the denominator keeps rows with `counts_as_ball_faced` (an outcome-conditioned denominator flag, section 5.3); it never selects states |
| Signals | Chase `s_bat2` (and `gap`, `req_to_exp`, `Wrem`, `Brem`); innings 1 `s_bat1` (and `Wrem`, `Brem`). Before-state: `batter_balls_faced_before`, `batter_runs_before`. |
| Batting relative pressure | `bat_pressure_rel = rank_pct(s_bat ; cell)` where `s_bat` is `s_bat1` or `s_bat2` by innings |
| Outcomes compared with expectation | Runs off the bat per ball faced, boundary flag, dot flag, dismissal flag on the delivery |
| Sample counts reported | Pressure balls faced, distinct matches, distinct innings, `n_eff_kish` (Phase 2.5 `n_eff` formula) |
| Restrictions | Section 12 |

### 7.4 Bowling pressure

Pressure on the bowler, defined from the batting side's state before the delivery. Two sign conventions are defined as formulas, reported separately and never averaged (open decision 2). Both are oriented so a higher value is more pressure on the bowler.

| Convention | Formula | Reading |
|---|---|---|
| A, mirror | `bowl_rel_A = 1 - bat_pressure_rel` (equal to `rank_pct(-s_bat ; cell)` under mid-rank ties) | The bowler is under pressure when the batting side is comfortable by the same relative measure used for batting pressure |
| B, projected surplus | Chase: `bowl_signal_B = projected_surplus = (CRR - RRR) * Brem / 6` (runs by which the batting side is on course to exceed the target at its current rate; NULL when `B_k = 0`). Innings 1: `bowl_signal_B = par_deviation`. Relative form: `bowl_rel_B = rank_pct(bowl_signal_B ; cell)`. | The bowler is under pressure when the batting side is on course to beat the target or par |

Convention B uses `CRR_k`, which is volatile at small `B_k` (one boundary on ball 2 dominates it). The value is NULL only at `B_k = 0`. Rows with `B_k < bowl_B_early_balls` (12, the first two overs; section 8) are kept but reported in a separate column (`bowl_B_early_flag`), as `rrr_min_brem_report` does for RRR, and every Stage 3 distribution and candidate population for convention B is shown with and without them.

In innings 1, A and B coincide as rankings by construction (`s_bat1 = -par_deviation`); a test checks this. They differ in chases because A is driven by `RRR` alone and B by the gap between current and required rate scaled by balls left.

| Item | Specification |
|---|---|
| Opportunity unit | Pressure membership is evaluated on ALL deliveries by the bowler in a state that satisfies a candidate bowling-pressure definition under convention A or B, including wide, Overstep and other rows. The legal filter (`legal_inc = 1`, an outcome-conditioned denominator flag) applies only to the denominator of per-legal-ball rates. Wides, Overstep and other rows are not legal; they count as pressure opportunities and as charged-runs and extras events. |
| Bowler before-state | Legal balls, runs and wickets before in the innings; overs completed before |
| Outcomes compared with expectation | Charged runs per legal ball (`BOWLER_SQL` definition), wicket credited to the bowler (Caught, Bowled, LBW, Stump, Hit Wicket), dot, boundary |
| Wicket credit | RunOut, Retire Out and both Obstructing spellings are team wickets, not bowler wickets |
| Sample counts reported | Pressure legal balls, distinct matches, distinct spells (bowler-innings), `n_eff_kish` |

### 7.5 Death overs

| Item | Specification |
|---|---|
| Definition (L = 120) | Legal over index 16 to 20, i.e. `B_k >= 90` and `Brem_k > 0`. Verified: 44,452 regulation rows (22.1%). |
| Definition (L < 120) | Ball-based; see 7.6 and the boundary table |
| Role | A phase (context) label, not a pressure label. A death-over delivery is not automatically high pressure. Death enters the baseline as a stratification variable, so death-over strike rates are never compared raw with ordinary-over strike rates. |
| Signals within death | The same chase and par signals. `Brem` is small by construction, so `RRR` is volatile. `RRR` is reported uncapped and capped (cap rule in section 8) and always alongside `Brem`; a cap is never applied silently. |
| Absolute / relative | Relative pressure within death uses the death cell, so a death-over chase is compared with other death-over chases. |

### 7.6 DLS and revised-overs matches

Per-innings definitions (these fix the row-level meaning):

- `dls_flag(match, innings)`: innings 1 = `first_inn_revised_overs` not null. Innings 2 = `second_inn_revised_overs` not null OR `revised_target` not null.
- `dls_match_flag`: any of the three revised fields not null (34 matches).
- `innings_limit_unstated`: innings 2 of a match with `first_inn_revised_overs` not null, `second_inn_revised_overs` null and `revised_target` null while innings 2 rows exist (matches 16753, 19959). `L` is recorded as `CARRIED_FROM_FIRST_INNINGS_UNVERIFIED`.
- `dls_state_reliable(match, innings)`: for `dls_flag` true, = own-innings revised value not null AND (innings 1, or `revised_target` not null). For `innings_limit_unstated` = false. For `dls_flag` false = NULL (not applicable; no reconstruction needed). Reliable means the fields exist; it does not remove the interruption-timing hindsight, which is carried separately by `limit_applied_from_start_assumed`.
- `dls_exclude_primary` = `dls_flag` OR `innings_limit_unstated`. Primary populations drop these innings. Innings 1 of a match whose revision appears only in innings 2 (9 matches) has `dls_flag` false and a normal limit, so it stays in the primary population.

Truth table of the 34 revised matches (verified; the Stage 2 build must reproduce it):

| Innings-1 limit stated | Innings-2 limit stated | Revised target stated | Innings 2 exists | Matches | Result status | Notes |
|---|---|---|---|---|---|---|
| yes | no | no | no | 7 | 1 ABANDONED, 6 NO_RESULT | innings-1 rows only |
| yes | yes | no | no | 2 | NO_RESULT | limit stated for a chase that never started |
| yes | no | no | yes | 2 | COMPLETED | 16753, 19959: `innings_limit_unstated` |
| yes | yes | yes | yes | 14 | 13 COMPLETED, 1 NO_RESULT (17765) | target = innings 1 + 1 in 8, differs in 6 |
| no | yes | yes | yes | 9 | COMPLETED | innings 1 unrevised; target differs from innings 1 + 1 in all 9 |
| | | | | 34 | | |

Per-innings counts from this table: `dls_flag` true in 25 innings-1 and 23 innings-2 innings (48 innings); `innings_limit_unstated` 2 innings; `dls_exclude_primary` 50 innings; `dls_state_reliable` true in 48 innings, false in 2.

| Item | Specification |
|---|---|
| Limit `L` | Own innings' revised value in balls when not null, else 120 (units verified as balls). |
| Target | `revised_target` for innings 2 (RULE_DLS_TARGETS). Cross-check against innings-1 total + 1 and report both (8 equal, 15 differ). |
| Interruption timing | Not in the data. The revision is applied from ball 1, flagged `limit_applied_from_start_assumed`. Rows before the real interruption are hindsight-contaminated. |
| DLS resource percentage | NOT reconstructed. The DLS resource table is not invented. `resource_status = 'NOT_RECONSTRUCTED'` on every `dls_flag` row. `resource_ratio` is a simple proxy, not a DLS resource. |
| Phases (L < 120) | BALL-BASED, not over-based. Integer arithmetic only: `pp_end = (3 * L) // 10` legal balls (floor of 0.30 L) and `death_start = -((-3 * L) // 4)` legal balls (integer ceiling of 0.75 L). Powerplay if `B_k < pp_end`, death if `B_k >= death_start`, middle otherwise. No floating-point factor is used. For L = 120 these are 36 and 90 (overs 7 and 16). A Stage 8 test asserts both formulas reproduce the 14-row table below exactly. For L < 120 the boundaries fall inside an over in most cases, so the `over_k` column is not used for phase there. `phase_rule` records `FULL_120` or `PROPORTIONAL_DLS`. The factors are a documented proxy for the ICC reduced-overs allocation (OPEN DECISION 4). |
| Pressure populations | Primary excludes `dls_exclude_primary` innings. A sensitivity variant adds `dls_state_reliable = true` innings. `innings_limit_unstated` innings appear in neither and are counted. |
| Not-chased matches | 9 matches (NO_RESULT or ABANDONED) have innings-1 rows only. RULE_NO_RESULT_MATCHES affects outcome and win-probability metrics only, not pre-delivery state. |
| DLS recorded only in `result` text | 20182, 23674, 24822, 28334: `result` says DLS or D/L, no revised field recorded. Primary `dls_flag` follows the revised fields only (RULE_DLS_TARGETS). Because `result` is post-match information, these four matches are NOT flagged inside the state; they are listed as `dls_suspected_unrecorded` in the Stage 7 report and tested as a sensitivity exclusion (OPEN DECISION 13). |
| Incomplete innings 1, no revised field | An innings 1 with `W < 10`, legal balls `< L1` and no revised field gives an innings-2 target of unverified validity. Innings 2 of such a match gets `target_basis_unverified = true`, is excluded from the primary chase population, and is included in a named sensitivity variant. Matches where only the `result` text mentions DLS (the four above) are not detected by this rule unless their innings 1 is incomplete (23674 is); the flag uses innings-1 data only. |
| Counts to reconcile | "34" union; "25" and "25" per column; "23" revised targets. All reported by Stage 2. |

Phase boundaries per distinct `L` (ball-based; regulation innings count per `L`):

| L | pp_end (balls) | death_start (balls) | Innings with this L |
|---|---|---|---|
| 30 | 9 | 23 | 4 |
| 42 | 12 | 32 | 3 |
| 48 | 14 | 36 | 4 |
| 54 | 16 | 41 | 4 |
| 60 | 18 | 45 | 3 |
| 66 | 19 | 50 | 4 |
| 72 | 21 | 54 | 2 |
| 78 | 23 | 59 | 2 |
| 84 | 25 | 63 | 4 |
| 90 | 27 | 68 | 7 |
| 102 | 30 | 77 | 4 |
| 108 | 32 | 81 | 2 |
| 114 | 34 | 86 | 5 |
| 120 | 36 | 90 | 1,664 |

## 8. Innings phase and configuration parameters

| Phase | Full innings (L = 120) | Legal over index | Balls before delivery |
|---|---|---|---|
| Powerplay | overs 1 to 6 | 1 to 6 | 0 to 35 |
| Middle | overs 7 to 15 | 7 to 15 | 36 to 89 |
| Death | overs 16 to 20 | 16 to 20 | 90 to 119 |

Phases are labels, not pressure thresholds. Every configuration value below lives in `config/pressure_rules_v1.json` (created in Stage 2). Basis classes: `EXISTING_RULE` (taken from an existing project rule or config file), `EXTERNAL_CONVENTION` (a convention from cricket practice, not defined in this project), `DATA_DERIVED` (a rule computed from the data), `ARBITRARY_PLACEHOLDER` (a stated value with the sensitivity run that tests it). Nothing here is tuned to improve a result.

**Wickets-bin merge algorithm (`wickets_bins`).** The domain is `Wrem` = 1 to 10. `Wrem` = 0 is not a pre-delivery state, because the tenth wicket ends the innings; no row has it. The partition is ONE global partition shared by all cells.

1. Start with ten singleton bins: {10}, {9}, ..., {1}.
2. For every bin compute `m(bin)` = the minimum, over all cells `competition_type x innings role x phase` (IPL and T20I, innings 1 and chase, powerplay, middle and death; 12 cells), of the number of DISTINCT innings that have at least one row with `Wrem` in the bin in that cell. Cells that are structurally empty for every `Wrem` (none expected) are skipped and listed.
3. If the minimum of `m(bin)` over all bins is at least `min_cell_innings`, stop.
4. Otherwise, among all pairs of ADJACENT bins, find the pair with the smallest combined `m` (the `m` of the merged bin). Ties are broken by merging the pair nearer to `Wrem` = 1. Merge that pair and go back to step 2.
5. Output the final partition and, for each merge performed, the pair merged, the cell and count that triggered it, and the combined `m`. If a single bin 1-10 is reached and `m` is still below `min_cell_innings`, stop, record `wickets_bins_failed = true` and fall back to no wickets dimension (cell level L1).

The merge reads distinct-innings counts across all matches, so the partition is `FULL_SAMPLE` (section 5.3), descriptive only. Stage 3 reports the partition and the merge log.

| Parameter | Initial value | Basis | Justification and sensitivity |
|---|---|---|---|
| `phase_bounds_L120` | overs 1-6 / 7-15 / 16-20 | EXTERNAL_CONVENTION | Common T20 powerplay and death convention. No project rule defines it (no phase rule exists in `app/analytics`, `app/core/config.py` or `config/*.json`). Section 2 verifies only that overs run 1 to 20, not that 16 to 20 is the right death definition. Sensitivity: death from over 17 (`B_k >= 96`) and powerplay overs 1-5 are reported as alternative phase definitions in Stage 3 |
| `phase_fractions` (L < 120) | powerplay end `(3 * L) // 10`; death start `-((-3 * L) // 4)` (integer arithmetic) | ARBITRARY_PLACEHOLDER | Equal to 36 and 90 at L = 120. Sensitivity: exclude the 48 shortened innings from phase-dependent metrics and report the change |
| `min_cell_innings` | 30 distinct innings | ARBITRARY_PLACEHOLDER | Numerically equal to Phase 2.5 `pool_min_absolute` (30), applied to innings. Sensitivity: 15, 30, 60; report cell fallback counts and population changes |
| `min_prior_innings` | 30 prior source innings per cell | ARBITRARY_PLACEHOLDER | Same value as `min_cell_innings`. Sensitivity: 15, 30, 60 |
| `par_ball_bin` | 6 legal balls (one over) | DATA_DERIVED | Natural unit of the over index; innings have 1 to 120 legal balls. Sensitivity: 3 and 12 |
| `exp_brem_bin` | 6 legal balls; bin index `(Brem - 1) // 6`; cell = `Brem` bin x global `Wrem` bin | DATA_DERIVED | Same unit as `par_ball_bin`. Sensitivity: 3 and 12 |
| `exp_cell_fallback_chain` | E0 binned cell (n >= threshold) -> E1 `Brem` bin only -> E2 `competition_type` pooled -> NULL | DATA_DERIVED | Order fixed by section 6; threshold is `min_cell_innings` (LOMO) or `min_prior_innings` (strictly prior). Sensitivity: thresholds 15 and 60 via those two parameters; report `exp_cell_level_used` counts |
| `wickets_bins` | Deterministic global merge, algorithm below | DATA_DERIVED | The coarsest-needed partition is chosen by the data, not by hand. Sensitivity: 4 bins (10-8, 7-5, 4-3, 2-1) |
| `rrr_cap` | NONE in primary. Reported variant: cap at the observed p99 of chase `RRR` over regulation chase rows (computed in Stage 3) | DATA_DERIVED | Never applied silently. Uncapped and capped statistics are reported side by side |
| `rrr_min_brem_report` | Rows with `Brem` < 6 reported as a separate column | DATA_DERIVED | One over; `RRR` is volatile |
| `quantile_grid` | ONE grid: 0.50, 0.60, 0.75, 0.80, 0.85, 0.90, 0.95 | ARBITRARY_PLACEHOLDER | A search grid for candidate generation, not a selection. The same grid is used for every signal and every candidate family (section 11); there is no second "extra" grid. The denser points show how smoothly populations change |
| `par_source_rule` | `L = 120` and (`W == 10` or legal balls `== L`), other matches only | DATA_DERIVED | Section 6 rule 3 |
| `bootstrap` | seed 20260512 (Phase 2.5 seed); 1,000 resamples for eligibility (Phase 2.5 `n_boot`); 500 for baseline | EXISTING_RULE (seed, 1,000); ARBITRARY_PLACEHOLDER (500) | Stage 4 sensitivity: 1,000 |
| `n_eff` | `n_eff_kish` and `n_eff_shrink` from `app/analytics/confidence_engine.py` and `app/analytics/shrinkage.py` | EXISTING_RULE | Clustering unit: innings |
| `bowl_B_early_balls` | 12 legal balls (first two overs) | ARBITRARY_PLACEHOLDER | Rows with `B_k` below it get `bowl_B_early_flag` (section 7.4). Sensitivity: 6 and 18 |
| `break_reproducibility_tol` | 0.05 in quantile terms | ARBITRARY_PLACEHOLDER | Tolerance for a data-derived break to count as reproduced across IPL, T20I, LOMO and strictly-prior (section 11c). Sensitivity: 0.025 and 0.10 |
| `zero_inflation_share` | 0.05 | ARBITRARY_PLACEHOLDER | Share of rows at a signal's minimum above which the value is reported as a boundary (section 11c). Sensitivity: 0.02 and 0.10 |
| `knee_rule` | Largest perpendicular distance to the chord between first and last points of the cumulative curve "share of rows with signal >= x"; both axes min-max normalised to [0, 1] | ARBITRARY_PLACEHOLDER | A method choice with no project precedent. Sensitivity: normalise the x axis by quantile rank instead of signal value and report whether the same break is found |
| `wrem_low_quantile` | `1 - q` quantile of `Wrem` in the context, lower-quantile convention (conjunctions of section 11b) | ARBITRARY_PLACEHOLDER | Tied to the same `q` as the paired condition. Sensitivity: "Wrem low" = the lowest global `wickets_bins` bin, and the `1 - q` rule on the strictly-prior population |
| `quantile_grid_by_family` | Family (a): all seven grid points. Family (b): all seven points, the same `q` in both conditions. Family (c): no grid (data-derived); breaks are reported as quantile positions | ARBITRARY_PLACEHOLDER | Sub-selection of the 0.50 to 0.95 grid per family. Sensitivity: coarse subset 0.50, 0.75, 0.90, 0.95 for (a) and (b); extended top 0.975 and 0.99 added for (a) |
| `tau2_floor` | 0.01, as a fraction of `sigma2_within` (`tau2 = max(between_moment, tau2_floor * sigma2_within)`; `k` at most 100) | ARBITRARY_PLACEHOLDER | Floor for the between-child variance in `shrink_to_parent` (section 6 rule 6). Sensitivity: 0.001 and 0.1 (10x each way); report `shrinkage_floor_hit` counts |

Configuration parity. `config/pressure_rules_v1.json` holds a `parameters` object with exactly one entry per row of the table above, keyed by the parameter name in the first column, each entry carrying `value`, `basis` and `sensitivity`; metadata (`config_version`, `state_version`) sits outside `parameters`. A Stage 8 test parses the first column of this table and asserts the set equals the key set of `parameters` (no row without a key, no key without a row), and that each `basis` is one of the four classes.

## 9. Formulae summary

```
legal_inc      = 1 if is_legal_ball and extras_type != 'Penalty' else 0
B_k            = sum(legal_inc over rows before k)
R_k            = sum(batter_runs + extras_primary_runs + extras_secondary_runs over rows before k)
W_k            = count(is_wicket over rows before k);   Wrem_k = 10 - W_k
W_alt_k        = count(is_wicket or dismissed_player_id not null over rows before k)
Brem_k         = L - B_k
CRR_k          = R_k / B_k * 6            (NULL when B_k = 0)
T              = revised_target  or  innings1_source_total_runs + 1     (innings 2 only)
Req_k          = T - R_k
RRR_k          = Req_k / Brem_k * 6       (NULL when Brem_k = 0 or no T)
gap_k          = RRR_k - CRR_k
projected_surplus_k = (CRR_k - RRR_k) * Brem_k / 6        (chase; NULL when B_k = 0)
resource_ratio = Brem_k * Wrem_k / (L * 10)
par_dev_k      = R_k - par_runs(c, B_k)            [LOMO or STRICTLY_PRIOR]
proj_gap_k     = R_k + exp_remaining(c, Brem_k, Wrem_k) - par_total(c)
req_to_exp_k   = Req_k / exp_remaining(c, Brem_bin, Wrem_bin)   (NULL when exp_remaining is NULL or <= 0)
s_bat          = -par_dev_k (innings 1)  |  RRR_k (innings 2)
bat_pressure_rel = rank_pct(s_bat ; cell(c, role, phase, Wrem bin), match M)        (section 4)
bowl_rel_A     = 1 - bat_pressure_rel
bowl_rel_B     = rank_pct(projected_surplus_k (innings 2) | par_dev_k (innings 1) ; cell, M)
```

## 10. Extras and unresolved categories

- `extras_type` is the literal string 'None' when no extra. It is not NULL and not zero.
- `other` behaves as a no-ball (not legal, ball faced). The label is UNVERIFIED (RULE_EXTRAS_OTHER, REPORT_WITH_SENSITIVITY). The state engine keeps `extras_label_unverified` as a flag and never merges `other` into Overstep. Results are reported with and without the 264 rows.
- `Penalty` (1 row, match 16753 innings 2 ball 34) is UNVERIFIED and contributes 0 legal balls (RULE_EXTRAS_PENALTY).
- `extras_secondary_runs` is not interpreted (RULE_EXTRAS_SECONDARY). Only the primary plus secondary sum enters `R_k`.
- 2 rows have `extras_type = 'None'` with nonzero extras runs. They stay in `R_k`, are flagged `extras_runs_with_none_type`, and are never coerced to zero.
- Unknown categories are never replaced by 0 or by a default; they remain separate flags.

## 11. Candidate generation (no choice made)

Candidate thresholds are generated from observed distributions in Stage 3 only:

1. For each signal and context, compute percentiles p5 to p95, histograms, and zero or boundary inflation.
2. Candidate definitions belong to exactly three families. No weighted composite, sum, product or score of several signals is a candidate: any weights would be arbitrary cutoffs by another name.
   - Family (a), single signal at a quantile. One signal `s` and one quantile `q` from the single grid in section 8 (`quantile_grid`). Rule: pressure if `s >= quantile(s, q)` where the quantile is taken over the signal's own context population (absolute view) or the relative percentile `rank_pct >= q` (relative view). Signals allowed: chase `RRR`, `Req`, `gap`, `req_to_exp`, `-resource_ratio`; innings 1 `-par_deviation`, `-projected_total_gap`, `-resource_ratio`; bowling convention B signal.
   - Family (b), conjunction. Logical AND of two family (a) conditions, each at the same grid, no weights. Pairs allowed (fixed list): (`RRR`, `Wrem` low); (`RRR`, `Brem` low); (`req_to_exp`, `Wrem` low); (`-par_deviation`, `Wrem` low); (`-resource_ratio`, phase = death). "Wrem low" means `Wrem` at or below the `wrem_low_quantile` = `1 - q` quantile of `Wrem` in the context (lower-quantile convention for the discrete `Wrem`). Both conditions use the same `q`. Grid use per family is fixed by `quantile_grid_by_family` (section 8).
   - Family (c), data-derived breaks. For each signal the cumulative curve "share of regulation deliveries with signal >= x" is computed. A break is the knee of that curve found by the maximum distance from the chord joining its end points (config `knee_rule`, section 8: the point with the largest perpendicular distance from the straight line between the first and last points of the curve, with both axes min-max normalised to [0, 1]). Also, a zero-inflation break: if more than `zero_inflation_share` (0.05) of rows share the signal's minimum value, that value is reported as a boundary, not as a cutoff. A break is a candidate only if it is reproducible: it must lie in the same region (within `break_reproducibility_tol` = 0.05 in quantile terms) in IPL and T20I separately and in the strictly-prior and LOMO variants. Breaks that do not reproduce are reported and not used.
   For each candidate report deliveries, matches, innings and players selected, for batters and bowlers separately, in IPL and T20I, for LOMO and strictly-prior par, and for both bowling conventions (B with and without `B_k < 12` rows).
3. The fixed list of families and signals above is the whole candidate set. Nothing outside it is a candidate. The grid is a search grid, not a selection.
4. The baseline (Stage 4) does not depend on a candidate pressure definition (section 13). Pressure membership only selects which deliveries are summed.
5. The Stage 5 eligibility experiment, not this document, selects a provisional pressure definition after reading the numbers, and labels it not validated.

## 12. Data-quality restrictions by metric (register v1)

Source: `config/data_quality_restrictions_v1.json` (`global_exclusion: false`). Rows stay in official tables. A rule is a mask, flag or interpretation limit on a derived metric. The 26 rule ids below are exactly the register's; a Stage 8 test asserts the set of rule ids in this table equals the register's set of 26 and that every metric in the register's `metric_vocabulary` appears.

| Metric or feature | Rules that apply | Effect on this framework |
|---|---|---|
| `pressure_state_label` | RULE_INNINGS_3_4 | Innings 3 and 4 get no pressure state label. Reason codes `CONFIRMED_SUPER_OVER_BY_CRICSHEET` (3 matches) or `UNVERIFIED_INNINGS_ROLE` (3 matches). 38 rows. |
| `batter_pressure_sample` | RULE_INNINGS_3_4 | Rows excluded; sensitivity not needed (all six matches excluded either way) |
| `bowler_pressure_sample` | RULE_INNINGS_3_4 | Same |
| `batter_balls_faced` | RULE_INNINGS_3_4, RULE_EXTRAS_OTHER, RULE_EXTRAS_PENALTY | Innings 3/4 and Penalty excluded. `other` rows reported with and without |
| `batter_runs_per_ball`, `batter_strike_rate` | RULE_INNINGS_3_4, RULE_CRICSHEET_TOTALS | Innings 3/4 excluded. The ten disagreeing innings in six matches reported with and without |
| `batter_dismissal_rate` | RULE_INNINGS_3_4, RULE_DISMISSED_NO_FLAG, RULE_WICKET_NO_DISMISSED | 12 rows with `dismissed_player_id` but `is_wicket` false: primary treats `is_wicket` as authoritative, sensitivity counts them. 1 row `is_wicket` true with no dismissed player: excluded from batter dismissal metrics only, still a team wicket and (if credited) a bowler wicket. Retire Out (6 rows) is not a dismissal-skill event. |
| `bowler_legal_balls` | RULE_INNINGS_3_4, RULE_EXTRAS_OTHER, RULE_EXTRAS_PENALTY | Innings 3/4 and Penalty excluded; `other` non-legal in primary, with sensitivity |
| `bowler_economy` | RULE_INNINGS_3_4, RULE_EXTRAS_OTHER, RULE_EXTRAS_PENALTY, RULE_EXTRAS_SECONDARY, RULE_CRICSHEET_TOTALS | Charged runs follow `BOWLER_SQL`; secondary runs not interpreted; ten-innings sensitivity |
| `bowler_wicket_rate` | RULE_INNINGS_3_4, RULE_DISMISSED_NO_FLAG | Credited types only; flag-disagreement rows in sensitivity |
| `wicket_event_label` | RULE_DISMISSED_NO_FLAG, RULE_WICKET_NO_DISMISSED | Wicket label from `is_wicket`; disagreements handled per dismissal metric as above. The STATE effect of the same rows (`W_alt`, section 3) is a separate sensitivity. |
| `innings_total_runs` | RULE_INNINGS_3_4, RULE_EXTRAS_SECONDARY, RULE_CRICSHEET_TOTALS | `source_total_runs` is authoritative (official data); ten innings reported with and without |
| `chase_target_features` | RULE_INNINGS_3_4, RULE_CRICSHEET_TOTALS, RULE_DLS_TARGETS | Revised fields required for DLS matches; ten disagreeing innings are a sensitivity drop (list read from `data_quality_impact_report.json` at key path `issue_register.cricsheet_total_disagreements`, used as a mask only) |
| `win_probability_features` | RULE_INNINGS_3_4, RULE_NO_RESULT_MATCHES, RULE_DLS_TARGETS | Not used in v1 (no outcome labels) |
| `match_outcome_label` | RULE_NO_RESULT_MATCHES, RULE_INFO_RESULT_STATUS | Not used in v1 |
| `extras_type_features` | RULE_EXTRAS_OTHER, RULE_EXTRAS_PENALTY, RULE_EXTRAS_SECONDARY, RULE_INFO_EXTRAS1_COMPARISON | Unverified categories remain separate flags, never coerced. RULE_INFO_EXTRAS1_COMPARISON is documentation of the extras comparison and is DOCUMENT_ONLY. |
| `player_identity_join` | RULE_DUPLICATE_NAMES | Join on `player_id` only. 7 names are shared by two ids; no merge on name. |
| `squad_membership_features` | RULE_XI_DUPLICATES, RULE_NO_XI_MATCHES, RULE_NO_MAPPING_ROW, RULE_STRIKER_NOT_IN_SQUAD, RULE_BOWLER_NOT_IN_SQUAD | Not used. No pressure statistic reads `match_squads`, so duplicated squad records cannot multiply player statistics. Test: pressure samples are identical with and without a join to `match_squads`. |
| `team_composition_features` | RULE_XI_DUPLICATES, RULE_NO_XI_MATCHES, RULE_XI_COUNT | Not used |
| `batting_order_features` | RULE_XI_DUPLICATES | Not used |
| `delivery_timestamp_features` | RULE_UTC_SUFFIX, RULE_MIDNIGHT_TIMES | Not used |
| `player_match_of_match_label` | RULE_MOM_SENTINEL | Not used |
| `format_assignment` | RULE_INFO_COMP_TYPE, RULE_INFO_IPL_FORMAT | OTHER_T20 (30 matches) documented and excluded from IPL and T20I scores |
| `innings_order_features` | RULE_FIRST_INNINGS_TEAM | Documented only |
| `match_coverage_denominators` | RULE_INFO_NO_DELIVERY_MATCHES | Documented only |
| `cricsheet_validation_coverage` | RULE_UNLINKABLE_MATCHES | Validation only, DOCUMENT_ONLY. Not used in any Phase 3 metric. |

The applier REUSES the existing loader in `app/validation/restrictions.py` (`load_restrictions`, `validate_restrictions`, `restrictions_for_metric`, `rule_by_id`) and adds only the row-mask implementation per rule; it does not re-parse the register.

Applier requirements (Stage 7): per metric, determine applicable rules; produce row masks and flags; produce primary and sensitivity variants; write an exclusion ledger per metric and rule (rows, matches, players, reason codes). The register's `row_filter` strings are descriptive text, so each rule needs an explicit implementation entry (DOCUMENT_ONLY rules recorded as such). Original official records are never altered.

## 13. Model options (design only, nothing trained)

Stage 4 uses a transparent stratified empirical-Bayes baseline. Cells are `format x innings role x phase x wickets-remaining bin` (no pressure band; the reference baseline is context-only, so it does not depend on any candidate pressure definition). A sensitivity baseline is rebuilt per candidate pressure definition with cell membership (in candidate pressure set or not); the number of baselines equals the number of candidate definitions listed in Stage 3. Regularised logistic regression and gradient boosting for expected runs, wicket, dot and boundary probabilities are design options. They are not used now because they add tuning freedom before the pressure definition is approved, and they need the temporal-holdout calibration in section 14 first. Details are in `baseline_methodology_v1.md`.

## 14. Validation plan (for approval before any scoring)

None of this is run in Phase 3 preparation except where Stage 3 to 6 say so.

| Check | Method |
|---|---|
| No leakage | Truncation and mutation tests (Stage 8). Any failure blocks the stage. |
| Strictly-prior par | Computed in Stage 3 (section 6) and compared with LOMO; used for any predictive claim |
| Temporal split | Fit par curves and baselines on matches before a cut date (for example 2022 to 2024), evaluate on later matches |
| Baseline variants | Every baseline result is produced in four variants and reported together: `full_sample` (B0, descriptive), `leave_player_out`, `leave_match_out` (always reported as a named sensitivity next to leave-player-out), and `strictly_prior` (the only variant allowed for predictive claims). The player EB prior is `FULL_SAMPLE` and descriptive (section 5.3); a predictive claim re-estimates it from matches before the cut date |
| Calibration | Expected versus actual outcomes by decile and pressure band on the held-out period. Calibration identity inside training cells is a code-correctness check on RAW cell means only (Stage 4 check a). |
| Ablation | Remove one signal at a time (`RRR`, `Wrem`, `Brem`, par deviation); report change in pressure population and baseline calibration |
| Stability | Bootstrap by match (seeded) for pressure-sample counts, shrunk actual-minus-expected, and rank stability (Top 10 overlap, Spearman) across neighbouring thresholds and candidate definitions |
| Sensitivity | Each DQ rule with and without affected rows. DLS rows in and out. `other` rows in and out. `W_alt` state variant. `min_cell_innings` 15/30/60. |
| Face validity | Aggregate pressure bands compared with simple cricket logic (monotone in `RRR`, `Wrem`, `Brem`), aggregates only |
| Sample sufficiency | Pool-size verdict per format and role (Phase 2.5 rule, configurable). Fewer than ten eligible players is reported, never padded. |
| Format weights | All eight configurations rerun with final pressure-specific thresholds; combined score only where both format scores exist and are eligible; no imputation |

## 15. Limitations

1. Pressure here is a state-based proxy from score, wickets and balls. It omits opposition quality, pitch, weather, dew, boundary-difficulty, remaining batting strength and real DLS resources.
2. Innings-1 pressure is inferred from a par curve and is weaker than chase pressure.
3. LOMO expectations use later matches. They describe history, not prediction. The strictly-prior variant is computed alongside; its early-window rows can be unavailable.
4. Revised overs and targets are final values applied from ball 1. The interruption time is not in the data.
5. DLS resources are not reconstructed. Four matches decided by DLS according to `result` text have no revised field (20182, 23674, 24822, 28334).
6. Phase boundaries for shortened innings are a proportional proxy.
7. The 70:30 weighting, any pressure band and any candidate threshold are provisional.
8. Extras categories `other` and `Penalty`, and the secondary extras split, remain unverified. Results are shown with and without.
9. 12 wicket-flag disagreements and 1 wicket without a dismissed player remain unresolved; both dismissal metrics and the state (`W_alt`) are sensitivity-tested.
10. Cricsheet confirms three Super Over matches and does not verify the other three; innings 3 and 4 are excluded in all six regardless.
11. Official data end in November 2026; nothing later is assumed. Sample sizes per player in pressure situations are small, so shrinkage and uncertainty are required, and conclusions about individuals are not drawn from this preparation.
12. Absolute pressure confounds phase and format; relative pressure depends on cell definitions.
13. Many configuration values are placeholders (section 8); each has a sensitivity run, none has been tuned.

## 16. Open decisions for the user

| # | Decision | Default used for exploration | Alternatives | Effect if changed |
|---|---|---|---|---|
| 1 | Primary pressure view: absolute or relative | Both reported; no primary | Absolute only; relative only | Changes which deliveries count as pressure and every sample size |
| 2 | Bowling pressure convention | A (mirror) and B (projected surplus) reported separately | Pick one | Changes which bowling deliveries are pressure deliveries |
| 3 | Innings-1 par basis for any pressure claim | LOMO and STRICTLY_PRIOR both reported; LOMO descriptive only | Strictly prior only; venue/season-adjusted par; DLS-style resource table | Innings-1 populations and baselines |
| 4 | Phase boundaries for DLS-shortened innings | Proportional, ball-based (0.30 L, 0.75 L) | ICC powerplay table by overs; exclude shortened innings from phase metrics | Death membership in 48 innings |
| 5 | DLS innings in primary pressure populations | Excluded from primary; sensitivity adds reliable-state innings | Include reliable-state; include all | Chase pressure counts in revised matches |
| 6 | Interruption timing | Revision applied from ball 1, flagged | Exclude rows of revised innings entirely | Hindsight in revised rows |
| 7 | `other` extras in primary | Not legal, ball faced, with and without sensitivity | Treat as Overstep; exclude | Ball counts for 264 rows |
| 8 | Wicket-flag disagreements | `is_wicket` authoritative for state and dismissals; `W_alt` and dismissal sensitivities | Use `dismissed_player_id` | 12 rows in dismissal metrics; 739 later state rows |
| 9 | Chase pressure for matches with no stated innings-2 limit (16753, 19959) | Excluded from primary and reported | Use first-innings limit | 2 matches |
| 10 | Venue, season and team run-environment adjustment | Off in primary; LOMO sensitivity only | On in primary | Baseline expectations |
| 11 | Pressure threshold choice | Not chosen; candidates from distributions | User picks a quantile rule | Eligible populations |
| 12 | Predictive validation variant | Temporal split, 2022 to 2024 train, later test | Rolling origin | Validation design |
| 13 | Matches where `result` says DLS but no revised field exists (20182, 23674, 24822, 28334) | Not flagged in state; sensitivity exclusion list only | Flag as DLS in primary (uses post-match text) | 4 matches |
| 14 | Config placeholders in section 8 (`min_cell_innings`, `quantile_grid`, `phase_fractions`, bootstrap 500 and every other ARBITRARY_PLACEHOLDER row) | Initial values with sensitivity runs | User-supplied values | Cell fallbacks and candidate populations |
| 15 | Death-over definition for L = 120 | Overs 16 to 20 (`EXTERNAL_CONVENTION`); death from over 17 reported as sensitivity | Over 17 start; user-supplied phase table | Death membership in 1,664 full-length innings |
| 16 | Par handling of innings that end early | Carry-forward of the final total (section 6); drop variant as sensitivity | Drop; condition on wickets only | Innings-1 par and `exp_remaining` |
| 17 | Season label for T20I | Calendar year of `match_date`, with `competitions.season` kept as `season_source` (section 3) | Use `competitions.season` including split-year labels | Season grouping for 18 split-year T20I matches |
| 18 | Chases whose target rests on an incomplete innings 1 with no revised field (`target_basis_unverified`) | Excluded from the primary chase population; included in a named sensitivity; count reported | Include in primary; also exclude the four `result`-text DLS matches | Chase pressure counts in the affected matches |

## 17. Stop point

This specification, the Stage 2 engine, Stage 3 distributions, the Stage 4 baseline, the Stage 5 eligibility experiment and tests are preparation only. Full pressure scoring, official rankings and ML training require explicit user approval.

## Appendix A. Responses to design review findings

| Finding | Response |
|---|---|
| M1 | Accepted. Availability matrix uses `PARTIAL` plus a `par_basis` column (LOMO or STRICTLY_PRIOR). Strictly-prior variant is required in Stage 3 and its population compared with LOMO (sections 5.3, 6). |
| M2 | Accepted. Added `cricsheet_validation_coverage`, `RULE_INFO_EXTRAS1_COMPARISON` under `extras_type_features`, `RULE_XI_COUNT` under `team_composition_features` only; test that section 12 ids equal the register's 26 (section 12). |
| M3 | Accepted. `W_alt`, `Wrem_alt` and `state_wicket_flag_disagreement` added; 12 innings and 739 later rows quantified; band change reported in Stage 3 (section 3). |
| M4 | Accepted with a correction. The suggested convention B (`-RRR_pct`) is identical to A in chases, so B is defined as projected surplus `(CRR - RRR) * Brem / 6`. A and B coincide in innings 1 by construction (section 7.4). |
| M5 | Accepted. Configuration table with basis class and sensitivity for each parameter (section 8). The quantile grid is the single section 8 `quantile_grid` (0.50, 0.60, 0.75, 0.80, 0.85, 0.90, 0.95), as set in Revision 3 finding 12; the earlier four-point grid (0.50, 0.75, 0.90, 0.95) is superseded and survives only as a named sensitivity subset (`quantile_grid_by_family`). |
| M6 | Accepted. Three separate checks are defined in `baseline_methodology_v1.md` and the design notes; only check (a) can fail the build. |
| M7 | Accepted. Reference baseline is context-only (no pressure band); per-candidate rebuilt baselines are a sensitivity (section 13). |
| M8 | Accepted. Per-innings `dls_flag`, `dls_state_reliable`, `innings_limit_unstated`, `dls_exclude_primary` and the 34-match truth table (section 7.6). |
| M9 | Accepted. Mid-rank percentile, other-match deliveries, direction, parent fallback and innings clustering (section 4). |
| M10 | Accepted. Completeness defined as `W == 10` or legal balls `== L`, applied to other matches only; named rain examples removed (section 6). |
| N1 | Accepted. Causes stated as undetermined; `Req <= 0` is a reported assertion (12 rows in match 48610 observed). |
| N2 | Accepted. 192,445 flagged legal, 192,444 counted (section 2). |
| N3 | Accepted. Phases ball-based for L < 120; boundary table for all 14 distinct `L` (section 7.6). |
| N4 | Accepted in the design notes: vectorised builder; a loop implementation exists only as a test oracle. |
| N5 | Accepted in the design notes: beta-binomial helper is new code in `shrinkage.py` with tests; `n_eff_kish` named as the Phase 2.5 `n_eff` formula. |
| N6 | Accepted. Mask-only statement and no-Cricsheet-path test (section 5.4 item 10); over-index behaviour and the 41509 over documented (section 2). |

### Revision 3 (second design review: 0 HIGH, 6 MEDIUM, 6 NIT)

| Finding | Response |
|---|---|
| 1 MEDIUM | Accepted. Section 5.3 gains `FULL_SAMPLE` rows for absolute cutoffs, `wickets_bins`, `rrr_cap`, baseline cell means, leave-player-out expectations and the player EB prior, plus `leave_match_out` and `strictly_prior` baseline variants. Section 4 states that absolute thresholds are full-sample. Section 14 requires the four baseline variants; design notes D states the EB prior is descriptive. |
| 2 MEDIUM | Accepted. Section 6: exact-ball par, carry-forward of the final total for early-ended source innings, drop variant as sensitivity, one observation per source innings per cell (first row in the cell), bins only for smoothing and reporting. |
| 3 MEDIUM | Accepted. `season_key` removed. `season_label` defined in section 3 (IPL `competitions.season`; T20I and OTHER_T20 calendar year of `match_date`; `season_source` kept). Season values verified (section 2). Open decision 17. |
| 4 MEDIUM | Accepted. New helpers `shrink_to_parent` (and a target-aware player shrink) with unit tests are specified in section 6 rule 6 and design notes D. `eb_shrink` is no longer claimed to do parent shrinkage. Player residuals shrink towards 0 with the target stated explicitly. |
| 5 MEDIUM | Accepted. Section 11 enumerates three families (single quantile, AND conjunction from a fixed pair list, data-derived reproducible breaks). Weighted composites removed. One grid. |
| 6 MEDIUM | Accepted. Section 8 gives a deterministic global merge algorithm over `Wrem` 1 to 10 with a tie rule, a merge log and a failure fallback. `Wrem` 0 removed from the domain; the 4-bin sensitivity is 10-8, 7-5, 4-3, 2-1. |
| 7 NIT | Accepted. `bowl_B_early_flag` for `B_k < 12`; distributions reported with and without (section 7.4). |
| 8 NIT | Accepted. `phase_bounds_L120` relabelled `EXTERNAL_CONVENTION`; death-from-over-17 sensitivity added; open decision 15. |
| 9 NIT | Accepted. Integer formulas `(3 * L) // 10` and `-((-3 * L) // 4)`, checked by hand against all 14 rows (section 7.6), test required. |
| 10 NIT | Accepted. Applier reuses `app/validation/restrictions.py` (section 12, design notes E). |
| 11 NIT | Accepted. Full path `issue_register.cricsheet_total_disagreements` (sections 2, 12). |
| 12 NIT | Accepted. Single quantile grid in section 8; resolved with finding 5. |

### Revision 4 (third design review: 0 HIGH, 6 MEDIUM, 3 NIT)

| Finding | Response |
|---|---|
| 1 MEDIUM | Accepted. Section 5.3 gains matrix rows for `counts_as_ball_faced` and `legal_inc` of row k (Pre-delivery NO, state no, outcome no, role "outcome-conditioned denominator flag"). Section 5.4 states the selection rule: bowler pressure membership is evaluated on all deliveries including wide, Overstep and other, and the legal filter applies only to per-legal-ball denominators. Sections 3, 7.3 and 7.4 restated. Test added: state columns of row k are identical when its `extras_type` or `is_legal_ball` is mutated. |
| 2 MEDIUM | Accepted. `target_basis_unverified` defined in section 3, listed in the matrix, used in 7.2 and 7.6 (primary excludes, sensitivity includes, count reported), counted in section 2 facts, open decision 18. `dls_suspected_unrecorded` stays report-only. Truth-table and unit tests required in Stage 8. |
| 3 MEDIUM | Accepted. Section 6: `exp_remaining` is defined on binned cells (`Brem` bin of 6 x global `Wrem` bin), observation is the first row of the innings in the bin, fallback chain E0 -> E1 -> E2 -> NULL, `exp_cell_level_used` per row, same for the strictly-prior variant; exact cells are a diagnostic. Section 8 rows `exp_brem_bin` and `exp_cell_fallback_chain`. |
| 4 MEDIUM | Accepted. Section 8 gains `bowl_B_early_balls`, `break_reproducibility_tol`, `zero_inflation_share`, `knee_rule`, `wrem_low_quantile`, `quantile_grid_by_family` (and `tau2_floor`, `exp_brem_bin`, `exp_cell_fallback_chain`), each with basis and sensitivity. Sections 7.4 and 11 cite the config names. The parity test (table keys equal `pressure_rules_v1.json` `parameters` keys) is specified after the table; design notes H mirrors the config design. |
| 5 MEDIUM | Accepted. "6 split-year" replaced by 18 (12 + 3 + 2 + 1) in section 2 and design notes F. |
| 6 MEDIUM | Accepted. Section 6 rule 6: `tau2 = max(between_moment, tau2_floor * sigma2_within)`, `k = sigma2_within / tau2`, `sigma2_within` the pooled per-delivery variance of the parent's children, `n = n_eff_kish` in both helpers, `shrinkage_floor_hit` reported, zero-between-variance unit test. One departure from the review wording: `tau2_floor` is stored as a fraction of `sigma2_within` so a single value serves every outcome stream. |
| 7 NIT | Accepted. Appendix A M5 cites the section 8 grid. |
| 8 NIT | Accepted. Section 4 NULL-handling bullet and section 9 `req_to_exp` formula; exclusions counted in the build manifest. |
| 9 NIT | Accepted. Section 6 rule 3 reworded: "402 are chases that ended before 120 legal balls without all out; the data do not record why". |

## 18. Open decisions / residual review findings

Source: design review 2 (final pass, revision 4): 0 HIGH, 4 MEDIUM, 5 NIT. These were not folded into the text above. Each item gives the reviewer's text verbatim and the safest documented handling. Implementation chunks treat them as known caveats.

1. **MEDIUM**
   - Reviewer: Player residuals are shrunk towards 0 although reference baseline B0 has no match-state or pressure term, so the pressure-sample mean residual is non-zero and low-volume players are pulled to the wrong centre (spec 6 rule 6, 13; notes D). Fix: set shrink target to the pooled mean pressure residual of other players (FULL_SAMPLE, descriptive; strictly prior for predictive use), keep 0 as a named sensitivity, add a synthetic test (all residuals +0.2, one-ball player approaches +0.2), and state that per-candidate baselines are the match-state control.
   - Handling: Primary: B0 plus shrink target set to the pooled mean pressure-sample residual of all other players (labelled FULL_SAMPLE, descriptive; strictly prior when used predictively). Target 0 is kept as a named sensitivity. Per-candidate baselines are the match-state control. Required test: all residuals +0.2, a one-ball player's shrunk value approaches +0.2. The Stage 4 build reports the pressure-sample mean residual.

2. **MEDIUM**
   - Reviewer: No rule for choosing the provisional pressure definition (spec 11.5): 'after reading the numbers' allows selection on exploratory scores and ignores multiplicity. Fix: selection may use only population-level quantities (deliveries, matches, innings, n_eff, eligible counts, cross-format and LOMO/prior reproducibility), never player scores or rankings; ties go to the larger population at the same q; ranking stability is reported not used; report total candidates examined.
   - Handling: Selection of the provisional pressure definition uses only population-level quantities (pressure deliveries, matches, innings, n_eff, eligible-player counts, reproducibility across IPL, T20I, LOMO and strictly prior). Player scores and rankings are never used. Ties go to the larger pressure population at the same q. Ranking stability is reported, not used to choose. The report records the total candidates examined and states that the recommendation is one of N.

3. **MEDIUM**
   - Reviewer: Wickets-bin merge step 4 merges the adjacent pair with the smallest combined m anywhere, so non-deficient bins (e.g. {2},{1}) can merge before the deficient bin ({10}); over-merges and is ambiguous (spec 8). Fix: merge the bin with the smallest m with the adjacent bin giving the larger combined m (ties toward Wrem 1), repeat; add a synthetic test where only {10} is deficient and {2},{1} stay separate.
   - Handling: Replace merge step 4: take the bin with the smallest m, merge it with the adjacent bin giving the larger combined m (ties toward Wrem 1), repeat from step 2. Required synthetic test: only {10} deficient, so {2} and {1} stay separate. Until implemented, treat the older rule as superseded.

4. **MEDIUM**
   - Reviewer: dls_state_reliable=true includes revised innings that ended short of the stated limit: 8 of 25 revised innings 1 end below the limit without all out (15410, 15546, 31707, 36208 COMPLETED, 41975, 46311, 46749, 50408), so Brem/RRR would be wrong in the sensitivity variant (spec 7.6, notes A). Fix: add innings_ended_short_of_stated_limit (legal balls < L, W < 10, dls_flag true; for innings 2 only when not completed by reaching the target), set dls_state_reliable=false when true, update the 48/2 counts, add a unit test.
   - Handling: Add innings_ended_short_of_stated_limit (legal balls < L, W < 10, dls_flag true; for innings 2 only when the chase did not end by reaching the target). Set dls_state_reliable = false when it holds. Expect 8 innings 1 (15410, 15546, 31707, 36208, 41975, 46311, 46749, 50408) and recompute innings 2. The 48 reliable-innings count is superseded and must be recomputed. Unit test required. Primary results already exclude DLS-unreliable rows; this only affects the sensitivity variant.

5. **NIT**
   - Reviewer: RRR when Req <= 0 is defined two ways: spec 3 and 9 say NULL only when Brem=0 or no target; spec 7.2 and 4 say NULL or non-pressure. Fix: RRR_k is NULL when req_nonpositive_flag is true (12 rows seen) and say so in section 3.
   - Handling: RRR_k is NULL whenever req_nonpositive_flag is true (12 rows seen) as well as when Brem = 0 or there is no target. Such rows are never pressure rows via RRR. Sections 3, 4, 7.2 and 9 are read consistently with this.

6. **NIT**
   - Reviewer: OTHER_T20 treatment in the state table is unstated (30 matches, 60 innings; par cells exist only for IPL and T20I). Fix: keep state columns, set par, exp_remaining and rank_pct NULL, count as format_out_of_scope, exclude from all pressure populations.
   - Handling: OTHER_T20 rows (30 matches, 60 innings) keep state columns, get NULL par, exp_remaining and rank_pct, are counted as format_out_of_scope, and enter no pressure population.

7. **NIT**
   - Reviewer: Candidate family details open (spec 11): quantile context for family (a) not stated as per-format or pooled; the pair (-resource_ratio, phase=death) has no quantile in its phase condition although 'both conditions use the same q'. Fix: quantiles per competition_type x role with pooled as sensitivity; for the death pair the phase is the fixed label and only -resource_ratio uses q.
   - Handling: Quantiles are computed per competition_type x role (IPL and T20I separately), with pooled as a sensitivity. For the (-resource_ratio, phase = death) pair, phase is the fixed label and only -resource_ratio uses q.

8. **NIT**
   - Reviewer: Availability matrix (spec 5.3) has no rows for resource_ratio, projected_surplus, bowl_rel_A, bowl_rel_B, bat_pressure_rel, bowl_B_early_flag. Fix: add one row each (pre-delivery yes, or PARTIAL with par_basis where par or rank cells are used).
   - Handling: Add one availability row each for resource_ratio, projected_surplus, bowl_rel_A, bowl_rel_B, bat_pressure_rel, bowl_B_early_flag, and gap_k. Default classification is pre-delivery yes. Where par or rank cells are used, mark PARTIAL with par_basis. Until the rows exist, the feature dictionary must carry these classifications and the leakage test must cover them.

9. **NIT**
   - Reviewer: Stage 5 and Stage 6 flows are specified only as 'reuse Phase 2.5' (spec 14, notes): eligibility candidate generation, feeding the exploratory score into the combination engine and ADJUSTED_ESTIMATE are not defined. Fix: add a short subsection naming the Phase 2.5 functions reused, their inputs, and the rule that a missing format score stays missing.
   - Handling: Stage 5/6 implementers read the Phase 2.5 code and name the functions reused, their inputs (pressure balls, pressure matches, n_eff) and the candidate percentile list per format and role in the build manifest. The exploratory score feeds the combination engine only as a labelled proxy. ADJUSTED_ESTIMATE stays in its own section. A missing format score stays missing and is never imputed.

