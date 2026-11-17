# Phase 5 unresolved issues

Status: EXPERIMENTAL_NOT_VALIDATED. Nothing here is validated. No ranking is published.

| # | issue | current state (from the stored outputs) | needed from you |
|---|---|---|---|
| 1 | Strict uncapped selection | Disabled. No authoritative cap source keyed by player_id. VERIFIED_CAPPED 0, DERIVED_CAPPED 655, VERIFIED_UNCAPPED 0, UNKNOWN 562. | An authoritative source with player ids. |
| 2 | 42 late T20I match dates | Original dates kept. Evidence classes: {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}. None is verified against an official record. | Official match-level dates for the 42 matches. |
| 3 | Data-weight gate | Fails for all 4 format-role cells (THRESHOLD_NOT_VALIDATED). Working pools are internal only. | A decision on how the data-weight gate can be met, or more data. |
| 4 | Methodology validation | validated=false in config/phase5_methodology_status_v1.json. The definition any|q0.75 is the rule winner of nine candidates and is not shown to be better. Only a human edit can change this. | Your review and, if you agree, a signed validation record. |
| 5 | Between-player variance not identified | The between-player moment is negative in every cell and every context (48 of 48), so shrinkage sits at its variance floor (k = 25) and scores are mostly shrinkage targets. | A decision whether to keep shrinkage as is, change the model, or collect more data. |
| 6 | Ranking instability | - Primary definition, non-trivial cells (4): the point Top 10 keeps on average 4.9 to 6.2 of its 10 members in a resampled Top 10; two independent resamples agree on 3.1 to 5.3 of 10. Fewer than 10 means the membership of the Top 10 depends on which matches happen to be in the sample.; - 21 of the 40 point-Top-10 slots in these cells have a Top-10 inclusion probability below 0.5. | Nothing to supply. This limits any selection use. |
| 7 | Primary TEST-set strictness | PRIMARY_RESTRICTED 99 matches, STRICT_OFFICIAL_ONLY 0, SENSITIVITY_ALL 144. | Choose which set counts as primary for a later TEST evaluation. |
| 8 | TEST is not a pristine hold-out | Phase 4 opened TEST once (FREEZE, OPEN, CLOSE) and aggregate results were shown in its summary. Phase 5 did not open it and its lock log is empty. | Accept that a later TEST run is not pristine, or supply fresh data. |
| 9 | Minimum pool sizes | Internal 5 and public 10 are provisional values. | Confirm or change the two numbers. |
| 10 | Refit has no hold-out | The TRAIN+VALIDATION refit used VALIDATION for fitting, so no out-of-sample check of the refit exists. | Decide whether a new hold-out is needed before any use. |


## Publication gates still failing

['data_weight_gate_passed', 'methodology_validated', 'date_verification']. `PUBLIC_ALLOWED` needs every applicable gate to pass. Request-level gates (`strict_classification_available`, `min_eligible_pool`) apply on top for requests that use them.
