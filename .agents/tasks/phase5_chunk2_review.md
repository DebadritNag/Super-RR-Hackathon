# Phase 5 Chunk 2 review: T20I date verification, restricted TEST set

**Verdict**: APPROVED

Chunk 2 classifies all 42 late T20I matches without modifying any date. None is marked official-verified. TEST stays unopened and the restricted set definitions are frozen in a manifest. The evidence file was present and complete. Suites were not re-run. One narrow spot-check was done, and it agreed with the evidence.

Watch for: the primary-set strictness is an open decision (plan D2); results are experimental and not validated.

## High-level view
Original dates are preserved. The report adds evidence columns and a class per match (consistent 36, single source 6, conflict 0, unverified 0, official 0). Only the user-supplied template path can produce OFFICIAL_VERIFIED, and incomplete rows are reported without being applied.

Cricsheet is read only inside `app/phase5/date_verification.py`. `test_manifest.py` imports only the class constants from it. The evidence states an AST test covers `app/phase4`, `app/phase5`, `app/analytics` and `pressure_service`.

TEST was not opened. `phase5_lock_log.json` is `[]`. The `phase4_lock_log.json` hash was recomputed in the spot-check as cae1e06c...75c, which equals the before/after value in the evidence.

## Issues (3, all non-blocking)
1. **Primary-set strictness (possible, open decision D2)**: PRIMARY_RESTRICTED (55 matches / 12,599 deliveries / 283 players) admits early matches that are consistent across sources but not official, and drops all 42 late ones. The brief's default says anything non-official counts as unverified. STRICT_OFFICIAL_ONLY (0 matches) is frozen alongside, so the user can choose. Present the choice at final review.
2. **Single-source dates (confirmed)**: 6 matches (Afghanistan v India, Afghanistan v Zimbabwe) rest on one source because Cricsheet has no Afghanistan 2026 fixtures. They are correctly excluded from the primary set. Keep them flagged.
3. **Plan hash discrepancy (confirmed, documentation only)**: the plan quoted 86f5ce9d... as the lock log hash. That is the frozen-choices hash. The evidence records the correct value, so later chunks should use cae1e06c....

## Details
<details><summary>Checks</summary>

- Original dates untouched: guards hash the `matches` date column and the four source CSVs before and after. The 42 dates are compared with an independent `csv` read.
- Classification logic: `classify` assigns CONSISTENT, SINGLE, CONFLICT and UNVERIFIED. Official status is set only from complete user rows. Tolerance is config-driven.
- Primary TEST excludes unverified, with real counts reported: 55/12,599/283 primary and 144/33,086/417 sensitivity. 89 matches and 20,487 deliveries are excluded. The 2 abandoned matches (48513, 50189) are unverified.
- Template: `config/t20i_official_date_verification_template.csv` and a report copy.
- Tests: 25 tests, including a realdata test that recomputes the 42 ids and timestamp statuses from raw CSVs, plus AST import enforcement.
- Determinism: three runs gave identical hashes.
</details>

<details><summary>Files</summary>

`app/phase5/{date_verification,test_manifest,lockguard,data}.py`, `scripts/phase5_date_verification.py`, `config/phase5_date_verification_v1.json`, the template CSV, `tests/test_phase5_date_verification.py`, and the reports and manifest.
</details>
