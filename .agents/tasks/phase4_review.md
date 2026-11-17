# Phase 4 final review
**Verdict**: APPROVED (experimental scope only)

Relied on phase4_verification.md (509 tests passed, ruff check/format clean, run_phase4 all steps exit 0), phase4_user_summary.md, and the hash files. Full suites were not re-run. Spot check: no frontend source files (tsx/jsx/vue/html/css) exist under d:/Data; user summary shows 0 verified Uncapped and 0 fabricated labels.

## Checks
- Scope: no official rankings, no ML training; outputs labelled EXPERIMENTAL_NOT_VALIDATED; ranking stability presented as distributions.
- Leakage: split frozen in config before evaluation; 0 matches in multiple periods; par strictly prior with same-day exclusion, missing flagged and never zero; test lock FREEZE, OPEN once, CLOSE, 0 refused reads (convention-level guard, disclosed).
- Selection rule: hashed before metrics, train/validation only, not population size. Winner any|q0.75 is PROVISIONAL (3 candidates in tie margin); chase|q0.9 retained in the nine-candidate table.
- Thresholds: re-derived from TRAIN per format and role; all four cells THRESHOLD_NOT_VALIDATED; not lowered to reach ten.
- Capped/nationality: no fabrication; unproven stays Unknown; same scoring and thresholds for uncapped.
- Restrictions: 26 rules applied; DLS 3,404 rows excluded, none imputed.
- Official data: hash before/after differ only for exploratory.duckdb (the experimental store); superr.duckdb and source CSVs identical.
- Cricsheet unused as an outcome source.
- Tests: real, cover the required areas, independent-method spot checks agree.

## Non-blocking notes
1. Signal-to-noise at or below 0 in 4 of 4 cells; rankings fragile (disclosed).
2. No multiplicity correction across nine definitions (disclosed).
3. 42 T20I matches dated after 2026-05-31 (TEST last date 2026-11-01) need user confirmation (disclosed).
4. Working thresholds are below Phase 3 placeholders; listed as an open decision.
