# Phase 5 classification migration

Status: EXPERIMENTAL_NOT_VALIDATED. Classification version `p5_classification_v2`. Nothing here is a validated cap list.

## What changed
`international_status` is now one of four **separate** values: `VERIFIED_CAPPED` (authoritative source or validated override only), `DERIVED_CAPPED` (the player appeared for a national team in an official T20I in the data on or before the as-of date), `VERIFIED_UNCAPPED` (authoritative source or validated override only) and `UNKNOWN`. Each row keeps its own evidence label (`international_status_verification`). `UNKNOWN` is shown only as the group `UNKNOWN_STATUS` with the banner `NOT_PROVEN_CAPPED_IS_NOT_UNCAPPED`: a player not proven capped is never labelled uncapped.

## Migration mapping (explicit; any other combination is fatal)
| Phase 4 status | Phase 4 verification | Phase 5 status |
|---|---|---|
| Capped | DERIVED_FROM_OFFICIAL_T20I_APPEARANCES | DERIVED_CAPPED |
| Capped | VERIFIED_FROM_SOURCE | VERIFIED_CAPPED |
| Uncapped | VERIFIED_FROM_SOURCE | VERIFIED_UNCAPPED |
| Unknown | UNVERIFIED | UNKNOWN |


## Counts from the real data
| Phase 5 status | players | Phase 4 label | Phase 4 players |
|---|---|---|---|
| VERIFIED_CAPPED | 0 | Capped (VERIFIED_FROM_SOURCE) | 0 |
| DERIVED_CAPPED | 655 | Capped (DERIVED_FROM_OFFICIAL_T20I_APPEARANCES) | 655 |
| VERIFIED_UNCAPPED | 0 | Uncapped | 0 |
| UNKNOWN (UNKNOWN_STATUS) | 562 | Unknown | 562 |


Players total: 1217. Phase 4 coverage JSON agrees (capped 655, uncapped 0, unknown 562); the migration asserts this and stops on any mismatch.

### Independent recount
- DERIVED_CAPPED recounted from `competitions.csv`, `matches.csv` and `playing_eleven.csv` with the csv module: **655** (stored 655).

### Nationality x status (all players)
| nationality | international_status | players |
|---|---|---|
| Indian | VERIFIED_CAPPED | 0 |
| Indian | DERIVED_CAPPED | 52 |
| Indian | VERIFIED_UNCAPPED | 0 |
| Indian | UNKNOWN | 112 |
| Overseas | VERIFIED_CAPPED | 0 |
| Overseas | DERIVED_CAPPED | 603 |
| Overseas | VERIFIED_UNCAPPED | 0 |
| Overseas | UNKNOWN | 3 |
| Unknown | VERIFIED_CAPPED | 0 |
| Unknown | DERIVED_CAPPED | 0 |
| Unknown | VERIFIED_UNCAPPED | 0 |
| Unknown | UNKNOWN | 447 |


### Nationality x status (scored players, 403)
| nationality | international_status | players |
|---|---|---|
| Indian | VERIFIED_CAPPED | 0 |
| Indian | DERIVED_CAPPED | 51 |
| Indian | VERIFIED_UNCAPPED | 0 |
| Indian | UNKNOWN | 35 |
| Overseas | VERIFIED_CAPPED | 0 |
| Overseas | DERIVED_CAPPED | 288 |
| Overseas | VERIFIED_UNCAPPED | 0 |
| Overseas | UNKNOWN | 1 |
| Unknown | VERIFIED_CAPPED | 0 |
| Unknown | DERIVED_CAPPED | 0 |
| Unknown | VERIFIED_UNCAPPED | 0 |
| Unknown | UNKNOWN | 28 |


### Evidence labels and reasons
- status verification: {'DERIVED_FROM_OFFICIAL_T20I_APPEARANCES': 655, 'UNVERIFIED': 562}
- nationality verification: {'DERIVED': 770, 'UNVERIFIED': 447}
- UNKNOWN reasons: {'NOT_PROVEN_CAPPED_IN_DATA': 498, 'FIRST_T20I_AFTER_AS_OF_DATE': 64}

## Dates
DERIVED_CAPPED uses T20I matches dated on or before the as-of date `2025-12-31`. The 42 T20I matches with disputed dates are all later than that date, so no DERIVED_CAPPED count depends on them.

## No inference
The migration reads only the stored classification table (built from T20I playing-eleven appearances). It imports no names, squad, domestic or IPL tables and never infers capped status from them. A player with IPL matches and no T20I stays `UNKNOWN`.

## Overrides
- Override file rows loaded and validated: 0. The file stays header-only and unchanged.
- A row needs `player_id`, `field`, `value`, `source`, `verified_by`, `verified_date` (ISO, not in the future). Legacy `Capped`/`Uncapped` values are rejected with the mapping named. A `VERIFIED_UNCAPPED` row for a `DERIVED_CAPPED` player is rejected (`CONTRADICTS_DERIVED_EVIDENCE`).

## Strict uncapped capability
- `strict_uncapped_enabled`: **False** (computed, never hand-set).
- reasons: ['NO_AUTHORITATIVE_SOURCE', 'NO_VERIFIED_ROWS', 'COVERAGE_BELOW_MINIMUM']
- authoritative id-keyed sources declared: 0; verified rows: 0; verified coverage of the scored pool: 0.0 (minimum 0.95, provisional; scored pool 403).
- While disabled, every uncapped ranking, uncapped preset, uncapped filter and uncapped composition constraint answers `STRICT_UNCAPPED_DISABLED` with the reason, the source needed and no rows. No approximation is produced.
- Source needed: An authoritative source of international status keyed by player_id (for example an official board or ICC record), declared in config/classification_source_manifest_v1.json with authoritative=true and id_keyed=true, plus validated override rows (source, verified_by, verified_date) in config/classification_overrides_v1.csv covering at least the minimum share of the scored pool.
