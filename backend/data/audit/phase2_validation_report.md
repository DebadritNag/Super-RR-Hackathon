# Phase 2 validation report

Run 1 (RUNNING, LOAD); schema `None`, data `None`.

Summary: INFO=5, OPEN=17, PASS=115

## Table row counts

| table | rows |
|---|---|
| competitions | 141 |
| teams | 38 |
| competition_teams | 353 |
| venues | 98 |
| players | 1217 |
| player_competition_mapping | 6413 |
| matches | 883 |
| match_squads | 28381 |
| innings | 1724 |
| deliveries | 200999 |
| match_reconciliation | 883 |
| raw_ball_by_ball | 200999 |
| raw_ball_by_ball_updated | 200999 |
| ball_by_ball_comparison | 33 |
| ball_by_ball_comparison_detail | 57 |

## Source lineage

| file | role | status | rows | sha256 |
|---|---|---|---|---|
| competitions.csv | PRIMARY | LOADED | 141 | 507ceb7189f972d4 |
| teams.csv | PRIMARY | LOADED | 353 | a65e5922a9b3bf49 |
| matches.csv | PRIMARY | LOADED | 883 | bb100ab84b8b9a15 |
| playing_eleven.csv | PRIMARY | LOADED | 28381 | 7517c73722a28d5d |
| competition_team_player_mapping.csv | PRIMARY | LOADED | 6413 | 1ded4e42a9336185 |
| updated_ball_by_ball.csv | PRIMARY | LOADED | 200999 | 01e2b4379edfbab6 |
| ball_by_ball.csv | COMPARISON_RAW | LOADED | 200999 | a3926f49d2c684dc |
| matches 2026.csv | SKIPPED_BY_DECISION | SKIPPED_BY_DECISION | 39 | c5b7854c1996c70c |
| batting_stats2026.csv | SKIPPED_BY_DECISION | SKIPPED_BY_DECISION | 15 | 20a987b705837c87 |
| bowling_stats2026.csv | SKIPPED_BY_DECISION | SKIPPED_BY_DECISION | 15 | 0d6548125f5c22af |
| fielding_stats2026.csv | SKIPPED_BY_DECISION | SKIPPED_BY_DECISION | 15 | 6673067eec412d39 |
| ipl squad.csv | PENDING_PHASE | PENDING_PHASE | 257 | e0b8a7c294421127 |

## FAIL (0)

| check | expected | observed | affected |
|---|---|---|---|

## OPEN (17)

| check | expected | observed | affected |
|---|---|---|---|
| open_playing_eleven_repeated_keys | 0 (issue preserved, not fixed) | 75 rows in 35 (match,team,player) groups across 3 matches; all kept | 75 |
| open_matches_without_playing_eleven_rows | 0 (issue preserved, not fixed) | 3 | 3 |
| open_playing_eleven_rows_without_mapping_row | 0 (issue preserved, not fixed) | 5 | 5 |
| open_delivery_striker_not_in_match_squad | 0 (issue preserved, not fixed) | 83 delivery rows, 6 distinct (match, striker) pairs | 83 |
| open_delivery_bowler_not_in_match_squad | 0 (issue preserved, not fixed) | 30 delivery rows, 3 distinct (match, bowler) pairs | 30 |
| open_dismissed_player_without_wicket_flag | 0 (issue preserved, not fixed) | 12 | 12 |
| open_wicket_without_dismissed_player | 0 (issue preserved, not fixed) | 1 | 1 |
| open_extras_type_other_label_unverified | 0 (issue preserved, not fixed) | 264 rows; extras_type kept verbatim | 264 |
| open_extras_type_Penalty_label_unverified | 0 (issue preserved, not fixed) | 1 rows; extras_type kept verbatim | 1 |
| open_extras_secondary_split_unverified | 0 (issue preserved, not fixed) | 36 rows with extras_2_runs > 0; split between extras1/extras_2 unverified | 36 |
| open_innings_3_4_role_unverified | 0 (issue preserved, not fixed) | 12 innings in 6 matches (38 delivery rows); not classified as Super Overs | 12 |
| open_man_of_the_match_zero_sentinel | 0 (issue preserved, not fixed) | 119 matches with man_of_the_match = 0 (not a player id; no FK) | 119 |
| open_delivery_time_utc_suffix_vs_ist_column_name | 0 (issue preserved, not fixed) | 200999 rows carry a 'UTC' suffix in column delivery_ist_time; no timezone conversion applied | 200999 |
| open_delivery_time_midnight_rows | 0 (issue preserved, not fixed) | 42 rows with a 00:00:00 time part (likely date-only) | 42 |
| open_duplicate_player_names_with_different_ids | 0 (issue preserved, not fixed) | 7 names map to more than one player_id; not merged | 7 |
| open_cricsheet_innings_total_disagreements | carried from Phase 1, not recomputed (Cricsheet is not loaded in Phase 2) | 10 innings (matches 14130, 14164, 32618, 37349, 37352, 50504) disagree with Cricsheet totals | None |
| open_matches_not_linkable_to_cricsheet | carried from Phase 1, not recomputed (Cricsheet is not loaded in Phase 2) | 108 matches with deliveries could not be linked to Cricsheet (79 T20I, 29 T20) | None |

## PASS (115)

| check | expected | observed | affected |
|---|---|---|---|
| rowcount_competitions_vs_competitions.csv | 141 | 141 | None |
| rowcount_competition_teams_vs_teams.csv | 353 | 353 | None |
| rowcount_matches_vs_matches.csv | 883 | 883 | None |
| rowcount_match_reconciliation_vs_matches.csv | 883 | 883 | None |
| rowcount_match_squads_vs_playing_eleven.csv | 28381 | 28381 | None |
| rowcount_player_competition_mapping_vs_competition_team_player_mapping.csv | 6413 | 6413 | None |
| rowcount_raw_ball_by_ball_updated_vs_updated_ball_by_ball.csv | 200999 | 200999 | None |
| rowcount_deliveries_vs_updated_ball_by_ball.csv | 200999 | 200999 | None |
| rowcount_raw_ball_by_ball_vs_ball_by_ball.csv | 200999 | 200999 | None |
| rowcount_teams_vs_distinct_team_ids_in_teams.csv | 38 | 38 | None |
| spec_rowcount_competition_teams | 353 | 353 | None |
| spec_rowcount_competitions | 141 | 141 | None |
| spec_rowcount_deliveries | 200999 | 200999 | None |
| spec_rowcount_match_reconciliation | 883 | 883 | None |
| spec_rowcount_match_squads | 28381 | 28381 | None |
| spec_rowcount_matches | 883 | 883 | None |
| spec_rowcount_player_competition_mapping | 6413 | 6413 | None |
| spec_rowcount_raw_ball_by_ball | 200999 | 200999 | None |
| spec_rowcount_raw_ball_by_ball_updated | 200999 | 200999 | None |
| spec_rowcount_teams | 38 | 38 | None |
| pk_unique_competitions | 0 | 0 | None |
| pk_unique_teams | 0 | 0 | None |
| pk_unique_competition_teams | 0 | 0 | None |
| pk_unique_venues | 0 | 0 | None |
| pk_unique_players | 0 | 0 | None |
| pk_unique_player_competition_mapping | 0 | 0 | None |
| pk_unique_matches | 0 | 0 | None |
| pk_unique_match_squads | 0 | 0 | None |
| pk_unique_innings | 0 | 0 | None |
| pk_unique_deliveries | 0 | 0 | None |
| pk_unique_match_reconciliation | 0 | 0 | None |
| pk_unique_raw_ball_by_ball | 0 | 0 | None |
| pk_unique_raw_ball_by_ball_updated | 0 | 0 | None |
| fk_orphans_competition_teams.comp_id->competitions | 0 | 0 | None |
| fk_orphans_competition_teams.team_id->teams | 0 | 0 | None |
| fk_orphans_player_competition_mapping.comp_id+team_id->competition_teams | 0 | 0 | None |
| fk_orphans_player_competition_mapping.player_id->players | 0 | 0 | None |
| fk_orphans_matches.comp_id->competitions | 0 | 0 | None |
| fk_orphans_matches.venue_id->venues | 0 | 0 | None |
| fk_orphans_matches.home_team_id->teams | 0 | 0 | None |
| fk_orphans_matches.away_team_id->teams | 0 | 0 | None |
| fk_orphans_matches.toss_win_team_id->teams | 0 | 0 | None |
| fk_orphans_matches.win_team_id->teams | 0 | 0 | None |
| fk_orphans_matches.home_team_captain_id->players | 0 | 0 | None |
| fk_orphans_matches.away_team_captain_id->players | 0 | 0 | None |
| fk_orphans_match_squads.match_id->matches | 0 | 0 | None |
| fk_orphans_match_squads.team_id->teams | 0 | 0 | None |
| fk_orphans_match_squads.player_id->players | 0 | 0 | None |
| fk_orphans_innings.match_id->matches | 0 | 0 | None |
| fk_orphans_innings.batting_team_id->teams | 0 | 0 | None |
| fk_orphans_innings.bowling_team_id->teams | 0 | 0 | None |
| fk_orphans_deliveries.match_id+innings_number->innings | 0 | 0 | None |
| fk_orphans_deliveries.batting_team_id->teams | 0 | 0 | None |
| fk_orphans_deliveries.bowling_team_id->teams | 0 | 0 | None |
| fk_orphans_deliveries.striker_id->players | 0 | 0 | None |
| fk_orphans_deliveries.non_striker_id->players | 0 | 0 | None |
| fk_orphans_deliveries.bowler_id->players | 0 | 0 | None |
| fk_orphans_deliveries.dismissed_player_id->players | 0 | 0 | None |
| fk_orphans_match_reconciliation.match_id->matches | 0 | 0 | None |
| provenance_run_id_competitions | 0 | 0 | None |
| provenance_source_file_competitions | 0 | 0 | None |
| provenance_run_id_teams | 0 | 0 | None |
| provenance_source_file_teams | 0 | 0 | None |
| provenance_run_id_competition_teams | 0 | 0 | None |
| provenance_source_file_competition_teams | 0 | 0 | None |
| provenance_run_id_venues | 0 | 0 | None |
| provenance_source_file_venues | 0 | 0 | None |
| provenance_run_id_players | 0 | 0 | None |
| provenance_run_id_player_competition_mapping | 0 | 0 | None |
| provenance_source_file_player_competition_mapping | 0 | 0 | None |
| provenance_run_id_matches | 0 | 0 | None |
| provenance_source_file_matches | 0 | 0 | None |
| provenance_run_id_match_squads | 0 | 0 | None |
| provenance_source_file_match_squads | 0 | 0 | None |
| provenance_run_id_innings | 0 | 0 | None |
| provenance_source_file_innings | 0 | 0 | None |
| provenance_run_id_deliveries | 0 | 0 | None |
| provenance_source_file_deliveries | 0 | 0 | None |
| provenance_run_id_match_reconciliation | 0 | 0 | None |
| provenance_source_file_match_reconciliation | 0 | 0 | None |
| provenance_run_id_raw_ball_by_ball | 0 | 0 | None |
| provenance_source_file_raw_ball_by_ball | 0 | 0 | None |
| provenance_run_id_raw_ball_by_ball_updated | 0 | 0 | None |
| provenance_source_file_raw_ball_by_ball_updated | 0 | 0 | None |
| provenance_source_row_no_competition_teams | 0 | 0 | None |
| provenance_source_row_no_matches | 0 | 0 | None |
| provenance_source_row_no_match_squads | 0 | 0 | None |
| provenance_source_row_no_deliveries | 0 | 0 | None |
| reconcile_matches_equal_with_plus_without | 883 | 883 | None |
| reconcile_no_delivery_matches_explained | all explained (ABANDONED/NO_RESULT, no winner) | 16 explained, 0 unexplained | 0 |
| reconcile_has_deliveries_flag_consistent | 0 | 0 | None |
| result_status_unknown | 0 | 0 | 0 |
| innings_teams_are_match_home_away_pair | 0 | 0 | None |
| innings_single_batting_and_bowling_team | 0 | 0 | None |
| innings_1_exists_for_every_match_with_deliveries | 0 | 0 | None |
| innings_ball_num_is_1_to_n | 0 | 0 | None |
| innings_legal_balls_and_total_recomputed_from_raw | 0 | 0 | None |
| innings_numbers_within_1_to_4 | 0 | 0 | None |
| comparison_row_counts_equal | 200999 | 200999 | None |
| comparison_key_sets_equal | 0 | 0 | None |
| source_unchanged_ball_by_ball.csv | a3926f49d2c684dca2a5d2de535a02c5ee46ea654ca1e79dd31c69e7544e9889 | a3926f49d2c684dca2a5d2de535a02c5ee46ea654ca1e79dd31c69e7544e9889 | None |
| source_unchanged_batting_stats2026.csv | 20a987b705837c8753cdf02d962ae22f5414feab587d6a19e4a586f88716911d | 20a987b705837c8753cdf02d962ae22f5414feab587d6a19e4a586f88716911d | None |
| source_unchanged_bowling_stats2026.csv | 0d6548125f5c22af79e1ca589468f33819425ad3d08c169b9d4a87960a44c596 | 0d6548125f5c22af79e1ca589468f33819425ad3d08c169b9d4a87960a44c596 | None |
| source_unchanged_competition_team_player_mapping.csv | 1ded4e42a933618572d6e2c3a521c3257eb1844fab4456d567d77cbb2d3bbb12 | 1ded4e42a933618572d6e2c3a521c3257eb1844fab4456d567d77cbb2d3bbb12 | None |
| source_unchanged_competitions.csv | 507ceb7189f972d4e4f299ddcfc97f3c3247af1913f6291106f161fa8353fd9b | 507ceb7189f972d4e4f299ddcfc97f3c3247af1913f6291106f161fa8353fd9b | None |
| source_unchanged_fielding_stats2026.csv | 6673067eec412d391afa709a47b89d1e2c0698eac646de874e465d2381a5366b | 6673067eec412d391afa709a47b89d1e2c0698eac646de874e465d2381a5366b | None |
| source_unchanged_ipl squad.csv | e0b8a7c2944211278f128971f1eafc3d317c9f67d4a097e57df2497b5faf0636 | e0b8a7c2944211278f128971f1eafc3d317c9f67d4a097e57df2497b5faf0636 | None |
| source_unchanged_matches 2026.csv | c5b7854c1996c70c1c9c248ba1dc8478e88ec0f542fd7bb8bcb7fb24e03dedb3 | c5b7854c1996c70c1c9c248ba1dc8478e88ec0f542fd7bb8bcb7fb24e03dedb3 | None |
| source_unchanged_matches.csv | bb100ab84b8b9a15160c1f2315cf675210131a30e779ec5079fd5403dcf56eef | bb100ab84b8b9a15160c1f2315cf675210131a30e779ec5079fd5403dcf56eef | None |
| source_unchanged_playing_eleven.csv | 7517c73722a28d5d61c808ccf0cbed315a8780586d02e946eb9a7f5daf011c27 | 7517c73722a28d5d61c808ccf0cbed315a8780586d02e946eb9a7f5daf011c27 | None |
| source_unchanged_teams.csv | a65e5922a9b3bf49247b24fc9471782e700efb31f8dcc5042923238b87c50a5d | a65e5922a9b3bf49247b24fc9471782e700efb31f8dcc5042923238b87c50a5d | None |
| source_unchanged_updated_ball_by_ball.csv | 01e2b4379edfbab6a6e456d304cb3c70f554cb312ef93d9588f3f32a82cb396e | 01e2b4379edfbab6a6e456d304cb3c70f554cb312ef93d9588f3f32a82cb396e | None |
| weights_sum_to_one | 1.0 | 1.0 | None |
| weighting_config_stored | >= 1 | 1 | None |
| open_players_without_any_name | 0 (issue preserved, not fixed) | 0 | 0 |

## INFO (5)

| check | expected | observed | affected |
|---|---|---|---|
| reconcile_matches_without_deliveries | None | 16 of 883 matches have no deliveries; 867 have | 16 |
| result_status_distribution | None | {"ABANDONED": 19, "COMPLETED": 833, "NO_RESULT": 21, "TIED": 1, "TIED_DECIDED_BY_TIEBREAK": 9} | None |
| competition_type_distribution | None | {"IPL": {"competitions": 5, "matches": 371}, "OTHER_T20": {"competitions": 2, "matches": 30}, "T20I": {"competitions": 134, "matches": 482}} | None |
| ipl_competitions_not_format_T20 | 0 | 0 | 0 |
| comparison_columns_that_differ | None | {"extras1_runs": 199980, "non_striker_name": 33, "striker_name": 24} | 200037 |
