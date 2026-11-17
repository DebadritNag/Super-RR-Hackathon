# Phase 6 chunk 3 review

## Summary
Chunk 3 adds the definition comparison, context reliability, eligibility reliability and data-weight options investigation. The evidence supports brief decisions 4, 5 and 8: selection criteria are hashed before results and refused on mismatch, no player columns reach the comparison, no TEST rows are read, the 0.5 gate stays unchanged, and options are labelled ACTUAL_RE_ESTIMATE or DESCRIPTIVE_PROJECTION. The findings are negative (no definition passes, 0 of 256 option rows pass the gate), which the brief names as a valid outcome.

Watch for: O3 and O6 are pooling variants that need a methodology decision (confirmed, not applied). Match-bootstrap intervals are shifted upward (confirmed, disclosed).

**Verdict**: APPROVED

## High-level view
The definition comparison is guarded by a criteria hash. `begin_comparison` raises `ResultsHashError` when stored result tables carry a different hash than the criteria file. Tests cover missing, edited and re-hashed files. No definition passes, so no top group is named and nothing is selected by who is promoted. A column guard rejects player-level fields in definition tables.

The gate is read, never assigned, in Phase 6. `gate_used` is 0.5 in all 304 option rows. The lowered-gate idea appears only under "Excluded by rule". O7 and O8 are labelled projections. The one O6 context that appears to reach 0.56 is not counted as a pass because its marginal individual is not estimable.

Limits are disclosed: in-sample only, TEST not pristine, confounded intersection comparison, non-centred match-bootstrap intervals, and O3 as empirical-Bayes pooling rather than a full hierarchical model.

<details>
<summary>Issues (2)</summary>

1. **O3/O6 pending decision** (confirmed) — keep them unapplied until the user decides on the methodology; they are already so labelled.
2. **Match-bootstrap bias** (confirmed) — keep the disclosure wherever "lower bound above 0" counts appear; no change needed to approve.

</details>

<details>
<summary>Details</summary>

### Pre-declared criteria
Spot-check of `definition_compare.py` confirmed the hash comparison against `criteria_sha256` in stored tables and the refusal path (lines 86-99). The player-column guard is at line 462. The verification file reports an independent recomputation of a split-half value (0.6848050605, matching) and of an n_eff and a data-weight value.

### Gate integrity
Grep of `app/phase6` and `scripts/phase6_*` found no assignment of GATE_B. The report's pass count excludes O8, the pool-restriction cost, and states 0 of 256 pass. The Phase 4 `ALT_GATES` constant is untouched and unused by Phase 6.

### Not checked
Suites were not re-run, per instructions; the 995 passed result is taken from the verification file.

</details>

## File map
<details><summary>Files</summary>

`app/phase6/{definition_compare,context_reliability,eligibility_reliability,data_weight_options}.py`, matching `scripts/phase6_*.py`, four report files in `data/reports/`, 78 new tests.

</details>
