# Phase 6 summary for review

Status: EXPERIMENTAL_NOT_VALIDATED. Everything below is internal. No official Top 10 was made, nothing was published, no model was trained for production, and no score is called validated. TEST was opened once in Phase 4 (aggregate results were shown) and is not a pristine hold-out. No independent out-of-sample validation is claimed anywhere.

## What I did
- **Cleanup.** The classification wording now names three real values (VERIFIED_CAPPED, DERIVED_CAPPED, UNKNOWN) and a disabled placeholder (VERIFIED_UNCAPPED). The always-true test assertions were replaced and a test now blocks new ones. The public `/players` directory no longer carries score, rank or eligibility fields. The ranking cache is keyed by scope and versions and returns copies.
- **Investigation.** Variance, split-half reliability, nine pressure definitions, context reliability, eligibility thresholds and data-weight options were examined. The selection criteria were written and hashed before any definition result.
- **Recent form and robustness.** 2024-onward and 2025-onward are separate analyses. Season-by-season checks are robustness checks, not validation.
- **Retention list.** A design note and an empty table exist. Nothing was imported.

## What I found
- **Between-player variance.** The estimate is at the shrinkage floor in 48 of 48 contexts. Per-context verdicts: {'MIXED': 19, 'H-C_SUPPORTED': 16, 'UNIDENTIFIED': 8, 'H-B_SUPPORTED': 4, 'NOT_ESTIMABLE': 1}. The data identify the spread between players only weakly, so most scores stay close to the pooled average. This is a finding about the data, not a bug; the floor arithmetic checks out.
- **Reliability.** Pooled odd/even reliability for the provisional definition (primary streams) is 0.37. Over 47 estimable contexts the median is 0.25. Many intervals include 0.
- **Definitions.** Result: NO_DEFINITION_PASSES. No definition was chosen and `any|q0.75` stays provisional. The comparison is confounded by different player pools.
- **Data-weight gate.** It stays at 0.5. It fails in 48 of 48 contexts. 0 of 256 option rows (18 legitimate options) pass it. The best marginal data weight is 0.56, and that option changes the methodology, so it needs your decision. Failed contexts stay restricted.
- **Required data.** Reliability 0.5 was reached in 2 of 4 cells within the tested ball ladder; 0.7 and 0.8 were not reached.
- **Recent form.** 2024-onward: 4 of 4 primary cells estimated, 0 pass the gate (best data weight 0.065). 2025-onward: 4 of 4, 0 pass (best 0.038). Shorter windows have fewer observations, so they do better on neither data weight nor intervals.
- **Seasons.** Within-season reliability: median 0.24 over 16 units, interval above 0 in 3. Adjacent-season correlation: median 0.11 over 12 units, interval above 0 in 1. This is robustness, not validation.

## What stays as it was
- Cross-source consistency of the 42 late T20I dates is not official verification. All 42 matches stay excluded.
- PRIMARY_RESTRICTED (99 matches) is for internal diagnostics only; STRICT_OFFICIAL_ONLY (0) is separate.
- Minimum pool sizes 5 and 10 are provisional and unvalidated. Results are never padded.
- Strict uncapped selection stays disabled.

## What I need from you
- Whether to keep the current shrinkage, change the model, or collect more data.
- How to treat low-reliability contexts: wider uncertainty, shorter lists or staying restricted.
- Official dates for the 42 matches, a cap source with player ids, and the retention list.
- Confirmation of the public `/players` change and the open decisions OD-1 to OD-3.

I stopped here. I will not change the official methodology or produce rankings until you review. Details: `phase6_unresolved_issues.md` and the reports it names.

## Honest limits and what the data cannot identify
- The data cannot separate genuine differences between players in pressure performance from noise. The between-player variance sits at the floor in all 48 contexts, so scores are pulled toward the average and player order inside a context is weakly supported.
- Reliability is low (pooled odd/even 0.37; median 0.25 across contexts), and many intervals include 0. No analysis here is independent validation, because TEST was opened once in Phase 4.
- Recent-form and season checks are in-sample robustness views. They show that shorter windows give less data, not better evidence.
- Which definition is best cannot be decided from this data. None passed the pre-declared criteria.

## Explicit statement
No official Top 10 was produced. No rankings were published, public or otherwise. No machine-learning model was trained. The official methodology is unchanged and the 0.5 gate is unchanged. I request your review before any methodology change or production ranking.
