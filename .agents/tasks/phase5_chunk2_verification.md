# Phase 5 Chunk 2 verification (T20I date verification, restricted TEST set)

All commands run from `d:/Data/backend` with `$env:PYTHONUTF8=1`.

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_phase5_date_verification.py` | 25 passed |
| `python scripts/phase5_date_verification.py` (run 3 times) | identical SHA-256 for `phase5_t20i_date_verification.json` and `phase5_test_set_manifest.json` (deterministic) |
| `python scripts/phase5_gates.py` | `date_verification` gate now read from the summary JSON, failing (0 of 42 official) |
| `python -m pytest -q` (full) | 651 passed (509 baseline + earlier Phase 5 chunks + 25 new), 3 pre-existing warnings |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 197 files already formatted |

## Results on real data
- 42 late T20I matches: 36 `DATE_CONSISTENT_ACROSS_SOURCES`, 6 `DATE_SINGLE_SOURCE` (Afghanistan v India 54408-54410 and Afghanistan v Zimbabwe 55559-55561; Cricsheet has no Afghanistan 2026 fixtures in the staged index), 0 conflict, 0 unverified. 0 official-verified.
- All 146 TEST-period IPL/T20I matches: 135 consistent, 9 single source, 2 unverified (match ids 48513, 50189, abandoned, no deliveries, not in the Phase 4 state), 0 conflict.
- Timestamp first-ball date equals the original date for 41 of 42, one day earlier for 1 (within tolerance). Cricsheet agrees 33 exact, 3 one day earlier.
- Sets (matches / deliveries / players): PRIMARY_RESTRICTED 55 / 12,599 / 283; STRICT_OFFICIAL_ONLY 0 / 0 / 0; SENSITIVITY_ALL 144 / 33,086 / 417. PRIMARY excludes 89 matches / 20,487 deliveries (339 players appear in them, 134 only there).

## Guards (from the script, asserted)
- `superr.duckdb` file hash, `matches` date column hash and the four source CSV hashes identical before and after.
- `phase4_lock_log.json` SHA-256 `cae1e06c3babffbb94594ea2ce08fe5416c98ea7da6628d21094d22c8d2eb75c` before and after (equals the value in `phase5_prerun_hashes.json`); events FREEZE, OPEN, CLOSE unchanged. Note: the plan quoted `86f5ce9d...` as the lock log hash; that is the hash of `phase4_frozen_choices.json`.
- `phase5_lock_log.json` created empty (`[]`), no OPEN event. TEST was not opened; only identity columns were read for TEST matches.
- 42 original dates equal `matches.csv` read independently with the `csv` module.

## Independent spot check
Match 45390 (England v India): `matches.csv` date 2026-07-01; first `delivery_ist_time` in `updated_ball_by_ball.csv` is `2026-07-01 16:33:43 UTC` (streamed with the `csv` module); Cricsheet file `t20s_male_json/1496574.json` has date 2026-07-01, first innings India 189 (equals the first-innings total used for identity). Two agreeing sources, no conflict, so `DATE_CONSISTENT_ACROSS_SOURCES` matches the report. The realdata test also recomputes the 42 ids and the timestamp status of three matches from the raw CSVs.

## Decisions and caveats
- Chose option D1 (do not re-open TEST; freeze set definitions in a manifest).
- Primary-set strictness is an open decision (plan D2): PRIMARY_RESTRICTED keeps early consistent matches; STRICT_OFFICIAL_ONLY is also frozen.
- Cricsheet access is confined to `app/phase5/date_verification.py` (AST test over `app/phase4`, `app/phase5`, `app/analytics`, `pressure_service`).
- Added small foundation modules the plan listed for Chunk 1 but which were absent: `app/phase5/lockguard.py`, `app/phase5/data.py`.
- No file under Phase 4, `superr.duckdb` or the source CSVs was modified. `exploratory.duckdb` gained `p5_t20i_date_verification`, `p5_test_match_date_check`, `p5_test_set_membership`, `p5_test_set_manifest`.

## Files
Created: `app/phase5/date_verification.py`, `test_manifest.py`, `lockguard.py`, `data.py`; `scripts/phase5_date_verification.py`; `config/phase5_date_verification_v1.json`, `config/t20i_official_date_verification_template.csv`; `tests/test_phase5_date_verification.py`; reports `phase5_t20i_date_verification.{md,csv,json}`, `phase5_test_match_date_check.csv`, `phase5_test_set_manifest.json`, `phase5_t20i_official_verification_template.csv`, `phase5_lock_log.json`.
