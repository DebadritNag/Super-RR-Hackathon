# Phase 5 Design Notes

Full design: `d:/Data/backend/docs/phase5_design.md`. All outputs `EXPERIMENTAL_NOT_VALIDATED`; `any|q0.75` PROVISIONAL; no TEST read; no Top 10.

## Decisions
- Classification: Capped+DERIVED -> DERIVED_CAPPED (655), Capped+VERIFIED_FROM_SOURCE -> VERIFIED_CAPPED (0), Uncapped+VERIFIED -> VERIFIED_UNCAPPED (0), Unknown -> UNKNOWN (562, shown only as UNKNOWN_STATUS). Unmapped combo raises. Override rows need source, verified_by, ISO verified_date; legacy `Capped`/`Uncapped` values rejected.
- `strict_uncapped_enabled` is computed (authoritative id-keyed source declared + validated VERIFIED rows + coverage >= 0.95); today false. Disabled -> 200 `STRICT_UNCAPPED_DISABLED` with no rows on internal routes, 403 gate response on public routes.
- Dates: originals never touched. Sources a (timestamps, +/-1 day), b/c/f internal (can only cause conflict), d (IPL only), e Cricsheet (validation-only, secondary, exact date). CONSISTENT needs >= 2 informative independent sources agreeing and no conflict. Nothing is official-verified without the user's CSV. Control group: pre-2026 T20Is.
- TEST not re-opened. Manifest freezes PRIMARY_RESTRICTED, STRICT_OFFICIAL_ONLY, SENSITIVITY_ALL; Phase 5 lock log stays empty.
- Gates: data_weight, methodology_validated (needs human-filled fields), strict_classification (when applicable), min_eligible_pool (10), date_verification. Fail closed. Enforced in one service function plus a route-enumeration test.
- Engine: stored (player, match, comp, role, stream, period, phase, situation) rows with n, s, s2; 48 atomic contexts; context tau2 from TRAIN only with documented floor (`CONTEXT_NOT_ESTIMABLE` below 8 train players, k=100 floor flag); per-context eligibility via the Phase 4 derivation; match-cluster bootstrap seeded, pool-relative ranks; no padding; ties by player_id; cache keyed by spec hash + data/model/gate version.
- Lock: manifest hashes configs, definition, thresholds, shrinkage, restrictions, locked code files, TEST manifest. Refit relabels VALIDATION as TRAIN in a copy; refuses without valid lock; not out-of-sample evidence.
- Investigations: moment + REML tau2, ICC, detectability simulation, three split-half modes, required-sample projection (NOT_ESTIMABLE when tau2 <= 0), 3 pre-declared bowler signals (sensitivity only), multi-format pooling, one-at-a-time sensitivity plus definition x shrinkage cross, stability per context.

## Corrections to the plan
1. Cricsheet identity matching must use pre-play facts (teams, toss, venue, XI), never winner/totals (would read TEST results).
2. Add split-boundary adjacency flag for dates.
3. `date_verification` gate defined precisely (no conflicts in scoring windows; designated TEST set fully official-verified).
4. Situation filters use `any|q0.75` rows by innings, not the `chase|q0.9` definition.
5. Unknown-classification toggles act only on a filtered axis.
6. Refit output is not out-of-sample evidence.

## Open decisions
Hold-out purity after Phase 4 aggregates were shown; primary TEST strictness; pool minimums 5/10; coverage 0.95; fit minimum 8 players; date source independence; unknown toggle semantics; shrinkage choice; 48-context multiplicity; refit context tables not served; unavoidable Phase 4 test edits.

## Revision (review pass 2)
- min_matches: combined = IPL+T20I pre-test sum; single format = that format. Gate date_verification (ii) deliberately unpassable without full official coverage. Cricsheet reader uses a column whitelist. VALIDATION never affects fitted params. Added open decisions 12 (TEST non-outcome ids read for counts) and 13 (date-source independence rates). Phase 4 baseline 509 tests.
