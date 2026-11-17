# Phase 5 Design Review (second pass)

Reviewed: `d:/Data/backend/docs/phase5_design.md` (including its Open decisions section 10 and review responses section 11) and `d:/Data/.agents/tasks/phase5_design_notes.md`, against `phase5_brief.md` and `phase5_plan.md`.

Rule applied: second pass. MEDIUM and NIT findings that are recorded as open decisions do not block. Only an unresolved HIGH blocks.

Verdict: APPROVED (0 HIGH). Two MEDIUM findings and two NITs are listed below. They are carried to the implementer as open items, not blockers.

## Findings

1. MEDIUM. Shrinkage floor arithmetic is stated wrongly (design 4.3 item 3).
   - The design says that on a floor hit `k = sigma2 / (0.01 * sigma2) = 100`, and that scores are "pulled almost entirely to the target". It also writes the condition as `tau2 <= tau2_floor (0.01 ...)`, which reads as an absolute floor.
   - In `app/phase4/shrink.py:k_for` the floor is relative: `floor_abs = 0.01 * sigma2`. The multiplier applies after the floor: `tau2 = max(max(between, floor_abs) * mult, floor_abs)`. For the locked choice `shrink_tau4` (mult 4), a floor hit gives `tau2 = 4 * floor_abs` and `k = 25`, not 100.
   - `k = 100` (`1 / floor`) applies only to the non-estimable branch (`sigma2` not finite or `between` not finite).
   - Fix: state `floor_abs = floor * sigma2`. State that floor-hit `k = 1 / (floor * mult)` (25 for `shrink_tau4`). State that the `k = 1 / floor` case applies only when `sigma2` or `between` is not finite. Replace "reliability about zero by construction" with the reliability implied by that `k`. Add a unit test of `k_for` that pins both values.

2. MEDIUM. Context eligibility uses VALIDATION for the window ratio (design 4.5 item 3 and 9 item 2).
   - The design says this is "exactly as Phase 4 did". The brief requires context thresholds derived from the observed distribution with the same method, and context tau2 TRAIN-only. The design meets both for tau2 and for the ball threshold.
   - The VALIDATION-based window ratio is a selection step that touches VALIDATION data. It is not a leak into TEST. It means that VALIDATION scores for these contexts are no longer fully out-of-sample.
   - Fix: add a sentence to the architecture report and to open decision 9 stating that context eligibility is chosen using VALIDATION and so VALIDATION is not a clean hold-out for the context rankings.

3. NIT. Notes (`phase5_design_notes.md`) describe the Cricsheet source as "exact date". The design uses `AGREE_EXACT` and records off-by-one as a disagreement, so the two documents are consistent. The notes should also say that identity uses toss, venue and XI. Add that.

4. NIT. Design 2.2(a) states independence of timestamps from `matches.match_date` is "assumed, not shown". This is flagged in open decision 13. Nothing further needed.

## Verified assumptions

- `shrink.CONFIGS["shrink_tau4"]` exists with floor 0.01 and mult 4.0. `fit_cell` runs on TRAIN input only and requires at least 2 players. `k_for` has a floor-hit flag. The design's use of these names is correct.
- No per-filter model training. Context tau2 is fitted once per atomic context (48 cells) at build time. The design says `fit_cell` is never called from the request path and requires a test. Filters re-aggregate stored `n, s, s2` rows. This is consistent with the brief.
- Strict uncapped cannot return approximations. The `uncapped_guard()` check runs before any score read. `VERIFIED_UNCAPPED` filters, presets, composition constraints and `include_uncapped` all return `STRICT_UNCAPPED_DISABLED` with `rows: []`. `UNKNOWN_STATUS` is a separate labelled group. `include_unknown_status` adds unknown players flagged `UNKNOWN_INCLUDED`, never labelled uncapped. There is no "not capped" filter that could stand in for uncapped.
- Capped status uses three separate values. The migration is explicit, fails on unmapped combinations and asserts counts 0 / 655 / 0 / 562. It imports no names, squad, domestic or IPL tables.
- TEST: no call to `evaluate_frozen`, no write to `phase4_lock_log.json`, SQL filter excludes TEST for scoring frames, and the refit asserts the period set is `{TRAIN}`.
- Cricsheet: confined to `date_verification.py`, outcome columns are never loaded (column whitelist), and an AST test bars scoring modules from importing it. Correction 0.1 item 1 removes the plan's winner and total identity checks.
- Original dates unchanged: no write path, SHA-256 of the `matches` date column before and after.
- Gates fail closed, are enforced in one service function, and `methodology_validated` can only be set by a human edit.

## Unverified or wrong assumptions

- Wrong: floor-hit `k = 100` for `shrink_tau4` (finding 1).
- Unverified by me, recorded by the design as a build-time risk (design section 11): that `candidate_thresholds`, `evaluate_cell` and `decide` run unchanged on a 48-context cell. The design assigns it as the first task of the context-eligibility chunk, with a wrapper fallback.
- Unverified: independence of timestamp and Cricsheet date sources. Recorded as open decision 13.
- Unverified: the claims of 42 and 144 match counts and the 655/562 counts. These come from the plan and Phase 4 reports. The design requires recomputation from raw files in real-data tests.
- Residual hold-out risk: Phase 4 aggregate TEST results were already shown to the user. Recorded as open decision 1.

## Blocking summary

HIGH: 0. MEDIUM: 2 (carried as open items). NIT: 2. Verdict: APPROVED.
