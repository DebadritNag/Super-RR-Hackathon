# Phase 2 Implementation Plan: DuckDB schema + idempotent official CSV ingestion

Scope: official competition CSVs only. No Cricsheet loading, no pressure, no rankings, no API/frontend.
Environment: Python 3.11 as `python`, PowerShell, `$env:PYTHONUTF8=1`, DuckDB 2.0.0. All paths lower-case drive `d:/Data/...`. Originals in `d:/Data` are read-only.
Gate contract of the existing loop is unchanged: `d:/Data/.agents/tasks/phase2_review.json` (`verdict` APPROVED|CHANGES_REQUESTED) is written by the last reviewer step; maxIterations 3.

## 0. Findings from exploration (what the plan is grounded in)

Read: `.agents/tasks/user_summary.md`, `data/audit/proposed_schema.sql`, `extras_mapping.md`, `app/core/config.py`, `app/data_pipeline/{data_quality,dataset_discovery}.py`, `app/utils/paths.py`, `scripts/audit_datasets.py`, `tests/test_dataset_audit.py`, `pyproject.toml`, `README.md`. Probed the real CSVs and DuckDB 2.0.0.

- Existing building blocks to reuse: `Settings` (pydantic-settings, `SUPERR_` prefix, `duckdb_path` already = `data/database/superr.duckdb`), `data_quality.classify_result()` (COMPLETED / NO_RESULT / ABANDONED / TIED / TIED_DECIDED_BY_TIEBREAK / UNKNOWN), `data_quality.register_csv_views()` pattern (`read_csv(..., all_varchar=true)`), `dataset_discovery.EXPECTED_CSVS`, `paths.posix/sql_quote`, ruff config (line-length 100, E501 ignored), pytest `pythonpath=["."]`. Baseline: `python -m pytest -q` = 19 passed.
- All 6 core CSVs are UTF-8 without BOM, comma separated, header row, empty string = NULL.
- `matches.match_date` is ISO `YYYY-MM-DD` (0 unparseable). `matches.csv` has NO venue name column, only `venue_id` (98 distinct) and `venue_country` (17; one country per venue_id). So `venues` = (venue_id, venue_country) only; no name is invented.
- `matches.toss_opted` values: `Fielding`, `Batting`, NULL. `knock_out` is `0`/`1`. `man_of_the_match` is mostly the string `0` (119 rows) otherwise a player id: keep it as INTEGER but do NOT FK it (0 is a sentinel); record sentinel count in DQ.
- `playing_eleven`: `is_played`/`is_captain`/`is_wk` are `true`/`false` strings (NULL for 8,667 not-played rows); `is_impact`/`is_impact_off` are `0`/`1`.
- Ball files: `is_four`/`is_six`/`is_wicket` are `true`/`false`. `delivery_ist_time` has the fixed form `YYYY-MM-DD HH:MM:SS UTC` (length 23 on every row) even though the column name says IST. Parse with `strptime(replace(x,' UTC',''), '%Y-%m-%d %H:%M:%S')` into a naive TIMESTAMP and keep the raw string. The "date-only" rows are those whose time part is `00:00:00`; recompute the count, do not assume 42.
- `extras_type` actual values: `None` 189,167, wide 7,714, legbyes 2,748, Overstep 576, byes 529, other 264, Penalty 1 (updated file; same in original). `batting_order` in the ball files is a per-ball value 1..13 (a batting position, not a ball counter).
- DuckDB `read_csv` here does NOT support `file_row_number`. `row_number() OVER ()` over `read_csv(...)` preserved file order (checked on 200,999 rows against the Python `csv` module). Use it for `source_row_no` (1-based data-row index, header excluded; this equals the physical line number minus 1 only when no quoted field spans lines). `verify_database.py` re-checks the ordering with the stdlib `csv` module.
- `(match_id, innings, innings_ball_num)` is unique in `updated_ball_by_ball.csv` (200,999 distinct groups). The PK is therefore safe, but the loader still verifies it before the replace and fails the run (no silent drop) if it ever stops holding.

### DuckDB FK behaviour tested on the installed 2.0.0 (drives the replace strategy)

| experiment | result |
|---|---|
| `DELETE` a parent row that no child references | OK |
| `DELETE` a parent row still referenced | `ConstraintException` (immediate) |
| In one transaction: `DELETE` child, `DELETE` parent, re-`INSERT` parent, re-`INSERT` child | FAILS with FK violation (DuckDB does not see the delete as applied within the same transaction for FK purposes) |
| `DROP TABLE parent` while child exists | `CatalogException` |
| In one transaction: `DROP` child, `DROP` parent, `CREATE` both, `INSERT` new rows, then `ROLLBACK` | old tables and rows fully restored |
| Same sequence then `COMMIT` | new tables and rows visible |
| `INSERT` into a table with `DEFAULT nextval(seq)` then `ROLLBACK` | row gone |
| Composite FK `(match_id, innings_number)` | enforced on insert |

**Chosen strategy: transactional drop-and-recreate of the replaceable data layer.** Inside one transaction: drop every replaceable table child-first, recreate them from the DDL file, bulk `INSERT ... SELECT` parent-first. Rollback restores the previous complete state (proven above). Rejected: ordered `DELETE`+`INSERT` (fails as shown); loading into a second DuckDB file and swapping files (not atomic with lineage and the run log, leaves two DB files to reconcile); `INSERT ... ON CONFLICT` upserts (cannot remove rows that disappeared from a source and every FK-referenced row update is fragile in DuckDB).

Consequences designed in:
- **Persistent tables, never dropped:** `ingestion_runs`, `ingestion_errors`, `dataset_lineage`, `data_quality_results`, `model_versions`, `metric_definitions`, `schema_meta`. No table has a FK to `ingestion_runs` (DuckDB updates a PK row as delete+insert, so `UPDATE ingestion_runs SET status=...` would fail once a child references it). `run_id` columns are plain INTEGER everywhere, and "run_id exists" is a validation check instead. `model_versions` is referenced by the empty later-phase tables, so it is only inserted into (`ON CONFLICT DO NOTHING` on `name`), never updated.
- **Replaceable tables** (dropped and recreated each load, including the empty later-phase tables because they carry FKs to `players`/`matches`/`teams`): everything else.
- FK to `players`: `players` is built as the union of every player id seen in any official source (mapping, playing_eleven, deliveries striker/non-striker/bowler/dismissed, match captains), so the real FKs from `deliveries`/`match_squads`/`matches` stay hard and no row is dropped.

## 1. Table-by-table DDL outline (final DDL goes to `d:/Data/backend/data/audit/phase2_schema.sql`)

Conventions: `INTEGER` ids, `VARCHAR` text, `DATE`, `TIMESTAMP`, `BOOLEAN`, `DOUBLE`; Postgres-compatible syntax; `source_file VARCHAR NOT NULL`, `source_row_no INTEGER` and `ingestion_run_id INTEGER NOT NULL` on every imported record (no FK on `ingestion_run_id`). Column naming differs from Phase 1 draft in one place: the innings column is `innings_number` (typed tables) and stays `innings` in the raw tables. Applied by code from this file (`Database.apply_schema()`); a hash of the file text is the schema version.

### 1a. Persistent control tables
- `ingestion_runs(run_id PK default nextval, started_at, finished_at, status [RUNNING|SUCCESS|NO_CHANGE|FAILED|ABORTED], mode [LOAD|FORCE|VALIDATE_ONLY], schema_version, data_version, force_flag, reason, error_message, source_hashes JSON, rows_loaded JSON, git_commit NULL)`.
- `ingestion_errors(error_id PK, run_id, severity [ERROR|WARNING], error_type [EXCEPTION|CAST_FAILURE|DUPLICATE_KEY_PRESERVED|ORPHAN_RECORDED_NOT_DROPPED|HEADER_MISMATCH|SOURCE_CHANGED_DURING_RUN], table_name, source_file, source_row_no, message, raw_payload JSON, created_at)`.
- `dataset_lineage(lineage_id PK, run_id, file_name, file_path, sha256, size_bytes, row_count, column_count, role [PRIMARY|COMPARISON_RAW|SKIPPED_BY_DECISION|PENDING_PHASE], target_table NULL, load_status [LOADED|SKIPPED_BY_DECISION|PENDING_PHASE], decision_note, loaded_at)`. Lineage rows are inserted inside the load transaction, so a lineage row exists only for a committed load.
- `data_quality_results(result_id PK, run_id, check_name, category [ROW_COUNT|PK|FK|RECONCILIATION|CONSISTENCY|OPEN_ISSUE], severity [ERROR|WARNING|INFO], status [PASS|FAIL|OPEN], expected VARCHAR, observed VARCHAR, affected_rows BIGINT, details JSON, checked_at)`. Append per run; the latest run's rows are the current view (`v_latest_data_quality` view).
- `model_versions(model_version_id PK, name UNIQUE, kind [DATA_VERSION|SCHEMA_VERSION|WEIGHTING_CONFIG], status [ACTIVE|PROVISIONAL], config_json, notes, created_at, created_by_run_id)`.
- `metric_definitions(metric_name, version, formula, input_columns, source_datasets, evidence, status [VERIFIED|PARTIALLY_VERIFIED|UNVERIFIED], applies_to, registered_at, PRIMARY KEY (metric_name, version))`.
- `schema_meta(key PK, value)` (schema_version, ddl_sha256).

### 1b. Raw tables (replaceable, all columns VARCHAR, verbatim; empty string kept as NULL by DuckDB, literal `None` kept)
- `raw_ball_by_ball` (from `ball_by_ball.csv`) and `raw_ball_by_ball_updated` (from `updated_ball_by_ball.csv`): the 33 source columns + `source_file`, `source_row_no`, `ingestion_run_id`; `PRIMARY KEY (source_row_no)`. Never read by analytics (`raw_ball_by_ball` is comparison/provenance only).
- The five reference CSVs are staged in TEMP tables only (typed tables carry `source_file`/`source_row_no`), so no extra raw copies.

### 1c. Reference tables (populated)
- `competitions(comp_id PK, comp_name, match_format CHECK IN ('T20','T20I'), season VARCHAR, competition_type [IPL|T20I|OTHER_T20] NOT NULL, + provenance)`. Rule: `comp_name LIKE 'IPL%'` -> IPL; else `match_format='T20I'` -> T20I; else OTHER_T20.
- `teams(team_id PK, team_name, + provenance)` from `teams.csv` (distinct id; fails the run if one id maps to two names, since Phase 1 verified global uniqueness).
- `competition_teams(comp_id, team_id, team_name, PK(comp_id, team_id), FK comp_id, FK team_id, + provenance)` (353 rows from `teams.csv`).
- `venues(venue_id PK, venue_country, + provenance)`; no venue name column exists.
- `players(player_id PK, player_name NOT NULL, name_source [MAPPING|DELIVERIES|UNKNOWN], name_variants JSON, in_mapping, in_playing_eleven, in_deliveries, in_matches_captain BOOLEAN, shares_name_with_other_id BOOLEAN, + ingestion_run_id)`. Name = mapping name, else delivery name; no name-based merging; the 7 duplicate-name pairs stay as separate ids with `shares_name_with_other_id = TRUE`. An id with no name anywhere gets `player_name = '<unknown id N>'` and an OPEN DQ row (expected 0).
- `player_competition_mapping(comp_id, team_id, player_id, player_name, PK(comp_id, team_id, player_id), FK (comp_id, team_id) -> competition_teams, FK player_id -> players, + provenance)`.

### 1d. Match-level tables
- `matches(match_id PK, comp_id FK, match_number, match_date DATE NOT NULL, stage, venue_id FK venues, venue_country, home_team_id FK, home_team, away_team_id FK, away_team, home_team_captain_id FK players NULL, away_team_captain_id FK players NULL, toss_win_team_id FK NULL, toss_opted, man_of_the_match INTEGER (NO FK; 0 is a sentinel), first_inn_revised_overs DOUBLE, second_inn_revised_overs DOUBLE, revised_target INTEGER, knock_out BOOLEAN, win_team_id FK NULL, result VARCHAR (verbatim), result_status VARCHAR NOT NULL, competition_type, has_deliveries BOOLEAN, first_innings_batting_team_id INTEGER NULL (from deliveries innings 1; never from home/away), + provenance)` = all 22 source columns + derived columns. `result_status` comes from `classify_result()` applied to the distinct `result` strings via a small temp mapping table.
- `match_squads(match_id FK, team_id FK, player_id FK, squad_row_no INTEGER, batting_order, is_played, is_captain, is_wk, is_impact, is_impact_off, duplicate_key_flag BOOLEAN, duplicate_group_size INTEGER, mapping_row_exists BOOLEAN, + provenance, PK(match_id, team_id, player_id, squad_row_no))`. `squad_row_no` = 1..k within each (match, team, player) group ordered by `source_row_no`. All 28,381 rows loaded; nothing deduplicated.
- `innings(match_id FK, innings_number CHECK 1..4, batting_team_id FK, bowling_team_id FK, delivery_count, legal_ball_count, batter_runs_total, extras_primary_total, extras_secondary_total, source_total_runs, wicket_rows, max_overid, teams_consistent BOOLEAN, innings_role_status [STANDARD for 1-2 | UNVERIFIED for >=3], + ingestion_run_id, source_file, PK(match_id, innings_number))`. No `is_super_over` column anywhere. `source_total_runs = batter_runs_total + extras_primary_total + extras_secondary_total` (label says it is the source-derived sum, not a verified total).
- `deliveries(match_id, innings_number, innings_ball_num, overid, over_ball_num, batting_team_id FK, bowling_team_id FK, striker_id FK, non_striker_id FK, bowler_id FK, batting_order, batting_type, bowling_type, pace_or_spin, bowl_speed DOUBLE, stroke, delivery_style, over_or_around, on_or_off, is_four, is_six, is_wicket BOOLEAN, dismissal_type_id, dismissal_type (verbatim), dismissed_player_id FK NULL, batter_runs (source runs), extras_type (verbatim, 'None' kept), has_extra BOOLEAN, extras_primary_runs, extras_secondary_runs, extras_split_status = 'UNVERIFIED', is_legal_ball BOOLEAN, legal_ball_status [VERIFIED|UNVERIFIED (Penalty)], extras_label_unverified BOOLEAN (extras_type IN ('other','Penalty')), dismissal_field_anomaly VARCHAR NULL ['DISMISSED_PLAYER_WITHOUT_WICKET'|'WICKET_WITHOUT_DISMISSED_PLAYER'], delivery_time_raw VARCHAR, delivery_ts TIMESTAMP, delivery_time_is_midnight BOOLEAN, source_file, source_row_no, ingestion_run_id, PK(match_id, innings_number, innings_ball_num), FK (match_id, innings_number) -> innings)`. `is_legal_ball = extras_type IS NULL OR extras_type NOT IN ('wide','Overstep','other')`; `has_extra = extras_type IS NOT NULL AND extras_type <> 'None'`. Dismissal fields are kept as given; no bowler credit decided.
- `match_reconciliation(match_id PK FK, comp_id, match_date, home_team_id, away_team_id, result (verbatim), result_status, win_team_id, has_deliveries, delivery_count, innings_count, squad_row_count, played_row_count, no_deliveries_explained BOOLEAN (= NOT has_deliveries AND result_status IN ('ABANDONED','NO_RESULT') AND win_team_id IS NULL), reason VARCHAR built from the actual fields, + provenance)`. All 883 rows.

### 1e. File-comparison tables
- `ball_by_ball_comparison(column_name PK, rows_compared, rows_different, rows_only_in_original, rows_only_in_updated, details JSON)` one row per source column (33). Join on `(match_id, innings, innings_ball_num)`, `IS DISTINCT FROM`. For `extras1_runs`, `details` holds the crosstab (original code, updated value, count, extras_type).
- `ball_by_ball_comparison_detail(match_id, innings, innings_ball_num, column_name, original_value, updated_value, PK(match_id, innings, innings_ball_num, column_name))` for every differing cell EXCEPT `extras1_runs` (that column differs on ~199,980 rows and is summarised by the crosstab; documented choice, keeps the table small). Expected: striker_name 24, non_striker_name 33.

### 1f. Empty later-phase tables (DDL only, with FKs as in `proposed_schema.sql`, `model_version_id` FK to `model_versions`)
`franchise_squads, squad_snapshots, player_availability, source_match_mapping, source_player_mapping, player_batting_stats, player_bowling_stats, player_season_stats, player_phase_stats, player_pressure_stats, match_pressure_summary, player_consistency_stats, team_season_stats, rr_team_analysis, squad_gap_analysis, player_valuation, player_rankings, raw_cricsheet_matches`. Copy from `proposed_schema.sql`, rename `innings_no` -> `innings_number` in `match_pressure_summary`, drop FKs onto `ingestion_runs`. Validation asserts they exist with 0 rows.

Views: `v_latest_data_quality` only.

## 2. Ingestion flow (`IngestionService.run(force=False, validate_only=False)`)

1. **Preflight (no DB writes).** Resolve the 6 core paths, `ball_by_ball.csv`, the 4 skipped files and `ipl squad.csv` from `Settings.data_root`. Missing core file -> FAILED run. For each file: read header (stdlib `csv`), compare to the expected column list (the Phase 1 expected set, order-insensitive for the two ball files), compute `sha256` (chunked), size, data-row count (`SELECT count(*) FROM read_csv`). Header mismatch on a loaded file -> FAILED, `HEADER_MISMATCH` error.
2. **Run row.** Autocommit `INSERT INTO ingestion_runs ... status RUNNING` (committed before the load transaction so it survives rollback). Any older run still RUNNING is set to ABORTED.
3. **Idempotency decision** (skipped when `--force`): fetch the lineage rows of the most recent run that has any lineage rows (= last committed load). If every tracked file's sha256 equals the current one, `schema_meta.ddl_sha256` equals the current DDL hash, the config weights equal the latest WEIGHTING_CONFIG row, AND each loaded table's row count equals the lineage row count (cheap tamper guard), then set status `NO_CHANGE`, write nothing else, print "no change" and exit 0. Otherwise continue with a recorded `reason`. `--validate-only` skips the load and just re-runs validation (section 3) on the current DB. The skipped files are hashed on every run; a changed skipped file counts as a change and triggers a full reload (a reload takes seconds, so no partial logic).
4. **Single load transaction** (`with db.transaction():`): `BEGIN`; drop the replaceable tables child-first; execute the replaceable part of the DDL; create TEMP staging tables for the 5 reference CSVs (`read_csv(..., all_varchar=true)` plus `row_number() OVER () AS source_row_no`); load `raw_ball_by_ball`, `raw_ball_by_ball_updated`; then typed inserts in parent order: competitions, teams, competition_teams, venues, players, player_competition_mapping, matches (with `result_status` mapping and `competition_type`), match_squads, innings (aggregated from staged updated deliveries), deliveries, then `matches.has_deliveries`/`first_innings_batting_team_id` update (UPDATE of `matches` columns that nothing references through a FK; if DuckDB rejects it because `matches` is FK-referenced, compute these columns in the INSERT SELECT via joins to the staged deliveries instead; the plan chooses the INSERT-time join so no UPDATE is needed), match_reconciliation, ball_by_ball_comparison + detail, lineage rows (all roles), `metric_definitions` and `model_versions` inserts (`ON CONFLICT DO NOTHING`), `schema_meta`. A `fault_hook(step_name)` callable is invoked after each step; tests use it to raise mid-load.
   In-transaction hard checks (raise -> rollback): header-derived row counts equal table counts for every loaded table; `(match_id, innings, innings_ball_num)` unique in both raw ball tables; `teams.csv` one name per team_id; no unclassifiable cast loss on key columns (a NULL typed key from a non-NULL source cell raises). `COMMIT`.
5. **Row-level warnings** (collected during the transaction in Python lists, written after COMMIT in a second small transaction so they cannot be lost or confused with rollback): `CAST_FAILURE` (non-NULL source, NULL typed value, raw payload kept in the raw table and in `raw_payload`), `DUPLICATE_KEY_PRESERVED` (the 75 playing_eleven rows), `ORPHAN_RECORDED_NOT_DROPPED` (playing_eleven rows without a mapping row; delivery rows whose striker/bowler is not in that match's squad). All with `table_name`, `source_file`, `source_row_no`, message and JSON payload.
6. **Source-unchanged check:** as the last action before COMMIT in step 4, re-hash the originals; if any hash differs from the preflight hash, raise `SOURCE_CHANGED_DURING_RUN` so the transaction rolls back and the run is FAILED.
7. **Validation + reports** (section 3) on the committed data; results inserted into `data_quality_results`; JSON/MD/CSV reports written. Then `ingestion_runs` is updated to SUCCESS (or FAILED).
8. **Failure path:** any exception in steps 4-6 -> `ROLLBACK` (inside the context manager), then outside the transaction: `UPDATE ingestion_runs SET status='FAILED', error_message=..., finished_at=...`, `INSERT INTO ingestion_errors` (EXCEPTION row + collected row-level rows), and rewrite `data/audit/ingestion_errors.csv` from the table for this run. Exit code 1. Previous data tables are untouched (verified by a test that compares table counts and a content hash before and after).
9. Exit codes: 0 success or no change; 1 FAILED; 2 loaded but a validation check has status FAIL.

Modular persistence: `app/repositories/base.py` (`Repository` Protocol: `execute`, `query`, `transaction`, `executescript`), `app/repositories/duckdb_repository.py` (implementation), and `app/core/database.py` (`connect()`, `Database` wrapper, DDL loader). The ingestion SQL stays inside `csv_loader.py` per table (DuckDB dialect), so a PostgreSQL implementation later replaces `csv_loader` SQL builders and the repository only. No SQLAlchemy dependency is added now.

## 3. Validation (`app/services/validation_service.py`; stored in `data_quality_results`, written to `data/audit/phase2_validation_report.json` and `.md`)

Every number is computed from the loaded DB; expected values from the brief are used only as `expected` labels for PASS/FAIL, and a differing actual is reported as is.

**PASS/FAIL checks (hard):**
- Row counts: table vs file for competitions 141, teams -> competition_teams 353 (and `teams` = distinct ids 38), matches 883, match_squads 28,381, player_competition_mapping 6,413, raw_ball_by_ball 200,999, raw_ball_by_ball_updated 200,999, deliveries 200,999, match_reconciliation 883. Source counts come from the file (independent of the 141/353/... spec numbers, which are a second check; the spec check is skipped when `expected_counts` is overridden, as in the synthetic tests).
- PK uniqueness for every table with a PK (`SELECT count(*) - count(DISTINCT key)`), including deliveries and match_squads.
- FK orphan count (all expected 0) for each enforced FK, listed individually: competition_teams -> competitions/teams; player_competition_mapping -> competition_teams/players; matches -> competitions/venues/teams(home, away, toss, win)/players(captains); match_squads -> matches/teams/players; innings -> matches/teams; deliveries -> matches/innings/teams(batting, bowling)/players(striker, non-striker, bowler, dismissed). Also: all `run_id`/`ingestion_run_id` values exist in `ingestion_runs`.
- Reconciliation: matches (883) = with deliveries + without; list the without-delivery matches with `result`, `result_status`, `win_team_id`, `no_deliveries_explained`; every delivery `match_id` exists in matches; `has_deliveries` equals the existence of deliveries.
- batting_team/bowling_team of each innings are exactly the match's home/away pair (and different from each other); one batting team per innings (`teams_consistent`).
- Innings numbering: values in 1..4; innings 1 exists whenever a match has deliveries; `innings_ball_num` exactly 1..n per innings; `legal_ball_count` per innings recomputed independently from `extras_type`; `source_total_runs` recomputed.
- Original vs updated comparison summary per column (values reported, status INFO; the row count equality 200,999 vs 200,999 and the key-set equality are PASS/FAIL).
- Empty later-phase tables exist and have 0 rows; all `result_status` values in the known set (UNKNOWN count reported, WARNING if > 0); `competition_type` assigned to every competition; IPL competitions have `match_format = 'T20'` (reported).
- Source files unchanged (sha256 now vs lineage).

**OPEN issues (status OPEN with the actual count; never FAIL, never fixed):** playing_eleven repeated keys (rows/groups/matches), delivery rows + distinct (match, striker) pairs whose striker is not in the match squad, same for bowler, matches with no playing_eleven rows, playing_eleven rows with no mapping row for that match's comp/team, deliveries with `is_wicket=false` but a `dismissed_player_id`, wicket rows without `dismissed_player_id` (list the dismissal types), `extras_type` `other` and `Penalty` label unverified (row counts), `extras_secondary_runs` split unverified, innings 3/4 role unverified (matches, rows), 10 innings disagreeing with Cricsheet totals (matches 14130, 14164, 32618, 37349, 37352, 50504) and 108 matches unlinkable to Cricsheet (both carried from `data/audit/cricsheet_overlap_report.json` as informational OPEN rows, source cited, not recomputed since Cricsheet is not loaded), 7 duplicate player names mapped to two ids (recomputed), `man_of_the_match = 0` sentinel count, `delivery_ist_time` UTC suffix vs column name, midnight-timestamp row count.

Reports also written: `data/audit/ingestion_errors.csv` (always, header-only if empty), `data/audit/ball_by_ball_comparison.json` + `.md`, `data/audit/phase2_match_reconciliation.csv` (new name; the Phase 1 `match_reconciliation.csv` is not overwritten).

## 4. metric_definitions and model_versions rows

`metric_definitions` (version `1.0`, `registered_at` set on first insert, `ON CONFLICT (metric_name, version) DO NOTHING`; a changed definition needs a new version):
- `is_legal_ball`: `extras_type IS NULL OR extras_type NOT IN ('wide','Overstep','other')`; inputs `extras_type`; dataset `updated_ball_by_ball.csv`; evidence "equals Cricsheet legal balls in 1,497 of 1,504 innings (extras_mapping.md)"; status VERIFIED (Penalty treated as legal by this rule but `legal_ball_status`=UNVERIFIED for that row).
- `batter_runs`: source `runs`; evidence 1,488 of 1,504 innings equal Cricsheet batter runs; VERIFIED.
- `has_extra`: `extras_type IS NOT NULL AND extras_type <> 'None'`; literal `None` is a category; VERIFIED (definitional, 189,167 rows 'None').
- `competition_type`: rule above; evidence counts per type from the DB; VERIFIED against competitions.csv.
- `result_status`: `classify_result(result)` from `app/data_pipeline/data_quality.py`; Phase 1 distribution; VERIFIED for the 16 no-delivery matches, PARTIALLY_VERIFIED overall (text classifier).
- `source_total_runs`: `batter_runs + extras_primary_runs + extras_secondary_runs` summed per innings; evidence 1,494 of 1,504 innings equal Cricsheet; PARTIALLY_VERIFIED (sum verified, extras_2 split UNVERIFIED).
- `extras_label_unverified`, `innings_role_status`, `extras_secondary_runs`: status UNVERIFIED with the reason text.

`model_versions` rows (insert only): `data_version` = `data-<first 12 hex of sha256 over the sorted "name:sha256" lines of PRIMARY + COMPARISON_RAW files>`; `schema_version` = `phase2-<first 8 hex of DDL sha256>`; `weighting_config` name `weighting-ipl0.70-t20i0.30`, `config_json={"ipl_weight":0.7,"t20i_weight":0.3,"status":"PROVISIONAL","note":"no calculation performed in Phase 2; sensitivity grid to be defined before use"}`. Weights come from `Settings.ipl_weight` / `t20i_weight`.

## 5. Ordered implementation items

- [ ] 1. Config: add `ipl_weight: float = 0.70`, `t20i_weight: float = 0.30` and a `model_validator` (each in [0,1], sum within 1e-9 of 1, else `ValueError`) to `Settings`; add `ingestion_errors_csv`, `validation_report_json/md` path properties derived from `audit_dir`; add `SUPERR_IPL_WEIGHT`/`SUPERR_T20I_WEIGHT` lines to `.env.example`. Register pytest marker `realdata` in `pyproject.toml` (`[tool.pytest.ini_options] markers`).
      Files: `app/core/config.py`, `.env.example`, `pyproject.toml`
      Verify: `python -m pytest -q` (19 Phase 1 tests still pass).

- [ ] 2. Write the final DDL `data/audit/phase2_schema.sql` from section 1 (two marked blocks: `-- PERSISTENT` and `-- REPLACEABLE`, with the drop order listed in a comment) and `app/core/database.py` (`connect`, `Database.transaction()`, `apply_schema(persistent=True/replaceable=True)`, `drop_replaceable()` using an explicit child-first table list, `ddl_sha256()`), plus `app/repositories/{__init__,base,duckdb_repository}.py`. Add a test module `tests/test_duckdb_schema.py`: schema applies on a fresh in-memory DB; replace-in-transaction with data then rollback restores previous rows (the strategy experiment, kept as a regression test); every FK is a real constraint (insert orphan raises).
      Files: `data/audit/phase2_schema.sql`, `app/core/database.py`, `app/repositories/*.py`, `tests/test_duckdb_schema.py`
      Verify: `python -m pytest tests/test_duckdb_schema.py -q`.

- [ ] 3. `app/data_pipeline/csv_loader.py`: `SourceSpec` list (file name, role, target table, expected columns, expected row count from `EXPECTED_CSVS`; add `updated_ball_by_ball.csv` = 200,999), `sha256_file`, `profile_file` (header, rows, cols), header validation, SQL builders for the temp staging tables, raw ball tables, and each typed INSERT ... SELECT (casts via `TRY_CAST`, boolean mapping from `true/false` and `0/1`, `strptime` for `delivery_ts`, derived columns exactly as section 1). Include `result_status` mapping via `classify_result`.
      Files: `app/data_pipeline/csv_loader.py`
      Verify: covered by item 5 tests (import check: `python -c "import app.data_pipeline.csv_loader"`).

- [ ] 4. `app/services/ingestion_service.py` implementing section 2 (run row, idempotency, transaction, post-commit error writing, failure path, `fault_hook`, `force`, `validate_only`, lineage with SKIPPED_BY_DECISION and PENDING_PHASE rows, metric_definitions/model_versions registration) and `app/services/validation_service.py` implementing section 3 and the report writers. Add `app/services/__init__.py`, `app/repositories` use throughout.
      Files: `app/services/{__init__,ingestion_service,validation_service}.py`
      Verify: `python -m ruff check app` and item 5 tests.

- [ ] 5. Tests `tests/test_csv_ingestion.py` with a `make_dataset(tmp_path)` fixture that writes 8 mini CSVs (core 6 + `ball_by_ball.csv` + skipped files; 4 matches, 1 without deliveries (ABANDONED), a duplicated playing_eleven key, innings 3 with `other`/`Penalty`/`None`/`wide` rows, a striker missing from the squad, a mapping-less squad row) and a `Settings(data_root=tmp, duckdb_path=tmp/db.duckdb, audit_dir=tmp/audit)`; the service is called with `expected_counts={}`. Cases: idempotency (second run `NO_CHANGE`, identical table counts and content hash); `--force` reload gives identical counts; changed CSV triggers reload; transaction rollback via `fault_hook` raising in `deliveries` (tables unchanged, run FAILED, `ingestion_errors` has an EXCEPTION row, written after rollback); duplicate playing_eleven preserved with `duplicate_key_flag`/`squad_row_no`; innings 3/4 `innings_role_status='UNVERIFIED'` and no `is_super_over` column exists; `other`/`Penalty` have `extras_label_unverified` TRUE, `other` `is_legal_ball` FALSE, `Penalty` legal with `legal_ball_status='UNVERIFIED'`; `None` kept verbatim with `has_extra` FALSE and 'legbyes' legal with `has_extra` TRUE; legal-ball count per innings; orphan striker not dropped and recorded in `ingestion_errors` and `data_quality_results`; the 4 skipped files and `ipl squad.csv` in lineage with the right role/status and no table rows; Settings weight validation (0.7/0.3 ok, 0.6/0.6 rejected, negative rejected, env override); match reconciliation (match without deliveries, `no_deliveries_explained`); original-vs-updated comparison rows (extras1 crosstab, name diffs in detail table); a non-existing `source_file`/provenance check (no NULL `source_file`/`ingestion_run_id` in any imported table); source-file-unchanged check. Plus `@pytest.mark.realdata` integration test that ingests the real `d:/Data` CSVs into a `tmp_path` DuckDB and asserts the real counts (141/353/883/28,381/6,413/200,999 x3, 867 matches with deliveries, 16 without, 75 duplicate rows in 35 groups, comparison diffs 199,980/24/33 as observed values compared to what the DB computes), skipped when the data directory is absent.
      Files: `tests/test_csv_ingestion.py`
      Verify: `python -m pytest -q -m "not realdata"` then `python -m pytest -q`.

- [ ] 6. Scripts: `scripts/ingest_competition_csv.py` (`--force`, `--validate-only`, `--db`, `--data-root`, prints run id, status, per-table row counts, validation PASS/FAIL/OPEN counts, exit codes in section 2) and `scripts/verify_database.py` (independent: stdlib `csv` + `hashlib` + `collections`, opens DuckDB `read_only=True`; checks file hashes vs lineage, row counts per table, key uniqueness recomputed in Python, source_row_no order, delivery/innings/legal-ball totals recomputed with the stdlib reader, duplicate playing_eleven groups, matches without deliveries set, orphan players, original-vs-updated diff counts, table row sums; prints `PASS`/`FAIL` per check, exit 1 on any FAIL).
      Files: `scripts/ingest_competition_csv.py`, `scripts/verify_database.py`
      Verify: `python scripts/ingest_competition_csv.py --help` and `python scripts/verify_database.py --help` exit 0.

- [ ] 7. Real run in this order, capturing raw output: `python scripts\ingest_competition_csv.py` (first run, expect SUCCESS, record run id, timing), `python scripts\ingest_competition_csv.py` (second run, expect `NO_CHANGE`, identical counts), `python scripts\verify_database.py`. If a count differs from the brief, report the actual number; if a hard check fails, fix the code only if the cause is a bug, otherwise report it. Do not edit original data.
      Files: `data/database/superr.duckdb`, `data/audit/{ingestion_errors.csv,phase2_validation_report.json,phase2_validation_report.md,ball_by_ball_comparison.json,ball_by_ball_comparison.md,phase2_match_reconciliation.csv}`
      Verify: exit codes 0, 0, 0; second-run output contains `no change`; sha256 of the original CSVs unchanged (script prints it).

- [ ] 8. Docs and deliverables: write `data/audit/phase2_ingestion_plan.md` (user-facing schema + ingestion plan, condensed from this document), update `README.md` (Phase 2 section: commands, tables, idempotency, `--force`, `--validate-only`, test markers), write `d:/Data/.agents/tasks/phase2_user_summary.md` (schema overview with FKs enforced vs recorded-only; design; commands; ACTUAL results: counts vs source, run ids, second-run result, PK/FK table, 16-match reconciliation, comparison summary, OPEN issues with actual counts, errors encountered, deviations, pytest/ruff output, files created/modified, Phase 3 leftovers) and `d:/Data/.agents/tasks/phase2_verification.md` (raw command outputs).
      Files: as listed
      Verify: files exist; numbers in the summary match the command output captured in item 7/9.

- [ ] 9. Full verification: `python -m pytest -q` (all, including `realdata`; expect 19 existing + new), `python -m ruff check .`, `python -m ruff format --check .` (run `python -m ruff format .` and fix findings first). Re-run `python scripts\verify_database.py` after tests to confirm the project DB was not touched by the tests.
      Verify: pytest all pass; ruff check "All checks passed!"; ruff format "already formatted"; verify script exit 0.

Dependencies: 1 -> 2 -> 3 -> 4 -> 5 (5 can be written alongside 4) -> 6 -> 7 -> 8/9. Items 6 and 5 can run in either order but 7 needs both. Each item leaves the repo buildable (`python -m pytest -q` passes at the end of 1, 2, 4+5).

## 6. Execution and verification commands (PowerShell, from `d:/Data/backend`)

```powershell
$env:PYTHONUTF8 = 1
python scripts\ingest_competition_csv.py          # first load
python scripts\ingest_competition_csv.py          # second run: expect "no change"
python scripts\ingest_competition_csv.py --force  # optional: identical counts after a reload
python scripts\verify_database.py                 # independent PASS/FAIL, non-zero exit on FAIL
python -m pytest -q
python -m pytest -q -m "not realdata"             # fast subset
python -m ruff check .
python -m ruff format --check .
```

## 7. Deviations and risks

Deviations from the brief / Phase 1 draft (all to be repeated in `phase2_user_summary.md`):
1. **Replace strategy is drop-and-recreate inside one transaction**, not DELETE+INSERT or upsert, because the DuckDB 2.0.0 test shows DELETE+INSERT of an FK-referenced parent fails even inside one transaction. Consequence: replaceable tables are recreated on every load (empty later-phase tables too), and table-level `ingestion_run_id` on data rows changes with each forced reload.
2. **No FK to `ingestion_runs`** (UPDATE of a PK-referenced row is unreliable in DuckDB); validation checks run-id integrity instead.
3. **`man_of_the_match` has no FK** (value 0 is a sentinel in 119 rows). **`match_squads`, deliveries' striker/bowler vs squad, and squad -> mapping are recorded-only relations** (known orphans), not FKs. All other reference FKs are hard.
4. **Column rename:** `innings_number` in typed tables (brief writes `innings`); raw tables keep `innings`.
5. `delivery_ist_time` carries a `UTC` suffix; stored as a naive TIMESTAMP with the raw string kept; no timezone conversion applied (UNVERIFIED which zone is true).
6. Extra columns added beyond the brief (flags and provenance): `legal_ball_status`, `dismissal_field_anomaly`, `delivery_time_is_midnight`, `extras_split_status`, `mapping_row_exists`, `teams_consistent`, `first_innings_batting_team_id`, `players` source flags. `ball_by_ball_comparison` is per-column with a detail table that excludes `extras1_runs` cells (summarised by crosstab).
7. Cricsheet-derived OPEN items (10 disagreeing innings, 108 unlinked matches) are carried from the Phase 1 JSON report, not recomputed, because Cricsheet is not loaded in this phase.
8. `ipl squad.csv` is recorded in lineage as PENDING_PHASE (hash/rows only); no table is populated from it.
9. The sensitivity tests mentioned in decision 4 are not defined anywhere in the brief and no calculation is allowed yet; only the weight config row is stored. The grid must be specified before Phase 3.

Risks and mitigations:
- `row_number() OVER ()` ordering on `read_csv` could change if DuckDB runs the reader in parallel on a different build. Mitigation: `verify_database.py` and a real-data test compare ordering against the stdlib `csv` reader; fallback is `read_csv(..., parallel=false)` or loading rows via pandas.
- A 200,999-row insert with 8 FKs and a composite PK could be slow or memory-heavy. Mitigation: set-based `INSERT ... SELECT`; measure in item 7; if > 60 s, create FKs-bearing table first and keep ART indexes minimal (no secondary indexes on deliveries in Phase 2).
- DuckDB may reject `DROP`/`CREATE` of a table referenced by an index/FK in some orders. Mitigation: explicit tested drop order list covered by `test_duckdb_schema.py`; if a failure appears on the full schema, report and fall back to dropping the whole replaceable set via a generated topological order.
- Hard in-transaction checks could fail on real data for a reason Phase 1 missed (e.g. a team_id with two names). The run then FAILS with the table untouched; report honestly, do not relax the check without a warning notification.
- Tests must never touch `data/database/superr.duckdb`: every test passes explicit temp paths; the real-data test uses `tmp_path`.
- `Settings` has an `.env` reader (`env_file=".env"`); tests construct `Settings(...)` with explicit arguments so a developer `.env` cannot change results.
- Data-row numbering assumes no quoted line breaks; documented, and the stdlib reader in the verify script counts logical records the same way.
- Decision on workflow shape: the work is one tightly coupled pipeline (schema, loader, service, validation, tests share the same table definitions), so it is NOT split into separate FEAT steps and the existing implement-and-review loop with its gate file is kept as is.
