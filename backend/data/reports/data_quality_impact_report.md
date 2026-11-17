# Data-quality impact report

## 1. Interpretation and status

- Read-only assessment of the open Phase 2 data-quality rows and carried-over issues. No record was deleted, no match is excluded globally and nothing was written to a database table.
- proxy_run: yes; pressure_status: PENDING_PHASE3; not_for_publication: yes.
- Register size: 26 issues (17 OPEN rows, 5 INFO rows, 4 carried over). BLOCKING: 0, NON_BLOCKING_WITH_RESTRICTIONS: 16, INFORMATIONAL: 10.

- BLOCKING: Prevents a planned calculation, label or model from being trusted until resolved.
- NON_BLOCKING_WITH_RESTRICTIONS: Work can proceed; named metrics, features or labels carry a documented, scoped restriction.
- INFORMATIONAL: Context only; no metric needs a restriction beyond a note.

## 2. Register

| id | check | class | rows | recomputed | agrees | rule |
|---|---|---|---|---|---|---|
| DQ-001 | open_playing_eleven_repeated_keys | NON_BLOCKING_WITH_RESTRICTIONS | 75 | 75 | yes | RULE_XI_DUPLICATES |
| DQ-002 | open_matches_without_playing_eleven_rows | NON_BLOCKING_WITH_RESTRICTIONS | 3 | 3 | yes | RULE_NO_XI_MATCHES |
| DQ-003 | open_playing_eleven_rows_without_mapping_row | INFORMATIONAL | 5 | 5 | yes | RULE_NO_MAPPING_ROW |
| DQ-004 | open_delivery_striker_not_in_match_squad | NON_BLOCKING_WITH_RESTRICTIONS | 83 | 83 | yes | RULE_STRIKER_NOT_IN_SQUAD |
| DQ-005 | open_delivery_bowler_not_in_match_squad | NON_BLOCKING_WITH_RESTRICTIONS | 30 | 30 | yes | RULE_BOWLER_NOT_IN_SQUAD |
| DQ-006 | open_dismissed_player_without_wicket_flag | NON_BLOCKING_WITH_RESTRICTIONS | 12 | 12 | yes | RULE_DISMISSED_NO_FLAG |
| DQ-007 | open_wicket_without_dismissed_player | NON_BLOCKING_WITH_RESTRICTIONS | 1 | 1 | yes | RULE_WICKET_NO_DISMISSED |
| DQ-008 | open_extras_type_other_label_unverified | NON_BLOCKING_WITH_RESTRICTIONS | 264 | 264 | yes | RULE_EXTRAS_OTHER |
| DQ-009 | open_extras_type_Penalty_label_unverified | NON_BLOCKING_WITH_RESTRICTIONS | 1 | 1 | yes | RULE_EXTRAS_PENALTY |
| DQ-010 | open_extras_secondary_split_unverified | NON_BLOCKING_WITH_RESTRICTIONS | 36 | 36 | yes | RULE_EXTRAS_SECONDARY |
| DQ-011 | open_innings_3_4_role_unverified | NON_BLOCKING_WITH_RESTRICTIONS | 12 | 12 | yes | RULE_INNINGS_3_4 |
| DQ-012 | open_man_of_the_match_zero_sentinel | NON_BLOCKING_WITH_RESTRICTIONS | 119 | 119 | yes | RULE_MOM_SENTINEL |
| DQ-013 | open_delivery_time_utc_suffix_vs_ist_column_name | NON_BLOCKING_WITH_RESTRICTIONS | 200,999 | 200,999 | yes | RULE_UTC_SUFFIX |
| DQ-014 | open_delivery_time_midnight_rows | INFORMATIONAL | 42 | 42 | yes | RULE_MIDNIGHT_TIMES |
| DQ-015 | open_duplicate_player_names_with_different_ids | INFORMATIONAL | 7 | 7 | yes | RULE_DUPLICATE_NAMES |
| DQ-016 | open_cricsheet_innings_total_disagreements | NON_BLOCKING_WITH_RESTRICTIONS | n/a | 10 | n/a | RULE_CRICSHEET_TOTALS |
| DQ-017 | open_matches_not_linkable_to_cricsheet | INFORMATIONAL | n/a | n/a | n/a | RULE_UNLINKABLE_MATCHES |
| DQ-018 | reconcile_matches_without_deliveries | INFORMATIONAL | 16 | 16 | yes | RULE_INFO_NO_DELIVERY_MATCHES |
| DQ-019 | result_status_distribution | INFORMATIONAL | n/a | 883 | n/a | RULE_INFO_RESULT_STATUS |
| DQ-020 | competition_type_distribution | INFORMATIONAL | n/a | 883 | n/a | RULE_INFO_COMP_TYPE |
| DQ-021 | ipl_competitions_not_format_T20 | INFORMATIONAL | 0 | 0 | yes | RULE_INFO_IPL_FORMAT |
| DQ-022 | comparison_columns_that_differ | INFORMATIONAL | 200,037 | 200,037 | yes | RULE_INFO_EXTRAS1_COMPARISON |
| DQ-023 | carried_no_result_or_abandoned_with_deliveries | NON_BLOCKING_WITH_RESTRICTIONS | n/a | 24 | n/a | RULE_NO_RESULT_MATCHES |
| DQ-024 | carried_dls_revised_targets | NON_BLOCKING_WITH_RESTRICTIONS | n/a | 34 | n/a | RULE_DLS_TARGETS |
| DQ-025 | carried_playing_xi_count_not_11 | NON_BLOCKING_WITH_RESTRICTIONS | n/a | 569 | n/a | RULE_XI_COUNT |
| DQ-026 | carried_first_innings_batting_team_not_fk | INFORMATIONAL | n/a | 0 | n/a | RULE_FIRST_INNINGS_TEAM |

## 3. Issue detail

### DQ-001 open_playing_eleven_repeated_keys (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 75; recomputed rows: 75; shares: matches 0.34%, players 2.71%.
- Why this class: 75 repeated squad rows in 3 matches. They are kept, flagged with duplicate_key_flag. Ball-level metrics do not read the squad table.
- Could block: Team-composition or batting-order features for the affected matches.
- Affects: calculations: squad size and composition counts; features: team composition, batting order, squad membership; labels: none; models: models using team-composition features
- Restriction RULE_XI_DUPLICATES: metrics team_composition_features, squad_membership_features, batting_order_features; filter `match_squads.duplicate_key_flag`; effect DO_NOT_INFER_FROM_SQUAD; global exclusion: no.
- Handling: Do not de-duplicate silently. Features from match_squads must carry the flag or skip flagged matches for that feature only.
- Phase: Phase 3 / 4; resolvable with evidence: yes (Provider correction of the duplicated playing-XI rows.)

### DQ-002 open_matches_without_playing_eleven_rows (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 3; recomputed matches: 3; shares: deliveries 0.00%, matches 0.34%.
- Why this class: 3 matches have deliveries but no playing XI rows. Ball-level metrics are unaffected.
- Could block: Team-composition features for the affected matches.
- Affects: calculations: team composition counts; features: team composition, squad membership; labels: none; models: models using squad features
- Restriction RULE_NO_XI_MATCHES: metrics team_composition_features, squad_membership_features; filter `match_id has no match_squads rows`; effect EXCLUDE_ROWS_FROM_METRIC; global exclusion: no.
- Handling: Keep the matches; leave squad features missing (never imputed) for them.
- Phase: Phase 3 / 4; resolvable with evidence: yes (Playing XI rows for the affected matches from the provider.)

### DQ-003 open_playing_eleven_rows_without_mapping_row (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: 5; recomputed rows: 5; shares: matches 0.57%, players 0.08%.
- Why this class: 5 squad rows have no competition-team mapping row. The rows are kept and only affect mapping-based lookups, which no current metric uses.
- Could block: Nothing planned.
- Affects: calculations: none; features: squad membership via the competition mapping; labels: none; models: none
- Restriction RULE_NO_MAPPING_ROW: metrics squad_membership_features; filter `match_squads.mapping_row_exists = false`; effect DOCUMENT_ONLY; global exclusion: no.
- Handling: Keep the rows; use match_squads directly instead of the mapping table.
- Phase: Phase 4; resolvable with evidence: yes (Mapping rows for the affected players.)

### DQ-004 open_delivery_striker_not_in_match_squad (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 83; recomputed rows: 83; shares: deliveries 0.04%, matches 0.34%, players 1.40%.
- Why this class: 83 delivery rows in 3 matches have a striker who is absent from the match squad. The deliveries are real, only the squad list is incomplete.
- Could block: Inferring who played from the squad table.
- Affects: calculations: none; features: squad membership and role inferred from squads; labels: none; models: none
- Restriction RULE_STRIKER_NOT_IN_SQUAD: metrics squad_membership_features; filter `delivery striker has no match_squads row in that match`; effect DO_NOT_INFER_FROM_SQUAD; global exclusion: no.
- Handling: Keep the deliveries in ball-level metrics; never infer participation from the squad table.
- Phase: Phase 3 / 4; resolvable with evidence: yes (Corrected playing-XI rows.)

### DQ-005 open_delivery_bowler_not_in_match_squad (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 30; recomputed rows: 30; shares: deliveries 0.01%, matches 0.34%, players 0.66%.
- Why this class: 30 delivery rows in 3 matches have a bowler absent from the match squad. Same handling as the striker case.
- Could block: Inferring who played from the squad table.
- Affects: calculations: none; features: squad membership and role inferred from squads; labels: none; models: none
- Restriction RULE_BOWLER_NOT_IN_SQUAD: metrics squad_membership_features; filter `delivery bowler has no match_squads row in that match`; effect DO_NOT_INFER_FROM_SQUAD; global exclusion: no.
- Handling: Keep the deliveries in ball-level metrics; never infer participation from the squad table.
- Phase: Phase 3 / 4; resolvable with evidence: yes (Corrected playing-XI rows.)

### DQ-006 open_dismissed_player_without_wicket_flag (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 12; recomputed rows: 12; shares: deliveries 0.01%, matches 1.36%, players 1.97%.
- Why this class: 12 rows name a dismissed player but is_wicket is false. The flag and the player field disagree and the truth is unknown.
- Could block: Exact wicket counts for the affected innings.
- Affects: calculations: wickets taken, dismissals, wickets in hand; features: wickets-in-hand, wicket-event features; labels: wicket event labels; models: models using wicket counts or wicket events
- Restriction RULE_DISMISSED_NO_FLAG: metrics wicket_event_label, batter_dismissal_rate, bowler_wicket_rate; filter `dismissed_player_id IS NOT NULL AND NOT is_wicket`; effect SENSITIVITY_EXCLUDE; global exclusion: no.
- Handling: Proxy metrics count only rows with is_wicket true. Report a sensitivity run that counts these rows; do not edit the flag.
- Phase: Phase 3; resolvable with evidence: yes (Provider correction or a rule that decides the flag from dismissal text.)

### DQ-007 open_wicket_without_dismissed_player (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 1; recomputed rows: 1; shares: deliveries 0.00%, matches 0.11%, players 0.16%.
- Why this class: 1 Retire Out row(s) have is_wicket true and no dismissed player. It cannot be attributed to a batter and Retire Out is not bowler-credited.
- Could block: Dismissal attribution for one row.
- Affects: calculations: batter dismissal counts; features: wicket-event features; labels: wicket event labels; models: none
- Restriction RULE_WICKET_NO_DISMISSED: metrics wicket_event_label, batter_dismissal_rate; filter `is_wicket AND dismissed_player_id IS NULL`; effect EXCLUDE_ROWS_FROM_METRIC; global exclusion: no.
- Handling: Keep the row; exclude it from batter dismissal metrics; not credited to a bowler.
- Phase: Phase 3; resolvable with evidence: yes (Dismissed player id from the provider.)

### DQ-008 open_extras_type_other_label_unverified (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 264; recomputed rows: 264; shares: deliveries 0.13%, matches 24.35%, players 22.84%.
- Why this class: The meaning of extras_type 'other' is not documented. It behaves like a no-ball in the Cricsheet comparison but this is not assumed. Proxy metrics can be run both ways.
- Could block: Any metric that needs a wide/no-ball/bye split for these rows.
- Affects: calculations: balls faced, legal balls bowled, runs charged to the bowler; features: extras-type features, no-ball/wide rates; labels: none; models: models using extras-type features
- Restriction RULE_EXTRAS_OTHER: metrics extras_type_features, bowler_economy, bowler_legal_balls, batter_balls_faced; filter `extras_type = 'other'`; effect REPORT_WITH_SENSITIVITY; global exclusion: no.
- Handling: Keep the rows and the legal_ball_status already stored. Report affected metrics with and without these rows (sensitivity). Do not map 'other' to a named extras type.
- Phase: Phase 3; resolvable with evidence: yes (Source documentation of the 'other' label from the data provider.)

### DQ-009 open_extras_type_Penalty_label_unverified (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 1; recomputed rows: 1; shares: deliveries 0.00%, matches 0.11%, players 0.16%.
- Why this class: 1 row(s); excluded from ball and charged-run counts by rule. Impact is negligible.
- Could block: Nothing at this size.
- Affects: calculations: balls faced, legal balls, bowler runs charged; features: extras-type features; labels: none; models: none
- Restriction RULE_EXTRAS_PENALTY: metrics batter_balls_faced, bowler_legal_balls, bowler_economy, extras_type_features; filter `extras_type = 'Penalty'`; effect EXCLUDE_ROWS_FROM_METRIC; global exclusion: no.
- Handling: Keep the row. Exclude it from the listed metrics; never assume it is a penalty-run type or a delivery.
- Phase: Phase 3; resolvable with evidence: yes (Source documentation of the 'Penalty' label.)

### DQ-010 open_extras_secondary_split_unverified (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 36; recomputed rows: 36; shares: deliveries 0.02%, matches 4.08%, players 5.26%.
- Why this class: 36 rows carry extras_secondary_runs; how these runs split with the primary extras is unverified. Secondary runs are not charged to the bowler in any proxy.
- Could block: Reconstructing innings totals or bowler runs conceded exactly.
- Affects: calculations: bowler runs conceded, innings totals rebuilt from components; features: extras-type features; labels: none; models: none
- Restriction RULE_EXTRAS_SECONDARY: metrics bowler_economy, extras_type_features, innings_total_runs; filter `extras_secondary_runs > 0`; effect DO_NOT_INTERPRET_FIELD; global exclusion: no.
- Handling: Do not interpret extras_secondary_runs; use source_total_runs for innings totals.
- Phase: Phase 3; resolvable with evidence: yes (Provider description of the extras_1/extras_2 split.)

### DQ-011 open_innings_3_4_role_unverified (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 12; recomputed innings: 12; shares: deliveries 0.02%, matches 0.68%, players 2.79%.
- Why this class: Innings 3 and 4 are probably Super Overs but the official file does not say so. Regulation metrics are well defined without them, so nothing blocks.
- Could block: Treating them as Super Overs (or as regulation innings) without evidence.
- Affects: calculations: any regulation-innings aggregate (runs, balls, wickets, required rate); features: phase and over-number features, chase state features; labels: pressure state labels, win/loss and chase outcomes; models: any model trained on regulation-innings pressure
- Restriction RULE_INNINGS_3_4: metrics batter_balls_faced, batter_runs_per_ball, batter_strike_rate, batter_dismissal_rate, bowler_legal_balls, bowler_economy, bowler_wicket_rate, innings_total_runs, chase_target_features, win_probability_features, pressure_state_label, batter_pressure_sample, bowler_pressure_sample; filter `innings_number IN (3, 4)`; effect EXCLUDE_ROWS_FROM_METRIC; global exclusion: no.
- Handling: Keep the rows; exclude innings 3/4 from the listed metrics by rule. Cricsheet evidence (cricsheet_super_over_validation) is context only and does not relabel the data.
- Phase: Phase 3 (metric extraction); resolvable with evidence: yes (Official statement of the innings role, or a human decision accepting the Cricsheet match.)

### DQ-012 open_man_of_the_match_zero_sentinel (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 119; recomputed matches: 119; shares: deliveries 10.19%, matches 13.48%.
- Why this class: 119 matches use 0 as man_of_the_match, which is not a player id. Phase 3 does not need Man of the Match.
- Could block: Using Man of the Match as a label or target.
- Affects: calculations: none; features: none; labels: player-of-the-match label; models: any model trained on that label
- Restriction RULE_MOM_SENTINEL: metrics player_match_of_match_label; filter `matches.man_of_the_match = 0`; effect DO_NOT_USE_AS_LABEL; global exclusion: no.
- Handling: Do not use man_of_the_match as a label until the sentinel is decoded; do not join it to players.
- Phase: Not planned; resolvable with evidence: yes (Provider documentation of the 0 value.)

### DQ-013 open_delivery_time_utc_suffix_vs_ist_column_name (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: 200,999; recomputed rows: 200,999; shares: deliveries 100.00%, matches 98.19%, players 78.72%.
- Why this class: All delivery timestamps carry a UTC suffix although the column is named IST. The time zone is unverified; ordering within a match uses innings_ball_num instead.
- Could block: Any feature that depends on the clock time of a delivery.
- Affects: calculations: none; features: time-of-day, day/night, elapsed-time features; labels: none; models: none
- Restriction RULE_UTC_SUFFIX: metrics delivery_timestamp_features; filter `delivery_time_raw LIKE '%UTC%' (all deliveries)`; effect DO_NOT_INTERPRET_FIELD; global exclusion: no.
- Handling: Do not convert time zones; do not derive time features. Order deliveries by innings_ball_num.
- Phase: Not planned; resolvable with evidence: yes (Provider statement of the time zone.)

### DQ-014 open_delivery_time_midnight_rows (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: 42; recomputed rows: 42; shares: deliveries 0.02%, matches 0.45%, players 1.40%.
- Why this class: 42 rows have a 00:00:00 time part, probably a date only. No metric uses timestamps.
- Could block: Nothing planned.
- Affects: calculations: none; features: time-of-day features; labels: none; models: none
- Restriction RULE_MIDNIGHT_TIMES: metrics delivery_timestamp_features; filter `delivery_time_is_midnight`; effect DO_NOT_INTERPRET_FIELD; global exclusion: no.
- Handling: Keep the rows; ignore the time part.
- Phase: Not planned; resolvable with evidence: yes (Provider statement on date-only timestamps.)

### DQ-015 open_duplicate_player_names_with_different_ids (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: 7; recomputed player names: 7; shares: deliveries 2.42%, matches 22.65%, players 1.15%.
- Why this class: 7 names map to 14 player ids. Everything joins on player_id, so no metric is affected as long as nobody joins on a name.
- Could block: Name-based joins (reports, Cricsheet linking by name).
- Affects: calculations: none; features: player identity joins; labels: none; models: none
- Restriction RULE_DUPLICATE_NAMES: metrics player_identity_join; filter `players.shares_name_with_other_id`; effect NO_JOIN_ON_NAME; global exclusion: no.
- Handling: Join on player_id only; do not merge or de-duplicate players.
- Phase: All phases; resolvable with evidence: no (Not resolvable from the data; ids are authoritative.)

### DQ-016 open_cricsheet_innings_total_disagreements (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: phase2_data_quality_table; stored rows: n/a; recomputed innings: 10; shares: matches 0.68%.
- Why this class: 10 innings in 6 matches disagree with Cricsheet totals. The official data stays authoritative; the affected innings can perturb run-based metrics a little.
- Could block: Exact innings totals and chase targets for those innings.
- Affects: calculations: innings totals, runs per ball, runs conceded; features: chase target and required-rate features for the same matches; labels: chase outcome labels in those matches; models: models using run-based features from those innings
- Restriction RULE_CRICSHEET_TOTALS: metrics innings_total_runs, batter_runs_per_ball, bowler_economy, chase_target_features; filter `(match_id, innings_number) in the ten innings listed in the register`; effect SENSITIVITY_EXCLUDE; global exclusion: no.
- Handling: Keep the rows (official file is authoritative). Run a sensitivity analysis that drops these innings for the listed metrics only.
- Phase: Phase 3; resolvable with evidence: yes (Provider confirmation of which source total is right.)
- Note: recounted from the Phase 1 audit artifact (Cricsheet is not loaded)

### DQ-017 open_matches_not_linkable_to_cricsheet (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: n/a; recomputed matches: n/a; shares: not applicable.
- Why this class: Some official matches have no Cricsheet counterpart. Cricsheet is validation-only, so rankings never depend on the link.
- Could block: Nothing; it limits validation coverage only.
- Affects: calculations: none; features: none; labels: none; models: none
- Restriction RULE_UNLINKABLE_MATCHES: metrics cricsheet_validation_coverage; filter `matches without a Cricsheet counterpart`; effect DOCUMENT_ONLY; global exclusion: no.
- Handling: Report validation coverage from the mapping counts; do not add Cricsheet-only matches.
- Phase: Not planned; resolvable with evidence: no (Not resolvable; Cricsheet simply lacks these matches.)
- Note: Cricsheet-derived; see super-over validation mapping counts

### DQ-018 reconcile_matches_without_deliveries (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: 16; recomputed matches: 16; shares: deliveries 0.00%, matches 1.81%, players 0.00%.
- Why this class: 16 matches have no deliveries and all are explained (abandoned without a ball).
- Could block: Nothing.
- Affects: calculations: match coverage denominators; features: none; labels: none; models: none
- Restriction RULE_INFO_NO_DELIVERY_MATCHES: metrics match_coverage_denominators; filter `NOT has_deliveries`; effect DOCUMENT_ONLY; global exclusion: no.
- Handling: Use matches with deliveries as the denominator for coverage statements.
- Phase: Phase 3; resolvable with evidence: no (Not applicable.)

### DQ-019 result_status_distribution (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: n/a; recomputed matches: 883; shares: not applicable.
- Why this class: Distribution of result statuses; informational.
- Could block: Nothing.
- Affects: calculations: none; features: none; labels: match outcome labels; models: none
- Restriction RULE_INFO_RESULT_STATUS: metrics match_outcome_label; filter `result_status NOT IN ('COMPLETED')`; effect DOCUMENT_ONLY; global exclusion: no.
- Handling: Outcome labels must handle TIED, TIED_DECIDED_BY_TIEBREAK, NO_RESULT, ABANDONED explicitly.
- Phase: Phase 3; resolvable with evidence: no (Not applicable.)

### DQ-020 competition_type_distribution (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: n/a; recomputed matches: 883; shares: not applicable.
- Why this class: Distribution of IPL, T20I and OTHER_T20 competitions; informational.
- Could block: Nothing.
- Affects: calculations: none; features: format assignment; labels: none; models: none
- Restriction RULE_INFO_COMP_TYPE: metrics format_assignment; filter `competition_type = 'OTHER_T20'`; effect DOCUMENT_ONLY; global exclusion: no.
- Handling: OTHER_T20 matches stay in the database and never enter IPL or T20I scores.
- Phase: Phase 3; resolvable with evidence: no (Not applicable.)

### DQ-021 ipl_competitions_not_format_T20 (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: 0; recomputed competitions: 0; shares: not applicable.
- Why this class: No IPL competition has a non-T20 format; check passes with zero rows.
- Could block: Nothing.
- Affects: calculations: none; features: format assignment; labels: none; models: none
- Restriction RULE_INFO_IPL_FORMAT: metrics format_assignment; filter `IPL competitions whose match_format is not T20`; effect DOCUMENT_ONLY; global exclusion: no.
- Handling: No action.
- Phase: Not planned; resolvable with evidence: no (Not applicable.)

### DQ-022 comparison_columns_that_differ (INFORMATIONAL)

- Source: phase2_data_quality_table; stored rows: 200,037; recomputed cell differences: 200,037; shares: matches 0.34%.
- Why this class: The original and updated ball-by-ball files differ in extras1_runs and two name columns. The updated file is the approved authority; the original is kept for provenance.
- Could block: Nothing; the approved source decision covers it.
- Affects: calculations: none; features: extras-type features; labels: none; models: none
- Restriction RULE_INFO_EXTRAS1_COMPARISON: metrics extras_type_features; filter `ball_by_ball.csv vs updated_ball_by_ball.csv differences`; effect DOCUMENT_ONLY; global exclusion: no.
- Handling: Use updated_ball_by_ball.csv only; keep the comparison tables as provenance.
- Phase: Not planned; resolvable with evidence: no (Not applicable.)

### DQ-023 carried_no_result_or_abandoned_with_deliveries (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: carried_over_phase1; stored rows: n/a; recomputed matches: 24; shares: deliveries 0.87%, matches 2.72%.
- Why this class: NO_RESULT and ABANDONED matches that still have deliveries have no valid outcome, but their balls are real. Only outcome-based labels are affected.
- Could block: Outcome-based labels for these matches.
- Affects: calculations: none; features: win-probability and chase-completion features; labels: match outcome labels; models: models trained on match outcomes
- Restriction RULE_NO_RESULT_MATCHES: metrics match_outcome_label, win_probability_features; filter `result_status IN ('NO_RESULT', 'ABANDONED') AND has_deliveries`; effect EXCLUDE_ROWS_FROM_METRIC; global exclusion: no.
- Handling: Keep the deliveries in ball-level metrics; exclude the matches from outcome labels only.
- Phase: Phase 3; resolvable with evidence: no (Not resolvable; there is no result.)
- Note: Matches with result_status NO_RESULT or ABANDONED that still have delivery rows.

### DQ-024 carried_dls_revised_targets (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: carried_over_phase1; stored rows: n/a; recomputed matches: 34; shares: deliveries 2.21%, matches 3.85%.
- Why this class: 34 matches with revised overs or targets (DLS-style) change the chase target and balls available. Features must use the revised fields.
- Could block: Chase target and required-rate features that use the original 20 overs.
- Affects: calculations: none; features: required run rate, balls remaining, target; labels: chase outcome labels; models: models using chase features
- Restriction RULE_DLS_TARGETS: metrics chase_target_features, win_probability_features; filter `revised_target IS NOT NULL OR revised overs IS NOT NULL`; effect REQUIRE_REVISED_FIELDS; global exclusion: no.
- Handling: Use revised_target and revised overs where present; never assume 20 overs for these matches.
- Phase: Phase 3; resolvable with evidence: yes (None; the revised fields exist in the official matches table.)
- Note: Matches with a revised target or revised overs (rain-affected).

### DQ-025 carried_playing_xi_count_not_11 (NON_BLOCKING_WITH_RESTRICTIONS)

- Source: carried_over_phase1; stored rows: n/a; recomputed match-team pairs: 569; shares: matches 33.86%.
- Why this class: 569 (match, team) pairs have a played-row count different from 11. A count of 12 is explained by impact substitutes in the IPL; other counts are anomalies. Ball-level metrics do not depend on it.
- Could block: Team-composition features.
- Affects: calculations: none; features: team composition counts; labels: none; models: none
- Restriction RULE_XI_COUNT: metrics team_composition_features; filter `(match_id, team_id) with a played-row count different from 11`; effect DO_NOT_INFER_FROM_SQUAD; global exclusion: no.
- Handling: Do not infer the XI from is_played counts; derive participation from deliveries.
- Phase: Phase 3 / 4; resolvable with evidence: yes (Provider-verified playing XI.)
- Note: (match, team) pairs whose played-row count in the squad table is not 11.

### DQ-026 carried_first_innings_batting_team_not_fk (INFORMATIONAL)

- Source: carried_over_phase1; stored rows: n/a; recomputed matches: 0; shares: matches 98.19%.
- Why this class: matches.first_innings_batting_team_id has no foreign key in the schema. The recount finds no orphan and no disagreement with innings 1.
- Could block: Nothing; a missing constraint, not bad data.
- Affects: calculations: none; features: innings order; labels: none; models: none
- Restriction RULE_FIRST_INNINGS_TEAM: metrics innings_order_features; filter `matches.first_innings_batting_team_id`; effect DOCUMENT_ONLY; global exclusion: no.
- Handling: Use innings.batting_team_id for innings order.
- Phase: Not planned; resolvable with evidence: no (Not applicable.)
- Note: matches.first_innings_batting_team_id has no declared foreign key.

## 4. Cricsheet total disagreements: perturbation

| match | innings | type | official delivery rows |
|---|---|---|---|
| 14130 | 1 | IPL | 124 |
| 14130 | 2 | IPL | 127 |
| 14164 | 1 | IPL | 124 |
| 32618 | 1 | T20I | 123 |
| 32618 | 2 | T20I | 132 |
| 37349 | 1 | T20I | 124 |
| 37349 | 2 | T20I | 105 |
| 37352 | 1 | T20I | 123 |
| 50504 | 1 | T20I | 126 |
| 50504 | 2 | T20I | 113 |

- batters: 65 players touched; largest share of one player's innings 1/2 deliveries inside these innings 0.475; median 0.026; 3 players with a share of 25% or more.
- bowlers: 47 players touched; largest share of one player's innings 1/2 deliveries inside these innings 0.147; median 0.040; 0 players with a share of 25% or more.

## 5. Restrictions per metric (for Phase 3)

| metric | rules |
|---|---|
| batter_balls_faced | RULE_INNINGS_3_4, RULE_EXTRAS_OTHER, RULE_EXTRAS_PENALTY |
| batter_runs_per_ball | RULE_INNINGS_3_4, RULE_CRICSHEET_TOTALS |
| batter_strike_rate | RULE_INNINGS_3_4 |
| batter_dismissal_rate | RULE_INNINGS_3_4, RULE_DISMISSED_NO_FLAG, RULE_WICKET_NO_DISMISSED |
| bowler_legal_balls | RULE_INNINGS_3_4, RULE_EXTRAS_OTHER, RULE_EXTRAS_PENALTY |
| bowler_economy | RULE_INNINGS_3_4, RULE_EXTRAS_OTHER, RULE_EXTRAS_PENALTY, RULE_EXTRAS_SECONDARY, RULE_CRICSHEET_TOTALS |
| bowler_wicket_rate | RULE_INNINGS_3_4, RULE_DISMISSED_NO_FLAG |
| innings_total_runs | RULE_INNINGS_3_4, RULE_EXTRAS_SECONDARY, RULE_CRICSHEET_TOTALS |
| chase_target_features | RULE_INNINGS_3_4, RULE_CRICSHEET_TOTALS, RULE_DLS_TARGETS |
| win_probability_features | RULE_INNINGS_3_4, RULE_NO_RESULT_MATCHES, RULE_DLS_TARGETS |
| match_outcome_label | RULE_NO_RESULT_MATCHES, RULE_INFO_RESULT_STATUS |
| pressure_state_label | RULE_INNINGS_3_4 |
| batter_pressure_sample | RULE_INNINGS_3_4 |
| bowler_pressure_sample | RULE_INNINGS_3_4 |
| extras_type_features | RULE_EXTRAS_OTHER, RULE_EXTRAS_PENALTY, RULE_EXTRAS_SECONDARY, RULE_INFO_EXTRAS1_COMPARISON |
| wicket_event_label | RULE_DISMISSED_NO_FLAG, RULE_WICKET_NO_DISMISSED |
| team_composition_features | RULE_XI_DUPLICATES, RULE_NO_XI_MATCHES, RULE_XI_COUNT |
| squad_membership_features | RULE_XI_DUPLICATES, RULE_NO_XI_MATCHES, RULE_NO_MAPPING_ROW, RULE_STRIKER_NOT_IN_SQUAD, RULE_BOWLER_NOT_IN_SQUAD |
| batting_order_features | RULE_XI_DUPLICATES |
| innings_order_features | RULE_FIRST_INNINGS_TEAM |
| player_identity_join | RULE_DUPLICATE_NAMES |
| delivery_timestamp_features | RULE_UTC_SUFFIX, RULE_MIDNIGHT_TIMES |
| player_match_of_match_label | RULE_MOM_SENTINEL |
| match_coverage_denominators | RULE_INFO_NO_DELIVERY_MATCHES |
| format_assignment | RULE_INFO_COMP_TYPE, RULE_INFO_IPL_FORMAT |
| cricsheet_validation_coverage | RULE_UNLINKABLE_MATCHES |

## 6. Preservation

Official CSV hashes, official table hashes and Cricsheet manifests unchanged: yes.
