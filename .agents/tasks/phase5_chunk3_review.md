# Chunk 3 review: investigations, sensitivity, ranking stability

**Verdict**: APPROVED

Chunk 3 adds the reliability investigation, the sensitivity grids and the bootstrap ranking-stability study, all driven by scripts and reports written from running code. The verification file shows 39 new tests, 690 passing in the full suite, ruff clean, and an independent split-half spot check (r = 0.243385 from both implementations, difference 8.3e-17). Phase 4 scores are reproduced exactly (max abs diff 0.0 over 1,345 players) before any new number is produced. I did not re-run the suites. I spot-checked the report artifacts only.

Watch for: (1) the Phase 4 noise model divides a per-ball variance by a Kish match count, so the "SNR at or below zero" finding is partly an estimator artifact. The chunk reports this but does not fix it, which is correct while the methodology is unlocked (confirmed). (2) Every ranking remains unstable (expected Top 10 overlap 4.9 to 6.2 of 10) and all publication gates still fail (confirmed, documented). (3) There is no git repo, so "local diff" could not be produced; review was against the artifacts and the verification file.

## High-level view

The investigation shows that the SNR failure comes from the noise basis. With independent-ball or match-cluster noise, tau2 is positive in 4 of 4 cells, but model-free split-half reliability is only 0.25 to 0.42. The estimator was deliberately left unchanged. Sensitivity covers the four definitions, thresholds, shrinkage, baselines, 8 format-weight configs and TEST set composition. Bowler-specific signals appear only as SENSITIVITY_ONLY. Stability uses 1000 match-cluster resamples with seed 20260512, with context re-aggregation on the same stored residuals and no per-context model.

<details>
<summary>Issues (3)</summary>

1. **Noise model undecided** (confirmed, non-blocking) — the Phase 4 noise basis needs an explicit methodology decision before the lock; this is carried in the unresolved-issues list.
2. **Bootstrap intervals not bias-corrected** (confirmed, non-blocking) — percentile intervals can sit off the point value; stated in the report, and one test was relaxed to match. Consider BCa intervals if the intervals are ever relied on.
3. **No VCS** (confirmed, non-blocking) — changes cannot be diffed; the evidence file was used instead.

</details>

<details>
<summary>Details</summary>

## Requirement coverage

Primary `any|q0.75` and the named alternatives `chase|q0.9`, `any|q0.9` and `chase|q0.75` all appear. The definitions CSV has 9 definitions with `is_primary` and `is_named_alternative` flags. The format-weight CSV has exactly 8 distinct config_ids. The investigation report covers variance decomposition, split-half, reliability against opportunities, required-sample projection (labelled DESCRIPTIVE_PROJECTION), a detectability simulation, bowler signals, IPL/T20I pooling, a section on what the data cannot support, unresolved issues and failing gates. Nothing is claimed as unsupported without an explanation.

## Honesty and scope

All three reports open with EXPERIMENTAL_NOT_VALIDATED, "TEST outcomes: not used. Cricsheet: not used". Every "validated" occurrence is a negation or a gate listing. A grep of `app/phase5` finds no Cricsheet reference, and AST tests enforce this and the absence of TEST opening. The phase5 lock log has 0 events. The SHA-256 of the Phase 4 lock log is unchanged. The Phase 4 report files are byte-identical.

## Determinism and tests

Seeded bootstrap (20260512, 1000 draws), with a determinism test. The tests recover known variance components on simulated data (tau2 0.04, sigma2 1.0, ICC 0.8, SB about 0.8), compare `half_stats` with a plain Python loop, and check projection and Kendall values by hand.

## Not tested

TEST set sensitivity is set composition only, by design. The effect of a later TEST evaluation not being a pristine hold-out is documented, not testable.

</details>

<details>
<summary>File map</summary>

app/phase5/{reliability,investigation,pressure_signals,sensitivity,stability,outputs,spotchecks,pipeline}.py; scripts/phase5_{investigation,sensitivity,ranking_stability}.py; config/phase5_investigation_v1.json; tests/test_phase5_investigation.py; data/reports/phase5_{investigation_report,sensitivity_report,ranking_stability}.md plus CSV/JSON.

</details>
