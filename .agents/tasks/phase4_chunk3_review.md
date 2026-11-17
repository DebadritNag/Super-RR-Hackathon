# Phase 4 chunk 3 review: definition comparison, eligibility, shrinkage, format weights, ranking stability

All results are EXPERIMENTAL_NOT_VALIDATED.

**Verdict**: APPROVED

Chunk 3 compares the nine pressure definitions with a selection rule written before any metric was computed. It derives eligibility thresholds from the data and does not lower any of them. It reruns the eight format weights under one frozen eligibility rule set, and it produces ranking distributions that are not padded. The evidence file is present and complete. I ran only the chunk-3 test file as a spot check, and all 26 tests passed. The full suite and Ruff results (417 passed, Ruff clean) are taken from the verification file.

Watch for: the definition choice is weak, the thresholds are not validated, and between-player signal is undetectable. All three are disclosed in the reports and none blocks approval.

## High-level view

The rule file `phase4_definition_rule_v1.json` was written at 18:01:23. The comparison CSV was written at 18:19:01 and the frozen choices at 18:19:12. The rule's SHA-256 is carried in the selection output and in the frozen choices. Selection uses TRAIN and VALIDATION only. Eligible population size is a report-only item and is never a selector. Test rows were never loaded and the lock stayed closed. The single test evaluation is deferred to chunk 5, as the brief requires.

The selected `any|q0.75` is a lexicographic tie-break winner inside a statistically indistinguishable top group (Sc 0.24 to 0.26). The reports label it PROVISIONAL and flag that it also has the largest pressure population. They include a sample-size confound check, and the full nine-candidate table is retained. `chase|q0.95` and `inn1|q0.95` are marked NOT_RANKABLE. `chase|q0.9` is rankable (Sc 0.17) but falls outside the top group.

All four cells (IPL/T20I x batter/bowler) came out THRESHOLD_NOT_VALIDATED, and no threshold was lowered. Downstream experiments use a pool labelled `ELIGIBLE_WORKING_POOL_NOT_VALIDATED`, built from the TRAIN median of per-player pressure balls. A test checks that a pool without a threshold is empty and not padded. The pools are small (combined 48 batters, 39 bowlers), which is the honest result.

Definition sensitivity and format-weight sensitivity are separate outputs and are not crossed. The format report fixes the definition and the shrinkage and refers to the definition report for the other axis. The test `test_sensitivity_tables_are_one_factor_not_a_joint_grid` enforces this. A missing format is never zero-filled, and 70:30 is not described as validated. Ranking summaries do not pad the pool. Top-10 inclusion probabilities sum to exactly 10 in each of the four pools.

<details>
<summary>Issues (4)</summary>

1. **Weak definition choice** (confirmed) — Selection shares are about 0.3 and the top three definitions are indistinguishable. Keep the PROVISIONAL label and present the choice as a tie-break outcome in the user summary.
2. **No detectable between-player signal** (confirmed) — SNR is negative in every cell and bowler split-half reliability is near 0. Say plainly in the user summary that rankings are fragile (expected Top-10 overlap about 5 to 6 of 10).
3. **Bowler pressure uses batter state signals** (confirmed) — Bowler signal B is not implemented. State this in the user summary and the limitations section.
4. **Unrun sensitivities** (confirmed) — `shrink_mu_window` and the unscaled-eligibility sensitivities were not run, and thresholds are held fixed across bootstrap resamples. All three are disclosed in the reports and should appear in the limitations section.

</details>

<details>
<summary>Details</summary>

## Selection rule fixed before test outcomes

The rule file predates every metric file by about 18 minutes. Its hash is recorded in the selection output. The frozen choices record the definition, the TRAIN-only thresholds, the shrinkage choice and the baseline version before any test evaluation. Tests cover the nine-candidate rule file, a large-population low-reliability candidate that does not win, a lexicographic tie-break, and the case where no rankable candidate exists. The population confound is reported, not used.

## No threshold lowering and no padding

The decision function takes the smallest passing threshold and never lowers one. With no valid threshold it returns THRESHOLD_NOT_VALIDATED, and the fallback needs both a floor and a positive interval. `test_eligible_mask_without_threshold_is_empty_and_pool_not_padded` and `test_rank_summary_inclusion_sums_and_never_pads` cover this. The working pool is labelled as not validated everywhere it is used.

## Format weights and baseline alternatives

Batter Top-10 overlap with 70:30 is 9 for IPL-only, 85:15 and 80:20, 7 at 50:50, and 3 for T20I-only. Bowler overlap is 5 for T20I-only and 9 to 10 elsewhere. I independently confirmed one stored Spearman from the verification file against the stored player table. Baseline alternatives correlate above 0.95 with the default baseline in every cell.

</details>

<details>
<summary>File map</summary>

- `app/phase4/engine.py`: pressure rows, match-cluster resampling and rank utilities
- `app/phase4/definitions.py` and `config/phase4_definition_rule_v1.json`: nine-candidate comparison with a pre-declared rule
- `app/phase4/eligibility.py`: data-derived thresholds per cell
- `app/phase4/sensitivity.py`: shrinkage, eight format weights, baseline alternatives, ranking stability
- `scripts/phase4_sensitivity.py`: orchestration and the freeze step
- `tests/test_phase4_chunk3.py`: 26 tests

</details>
