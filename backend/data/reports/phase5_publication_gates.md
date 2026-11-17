# Phase 5 publication gates

Status: EXPERIMENTAL_NOT_VALIDATED. `PUBLIC_ALLOWED` requires every applicable gate to pass. A missing, unreadable or malformed input fails its gate (`INPUT_UNAVAILABLE`). Only a human edit of `config/phase5_methodology_status_v1.json` can set `methodology_validated`.

## Gate definitions
| gate | passes when |
|---|---|
| data_weight_gate_passed | none of the four format-role cells is `THRESHOLD_NOT_VALIDATED` in `phase4_frozen_choices.json` |
| methodology_validated | `validated: true` with non-blank `validated_by`, `validated_date`, `evidence_path` |
| strict_classification_available | applicable only to requests using uncapped or verified filters; passes when `strict_uncapped_enabled` |
| min_eligible_pool | eligible rows after all filters >= 10 (provisional) |
| date_verification | date-verification summary reports the gate as passed (not yet run in this chunk: fails with `NOT_RUN`) |


## descriptive (no rows, no strict filter)
publication_status: **INTERNAL_EXPERIMENTAL_ONLY**; failing: ['data_weight_gate_passed', 'methodology_validated', 'date_verification']
| gate | passed | applicable | detail |
|---|---|---|---|
| data_weight_gate_passed | no | yes | 4 of 4 cells THRESHOLD_NOT_VALIDATED |
| methodology_validated | no | yes | methodology not validated |
| strict_classification_available | yes | no | not applicable: request uses no strict status filter |
| min_eligible_pool | yes | no | not applicable: evaluated per request with rows |
| date_verification | no | yes | 0 of 42 late T20I matches are official-verified; classes {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}; none verified against an authoritative record unless supplied |


## ranking with rows (pool of 10 assumed)
publication_status: **INTERNAL_EXPERIMENTAL_ONLY**; failing: ['data_weight_gate_passed', 'methodology_validated', 'date_verification']
| gate | passed | applicable | detail |
|---|---|---|---|
| data_weight_gate_passed | no | yes | 4 of 4 cells THRESHOLD_NOT_VALIDATED |
| methodology_validated | no | yes | methodology not validated |
| strict_classification_available | yes | no | not applicable: request uses no strict status filter |
| min_eligible_pool | yes | yes | 10 eligible rows, minimum 10 |
| date_verification | no | yes | 0 of 42 late T20I matches are official-verified; classes {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}; none verified against an authoritative record unless supplied |


## strict-uncapped request
publication_status: **INTERNAL_EXPERIMENTAL_ONLY**; failing: ['data_weight_gate_passed', 'methodology_validated', 'strict_classification_available', 'date_verification']
| gate | passed | applicable | detail |
|---|---|---|---|
| data_weight_gate_passed | no | yes | 4 of 4 cells THRESHOLD_NOT_VALIDATED |
| methodology_validated | no | yes | methodology not validated |
| strict_classification_available | no | yes | STRICT_UNCAPPED_DISABLED |
| min_eligible_pool | yes | yes | 10 eligible rows, minimum 10 |
| date_verification | no | yes | 0 of 42 late T20I matches are official-verified; classes {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}; none verified against an authoritative record unless supplied |


## Dynamic filter-driven ranking
Every dynamic ranking, context preview, coverage page and filter catalog response carries `publication_status` and `gate_results`, produced by the same `apply_gates` call as the other rankings (one enforcement point in the service layer, not in the routes). Internal routes (`/api/v1/internal/rankings/dynamic...`, admin token required) return rows labelled `INTERNAL_EXPERIMENTAL_ONLY`. Public twins (`/api/v1/dynamic-rankings...`) answer 403 `PUBLICATION_GATE_NOT_SATISFIED` with the failing gates and no rows.

Per-request gate inputs: `min_eligible_pool` uses the final pool after every filter; `strict_classification_available` becomes applicable when the request uses a verified status filter (`VERIFIED_CAPPED`, `VERIFIED_UNCAPPED`). A filter never changes the other gates: a context with a small sample is reported as `INSUFFICIENT_SAMPLE_FOR_CONTEXT` and the global `data_weight_gate_passed` stays failed. Contexts also report the Phase 4 marginal data-weight gate per context (`CONTEXT_DATA_WEIGHT_GATE_NOT_PASSED`).

Measured coverage (precomputed, `p5_context_coverage`): 3888 valid filter combinations, 432 disabled (strict uncapped), 1889 reach the internal minimum pool (5), 1558 reach the public-size rule (10). Reaching the pool-size rule is only one gate: `data_weight_gate_passed`, `methodology_validated` and `date_verification` still fail, so no combination is publishable.
