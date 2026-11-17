# Phase 2: DuckDB schema and ingestion plan

Scope: the official competition CSVs only. No Cricsheet loading, no pressure or ranking calculation, no API or frontend. DuckDB 2.0.0. The DDL is `phase2_schema.sql` (the schema version is the hash of that file).

## Sources and decisions applied

| file | role | handling |
|---|---|---|
| competitions.csv, teams.csv, matches.csv, playing_eleven.csv, competition_team_player_mapping.csv | PRIMARY | typed tables |
| updated_ball_by_ball.csv | PRIMARY (authoritative deliveries) | `raw_ball_by_ball_updated`, `deliveries`, `innings` |
| ball_by_ball.csv | COMPARISON_RAW | `raw_ball_by_ball`, `ball_by_ball_comparison`, `ball_by_ball_comparison_detail`; never read by analytics |
| matches 2026.csv, batting/bowling/fielding_stats2026.csv | SKIPPED_BY_DECISION | `dataset_lineage` row with sha256 and row count; no data loaded |
| ipl squad.csv | PENDING_PHASE | `dataset_lineage` row only |

## Tables

Persistent (never dropped): `ingestion_runs`, `ingestion_errors`, `dataset_lineage`, `data_quality_results` (+ view `v_latest_data_quality`), `model_versions`, `metric_definitions`, `schema_meta`.

Replaceable data layer (dropped child-first and recreated inside the load transaction): `competitions`, `teams`, `competition_teams`, `venues`, `players`, `player_competition_mapping`, `matches`, `match_squads`, `innings`, `deliveries`, `match_reconciliation`, `raw_ball_by_ball`, `raw_ball_by_ball_updated`, `ball_by_ball_comparison`, `ball_by_ball_comparison_detail`.

Primary keys: competitions(comp_id), teams(team_id), competition_teams(comp_id, team_id), venues(venue_id), players(player_id), player_competition_mapping(comp_id, team_id, player_id), matches(match_id), match_squads(match_id, team_id, player_id, squad_row_no), innings(match_id, innings_number), deliveries(match_id, innings_number, innings_ball_num), match_reconciliation(match_id), raw tables(source_row_no).

Enforced foreign keys: competition_teams to competitions and teams; player_competition_mapping to competition_teams and players; matches to competitions, venues, teams (home, away, toss, win) and players (captains); match_squads to matches, teams, players; innings to matches and teams; deliveries to innings (match_id, innings_number), teams (batting, bowling) and players (striker, non-striker, bowler, dismissed); match_reconciliation to matches.

Recorded-only relations (kept without a FK because known unresolved ids exist, with orphan checks stored): playing_eleven rows without a mapping row (`match_squads.mapping_row_exists`), deliveries whose striker or bowler is not in the match squad (`ingestion_errors`, `open_*` checks), `matches.man_of_the_match` (0 is a sentinel), `matches.first_innings_batting_team_id`, `ingestion_run_id` on every table (no FK to `ingestion_runs`).

`players` is the union of every player id seen in the mapping, playing_eleven, deliveries (striker, non-striker, bowler, dismissed) and match captains, so the player FKs are hard and no row is dropped. Players are never merged by name.

## Column rules

- Every imported record has `source_file`, `source_row_no` (1-based data row, header excluded) and `ingestion_run_id`.
- `deliveries`: `batter_runs` = source `runs`; `extras_type` verbatim (`'None'` stays `'None'`, `has_extra` derived); `extras_primary_runs` = `extras1_runs`, `extras_secondary_runs` = `extras_2_runs` (`extras_split_status` = UNVERIFIED); `is_legal_ball` = `extras_type` not in (`wide`, `Overstep`, `other`); `extras_label_unverified` is true for `other` and `Penalty`; dismissal fields verbatim plus `dismissal_field_anomaly`; the timestamp keeps the raw string and a naive parsed value.
- `innings`: `innings_role_status` is `UNVERIFIED` for innings 3 and 4. There is no `is_super_over` column anywhere.
- `match_squads`: nothing is de-duplicated; `squad_row_no`, `duplicate_key_flag`, `duplicate_group_size`.
- `competitions.competition_type`: IPL when `comp_name` starts with `IPL`, T20I when `match_format` is `T20I`, otherwise OTHER_T20. `matches.result_status` comes from the Phase 1 `classify_result`.
- `model_versions` stores the data version, schema version and the provisional weighting config (IPL 0.70, T20I 0.30, configurable and validated to sum to 1).

## Ingestion flow

1. Preflight, no data writes: file presence, header check, sha256, size, row count for each tracked file.
2. A `RUNNING` row is committed in `ingestion_runs` (older `RUNNING` rows become `ABORTED`).
3. Idempotency (skipped with `--force`): the last run that has lineage rows must be `SUCCESS`; every file sha256, the DDL hash and each loaded table's row count must equal the lineage values. Otherwise the run reloads and records the reason. A matching run ends as `NO_CHANGE` with no other writes.
4. One DuckDB transaction: drop replaceable tables, recreate them, stage each CSV as an all-VARCHAR temp table, run hard checks (row counts, key casts, one name per team id, unique ball keys), insert in parent order, build the original-vs-updated comparison, write lineage, model versions and metric definitions, re-hash the sources, commit. Any exception rolls back to the previous complete state.
5. After commit: row-level findings (preserved duplicate keys, orphans, non-key cast failures) are written to `ingestion_errors`; validation results go to `data_quality_results`; reports and `ingestion_errors.csv` are written.
6. On failure: rollback first, then the run is set to `FAILED`, the exception and any collected rows go to `ingestion_errors`, and `ingestion_errors.csv` is rewritten.

Replace strategy, tested on DuckDB 2.0.0 (regression tests in `tests/test_duckdb_schema.py`): `DELETE` then `INSERT` of an FK-referenced parent fails even inside one transaction; `DROP` + `CREATE` + `INSERT` followed by `ROLLBACK` restores the old tables and rows; the same sequence followed by `COMMIT` shows the new data. The load therefore uses transactional drop-and-recreate.

## Validation (stored in `data_quality_results`)

PASS/FAIL: row counts against each file and against the brief, PK uniqueness, FK orphan counts, run-id and source-file provenance, match reconciliation, innings consistency (team pair equals home/away, legal-ball count and run totals recomputed from the raw table), original-vs-updated key sets, source files unchanged. OPEN (preserved, never fixed): repeated playing_eleven keys, matches without playing_eleven rows, squad rows without a mapping row, strikers/bowlers outside the squad, dismissed player without a wicket flag, wicket without a dismissed player, `other` and `Penalty` labels, extras split, innings 3/4 role, `man_of_the_match` = 0, UTC suffix on `delivery_ist_time`, midnight timestamps, duplicate player names, and two Cricsheet-derived items carried from Phase 1.

## Out of scope in Phase 2

Analytics tables, Cricsheet tables, raw 2026 tables, the sensitivity-test grid for the IPL/T20I weights (it is not defined in the brief), any pressure or ranking calculation.
