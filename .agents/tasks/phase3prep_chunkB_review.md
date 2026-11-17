# Chunk B review: pressure feature distributions and context-adjusted baseline

Chunk B adds exploratory distributions over 200,999 pre-delivery state rows and a hierarchical empirical-Bayes batter and bowler baseline. All outputs are labelled `EXPLORATORY_NOT_VALIDATED`, `official_ranking: false`, `not_for_publication: true`. Both reports open with an exploratory-versus-validated section stating that no number is validated. No cutoff is selected: 384 candidates are examined as a quantile grid, an AND-combination family and reproducible knee breaks, each with a population effect table. Watch for: the tau2 floor binds in most shrinkage parents, so the shrinkage strength is mostly the floor rather than an estimate (confirmed, disclosed with sensitivity); the wicket-stream shrinkage prior is barely identified, so player intervals are uninformative (confirmed, disclosed); one knee candidate is labelled usable although it selects most rows (likely).

**Verdict**: APPROVED

## High-level view

Distributions come from the official DuckDB through the state table, with explicit populations. The base is 190,584 rows over 812 matches, chase primary is 89,589 rows and innings-1 primary is 100,425 rows. Exclusions are itemised: innings 3/4 (38 rows), OTHER_T20 (6,985), DLS-excluded (3,404), unverified targets (570). Percentiles, histograms, zero-inflation checks and cell sizes are shown, and an independent SQL spot check matches the engine on threshold, balls, matches, innings and player count.

Candidate thresholds are derived from per-format, per-context quantiles of the signals. Each row of the effect tables reports pressure rows, distinct matches, innings, Kish n_eff and players above the Phase 2.5 floors, so the effect on the eligible population is visible. The tables show that many high-quantile candidates leave fewer than ten qualifying players, for example chase RRR at q0.95 gives 2 IPL and 0 T20I batters, which supports not forcing a Top 10 later.

The baseline has separate batter and bowler streams, with cells defined by competition, innings role, phase and wickets bin. Cells shrink to parents by method of moments (continuous) or design-effect-scaled beta-binomial (binary). Expectations are leave-player-out, with leave-match-out as a named sensitivity. The calibration identity holds (max residual 4.3e-10). Player residuals are shrunk to the pooled mean of other players, with 0 as a named sensitivity. The bootstrap resamples matches, stratified by format, seed 20260512, 500 resamples.

Leakage control is stated in the reports: par and expected-remaining are leave-one-match-out, quantiles are FULL_SAMPLE, and the strictly-prior variant is reported as unavailable for 7,692 rows rather than filled. Neither module reads win_team, result, margin or man_of_the_match.

<details>
<summary>Issues (6)</summary>

1. **Fixed-by-floor shrinkage** (confirmed, non-blocking) — `tau2_floor = 0.01` binds in 16 of 18 batter-runs parents and 18 of 18 for dismissal, boundary and wicket streams, so k is set by the floor. The 0.001 and 0.1 sensitivities are tabulated (mean |dE| up to 0.02 runs per ball). In Stage 5, report ranking stability under the floor values before using the scores.
2. **Weakly identified wicket prior** (confirmed, non-blocking) — the bowler wicket stream has eb k of about 3,900, so shrunk residuals are nearly constant (about -0.0055 for every technical-sample player) and 8% of point estimates sit outside their own interval. Do not use this stream for ranking without a different prior or a pooled-count design.
3. **Fixed baseline in bootstrap** (confirmed, non-blocking) — the baseline expectation is not refit inside resamples, so intervals understate baseline uncertainty. This is disclosed in limitation 3. State it in the Stage 5 uncertainty section.
4. **Knee candidate over-inclusive** (likely, non-blocking) — the innings-1 `neg_par_dev` and `neg_proj_gap` knees sit at q about 0.09 (39,712 IPL rows, 119 batters) and are flagged usable, which makes them near-all-situation populations rather than pressure. Mark them as non-pressure in the Stage 5 candidate list.
5. **Per-candidate baselines cover four candidates only** (confirmed, non-blocking) — pressure-specific baselines are built for four diagnostic candidates, not all 384, and strictly-prior baselines are not built. Stage 5 must build the baseline for any candidate it scores.
6. **Pressure-sample residual not zero under B0** (confirmed, informational) — chase RRR >= p75 shows +0.08 runs per ball for B0, down to +0.05 for the candidate baseline. It remains a diagnostic, not a skill estimate. Keep that wording in later reports.

</details>

<details>
<summary>Details</summary>

### Candidate derivation and population effects

Thresholds are observed quantiles per competition type within context. Family (b) adds a wickets or balls-remaining condition at the matching quantile of that variable. Family (c) is the knee of the cumulative curve and is kept only when the IPL and T20I quantile positions agree within 0.05. No candidate is chosen. The effect tables show the steep loss of players as the quantile rises: chase RRR from q0.75 (51 IPL batters at floor 2) to q0.90 (10) to q0.95 (2). The 5.9k to 3.9k row drop between q0.85 and q0.90 gives the reader the trade-off directly. The floors are the Phase 2.5 ladders and are labelled provisional. The over-inclusive knee candidates are the exception (Issue 4).

### Baseline controls and calibration

Controls: competition, innings role, phase and a two-bin wickets partition produced by a deterministic merge rule. The partition is coarse because singleton low-wicket bins are empty in powerplay cells, which the report states instead of tuning. Season, competition and venue are examined as sensitivities: ten comp-by-season cells are supportable and a leave-one-match-out offset peaks at 0.081 runs per ball, with median shrunk-residual shift 0.005, so it stays off by default. Venue is not used (17 of 94 venues have at least 30 innings). Phase effects are removed by the phase cell, which answers the requirement not to compare death-over and ordinary-over strike rates raw: the residual table shows death-over mean residuals of 0.01 to 0.03 against raw death runs per ball 1.45 to 1.72.

### Shrinkage and bootstrap

The player shrink target is the pooled mean of other players' residuals, with a synthetic test confirming a one-ball player lands near the pooled value, not 0. Technical-sample players are listed only as `comp|player_id`, ordered by id, labelled `TECHNICAL_SAMPLE_NOT_A_RANKING`.

### Leakage

The baseline and feature modules do not reference win_team_id, result_status, margin or man_of_the_match. Par and expected-remaining runs use leave-one-match-out, so a delivery never uses its own match outcome. Quantile cutoffs use the full sample, which the reports flag as descriptive only. Strictly-prior variants for innings-1 par exist and report unavailability for 7,692 rows.

### Tests

31 tests across `tests/test_baseline.py` and `tests/test_pressure_eligibility.py`. A narrow spot-check run passed (31 in 2.3 s, 67 assert statements). They use hand-checkable synthetic data: leave-player-out arithmetic, calibration identity, parent fallback for sparse and empty cells, probability bounds, determinism, seed sensitivity, bootstrap resampling matches rather than deliveries, merge rule cases, own-match removal in rank_pct, an independent pandas count of pressure samples, Kish n_eff, and a real-store test for populations and restricted innings. The coder's evidence also records a full 254-test pass and ruff clean, and two scripts run twice with identical JSON apart from timestamp. Not re-run here.

### Not covered (belongs to later chunks)

Stage 5 eligibility, Stage 6 weight sensitivity, the restriction applier and the feature dictionary are out of scope for chunk B and listed by the coder as chunks C and D.

</details>

<details>
<summary>File map</summary>

- `app/analytics/shrinkage.py`: additive shrinkage helpers
- `app/analytics/pressure_features.py`: populations, par curves, signals, candidate families
- `app/analytics/pressure_distributions.py`, `pressure_distribution_report.py`: tables and markdown
- `app/analytics/baseline_engine.py`: hierarchical expected values, shrinkage, bootstrap
- `scripts/run_pressure_distributions.py`, `scripts/run_baseline_exploration.py`: runners
- `tests/test_baseline.py`, `tests/test_pressure_eligibility.py`: 31 tests
- `data/reports/pressure_distribution_report.md/.json`, `baseline_methodology_v1.md`, `baseline_exploration.json`: outputs

</details>
