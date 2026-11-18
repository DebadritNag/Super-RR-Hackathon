# Phase 8 technical design: independent pressure-performance methodology

Authority: `.agents/tasks/phase8_brief.md` and `.agents/tasks/phase8_plan.md` (decisions D1-D16). This document turns them into an implementable design. Where the plan left a choice open, the choice is made here and listed in section 16 if it needs owner confirmation. The technology stack below is locked once this design is approved.

## 1. Overview

Phase 8 builds three genuinely different pressure-performance approaches for batters and bowlers separately, compares them under criteria declared and hashed before any comparison result exists, and submits the best-supported ordered Top 10 per role with honest status labels.

- **A. Context-adjusted performance.** Gradient-boosting expected-outcome models give a pre-delivery expectation for each ball. The player is scored by the intensity-weighted mean of observed minus expected.
- **B. Leverage and Win Probability Added (WPA).** Calibrated win-probability models, explicit attribution rules, and WPA above what leverage alone would predict.
- **C. Pressure Response Index (PRI).** A data-weighted combination of A, B and consistency components with hierarchical shrinkage.

Pressure is a continuous per-delivery intensity in [0,1] (not a percentile slice). The unit of analysis is the player-match record (batter innings or bowler spell), which is the unit for REML, split-half and bootstrap. Phase 6 found no reliable separation of players (pooled odd/even 0.37, median 0.25, 0/48 contexts pass the 0.5 gate, variance at the floor). Phase 8 tests whether continuous intensity, a richer expected-outcome model and match-level units change that. It does not assume they do. The most likely outcome is PROVISIONAL at best for batters and EXPLORATORY for bowlers, and the design makes that outcome a first-class result, not a failure.

### 1.1 Technology stack (locked)

Python 3.11, DuckDB 2.0.0, numpy 1.26.4, pandas 2.2.3, scipy 1.15.2 (REML via `scipy.optimize`), scikit-learn 1.6.1 (`HistGradientBoostingRegressor/Classifier`, `LogisticRegression`, `IsotonicRegression`), joblib, FastAPI + Pydantic v2, pytest, ruff. Frontend: Vite 8, React 19, TypeScript, Tailwind 4, recharts, oxlint. No statsmodels, no xgboost, no new dependencies.

### 1.2 Hard constraints carried into every module

1. `superr.duckdb`, `exploratory.duckdb`, source CSVs and Phase 2-6 reports/tables are read-only. Hashes are compared against `phase8_prehash.json` at the start and end of every script (reuse `app/analytics/integrity.py`).
2. All new tables live in a new file `backend/data/database/phase8.duckdb` (D5) that attaches the two protected databases read-only.
3. TEST (matches from 2026-01-01) is never loaded (D3). Rankings use PRE_TEST (TRAIN to 2024-12-31 plus VALIDATION calendar 2025).
4. Missing is never zero. Restriction register `config/data_quality_restrictions_v1.json` applies at metric level. Super Over innings (3/4 in 34429, 45512, 50359), RULE_INNINGS_3_4 innings in 40725, 48027, 48029, the 42 late-dated T20I matches, OTHER_T20, DLS rows that cannot be reconstructed, and extras of type other/Penalty are excluded or flagged exactly as in `exp_pre_delivery_state` flags.
5. Cricsheet, `matches 2026.csv` and `*_stats2026.csv` are never read by any `app/phase8` module (static-scan test).
6. Batting and bowling statistics are never compared with each other. Every table has a `role` column.

## 2. Data layer

### 2.1 Source and filters

Single source: `exp_pre_delivery_state` (200,999 rows) joined to `p4_match_period` (period), `p4_player_classification` (names), and `superr.deliveries`/`matches` only for result labels and `result`, `win_team_id`, `competition_type`, `match_date`. Loader `app/phase8/data.py::load_pre_test_deliveries(con)` applies, in order:

1. `competition_type IN ('IPL','T20I')` (drops OTHER_T20, `format_out_of_scope`).
2. `period IN ('TRAIN','VALIDATION')`, enforced by `guard_frame` from `app/phase4/lockguard.py` and `assert_no_test_rows`.
3. Exclusion of Super Over and RULE_INNINGS_3_4 innings (innings 3/4 anywhere in scope; a handful of rows).
4. Exclusion of the 42 late-dated T20I matches (`p5_t20i_date_verification`).
5. `dls_exclude_primary = 0` for primary scoring (DLS rows counted in coverage reports, never imputed).
6. Metric-level flags: `den_wicket_flag_anomaly` rows are excluded from wicket targets only; `den_extras_label_unverified` rows are excluded from run targets only. Each exclusion count is written to `p8_data_exclusions` (reason, role, rows, matches).

Feature columns allowed (pre-delivery only): `innings_number, chase_flag, team_runs_before, team_wickets_before, wickets_remaining, legal_balls_bowled_before, innings_limit_balls, legal_balls_remaining, crr, innings_phase, target, runs_required, rrr, gap, projected_surplus, resource_ratio, striker_batting_order, batter_balls_faced_before, batter_runs_before, bowler_legal_balls_before, bowler_runs_charged_before, batting_type, bowling_type, pace_or_spin, competition_type, stage, knock_out`, plus `par_prior` (joined from `p4_par_prior`, NULL when fewer than 30 prior innings), `projected_total = team_runs_before + crr * legal_balls_remaining / 6` (NULL when `legal_balls_bowled_before = 0`), opposition strength (6.3) and pre-match prior (6.3). `par_prior` and `projected_total` are not columns of `exp_pre_delivery_state` (verified); they are derived in `data.py` and are on the feature-guard whitelist. The delivery order key is `innings_ball_num` (there is no `ball_index` column). Columns starting `out_`, `den_`, `post_innings_`, player identifiers, and anything derived from them are label-only. A test asserts the feature list contains no such column and no player id.

### 2.2 Player-match units

`app/phase8/units.py` builds `p8_units` with one row per (role, player_id, match_id, innings) with: format, period, match_date, n_balls (legal balls faced or bowled), sum of intensity `sw`, sum of squared intensity, intensity-weighted sum of residuals per target (`swr_<target>`), mean intensity, balls in intensity tercile 3, phase counts, innings type counts, batting-order group or bowler type, opposition id. Weighted unit mean = `swr / sw`, unit weight = `sw`. A unit with `sw = 0` or no eligible deliveries is not created (never zero-filled).

## 3. Pressure-intensity definitions and validity tests

Intensity `w(d) in [0,1]` is a function of pre-delivery state only. Each candidate is mapped to [0,1] by the empirical CDF of its raw value fitted on TRAIN (stored in `p8_intensity_cdf`), so the scale is comparable across candidates and unaffected by validation data.

| ID | Raw value | Strength | Weakness |
|---|---|---|---|
| P0 | Phase 6 binary `any|q0.75` (reference only, 0 or 1) | Continuity with Phase 6 | Thin slice, discards 75% of balls |
| P1 | Leverage: expected absolute WP swing of the next ball (section 7.4) | Directly tied to outcome stakes | Needs the WP model, innings 1 weaker, partly mechanical with WPA |
| P2 | Decision closeness: `1 - 2*abs(WP - 0.5)` | Intuitive (open game) | Peaks at start of innings 2 when WP is near 0.5 for any ball; ignores stakes of the next ball |
| P3 | Chase difficulty: standardised `gap`, scaled by wickets in hand and balls remaining (`resource_ratio`) | Observable, no model | Innings 2 only |
| P4 | Resource scarcity: `(1 - wickets_remaining/10) * (legal_balls_bowled_before/innings_limit_balls)`; innings 1 uses prior-only par deviation | Both innings | Mixes wickets lost and late phase, which are partly phase effects |
| P5 | Defending difficulty (bowler side): batting side required-rate gap, wickets in hand, phase | Meaningful for bowlers | Correlated with P3 |
| P6 | Composite of passing candidates: first principal component of P1-P5 standardised on TRAIN (no hand weights); built only if each input passes alone and the composite is not worse on tests (a)-(e) | Uses all evidence | Harder to explain |

For batters the intensity is evaluated from the batting side, for bowlers from the fielding side. P5 is bowler-specific, the others apply to both with the same value for a delivery.

### 3.1 Validity tests (predeclared; computed on TRAIN, confirmed on VALIDATION; neither period used to pick names)

For each candidate, split deliveries into intensity deciles (ten equal-count bins on TRAIN edges), by innings (1, 2) and phase (powerplay, middle, death):

- (a) Scoring direction: runs per legal ball minus the intensity-free phase baseline is lower in decile 10 than decile 1 by more than the bootstrap (match-cluster, 500 draws) 95% half-width.
- (b) Wicket probability higher in decile 10 than 1, same interval rule.
- (c) Variance of runs per ball higher in decile 10 than 1.
- (d) Mean absolute WPA larger (reported for P3-P5 and P0; for P1 and P2 it is mechanical and flagged `MECHANICAL`, not counted).
- (e) Monotonic trend: Spearman correlation between decile index and the decile statistic at least 0.7 for (a) (sign-adjusted) and (b).
- (f) Inter-candidate correlation matrix (Spearman) reported.
- (g) Coverage: tests run for both innings and the three phases; cells with fewer than 2,000 deliveries are reported `NOT_ESTIMABLE`.

A candidate PASSES if (a), (b), (e) hold in the pooled sample on TRAIN and the same signs hold on VALIDATION, and passes in at least 2 of the 3 phases. The primary definition is the passing candidate with the highest count of passed tests among (a)-(e), then widest innings coverage, then lowest id. P6 competes on the same terms. Candidates are never evaluated on who they rank. Innings-1 rule (predeclared in the criteria file): P3 and P5 are innings-2 only. If the primary candidate has no valid innings-1 value (innings-2-only candidate, or P1/P2 whose W1 fails its gate in 7.2), innings-1 intensity is taken from the best-passing both-innings candidate (P4, then P6). If none passes, innings-1 deliveries get `w = NULL` and are excluded from pressure units (counted in `p8_data_exclusions`), and the Top 10 is stated to cover innings-2 pressure only. If a both-innings candidate passes for innings 1 on the tests, it is used and an innings-2-only sensitivity is reported alongside. Unit counts, eligibility and exposure are computed after this rule is applied. Results: `p8_intensity_tests`, `p8_intensity_corr`, report section "definitions tested".

## 4. Predeclared criteria, hashing and run-order enforcement

### 4.1 Files

- `backend/config/phase8_selection_criteria_v1.json`: the criteria (canonical JSON, sorted keys, UTF-8, trailing newline).
- `backend/data/reports/phase8_selection_criteria_hash.json`: `{criteria_sha256, git_blob_sha1, config_file_sha256, written_at, version}`.
- `p8_run_log` in `phase8.duckdb` (append-only): seq 1 is the `plan` row holding the criteria hash.

### 4.2 Contents of the criteria file (all fixed before any result)

- Status thresholds (section 9) and eligibility floors (section 10).
- Evidence classes, approach-independent functions of (interval, eligibility multiple `m = n_matches / min_matches`, consistency share `cs` = share of pressure units with positive residual, dispersion `disp` = between-unit SD relative to cohort), evaluated in this order, first match wins: `INSUFFICIENT` (below eligibility floor); `INCONSISTENT` (`cs < 0.5`, or `disp` above the cohort 75th percentile with positive mean); `STRONG_SUBSTANTIAL` (`ci_low > 0` and `m >= 2` and `cs >= 0.5`); `STRONG_LIMITED` (all other eligible players: observed estimate above the cohort 80th percentile with interval including 0 or `1 <= m < 2`); `NONE_OF_THE_ABOVE` is not allowed, so any remaining eligible player is `STRONG_LIMITED` only if above the 80th percentile, else `UNCLASSIFIED_LOW`. The brief's four classes are exhaustive for ranked players (Top 10 rows are always above the 80th percentile or already classed).
- Innings-1 intensity fallback rule (section 3.1) and the rank driver and baseline definitions (6.2).
- Reliability minimum player counts (section 5).
- Tie rule: `|diff| < 1e-12` only (section 12).
- Intensity validity tests and pass rule (section 3.1).
- Approach comparison rule (section 8.4): metrics, minimum differences, tie-break order.
- Ranking rules: posterior mean descending, tie-break `player_id` ascending, bootstrap 1000 draws, seed 20260512, Top-10 inclusion probability and 95% rank interval.
- Models: hyper-parameter grids and the single selection metric (validation log loss for classifiers, validation RMSE for regressors; one selection pass, no repeats).
- Splits: reference to `config/phase4_split_v1.json` content hash; TEST never opened.
- Forbidden inputs: player identity, player rank, score level, Top-10 membership, nationality, capped status, TEST outcomes, Cricsheet.
- Phase 6 data-weight gate 0.5 reported unchanged.
- `declared_before_any_result: true`.

### 4.3 Mechanism (reuse Phase 6, `app/phase8/criteria.py`)

Same API as `app/phase6/criteria.py`: `write_criteria()` (idempotent; refuses to rewrite different content once a hash file or run-log row exists), `verify_criteria()` (raises `CriteriaError` if the file hash differs from the hash file or log, if seq 1 is missing, or if `forbidden_hits` finds forbidden wording outside the `forbidden_inputs` list), `begin_step(step)` (calls `verify_criteria`, appends a run-log row). Every analysis entry point (`intensity`, `expected`, `winprob`, `approach_*`, `reliability`, `stability`, `ranking`) calls `begin_step` as its first statement. Procedure, executed in chunk 1 before any module that produces a comparison result is run:

1. Write the JSON file; compute `sha256` of the canonical bytes and the git blob SHA-1.
2. Write the hash file and run-log seq 1.
3. Commit-order check: a test asserts the hash file mtime and run-log `ts` precede every row in `p8_*` result tables (`p8_intensity_tests` onward) by `ts`.
4. Any later change of the file makes every step fail with `CriteriaError`. A needed change goes in a new versioned file (`_v2`) with a new log row and a recorded reason. It is never an overwrite.

Result tables carry `criteria_sha256` and `run_seq` columns so every number is traceable to the hash.

## 5. Splits and TEST lock

- Reuse `config/phase4_split_v1.json` unchanged: TRAIN to 2024-12-31, VALIDATION 2025, TEST 2026+. Matches never straddle partitions (assert on match_id uniqueness per period).
- Model fitting (WP models, expected-outcome models, scalers, intensity CDFs, par priors, team priors): TRAIN only. Hyper-parameter choice: one pass on VALIDATION by the predeclared metric. No refit on TRAIN+VALIDATION (a refit would remove the out-of-sample property for VALIDATION; this is the safest choice).
- Scoring: VALIDATION deliveries scored out-of-sample by the TRAIN-fit models. TRAIN deliveries scored by 5-fold out-of-fold predictions grouped by `match_id` (fold = `match_id % 5`, deterministic, never Python `hash`), so no ball is scored by a model that saw its match. This OOF scheme applies to every fitted component, not only the expected-outcome models: W1, W2, the WPA-on-leverage regression and the intensity CDFs (CDF for a TRAIN delivery uses the fold's training part). Fold models differ from the full-TRAIN model that scores VALIDATION; this is accepted and stated in the report. Test: a TRAIN delivery's WP and expected values come from a model whose fit data excludes its match. Player records in rankings use both periods.
- Out-of-time validation: fit player estimates on 2022-24 units, correlate with player estimates on 2025 units (players with both, at least the per-window floor in both: the full floor in 2022-24 and `min_matches_2025 = 4` in 2025, declared before results). Criteria keys `min_players_out_of_time: 30` and `min_players_split_half: 30`. Below that count the criterion is `NOT_ESTIMABLE` and the list cannot be PROVISIONAL or VALIDATED (it is EXPLORATORY).
- TEST lock: `app/phase8/lockguard.py` wraps Phase 6 `assert_no_test_rows` and `assert_lock_state_unchanged`; Phase 4 lock log sha256 (`cae1e06c...d75c`) is checked at start and end of each script. `evaluate_on_test` is never imported by phase8 modules (static-scan test). Phase 4 TEST aggregates, if mentioned, are quoted from `phase4_test_evaluation.json` as "previously accessed, non-pristine". A TEST-period descriptive application needs owner authorisation (OD-P8-1) and is out of this design.

## 6. Shared building blocks

### 6.1 Expected-outcome models (used by A and B)

`app/phase8/expected.py`. Targets and learners:

| Target | Role | Learner |
|---|---|---|
| runs off bat (0-6) | batter | HistGradientBoostingRegressor |
| runs charged to bowler (bat runs + wides + no-balls) | bowler | HistGradientBoostingRegressor |
| dismissal of striker (any dismissal) | batter | HistGradientBoostingClassifier |
| bowler-credited wicket | bowler | HistGradientBoostingClassifier |
| dot (0 runs off bat and no charged extra), boundary (4 or 6 off bat) | both | HistGradientBoostingClassifier |

Population: eligible legal-ball deliveries of the target (wides/no-balls are not legal balls; for batter targets they are excluded, for the bowler charged-runs target they are included as additional charged runs with no legal ball counted, see 6.2). Fixed hyper-parameters grid declared in the criteria: `max_depth in {3,5}`, `learning_rate in {0.05,0.1}`, `max_iter` 200 with early stopping on a TRAIN-internal grouped holdout, `l2_regularization in {0,1}`, `min_samples_leaf 200`. Seed 20260512. Monotonic constraints not used (documented). Calibration for classifiers: isotonic on the TRAIN-internal holdout; checked by decile calibration on VALIDATION.

Leakage controls: features restricted to 2.1; player ids excluded so the model cannot absorb player skill (otherwise residuals would remove the signal); opposition and prior features computed from strictly earlier matches (4.4, 6.3). Tests: truncation test (delete all later rows of an innings and the prediction for ball t is identical), mutation test (change future runs and results; identical prediction), model-fit-only-on-TRAIN test (fit data match ids all in TRAIN), and a feature-name guard.

Metrics against baselines on VALIDATION: constant mean, the Phase 4 B0 cell baseline, and a phase-and-wickets lookup; RMSE/MAE for regressors, log loss and Brier for classifiers, decile calibration, calibration slope and intercept. The model is kept only if it beats the constant on the primary metric; otherwise A uses the best baseline and the report says so (the Phase 7 finding was under 1% RMSE gain for B0, so a small gain is expected and is reported as is).

Artefacts: `backend/data/models/p8_expected_<target>_v1.joblib` and `.json` metadata (algorithm, version, training period, match count, delivery count, feature list, target, metrics, data hash, seed, timestamp, criteria hash).

### 6.2 Residual definition, normal baseline and pressure delta

For a legal ball with expected `e` and observed `o`, residual `r = o - e` (or `o - p` for 0/1 targets). Wides and no-balls: bowler charged-runs residual includes extras with expected extras estimated by the same model class on all deliveries (target charged runs per delivery); batter targets skip them. Extras of type other/Penalty are excluded (register). Missing expected value gives no residual (row dropped and counted).

Player-level definitions (per role, target and format; all use the same targets and expected-outcome models):

```
normal_baseline_i = unweighted mean residual of player i over deliveries with intensity < 0.5
pressure_perf_i   = intensity-weighted mean residual over deliveries with intensity >= 0.5   (continuous-weight value over all deliveries also reported)
pressure_delta_i  = pressure_perf_i - normal_baseline_i   (SE from the match-cluster bootstrap)
```

The cut 0.5 is the median of the intensity CDF, so it is definition-independent. Residuals are context-adjusted by the player-blind model, so `pressure_perf` alone still contains the player's overall quality. Rank driver (predeclared): the primary ranking is by `pressure_perf` (REML-shrunk or UNSHRUNK per 6.4); `normal_baseline` and `pressure_delta` are reported columns in the Top 10 CSV, `p8_estimates` and the explanations, and a sensitivity ranking by `pressure_delta` is in the sensitivity grid. The limitation "overall quality confounds pressure performance" is stated in the methodology report.

### 6.3 Context features that need history

- Opposition strength: team rolling points-per-match-style rating (win rate with prior 5 matches shrunk to 0.5) from matches strictly before `match_date` (same-day rule `EXCLUDE_SAME_DATE`, as in `p4_par_prior`); insufficient prior history gives NULL and the feature is treated natively by HistGradientBoosting (missing never zero).
- Pre-match prior: batting-side prior win rate from earlier matches, same rule.
- Innings-1 par: `p4_par_prior` (min 30 prior innings; otherwise NULL and flag).

### 6.4 REML estimation (`app/phase8/reml.py`)

For a player i with units j: `y_ij = mu + u_i + e_ij`, `u_i ~ N(0, tau^2)`, `e_ij ~ N(0, sigma^2 / w_ij)` where `y_ij` is the unit weighted mean residual and `w_ij` its intensity weight (`sw`), with a cluster-level sigma estimated from within-player between-unit variation (this is the match-cluster correction). Parameters `(mu, tau^2, sigma^2)` by REML via `scipy.optimize.minimize` (L-BFGS-B on log variances, analytic profile of `mu`). Fits per (role, format, target). Variance estimators: `tau^2` is allowed to be 0 and is reported as such with `FLOOR` flag when `tau^2 < 1e-8 * sigma^2`; there is no externally imposed floor and no gate-driven change. When `tau^2 = 0`, the posterior collapses to `mu` and the cell is labelled `NO_BETWEEN_PLAYER_SIGNAL`; this finding is reported and propagates to the status label. Because Phase 6 found the floor in 48 of 48 contexts, this is the expected case and has its own rules. (i) Reliability (split-half, ICC, out-of-time) is always computed on UNSHRUNK precision-weighted unit means `ybar_i = sum(sw*y)/sum(sw)`, never on posterior means. (ii) Ranking rule: if `tau^2 = 0` (FLOOR) for the primary cell, players are ranked by unshrunk `ybar_i` among eligible players, `rank_basis = UNSHRUNK_FLOOR`, list status forced to EXPLORATORY, and the banner reads: "between-player variance not distinguishable from zero; ordering reflects observed means with high noise". (iii) The `player_id` tie-break applies only to exact numeric ties (`|diff| < 1e-12`) and is never the ordering mechanism. (iv) This changes only the ranking basis when the floor binds; other cells keep shrinkage. Both orderings (posterior and unshrunk) are reported in `p8_sensitivity`. Posterior: `theta_i = mu + B_i (ybar_i - mu)`, `B_i = tau^2/(tau^2 + sigma^2/W_i)`, `SE_i = sqrt(B_i sigma^2/W_i)`. Phase 4 `shrink.py` is not modified. A comparison table reports the REML posterior beside the Phase 4 estimator for the same data (no switch to Phase 4 to pass a gate).

### 6.5 Bootstrap

Seeded match-cluster bootstrap (`app/phase8/stability.py`): resample match ids with replacement within period strata (seed 20260512, 1000 draws), recompute unit sums, refit REML with `tau^2` fixed at the full-sample value for speed in ranking draws (documented approximation). Pass criterion: a 200-draw full-refit check must give Top-10 inclusion probabilities within 0.05 of the fixed-tau^2 values for players with p >= 0.1; otherwise the full refit is used for the final ranking, derive posterior estimates, ranks, Top-10 inclusion probability, 95% rank interval (2.5/97.5 percentiles), and 95% estimate interval. Ties broken by `player_id` ascending in every draw.

## 7. Approach designs

### 7.1 Approach A: context-adjusted statistical performance

Targets and components (batters): runs above expected per ball (reported also as strike-rate difference), boundary contribution above expected, dot avoidance (negative of dot rate above expected), dismissal risk above expected (negative). Bowlers: runs charged above expected (negative is good), bowler-credited wicket above expected, dot generation above expected, boundary prevention above expected. Direction is oriented so that positive is better; the sign convention is stored in `p8_component_defs`.

Attribution: each delivery belongs to the striker (batter components) and the bowler (bowler components) only. Wicket targets credit the bowler only for bowler-credited dismissals (`den_bowler_credited_wicket = 1`). Run-outs and other non-credit dismissals count as dismissal events for the batter (dismissal risk) but never as bowler wickets.

Weighting: unit weight is the sum of intensity `w`; expected values pre-delivery only. Primary component for ranking within A: a batter's runs-above-expected and dismissal-risk components are combined into one A score by inverse-variance weighting after standardising each by its REML `sigma`; weights fixed from TRAIN and reported; the bowler A score likewise (charged runs, wicket). Boundary and dot components are reported but not in the A score (they overlap runs). Shrinkage: REML (6.4) per component, then precision-weighted combination with covariance ignored but reported correlation of components. Context: batting order group, phase, wickets, balls remaining, RRR in chases, innings, competition, opposition strength, pace/spin and bowling type (features, 6.1). Unit: player-match (batter innings, bowler spell = bowler's legal balls in the innings). Bootstrap: 6.5.

### 7.2 Approach B: leverage and WPA

Models (`winprob.py`):
- W2 (innings 2): `HistGradientBoostingClassifier` on `runs_required, legal_balls_remaining, wickets_remaining, rrr, crr, gap, resource_ratio, innings_limit_balls, competition_type, pre-match prior`; target: chasing side wins (decisive matches only).
- W1 (innings 1): same learner on `team_runs_before, wickets_remaining, legal_balls_remaining, crr, projected_total, par_prior (NULL handled natively; a derived `par_deviation_prior = projected_total - par_prior` only when `par_prior` is not NULL), competition_type, pre-match prior`; target: batting side eventually wins. A secondary expected-final-score formulation is used as a feature check only.
- Baselines: constant prior; logistic regression on `resource_ratio` (innings 2) and on projected total (innings 1).
- Labels: label = 1 or 0 (batting side won) only if `win_team_id IS NOT NULL` AND `result` does not match the case-insensitive regex `super over|eliminator|tied|tie\b|no result|abandon|d/?l|dls` AND `revised_target IS NULL`. Everything else (ties, Super Over and eliminator decisions, no results, abandoned, DLS or D/L strings, DLS-revised targets, excluded matches) is listed in `p8_wp_label_exclusions` with the matched reason and never imputed; a Super Over winner is never labelled a regulation winner. `result_status` values are enumerated by `data.py` on load, written to the report, and not used as a filter. Counts per reason are recorded in the report. A unit test runs the regex on synthetic result strings ("Match Tied", "won the Super Over", "Tied with DC won the Super Over", "Won the one over Eliminator", "No Result", "Match Abandoned", "(DLS Method)", "(D/L method)", plain "X won by 5 wickets").
- Calibration (`calibration.py`): reliability curve, ten-decile table, Brier, log loss, calibration slope and intercept (logistic recalibration), all on VALIDATION; function unit-tested on synthetic data with known calibration.
- Innings-1 gate (declared): W1 is used in primary WPA only if validation calibration slope lies in [0.8, 1.2] and Brier improves at least 2% over constant. Otherwise innings-1 WPA is reported `NOT_RELIABLE` and excluded, and B is innings 2 only (stated in the report and status, never fabricated).

WP timeline: `WP_before(t)` is the model on the state before ball t. `WP_after(t) = WP_before(t+1)` of the same innings (from the next row's pre-delivery state); the terminal ball uses the match result label (1 or 0) for the batting side. Innings 1 to 2 transition: the innings-1 terminal WP is the W2 output at the first ball of innings 2 transformed to the innings-1 batting side (`1 - WP2`); there is no separate label leakage because it is the pre-delivery model output. WP is clipped to [0.005, 0.995] before differencing.

Attribution (D12):
- Runs off the bat and boundary events: striker credit `+WPA`, bowler credit `-WPA` for the portion not from extras.
- Wides and no-balls: charged to the bowler; the ball's WPA goes to the bowler as `-WPA` (extras help the batting side), no striker credit except runs off the bat on a no-ball.
- Byes and leg-byes: attributed to the batting side collectively; no striker or bowler credit (`TEAM_ONLY`).
- Bowler-credited wicket: bowler gets `-WPA`, dismissed batter gets `+WPA` (negative for the batter).
- Run-out and other non-credit dismissals: the dismissed batter takes the batting-side delta; the bowler gets no credit and no blame; fielding credit is not modelled. On a run-out ball that also has runs off the bat, the striker keeps the WPA share of the runs off bat (by the expected-share rule below) and the remainder, i.e. the wicket share, goes to the dismissed batter (the striker when he is the one out, otherwise the non-striker). A unit test covers this and the no-ball plus bat-runs split.
- Retired hurt, retired out, obstructing the field, timed out, handled ball: excluded and counted in `p8_wpa_excluded_events`.
- Decomposition for a ball with both bat runs and extras (no-ball plus bat runs): split by expected-value shares computed from the A model (documented rule), never by outcome.

Pressure vs leverage vs impact: leverage `L(t)` is the pre-delivery expected absolute WP swing of the next ball, `L = sum_k p_k |WP(state_k) - WP_before|` over seven outcome classes (dot, 1, 2, 3, 4, 6, wicket) using class probabilities from the A models and `state_k` obtained by applying the class to the pre-delivery state (innings-2 deterministic transitions). Pressure intensity (section 3) is a separate object and WPA is realised contribution; the report never equates high WPA with pressure.

Player-level B metrics: leverage-weighted WPA per opportunity `sum(L*WPA)/sum(L)`; and WPA above leverage expectation: unit-level regression `WPA_ball = a + b L + c phase + d A-expected-runs + e` fitted on TRAIN, the residual is the B score input. Unit and REML as in 6.4. Leakage tests as in 6.1 for WP, plus truncation of the match after ball t leaves `WP_before(t)` unchanged and mutation of the result label leaves all `WP_before` unchanged (only terminal-ball `WP_after` may change).

### 7.3 Approach C: Pressure Response Index (PRI)

Components per role (all REML-shrunk with SE): 
1. `A` : the A score (7.1).
2. `B` : the B score (7.2), innings 2 only if W1 fails the gate.
3. `K` : consistency: share of the player's pressure units with positive intensity-weighted residual (shrunk toward 0.5 by Beta-binomial empirical Bayes), and between-unit dispersion (not scored directly; reported).
4. Exposure (mean intensity and count) is reported and used only as a precision input, never as a score.

Weights are derived from data, not chosen: (i) per component, split-half reliability `r` (odd/even match parity, Spearman-Brown) on TRAIN gives noise-aware weight `w_c = r_c/(1 - r_c)` for `r_c in (0,1)` (non-positive reliability gives weight 0 and the component is reported as `NO_SIGNAL`); (ii) if any pair of components has Spearman correlation > 0.5 on TRAIN-parity half 1, PCA on standardised components; first-component loadings define the combination and loadings are reported (otherwise the weighted sum with `w_c` normalised); (iii) weights are fitted ONLY on TRAIN odd-parity matches; C's selection reliability (8.4) is computed only on held-out data (even-parity plus VALIDATION). A and B have no tuned weights beyond the fixed TRAIN inverse-variance weights, which are also fitted on odd-parity TRAIN and evaluated on held-out data, so all three are judged the same way. (iv) If a component has `tau^2 = 0`, set `w_c = 0` and flag `NO_SIGNAL` (the standardisation `z_c` would divide by zero). (v) If `r_c >= 1`, clip to 0.99. If all components get weight 0 PRI is `NOT_DEFINED` and not produced. PRI is `sum_c w_c z_c` where `z_c` is the component's shrunk estimate divided by its between-player SD; SE by propagation from the component SEs with component covariance from the bootstrap. Final shrinkage: REML on PRI-unit scores is not applied again (components already shrunk); instead the bootstrap provides intervals, and players with insufficient evidence are classed.

Evidence classes are defined once in 4.2 as approach-independent functions and apply to A, B and C alike. PRI is an observable-performance index, not a psychological score.

### 7.4 Leverage computation detail

Computed in chunk 2 on every eligible delivery using W-models and the A class-probability models; stored in `p8_delivery_leverage` (match_id, innings, innings_ball_num, leverage, wp_before). Leakage tests: leverage unchanged under truncation and under future-row mutation.

## 8. Comparison and approach selection

### 8.1 Opposition and fairness strata

Strata reported for every approach: IPL vs T20I, batting-order group (1-3, 4-5, 6+), phase, pace vs spin (bowlers: pace/spin; batters: runs against each), opposition strength tercile, innings. Volume-bias check: Spearman of player estimate with exposure; a significant positive correlation (> 0.3) is flagged as `VOLUME_BIAS`.

### 8.2 Metrics for the methodology comparison (`methodology_comparison.md`)

Per approach and role: split-half (match parity, and early/late by date) Spearman-Brown with bootstrap interval, ICC(1) of unit means, between-player variance over noise (`tau^2 / (sigma^2/Wbar)`), out-of-time rank correlation (2022-24 to 2025), bootstrap Top-10 inclusion probability concentration (number of players with probability >= 0.5) and median rank interval width, top-10 overlap across definitions (P1-P6), windows, formats and floors, predictive quality on VALIDATION (expected-outcome RMSE/log loss vs baselines; WPA model Brier), explainability score from a predeclared checklist (inputs observable, no latent factor, plain-language statement possible; 0-3), format fairness (cross-format correlation and format residual size). The Phase 6 data-weight gate (0.5) status is reported for each approach unchanged.

### 8.3 Reliability procedures (`reliability.py`)

- Split-half by match parity: odd/even match order within player by date; each half scored by the same pipeline with REML parameters estimated on the full sample (not per half) to avoid mismatch; half estimates are the UNSHRUNK precision-weighted unit means (6.4), so the correlation is defined when `tau^2 = 0`; correlation of half estimates over players eligible at half the floor in both halves; Spearman-Brown `2r/(1+r)`; Fisher-z pooling over strata; match-cluster bootstrap for the interval (1000 draws).
- Split-half by time: early (first half of each player's matches) vs late; reported separately because it mixes skill change.
- ICC(1) of unit means per role-format from one-way random effects on units with at least 2 units; reported with bootstrap interval.
- Calibration of estimates: slope of late-half observed on early-half posterior; the Phase 6 over-shrinkage slope result (1.9-3.4) is the comparison point.
- Phase 6 gate: share of contexts with data weight above 0.5, computed with the Phase 6 definition on the Phase 8 REML output, reported as is; not used for labelling.

### 8.4 Selection rule (predeclared)

Per role: choose the approach with the highest lower 95% bound of pooled split-half (parity) Spearman-Brown reliability; if `lower_bound_best - lower_bound_other < 0.05` (comparing lower bounds only), choose by higher out-of-time correlation lower bound; then by higher Top-10 inclusion concentration; then by explainability; then by id order A, B, C. If no approach has a positive lower bound, the role's list is EXPLORATORY and the approach with the highest point estimate is submitted with that stated. The batter and bowler choice may differ. The rule uses no player identity or rank (verified by `forbidden_hits` and a test that the selection function receives only metrics).

## 9. Reliability thresholds and status labels

### 9.1 Thresholds (declared in the criteria file)

- `0.5` PROVISIONAL, `0.7` VALIDATED, on split-half (parity) Spearman-Brown reliability of the submitted approach's player estimates for the role.
- Interval requirement: VALIDATED needs bootstrap lower bound >= 0.5; PROVISIONAL needs lower bound > 0.
- Out-of-time requirement: VALIDATED needs out-of-time Spearman lower bound > 0.3; PROVISIONAL needs lower bound > 0.
- The Phase 6 0.5 data-weight gate is reported unchanged and is not an input to labelling. It is stated separately.

### 9.2 List-level status (exactly one)

- `VALIDATED`: all VALIDATED requirements met, and the W1 gate satisfied or the approach uses innings 2 only with that stated.
- `PROVISIONAL`: PROVISIONAL requirements met, VALIDATED not met.
- `EXPLORATORY`: an ordered list is producible but PROVISIONAL requirements are not met (including every `tau^2 = 0` cell, which is forced to EXPLORATORY with `rank_basis = UNSHRUNK_FLOOR`); the reason is a column.
- `INSUFFICIENT_EVIDENCE`: fewer than 10 players meet eligibility, or the approach cannot be computed; list shorter than ten with a shortfall note and a separate labelled candidate pool.

### 9.3 Row-level status (exactly one)

- A row's status never exceeds the list status. `INSUFFICIENT_EVIDENCE` if the player is below the eligibility floor at any required scale (never the case for rows in the Top 10 list; rows that fail are not ranked, they appear in the candidate pool).
- `VALIDATED` row: list VALIDATED and player's evidence class `STRONG_SUBSTANTIAL` and Top-10 inclusion probability >= 0.5.
- `PROVISIONAL` row: list at least PROVISIONAL and inclusion probability >= 0.25.
- Otherwise `EXPLORATORY`.
- A separate `ranking_status` (submitted ranking status) and `model_validation_status` (list status of the approach) are both columns, so the submitted order's status and the model's validation status are distinct as required.

Explicit wording files: `config/phase8_status_labels_v1.json` with definitions text used by API, UI and reports (single source).

## 10. Eligibility rules

Fixed in the criteria file before results; derived from Phase 4/6 frozen values (`phase4_eligibility_frozen.json`, `pressure_eligibility_rules_v1.json`) and not tuned on results.

Numbered rules; each threshold is a named key in the criteria file. All must hold in the format being scored.

1. `min_matches = 8` distinct matches.
2. `min_effective_n = 60`: Kish effective count `sum(w)^2/sum(w^2)` over the player's deliveries is at least 60 (additional to rules 3-5; plain `sum(w)` is also stored).
3. Batter: `min_balls_faced = 60` legal balls in PRE_TEST in that format.
4. Bowler: `min_balls_bowled = 72` legal balls in PRE_TEST in that format.
5. `min_high_intensity_units = 8`: innings or spells with at least one legal ball at intensity >= 0.5. The 0.5 cut is the median of the intensity CDF, so this rule does not depend on which definition is primary and is known when the criteria file is hashed.
6. Combined list: eligibility is evaluated on combined totals. In the common-effect combination (section 11), only formats with at least half the floor (rules 1-5 at 0.5x) enter `u_i`; a format below that is shown as `LOW_FORMAT_EVIDENCE` and enters only through its own precision weight, which down-weights it automatically.
- Sensitivity floors: 0.5x and 2x; results go to the sensitivity table, not to the submitted list.
- Players failing the floor are `INSUFFICIENT_EVIDENCE`; exclusion reasons use actual counts (never "poor performer").

## 11. IPL and T20I combination study

1. Per-format estimates (REML, 6.4) for each approach/role.
2. Cross-format correlation: Spearman and Pearson (precision-weighted) over players with both formats and at least the floor in both; bootstrap interval; also a disattenuated correlation with the estimate reliabilities.
3. Hierarchical model: `theta_i,f = mu_f + u_i + v_i,f`, with `u_i` common effect, `v_i,f` format deviation; estimated by REML on the stacked units with format as fixed effect; precision weights follow from the variance components (no fixed 70:30).
4. Decision rule (predeclared): combine if the cross-format correlation lower 95% bound is at least 0.3 and at least 30 players have both formats; the common effect `u_i` posterior drives the combined ranking. Otherwise the submitted list is the precision-weighted combination for players with both formats shown with each format's contribution and single-format players ranked by the single-format estimate, with `FORMAT_COMBINATION_UNSUPPORTED` flag and a separate IPL-only and T20I-only list in the evidence file. The submitted CSV always states the basis in a column `combination_basis`.
5. Combined ranking vs IPL-only vs T20I-only: Spearman and Top-10 overlap reported in `p8_format_study`.

## 12. Ranking, outputs and explanations

`ranking.py`: rank = descending posterior estimate of the chosen approach per role; when `rank_basis = UNSHRUNK_FLOOR` (6.4) rank by unshrunk precision-weighted mean; `player_id` ascending only for exact numeric ties (|diff| < 1e-12). Output files in `backend/data/reports/`:

- `pressure_batters_top10.csv`, `pressure_bowlers_top10.csv`, JSON twins, with columns: `rank, player_id, player_name, primary_methodology, pressure_score, normal_baseline, pressure_delta, rank_basis, score_a, score_b, score_c_components, pressure_matches, pressure_innings_or_spells, pressure_deliveries, mean_intensity, ipl_contribution, t20i_contribution, combination_basis, interval_low, interval_high, top10_inclusion_probability, rank_interval_low, rank_interval_high, evidence_class, short_explanation, ranking_status (row), model_validation_status (list), eligibility_flags, data_quality_flags, methodology_version, data_version_hash, criteria_sha256, generated_at`. Unavailable values are empty with a flag, never zero.
- `pressure_top10_status.md` (banner and definitions; old file copied to `_phase7_obsolete` first).
- `player_selection_explanations.md`: per selected player pressure situations (counts by phase and innings type, mean intensity), observed vs expected and difference, component breakdown, share of matches positive and dispersion, evidence amount, rank under A, B, C, IPL-only, T20I-only, combined, limitations, and "why this position relative to neighbours" using interval overlap statements; ranks 11-20 and high raw-statistics non-selected players with data-based exclusion reasons from a fixed reason set: `BELOW_ELIGIBILITY_FLOOR (counts)`, `INTERVAL_OVERLAPS_BUT_LOWER_POSTERIOR`, `LOW_TOP10_INCLUSION_PROBABILITY`, `ONE_FORMAT_ONLY_LOW_EVIDENCE`, `INCONSISTENT_ACROSS_MATCHES`, `HIGH_RAW_BUT_NEGATIVE_AFTER_CONTEXT_ADJUSTMENT`. Never a negative performance claim from missing evidence.
- Descriptive profiles regenerated by `app/phase7/descriptive.py` (D2), no composite or rank.
- Determinism: two consecutive runs produce identical SHA-256 digests of all outputs (excluding `generated_at`, which is held in a separate manifest row).

## 13. AI/ML pipeline verification

`app/phase8/ai_verify.py` checks and records: artefacts exist (`backend/data/models/*.joblib` and `.json`), loaded estimator class, training reproducibility (retrain with fixed seed and compare predictions on a fixed 10,000-row sample within 1e-9), validation metrics vs baselines, prediction pathway uses the artefact (monkeypatch test), features real (list from metadata equals columns present in the DB), no hardcoded/mock player data (static scan of `backend/app` and `frontend/src` for player-name literal lists, ranking arrays, `Math.random` scores; allowed only in tests and listed in the audit table), target appropriateness statements, TEST not used. Writes `ai_pipeline_verification.md` (old copied to `ai_pipeline_verification_phase7_aborted.md` first). Technical success is stated separately from reliability. Experimental predictions are a real player-level model, not a re-ranking of residuals. Target: a player's intensity-weighted residual (`pressure_perf`, primary target) in 2025, predicted from 2022-24 player features only (shrunk and unshrunk pressure and baseline estimates, exposure, mean intensity, format mix, role group) by a ridge regression (`sklearn.linear_model.Ridge`, alpha chosen by grouped CV within 2022-24 only). It is evaluated out-of-time against a naive carry-forward baseline (2022-24 estimate used as the 2025 prediction) and the league-mean baseline, by RMSE and Spearman on players meeting the 2025 floor (`min_players_out_of_time` applies; below it the predictions are not produced and the page shows the verification only). Predictions come from a model fitted on 2022-24 and applied to 2022-24 features for the 2025 window as the evaluation, and the shipped list uses the same fitted model with features through 2025 (no refit, no TEST). Output rows (`experimental_ai_top10_batters.csv`, `experimental_ai_top10_bowlers.csv`) carry `status = EXPERIMENTAL_NOT_VALIDATED`, the measured out-of-time metrics and the baseline comparison; they are served only from the token-protected internal endpoint and never merged into the submitted lists. If the model does not beat carry-forward, that result is reported and the CSVs are marked `NO_PREDICTIVE_GAIN`.

## 14. Module layout

```
backend/app/phase8/
  __init__.py
  constants.py      seeds, paths, table names, TEST/forbidden lists
  criteria.py       predeclaration, hashing, begin_step, verify_criteria
  store.py          phase8.duckdb access, p8_run_log append-only, attach read-only
  lockguard.py      TEST guards, lock-state checks, prehash checks
  data.py           pre-test loader, exclusions, feature whitelist
  units.py          player-match units
  intensity.py      P0-P6, CDFs, validity tests
  expected.py       expected-outcome GBMs, OOF scoring, artefacts
  calibration.py    reliability curves, Brier, log loss, slopes
  winprob.py        W1/W2, WP timeline, leverage
  wpa.py            attribution rules
  reml.py           REML random effects
  approach_a.py  approach_b.py  approach_c.py
  reliability.py    split-half, ICC, Spearman-Brown, gate report
  stability.py      match-cluster bootstrap, inclusion probabilities
  combination.py    IPL/T20I study
  selection.py      predeclared approach selection
  status.py         list/row status rules
  ranking.py        Top 10 construction
  explain.py        per-player evidence and exclusion reasons
  reports.py        generated Markdown/CSV/JSON
  serving.py        read layer for the API
  ai_verify.py      pipeline verification
backend/app/api/v1/routes_submission.py   public /api/v1/submission/*
backend/app/schemas/submission.py         Pydantic v2 models
backend/app/services/submission_service.py
backend/scripts/phase8_{criteria,data,intensity,winprob,expected,approach_a,approach_b,approach_c,compare,rank,reports,ai_verify}.py
backend/scripts/run_phase8.py             orchestrator (calls scripts in order, verifies hashes)
backend/config/phase8_selection_criteria_v1.json
backend/config/phase8_methodology_v1.json
backend/config/phase8_status_labels_v1.json
backend/data/models/p8_*.joblib, p8_*.json
backend/data/database/phase8.duckdb
```

### 14.1 p8_* table schemas (in `phase8.duckdb`; each result table also has `criteria_sha256 VARCHAR, run_seq INTEGER, generated_at TIMESTAMP`)

| Table | Columns |
|---|---|
| `p8_run_log` | seq INT PK, step VARCHAR, ts TIMESTAMP, criteria_sha256, git_sha, inputs_hash, note |
| `p8_data_exclusions` | reason, role, rows BIGINT, matches INT, competition_type |
| `p8_units` | role, player_id, match_id, innings INT, competition_type, period, match_date DATE, n_balls INT, sw DOUBLE, sw2 DOUBLE, target, swr DOUBLE, mean_intensity DOUBLE, balls_t3 INT, phase_counts JSON, opposition_id, group_key |
| `p8_intensity_cdf` | candidate, innings, quantile_grid JSON |
| `p8_intensity_tests` | candidate, test_id, innings, phase, period, statistic DOUBLE, ci_low, ci_high, passed BOOL, note |
| `p8_intensity_corr` | candidate_a, candidate_b, spearman DOUBLE, n BIGINT |
| `p8_expected_metrics` | target, model, period, metric, value, baseline_value |
| `p8_wp_metrics` | model (W1/W2), period, brier, logloss, slope, intercept, baseline_brier, n |
| `p8_wp_calibration` | model, decile, mean_pred, mean_obs, n |
| `p8_wp_label_exclusions` | match_id, reason |
| `p8_delivery_leverage` | match_id, innings, innings_ball_num, wp_before, wp_after, leverage, intensity_P0..P6 |
| `p8_wpa_excluded_events` | match_id, innings, innings_ball_num, event_type |
| `p8_estimates` | approach (A/B/C), role, player_id, competition_type (IPL/T20I/COMBINED), component, estimate, normal_baseline, pressure_delta, delta_se, ybar_unshrunk, rank_basis, se, tau2, sigma2, n_units, n_balls, sum_w, w_eff, flags |
| `p8_reliability` | approach, role, scope, method, r, r_low, r_high, spearman_brown, n_players, gate_phase6_pass_share |
| `p8_stability` | approach, role, scope, player_id, top10_prob, rank_median, rank_low, rank_high, est_low, est_high |
| `p8_format_study` | approach, role, statistic, value, ci_low, ci_high, n_players, decision |
| `p8_sensitivity` | approach, role, variant, overlap_top10, spearman, note |
| `p8_method_selection` | role, approach_chosen, metrics JSON, rule_text, decision_ts |
| `p8_rankings` | role, rank, player_id, approach, scope, estimate, interval, top10_prob, evidence_class, ranking_status, model_validation_status |
| `p8_explanations` | role, player_id, kind (SELECTED/NEAR/EXCLUDED), reason_code, detail JSON, text |
| `p8_descriptive_radar` | role, player_id, competition_type, dimension, raw_value, denominator, cohort_pct, cohort_definition, available BOOL |

## 15. API and frontend contract

### 15.1 API (public read-only, GET only, `app/api/v1/routes_submission.py`, Pydantic v2 response models, validated query params, parameterised service queries, no user text in SQL)

All responses include `status: {label, definition, caveats[], criteria_sha256, methodology_version}`; the Top 10 responses include `ranking_status`, `model_validation_status`, and a `banner` string. Paginated lists use `limit` (1-100, default 25) and `offset >= 0`.

| Endpoint | Content |
|---|---|
| `GET /api/v1/submission/overview` | counts, statuses of both lists, headline caveats, data provenance hashes |
| `GET /api/v1/submission/top10/batters`, `/top10/bowlers` | ordered rows with uncertainty, stability, evidence class, row and list status |
| `GET /api/v1/submission/players?role=&format=&q=&limit=&offset=` | descriptive profile list (no score, no rank, no eligibility fields, same shape as existing `/players`) |
| `GET /api/v1/submission/players/{player_id}?role=` | descriptive profile, denominators, sample flags |
| `GET /api/v1/submission/players/{player_id}/evidence?role=` | observed vs expected, difference, components, matches/balls, reliability, rank under A/B/C and formats |
| `GET /api/v1/submission/radar/{player_id}?role=` | actual descriptive dimensions with raw value, denominator, cohort definition; unavailable dimensions flagged, not zero |
| `GET /api/v1/submission/compare?role=&ids=` (2-4 ids) | compatible metrics side by side with intervals; no superiority statement unless intervals do not overlap and that statement is generated from data |
| `GET /api/v1/submission/why?role=&player_id=` and `/why/index?role=` | selected explanation or exclusion reason with counts |
| `GET /api/v1/submission/methodology` | definitions, approach comparison summary, combination study result |
| `GET /api/v1/submission/validation` | reliability tables, calibration, gates (Phase 6 gate shown unchanged), sensitivity, limitations |
| `GET /api/v1/internal/ai/predictions?role=` | token-protected (existing mechanism in `routes_internal_ai.py`), experimental predictions with `EXPERIMENTAL_NOT_VALIDATED` |

Rules: existing `/players` stays descriptive-only; `/internal/players` stays token-protected; Phase 5 gating for the old ranking engine unchanged; cache scope and version isolation and copy semantics kept (`submission_service` returns deep copies of cached data keyed by data version). Error handling in section 15.3.

### 15.2 Frontend contract

Exactly ten navigation items in this order: Overview, Top 10 Batters, Top 10 Bowlers, Batter Profiles, Bowler Profiles, Player Comparison, Why Selected / Why Not Selected, Pressure Methodology, Data & Validation, Experimental AI Predictions. Mapping to existing components: `PressureBattersPage`, `PressureBowlersPage`, `PlayerComparison`, `WhySelectedPage`, `MethodologyPage`, `PlayerRadarChart`, `ComparisonRadarChart`, `PlayerProfileModal`, `StatCard`, `StatusBadge`, `Shell/Sidebar/Topbar` are rewired to a typed API client (`src/api/submission.ts`, fetch with `AbortController`, typed responses); `src/data/mock/*` and mock-importing services are deleted; obsolete features (`auction-intelligence`, `custom-selection`, `historical-needs`, `purse-explorer`, `rr-analysis`, `saved-shortlists`, `squad-builder`, `settings`) are unrouted and removed from the nav. New pages: Overview, Batter Profiles, Bowler Profiles, Data & Validation, Experimental AI Predictions (token entered at runtime, kept in memory only, locked state otherwise).

Every ranking view shows a persistent status banner (list status, definition link, caveats). Sample size, denominators, intervals, and inclusion probability are visible in tables and tooltips. Radar charts use real descriptive dimensions with raw values and denominators and state the normalisation cohort. Comparison supports 2-4 players and makes no "better under pressure" claim without interval evidence from the API. Loading, empty, error states are explicit. Style: forest green #246B4B, charcoal #202522, ivory #F7F6F2, amber #D97736, muted greys; SVG icons only; `cursor-pointer`; transitions 150-300 ms; visible focus ring; contrast at least 4.5:1; `prefers-reduced-motion`; labelled inputs; responsive at 375/768/1024/1440 with no horizontal scroll. Build gates: `npm run build`, `npm run lint`.

### 15.3 Error handling (concrete)

| Operation | Failure | Class | Caller receives | Log |
|---|---|---|---|---|
| Criteria verify | file missing/hash mismatch/not logged | Fatal | `CriteriaError`, script exit 2 | ERROR |
| Protected DB hash differs | Fatal | `IntegrityError`, exit 3, outputs not written | ERROR |
| TEST rows in a frame / lock state changed | Fatal | `LockViolation`, exit 4 | ERROR |
| Model fit non-convergence | Recoverable | fallback to the best baseline for that target; `fallback=True` in metadata; report states it | WARNING |
| REML non-convergence or `tau^2` at boundary | Recoverable | estimate with `tau^2=0`, `FLOOR` flag, status cannot exceed EXPLORATORY | WARNING |
| W1 gate fails | Recoverable | innings-1 WPA excluded, B innings-2 only, stated | WARNING |
| Missing expected value or label for a delivery | Recoverable | row dropped, counted in `p8_data_exclusions` | INFO |
| Fewer than 10 eligible players | Recoverable | shorter list, `INSUFFICIENT_EVIDENCE`, candidate pool | WARNING |
| API: unknown role/format/id | Client | 404 `{detail, code}` or 422 for invalid parameters | none (INFO access log) |
| API: p8 tables missing (pipeline not run) | Fatal for the request | 503 `{code: "PHASE8_NOT_BUILT"}` | ERROR |
| API: internal route without valid token | Client | 401/403 (existing behaviour) | WARNING |
| Frontend fetch failure | Recoverable | error state with retry, no cached fake data | console only |

### 15.4 Input validation

API: `role in {batter,bowler}` (required where stated); `format in {IPL,T20I,COMBINED}` default COMBINED; `limit` int 1-100; `offset` int >= 0; `q` string up to 60 chars, matched with a parameterised `ILIKE` on a whitelisted column; `ids` 2-4 distinct positive integers; `player_id` positive int. Failures return 422 (never silently clamped). Scripts: config files validated by schema on load (required keys, numeric ranges); unknown keys are an error. Invariant ownership: no-TEST invariant owned by `data.py` plus `lockguard.py` (single loader); no-future-information invariant owned by `data.py` feature whitelist and tests; status-label invariant owned by `status.py` only (API and reports read labels from tables, never recompute); criteria immutability owned by `criteria.py`.

## 16. Testing plan and open decisions

Unit tests: intensity functions and CDFs; REML against closed-form balanced one-way case; WPA attribution (striker, bowler, wicket, run-out, extras, no-ball with bat runs); calibration function on known synthetic data; eligibility including missing data; ranking determinism and tie-breaks (two runs, identical digest); status rules (every list/row combination); selection rule consuming metrics only. Leakage tests: truncation and mutation for WP and expected values; chronological split integrity (no match in two partitions, TRAIN dates < VALIDATION dates); training matches all TRAIN. Guards: criteria-hash enforcement and run-order, TEST-lock preservation, no Cricsheet/2026 CSV references in `app/phase8`, protected-file preservation, API schema (status labels on every submission response; `/players` has no ranking fields; `/internal/*` protected), no-hardcoded-data scan over `frontend/src` and backend production paths. Integration (marked slow): small-sample end-to-end on a two-season subset in a temporary DuckDB; full-data run only in chunk 8. Heavy full-suite pytest reserved for chunk 8.

Chunk bindings carried from the plan: chunk 1 includes fixing the failing `test_only_the_retention_modules_reference_retention_data` (plan D6) so the retention-module allow-list matches the retained legacy modules without reintroducing retention scope; chunk 1 also writes the D2 descriptive-profile columns appended to `descriptive_batter_profiles.csv` and `descriptive_bowler_profiles.csv`. Model grid time budget: 2 x 2 x 2 = 8 configurations x 6 targets x 5 folds; the coder caps the grid at a 20-minute total fit budget, and when exceeded uses the first four configurations in declared order and records the cap in model metadata.

### Open decisions (for the owner or later steps)

1. OD-P8-1: 2026 (TEST) matches are excluded from all rankings; a labelled non-pristine application needs owner authorisation.
2. OD-P8-2: p8_* tables are in `phase8.duckdb`, not `exploratory.duckdb`, to keep the protected files byte-identical (deviation from brief wording).
3. OD-P8-3: confirmation of status-label wording (`config/phase8_status_labels_v1.json`) and the 0.5/0.7 thresholds on Spearman-Brown reliability with the stated interval requirements.
4. OD-P8-4: optional official verification of the 42 late-dated T20I matches (excluded from primary evaluation).
5. OD-P8-5: models are fit on TRAIN only with no refit on TRAIN+VALIDATION (safer for out-of-sample claims, costs some training data).
6. OD-P8-6: eligibility floors (8 matches, 60 balls faced / 72 balls bowled in a format, combined-format rule) are set from the Phase 4/6 frozen values; they are declared now and cannot change after results.
7. OD-P8-7: innings-1 WP is used only if the W1 calibration gate passes; otherwise B and the B component of C are innings 2 only.
8. OD-P8-8: the combination decision rule (cross-format lower bound >= 0.3 and >= 30 players with both formats) is a declared judgement; no data-independent value exists for it.
9. OD-P8-9: row-level status inclusion-probability cut-points 0.5 and 0.25 are conventions, declared before results.
10. OD-P8-10 (resolved): the experimental model is trained on 2022-24 and evaluated out-of-time on 2025 (section 13); the shipped list uses features through 2025 with no refit.
11. OD-P8-11 (design review, medium): `tau^2 = 0` is expected. Chosen safest option: rank by unshrunk means, force EXPLORATORY, state the noise banner (6.4). Alternative (rank by posterior with arbitrary ties) rejected.
12. OD-P8-12: cut-points in 4.2 (`cs >= 0.5`, `m >= 2`, 75th and 80th percentile) and `min_players 30`, `min_matches_2025 = 4` are conventions declared before results. Safest option: strict values, which push lists toward EXPLORATORY.
13. OD-P8-13: `UNCLASSIFIED_LOW` is added to the evidence classes for eligible non-top players; it cannot appear in a submitted Top 10 row.
14. OD-P8-14: the experimental model is a simple ridge model. If it fails to beat carry-forward, the result is reported as `NO_PREDICTIVE_GAIN` rather than tuning.
15. OD-P8-15: the grid time cap (section 16) may reduce the hyper-parameter grid; this is recorded in metadata, not hidden.

## 17. Responses to design review findings

1 HIGH: addressed (6.4, 8.3, 12 via `rank_basis`, 9.2 forced EXPLORATORY). 2 HIGH: addressed (6.2 definitions, columns, sensitivity by `pressure_delta`, limitation). 3: addressed (2.1, 7.2, `innings_ball_num`). 4: addressed (4.2 approach-independent classes and order; 7.3 points to it). 5: addressed (3.1 innings-1 rule, predeclared in criteria). 6: addressed (section 5 OOF for all components, `match_id % 5`, test). 7: addressed (7.3 (iii)-(v)). 8: addressed (section 5 minimum counts, `NOT_ESTIMABLE`). 9: addressed (section 10 rewritten as keyed rules). 10: addressed (7.2 labels with regex and tests). 11: addressed (section 13 real model, OD-P8-10 resolved). Nits 12-15 addressed (8.4, 6.5, section 16, 7.2). Remaining judgement calls are in OD-P8-11 to OD-P8-15.
