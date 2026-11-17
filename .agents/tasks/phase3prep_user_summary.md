# SupeRR Phase 3 preparation: user summary

**Status: EXPLORATORY_NOT_VALIDATED.** No number here is a validated pressure score. No official Top 10 was published, no ML model was trained, 70:30 remains a PROVISIONAL default, Cricsheet is validation-only and not a feature source. **Full pressure scoring, official rankings and ML model training await your approval.**

## 1. Implemented files (d:/data/backend)
- Reports in `data/reports/`: `pressure_framework_v1.md` (copy in `docs/`), `pressure_feature_dictionary.json`, `pressure_distribution_report.md/.json`, `pressure_threshold_experiment.json`, `pressure_eligibility_report.md`, `baseline_methodology_v1.md`, `baseline_exploration.json`, `phase3_data_quality_application_report.md/.json`, `pressure_format_weight_sensitivity.json/.md`, `phase3_preservation.json`, state manifest and spot-check JSON.
- Code (`app/analytics/`): `pressure_engine.py`, `pressure_features.py`, `pressure_distributions.py`, `pressure_distribution_report.py`, `baseline_engine.py`, `feature_registry.py`, a restriction service, and reuse of the Phase 2.5 `confidence_engine` and combination engine.
- Scripts: `build_pre_delivery_state.py`, `run_pressure_distributions.py`, `run_baseline_exploration.py`, `run_pressure_eligibility.py`, `run_pressure_format_sensitivity.py`, `apply_dq_restrictions.py`, orchestrator `run_phase3_prep.py`.
- Tests: `test_pressure_state.py`, `test_pressure_leakage.py`, `test_baseline.py`, `test_pressure_eligibility.py`, `test_pressure_thresholds.py`, `test_restriction_service.py`, `test_phase3_format_sensitivity.py`, plus the 142 earlier tests.
- Separate exploratory store `data/database/exploratory.duckdb` (`exp_pre_delivery_state`, `exp_pressure_signals`, manifest). `superr.duckdb` is never written.

## 2. Commands
```
cd d:/data/backend; $env:PYTHONUTF8=1
python scripts/run_phase3_prep.py   # exit 0, all 7 steps 0, deliverables_ok=True
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

## 3. Test and lint output
- pytest: **309 passed in 231.76 s** (the 142 earlier tests still pass).
- ruff check: `All checks passed!`. ruff format --check: `101 files already formatted`.
- Raw outputs: `phase3prep_verification.md`.

## 4. Actual figures from DuckDB (exploratory proxy)
- State table 200,999 rows (equals CSV rows), 867 matches, 1,724 innings. Regulation in-scope (innings 1/2, IPL/T20I): 193,988 rows, 837 matches. Base population without DLS-excluded rows: 190,584 rows, 812 matches. Chase primary: 89,589 rows, 784 chases (IPL 355, T20I 429). Innings-1 primary: 100,425 rows.
- Exclusions: innings 3/4 38 rows in 6 matches; OTHER_T20 6,985 rows (30 matches); DLS-excluded 3,404 rows; chase rows with unverified target basis 570; state rows with wicket-flag disagreement 652 (base).
- Independent spot-checks (plain csv recomputation from `updated_ball_by_ball.csv` and `matches.csv`): 6 random non-DLS chase deliveries match on runs required, legal balls remaining, wickets remaining and RRR; innings-2 target = innings-1 total + 1 in 8 matches; revised_target equals state target (source REVISED_TARGET) in 10 DLS matches; legal-ball totals match in 25 innings-1 samples; innings>=3 rows 25 + 13 in the six expected matches. 8 of 8 passed.
- Chase RRR quantiles (IPL / T20I): median 10.09 / 9.31, p75 12.22 / 11.75, p90 15.94 / 15.75, p95 21.19 / 20.57.
- Preservation: all 12 source CSV hashes and the `superr.duckdb` hash (cb4077ee...a391d) equal the Phase 2.5 recorded values; `phase3_preservation.json` shows `official_unchanged=true`, empty diff.

## 5. Candidate thresholds and pressure populations
384 candidates examined (family a 280, family b 84, family c reproducible breaks 20). No cutoff was hand-picked. Chase batter, absolute view (balls faced), IPL / T20I:

| Signal | q | IPL thr | IPL rows | IPL matches | T20I thr | T20I rows | T20I matches |
|---|---|---|---|---|---|---|---|
| gap | 0.75 | 4.70 | 9,725 | 313 | 5.00 | 11,492 | 364 |
| gap | 0.90 | 8.57 | 3,856 | 220 | 8.94 | 4,553 | 244 |
| gap | 0.95 | 12.80 | 1,915 | 154 | 13.31 | 2,273 | 189 |
| neg_resource_ratio | 0.75 | -0.18 | 9,759 | 337 | -0.17 | 11,550 | 384 |
| neg_resource_ratio | 0.90 | -0.06 | 3,912 | 284 | -0.06 | 4,725 | 327 |

Nine definitions went through the full eligibility harness (chase / inn1 / any x q 0.75, 0.9, 0.95). Pressure unit rows over four format-role cells: chase 43,526 / 17,356 / 8,673; inn1 49,389 / 19,748 / 9,871; any 92,915 / 37,104 / 18,544. Viable: chase|q0.75, any|q0.75, chase|q0.9. **Provisional: chase|q0.9**, picked only from population-level quantities (highest viable quantile, ties to larger population), one of N=9 drawn from 364 family a/b candidates. Not validated.

## 6. Baseline calibration (Stage 4)
- Separate batter and bowler stratified empirical-Bayes baselines (competition x context x phase x wickets bin), hierarchical shrinkage, leave-player-out and leave-match-out expectations, bootstrap by match (seed 20260512, 1000 resamples). No ML.
- Calibration identity on raw cell means holds for all 8 streams (max cell residual about 4e-10, 24 finest cells); second run identical. Expected batter runs per ball 1.17 to 1.76 (mean 1.40), no NaN.
- Season offsets: 10 of 10 comp x season cells supportable, sensitivity only, max |offset| 0.0809 runs/ball. Venue not used (17 of 94 venues have 30+ innings; no pitch or dew data).
- Residual findings 1 and 3 are implemented and tested (shrink target is the pooled mean residual of other players with 0 as a named sensitivity; wickets-bin merge rule).

## 7. Pressure-specific eligibility vs Phase 2.5 all-situation thresholds (chase|q0.9, balls family)

| Format | Role | P2.5 min balls | P2.5 eligible (all situations) | Pass P2.5 min on pressure sample | Pressure min | Pressure eligible | Matches | Pressure deliveries | Boot. Top 10 overlap | Spearman | Median CI width |
|---|---|---|---|---|---|---|---|---|---|---|---|
| IPL | batter | 120 | 129 | 1 of 211 | 24 | 56 | 154 | 2,531 | 6.61 | 0.81 | 74.33 |
| IPL | bowler | 192 | 119 | 0 of 169 | 32 | 43 | 163 | 2,425 | 5.18 | 0.62 | 3.62 |
| T20I | batter | 120 | 205 | 0 of 334 | 24 | 61 | 156 | 2,371 | 7.01 | 0.80 | 74.94 |
| T20I | bowler | 144 | 191 | 1 of 269 | 36 | 32 | 136 | 2,077 | 6.55 | 0.69 | 3.67 |

Pool rule max(30, 30) is met in all four cells. Only 8 batters and 6 bowlers qualify in both formats, so no combined Top 10 exists and nothing is padded. The thresholds are necessary, not sufficient: intervals are wide and Top 10 membership is unstable.

## 8. Format-weight sensitivity (eight configs: 100:0, 85:15, 80:20, 70:30, 60:40, 55:45, 50:50, 0:100)
- Eligible: batters IPL 56, T20I 61, both 8; bowlers IPL 43, T20I 32, both 6. Looser rung: 12 and 10 combined; stricter: 6 and 4. Phase 2.5 all-situation reference: 133 batters and 114 bowlers in both formats. Combined only where both format scores exist; none imputed; single-format players in their own lists; ADJUSTED_ESTIMATE in a separate section.
- Combined batters (8): overlap with 70:30 is 8 in every config; Spearman vs 70:30: 100:0 0.95, 85:15 0.95, 80:20 0.95, 60:40 0.98, 55:45 0.90, 50:50 0.88, 0:100 0.12 (max rank move 6).
- Combined bowlers (6): overlap 6 in every config; Spearman: 100:0 0.71, 85:15 0.94, 80:20 1.00, 60:40 0.94, 55:45 0.89, 50:50 0.89, 0:100 0.60.
- Reading: with so few combined players, overlap is trivially full; Spearman is the informative column, and 0:100 differs most. Config id and hash (`a77cb111...7ec7417`) are on every result.

## 9. Restriction ledger (register: 26 rules, global_exclusion false)
- RULE_INNINGS_3_4: 38 rows, 6 matches excluded from 13 metrics (reason codes CONFIRMED_SUPER_OVER_BY_CRICSHEET 16 rows / 3 matches: 34429, 45512, 50359; UNVERIFIED_INNINGS_ROLE 22 rows / 3 matches: 40725, 48027, 48029). Rows remain in `deliveries`; none enter a pressure population.
- Extras: `other` 264 rows kept as a separate category (0 mapped to None), Penalty 1 row removed from ball counts, 2 None-type rows with runs flagged, 265 rows with an unverified label, 36 rows with secondary extras runs not interpreted.
- Wicket flags: 12 dismissed-without-flag rows (sensitivity exclude), 1 wicket-without-dismissed (excluded from dismissal metrics only).
- DLS: 34 matches, 4,433 rows; 3,404 rows not reconstructable, 0 in the primary chase sample. RULE_CRICSHEET_TOTALS: 1,221 rows (ten innings) with sensitivity variant. RULE_NO_RESULT_MATCHES: 1,753 rows excluded from outcome labels only.
- Identity: 14 players share 7 names; join on player_id only (a name join would merge 10 ids). Squads: `match_squads` 28,381 rows, 75 flagged duplicates; the pressure sample is identical (89,589 rows) with and without the deduplicated join, and a naive join adds 375 rows; the pipeline never reads `match_squads`.
- 26 of 26 rules and 99 features covered (`ok=True`).

## 10. Open decisions for you
Residual findings (design review 2), with handling used:
1. Shrink target: pooled mean pressure residual of other players (0 kept as a sensitivity). Confirm.
2. Selecting the provisional definition: population-level quantities only; chase|q0.9 is one of 9 run (364 candidates). Confirm the rule and the choice.
3. Wickets-bin merge rule: implemented as revised (smallest bin merges with the neighbour giving the larger combined m).
4. DLS reliability: `innings_ended_short_of_stated_limit` flags 8 innings 1 (15410, 15546, 31707, 36208, 41975, 46311, 46749, 50408) plus 1 innings 2 as unreliable; affects only the DLS sensitivity variant.
5. to 9. (RRR NULL when requirement is non-positive; OTHER_T20 gets NULL par and is out of scope; quantiles per competition x role with pooled as a sensitivity; availability rows for the added features; Stage 5/6 reuse of Phase 2.5 functions with missing scores never imputed): handled as documented.

Further decisions: par definition for innings 1 (LOMO descriptive vs strictly prior), DLS resource reconstruction (currently NOT_RECONSTRUCTED), phase boundaries in DLS-shortened innings, pressure definition and thresholds (provisional), whether to retain the weak-stability bowler and batter thresholds, and whether to proceed to full scoring.

## 11. Unresolved issues and caveats
- Individual pressure residuals are very uncertain: median 95% CI width about 74 (batter score units); bowler Top 10 overlap only 5.2 to 6.6.
- Stage 7 sensitivity uses unshrunk raw proxy residuals, not the Stage 4 baseline (disclosed; rerun on the Stage 4 baseline before any scoring phase).
- Of 4,433 DLS rows, 3,404 are not reconstructable; the composition of the remaining 1,029 is not itemised in detail.
- Nominal ladder rungs are placeholders scaled for pressure sample sizes. Eligibility is held fixed inside the bootstrap. Quantile thresholds and baselines are FULL_SAMPLE and descriptive, not predictive.
- Two deliverable tests use `pytest.skip` when outputs are absent (all pass after a full run).

## 12. Deviations
None from the approved decisions. Combined lists are short (8 and 6) rather than 10, by design. Technical outputs contain no player names or rankings.

## 13. Exploratory vs validated
Everything above is an exploratory proxy calculation from official DuckDB data via `exp_pre_delivery_state`. The measured stream is shrunk actual-minus-expected (`PROXY_ACTUAL_MINUS_EXPECTED_NOT_A_PRESSURE_SCORE`). Nothing is validated. A validation plan (temporal split, calibration, ablation, stability, bootstrap) is in the framework spec and baseline methodology.

## 14. Approval gate
Awaiting your approval before: full pressure scoring, official rankings, and ML model training. 70:30 stays provisional. No official Top 10 exists. Cricsheet is not a feature source.
