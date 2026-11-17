-- SupeRR Selector Season 2: Phase 2 DuckDB schema (official competition CSVs only).
--
-- Applied by app/core/database.py. The file has two blocks, split on the marker lines below.
--   PERSISTENT : control tables, created once (IF NOT EXISTS), never dropped by a reload.
--   REPLACEABLE: the data layer, dropped (child first) and recreated inside the load transaction.
-- Replace strategy: transactional DROP + CREATE + INSERT. Tested on DuckDB 2.0.0: DELETE then
-- INSERT of an FK-referenced parent row fails even inside one transaction, while DROP/CREATE/INSERT
-- followed by ROLLBACK restores the previous tables and rows completely.
-- Replaceable drop order (child first): ball_by_ball_comparison_detail, ball_by_ball_comparison,
--   match_reconciliation, deliveries, innings, match_squads, matches, player_competition_mapping,
--   players, venues, competition_teams, teams, competitions, raw_ball_by_ball_updated,
--   raw_ball_by_ball.
-- Provenance on every imported record: source_file, source_row_no (1-based data row, header
--   excluded), ingestion_run_id. ingestion_run_id carries NO foreign key to ingestion_runs
--   (DuckDB cannot UPDATE a referenced PK row reliably); run-id integrity is a validation check.
-- Not created in Phase 2 (deferred): analytics tables, Cricsheet tables, 2026 raw tables.
-- Deliberately absent: any is_super_over column (innings 3/4 role is UNVERIFIED).

-- ==== PERSISTENT ====
CREATE SEQUENCE IF NOT EXISTS seq_ingestion_run START 1;
CREATE SEQUENCE IF NOT EXISTS seq_ingestion_error START 1;
CREATE SEQUENCE IF NOT EXISTS seq_lineage START 1;
CREATE SEQUENCE IF NOT EXISTS seq_dq_result START 1;
CREATE SEQUENCE IF NOT EXISTS seq_model_version START 1;

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id INTEGER PRIMARY KEY DEFAULT nextval('seq_ingestion_run'),
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status VARCHAR NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'NO_CHANGE', 'FAILED', 'ABORTED')),
    mode VARCHAR NOT NULL,
    schema_version VARCHAR,
    data_version VARCHAR,
    force_flag BOOLEAN NOT NULL DEFAULT FALSE,
    reason VARCHAR,
    error_message VARCHAR,
    source_hashes VARCHAR,
    rows_loaded VARCHAR
);

CREATE TABLE IF NOT EXISTS ingestion_errors (
    error_id INTEGER PRIMARY KEY DEFAULT nextval('seq_ingestion_error'),
    run_id INTEGER NOT NULL,
    severity VARCHAR NOT NULL,
    error_type VARCHAR NOT NULL,
    table_name VARCHAR,
    source_file VARCHAR,
    source_row_no INTEGER,
    message VARCHAR,
    raw_payload VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS dataset_lineage (
    lineage_id INTEGER PRIMARY KEY DEFAULT nextval('seq_lineage'),
    run_id INTEGER NOT NULL,
    file_name VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    sha256 VARCHAR,
    size_bytes BIGINT,
    row_count BIGINT,
    column_count INTEGER,
    role VARCHAR NOT NULL,
    target_table VARCHAR,
    load_status VARCHAR NOT NULL,
    decision_note VARCHAR,
    loaded_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS data_quality_results (
    result_id INTEGER PRIMARY KEY DEFAULT nextval('seq_dq_result'),
    run_id INTEGER NOT NULL,
    check_name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('PASS', 'FAIL', 'OPEN', 'INFO')),
    expected VARCHAR,
    observed VARCHAR,
    affected_rows BIGINT,
    details VARCHAR,
    checked_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS model_versions (
    model_version_id INTEGER PRIMARY KEY DEFAULT nextval('seq_model_version'),
    name VARCHAR NOT NULL UNIQUE,
    kind VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    config_json VARCHAR NOT NULL,
    notes VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    created_by_run_id INTEGER
);

CREATE TABLE IF NOT EXISTS metric_definitions (
    metric_name VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    formula VARCHAR NOT NULL,
    input_columns VARCHAR,
    source_datasets VARCHAR,
    evidence VARCHAR,
    status VARCHAR NOT NULL,
    registered_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (metric_name, version)
);

CREATE TABLE IF NOT EXISTS schema_meta (
    key VARCHAR PRIMARY KEY,
    value VARCHAR
);

CREATE OR REPLACE VIEW v_latest_data_quality AS
SELECT * FROM data_quality_results
WHERE run_id = (SELECT max(run_id) FROM data_quality_results);

-- ==== REPLACEABLE ====
CREATE TABLE raw_ball_by_ball (
    match_id VARCHAR, innings VARCHAR, overid VARCHAR, over_ball_num VARCHAR,
    innings_ball_num VARCHAR, batting_team_id VARCHAR, bowling_team_id VARCHAR,
    striker_id VARCHAR, striker_name VARCHAR, non_striker_id VARCHAR, non_striker_name VARCHAR,
    bowler_id VARCHAR, bowler_name VARCHAR, batting_type VARCHAR, bowling_type VARCHAR,
    batting_order VARCHAR, runs VARCHAR, is_four VARCHAR, is_six VARCHAR, is_wicket VARCHAR,
    dismissal_type_id VARCHAR, dismissal_type VARCHAR, dismissed_player_id VARCHAR,
    extras_type VARCHAR, extras1_runs VARCHAR, extras_2_runs VARCHAR, pace_or_spin VARCHAR,
    bowl_speed VARCHAR, stroke VARCHAR, delivery_style VARCHAR, over_or_around VARCHAR,
    on_or_off VARCHAR, delivery_ist_time VARCHAR,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER PRIMARY KEY,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE raw_ball_by_ball_updated (
    match_id VARCHAR, innings VARCHAR, overid VARCHAR, over_ball_num VARCHAR,
    innings_ball_num VARCHAR, batting_team_id VARCHAR, bowling_team_id VARCHAR,
    striker_id VARCHAR, striker_name VARCHAR, non_striker_id VARCHAR, non_striker_name VARCHAR,
    bowler_id VARCHAR, bowler_name VARCHAR, batting_type VARCHAR, bowling_type VARCHAR,
    batting_order VARCHAR, runs VARCHAR, is_four VARCHAR, is_six VARCHAR, is_wicket VARCHAR,
    dismissal_type_id VARCHAR, dismissal_type VARCHAR, dismissed_player_id VARCHAR,
    extras_type VARCHAR, extras1_runs VARCHAR, extras_2_runs VARCHAR, pace_or_spin VARCHAR,
    bowl_speed VARCHAR, stroke VARCHAR, delivery_style VARCHAR, over_or_around VARCHAR,
    on_or_off VARCHAR, delivery_ist_time VARCHAR,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER PRIMARY KEY,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE competitions (
    comp_id INTEGER PRIMARY KEY,
    comp_name VARCHAR NOT NULL,
    match_format VARCHAR NOT NULL CHECK (match_format IN ('T20', 'T20I')),
    season VARCHAR,
    competition_type VARCHAR NOT NULL CHECK (competition_type IN ('IPL', 'T20I', 'OTHER_T20')),
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY,
    team_name VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE competition_teams (
    comp_id INTEGER NOT NULL REFERENCES competitions (comp_id),
    team_id INTEGER NOT NULL REFERENCES teams (team_id),
    team_name VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL,
    PRIMARY KEY (comp_id, team_id)
);

CREATE TABLE venues (
    venue_id INTEGER PRIMARY KEY,
    venue_country VARCHAR,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,
    player_name VARCHAR NOT NULL,
    name_source VARCHAR NOT NULL,
    name_variants VARCHAR,
    in_mapping BOOLEAN NOT NULL,
    in_playing_eleven BOOLEAN NOT NULL,
    in_deliveries BOOLEAN NOT NULL,
    in_matches_captain BOOLEAN NOT NULL,
    shares_name_with_other_id BOOLEAN NOT NULL,
    source_file VARCHAR NOT NULL,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE player_competition_mapping (
    comp_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    player_name VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL,
    PRIMARY KEY (comp_id, team_id, player_id),
    FOREIGN KEY (comp_id, team_id) REFERENCES competition_teams (comp_id, team_id)
);

CREATE TABLE matches (
    match_id INTEGER PRIMARY KEY,
    comp_id INTEGER NOT NULL REFERENCES competitions (comp_id),
    match_number INTEGER,
    match_date DATE NOT NULL,
    stage VARCHAR,
    venue_id INTEGER REFERENCES venues (venue_id),
    venue_country VARCHAR,
    home_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    home_team VARCHAR,
    away_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    away_team VARCHAR,
    home_team_captain_id INTEGER REFERENCES players (player_id),
    away_team_captain_id INTEGER REFERENCES players (player_id),
    toss_win_team_id INTEGER REFERENCES teams (team_id),
    toss_opted VARCHAR,
    man_of_the_match INTEGER,
    first_inn_revised_overs DOUBLE,
    second_inn_revised_overs DOUBLE,
    revised_target INTEGER,
    knock_out BOOLEAN,
    win_team_id INTEGER REFERENCES teams (team_id),
    result VARCHAR,
    result_status VARCHAR NOT NULL,
    competition_type VARCHAR NOT NULL,
    has_deliveries BOOLEAN NOT NULL,
    first_innings_batting_team_id INTEGER,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE match_squads (
    match_id INTEGER NOT NULL REFERENCES matches (match_id),
    team_id INTEGER NOT NULL REFERENCES teams (team_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    squad_row_no INTEGER NOT NULL,
    batting_order INTEGER,
    is_played BOOLEAN,
    is_captain BOOLEAN,
    is_wk BOOLEAN,
    is_impact BOOLEAN,
    is_impact_off BOOLEAN,
    duplicate_key_flag BOOLEAN NOT NULL,
    duplicate_group_size INTEGER NOT NULL,
    mapping_row_exists BOOLEAN NOT NULL,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL,
    PRIMARY KEY (match_id, team_id, player_id, squad_row_no)
);

CREATE TABLE innings (
    match_id INTEGER NOT NULL REFERENCES matches (match_id),
    innings_number INTEGER NOT NULL CHECK (innings_number BETWEEN 1 AND 4),
    batting_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    bowling_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    teams_consistent BOOLEAN NOT NULL,
    delivery_count INTEGER NOT NULL,
    legal_ball_count INTEGER NOT NULL,
    batter_runs_total INTEGER,
    extras_primary_total INTEGER,
    extras_secondary_total INTEGER,
    source_total_runs INTEGER,
    wicket_rows INTEGER NOT NULL,
    max_overid INTEGER,
    innings_role_status VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    first_source_row_no INTEGER,
    last_source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL,
    PRIMARY KEY (match_id, innings_number)
);

CREATE TABLE deliveries (
    match_id INTEGER NOT NULL,
    innings_number INTEGER NOT NULL,
    innings_ball_num INTEGER NOT NULL,
    overid INTEGER,
    over_ball_num INTEGER,
    batting_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    bowling_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    striker_id INTEGER REFERENCES players (player_id),
    non_striker_id INTEGER REFERENCES players (player_id),
    bowler_id INTEGER REFERENCES players (player_id),
    batting_order INTEGER,
    batting_type VARCHAR,
    bowling_type VARCHAR,
    pace_or_spin VARCHAR,
    bowl_speed DOUBLE,
    stroke VARCHAR,
    delivery_style VARCHAR,
    over_or_around VARCHAR,
    on_or_off VARCHAR,
    is_four BOOLEAN,
    is_six BOOLEAN,
    is_wicket BOOLEAN,
    dismissal_type_id INTEGER,
    dismissal_type VARCHAR,
    dismissed_player_id INTEGER REFERENCES players (player_id),
    batter_runs INTEGER,
    extras_type VARCHAR,
    has_extra BOOLEAN,
    extras_primary_runs INTEGER,
    extras_secondary_runs INTEGER,
    extras_split_status VARCHAR NOT NULL,
    is_legal_ball BOOLEAN NOT NULL,
    legal_ball_status VARCHAR NOT NULL,
    extras_label_unverified BOOLEAN NOT NULL,
    dismissal_field_anomaly VARCHAR,
    delivery_time_raw VARCHAR,
    delivery_ts TIMESTAMP,
    delivery_time_is_midnight BOOLEAN,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER NOT NULL,
    ingestion_run_id INTEGER NOT NULL,
    PRIMARY KEY (match_id, innings_number, innings_ball_num),
    FOREIGN KEY (match_id, innings_number) REFERENCES innings (match_id, innings_number)
);

CREATE TABLE match_reconciliation (
    match_id INTEGER PRIMARY KEY REFERENCES matches (match_id),
    comp_id INTEGER,
    match_date DATE,
    home_team_id INTEGER,
    away_team_id INTEGER,
    result VARCHAR,
    result_status VARCHAR,
    win_team_id INTEGER,
    has_deliveries BOOLEAN NOT NULL,
    delivery_count INTEGER NOT NULL,
    innings_count INTEGER NOT NULL,
    squad_row_count INTEGER NOT NULL,
    played_row_count INTEGER NOT NULL,
    no_deliveries_explained BOOLEAN NOT NULL,
    reason VARCHAR,
    source_file VARCHAR NOT NULL,
    source_row_no INTEGER,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE ball_by_ball_comparison (
    column_name VARCHAR PRIMARY KEY,
    rows_compared BIGINT NOT NULL,
    rows_different BIGINT NOT NULL,
    rows_only_in_original BIGINT NOT NULL,
    rows_only_in_updated BIGINT NOT NULL,
    details VARCHAR,
    source_file VARCHAR NOT NULL,
    ingestion_run_id INTEGER NOT NULL
);

CREATE TABLE ball_by_ball_comparison_detail (
    match_id VARCHAR NOT NULL,
    innings VARCHAR NOT NULL,
    innings_ball_num VARCHAR NOT NULL,
    column_name VARCHAR NOT NULL,
    original_value VARCHAR,
    updated_value VARCHAR,
    source_file VARCHAR NOT NULL,
    ingestion_run_id INTEGER NOT NULL,
    PRIMARY KEY (match_id, innings, innings_ball_num, column_name)
);
