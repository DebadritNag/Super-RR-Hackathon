# Semantic review: SupeRR Phase 3 preparation (pressure framework, state engine, exploratory eligibility)

Phase 3 prep adds a leakage-controlled pre-delivery state engine, an exploratory store separate from `superr.duckdb`, a stratified empirical-Bayes baseline, a pressure-specific eligibility experiment, a format-weight rerun and a metric-level application of the 26-rule restriction register. Everything is labelled `EXPLORATORY_NOT_VALIDATED` with `official_ranking: false` and `not_for_publication: true`. No official Top 10, no ML training, 70:30 provisional, official data byte-identical. Watch for: the provisional definition and the Stage 7 sensitivity use proxies that are disclosed but not yet on the Stage 4 baseline (confirmed, disclosed, non-blocking); individual residual intervals are very wide (confirmed, disclosed).

**Verdict**: APPROVED

## High-level view

The state engine computes each delivery's state only from earlier rows of the same innings. The innings-2 target is the innings-1 total plus 1, and that value is never exposed to innings-1 states. Leakage tests cover truncation and mutation. Innings-1 par uses leave-one-match-out expectations that include later matches. This is disclosed as descriptive and a strictly-prior variant is reported separately, so it is a labelled limitation rather than a hidden leak.

Pressure cutoffs come from per-format quantiles of observed signals. 384 candidates were enumerated and 9 definitions ran through the eligibility harness. The provisional `chase|q0.9` was chosen by a pre-declared population-level rule, with player scores and rankings excluded from the choice. Eligibility is recomputed from pressure observations and compared against the Phase 2.5 thresholds. The shortfall is real: combined (both-format) pools are 8 batters and 6 bowlers, and the reports state the lists are not padded to ten.

Restrictions are applied as masks and flags. Innings 3/4 rows (38, six matches) stay in `deliveries` and are excluded from pressure populations with the two reason codes. `other` extras stay a separate category and are not zero-filled. Joins use player_id only, and the squad join is shown not to alter the pressure sample.

<details>
<summary>Issues (4)</summary>

1. **Stage 7 sensitivity on raw proxy residuals** (confirmed, disclosed in summary section 11) — rerun on the Stage 4 baseline before any scoring phase.
2. **Wide individual uncertainty** (confirmed) — median 95% CI width about 74 for batters and Top 10 bootstrap overlap 5.2 to 7.0 mean no individual ordering is supportable. Keep scores non-publishable.
3. **FULL_SAMPLE quantile thresholds and LOMO par** (confirmed, disclosed) — descriptive, not predictive. A temporal split is needed before validation claims.
4. **Two tests skip when deliverables are absent** (confirmed) — they pass after a full run. Prefer a hard fail or a fixture in CI.

</details>

<details>
<summary>Details</summary>

## Scope limits and labelling

All three JSON deliverables checked (`pressure_feature_dictionary`, `pressure_threshold_experiment`, `pressure_format_weight_sensitivity`) carry the exploratory status, `official_ranking: false` and `not_for_publication: true`. All six markdown reports open with a status section stating that no number is validated. The provisional recommendation status is `PROVISIONAL_NOT_VALIDATED`. The weight sensitivity reports lists of 8 and 6 players with "not padded" statements, as ids only. The 8 configurations including 70:30 are preserved, and 70:30 is described as provisional.

## Leakage and cutoffs

Code review of `pressure_features.py` found the `fillna(0)` calls only in leave-one-out arithmetic for absent merge keys. They do not impute a player or format score. The Cricsheet references in `pressure_engine.py` and `pressure_service.py` consume Phase 2.5 report masks only, and the service records `cricsheet_files_opened: 0`. Cricsheet is not a feature source. The test suites cover state (45), leakage (17), baseline (19), thresholds (22), eligibility (12), restriction service (19) and format sensitivity (14).

## Figure consistency

Spot-checked against the reports: the chase RRR quantiles (10.09/9.31 median, 21.19/20.57 p95), the 193,988 and 89,589 populations, the 38-row innings 3/4 ledger and its reason split, the 264 `other` rows, squad row counts (28,381, 89,589 with and without the join), the provisional definition table (IPL batter 56, bowler 43, T20I 61 and 32, combined 8 and 6), and the Spearman values (0.12 for batters at 0:100, 0.71 for bowlers at 100:0). All agree with the user summary. The verification file reports 309 tests passed, ruff clean, 8 of 8 independent spot-checks and unchanged hashes. I did not re-run the suites, as instructed.

## Residual risks

The pass depends on the verification file being accurate, since the suites were not re-run. The conclusions that matter most (small combined pools and wide intervals) are stated honestly and push the decision to the user.

</details>

<details>
<summary>File map</summary>

Reports under `d:/Data/backend/data/reports/`, code under `app/analytics/` and `app/services/`, scripts under `scripts/`, tests under `tests/`. No git repository exists in the workspace, so no diff was available. Review was by file inspection.

</details>
