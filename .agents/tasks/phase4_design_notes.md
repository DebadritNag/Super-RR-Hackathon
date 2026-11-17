# Phase 4 Design Notes (authoring step output)

Status of everything described: `EXPERIMENTAL_NOT_VALIDATED`, `official_ranking=false`. This document is the design that Chunks 1 to 5 of `phase4_plan.md` implement. It adds decisions the plan left open and corrects four plan statements. The stack is locked as in the plan: Python 3.11, pandas/numpy, DuckDB (official DB read-only, `p4_*` tables in `exploratory.duckdb`), FastAPI 0.111 with Pydantic v2, pytest, Ruff. No new dependencies (no scipy `milp`, no networkx).

Companion: `d:/Data/backend/data/reports/phase4_temporal_validation_plan.md` (boundaries, counts, lock).

## 0. Corrections to `phase4_plan.md` (found by running read-only queries)

1. Plan section 0.2 mixed IPL with OTHER_T20 in a "T20" column. Correct counts: IPL 74/74/71/74/74 matches in 2022 to 2026 (367 total), OTHER_T20 15 in 2024 and 15 in 2025, T20I 106/66/106/122/70 (470 total).
2. Same-date groups: IPL 64 dates (128 matches), OTHER_T20 14 dates (28 matches), **T20I 70 dates (147 matches)**. The plan said "2 in T20I"; that is wrong. The same-day tie-break therefore matters for T20I as well.
3. Shortened innings: 50 innings (limit not 120) in innings 1 and 2, covering 3,404 deliveries. They are exactly the 3,404 DLS-excluded rows (`phase_rule = PROPORTIONAL_DLS`). `pressure_rules_v1` mentions "48 shortened innings"; Chunk 1 must reconcile 48 versus 50 and report which is right before finalising the phase documentation.
4. Revised-overs fields hold balls (multiples of 6), not overs. The set of limits actually present is L = 30, 42, 48, 54, 60, 66, 72, 78, 84, 90, 102, 108, 114, 120. The plan's example list (96, 100) does not occur in the data; tests still cover 96 and 100 as synthetic lengths (hand-checked) in addition to the real set.

## 1. Chronological split (Stage A)

Boundaries (fixed in `config/phase4_split_v1.json` before any evaluation code reads outcomes):

| period | rule | IPL matches | T20I matches |
|---|---|---|---|
| TRAIN | match_date <= 2024-12-31 | 219 | 278 |
| VALIDATION | 2025-01-01 to 2025-12-31 | 74 | 122 |
| TEST | match_date >= 2026-01-01 | 74 | 70 |

OTHER_T20: TRAIN 15, VALIDATION 15, TEST 0 (never in scope). Matches and their deliveries stay together; assignment is `period = f(match_date)` only, one function, deterministic. Full counts, per-player thinness, and the limitation statements are in the temporal validation plan. Key finding that shapes later design: single-period player-level pressure samples are thin (VALIDATION has 0 to 6 players per cell with 36 or more pressure balls). Consequences:

- Player scores shown to users use the pooled `PRE_TEST` window (TRAIN + VALIDATION). Parameters (baseline cells, `k`, quantile thresholds) are TRAIN-only, so VALIDATION residuals are out-of-sample and TRAIN residuals use leave-one-player-out.
- TEST gets population-level evaluation always, and player-level evaluation only for cells with at least 15 qualifying players, otherwise reported `INSUFFICIENT_FOR_PLAYER_LEVEL_TEST`.
- Rolling origins 2024-01-01 and 2025-01-01 serve the stability metric only.

Alternative rejected: refit on TRAIN+VALIDATION for the primary test run. It gives more data but breaks "normalisation uses training-period parameters". It is reported as a sensitivity.

## 2. Baseline (Stage B) and what "pressure residual" means

Reuse `baseline_engine` (levels L0 `comp|role|phase|wbin` to L3 `comp`, EB shrinkage between levels). Fit on TRAIN rows only. Apply unchanged to VALIDATION and TEST. Fallback counts per level are reported per period.

Design point the plan did not state: the **Stage B baseline has no pressure term** (B0). Phase 3 used a per-candidate baseline with pressure membership as the finest level, so residuals inside the pressure sample were about zero on average by construction. That cannot support "pressure discrimination" (pressure rows versus non-pressure rows relative to the same baseline). Decision:

- Primary: pressure residual = actual minus B0 expected inside the pressure sample. Pressure effect = mean B0 residual in pressure rows minus mean B0 residual in non-pressure rows of the same format/role/innings population.
- Sensitivity (reported, not primary): Phase 3's per-candidate baseline, and a **within-player differential** (player's pressure residual minus own non-pressure residual), which separates pressure-specific skill from general skill. The primary residual mixes the two, because the baseline cells are not player-specific. This is stated as a limitation in the scoring report. Open decision O9.

Streams: batter runs off the bat per ball faced; bowler charged runs per delivery; bowler wicket rate per delivery. The Phase 2.5 composite bowler score (negative z of runs plus z of wickets, equal weights) is carried only as a labelled arbitrary convention.

Validation checks: calibration identity on TRAIN (sum of expected equals sum of actual per stream within 1e-6 relative), out-of-period calibration on VALIDATION by expected-value decile, format, phase and wickets-remaining bin, residual distribution, level-usage counts, per-year drift. DLS rows (3,404) are excluded by mask, not deleted.

## 3. Definition-selection rule (written before test; TRAIN and VALIDATION only)

Candidates: the nine full-eligibility definitions `{chase, inn1, any} x q in {0.75, 0.90, 0.95}`. Quantile thresholds are recomputed on TRAIN rows only (Phase 3 used the full sample; that is a leakage risk now removed). Real TRAIN-only chase `rrr` thresholds: IPL q0.75 12.26, q0.90 16.17, q0.95 21.20; T20I 11.61, 15.38, 20.00.

Cells: format (IPL, T20I) x role (batter, bowler) = 4.

Metrics per candidate and cell (all with match-cluster bootstrap, seed 20260512, 1,000 resamples):

| metric | definition | period |
|---|---|---|
| D, discrimination | standardised mean difference of B0 residual, pressure rows versus non-pressure rows of the same population; also dismissal, dot, boundary rate differences | VALIDATION (out-of-sample) |
| R, reliability | split-half over matches (odd/even by date rank within each player), Spearman-Brown corrected, players with at least 12 pressure balls | TRAIN |
| S, stability | Pearson/Spearman of player residual TRAIN versus VALIDATION, players with at least 12 TRAIN and at least 6 VALIDATION pressure balls | TRAIN vs VALIDATION |
| SNR | tau2 divided by mean noise variance of player means | TRAIN |
| P, population | players at or above 18 pressure balls in TRAIN | TRAIN (gate only) |
| report-only | format difference of D, ranking stability (bootstrap Top-10 inclusion), threshold sensitivity, par availability, sample sufficiency | TRAIN/VALIDATION |

**Order of selection steps (fixed; review finding 3).** (1) Definition, evaluated on the all-players pool with only the 12 and 6 ball floors already inside R and S, no eligibility threshold, and shrinkage at the `shrink_eb` default. (2) Shrinkage strength, for the chosen definition only, over all players with data in both TRAIN and VALIDATION. (3) Eligibility threshold, for the chosen definition and chosen `k`. Definition sensitivity (Stage D) re-runs steps 2 and 3 at fixed defaults only. The three choices are frozen in this order, and the frozen file records the order.

**Leakage-free signals per candidate (review finding 1, HIGH).** Phase 4 uses only these columns to build the nine flags:
- `chase`: `rrr` (pre-delivery state). Quantile thresholds from TRAIN rows only.
- `inn1`: `neg_par_dev_prior` (strictly prior par, section 5). Quantile thresholds from TRAIN rows only. Rows with `par_unavailable_insufficient_prior = True` get flag NULL and are excluded from that candidate's population; the excluded count is reported per format and period.
- `any`: the union of the two flags by innings (chase rows use `rrr`, innings-1 rows use `neg_par_dev_prior`). It uses no signal beyond those two.
- Bowler signal B: rebuilt from `neg_par_dev_prior` and a prior-only or TRAIN-frozen expected-remaining-runs value (`exp_remaining_train`, the E0 to E2 curve fitted on TRAIN, applied unchanged to later periods). It never uses `par_deviation_lomo`, `par_total_lomo`, `exp_remaining_lomo` or `projected_surplus` built from them.
- Rank-percentile columns (`rank_pct_with_fallback`) are replaced by TRAIN-fitted percentile maps (empirical CDF from TRAIN rows), applied to all periods.
- `LeakageGuard` rejects any column name ending in `_lomo` and any registered full-sample rank column. New test: mutate every later match and check that all nine flags for earlier matches are unchanged. Existing LOMO columns remain only in the descriptive table.

Rule (`config/phase4_definition_rule_v1.json`, SHA-256 recorded in the frozen-choices file):
1. **Gate 1 (floor, not an objective).** The candidate needs P >= 15 in every one of the four cells. Failing candidates are listed and excluded. This blocks near-empty pools. Beyond this floor, population size has no effect on the choice.
2. **Score (Gate 2 removed; estimability is part of ranking).** A candidate is rankable only if all four cells are estimable (at least 15 qualifying players for R and for S). Otherwise it is `NOT_RANKABLE` and listed with the failing cells. For each cell, clip `r` to [-0.99, 0.99] and apply Spearman-Brown to R before clipping (a split-half `r <= 0` gives a corrected R of at most 0, which is kept as is and clipped). Compute `z_R` and `z_S` per cell, each with its own weight `n - 3` where `n` is the number of players behind that statistic. Pool each statistic across cells by weighted mean, then `Sc = 0.5 * (zbar_R + zbar_S)`, back-transformed with tanh for display. The bootstrap SE of `Sc` (1,000 match resamples) is reported beside every candidate.
3. **Choice.** Rank by `Sc` descending. Candidates within 0.02 of the best `Sc`, or within 1 bootstrap SE of the best, whichever is larger, form the top group. Ties inside the top group go to lexicographic `definition_id`. **D is report-only** (review finding 5): the expected sign is declared before the run (batter runs per ball below baseline, batter dismissal rate above, bowler runs above baseline, bowler wicket rate below baseline); the report counts D only in the expected direction, states that |D| grows with the quantile by construction, and compares D only among candidates with the same quantile. Eligible population is never a selector or tiebreaker.
4. **Output.** The winner is reported as `PROVISIONAL, one of 9 examined`. The report gives the full nine-row table, `NOT_RANKABLE` and Gate 1 failures, and a **selection-stability** figure: the share of 1,000 match-bootstrap resamples (of TRAIN and VALIDATION matches) in which each candidate wins. Each resample recomputes TRAIN-only quantile thresholds and the percentile maps; the baseline is held fixed (review nit 14). A winner with a low share is said to be indistinguishable from others.
5. `chase|q0.9` remains the labelled leading candidate. If the rule picks another definition or `chase|q0.9` fails Gate 1, the report says so. Stage C scores are written for all nine definitions. The headline file uses the rule winner and also flags `chase|q0.9` rows, so the user decides (open decision O6). No result is relabelled to match the earlier preference.

Why not maximise population: population measures how many players pass a count threshold, which grows as the threshold flag loosens, and says nothing about whether the sample separates players. R and S measure that directly. Why these two: a definition that cannot reproduce a player's relative performance across half-samples or across periods has no player-level signal, whatever D says.

Multiplicity and noise: with nine candidates and four noisy cells, picking the maximum inflates `Sc`. The selection-stability share and the cell sizes make this visible; no claim of superiority is made unless the winner's interval separates from the runner-up.

## 4. Shrinkage (Decision 2)

Estimator, per (role, format, stream), fitted on TRAIN-window data only (for PRE_TEST scoring, parameters stay TRAIN-fitted, data in the player estimate come from the scoring window):
- Ball-level residual `e_ij` = actual minus B0 expected (LPO on TRAIN rows).
- Player mean `r_i`; per-match ball counts give `n_eff_i` (Kish, `shrinkage.n_eff_kish`).
- Noise variance: pooled within-player ball variance `sigma2_w` (homoscedastic). Per-player own variance is rejected as primary because median pressure sample is 6 to 15 balls, which gives unusable per-player variances. A per-player bootstrap variance for players with at least 5 matches is a sensitivity.
- Between-player variance by method of moments: `tau2 = max(var(r_i) - mean(sigma2_w / n_eff_i), tau2_floor * sigma2_w)`, `k = sigma2_w / tau2`. This is `shrinkage.k_from_children`, reused unchanged. **Floor**: `tau2_floor = 0.01` (existing, relative to `sigma2_w`), so `k <= 100`. When the moment falls below the floor, `shrinkage_floor_hit = True` is stored and reported. Because a floor hit means the data show less between-player spread than the floor and so a weaker shrinkage than the data support, a second floor 0.001 (`k <= 1000`) is in the grid.
- Estimate: `m_i = mu_{-i} + B_i (r_i - mu_{-i})`, `B_i = n_eff_i / (n_eff_i + k)`, equal to `shrink_to_parent`. `mu_{-i}` is the pooled mean of all OTHER players' residuals in the same role and format, from `shrinkage.pooled_other_mean` (ball-weighted). The player's own rows never enter `mu_{-i}`. `tau2` uses all players (second-order dependence on player i; documented, and a leave-player-out `tau2` check is reported descriptively).
- Role and format separation: batter and bowler populations never mix; IPL and T20I are shrunk separately; combination (weights from `config/format_weights_v1.json`) happens after shrinkage, and only for players eligible in both formats.
- Assumptions written into the report: normal residual means, independent matches (cluster = match), exchangeable players within a cell, homoscedastic noise after n_eff, `tau2` constant over the window.

Configurations (ids stored in output): `shrink_none` (B = 1, zero shrinkage, kept as sensitivity), `shrink_eb` (fitted tau2, floor 0.01), `shrink_tau0.5`, `shrink_tau2`, `shrink_tau4` (multipliers on fitted tau2 after the floor), `shrink_floor0.001`, `shrink_target0` (target 0 instead of `mu_{-i}`, named sensitivity).

Choice rule (written before test, VALIDATION only): for players with data in both TRAIN and VALIDATION, predict the VALIDATION raw mean residual from the TRAIN-based estimate; loss = VALIDATION-`n_eff`-weighted squared error pooled over the four cells; choose the lowest loss among `shrink_eb`, `tau0.5`, `tau2`, `tau4`, `floor0.001`. The standard error is the match-cluster bootstrap SE (1,000 resamples, seed 20260512) of the paired loss difference `loss(config) - loss(shrink_eb)`, resampling VALIDATION matches. A non-default config is chosen only when its mean difference is below `-1 SE`; otherwise `shrink_eb` stays (the principled default). Grid note: `tau0.5/2/4` are multipliers on fitted tau2 after the floor; `floor0.001` changes the floor only. `shrink_none` and `shrink_target0` are reported but cannot be chosen as primary. TEST outcomes are never used. The choice is recorded in `phase4_frozen_choices.json` before `evaluate_on_test`.

**Window rules (review finding 7).** Primary: the shrinkage target `mu_{-i}` is the pooled mean of OTHER players' residuals from TRAIN only, so decision 2 ("training period only") holds for every parameter (`k`, `mu_{-i}`, thresholds). The player's own `r_i` and `n_eff_i` come from the scoring window (PRE_TEST). Sensitivity `shrink_mu_window`: `mu_{-i}` from the PRE_TEST window (leave-one-player-out within it), labelled a deviation from "training only". Eligibility ball counts for PRE_TEST scoring: the TRAIN-derived threshold `t` is applied to the TRAIN-equivalent count rescaled by the window ratio, i.e. a PRE_TEST player is eligible when PRE_TEST pressure balls >= `t * W`, where `W` = PRE_TEST pressure balls / TRAIN pressure balls for that cell (state-only, about 1.3 to 1.5). The unscaled variant is a sensitivity.

Uncertainty interval: seeded match-cluster bootstrap (1,000 resamples) of the player's matches, recomputing `r_i` and `m_i` with `k` and `mu_{-i}` held fixed; 2.5 and 97.5 percentiles. The analytic posterior SD `sqrt(B_i sigma2_w / n_eff_i)` is stored beside it. Intervals do not include `tau2` estimation error; that is stated.

## 5. Strictly prior first-innings par (Decision 3)

Rule: par for evaluated match `m` with date `d`, competition type `c` uses first-innings source innings (the existing `par_source_rule`: 120-ball limit and complete innings) with `match_date < d`, same `c`. Same-day matches excluded, including the earlier of a double-header. The per-ball par curve is the mean cumulative runs at each legal ball over prior source innings, as in `par_columns`.
- Insufficient prior: fewer than `min_prior_innings = 30` prior source innings gives NULL and `par_unavailable_insufficient_prior = True`. There is no cross-format or LOMO fallback and no zero-fill. A single curve per competition type has no coarser level within par; the plan's "coarser level" fallback applies to the remaining-runs expectation (`E0 -> E1 -> E2 -> NONE`), not to par. Sensitivity: `min_prior_innings` 15 and 60.
- Real effect on the current build (first-innings rows): IPL 3,737 of 45,588 rows NULL, 30 matches, last NULL date 2022-04-18. T20I 3,955 of 56,466 rows NULL, 33 matches, last NULL date 2022-07-18. All in TRAIN. Chunk 1 reports affected innings and rows by format and period.
- Implementation: the existing vectorised `searchsorted(side="left")` code is the base. `app/phase4/par.py` wraps it, adds the flag, and a test proves equivalence against a brute-force loop on synthetic data and against raw CSV for one real innings (spot check).
- LOMO par stays in a descriptive table with label `DESCRIPTIVE_ONLY_USES_FUTURE_MATCHES`. `LeakageGuard` raises if scoring code requests a column ending in `_lomo`.
- TEST par: computed inside `evaluate_on_test` (it includes earlier TEST first innings, which are TEST outcomes). Sensitivity: par frozen at 2025-12-31.

## 6. Eligibility thresholds (Decision 5)

Separately for IPL batter, IPL bowler, T20I batter, T20I bowler.

Candidates per cell: percentiles P10, P25, P50, P75 of per-player pressure balls in TRAIN (existing config), plus the existing practical rungs (batter balls 6 to 120, bowler balls 6 to 144) and match rungs 2 to 15 (`confidence_engine.percentile_candidates`, `practical_candidates`, `build_ladder`). Real TRAIN distribution under the state-only proxy (chase, TRAIN-only q0.9 `rrr` flag): IPL batter P50 9 / P75 21.25 / P90 40.1 balls; IPL bowler 15 / 35.75 / 59.5; T20I batter 7 / 14 / 30; T20I bowler 12 / 20.75 / 40. Players with 24 or more balls: 37, 38, 35, 34 (same order); with 36 or more: 18, 27, 15, 20. Phase 3's T20I placeholders (batter 24, bowler 36 balls) are labelled superseded.

Metrics per candidate: pressure opportunities, distinct matches, `n_eff`, median shrunk-interval width, median data weight `B_i`, bootstrap stability (mean pairwise Jaccard of Top-10 sets and pool-size interval across 1,000 resamples), ranking stability (Top-10 inclusion distribution), temporal reproducibility (Spearman of TRAIN versus VALIDATION residuals for players with TRAIN balls >= t and VALIDATION balls >= ceil(t * R), where R = VALIDATION pressure balls / TRAIN pressure balls for the cell, from state only; n players stated).

Selection rule (pre-declared, TRAIN and VALIDATION only, saved to `config/phase4_eligibility_candidates_v1.json`):
1. Gate on the player at the threshold (review finding 6): `B(t) = n_t / (n_t + k) >= 0.5`, where `n_t` is the `n_eff` of the lowest-count eligible player at threshold `t` (observed minimum `n_eff` among players with count >= `t`). This is the existing `recommendation.min_data_weight` applied to the marginal player, not the median. The median `B_i` is reported beside it as information. Equivalent to `n_t >= k`.
2. Among passing candidates the smallest threshold is chosen, provided reproducibility is not significantly negative. "Significantly negative" means the match-bootstrap 95% interval of the TRAIN-vs-VALIDATION Spearman correlation lies entirely below 0. Reproducibility is estimated only when at least 15 players qualify in both periods; otherwise it is `REPRODUCIBILITY_NOT_ESTIMABLE` and does not block the candidate (the report states this).
3. If no candidate passes, the cell is `THRESHOLD_NOT_VALIDATED`. The report lists every candidate with at least 5 eligible players and its reproducibility (with n and interval). A fallback is named only if one candidate has reproducibility estimable (n >= 15) and its interval excludes 0 on the positive side; otherwise no fallback is named. A named fallback is labelled `PROVISIONAL_LOW_DATA_WEIGHT`, with a note that it is a maximum over noisy values with no multiplicity correction. It is never labelled validated.
4. The pool is whatever remains. Fewer than ten is reported as is. No threshold is lowered to reach ten, and no pool is padded.

Expected difficulty, stated now: with `k` up to 100, a data weight of 0.5 needs `n_eff` near `k`, while the TRAIN P90 is 30 to 60 balls. Cells may land in `THRESHOLD_NOT_VALIDATED`. That is an acceptable outcome and will be reported; a 0.3 data-weight alternative is shown beside it, not substituted. Open decision O10.

## 7. Phase boundaries and shortened innings (Decision 4)

Existing implementation (`phase_engine`): powerplay if `B < floor(3L/10)`, death if `B >= ceil(3L/4)`, middle otherwise, where `B` = legal balls bowled before the delivery and `L` = innings limit in balls. Boundaries for every L in the data (balls; innings / deliveries affected, innings 1 and 2):

| L | pp_end | death_start | innings | deliveries |
|---|---|---|---|---|
| 30 | 9 | 23 | 4 | 97 |
| 42 | 12 | 32 | 3 | 126 |
| 48 | 14 | 36 | 4 | 187 |
| 54 | 16 | 41 | 4 | 173 |
| 60 | 18 | 45 | 3 | 184 |
| 66 | 19 | 50 | 6 | 422 |
| 72 | 21 | 54 | 2 | 100 |
| 78 | 23 | 59 | 2 | 141 |
| 84 | 25 | 63 | 4 | 267 |
| 90 | 27 | 68 | 7 | 610 |
| 102 | 30 | 77 | 4 | 420 |
| 108 | 32 | 81 | 2 | 173 |
| 114 | 34 | 86 | 5 | 504 |
| 120 | 36 | 90 | 1,662 | 197,557 |

The limit is constant within each innings (0 innings vary). Limit sources: `DEFAULT_120` 197,557 rows, `REVISED_FIELD` 3,270 rows, `CARRIED_FROM_FIRST_INNINGS_UNVERIFIED` 134 rows. All 3,404 non-120 rows carry `phase_rule = PROPORTIONAL_DLS` and `dls_exclude_primary = True`, so they are already excluded from the primary scoring and 0 are in the primary chase sample. Phase is ball-based; for L < 120 the boundaries fall inside overs.

Future information: the label uses only `B` (before the ball) and `L`. `L` is known at the time only if the revision was announced before that ball. For innings-1 revisions and for revisions announced mid-innings, balls before the announcement would have used the original limit of 120. The data does not record announcement time, so labels for those innings may use later-known information. Handling: these innings are already excluded (DLS mask). Chunk 1 documents the timing issue, tests that the label is a function of `(B, L)` alone, and reports the sensitivity "exclude all non-120 innings from phase-dependent metrics" (which equals the current exclusion). Shortened innings are never imputed. Revisions by period: IPL TRAIN 1, VALIDATION 2, TEST 2 matches; T20I 16, 7, 6 matches. All delivery records stay in the table; exclusions are masks, and a test asserts row counts are unchanged.

## 8. Test-period lock design

Components in `app/phase4/split.py`:
- `Split.from_config()` loads boundaries and exposes `assign_period(date)`.
- `TestLock` (singleton per run) with `is_open`, `log`, `open_for_evaluation()`.
- `LockedFrame` wraps a DataFrame holding TEST outcome columns. `__getitem__`, `.values`, `.to_numpy`, iteration, aggregation helpers all go through `_check()`, which raises `TestPeriodLockError` and appends `{seq, caller, columns}` to `data/reports/phase4_lock_log.json` while the lock is closed.
- Outcome column set: `out_*`, `den_*` outcome fields, any column named `*residual*`, `*expected*` derived with outcomes, per-player outcome aggregates. Non-outcome state columns (`rrr`, `legal_balls_bowled_before`, `team_wickets_before`, ...) stay readable.
- **Freeze audit (review finding 8).** At freeze time the writer computes SHA-256 of `phase4_frozen_choices.json` and appends it as a separate, append-only entry `{seq: N, event: FREEZE, sha256}` in `phase4_lock_log.json` and in the Chunk report. `evaluate_on_test` must find FREEZE entry N with a matching hash, then write `{seq: N+1, event: OPEN}`; any other order raises. A separate non-hashed audit file `phase4_lock_audit.txt` records file modification times of the frozen file and the log, so freeze-before-open is auditable (the main log stays deterministic). TEST outcome tables are stored only with the prefix `p4_test_locked_`. A static test greps `app/phase4` and `app/api`, and asserts that only `evaluate.py` references that prefix. `LockedFrame` stops accessors only; direct DuckDB reads of that prefix are prevented by the naming test and by the API opening only non-locked `p4_*` tables. This is a convention-level guard, not a security boundary; the report says so.
- `evaluate_on_test(frozen_path)`: verify the file exists and its SHA-256 matches the FREEZE log entry and the config hashes; open the lock once; compute TEST scores and metrics for the frozen configuration plus the TEST_CORE sensitivity; close; write the log. A second call raises.
- Selection code (definition, shrinkage, eligibility, baseline variant) takes a `SelectionContext` containing only TRAIN and VALIDATION frames, so TEST data is structurally absent rather than merely discouraged.

Tests: reading TEST outcomes raises and logs; evaluation opens once; missing or modified frozen file refuses; mutating TEST outcomes does not change any frozen choice.

## 9. Classification design (additional requirement 1)

Table `p4_player_classification`: `player_id`, `nationality` {Indian, Overseas, Unknown}, `nationality_verification` {VERIFIED_FROM_SOURCE, DERIVED, UNVERIFIED}, `nationality_source`, `international_status` {Capped, Uncapped, Unknown}, `international_status_verification`, `international_status_source`, `unknown_reason`, `conflict_flag`, `classification_version`. All four combinations are representable; the two fields are never inferred from each other.

Evidence found in the data (verified now):
- `ipl squad.csv`: 257 rows, 10 teams, nationality Indian 175 and Overseas 82, no blanks; `designation` holds only Captain (10) or blank (247), so **there is no capped/uncapped information in any file**. `competition_team_player_mapping.csv`, `ball_by_ball` and `playing_eleven` have no nationality.
- Name resolution (case-insensitive exact against `players.player_name`): unique 232, none 23, ambiguous 2 (Rashid Khan, Abdul Samad).
- Players who played at least one T20I in the data: 719 of 1,217. Squad-matched players: Indian 106 not seen in T20I and 50 seen; Overseas 2 not seen and 74 seen.

Rules:
- `nationality`: override (VERIFIED_FROM_SOURCE, source `MANUAL_OVERRIDE:<source>`) first; then squad CSV unique exact name match **corroborated by team** (squad `team_name` equals a team the player has a `player_id`-keyed row for in `competition_team_player_mapping.csv` in the same competition): `DERIVED`, source `ipl squad.csv NAME_PLUS_TEAM_MATCH` (review finding 2, HIGH; name matching only generates candidates). A unique name match without team corroboration stays `UNVERIFIED` with nationality `Unknown` and is listed as a candidate. `VERIFIED_FROM_SOURCE` is reserved for a `player_id`-keyed source or a manual override. The count of corroborated versus uncorroborated matches (of the 232) is measured and reported in Chunk 3. Then optional DERIVED from T20I national-team appearance (`DERIVED_FROM_T20I_NATIONAL_TEAM`, team recorded; Indian only if the T20I team is India, Overseas only if all T20I appearances are for other teams); else Unknown. A franchise team never derives nationality. Variant-name candidates (the 23 unresolved) are written to the unresolved list with their candidate id and are **not applied**; the user confirms them. A squad/derived disagreement sets `conflict_flag` and keeps the source value.
- `international_status`: override first; else Capped with verification `DERIVED` and source `DERIVED_FROM_OFFICIAL_T20I_APPEARANCES` when the player was listed in `playing_eleven` for a T20I match dated on or before `as_of_date` (default 2025-12-31, the end of PRE_TEST; the first T20I date is stored; "appeared" means listed in the playing eleven, chosen because it needs no ball-level event and is available before the match; review finding 9). A TEST-period debut is therefore not Capped for PRE_TEST scoring; else Unknown with `unknown_reason = NOT_PROVEN_CAPPED_IN_DATA`. **Uncapped is only ever VERIFIED_FROM_SOURCE via override or a source file.** Never appearing in the data is not evidence of Uncapped (the data begins 2022-01-22, so a player capped earlier who did not play since is Unknown). Expected Uncapped count today: 0.
- Overrides: `config/classification_overrides_v1.csv` header-only; load validation (known `player_id`, field in the two names, value in enum, non-empty `source` and `verified_by`, ISO `verified_date`, no duplicate `(player_id, field)`); never pre-populated.
- Coverage report: counts per nationality x status combination including Unknown, with reasons; unresolved players list; data request (verified cap list keyed by player_id or by name plus team; player_id keys for 23 + 2 squad names; nationality for non-squad players).
- Tests: same name but different team stays `Unknown`/`UNVERIFIED`; TEST-period debutant not Capped as of 2025-12-31. API profile and ranking endpoints read only non-locked `p4_*` tables and exclude TEST-period outcome fields until `evaluate_on_test` has completed.
- Selection default `classification_basis = INCLUDE_DERIVED_CAPPED` (derived Capped counts as Capped, always labelled DERIVED), alternative `VERIFIED_ONLY` treats derived-capped players as Unknown. Open decision O5.

## 10. Selection optimiser (additional requirement 3)

Groups (a player belongs to exactly one): `IN_CAPPED`, `IN_UNCAPPED`, `OS_CAPPED`, `OS_UNCAPPED`, `UNKNOWN` (nationality Unknown or status Unknown). **Score and roles (review finding 10).** `selection_score` = shrunk residual converted to higher-is-better (negated for bowler runs conceded; bowler wicket stream enters only through the labelled composite, O12), then standardised per (role-side, format) as `(m - mean_TRAIN) / sd_TRAIN` using TRAIN parameters, so batter and bowler scores share a scale. Roles: the four squad-file role values, taken verbatim from `ipl squad.csv` (Batter, Bowler, All-Rounder, Wicket-Keeper; Chunk 3 reads the exact strings and fails if the count is not four). Players absent from the squad file get role `Unknown` and are excluded from role-constrained requests (counted in the response). A player with both a batter and a bowler score is selected under the side with the higher standardised score, one entry per player (no double count); the other side's score is shown but not used.

Request: total `N` (default 10), per-group `{exact | min | max}` (exact sets min = max), optional role min/max per role, `classification_basis`, `include_unknown` (default False: UNKNOWN has max 0 unless the request names it). Unconstrained groups have min 0, max N. Pool = experimental eligible players only; ineligible players are never candidates.

Algorithm (deterministic, exact):
1. Sort each (group, role) cell by score descending, then `player_id` ascending. Prefix sums `P_c(j)`.
2. Feasibility pre-check, reported with the failing constraint and available counts: for each group `min_g <= avail_g`; role mins versus availability; `sum(min_g) <= N <= sum(min(avail_g, max_g))`; role analogues; then a full DP feasibility pass for combined constraints.
3. If no role constraints: DP over the five groups with state = players chosen so far, value = best sum of `P_g(j)` for `j` in `[min_g, min(max_g, avail_g)]`. With roles: process groups in turn, state = vector of role counts (at most C(N+4, 4) = 1,001 vectors with total at most N for 4 roles and N = 10; `Wicket Keeper`/`All Rounder` grouped as in the squad file's four roles), transition = choose a count per role for the group with the group total in `[min_g, max_g]`.
4. Take the best total `V*` (comparison tolerance 1e-9 after rounding scores to 9 dp). Reconstruct all count vectors achieving `V*` by backward search using the stored value-to-go; for each vector, the selection is the top-`j` prefix of each cell. Among tied optimal selections choose the lexicographically smallest sorted `player_id` tuple.
5. Return fewer than N, explicit `INFEASIBLE`, or a degraded preset message. Never pad with ineligible, never relax a constraint silently.

Optimality argument: (a) every constraint depends only on cell counts `c = (c_{g,r})`; (b) for a fixed `c`, taking the top `c_{g,r}` players in each cell maximises the sum by an exchange argument (replacing a chosen player with an unchosen higher-scoring player of the same cell changes no constraint); (c) the DP enumerates all feasible count vectors (it is exhaustive over group totals and role vectors, with only dominated states pruned by equal-state value comparison, which is safe because future transitions depend on the state alone); hence the result is optimal. Tests compare the DP to brute-force subset enumeration on pools of up to 14 players, covering exact, min, max, role constraints, ties, and infeasible cases, plus the 4/3/2/1 example.

Presets are JSON parameter templates (`config/phase4_selection_presets_v1.json`), not precomputed rankings: Best Indian Uncapped XI, Top Indian Uncapped Batters, Top Indian Uncapped Bowlers, Best Overseas Uncapped Players, Emerging Domestic Talent (Indian + verified Uncapped + eligible + optional min matches), Mixed Capped and Uncapped XI. With zero verified Uncapped players, every uncapped preset returns `status = POOL_TOO_SMALL` with available and required counts and a pointer to the data request, never a relaxed constraint.

## 11. API surface (additional requirements 2, 4, 5, 6)

There is no FastAPI app in the repo. Chunk 4 creates `app/main.py`, `app/api/{deps,errors}.py`, `app/api/v1/*`, `app/schemas/phase4.py`, `app/repositories/phase4_repo.py`, `app/services/phase4_service.py`.

Under `/api/v1` (all JSON; Pydantic v2 models; uniform error `{"error": {"code", "message", "details"}}`; pagination `{items, total, limit, offset}` with `limit <= 200`, `offset >= 0`):

| method | path | purpose |
|---|---|---|
| GET | `/players` | directory with filters, sort, pagination |
| GET | `/players/{player_id}` | classification and summary |
| GET | `/players/{player_id}/profile` | stats, pressure, radar data, strengths with evidence, percentiles, `INSUFFICIENT_DATA` labels |
| GET | `/rankings/{role}` | experimental ranking distribution rows, role in `batter`, `bowler` |
| GET | `/rankings/uncapped/{kind}` | `indian_batters`, `indian_bowlers`, `overseas_batters`, `overseas_bowlers`, `overall` (filters over the main experimental scoring; test asserts equality with the filtered main ranking) |
| GET | `/compare` | up to 5 player_ids, side-by-side with percentiles |
| POST | `/selection/custom` | composition request, optimiser result or infeasibility |
| GET | `/selection/presets` and POST `/selection/presets/{preset_id}` | templates and runs |
| GET | `/meta/classification-coverage` | coverage counts |
| POST | `/admin/classification/reload`, GET `/admin/classification/overrides` | admin only |

Filters (enum `classification_filter`): `indian_uncapped`, `overseas_uncapped`, `all_uncapped`, `capped`, `unknown_international_status`; `include_uncapped` / `exclude_uncapped`; `min_matches`, `min_pressure_matches`; sorts are an enum whitelist mapped to column names in the repository; all SQL is parameterised; no endpoint takes a file path or raw SQL.

Every result row carries: `player_id`, `name`, `nationality`, `nationality_verification`, `international_status`, `international_status_verification`, `eligibility`, `score`, `pressure_opportunities`, `distinct_matches`, `n_eff`, `interval_low`, `interval_high`, `restrictions_applied`, `status = EXPERIMENTAL_NOT_VALIDATED`, `official_ranking = false`, `disclaimer`. Rankings read only `p4_*` tables, opened `read_only=True`. A request with `official=true` or publication intent returns 403 `OFFICIAL_RANKING_NOT_AUTHORIZED`. Admin routes require `X-Admin-Token` compared with `hmac.compare_digest` to `SUPERR_ADMIN_TOKEN`; unset means 503 `ADMIN_DISABLED`; wrong token 401. Docs: `docs/frontend_backend_contracts.md` (copied to `data/reports/`) and `docs/backend_implementation_spec.md`. No frontend code.

## 11b. Format-combined estimate and Stage D/E procedures (review finding 11)

- Combined estimate for player `i` (eligible in both formats): `m_comb = w_ipl * m_ipl + w_t20i * m_t20i`, weights from `config/format_weights_v1.json` (eight configurations; 70:30 provisional). Interval: bootstrap IPL and T20I matches independently (1,000 resamples each, seed 20260512), recompute `m_ipl` and `m_t20i` with `k` and `mu` fixed, combine, take 2.5 and 97.5 percentiles. Single-format estimates stay reported separately; a player eligible in one format is never combined and is never imputed.
- Top-10 overlap between two configurations is reported only when both pools have at least 10 players. Otherwise overlap uses `k = min(pool_a, pool_b)` and is marked `TRIVIAL_FULL_POOL` when `k` equals the pool size of both. Spearman and rank movement use the intersection of eligible players, with n stated.
- Stage E: per-resample rank, rank interval (2.5 and 97.5 percentiles of rank), Top-10 inclusion probability, expected Top-10 overlap with the point-estimate Top 10, Spearman versus point-estimate rank. Pools below ten are not padded.
- Baseline alternatives (ids): `B0` primary; `B_noseason` (no season offset), `B_coarse` (L1 as finest level), `B_fine` (L0 plus over-in-innings bin), `B_phase3` (per-candidate baseline with pressure membership). Every alternative is fitted on TRAIN only and judged by VALIDATION calibration and by Spearman against `B0` scores.
- Definition, shrinkage, threshold, format-weight and baseline sensitivities run as separate one-factor-at-a-time analyses with the others held at frozen defaults. They are never crossed in one table.

## 12. Testability

- Unit-testable with synthetic frames (`tests/pressure_helpers.py`): split, par (same-day, insufficient prior, brute-force equivalence), phase boundaries (L = 30 to 120, including 96 and 100), shrinkage (hand-checkable normal-normal, zero tau2, floor hit, zero shrinkage equals raw, LPO exclusion), eligibility percentiles, bootstrap determinism and inclusion-probability sums, classification rules, override validation, optimiser vs brute force, lock behaviour, API schema through `TestClient`.
- Integration-tested on real data: calibration identity, restriction counts (DLS 3,404; 0 in the primary chase sample), preservation hashes, `p4_` write guard, spot checks by pandas (par for one innings from raw CSV, period counts, a player's pressure balls and residual, one shrunk estimate recomputed from stored components, one classification count from the CSV).

## 13. Open decisions (safest option taken, none blocks)

| id | decision | option taken |
|---|---|---|
| O1 | no FastAPI scaffold in the repo | create it in Chunk 4, no frontend code |
| O2 | admin protection | static token in `SUPERR_ADMIN_TOKEN`, disabled when unset; no real auth system |
| O3 | 42 T20I matches dated 2026-06-12 to 2026-11-01 | kept as recorded in TEST; TEST_CORE (to 2026-05-31) sensitivity; user to confirm the dates |
| O4 | split boundaries | proposal fixed in config before evaluation; user may prefer rolling-origin as primary |
| O5 | classification basis for selection | derived Capped counts as Capped, always labelled; `VERIFIED_ONLY` available; UNKNOWN is one group excluded by default |
| O6 | definition choice if the rule does not pick `chase\|q0.9` | all nine scored; headline = rule winner; `chase\|q0.9` flagged; user decides |
| O7 | Emerging Domestic Talent preset | Indian + verified Uncapped + eligible; returns `POOL_TOO_SMALL` until verified classification exists |
| O8 | data requests | verified cap list; player_id keys for 23 unresolved plus 2 ambiguous squad names; confirmation of 2026 T20I dates; nationality for non-squad players |
| O9 | meaning of pressure residual | primary B0 residual in the pressure sample; within-player differential and Phase 3 per-candidate baseline as sensitivities |
| O10 | data-weight gate 0.5 for eligibility | inherited from Phase 3; likely yields `THRESHOLD_NOT_VALIDATED` cells; 0.3 shown as sensitivity only |
| O11 | TEST par | strictly prior including earlier TEST matches, computed under the open lock; frozen-at-2025-12-31 sensitivity |
| O12 | bowler composite (runs + wickets) | Phase 2.5 equal-weight z convention, labelled arbitrary; components reported separately |
| O13 | reconcile 48 versus 50 shortened innings | Chunk 1 resolves and documents before finalising phase notes |
| O14 | variant-name squad matches (23) | listed as candidates, not applied until the user confirms |
| O15 | primary-test refit | TRAIN-only parameters primary; TRAIN+VALIDATION refit sensitivity |
| O16 | `mu_{-i}` window and eligibility window scaling for PRE_TEST scoring | TRAIN-only `mu_{-i}`; thresholds scaled by window ratio `W`; PRE_TEST `mu` and unscaled variants as sensitivities |
| O17 | squad nationality without team corroboration | stays `UNVERIFIED`/`Unknown`; user may confirm in bulk through the override file |
| O18 | derived Capped `as_of_date` and "appeared" definition | 2025-12-31, playing-eleven listing; user may prefer ball-level appearance |
| O19 | lock is convention-level, not a security boundary | naming prefix plus static test plus audit file; stated in the report |
| O20 | two-sided players in selection | one entry under the higher standardised side; user may prefer both entries |
| O21 | "meaningful" Top-10 overlap | both pools >= 10, else `TRIVIAL_FULL_POOL` |

## 14. Responses to design review (one fix pass)

| finding | response |
|---|---|
| 1 HIGH leakage in signals | addressed: section 3 lists prior-only/TRAIN-only signals per candidate, extends `LeakageGuard`, adds mutation test; plan section 8 gains checks 7 and 8 |
| 2 HIGH name match labelled verified | addressed: section 9 requires team corroboration (DERIVED) else Unknown |
| 3 order of steps | addressed: section 3, fixed order definition, shrinkage, eligibility |
| 4 Sc under-specified | addressed: clipping, per-cell weights, all four cells required, `NOT_RANKABLE`, SE beside margin |
| 5 D tie-break | addressed: D report-only, expected sign declared, same-quantile comparison |
| 6 eligibility gate | addressed: marginal-player gate, defined significance, no fallback without estimable positive reproducibility |
| 7 windows | addressed: TRAIN-only `mu_{-i}`, scaled thresholds, sensitivities (O16) |
| 8 lock audit | addressed: FREEZE/OPEN entries, audit file, prefix test; residual convention-level risk (O19) |
| 9 Capped as_of | addressed: `as_of_date`, playing-eleven definition, API exclusion of TEST fields |
| 10 optimiser score | addressed: standardised higher-is-better score, roles, two-sided rule (O20) |
| 11 combined estimate | addressed: section 11b |
| 12 shrinkage SE | addressed: paired match-cluster SE, -1 SE rule |
| 13 nit rolling origin | addressed in plan section 6: refit per origin |
| 14 nit bootstrap | addressed: thresholds recomputed per resample, baseline fixed |

Unresolved and carried as open decisions: O16 to O21 (each has a safe default and does not block).
