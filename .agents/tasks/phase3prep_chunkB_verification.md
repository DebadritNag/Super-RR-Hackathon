# Phase 3 prep, chunk B verification (distributions and baseline)

Status of every output: `EXPLORATORY_NOT_VALIDATED`, `official_ranking: false`, `not_for_publication: true`.
No official ranking, no ML training, no validated pressure score. Official DuckDB opened read-only;
integrity snapshot before/after every script run reported `official_unchanged=True`.
Gate file `phase3prep_chunkB_gate.json` did not exist at start, so this is a first implementation.

## Files added or changed (project root d:/Data/backend)

| File | Change |
|---|---|
| `app/analytics/shrinkage.py` | Additive: `k_from_children` (method of moments, `tau2 = max(between, tau2_floor * sigma2_within)`, `k <= 1/tau2_floor`, `shrinkage_floor_hit`), `shrink_to_parent`, `beta_binomial_shrink` (design-effect scaled), `pooled_other_mean`. Existing functions untouched. |
| `app/analytics/pressure_features.py` | New. Populations (base, chase, innings 1; innings 3/4, OTHER_T20, DLS-excluded, `target_basis_unverified`, `Req<=0` never in any population), wickets-bin merge with the corrected residual-finding-3 rule, LOMO par curve and strictly-prior par, LOMO `exp_remaining` with chain E0 -> E1 -> E2 -> NONE, `exp_cell_level_used`, `shrinkage_floor_hit`, signals, `rank_pct` with own match removed and cell fallback, candidate families (a) and (b) with per-competition-type quantiles. |
| `app/analytics/pressure_distributions.py` | New. Percentile tables, histograms, zero inflation, per-player opportunity counts (balls faced / deliveries, legal balls, matches, innings, Kish n_eff), candidate effect rows, family (c) knee breaks with IPL/T20I and LOMO/prior reproducibility, strictly-prior vs LOMO table. |
| `app/analytics/pressure_distribution_report.py` | New. Markdown renderer. |
| `app/analytics/baseline_engine.py` | New. Batter and bowler frames, hierarchical EB expected values (pooled, leave-player-out, leave-match-out), calibration identity, player shrinkage to pooled-other target (0 as sensitivity), bootstrap by match stratified by format with fixed seed. |
| `scripts/run_pressure_distributions.py` | New. Writes `data/reports/pressure_distribution_report.md/.json`, table `exp_pressure_signals` in `data/database/exploratory.duckdb`; independent SQL spot check. |
| `scripts/run_baseline_exploration.py` | New. Writes `data/reports/baseline_methodology_v1.md` and `baseline_exploration.json`. |
| `tests/test_baseline.py`, `tests/test_pressure_eligibility.py` | New, 31 tests. |

## Commands run and results (raw)

```
PS> python scripts/run_pressure_distributions.py
candidates=384 spot_check_all_match=True official_unchanged=True

PS> python scripts/run_baseline_exploration.py
calibration_identity_holds=True reproducible=True official_unchanged=True

PS> python -m pytest -q tests/test_baseline.py tests/test_pressure_eligibility.py
31 passed in 2.59s

PS> python -m pytest -q
254 passed in 183.06s (0:03:03)

PS> python -m ruff check .
All checks passed!
PS> python -m ruff format --check .
85 files already formatted
```

Determinism: both scripts were run twice; the JSON outputs were identical apart from
`provenance.generated_at_utc` (`identical_except_timestamp: True` for both files).

## Key figures (from DuckDB through the exploratory state)

- State rows 200,999. Base population 190,584 rows, 812 matches, 1,602 innings. Chase primary
  89,589 rows (784 innings); innings-1 primary 100,425 rows (812 innings).
- Exclusions: innings 3/4 38 rows; OTHER_T20 6,985; DLS-excluded 3,404; `target_basis_unverified`
  chase rows 570; `Req <= 0` 0 and RRR NULL 0 inside the base after earlier filters. Rows with a
  state wicket-flag disagreement inside the base: 652.
- Wickets bins (global merge, min 30 distinct innings): {10-8}, {7-1}. The low singleton bins are
  empty in powerplay cells, which forces the coarse partition. `wickets_bins_failed` false.
- Par source innings: IPL 358, T20I 435 (793). `exp_cell_level_used`: E0 192,669; E1 1,319;
  NONE 7,011 (OTHER_T20, innings 3/4, zero balls left). Strictly-prior par unavailable for 7,692
  innings-1 rows (not filled).
- Chase RRR p50/p90/p99: IPL 10.09/15.94/50.40; T20I 9.31/15.75/48.00. Death-phase p50 about 13.2.
- 384 candidate definitions examined (family a 280, family b 84, family c 20 reproducible-break
  rows). Effect tables show pressure balls, matches, innings, Kish n_eff and players above the
  Phase 2.5 floors. Example: chase RRR >= p90 gives 10 IPL and 7 T20I batters with at least 60
  pressure balls.
- Independent SQL spot check of `a|chase|IPL|batter|rrr|abs|0.9`: threshold 15.94, 3,884 balls
  faced, 175 matches, 175 innings, 10 batters >= 60 balls. All five quantities match the engine.
- Baseline: calibration identity max |cell residual| <= 4.3e-10 in all eight streams. Expected
  ranges plausible (batter runs per ball 1.17 to 1.76; probabilities in [0, 1]; no NaN).
  The tau2 floor binds in most parents (for example, 16 of 18 for batter runs); the 0.001 and 0.1 sensitivities
  are tabulated. Season environment: 10 supportable comp x season cells, LOMO offset max 0.081
  runs per ball, median shift in shrunk player residual 0.005; default off.
  Venue: 17 of 94 venues have at least 30 innings; not used.
- B0 pressure-sample mean residual (chase RRR >= p75): batter runs +0.08; the per-candidate baseline
  reduces it to +0.05. Bootstrap: seed 20260512, 500 resamples.

## Residual findings handled in this chunk

1. Shrink target = pooled mean residual of OTHER players; 0 kept as named sensitivity; synthetic
   test `test_player_shrink_target_is_pooled_other_residual` (one-ball player near +0.2).
2. No definition selected; total candidates examined reported (384).
3. Merge rule replaced; test `test_merge_only_deficient_bin_merges_and_low_bins_stay_separate`.
5. Chase population excludes `req_nonpositive_flag` and NULL RRR.
6. OTHER_T20 gets NULL par/exp_remaining/rank and enters no population.
7. Quantiles per competition type within context; the death pair uses phase as the fixed label.

## Known gaps (left for later chunks or approval)

- Strictly-prior `exp_remaining`/`req_to_exp` and a strictly-prior baseline are not built; pooled
  quantile sensitivity (residual finding 7) not built; membership changes under `W_alt` per candidate
  not recomputed (counted only).
- Per-candidate baselines are built for four diagnostic candidates, not for all 384.
- For the wicket stream the bootstrap re-estimates a weakly identified prior, so some point
  estimates fall outside their percentile interval; the report states the share.
- Stage 5 eligibility, Stage 6 weight sensitivity, the restriction applier and the feature
  dictionary belong to chunks C and D.
