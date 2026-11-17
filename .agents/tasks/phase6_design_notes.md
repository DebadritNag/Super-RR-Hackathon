# Phase 6 design notes and open decisions

Companion to `d:/Data/backend/docs/phase6_design.md`. Facts below were checked against the code on this date; the design doc has the evidence table (F1 to F15).

## Corrections to the plan (the design overrides these)

1. **Where the 0.5 gate lives.** Plan step 17 reads the gate "from the Phase 5 gate module". It is `GATE_B = 0.5` in `app/phase4/eligibility.py:36`, used in `app/phase5/context_eligibility.py:132`. The Phase 5 `data_weight_gate_passed` publication gate (`gating.py`) checks the four cell statuses (`THRESHOLD_NOT_VALIDATED`) and has no numeric 0.5. The AST scan for lowered gates must cover `app/phase4/eligibility.py`, `app/phase5/context_eligibility.py` and `app/phase5/gating.py`, and the unchanged-hash test must include `app/phase4/eligibility.py`.
2. **Floor-hit `k` values.** Plan step 11 lists `shrink_tau0.5` as 200. `k_for` uses `max(max(between, floor_abs) * mult, floor_abs)`, so the 0.5 multiplier cannot go under the floor and `k = 100`. Correct set: eb 100, tau0.5 100, tau2 50, tau4 25, floor0.001 1000; non-finite branch `1/floor`. The brief's "25 for shrink_tau4" is confirmed, and all 48 stored contexts have `k = 25.0`.
3. **A third vacuous assertion.** `tests/test_pressure_state.py:45` also has `or True` (plan step 4 already covers it).
4. **2025-onward has no TRAIN rows.** The 2025 window is exactly VALIDATION (211 matches). The plan's "fit on the window's own TRAIN-equivalent rows" cannot work there. The design fits within-window parameters on all window rows, in-sample and labelled, while B0 and thresholds stay TRAIN-fitted (identical residuals in every window).
5. **Cache key delimiter.** The current key joins fields with `|`; the design uses a JSON-encoded list so values containing `|` cannot collide.
6. **Two readings of "data weight".** Per-context B (`n_eff_min/(n_eff_min + k)`, gate 0.5) and the publication gate (cell status). The options report covers the first; the second stays failing regardless.

## Findings that shape the investigation (not conclusions)

- F6/F7: the Phase 4 noise term divides a per-ball variance by a per-match Kish count. It overstates the noise of a ball-weighted mean by roughly the balls per match, which alone could make the between-moment negative. Phase 5 already showed the sign flips on the match-cluster basis (tau2 about 0.10, ICC 0.59 for IPL batters), while the model-free split-half SB for the same cell is about 0.27. The two disagree, so the cluster basis may understate noise. The design uses the split-covariance estimator (E7) as arbiter and does not pre-judge.
- Because all 48 contexts hit the floor with the same multiplier, `k` is a constant 25 set by the shrink_tau4 assumption, not by the data. Under that choice B depends only on `n_eff`, and 0.5 needs a marginal eligible player with 25 equal-size matches. Anything that lowers `k` by assumption (tau multipliers) is excluded from the options as a disguised gate change. Options O3 and O6 estimate tau2 from data but imply a methodology change; they are flagged `requires_methodology_decision` and never applied.

## Open decisions (recorded; none blocks the work)

| ID | Decision | Default taken in the design |
|---|---|---|
| OD-1 | Primary window = PRE_TEST (723 matches), not "all matches". TEST was opened once and 42 T20I dates are unverified. | PRE_TEST only; TEST outcomes unopened |
| OD-2 | Eligibility thresholds for 2024+/2025+ windows | Phase 4 frozen ball thresholds scaled by the window's own ratio, labelled provisional |
| OD-3 | Whether to collect a clean hold-out (no pristine TEST exists) | None collected; every result is in-sample / diagnostic |
| OD-4 | If H-B (noise-model misspecification) is supported: change the shrinkage noise basis in the methodology? | Not changed; reported with evidence for the user's decision |
| OD-5 | Cross-definition comparison is confounded by different player sets | Criteria file requires the intersection-player version; rule not applied if fewer than 30 common players per cell |
| OD-6 | Remove `min_pressure_matches` from the public `/players` filter signature (it filters on an experimental pressure count) | Removed from public, kept on internal routes; a public API change, listed in the cleanup report |
| OD-7 | Keep `shrink_tau4` (assumption-driven k = 25) as the lock configuration | Unchanged; reported as an assumption in the variance report |
| OD-8 | Gamma-Poisson and beta-binomial are approximate for run streams (bounded 0 to 6) | Run as sensitivity with `MISSPECIFIED_FOR_STREAM`, not used in verdicts |
| OD-9 | `scipy` availability | Superseded by review finding 12: scipy is already a dependency; `scipy.special.gammaln` is permitted for E4/E5; REML/ML stay in numpy |
| OD-10 | Deep copy versus pickled bytes in the cache | Deep copy; switch to pickled bytes if one copy exceeds 50 ms on the largest real context |

## Items for the implementer to check first

- Run the three old vacuous assertions before replacing them. If `interval_low <= score <= interval_high` fails for a real reason (bootstrap percentile of the shrunk score with k and target fixed need not bracket the point estimate), assert the true invariant and say why in a comment. Do not reintroduce `or True`.
- Confirm no `VERIFIED_UNCAPPED` rows exist in `p5_player_classification` before narrowing the schema literal.
- Check existing API tests (`test_phase4_api.py`, `test_phase5_api.py`) for assertions on `eligible_scopes`, `conflict_flag`, `publication_status` in `/players` responses; update only those and list them.
- `window_cols` in `app/phase5/reliability.py` accepts only `TRAIN` and `PRE_TEST`. Do not edit it; build date-window masks in `app/phase6/split_half.py`.
- `phase6_prerun_hashes.json` must be verified intact before step 1 and again at the end.
- Stop conditions: no change to methodology, no publication, no TEST access, no retention import; request review after the reports and register.

## Design review fix pass (single pass; responses to findings)

| # | Sev | Response |
|---|---|---|
| 1 | HIGH | Fixed. 4.1 rule replaced with the mechanical form (per-cell R and lower bound, pooled M1 with SE1 from the same match-cluster draws, scalar M4, M2/M3/M6 descriptive, `DEFINITION_ORDER_NOT_STABLE`, `COMPARISON_CONFOUNDED`). |
| 2 | HIGH | Fixed. Append-only `p6_run_log` replaces the timestamp-vs-table check; criteria and hash files committed to git before the first run, git blob hash recorded. |
| 3 | HIGH | Fixed. 3.1 enumerates the affected files and lines, adds `ACCEPTED_STORED_VALUES`, `by_status.get(...)` and the override and strict-filter tests. |
| 4 | MED | Fixed. `official_ranking` removed from the public model; `Disabled` union kept and walked by the schema test. |
| 5 | MED | Fixed. 90% test uses E1c draws only; E2 is a sign-consistency check; E4/E5 are sensitivity only; numeric flag table and flag-to-verdict table added. |
| 6 | MED | Fixed with a changed approach. Window ratio for windows without TRAIN = window balls / PRE_TEST balls. `share_rows_in_b0_fit_window` column added. The reviewer's "2024 on VALIDATION rows only" sensitivity is not run as a separate result: VALIDATION rows from 2025-01-02 are the 2025-onward window, so 2025-onward serves as the clean-residual analysis and 2024-onward is labelled mixed-residual. |
| 7 | MED | Fixed. M6 non-pressure matched control added as a descriptive metric (not in the rule, so the criteria hash is not affected by it being unused in selection). |
| 8 | MED | Fixed. `n_eff_basis` column; O3/O6 use the match-cluster effective count; validator rejects mismatches; 4.8 regression only on `KISH_MATCH`. |
| 9 | MED | Fixed. Eight additional tests listed in section 10. |
| 10 | MED | Fixed. Final assertions written in 3.2; containment rate is recorded as a finding, not asserted. |
| 11 | MED | Fixed. Callers, tests, no-default parameters, `gate_state_hash` source and docstring rewrite specified in 3.4. |
| 12 | LOW | Fixed (scipy allowed). |
| 13 | LOW | Fixed (primary stream only in the rule). |
| 14 | LOW | Fixed in 4.7 (vectorised, 30-minute budget, `--quick` refused for report runs). The 30-minute figure is an estimate, not measured. |
| 15 | LOW | Fixed (deliverable map and register carry-forward in section 11). |

## Residual open decisions after the fix pass

| ID | Decision | Default taken |
|---|---|---|
| OD-11 | The 0.01 ratio used for H-A power and the cut-offs in the 4.4 flag table (25%, 1.5/0.67, ICC 0.05, dispersion 1.5, 90% draw share) are declared by the designer, not derived from data. | Fixed in the plan file before any run; shown as provisional; the user may change them at review, before a rerun. |
| OD-12 | M6 is descriptive only. If the user wants it to gate a definition, the criteria file must be rewritten and the investigation rerun from the plan step. | Descriptive only. |
| OD-13 | The 30-minute runtime budget and the 50 ms deep-copy threshold are estimates. | Measured by the implementer and reported; no design change unless exceeded. |
| OD-14 | `evaluate_gates` as the source of failing-gate ids for `gate_state_hash` was named from the review description; the implementer confirms the actual function name in `app/phase5/gating.py` and uses the one that `Phase5Service._full` already calls. | Use the existing call; record the name in the cleanup report. |
| OD-15 | Test file names for cache tests (`tests/test_phase5_cache*.py`) are patterns, found by grep before editing. | Grep first. |