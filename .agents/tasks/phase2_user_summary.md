# Phase 2: DuckDB schema and official CSV ingestion (summary)

Status: implemented, run on the real data, verified. No pressure metric, ranking, API or frontend was built. Cricsheet was not loaded. The original data files in `d:/Data` were not modified (sha256 re-verified after the load and after the tests). `d:/Data` is not a git repository, so nothing was committed. Raw command outputs are in `d:/Data/.agents/tasks/phase2_verification.md`.

Database: `d:/Data/backend/data/database/superr.duckdb` (50.3 MB). Schema: `d:/Data/backend/data/audit/phase2_schema.sql`. Plan: `d:/Data/backend/data/audit/phase2_ingestion_plan.md`.

## Schema overview

- **Persistent control tables** (never dropped): `ingestion_runs`, `ingestion_errors`, `dataset_lineage`, `data_quality_results` (+ view `v_latest_data_quality`), `model_versions`, `metric_definitions`, `schema_meta`.
- **Replaceable data layer** (15 tables): `competitions`, `teams`, `competition_teams`, `venues`, `players`, `player_competition_mapping`, `matches`, `match_squads`, `innings`, `deliveries`, `match_reconciliation`, `raw_ball_by_ball`, `raw_ball_by_ball_updated`, `ball_by_ball_comparison`, `ball_by_ball_comparison_detail`.
- **Primary keys:** competitions(comp_id); teams(team_id); competition_teams(comp_id, team_id); venues(venue_id); players(player_id); player_competition_mapping(comp_id, team_id, player_id); matches(match_id); match_squads(match_id, team_id, player_id, squad_row_no); innings(match_id, innings_number); deliveries(match_id, innings_number, innings_ball_num); match_reconciliation(match_id); raw tables(source_row_no).
- **Foreign keys enforced by DuckDB (26):** competition_teams to competitions and teams; player_competition_mapping to competition_teams and players; matches to competitions, venues, teams (home, away, toss, win) and players (two captains); match_squads to matches, teams, players; innings to matches and teams (batting, bowling); deliveries to innings, teams (batting, bowling) and players (striker, non-striker, bowler, dismissed); match_reconciliation to matches.
- **Relations recorded only, not FKs** (known unresolved ids): playing_eleven rows without a mapping row (`mapping_row_exists`), deliveries whose striker/bowler is not in the match squad, `matches.man_of_the_match` (0 is a sentinel in 119 matches), `matches.first_innings_batting_team_id`, and every `ingestion_run_id` column. Each has an orphan or integrity check stored in `data_quality_results`.
- Provenance: every imported record carries `source_file`, `source_row_no` (1-based data row, header excluded) and `ingestion_run_id`. The three aggregate tables carry the equivalent (`innings` has first/last source row, comparison tables carry the file pair).
- Deliberately absent: any `is_super_over` column.

## Ingestion, idempotency and transaction design

- Source files are profiled first (header check, sha256, row count). A `RUNNING` run row is committed before the load.
- Idempotency: a run is `NO_CHANGE` when every file sha256, the DDL hash and the row count of each loaded table equal the last successful load recorded in `dataset_lineage`. `--force` reloads regardless.
- The load is one DuckDB transaction that drops and recreates the data layer and inserts everything. Any exception rolls back to the previous complete state. After the rollback the run is set to `FAILED` and the error rows and `ingestion_errors.csv` are written. A test injects a fault during the `deliveries` step and confirms the tables are unchanged.
- Strategy test on DuckDB 2.0.0: `DELETE` + `INSERT` of an FK-referenced parent row fails even inside one transaction; `DROP` + `CREATE` + `INSERT` then `ROLLBACK` restores the old state. So the replace uses drop-and-recreate (kept as regression tests in `tests/test_duckdb_schema.py`).
- Nothing is dropped silently: row counts of every table are compared with the file inside the transaction, and key columns that cannot be cast abort the run. Non-key cast failures would be stored as NULL and listed in `ingestion_errors` (there were none).
- Decisions applied: `updated_ball_by_ball.csv` feeds `deliveries`/`innings`; `ball_by_ball.csv` is kept raw with a comparison table; `matches 2026.csv` and the three `*_stats2026.csv` files are `SKIPPED_BY_DECISION` in lineage (hash and row count only); `ipl squad.csv` is `PENDING_PHASE`; no Cricsheet data; weights 0.70/0.30 are stored in `model_versions` as a `PROVISIONAL` config and are not used in any calculation.

## Commands

```powershell
cd d:/Data/backend
$env:PYTHONUTF8 = 1
python scripts\ingest_competition_csv.py             # run 1: load; run 2: "no change"
python scripts\ingest_competition_csv.py --force     # reload
python scripts\ingest_competition_csv.py --validate-only
python scripts\verify_database.py                    # independent check, exit 1 on FAIL
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

## Actual results

### Runs

| run_id | command | status | seconds |
|---|---|---|---|
| 1 | `ingest_competition_csv.py` | SUCCESS (reason: no previous successful load) | 11.24 |
| 2 | `ingest_competition_csv.py` | NO_CHANGE (hashes, schema and row counts match; nothing reloaded, same counts) | 0.82 |

`verify_database.py`: 45 PASS, 0 FAIL, exit 0 (also after the test suite). Ingestion exit codes 0 and 0.

### Row counts: table against source

| table | source file | file rows | table rows |
|---|---|---|---|
| competitions | competitions.csv | 141 | 141 |
| competition_teams | teams.csv | 353 | 353 |
| teams | distinct team_id in teams.csv | 38 | 38 |
| venues | distinct venue_id in matches.csv | 98 | 98 |
| players | union of all player ids | 1,217 | 1,217 |
| player_competition_mapping | competition_team_player_mapping.csv | 6,413 | 6,413 |
| matches | matches.csv | 883 | 883 |
| match_reconciliation | matches.csv | 883 | 883 |
| match_squads | playing_eleven.csv | 28,381 | 28,381 |
| raw_ball_by_ball | ball_by_ball.csv | 200,999 | 200,999 |
| raw_ball_by_ball_updated | updated_ball_by_ball.csv | 200,999 | 200,999 |
| deliveries | updated_ball_by_ball.csv | 200,999 | 200,999 |
| innings | distinct (match, innings) | 1,724 | 1,724 |
| ball_by_ball_comparison | 33 source columns | 33 | 33 |
| ball_by_ball_comparison_detail | differing cells except extras1_runs | 57 | 57 |

All spec counts (141, 353, 883, 28,381, 6,413, 200,999) match.

### PK and FK validation

- 13 primary-key checks (every table with a key): 0 duplicate keys each, all PASS.
- 26 enforced FK checks: 0 orphans each, all PASS. Run-id and `source_file` provenance checks on every table: 0 missing, PASS.
- Validation totals for run 1 (`data_quality_results`): 115 PASS, 17 OPEN, 5 INFO, 0 FAIL.

### Reconciliation of the 16 matches without deliveries

883 matches = 867 with deliveries + 16 without. All 16 have `result` = `Match Abandoned`, `result_status` ABANDONED, no `win_team_id`, and `no_deliveries_explained` = true (check `reconcile_no_delivery_matches_explained` PASS): 31281, 31284, 31288, 32610, 32612, 32622, 36210, 36564, 38797, 40761, 41502, 41503, 42030, 46008, 48513, 50189. Three of them (36210, 41503, 48513) also have no playing_eleven rows. Every delivery `match_id` exists in `matches` (0 orphans). `result_status` distribution: COMPLETED 833, NO_RESULT 21, ABANDONED 19, TIED_DECIDED_BY_TIEBREAK 9, TIED 1, UNKNOWN 0. Competition types: IPL 5 competitions / 371 matches, T20I 134 / 482, OTHER_T20 2 / 30.

### Original against updated ball-by-ball

Same 200,999 rows and identical key sets (0 rows only in either file). Differing columns: `extras1_runs` 199,980 rows (category code in the original, run count in the updated file; crosstab by `extras_type` is stored in `ball_by_ball_comparison.details`), `striker_name` 24 rows, `non_striker_name` 33 rows (the 57 name differences are in `ball_by_ball_comparison_detail`). All other columns are identical. This reproduces the Phase 1 figures.

### Data loaded from `updated_ball_by_ball.csv`

`extras_type` verbatim: None 189,167; wide 7,714; legbyes 2,748; Overstep 576; byes 529; other 264; Penalty 1. `is_legal_ball`, `legal_ball_count` and run totals per innings were recomputed from the raw table and by `verify_database.py` with the stdlib `csv` module: 0 mismatches over 1,724 innings.

### OPEN data-quality issues (preserved, counts recomputed from the loaded database)

| issue | count |
|---|---|
| playing_eleven repeated keys (all kept, flagged) | 75 rows in 35 groups in 3 matches |
| matches without playing_eleven rows | 3 |
| playing_eleven rows without a mapping row | 5 |
| delivery strikers not in the match squad | 83 rows, 6 (match, striker) pairs |
| delivery bowlers not in the match squad | 30 rows, 3 (match, bowler) pairs |
| `is_wicket` false but a dismissed player given | 12 rows |
| wicket without a dismissed player | 1 row (Retire Out) |
| `extras_type` `other` (label unverified) | 264 rows |
| `extras_type` `Penalty` (label unverified) | 1 row |
| rows with `extras_2_runs` > 0 (split unverified) | 36 |
| innings 3/4 (role unverified, not called Super Overs) | 12 innings in 6 matches, 38 delivery rows |
| `man_of_the_match` = 0 sentinel | 119 matches |
| `delivery_ist_time` has a `UTC` suffix although the column says IST | 200,999 rows (no timezone conversion applied) |
| delivery rows with a 00:00:00 time part | 42 |
| player names shared by two player ids (not merged) | 7 names |
| Cricsheet totals disagree (carried from Phase 1, not recomputed) | 10 innings: matches 14130, 14164, 32618, 37349, 37352, 50504 |
| matches not linkable to Cricsheet (carried from Phase 1) | 108 |

`ingestion_errors` for run 1 holds 193 WARNING rows: 75 DUPLICATE_KEY_PRESERVED, 5 ORPHAN_RECORDED_NOT_DROPPED (match_squads), 113 ORPHAN_RECORDED_NOT_DROPPED (deliveries). There are no ERROR rows. `data/audit/ingestion_errors.csv` has the same 193 rows.

## Errors encountered during development

- First real load failed and rolled back: `players.in_deliveries` was NULL because `id IN (subquery with NULLs)` returns NULL. Fixed by filtering NULL ids and coalescing; the rollback left the previous state intact.
- DuckDB's CSV sniffer failed on a synthetic test file with mixed `\r\n` and `\n` line endings. The loader now passes explicit delimiter/quote/escape options and the test file uses consistent line endings. The real files were unaffected.
- One wrong expected row number in my own test (fixed).
- No errors in the final runs.

## Deviations from the brief and the plan

1. The replace strategy is drop-and-recreate inside one transaction, not row-level delete/insert (see above).
2. No FK from any table to `ingestion_runs`; run-id integrity is a validation check (DuckDB cannot reliably update a referenced primary-key row).
3. `man_of_the_match`, squad-to-mapping, delivery-to-squad and `first_innings_batting_team_id` are not FKs (see schema overview).
4. The typed tables name the innings column `innings_number` (raw tables keep `innings`).
5. `delivery_ist_time` is stored raw plus a naive parsed timestamp; the true time zone is unverified.
6. Extra columns beyond the brief: `legal_ball_status`, `dismissal_field_anomaly`, `delivery_time_is_midnight`, `extras_split_status`, `mapping_row_exists`, `teams_consistent`, `first_innings_batting_team_id`, player source flags.
7. The empty later-phase analytics tables, `source_*_mapping`, `raw_cricsheet_matches` and the raw 2026 tables from the Phase 1 draft were not created; they belong to later phases. `app/repositories/` was not added; `app/core/database.py` is the single thin abstraction.
8. The two Cricsheet-related OPEN items are carried from the Phase 1 report as constants (Cricsheet is not loaded), not recomputed.
9. A `NO_CHANGE` run does not re-run validation or rewrite the reports; use `--validate-only` for that.
10. The sensitivity tests in decision 4 are not defined in the brief and no calculation is allowed yet, so only the weight configuration is stored. The grid must be specified before Phase 3.
11. `Settings` default paths were changed from `D:/Data` to lower-case `d:/Data`.
12. Delivery match-level squad check: strikers/bowlers are compared with the match squad of either team, as in Phase 1.

## Test and lint results

- `python -m pytest -q`: `58 passed in 70.18s` (19 Phase 1 tests, 7 schema tests, 32 ingestion tests including the `realdata` test that ingests the real CSVs into a temporary database and checks the counts above and the NO_CHANGE second run).
- `python -m ruff check .`: `All checks passed!`
- `python -m ruff format --check .`: `34 files already formatted`

## Files

Created in `d:/Data/backend`: `app/core/database.py`, `app/data_pipeline/csv_loader.py`, `app/services/{__init__,ingestion_service,validation_service}.py`, `scripts/ingest_competition_csv.py`, `scripts/verify_database.py`, `tests/test_csv_ingestion.py`, `tests/test_duckdb_schema.py`, `data/audit/{phase2_schema.sql,phase2_ingestion_plan.md,ingestion_errors.csv,phase2_validation_report.json,phase2_validation_report.md,ball_by_ball_comparison.json,ball_by_ball_comparison.md,phase2_match_reconciliation.csv}`, `data/database/superr.duckdb`. Modified: `app/core/config.py` (weights, validator, report paths, lower-case default paths), `.env.example`, `pyproject.toml` (pytest marker `realdata`), `README.md` (Phase 2 section). In `d:/Data/.agents/tasks`: `phase2_verification.md`, `phase2_user_summary.md`.

## What remains for Phase 3

- Define the IPL/T20I sensitivity grid and eligibility rules (not in the brief or the problem statement).
- Resolve or keep carrying the OPEN issues: meaning of `other` and `Penalty`, innings 3/4 role (Cricsheet super-over flags need checking), repeated playing_eleven keys, strikers/bowlers outside the squad, the 10 Cricsheet total disagreements.
- Decide how Cricsheet may be used for validation only, then add source mapping tables if needed.
- Then pressure definition, baselines, ratings and rankings, with the stored weight config and `model_versions`.
