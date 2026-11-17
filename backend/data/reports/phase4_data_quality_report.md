# Phase 4 data-quality report

Status: EXPERIMENTAL_NOT_VALIDATED. Not an official ranking and not a validated methodology. No final ML model was trained. Automated tests passing does not validate the methodology.

Restrictions come from `config/data_quality_restrictions_v1.json` and are applied as masks on metrics and features. No official record was changed or deleted and no match was excluded globally. Figures below are read from the stored Phase 3 register application (`phase3_data_quality_application.json`), the Phase 4 split manifest, the exploratory store, and a scan of the Phase 4 source files.

## 1. Register
| item | value |
|---|---|
| register version | data_quality_restrictions_v1 |
| register status | PROVISIONAL |
| rules | 26 |
| global exclusion | no |
| rules implemented | yes |
| records deleted | 0 |
| innings 3/4 rows in a pressure population | no |


## 2. Row categories used by Phase 4 scoring (all delivery rows preserved)
Total state rows: 200,999. Categories are mutually exclusive and applied in the listed order. Counts use flags and dates only (no outcome columns).
| period | category | rows | share of period |
|---|---|---|---|
| TEST | 1_innings_3_4_restricted | 4 | 0.000121 |
| TEST | 3_dls_not_reconstructable | 1,086 | 0.03 |
| TEST | 5_in_primary_scoring_base | 31,996 | 0.97 |
| TRAIN | 1_innings_3_4_restricted | 5 | 4.16e-05 |
| TRAIN | 2_out_of_scope_format | 3,519 | 0.03 |
| TRAIN | 3_dls_not_reconstructable | 1,512 | 0.01 |
| TRAIN | 5_in_primary_scoring_base | 115,212 | 0.96 |
| VALIDATION | 1_innings_3_4_restricted | 29 | 0.000608 |
| VALIDATION | 2_out_of_scope_format | 3,454 | 0.07 |
| VALIDATION | 3_dls_not_reconstructable | 806 | 0.02 |
| VALIDATION | 5_in_primary_scoring_base | 43,376 | 0.91 |


## 3. Innings 3 and 4 (RULE_INNINGS_3_4)
| item | value |
|---|---|
| rows | 38 |
| matches | 6 |
| rows by innings | {"3": 25, "4": 13} |
| reason codes (rows) | {"UNVERIFIED_INNINGS_ROLE": 22, "CONFIRMED_SUPER_OVER_BY_CRICSHEET": 16} |
| matches by reason | {"CONFIRMED_SUPER_OVER_BY_CRICSHEET": [34429, 45512, 50359], "UNVERIFIED_INNINGS_ROLE": [40725, 48027, 48029]} |
| rows still in the official deliveries table | 38 |
| any row in a pressure population | no |


Two reason codes apply: `CONFIRMED_SUPER_OVER_BY_CRICSHEET` (confirmed by the Phase 2.5 validation report) and `UNVERIFIED_INNINGS_ROLE` (role not verified). Both are excluded from every metric the rule lists.

## 4. Extras (`other`, `Penalty`) preserved and flagged
| extras category | rows |
|---|---|
| None | 189,165 |
| wide | 7,714 |
| legbyes | 2,748 |
| Overstep | 576 |
| byes | 529 |
| other | 264 |
| None_with_runs | 2 |
| Penalty | 1 |

| item | value |
|---|---|
| `other` rows mapped to None | 0 |
| `Penalty` rows mapped to None | 0 |
| rows with an unverified label | 265 |
| Penalty rows removed from ball-count masks | {"batter_balls_faced": 1, "bowler_legal_balls": 1} |
| rows with secondary extras runs | 36 |
| secondary-runs guard blocks bowler economy | yes |


## 5. Wicket-flag anomalies
| item | value |
|---|---|
| dismissed player without wicket flag (rows) | 12 |
| wicket flag without dismissed player (rows) | 1 |
| state rows where wicket-count variants differ | 739 |
| state rows dropped | 0 |
| dismissal-metric rows excluded (primary) | {"wicket_event_label": 1, "batter_dismissal_rate": 39, "bowler_wicket_rate": 38} |


## 6. DLS and shortened innings (never imputed)
| item | value |
|---|---|
| DLS matches | 34 |
| DLS rows | 4,433 |
| rows without reconstructable revised state | 3,404 |
| shortened innings (limit below 120) | 50 |
| shortened matches | 34 |
| shortened deliveries | 3,404 |
| all shortened innings excluded by the DLS mask | 50 |
| chase rows excluded that would otherwise be eligible | 1,775 |
| DLS resources imputed | no |
| delivery rows deleted | 0 |
| deliveries whose phase label depends on a revised limit | 1,154 |
| revision announcement time in the data | no |


Shortened innings by period: {"IPL|TEST": 4, "IPL|TRAIN": 1, "IPL|VALIDATION": 3, "T20I|TEST": 10, "T20I|TRAIN": 23, "T20I|VALIDATION": 9}. Phase boundaries for every innings limit present are in `phase4_phase_boundaries.md`. Phase labels use only the legal balls bowled before the delivery and the innings limit.

## 7. Identity by player_id only
| item | value |
|---|---|
| players sharing a name | 14 |
| distinct shared names | 7 |
| rows if joined on id | 958 |
| rows if naively joined on name | 968 |
| ids a name join would merge | 10 |
| name-join guard raises | yes |
| pipeline join key | player_id only |


## 8. Duplicate squad records never multiply statistics
| item | value |
|---|---|
| squad rows | 28,381 |
| rows flagged duplicate | 75 |
| pressure-sample rows without a squad join | 89,589 |
| rows with the safe join | 89,589 |
| rows with a naive join | 89,964 |
| per-player counts identical with and without the safe join | yes |
| Phase 4 scoring uses match_squads | no |


## 9. Cricsheet is not a data source
Scan of 30 Phase 4 data and scoring source files (the report writers are excluded) for string literals (excluding docstrings) containing `cricsheet`: 0 hits. Cricsheet appears only as a reason-code label inherited from the Phase 2.5 register.

## 10. Date observation
| item | value |
|---|---|
| core_end | 2026-05-31 |
| t20i_matches_after_core_end | 42 |
| first_date_after_core_end | 2026-06-12 |
| last_date | 2026-11-01 |
| t20i_test_period_matches | 70 |


T20I matches dated after the core end carry deliveries and sit in the TEST period. Dates are used as recorded and were not corrected. The TEST evaluation reports a `TEST_CORE` sensitivity that excludes them. Please confirm whether these dates are real.

## 11. Limits
- The register application (sections 3 to 8) was computed in Phase 3 over all periods from descriptive flags, not from TEST outcomes.
- The register is PROVISIONAL; rules marked DOCUMENT_ONLY change no metric.
- Split boundaries: {"TEST": {"end": null, "start": "2026-01-01"}, "TRAIN": {"end": "2024-12-31", "start": null}, "VALIDATION": {"end": "2025-12-31", "start": "2025-01-01"}}.
