# Phase 5 summary for review

**Everything here is experimental. Nothing is validated. No Top 10 is published. I have stopped for your review.**

## What was done
- Moved player classification to four separate statuses (verified capped, derived capped, verified uncapped, unknown). Strict uncapped selection is switched off.
- Checked the 42 late T20I dates against the other sources in the data. The original dates are kept and unchanged.
- Ran reliability, sensitivity and ranking-stability studies for the provisional definition `any|q0.75` and the alternatives `chase|q0.9`, `any|q0.9`, `chase|q0.75`.
- Built the filter-driven ranking engine (one scoring model; filters only select who is compared). It is internal only and every response carries the failing gates.
- Wrote a methodology lock (label EXPERIMENTAL_LOCK) and one refit on TRAIN + VALIDATION. TEST was not opened.

## Real numbers
- Players: 1,217. VERIFIED_CAPPED 0, DERIVED_CAPPED 655, VERIFIED_UNCAPPED 0, UNKNOWN 562.
- 42 late T20I dates: evidence classes {'DATE_CONSISTENT_ACROSS_SOURCES': 36, 'DATE_SINGLE_SOURCE': 6, 'DATE_CONFLICT': 0, 'DATE_UNVERIFIED': 0}. None is checked against an official record.
- TEST-set options: restricted primary 99 matches, official-only 0, all 144.
- Definition axis: over 31 non-trivial single-format comparisons the Top-10 overlap with the primary ranges from 0 to 8 of 10 (median 4.0), Spearman from 0.27 to 0.90. The ordering depends on the pressure definition.
- Shrinkage axis: against the same definition's frozen shrinkage the Top-10 overlap ranges from 0 to 10 (median 9.0); Spearman -0.87 to 1.00.
- Primary definition, non-trivial cells (4): the point Top 10 keeps on average 4.9 to 6.2 of its 10 members in a resampled Top 10; two independent resamples agree on 3.1 to 5.3 of 10. Fewer than 10 means the membership of the Top 10 depends on which matches happen to be in the sample.
- 21 of the 40 point-Top-10 slots in these cells have a Top-10 inclusion probability below 0.5.
- Filter combinations: 3888; 432 are disabled (strict uncapped); 1889 reach the internal minimum pool of 5; 1558 reach the public-size rule of 10 (size alone does not make anything publishable).
- Refit on TRAIN+VALIDATION: 167,913 delivery rows, 723 matches, 2022-01-22 to 2025-12-19. Top-10 overlap with the Phase 4 scores per cell: IPL batter 9/10, IPL bowler 9/10, T20I batter 9/10, T20I bowler 10/10. Spearman between old and new scores (eligible players): 0.99, 0.99, 0.99, 0.99.
- Phase 4 tables and reports byte-identical after the refit: True. TEST rows used: 0.

## Gates still failing (exact)
- `['data_weight_gate_passed', 'methodology_validated', 'date_verification']`.
- `data_weight_gate_passed`: all 4 format-role cells are THRESHOLD_NOT_VALIDATED.
- `methodology_validated`: validated=false; only a human edit can change it.
- `date_verification`: 0 of 42 late T20I matches are verified against an official record.
- Request-level: `strict_classification_available` (no authoritative cap source) and `min_eligible_pool`.

## Unresolved issues
See `phase5_unresolved_issues.md` (ten items). The main ones: the between-player variance cannot be identified (shrinkage sits at its floor in all 48 contexts), the rankings move a lot between resamples, TEST is no longer a pristine hold-out, and the refit has no out-of-sample check.

## Decisions needed from you
1. Supply an authoritative cap source with player ids (to enable strict uncapped), or keep it off.
2. Supply official match-level dates for the 42 matches, or confirm they stay excluded from the primary chronological TEST evaluation.
3. Choose which TEST set is primary (restricted, official-only, all), and accept that a later TEST run is not pristine.
4. Confirm or change the minimum pool sizes (internal 5, public 10).
5. Say whether the data-weight gate can be met and how. Nothing becomes public before it does.
6. Whether to approve any validation of the pressure definition, official rankings or official ML training. None is approved now.

## Stop for review
I have not published a Top 10, not trained an official model, not opened TEST and not changed the official data. I will not go further until you review this. The lock hash is `ea50abd44c4152eb1d5597d700f81acdd2d6a40b0a1828964d2e02f133c89595`.
