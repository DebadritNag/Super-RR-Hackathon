-- SupeRR Selector Season 2: proposed schema (DuckDB first, PostgreSQL-compatible where feasible).
-- PHASE 1 DELIVERABLE: a proposal only. Nothing here has been loaded; no ingestion exists yet.
--
-- Decisions that depend on audit findings (see dataset_audit.md / data_quality_report.json):
--   * team_id IS globally unique in the supplied data (38 team_ids <-> 38 team_names across
--     teams.csv and the mapping file, no id with two names). So `teams` is keyed by team_id alone and
--     competition membership lives in `competition_teams(comp_id, team_id)`.
--     If a future data drop breaks this, switch the keys to (comp_id, team_id).
--   * Two ball-by-ball files exist and differ only in extras1_runs (+ a few name spellings).
--     Which one is authoritative is an OPEN DECISION for the user. `deliveries` has a
--     `source_file` column so either choice (or both) can be loaded; the raw_* tables keep both.
--   * extras1_runs means different things in the two files (original: category code, updated:
--     runs). `deliveries.extras_primary_runs` / `extras_secondary_runs` hold the *validated run
--     semantics only* and must be populated from the updated file (or recomputed) at ingestion.
--   * match_id from official CSVs and Cricsheet ids are different namespaces: they are only linked
--     through source_match_mapping (date + teams candidate links, with a status column).
--   * Booleans are text 'true'/'false' in the CSVs and 0/1 for impact flags: cast at ingestion.
--   * Cricsheet-derived rows must never be mixed into official-CSV tables without a source tag.
--
-- Types are limited to INTEGER, BIGINT, VARCHAR, DATE, TIMESTAMP, BOOLEAN, DOUBLE, DECIMAL.

-- ---------------------------------------------------------------------------------------------
-- 0. Sequences
-- ---------------------------------------------------------------------------------------------
CREATE SEQUENCE seq_ingestion_run START 1;
CREATE SEQUENCE seq_ingestion_error START 1;
CREATE SEQUENCE seq_dq_result START 1;
CREATE SEQUENCE seq_snapshot START 1;
CREATE SEQUENCE seq_model_version START 1;

-- ---------------------------------------------------------------------------------------------
-- 1. Raw source tables (verbatim, all-text copies; one row per source row; no coercion)
-- ---------------------------------------------------------------------------------------------
CREATE TABLE raw_ball_by_ball (
    match_id VARCHAR, innings VARCHAR, overid VARCHAR, over_ball_num VARCHAR,
    innings_ball_num VARCHAR, batting_team_id VARCHAR, bowling_team_id VARCHAR,
    striker_id VARCHAR, striker_name VARCHAR, non_striker_id VARCHAR, non_striker_name VARCHAR,
    bowler_id VARCHAR, bowler_name VARCHAR, batting_type VARCHAR, bowling_type VARCHAR,
    batting_order VARCHAR, runs VARCHAR, is_four VARCHAR, is_six VARCHAR, is_wicket VARCHAR,
    dismissal_type_id VARCHAR, dismissal_type VARCHAR, dismissed_player_id VARCHAR,
    extras_type VARCHAR, extras1_runs VARCHAR, extras_2_runs VARCHAR, pace_or_spin VARCHAR,
    bowl_speed VARCHAR, stroke VARCHAR, delivery_style VARCHAR, over_or_around VARCHAR,
    on_or_off VARCHAR, delivery_ist_time VARCHAR
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
    on_or_off VARCHAR, delivery_ist_time VARCHAR
);
CREATE TABLE raw_matches_2026 (
    match_id VARCHAR, date VARCHAR, venue VARCHAR, team1 VARCHAR, team2 VARCHAR, stage VARCHAR,
    toss_winner VARCHAR, toss_decision VARCHAR, first_ings_score VARCHAR, first_ings_wkts VARCHAR,
    second_ings_score VARCHAR, second_ings_wkts VARCHAR, match_result VARCHAR, match_winner VARCHAR,
    wb_runs VARCHAR, wb_wickets VARCHAR, balls_left VARCHAR, player_of_the_match VARCHAR,
    top_scorer VARCHAR, highscore VARCHAR, best_bowling VARCHAR, best_bowling_figure VARCHAR,
    super_over_match VARCHAR
);
CREATE TABLE raw_batting_stats_2026 (
    position VARCHAR, batsman VARCHAR, team VARCHAR, matches VARCHAR, innings VARCHAR, runs VARCHAR,
    impact VARCHAR, average VARCHAR, strike_rate VARCHAR, not_outs VARCHAR, high_score VARCHAR,
    balls_faced VARCHAR, hundreds VARCHAR, fifties VARCHAR, ducks VARCHAR, fours VARCHAR,
    sixes VARCHAR
);
CREATE TABLE raw_bowling_stats_2026 (
    position VARCHAR, bowler VARCHAR, team VARCHAR, matches VARCHAR, innings VARCHAR,
    wickets VARCHAR, economy VARCHAR, impact VARCHAR, bbi VARCHAR, overs VARCHAR, balls VARCHAR,
    dot_balls VARCHAR, maiden_overs VARCHAR, runs VARCHAR, avg VARCHAR, "4wh" VARCHAR, "5wh" VARCHAR
);
CREATE TABLE raw_fielding_stats_2026 (
    rank VARCHAR, player VARCHAR, team VARCHAR, matches VARCHAR, catches VARCHAR, cpm VARCHAR
);
CREATE TABLE raw_cricsheet_matches (
    cricsheet_id VARCHAR NOT NULL,
    directory VARCHAR NOT NULL,
    match_date DATE,
    team_a VARCHAR, team_b VARCHAR, teams_key VARCHAR,
    event_name VARCHAR, match_type VARCHAR, gender VARCHAR, team_type VARCHAR,
    season VARCHAR, venue VARCHAR, city VARCHAR, data_version VARCHAR,
    outcome_keys VARCHAR, winner VARCHAR, result VARCHAR, dls_method VARCHAR,
    innings_summary VARCHAR,           -- JSON text of per-innings totals (as built by the audit)
    PRIMARY KEY (cricsheet_id, directory)  -- the same id legitimately appears in several directories
);

-- ---------------------------------------------------------------------------------------------
-- 2. Reference data (official CSVs)
-- ---------------------------------------------------------------------------------------------
CREATE TABLE competitions (
    comp_id INTEGER PRIMARY KEY,
    comp_name VARCHAR NOT NULL,
    match_format VARCHAR NOT NULL CHECK (match_format IN ('T20', 'T20I')),
    season VARCHAR NOT NULL,           -- text: values like '2024/25' exist
    is_ipl BOOLEAN NOT NULL DEFAULT FALSE  -- derived: comp_name starts with 'IPL'
);
CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY,       -- globally unique per audit (see header)
    team_name VARCHAR NOT NULL
);
CREATE TABLE competition_teams (
    comp_id INTEGER NOT NULL REFERENCES competitions (comp_id),
    team_id INTEGER NOT NULL REFERENCES teams (team_id),
    PRIMARY KEY (comp_id, team_id)
);
CREATE TABLE venues (
    venue_id INTEGER PRIMARY KEY,
    venue_country VARCHAR
);
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,     -- sole player identity; never merged by name
    canonical_name VARCHAR NOT NULL,
    name_variants VARCHAR              -- JSON text list of other spellings seen
);
CREATE TABLE player_competition_mapping (
    comp_id INTEGER NOT NULL REFERENCES competitions (comp_id),
    team_id INTEGER NOT NULL REFERENCES teams (team_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    player_name VARCHAR NOT NULL,
    PRIMARY KEY (comp_id, team_id, player_id)
);

-- ---------------------------------------------------------------------------------------------
-- 3. Matches, squads, innings, deliveries
-- ---------------------------------------------------------------------------------------------
CREATE TABLE matches (
    match_id INTEGER PRIMARY KEY,
    comp_id INTEGER NOT NULL REFERENCES competitions (comp_id),
    match_number INTEGER,
    match_date DATE NOT NULL,
    stage VARCHAR,
    venue_id INTEGER REFERENCES venues (venue_id),
    home_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    away_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    home_team_captain_id INTEGER REFERENCES players (player_id),
    away_team_captain_id INTEGER REFERENCES players (player_id),
    toss_win_team_id INTEGER REFERENCES teams (team_id),
    toss_opted VARCHAR,
    man_of_the_match VARCHAR,          -- audit: value '0' occurs; keep as text until inspected
    first_inn_revised_overs DOUBLE,
    second_inn_revised_overs DOUBLE,
    revised_target INTEGER,
    knock_out BOOLEAN,
    win_team_id INTEGER REFERENCES teams (team_id),
    result_text VARCHAR,
    result_class VARCHAR,              -- COMPLETED/ABANDONED/NO_RESULT/TIED/TIED_DECIDED_BY_TIEBREAK/UNKNOWN
    has_ball_by_ball BOOLEAN NOT NULL DEFAULT FALSE,
    first_batting_team_id INTEGER REFERENCES teams (team_id)  -- from deliveries, NOT home/away
);
CREATE TABLE match_squads (
    match_id INTEGER NOT NULL REFERENCES matches (match_id),
    team_id INTEGER NOT NULL REFERENCES teams (team_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    squad_row_no INTEGER NOT NULL,     -- audit: (match_id, team_id, player_id) repeats in some
                                       -- matches (see data_quality_report.json), so a row number
                                       -- is part of the key until the cause is confirmed
    batting_order INTEGER,
    is_played BOOLEAN NOT NULL,
    is_captain BOOLEAN,
    is_wk BOOLEAN,
    is_impact BOOLEAN,
    is_impact_off BOOLEAN,
    PRIMARY KEY (match_id, team_id, player_id, squad_row_no)
);
CREATE TABLE innings (
    match_id INTEGER NOT NULL REFERENCES matches (match_id),
    innings_no INTEGER NOT NULL CHECK (innings_no BETWEEN 1 AND 4),  -- 3,4 = super over rows
    batting_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    bowling_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    is_super_over BOOLEAN NOT NULL DEFAULT FALSE,
    total_runs INTEGER,                -- batter + extras (validated formula)
    wickets INTEGER,
    legal_balls INTEGER,
    PRIMARY KEY (match_id, innings_no)
);
CREATE TABLE deliveries (
    match_id INTEGER NOT NULL,
    innings_no INTEGER NOT NULL,
    innings_ball_num INTEGER NOT NULL, -- audit: strictly 1..n within an innings
    source_file VARCHAR NOT NULL,      -- 'ball_by_ball.csv' | 'updated_ball_by_ball.csv'
    overid INTEGER NOT NULL,
    over_ball_num INTEGER NOT NULL,
    striker_id INTEGER NOT NULL REFERENCES players (player_id),
    non_striker_id INTEGER NOT NULL REFERENCES players (player_id),
    bowler_id INTEGER NOT NULL REFERENCES players (player_id),
    batting_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    bowling_team_id INTEGER NOT NULL REFERENCES teams (team_id),
    batter_runs INTEGER NOT NULL,      -- source column `runs` (off the bat only; verified)
    extras_type VARCHAR,               -- source literal 'None' stored as NULL
    extras_primary_runs INTEGER,       -- updated file extras1_runs
    extras_secondary_runs INTEGER,     -- extras_2_runs
    is_legal_ball BOOLEAN NOT NULL,    -- extras_type NOT IN ('wide','Overstep','other')
    is_four BOOLEAN, is_six BOOLEAN,
    is_wicket BOOLEAN NOT NULL,
    dismissal_type_id INTEGER, dismissal_type VARCHAR,
    dismissed_player_id INTEGER REFERENCES players (player_id),
    batting_type VARCHAR, bowling_type VARCHAR, pace_or_spin VARCHAR, bowl_speed DOUBLE,
    stroke VARCHAR, delivery_style VARCHAR, over_or_around VARCHAR, on_or_off VARCHAR,
    delivery_ts TIMESTAMP,             -- many early rows are date-only (00:00:00)
    PRIMARY KEY (match_id, innings_no, innings_ball_num, source_file),
    FOREIGN KEY (match_id, innings_no) REFERENCES innings (match_id, innings_no)
);
CREATE INDEX idx_deliveries_striker ON deliveries (striker_id);
CREATE INDEX idx_deliveries_bowler ON deliveries (bowler_id);

-- ---------------------------------------------------------------------------------------------
-- 4. Source linkage (official <-> Cricsheet; candidate links only, never silently trusted)
-- ---------------------------------------------------------------------------------------------
CREATE TABLE source_match_mapping (
    match_id INTEGER NOT NULL REFERENCES matches (match_id),
    cricsheet_id VARCHAR,
    link_method VARCHAR NOT NULL,      -- e.g. 'date+teams'
    link_status VARCHAR NOT NULL,      -- LINKED | AMBIGUOUS | NO_CRICSHEET_MATCH
    validated_total_runs_match BOOLEAN,
    PRIMARY KEY (match_id, link_method)
);
CREATE TABLE source_player_mapping (
    source VARCHAR NOT NULL,           -- 'ipl_squad' | 'cricsheet_registry' | 'stats_2026'
    source_player_name VARCHAR NOT NULL,
    source_team VARCHAR NOT NULL,
    player_id INTEGER REFERENCES players (player_id),
    match_method VARCHAR NOT NULL,     -- exact | normalised | candidate | manual
    candidate_count INTEGER NOT NULL,
    status VARCHAR NOT NULL,           -- CONFIRMED | CANDIDATE | UNMATCHED | AMBIGUOUS
    PRIMARY KEY (source, source_player_name, source_team)
);

-- ---------------------------------------------------------------------------------------------
-- 5. Franchise / availability (from ipl squad.csv and later sources)
-- ---------------------------------------------------------------------------------------------
CREATE TABLE squad_snapshots (
    snapshot_id INTEGER PRIMARY KEY DEFAULT nextval('seq_snapshot'),
    snapshot_name VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    taken_at TIMESTAMP,
    notes VARCHAR
);
CREATE TABLE franchise_squads (
    snapshot_id INTEGER NOT NULL REFERENCES squad_snapshots (snapshot_id),
    team_no INTEGER NOT NULL,
    team_name VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    player_id INTEGER REFERENCES players (player_id),  -- NULL until matched
    nationality VARCHAR, role VARCHAR, designation VARCHAR,
    PRIMARY KEY (snapshot_id, team_name, player_name)
);
CREATE TABLE player_availability (
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    snapshot_id INTEGER NOT NULL REFERENCES squad_snapshots (snapshot_id),
    availability_status VARCHAR NOT NULL,   -- only values supplied by a real source
    source VARCHAR NOT NULL,
    note VARCHAR,
    PRIMARY KEY (player_id, snapshot_id)
);

-- ---------------------------------------------------------------------------------------------
-- 6. Method / run bookkeeping
-- ---------------------------------------------------------------------------------------------
CREATE TABLE ingestion_runs (
    run_id INTEGER PRIMARY KEY DEFAULT nextval('seq_ingestion_run'),
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status VARCHAR NOT NULL,
    git_commit VARCHAR,
    source_hashes VARCHAR,             -- JSON text: file -> sha256
    notes VARCHAR
);
CREATE TABLE ingestion_errors (
    error_id INTEGER PRIMARY KEY DEFAULT nextval('seq_ingestion_error'),
    run_id INTEGER NOT NULL REFERENCES ingestion_runs (run_id),
    source_file VARCHAR, row_ref VARCHAR, error_type VARCHAR, message VARCHAR
);
CREATE TABLE data_quality_results (
    result_id INTEGER PRIMARY KEY DEFAULT nextval('seq_dq_result'),
    run_id INTEGER REFERENCES ingestion_runs (run_id),
    check_name VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    passed BOOLEAN NOT NULL,
    observed VARCHAR, expected VARCHAR, severity VARCHAR
);
CREATE TABLE model_versions (
    model_version_id INTEGER PRIMARY KEY DEFAULT nextval('seq_model_version'),
    name VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    config_json VARCHAR NOT NULL,      -- exact parameters (weights, thresholds, priors)
    code_commit VARCHAR,
    notes VARCHAR,
    UNIQUE (name)
);
CREATE TABLE metric_definitions (
    metric_name VARCHAR NOT NULL,
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    role VARCHAR NOT NULL,             -- batting | bowling
    formula_text VARCHAR NOT NULL,
    unit VARCHAR,
    min_sample_rule VARCHAR,
    PRIMARY KEY (metric_name, model_version_id)
);

-- ---------------------------------------------------------------------------------------------
-- 7. Derived analytics (empty in Phase 1; all rows must carry a model_version_id)
-- ---------------------------------------------------------------------------------------------
CREATE TABLE player_batting_stats (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    scope VARCHAR NOT NULL,            -- 'IPL' | 'T20I' | 'ALL'
    innings INTEGER, balls_faced INTEGER, runs INTEGER, dismissals INTEGER,
    strike_rate DOUBLE, average DOUBLE, boundary_pct DOUBLE, dot_ball_pct DOUBLE,
    PRIMARY KEY (model_version_id, player_id, scope)
);
CREATE TABLE player_bowling_stats (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    scope VARCHAR NOT NULL,
    innings INTEGER, legal_balls INTEGER, runs_conceded INTEGER, wickets INTEGER,
    economy DOUBLE, average DOUBLE, strike_rate DOUBLE, dot_ball_pct DOUBLE,
    PRIMARY KEY (model_version_id, player_id, scope)
);
CREATE TABLE player_season_stats (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    comp_id INTEGER NOT NULL REFERENCES competitions (comp_id),
    role VARCHAR NOT NULL,
    matches INTEGER, balls INTEGER, runs INTEGER, wickets INTEGER,
    PRIMARY KEY (model_version_id, player_id, comp_id, role)
);
CREATE TABLE player_phase_stats (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    role VARCHAR NOT NULL,
    phase VARCHAR NOT NULL,            -- e.g. powerplay | middle | death
    balls INTEGER, runs INTEGER, wickets INTEGER, strike_rate DOUBLE, economy DOUBLE,
    PRIMARY KEY (model_version_id, player_id, role, phase)
);
CREATE TABLE player_pressure_stats (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    role VARCHAR NOT NULL,
    pressure_balls INTEGER, baseline_balls INTEGER,
    pressure_metric DOUBLE, baseline_metric DOUBLE,
    shrunk_delta DOUBLE, ci_low DOUBLE, ci_high DOUBLE,
    PRIMARY KEY (model_version_id, player_id, role)
);
CREATE TABLE match_pressure_summary (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    match_id INTEGER NOT NULL REFERENCES matches (match_id),
    innings_no INTEGER NOT NULL,
    pressure_balls INTEGER, mean_pressure_index DOUBLE, max_pressure_index DOUBLE,
    PRIMARY KEY (model_version_id, match_id, innings_no)
);
CREATE TABLE player_consistency_stats (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    role VARCHAR NOT NULL,
    matches_with_pressure INTEGER, share_matches_above_baseline DOUBLE, bootstrap_rank_stability DOUBLE,
    PRIMARY KEY (model_version_id, player_id, role)
);
CREATE TABLE team_season_stats (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    team_id INTEGER NOT NULL REFERENCES teams (team_id),
    comp_id INTEGER NOT NULL REFERENCES competitions (comp_id),
    matches INTEGER, wins INTEGER, runs_for INTEGER, runs_against INTEGER,
    PRIMARY KEY (model_version_id, team_id, comp_id)
);
CREATE TABLE rr_team_analysis (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    team_id INTEGER NOT NULL REFERENCES teams (team_id),
    comp_id INTEGER NOT NULL REFERENCES competitions (comp_id),
    section VARCHAR NOT NULL, finding VARCHAR NOT NULL, evidence_json VARCHAR,
    PRIMARY KEY (model_version_id, team_id, comp_id, section, finding)
);
CREATE TABLE squad_gap_analysis (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    snapshot_id INTEGER NOT NULL REFERENCES squad_snapshots (snapshot_id),
    team_name VARCHAR NOT NULL,
    gap_area VARCHAR NOT NULL, gap_description VARCHAR, evidence_json VARCHAR,
    PRIMARY KEY (model_version_id, snapshot_id, team_name, gap_area)
);
CREATE TABLE player_valuation (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    valuation_score DOUBLE, components_json VARCHAR,
    PRIMARY KEY (model_version_id, player_id)
);
CREATE TABLE player_rankings (
    model_version_id INTEGER NOT NULL REFERENCES model_versions (model_version_id),
    role VARCHAR NOT NULL CHECK (role IN ('batting', 'bowling')),
    rank_no INTEGER NOT NULL CHECK (rank_no >= 1),
    player_id INTEGER NOT NULL REFERENCES players (player_id),
    score DOUBLE NOT NULL,
    ci_low DOUBLE, ci_high DOUBLE,
    eligible BOOLEAN NOT NULL,
    evidence_json VARCHAR NOT NULL,    -- traceable inputs; a ranking without evidence is invalid
    PRIMARY KEY (model_version_id, role, rank_no),
    UNIQUE (model_version_id, role, player_id)
);
