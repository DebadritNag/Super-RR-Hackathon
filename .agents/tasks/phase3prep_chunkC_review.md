# Pressure-specific eligibility and format-weight sensitivity (Phase 3 prep, chunk C)

Chunk C recomputes eligibility thresholds from pressure observations and reruns the eight format-weight configurations on them. Thresholds come from a nine-definition harness run (reusing `confidence_engine.py` unchanged), and `chase|q0.9` is selected by a pre-declared population-only rule. At that definition only 8 batters and 6 bowlers qualify in both formats, so the combined lists are short and are not padded. All outputs carry `EXPLORATORY_NOT_VALIDATED`, `official_ranking: false`, `not_for_publication: true`, and 70:30 stays provisional. Watch for: (1) T20I minimum-ball thresholds (24 batter, 36 bowler) sit on nominal ladder rungs, not observed percentiles (confirmed); (2) the selected definition is one of nine examined from 364 candidates, with eligibility held fixed inside the bootstrap (confirmed, disclosed); (3) combined overlap and Spearman on 8 and 6 players are descriptive only (confirmed, disclosed).

**Verdict**: APPROVED

## High-level view

Pressure thresholds were recomputed from pressure balls faced and bowled per format and role, independently for batters and bowlers. The Phase 2.5 all-situation cut-offs (120/192 IPL, 120/144 T20I) were checked against the same samples and only 1, 0, 0 and 1 players pass them, so they were not reused. The report and JSON show that comparison, which matches the Phase 2.5 report values.

The selection rule works at population level only (highest quantile with a sufficient pool in all four format-role cells), and the tests assert that it ignores player scores. The result is a short both-format pool (8 batters, 6 bowlers). The rerun reports those short lists as they are, with 6 and 4 under a stricter rung and 12 and 10 under a looser rung.

All eight configurations are present, each with id, weights, version and hash. Players who are not eligible in both formats get a null combined score and an explicit status. The audit shows 0 combined scores for 446 batters and 355 bowlers outside the both-format pool. Single-format adjusted estimates sit in a separate, labelled section. Rankings are trimmed technical player ids with no names, and no official ranking is published.

## Issues (4)

<details>
<summary>Issues (4)</summary>

1. **Nominal T20I rungs** (confirmed, non-blocking): T20I batter 24 and bowler 36 come from nominal `PR` rungs, not observed percentiles, and the T20I stricter alternative equals the recommendation. Keep the "nominal placeholder" caveat prominent when requesting approval.
2. **Selection among nine definitions** (confirmed, non-blocking): `chase|q0.9` is chosen from 9 of 364 candidates, and the per-candidate baselines exist only for those nine. The recommendation must stay "provisional, one of N examined".
3. **Low stability** (confirmed, non-blocking): expected Top 10 overlap is 5.2 to 7.0 and the bootstrap 95% interval excludes zero for only 27% (IPL) and 15% (T20I) of eligible batters. Any later scoring needs a larger sample or a coarser pressure definition.
4. **Tiny combined pools** (confirmed, non-blocking): with 8 batters and 6 bowlers, the Top 10 overlap and Spearman figures across the eight configurations are descriptive only, and 100:0 and 0:100 merely re-rank one format's z-score within that pool.

</details>

<details>
<summary>Details</summary>

## Threshold recomputation and the Phase 2.5 comparison

The ladder rescaling is declared in `pressure_eligibility_rules_v1.json`. Percentile rungs come from the observed pressure distribution and nominal rungs are kept only between observed p10 and p90. The chosen thresholds are IPL batter 24 and bowler 32, T20I batter 24 and bowler 36. Eligible counts are 56, 43, 61 and 32, and the data-weight crossover points are 20.9, 30.3, 22.0 and 33.6 balls. Pressure deliveries for `chase|q0.9` are 3,884, 4,093, 4,592 and 4,787. The same numbers appear in the report table and the JSON. The T20I thresholds rely on nominal rungs, so they are less data-derived than the IPL ones.

## Short combined pools and the missing-format rule

The both-format intersection (8 batters, 6 bowlers) is below ten, and the output never pads. The adjusted-estimate section renormalises weights over a player's eligible formats and is labelled as not comparable to two-format scores. The audit and tests (`test_missing_format_gives_null_combined_and_explicit_status_never_zero`, `test_observed_but_not_eligible_format_is_also_null`, `test_format_without_pressure_rows_yields_empty_table_not_fake_players`) cover the no-zero-fill rule.

## Eight configurations

Spearman against 70:30 runs from 0.12 (batters at 0:100) to 1.0, with a maximum rank change of 6 at 0:100. The bowler 0:100 Spearman is 0.60. Only the 70:30 default is compared with itself at 1.0. The 0:100 batter result shows how much the order depends on IPL versus T20I weighting in a pool of 8, and it is reported as descriptive.

## Tests

The chunk adds 36 tests (22 + 14, about 117 assertions). They include an independent pandas count of batter pressure samples, a leave-player-out residual check, seed reproducibility of the match bootstrap, and a check that selection does not depend on scores. They also cover short-pool no-padding, the Phase 2.5 threshold parsing, and a real-output test that checks exploratory labelling, no names and no zero-fill. The evidence shows the full suite at 290 passed, ruff check clean and ruff format clean, and a twice-run determinism comparison. I did not re-run the suites. A cross-check of the report figures against the JSON (pressure delivery counts, the Phase 2.5 threshold values 120/192/120/144, and the eight config hashes) is consistent.

</details>

<details>
<summary>File map</summary>

- `config/pressure_eligibility_rules_v1.json`: pre-declared definition grid and ladders.
- `app/analytics/pressure_eligibility.py`, `pressure_eligibility_report.py`: samples, harness, selection, report.
- `app/analytics/pressure_format_sensitivity.py`, `pressure_format_report.py`: format-weight rerun and report.
- `app/analytics/normalization_engine.py`: additive injection arguments only.
- `scripts/run_pressure_eligibility.py`, `scripts/run_pressure_format_sensitivity.py`: runners.
- `tests/test_pressure_thresholds.py`, `tests/test_phase3_format_sensitivity.py`: 36 new tests.
- `data/reports/pressure_threshold_experiment.json`, `pressure_eligibility_report.md`, `pressure_format_weight_sensitivity.json`, `.md`: outputs.

</details>
