# Phase 5: T20I date verification and restricted TEST set

Status: **EXPERIMENTAL_NOT_VALIDATED**. Internal investigation only. No ranking is published.

## Statement

**No match is official-verified: no user-supplied official record is loaded. Classes below are evidence consistency only, not verification against an authoritative record.**

Original dates are preserved exactly (SHA-256 of the `matches` date column and of the database file are identical before and after the run; the 42 late dates also equal `matches.csv` read independently). Cricsheet is secondary, validation-only evidence and not an official record. It is read only by `app/phase5/date_verification.py` and is not an input to any score, baseline, threshold or ranking.

## Evidence checks

| Check | Source | Counts as agreeing source |
|---|---|---|
| (a) first/last `delivery_ist_time` date part (column carries a `UTC` suffix; compared within +-1 day, conflict at 2+ days) | updated_ball_by_ball | yes |
| (b) series ordering by match_number, spacing, a team on two matches on one date | matches | no (internal) |
| (c) competition season/year token vs date year (competitions.csv has no date windows) | competitions.csv | no (internal, weak) |
| (d) `matches 2026.csv` (IPL 2026 only, first 39 matches) | matches 2026.csv | yes, IPL only |
| (e) Cricsheet date for the same team pair within 3 days, identity confirmed by first-innings team and total | cricsheet_index | yes |
| (f) internal conflicts (any failed internal check or source disagreement) | derived | creates DATE_CONFLICT |

## Class distribution

| Class | 42 late T20I matches | All TEST-period matches checked |
|---|---|---|
| DATE_CONSISTENT_ACROSS_SOURCES | 36 | 135 |
| DATE_SINGLE_SOURCE | 6 | 9 |
| DATE_CONFLICT | 0 | 0 |
| DATE_UNVERIFIED | 0 | 2 |

Official-verified among the 42: **0**. Publication gate `date_verification`: passed = False.

## The 42 T20I matches dated after 2026-05-31

| match_id | series | teams | original date | timestamp | Cricsheet | ordering | class |
|---|---|---|---|---|---|---|---|
| 45390 | India in England T20I Series 2026 | England v India | 2026-07-01 | AGREE (2026-07-01) | AGREE (2026-07-01) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 45391 | India in England T20I Series 2026 | England v India | 2026-07-04 | AGREE (2026-07-04) | AGREE (2026-07-04) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 45392 | India in England T20I Series 2026 | England v India | 2026-07-07 | AGREE (2026-07-07) | AGREE (2026-07-07) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 45393 | India in England T20I Series 2026 | England v India | 2026-07-09 | AGREE (2026-07-09) | AGREE (2026-07-09) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 45394 | India in England T20I Series 2026 | England v India | 2026-07-11 | AGREE (2026-07-11) | AGREE (2026-07-11) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 45489 | Sri Lanka in England T20I Series 2026 | England v Sri Lanka | 2026-09-15 | AGREE (2026-09-15) | AGREE (2026-09-15) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 45490 | Sri Lanka in England T20I Series 2026 | England v Sri Lanka | 2026-09-17 | AGREE (2026-09-17) | AGREE (2026-09-17) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 45491 | Sri Lanka in England T20I Series 2026 | England v Sri Lanka | 2026-09-19 | AGREE (2026-09-19) | AGREE (2026-09-19) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50340 | India in Ireland T20I Series 2026 | Ireland v India | 2026-06-26 | AGREE (2026-06-26) | AGREE (2026-06-26) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50341 | India in Ireland T20I Series 2026 | Ireland v India | 2026-06-28 | AGREE (2026-06-28) | AGREE (2026-06-28) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50404 | West Indies in India T20I Series 2026 | India v West Indies | 2026-10-06 | AGREE (2026-10-06) | AGREE (2026-10-06) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50405 | West Indies in India T20I Series 2026 | India v West Indies | 2026-10-09 | AGREE (2026-10-09) | AGREE (2026-10-09) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50406 | West Indies in India T20I Series 2026 | India v West Indies | 2026-10-11 | AGREE (2026-10-11) | AGREE (2026-10-11) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50407 | West Indies in India T20I Series 2026 | India v West Indies | 2026-10-14 | AGREE (2026-10-14) | AGREE (2026-10-14) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50408 | West Indies in India T20I Series 2026 | India v West Indies | 2026-10-17 | AGREE (2026-10-17) | AGREE (2026-10-17) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50503 | Sri Lanka in West Indies T20I Series 2026 | West Indies v Sri Lanka | 2026-06-12 | AGREE (2026-06-12) | AGREE (2026-06-11) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50504 | Sri Lanka in West Indies T20I Series 2026 | West Indies v Sri Lanka | 2026-06-14 | AGREE (2026-06-14) | AGREE (2026-06-13) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50505 | Sri Lanka in West Indies T20I Series 2026 | West Indies v Sri Lanka | 2026-06-15 | AGREE (2026-06-15) | AGREE (2026-06-14) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50507 | India in Zimbabwe T20I Series 2026 | Zimbabwe v India | 2026-07-23 | AGREE (2026-07-23) | AGREE (2026-07-23) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50508 | India in Zimbabwe T20I Series 2026 | Zimbabwe v India | 2026-07-25 | AGREE (2026-07-25) | AGREE (2026-07-25) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50509 | India in Zimbabwe T20I Series 2026 | Zimbabwe v India | 2026-07-26 | AGREE (2026-07-26) | AGREE (2026-07-26) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50597 | Australia in Bangladesh T20I Series 2026 | Bangladesh v Australia | 2026-06-17 | AGREE (2026-06-17) | AGREE (2026-06-17) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50598 | Australia in Bangladesh T20I Series 2026 | Bangladesh v Australia | 2026-06-19 | AGREE (2026-06-19) | AGREE (2026-06-19) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 50599 | Australia in Bangladesh T20I Series 2026 | Bangladesh v Australia | 2026-06-21 | AGREE (2026-06-21) | AGREE (2026-06-21) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 51383 | Bangladesh in Zimbabwe T20I Series 2026 | Zimbabwe v Bangladesh | 2026-07-15 | AGREE (2026-07-14) | AGREE (2026-07-15) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 51384 | Bangladesh in Zimbabwe T20I Series 2026 | Zimbabwe v Bangladesh | 2026-07-17 | AGREE (2026-07-17) | AGREE (2026-07-17) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 51385 | Bangladesh in Zimbabwe T20I Series 2026 | Zimbabwe v Bangladesh | 2026-07-19 | AGREE (2026-07-19) | AGREE (2026-07-19) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 54210 | India in New Zealand T20I Series 2026 | New Zealand v India | 2026-10-22 | AGREE (2026-10-22) | AGREE (2026-10-22) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 54211 | India in New Zealand T20I Series 2026 | New Zealand v India | 2026-10-24 | AGREE (2026-10-24) | AGREE (2026-10-24) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 54212 | India in New Zealand T20I Series 2026 | New Zealand v India | 2026-10-27 | AGREE (2026-10-27) | AGREE (2026-10-27) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 54213 | India in New Zealand T20I Series 2026 | New Zealand v India | 2026-10-30 | AGREE (2026-10-30) | AGREE (2026-10-30) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 54214 | India in New Zealand T20I Series 2026 | New Zealand v India | 2026-11-01 | AGREE (2026-11-01) | AGREE (2026-11-01) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 54408 | Afghanistan vs India in India T20I Series 2026 | Afghanistan v India | 2026-09-13 | AGREE (2026-09-13) | NO_CANDIDATE (None) | ok | DATE_SINGLE_SOURCE |
| 54409 | Afghanistan vs India in India T20I Series 2026 | Afghanistan v India | 2026-09-15 | AGREE (2026-09-15) | NO_CANDIDATE (None) | ok | DATE_SINGLE_SOURCE |
| 54410 | Afghanistan vs India in India T20I Series 2026 | Afghanistan v India | 2026-09-17 | AGREE (2026-09-17) | NO_CANDIDATE (None) | ok | DATE_SINGLE_SOURCE |
| 54711 | India in Japan T20I Match 2026 | Japan v India | 2026-09-22 | AGREE (2026-09-22) | AGREE (2026-09-22) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 55078 | Sri Lanka in Pakistan T20I Series 2026 | Pakistan v Sri Lanka | 2026-10-09 | AGREE (2026-10-09) | AGREE (2026-10-09) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 55079 | Sri Lanka in Pakistan T20I Series 2026 | Pakistan v Sri Lanka | 2026-10-11 | AGREE (2026-10-11) | AGREE (2026-10-11) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 55080 | Sri Lanka in Pakistan T20I Series 2026 | Pakistan v Sri Lanka | 2026-10-13 | AGREE (2026-10-13) | AGREE (2026-10-13) | ok | DATE_CONSISTENT_ACROSS_SOURCES |
| 55559 | Afghanistan v Zimbabwe T20I Series 2026 | Afghanistan v Zimbabwe | 2026-10-27 | AGREE (2026-10-27) | NO_CANDIDATE (None) | ok | DATE_SINGLE_SOURCE |
| 55560 | Afghanistan v Zimbabwe T20I Series 2026 | Afghanistan v Zimbabwe | 2026-10-29 | AGREE (2026-10-29) | NO_CANDIDATE (None) | ok | DATE_SINGLE_SOURCE |
| 55561 | Afghanistan v Zimbabwe T20I Series 2026 | Afghanistan v Zimbabwe | 2026-11-01 | AGREE (2026-11-01) | NO_CANDIDATE (None) | ok | DATE_SINGLE_SOURCE |

Full evidence columns: `phase5_t20i_date_verification.csv` / `.json`. Every TEST-period match: `phase5_test_match_date_check.csv`.

## Official verification template

Fill `config/t20i_official_date_verification.csv` (header copy: `phase5_t20i_official_verification_template.csv`) with columns `match_id, verified_date, source, verified_by, verified_date_of_verification`. Only rows with all five fields are OFFICIAL; incomplete rows are listed and ignored. A bad ISO date or unknown match id stops the run. A verified date that differs from the original is reported as `OFFICIAL_DATE_DIFFERS`; the original is not changed and the match is not treated as verified. Then re-run `python scripts/phase5_date_verification.py`.

## Restricted TEST sets (definition only, TEST not evaluated)

| Set | Rule | Matches | Deliveries | Players |
|---|---|---|---|---|
| PRIMARY_RESTRICTED | OFFICIAL_VERIFIED, or date <= core_end and class DATE_CONSISTENT_ACROSS_SOURCES | 99 | 23,039 | 324 |
| STRICT_OFFICIAL_ONLY | match in the user-supplied official verification record with an unchanged date | 0 | 0 | 0 |
| SENSITIVITY_ALL | all TEST matches, as Phase 4 evaluated them | 144 | 33,086 | 417 |

Affected by the PRIMARY_RESTRICTED rule: 45 matches, 10047 deliveries, 207 players appear in them (93 appear in no included TEST match). Under STRICT_OFFICIAL_ONLY every match is excluded until official rows are supplied: 144 matches, 33086 deliveries.

Per competition type (matches / deliveries / players):

| Set | Competition type | Matches | Deliveries | Players |
|---|---|---|---|---|
| PRIMARY_RESTRICTED | IPL | 74 | 17,527 | 201 |
| PRIMARY_RESTRICTED | T20I | 25 | 5,512 | 182 |
| SENSITIVITY_ALL | IPL | 74 | 17,527 | 201 |
| SENSITIVITY_ALL | T20I | 70 | 15,559 | 296 |

TEST-period matches in `matches` but absent from the Phase 4 state: 48513 (T20I, 2026-01-10, deliveries 0); 50189 (T20I, 2026-04-29, deliveries 0). They have no deliveries (abandoned), so they never entered the Phase 4 evaluation and do not change any set.

Manifest: `phase5_test_set_manifest.json`, self SHA-256 `032bbde633066dc32594b3383b89adedb78f2cff3c957fd597fa56a0aea283d9`.

## TEST lock handling (option D1)

TEST is **not** re-opened. The Phase 4 lock is single-use (an OPEN event is already logged) and re-opening it would need a log reset that erases the evidence of the original opening. The methodology and the data-weight gate are not locked, so a second evaluation is premature. Phase 5 reads only identity columns (`match_id`, innings, ball number, striker, bowler) of TEST matches through an allow-list that rejects `out_`, `den_`, `post_innings_` and residual columns. The restricted sets are frozen in the manifest for one future evaluation under a new `phase5_lock_log.json`, which stays empty.

| Guard | Result |
|---|---|
| Phase 4 lock log SHA-256 before | cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c |
| Phase 4 lock log SHA-256 after | cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c |
| Phase 4 lock log events | FREEZE, OPEN, CLOSE |
| Phase 5 lock log events (no OPEN) | 0 |
| official database file unchanged | yes |
| matches date column unchanged | yes |
| source CSVs unchanged | yes |
| 42 originals equal matches.csv | yes |

Phase 4's TEST evaluation covered all 144 state matches, including the 42 late matches whose dates are unverified. It is preserved byte-identical and is sensitivity-only in Phase 5 reports.

## Open decisions and unresolved issues

1. **Primary-set strictness.** The brief's strict default would exclude all 144 matches until officially verified. The plan chose PRIMARY_RESTRICTED (early consistent matches plus official rows). STRICT_OFFICIAL_ONLY is also frozen; the user should confirm which is primary.
2. **Not a pristine hold-out.** Aggregate TEST results were already shown in Phase 4, so a later evaluation is not a clean hold-out.
3. **No official record is supplied.** All 42 dates remain unverified against an authoritative source. Cricsheet agreement is secondary evidence only.
4. **Weak checks.** `competitions.csv` has no date windows (season token only); `matches 2026.csv` covers 39 IPL matches only; Cricsheet identity needs the first innings to be present.
5. **Timestamp column name.** `delivery_ist_time` ends in `UTC`; the clock times behave like UTC, so a one-day offset is tolerated and larger offsets are conflicts.
6. **Lock hash note.** The plan quoted `86f5ce9d...` as the lock log hash; that is the hash of `phase4_frozen_choices.json`. The lock log hash recorded in `phase5_prerun_hashes.json` is used.
