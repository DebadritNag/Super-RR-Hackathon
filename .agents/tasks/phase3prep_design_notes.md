# Phase 3 prep design notes (revision 4): state-engine interface and context-adjusted baseline

Companion to `d:/Data/backend/docs/pressure_framework_v1.md` (the spec, revision 4; its section numbers are cited as "spec N"). Design only, no code. Stack locked: Python 3.11, pandas 2.2.3, numpy 1.26.4, scipy 1.15.2, DuckDB 2.0.0, pyarrow, pytest, ruff (line length 100). No new dependencies.

## A. Verified data facts that change the implementation (read-only queries on superr.duckdb)

- `first_inn_revised_overs` and `second_inn_revised_overs` hold BALLS (13 distinct values, all multiples of 6). Config names mislead. The engine converts nothing, uses the value as the ball limit, and asserts `value % 6 == 0` and `legal_ball_count <= value`. 14 distinct `L` values including 120.
- 34 revised matches; truth table in spec 7.6 (7 / 2 / 2 / 14 / 9). Per-innings: `dls_flag` 48 innings, `innings_limit_unstated` 2 (16753, 19959), `dls_exclude_primary` 50.
- 23 revised targets: 8 equal innings 1 + 1, 15 differ. 22 of 22 COMPLETED revised matches agree with `score >= revised_target`; 809 of 811 plain COMPLETED chases agree with `score >= innings 1 + 1`; the 2 exceptions are 24822 and 28334, whose `result` text says DLS but have no revised field. Four such matches exist (20182, 23674, 24822, 28334).
- `overid` equals the legal over index on all but 33 regulation rows (5 innings in 4 matches: 14130 x2, 14164, 16753, 41509). Phase and over come from legal balls. Over index advances on the 7th legal ball of `overid` 12 in match 41509 innings 1.
- Penalty: 1 row (16753, innings 2, ball 34), `is_legal_ball` true in DB, engine counts 0. 192,445 flagged legal, 192,444 counted.
- 2 regulation rows with `extras_type = 'None'` and nonzero extras: 17555 (innings 1, ball 29), 36097 (innings 2, ball 49). Flag, keep runs.
- 12 wicket-flag disagreement rows precede 739 later rows (spec 3). 1 wicket without dismissed player (40709).
- `matches` has no season column. `season_label` = `competitions.season` for IPL (2022 to 2026) and calendar year of `match_date` for T20I and OTHER_T20; `season_source` keeps the original (T20I has `2022/23`, `2023/24`, `2024/25` labels on 12, 3 and 3 matches). Joined via `matches.comp_id = competitions.comp_id`. The builder asserts the label set.
- 81 innings-1 and 153 innings-2 innings end all out before their stated limit; par must define early endings (spec 6).
- `Req <= 0` before a delivery: 12 rows, all match 48610 innings 2. Report as assertion count; do not fail the build.
- The ten Cricsheet-disagreeing innings are read from `data/reports/data_quality_impact_report.json` key path `issue_register.cricsheet_total_disagreements` (10 entries). Used only as masks.

## B. State-engine interface (Stage 2)

One pure function, used by the builder and by the leakage tests, so truncation tests exercise the production path.

```
compute_innings_state(rows: DataFrame, ctx: InningsContext, rules: PressureRules) -> DataFrame
```

- `rows`: one innings, columns from `deliveries`, sorted by `innings_ball_num`. The function re-sorts and asserts uniqueness and contiguity 1..n.
- `InningsContext` (frozen dataclass): `match_id, innings_number, competition_type, limit_balls, limit_source, target (int|None), target_source, dls_flag, dls_match_flag, innings_limit_unstated, dls_state_reliable (bool|None), dls_exclude_primary, restricted_reason (str|None), par_view (see C)`.
- `PressureRules`: loaded from `config/pressure_rules_v1.json`, created in Stage 2, containing every parameter in spec section 8 with its basis class, plus version string and seed.
- Output: one row per input row; lineage columns first (`match_id, innings_number, innings_ball_num, source_row_no`), then state columns and flags, then the `out_` group.
- Rule: every state column at row k uses only rows with position < k. Exclusive cumsum (`cumsum - current`) inside a groupby of `(match_id, innings_number)`; never `shift` across groups.
- Context building is separate: `build_match_context(conn_readonly) -> DataFrame` returns per `(match_id, innings_number)` the limit, target, DLS columns of spec 7.6 and reason codes. The innings-1 total is attached only to innings-2 contexts. A test passes a poisoned innings-1 total to an innings-1 call and asserts no effect.
- Builder: `build_pre_delivery_state(conn_ro, out_conn, rules)` is a VECTORISED pandas pass (groupby with exclusive cumsum) over all 200,961 regulation rows plus a restricted-row pass for the 38 rows of innings 3 and 4 (reason code attached, no state label). A per-row Python loop implementation exists only inside tests as an independent oracle and is compared with the vectorised output on synthetic and real innings.
- Output store: `exp_pre_delivery_state` and `exp_build_manifest` in `data/database/exploratory.duckdb` plus a parquet copy under `data/processed/`. `superr.duckdb` opened `read_only=True`; table content hashes and file sha256 checked before and after. Each row has a provenance/version column.
- Truth-table output: the builder writes the 34-match DLS truth table (spec 7.6) and asserts its counts (7, 2, 2, 14, 9). It also asserts multiples of 6, `legal_ball_count <= L` and innings contiguity, and checks each verified count in spec section 2 against the recomputed value.
- Outcome-conditioned denominator flags of row k (`counts_as_ball_faced`, `legal_inc`) are stored in the `out_` group (`out_counts_as_ball_faced`, `out_legal_inc`), so no state, par or rank function can receive them. Pressure membership is computed from state columns only; the flags select denominators afterwards. Bowler pressure membership covers ALL bowler deliveries in the state (wide, Overstep, other included); the legal filter applies only to per-legal-ball denominators (spec 5.4).
- `build_match_context` also writes `target_basis_unverified` for innings 2 (innings 1 `W < 10`, legal balls `< L1`, no `first_inn_revised_overs`, no `revised_target`), uses innings-1 data only, never `result` text, and reports the affected-chase count in the manifest. The primary chase population excludes it; a sensitivity variant includes it. `dls_suspected_unrecorded` stays a report-only list.
- Manifest counters for NULL handling (spec 4): `n_null_signal_excluded_from_V`, `n_rank_pct_null_own_signal`, `n_req_to_exp_null`, `exp_unavailable`, `par_unavailable`, `shrinkage_floor_hit`.
- State columns include both `W_k`/`Wrem_k` and `W_alt_k`/`Wrem_alt_k`, `state_wicket_flag_disagreement`, `req_nonpositive_flag`, `limit_applied_from_start_assumed`, `resource_status`, `phase_rule`, `par_basis` columns for both par variants.

Leakage tests (spec 5.4): truncate-and-recompute equality per row; state, par and rank columns of row k are identical when row k's `extras_type` or `is_legal_ball` is mutated; mutate later rows or the match result and earlier state is unchanged; innings-2 state at ball k independent of later innings-2 rows; innings-1 states independent of innings 2 and of the innings-1 total; par and `rank_pct` for match M independent of any value in M; strictly-prior par at date d independent of matches dated d or later; no function in the feature path accepts an `out_` column; no Phase 3 module opens a Cricsheet path.

## C. Par-model interface

```
build_par_tables(state_inputs, rules) -> ParTables          # cell sums, counts, per-(match, cell) contributions
ParTables.lomo_par_runs(match_id, competition_type, balls_before) -> float|None
ParTables.lomo_exp_remaining(match_id, competition_type, balls_remaining, wickets_remaining) -> float|None
ParTables.prior_par_runs(match_date, competition_type, balls_before) -> float|None       # STRICTLY_PRIOR
ParTables.prior_exp_remaining(match_date, competition_type, balls_remaining, wickets_remaining) -> float|None
```

- Source innings (spec 6): innings 1, `L = 120`, complete (`W == 10` or legal balls `== L`), IPL or T20I. Expected counts: 358 IPL + 435 T20I = 793.
- LOMO: store per-cell `sum`, `count` and per-(match, cell) contribution; leave-one-out is `(sum - own_sum) / (count - own_count)` vectorised.
- STRICTLY_PRIOR: cumulative per-cell sums ordered by `match_date`, taking the cumulative value from before the current date (same-day matches excluded). Cells below `min_prior_innings` return None and the row is counted as `par_unavailable`.
- Par rule (spec 6): `par_runs(c, b)` is read at the exact legal-ball count `b`; a source innings that ended all out before `b` contributes its final total (carry-forward). `par_drop_early_ended` is the named sensitivity. Table layout: one row per (source innings, b) stored as a dense per-innings cumulative-runs array padded with the final total, so carry-forward is an array fill, not a special case.
- `exp_remaining` (spec 6): defined on BINNED cells = `competition_type` x `Brem` bin (`(Brem - 1) // exp_brem_bin`, 6 balls) x global `Wrem` bin. Each source innings contributes one observation per binned cell, from its first row in the bin (`final_total - R` at that row); the clustering unit is the innings. Fallback chain: E0 binned cell (distinct source innings >= `min_cell_innings` for LOMO, `min_prior_innings` for strictly prior; shrunk to E1 with `shrink_to_parent`) -> E1 `Brem` bin only (used entire) -> E2 `competition_type` pooled (used entire) -> NULL (`exp_unavailable`). `exp_cell_level_used` and `exp_cell_level_used_prior` are stored per row. Exact `(Brem, Wrem)` cells are a diagnostic: the build reports how many reach the threshold and never uses them for a value. The `Wrem` partition is FULL_SAMPLE even for the strictly-prior variant (stated limitation). `par_ball_bin` is used only for sparse-cell smoothing and reports.
- Sparse cells fall back to a parent using the NEW helper `shrink_to_parent(n, sum_x, sum_x2, parent_mean, k)` in `app/analytics/shrinkage.py` (see D). `eb_shrink` is not used for this.
- Stage 3 reports, for innings 1 and for each candidate definition, the population (deliveries, matches, innings, rows with `par_unavailable`) under LOMO versus STRICTLY_PRIOR.
- Relative percentile (`rank_pct`, spec 4): mid-rank over deliveries of other matches in the cell; direction oriented so higher is more pressure; parent fallback when distinct innings < `min_cell_innings`; `cell_level_used` stored. Computed in a vectorised sorted-array form per cell (cumulative counts), with own-match removal done by subtracting the match's own counts. Both LOMO and strictly-prior cell data variants exist.

## D. Context-adjusted baseline design (Stage 4)

Goal: expected outcome per delivery given context, so actual minus expected compares like with like. No model fitting.

- Separate batter and bowler baselines.
- Batter outcomes: runs off the bat per ball faced, boundary, dot, dismissal. Bowler outcomes: charged runs per legal ball (`BOWLER_SQL` definition), bowler-credited wicket, dot, boundary, and extras rates (wide, Overstep, other tracked separately).

**Cell definition (reference baseline, B0; resolves review M7).** Cells use only context, never a pressure definition:

| Level | Cell |
|---|---|
| L0 | `competition_type x innings role (first innings / chase) x phase x wickets-remaining bin` |
| L1 | `competition_type x innings role x phase` |
| L2 | `competition_type x phase` |
| L3 | `competition_type` |
| L4 | pooled IPL + T20I |

Wickets bins come from the spec 8 global merge algorithm over `Wrem` 1 to 10 (data-derived, deterministic, merge log written to the output). `phase` uses the ball-based phase for L < 120 (spec 7.6). Pressure membership is not in the cell. The pressure effect is measured by summing actual minus expected over the deliveries that belong to a candidate pressure set; membership selects deliveries, it does not define expectations. Because phase and wickets are in the cell, a death-over delivery is compared only with deliveries of the same phase and wickets state, never with ordinary-over rates.

**Sensitivity baselines (B1..Bn).** One baseline is rebuilt per candidate pressure definition listed by Stage 3, with an extra cell dimension `in_pressure_set` (true or false). The count of baselines built equals the number of candidate definitions, and is reported. They are used only to show how much results change when pressure is stratified instead of measured as a residual. B0 is the primary exploratory baseline.

- Shrinkage helpers (all new code in `app/analytics/shrinkage.py`, each with unit tests; `eb_shrink(n, sum_x, sum_x2)` stays unchanged and is only used where shrinkage towards the pooled mean of its own input array is wanted):
  - `shrink_to_parent(n_eff, cell_mean, parent_mean, k)` returns `(n_eff * cell_mean + k * parent_mean) / (n_eff + k)`. `n_eff` is `n_eff_kish` of the cell (innings clustering). `k` comes from `k_from_children(children, tau2_floor)`: `sigma2_within` = pooled per-delivery variance of the parent's children; `between_moment` = variance of child means minus the mean of `sigma2_within / n_eff_child`; `tau2 = max(between_moment, tau2_floor * sigma2_within)`; `k = sigma2_within / tau2`, at most `1 / tau2_floor`. It returns `(k, tau2, sigma2_within, floor_hit)`; floor hits are reported as `shrinkage_floor_hit`. `tau2_floor` is a config value (ARBITRARY_PLACEHOLDER, 0.01 as a fraction of `sigma2_within`; sensitivity 0.001 and 0.1). Signature differs from the earlier `(n, sum_x, sum_x2, parent_mean, k)` because the cell mean and `n_eff` are what the formula needs; the caller derives the mean from raw sums.
  - `shrink_player(n_eff, sum_resid, tau2, sigma2, target=0.0)` (`n_eff` = `n_eff_kish` of the player's pressure sample, and `mean_resid = sum_resid / n_raw` supplied by the caller) returns the shrunk per-ball residual `target + (n * tau2 / (n * tau2 + sigma2)) * (mean_resid - target)`. Residuals (actual minus expected) are shrunk towards `target = 0`, stated explicitly; `tau2` is the between-player variance by method of moments and `sigma2` the per-ball variance.
  - `beta_binomial_shrink` for binary outcomes (below). Binary outcomes never go through `shrink_to_parent`; their counts are scaled by the design effect `n_eff / n` so both helpers use the same effective sample size.
  - Tests: `shrink_to_parent` equals the parent mean at n_eff = 0 and the cell mean as n_eff grows, monotone between; a parent whose children have zero (or negative moment) between variance gives `k = 1 / tau2_floor`, a finite result and `floor_hit = True`; `shrink_player` equals `target` at n = 0, tends to the raw mean as n grows, is zero for a player with zero residual.
- Shrinkage: binary outcomes (boundary, dot, dismissal, wicket) use a beta-binomial helper that does NOT exist in `app/analytics/shrinkage.py` today. It is new code (`beta_binomial_shrink`), with unit tests (known prior and counts, shrinkage toward parent grows as n falls, output in [0, 1]). Runs outcomes use `shrink_to_parent` (normal, method-of-moments `k`) toward the parent cell. A cell below `min_cell_innings` takes its parent value entirely. `n_eff_kish` (Phase 2.5 `n_eff` formula) is the effective sample size reported everywhere.
- Baseline variants, always reported together: `full_sample` (B0 cell means, own match included, descriptive); `leave_player_out` (cell sums minus the player's own contribution; the same match's other deliveries and all later matches remain, so it is `FULL_SAMPLE` in the availability matrix); `leave_match_out` (cell sums minus every delivery of the row's own match; a NAMED sensitivity reported beside leave-player-out, still uses later matches); `strictly_prior` (cells from matches dated before the row's match date only; cells below `min_prior_innings` are NULL and counted; the only variant allowed for predictive claims, used in the temporal split of spec 14).
- Descriptive status: the cell means in B0, the leave-player-out expectation and the player EB prior (between-player variance `tau2`) are estimated on all matches, so they include the delivery's own match and later matches. They are descriptive (`par_basis = FULL_SAMPLE`, spec 5.3) and are not future-clean; the player EB prior counts as a future player statistic if used predictively. Any predictive or validation claim re-estimates the prior and cells from matches before the cut date (`strictly_prior`).
- Season and competition: LOMO shrunk run-environment ratio by `competition x season_label`, other matches only. Off in the primary (open decision 10); reported if cell counts support it. Venue: same. If not computable without leakage, recorded as "not used". The ratio is labelled PARTIAL (LOMO) in the availability matrix.
- Actual versus expected per player: `sum(actual) - sum(expected)` over the player's pressure deliveries, then a shrunk per-ball estimate toward zero (`shrink_player`, `target = 0`) with an EB prior (between-player variance by method of moments, FULL_SAMPLE, descriptive), with 95% bootstrap CI by match (seed 20260512, 500 resamples for baseline, 1,000 as sensitivity; baseline held fixed inside the bootstrap, stated as a limitation).

**Sanity checks (resolves review M6).** Three separate checks:

1. Code-correctness identity on RAW cell means: within every L0 cell, pooled `sum(expected_raw) - sum(actual)` is zero to numerical tolerance (1e-9 on counts, 1e-6 relative on runs). This check can fail the build. It is a tautology by construction and exists only to catch indexing and join errors.
2. Shrunk-gap report: per L0 cell, `sum(expected_shrunk) - sum(actual)` with the reason for each non-zero gap (shrinkage toward parent, whole-cell parent fallback, own-match exclusion). Reported with a tolerance stated beside it; never fails the build.
3. Leave-player-out difference report: total `sum(expected_lpo) - sum(actual)` per outcome, reported.

Also: expected values within plausible ranges (probabilities in [0, 1], runs per ball between 0 and 6), and a rerun gives identical output (seeded).

- Outputs are aggregate only (cell tables, distributions of per-player estimates, check tables) plus a small technical sample labelled EXPLORATORY and not a ranking.
- Restrictions applied before cell building through the restriction applier: innings 3/4 out; Penalty out; `other` primary/sensitivity; flag-disagreement rows as sensitivity for dismissal outcomes; `W_alt` state variant; ten Cricsheet-disagreeing innings as sensitivity (mask only); `dls_exclude_primary` innings out of primary, in the sensitivity. Joins on `player_id` only; no `match_squads` read.
- Rejected for now: regularised logistic and gradient boosting expected-outcome models, because they add tuning freedom before the pressure definition is approved. Revisit after approval with temporal-holdout calibration.

## E. Restriction applier interface (Stage 7)

The applier IMPORTS and reuses `app/validation/restrictions.py` (`load_restrictions`, `validate_restrictions`, `restrictions_for_metric`, `rule_by_id`) and adds only the per-rule row-mask implementations. It does not re-parse the register.

```
RestrictionApplier(register_path, ledger_sources)
  .masks_for(metric, frame) -> (primary_mask, sensitivity_variants: dict[rule_id, mask])
  .ledger() -> per (metric, rule): rows_excluded, matches, players, reason_code_counts
```

- Each of the 26 rules has an explicit implementation entry; DOCUMENT_ONLY or unused-in-Phase-3 rules are recorded as such (spec 12). The test compares the applier's rule ids with the register's 26 and checks every `metric_vocabulary` entry is handled.
- `RULE_UNLINKABLE_MATCHES` (`cricsheet_validation_coverage`): validation only. `RULE_INFO_EXTRAS1_COMPARISON` (`extras_type_features`): DOCUMENT_ONLY.
- Reason codes for innings 3/4: 3 matches `CONFIRMED_SUPER_OVER_BY_CRICSHEET`, 3 matches `UNVERIFIED_INNINGS_ROLE`. The ids come from Phase 2.5 reports, mask only; no Cricsheet file is read and a test asserts it.
- The register's `row_filter` strings are descriptive text, not executable.

## F. Risks the coder should treat as tests

- Revised limit and target applied from ball 1 (hindsight) are flagged and kept out of the primary population.
- LOMO par with the own match left in would leak; test mutates own-match values.
- Strictly-prior par must not read same-day or later matches.
- Treating `revised_target` as `total + 1` would be wrong for 15 matches.
- Treating the revised-overs columns as overs (x6) would be wrong; assert multiples of 6 and `legal_ball_count <= value`.
- Using `overid` or `over_ball_num` for phase would misplace 33 rows and misread counters; use legal balls.
- Any column prefixed `out_` reaching a state feature is a failure; a test checks the feature function signature.
- `W_alt` variant: rows after a disagreement row differ in `Wrem`, rows before do not (739 later rows across 12 innings).
- Bowling conventions: A equals B as a ranking in innings 1; they differ in chases.
- Section 12 rule-id set equals the register's 26.
- Phase boundaries: `(3 * L) // 10` and `-((-3 * L) // 4)` reproduce the 14-row table in spec 7.6 exactly.
- Par with early-ended source innings: carry-forward fills the final total; the drop variant differs; one observation per innings per cell in `exp_remaining`.
- Wickets-bin merge: deterministic on a synthetic count table (tie broken towards `Wrem` 1), domain 1 to 10, merge log produced, failure fallback when a single bin is still sparse.
- `season_label`: IPL = `competitions.season`; the 18 split-year T20I matches map to calendar year of `match_date` (12 to 2022, 3 to 2023, 2 to 2024, 1 to 2025).
- Candidate families: no weighted composite exists; conjunction pairs come only from the fixed list; breaks are reported unused if they do not reproduce across IPL, T20I, LOMO and strictly-prior.
- Convention B: rows with `B_k < bowl_B_early_balls` (12) are flagged and distributions are produced with and without.
- Denominator flags: mutating `extras_type` / `is_legal_ball` of row k leaves every state, par and rank column of row k identical; bowler pressure membership counts wide, Overstep and other deliveries; the legal filter appears only in per-legal-ball denominators.
- `target_basis_unverified`: truth table on a synthetic innings 1 (W < 10, short, no revised field -> true; revised field present -> false; complete -> false; `revised_target` present -> false); the flag does not read `result`; primary chase population excludes it, sensitivity includes it; count reported.
- `exp_remaining`: binned cell value with one observation per innings per bin (first row in the bin); fallback E0 -> E1 -> E2 -> NULL on a synthetic table; `exp_cell_level_used` recorded; strictly-prior variant records its own level and never reads same-day or later matches.
- NULL handling: NULL signals excluded from `V` and counts; `rank_pct` NULL when own signal NULL; `req_to_exp` NULL when `exp_remaining` is NULL or `<= 0`; manifest counters equal the exclusions on a synthetic table.
- Config parity: the set of parameter names in the spec section 8 table equals the key set of `pressure_rules_v1.json` `parameters`; every `basis` is one of the four classes; every ARBITRARY_PLACEHOLDER has a non-empty `sensitivity`.

## G. Responses to review findings

All 16 first-round findings, all 12 second-round findings (6 MEDIUM, 6 NIT) and all 9 third-round findings (6 MEDIUM, 3 NIT) are addressed; the tables are in spec Appendix A, including "Revision 3" and "Revision 4". Third-round placement: finding 1 in B, F and spec 5.3/5.4/7.3/7.4; 2 in B, F and spec 3/7.2/7.6; 3 in C and spec 6; 4 in H and spec 8/11; 5 in F; 6 in D and spec 6; 7 spec Appendix A M5; 8 in B, F and spec 4/9; 9 spec 6 rule 3. One departure: `tau2_floor` is a fraction of `sigma2_within`, so one value serves every outcome stream. Differences from the reviewer's suggested fixes: M4 convention B is projected surplus rather than `-RRR_pct`, because the latter equals convention A in chases; M7 picks the context-only reference baseline and treats per-candidate stratified baselines as sensitivity.

## H. `config/pressure_rules_v1.json` design (Stage 2 creates it; no thresholds chosen)

Structure: `{"config_version": ..., "state_version": "pre_delivery_state_v1", "parameters": {<name>: {"value": ..., "basis": ..., "sensitivity": [...]}}}`. `parameters` keys equal the first column of the spec section 8 table (parity test). Names and initial values:

| Parameter | Value | Basis | Sensitivity |
|---|---|---|---|
| `phase_bounds_L120` | overs 1-6 / 7-15 / 16-20 | EXTERNAL_CONVENTION | death from over 17; powerplay overs 1-5 |
| `phase_fractions` | `(3*L)//10`, `-((-3*L)//4)` | ARBITRARY_PLACEHOLDER | exclude the 48 shortened innings |
| `min_cell_innings` | 30 | ARBITRARY_PLACEHOLDER | 15, 60 |
| `min_prior_innings` | 30 | ARBITRARY_PLACEHOLDER | 15, 60 |
| `par_ball_bin` | 6 | DATA_DERIVED | 3, 12 |
| `exp_brem_bin` | 6 | DATA_DERIVED | 3, 12 |
| `exp_cell_fallback_chain` | E0, E1, E2, NULL | DATA_DERIVED | thresholds via `min_cell_innings`, `min_prior_innings` |
| `wickets_bins` | global merge algorithm | DATA_DERIVED | 4 bins 10-8, 7-5, 4-3, 2-1 |
| `rrr_cap` | none; reported variant p99 | DATA_DERIVED | capped and uncapped side by side |
| `rrr_min_brem_report` | 6 | DATA_DERIVED | none |
| `quantile_grid` | 0.50, 0.60, 0.75, 0.80, 0.85, 0.90, 0.95 | ARBITRARY_PLACEHOLDER | coarse subset; extended top |
| `quantile_grid_by_family` | (a) all seven; (b) all seven, same q; (c) none | ARBITRARY_PLACEHOLDER | coarse 0.50/0.75/0.90/0.95; add 0.975, 0.99 for (a) |
| `par_source_rule` | `L = 120` and complete, other matches only | DATA_DERIVED | none |
| `bootstrap` | seed 20260512; 1,000 eligibility; 500 baseline | EXISTING_RULE / ARBITRARY_PLACEHOLDER | baseline 1,000 |
| `n_eff` | `n_eff_kish`, `n_eff_shrink` | EXISTING_RULE | none |
| `bowl_B_early_balls` | 12 | ARBITRARY_PLACEHOLDER | 6, 18 |
| `break_reproducibility_tol` | 0.05 | ARBITRARY_PLACEHOLDER | 0.025, 0.10 |
| `zero_inflation_share` | 0.05 | ARBITRARY_PLACEHOLDER | 0.02, 0.10 |
| `knee_rule` | max perpendicular distance to first-last chord, min-max normalised axes | ARBITRARY_PLACEHOLDER | x axis by quantile rank |
| `wrem_low_quantile` | `1 - q`, lower-quantile convention | ARBITRARY_PLACEHOLDER | lowest global wickets bin |
| `tau2_floor` | 0.01 x `sigma2_within` | ARBITRARY_PLACEHOLDER | 0.001, 0.1 |

