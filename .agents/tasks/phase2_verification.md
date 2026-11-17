# Phase 2 verification (raw outputs)

Everything below was actually run in this order. The project database was deleted before run 1 so that run ids start at 1. Outputs are copied unedited from files written at run time.

## 1. First ingestion (real data)

Command: `python scripts\ingest_competition_csv.py` (cwd d:/Data/backend, $env:PYTHONUTF8=1)

```
run_id: 1
mode: LOAD
status: SUCCESS
reason: no previous successful load
elapsed_seconds: 11.24
table row counts:
  raw_ball_by_ball: 200999
  raw_ball_by_ball_updated: 200999
  competitions: 141
  teams: 38
  competition_teams: 353
  venues: 98
  players: 1217
  player_competition_mapping: 6413
  matches: 883
  match_squads: 28381
  innings: 1724
  deliveries: 200999
  match_reconciliation: 883
  ball_by_ball_comparison: 33
  ball_by_ball_comparison_detail: 57
validation: INFO=5, OPEN=17, PASS=115
exit_code: 0
exit=0
```

## 2. Second ingestion (idempotency)

Command: `python scripts\ingest_competition_csv.py` (cwd d:/Data/backend, $env:PYTHONUTF8=1)

```
run_id: 2
mode: LOAD
status: NO_CHANGE
reason: no change: source hashes, schema and row counts match the last load
elapsed_seconds: 0.82
no change: nothing was reloaded
table row counts:
  raw_ball_by_ball: 200999
  raw_ball_by_ball_updated: 200999
  competitions: 141
  teams: 38
  competition_teams: 353
  venues: 98
  players: 1217
  player_competition_mapping: 6413
  matches: 883
  match_squads: 28381
  innings: 1724
  deliveries: 200999
  match_reconciliation: 883
  ball_by_ball_comparison: 33
  ball_by_ball_comparison_detail: 57
exit_code: 0
exit=0
```

## 3. Independent verification

Command: `python scripts\verify_database.py` (cwd d:/Data/backend, $env:PYTHONUTF8=1)

```
PASS  lineage_exists: latest load run 1
PASS  last_load_run_status_SUCCESS: status=SUCCESS
PASS  hash_ball_by_ball.csv: role=COMPARISON_RAW status=LOADED
PASS  hash_batting_stats2026.csv: role=SKIPPED_BY_DECISION status=SKIPPED_BY_DECISION
PASS  hash_bowling_stats2026.csv: role=SKIPPED_BY_DECISION status=SKIPPED_BY_DECISION
PASS  hash_competition_team_player_mapping.csv: role=PRIMARY status=LOADED
PASS  hash_competitions.csv: role=PRIMARY status=LOADED
PASS  hash_fielding_stats2026.csv: role=SKIPPED_BY_DECISION status=SKIPPED_BY_DECISION
PASS  hash_ipl squad.csv: role=PENDING_PHASE status=PENDING_PHASE
PASS  hash_matches 2026.csv: role=SKIPPED_BY_DECISION status=SKIPPED_BY_DECISION
PASS  hash_matches.csv: role=PRIMARY status=LOADED
PASS  hash_playing_eleven.csv: role=PRIMARY status=LOADED
PASS  hash_teams.csv: role=PRIMARY status=LOADED
PASS  hash_updated_ball_by_ball.csv: role=PRIMARY status=LOADED
PASS  skipped_matches 2026.csv: recorded with hash/row count, no table loaded
PASS  skipped_batting_stats2026.csv: recorded with hash/row count, no table loaded
PASS  skipped_bowling_stats2026.csv: recorded with hash/row count, no table loaded
PASS  skipped_fielding_stats2026.csv: recorded with hash/row count, no table loaded
PASS  rowcount_competitions: db=141 csv=141 (competitions.csv)
PASS  rowcount_competition_teams: db=353 csv=353 (teams.csv)
PASS  rowcount_matches: db=883 csv=883 (matches.csv)
PASS  rowcount_match_squads: db=28381 csv=28381 (playing_eleven.csv)
PASS  rowcount_player_competition_mapping: db=6413 csv=6413 (competition_team_player_mapping.csv)
PASS  rowcount_deliveries: db=200999 csv=200999 (updated_ball_by_ball.csv)
PASS  rowcount_raw_ball_by_ball_updated: db=200999 csv=200999 (updated_ball_by_ball.csv)
PASS  rowcount_raw_ball_by_ball: db=200999 csv=200999 (ball_by_ball.csv)
PASS  rowcount_match_reconciliation: db=883 csv=883 (matches.csv)
PASS  rowcount_teams: distinct team_id in csv=38
PASS  deliveries_keys_unique_in_csv: 200999 rows
PASS  deliveries_key_set_equals_csv: db=200999
PASS  deliveries_source_row_no_matches_csv_order: row i of the CSV has source_row_no i
PASS  raw_updated_provenance: source_file/source_row_no set on every row
PASS  deliveries_ingestion_run_ids_exist: missing=0
PASS  extras_type_distribution_verbatim: {'None': 189167, 'wide': 7714, 'legbyes': 2748, 'byes': 529, 'Overstep': 576, 'other': 264, 'Penalty': 1}
PASS  innings_aggregates_match_csv: innings=1724 mismatches=0
PASS  no_is_super_over_column: no super-over column exists
PASS  innings_3_4_unverified: violations=0
PASS  playing_eleven_duplicates_preserved: csv rows=75 groups=35; db rows=75 groups=35
PASS  matches_without_deliveries_set: 16 matches
PASS  delivery_match_ids_exist_in_matches: orphans=0
PASS  no_delivery_matches_explained: unexplained=0
PASS  players_equal_union_of_ids: csv=1217 db=1217
PASS  duplicate_names_not_merged: 7 names
PASS  original_vs_updated_differences: {'extras1_runs': 199980, 'non_striker_name': 33, 'striker_name': 24}
PASS  competition_type_ipl_rule: violations=0

summary: 45 PASS, 0 FAIL
exit=0
```

## 4. Full test suite (19 Phase 1 + 7 schema + 32 ingestion, includes the realdata test)

Command: `python -m pytest -q` (cwd d:/Data/backend, $env:PYTHONUTF8=1)

```
..........................................................               [100%]
58 passed in 70.18s (0:01:10)
```

## 5. Ruff lint

Command: `python -m ruff check .` (cwd d:/Data/backend, $env:PYTHONUTF8=1)

```
All checks passed!
```

## 6. Ruff format check

Command: `python -m ruff format --check .` (cwd d:/Data/backend, $env:PYTHONUTF8=1)

```
34 files already formatted
```

## 7. Verify again after the test suite

`python scripts\verify_database.py` was re-run after pytest: `summary: 45 PASS, 0 FAIL` (the tests use temporary databases and did not touch `data/database/superr.duckdb`).


## Notes

- During development a scratch database in %TEMP% was loaded three times (first load, no-change run, `--force` reload). `verify_database.py --db <scratch>` passed 45/45 after the forced reload. The project database was loaded once and then re-run once (no change). `--force` was not run against it; the forced reload is covered by the test `test_force_reload_gives_identical_content`.
- Original data files in d:/Data are read-only inputs. Their sha256 values are re-verified by the `hash_*` checks of `verify_database.py` and by the `source_unchanged_*` validation checks.
- `d:/Data` is not a git repository, so nothing was committed.
