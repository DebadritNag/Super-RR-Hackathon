# Dataset audit (Phase 1)

Generated: 2026-11-14T18:07:49.054122+00:00

All numbers below are produced by `scripts/audit_datasets.py`.

## CSV files: actual vs spec

| file | rows | spec_rows | delta | cols | spec_cols | dup_rows | dup_pk | streamed_rows |
|---|---|---|---|---|---|---|---|---|
| competitions.csv | 141 | 141 | 0 | 4 | 4 | 0 | 0 | 141 |
| teams.csv | 353 | 353 | 0 | 3 | 3 | 0 | 0 | 353 |
| matches.csv | 883 | 883 | 0 | 22 | 22 | 0 | 0 | 883 |
| playing_eleven.csv | 28381 | 28381 | 0 | 9 | 9 | 0 | 35 | 28381 |
| competition_team_player_mapping.csv | 6413 | 6413 | 0 | 6 | 6 | 0 | 0 | 6413 |
| ball_by_ball.csv | 200999 | 200999 | 0 | 33 | 33 | 0 | 0 | 200999 |
| ipl squad.csv | 257 | None | None | 6 | 6 | 0 | 0 | 257 |
| updated_ball_by_ball.csv | 200999 | None | None | 33 | None | 0 | 0 | 200999 |
| matches 2026.csv | 39 | None | None | 23 | None | 0 | None | 39 |
| batting_stats2026.csv | 15 | None | None | 17 | None | 0 | None | 15 |
| bowling_stats2026.csv | 15 | None | None | 17 | None | 0 | None | 15 |
| fielding_stats2026.csv | 15 | None | None | 6 | None | 0 | None | 15 |

Note: `streamed_rows` = raw newline count minus header; it differs from `rows` only if a file contains embedded newlines in quoted fields.

## Schema differences vs spec

- `competitions.csv`: exact=True, missing=[], unexpected=[], order_differs=False
- `teams.csv`: exact=True, missing=[], unexpected=[], order_differs=False
- `matches.csv`: exact=True, missing=[], unexpected=[], order_differs=False
- `playing_eleven.csv`: exact=True, missing=[], unexpected=[], order_differs=False
- `competition_team_player_mapping.csv`: exact=True, missing=[], unexpected=[], order_differs=False
- `ball_by_ball.csv`: exact=False, missing=[], unexpected=[], order_differs=True
- `ipl squad.csv`: exact=True, missing=[], unexpected=[], order_differs=False

## Missing values (null or empty string)

- `competitions.csv`: none (column=null/empty)
- `teams.csv`: none (column=null/empty)
- `matches.csv`: home_team_captain_id=44/0, away_team_captain_id=45/0, toss_win_team_id=15/0, toss_opted=15/0, first_inn_revised_overs=858/0, second_inn_revised_overs=858/0, revised_target=860/0, win_team_id=41/0 (column=null/empty)
- `playing_eleven.csv`: batting_order=8678/0, is_captain=8667/0, is_wk=8667/0 (column=null/empty)
- `competition_team_player_mapping.csv`: none (column=null/empty)
- `ball_by_ball.csv`: dismissal_type_id=190118/0, dismissal_type=190118/0, dismissed_player_id=190107/0, stroke=12/0, delivery_style=7/0, over_or_around=407/0 (column=null/empty)
- `ipl squad.csv`: designation=247/0 (column=null/empty)
- `updated_ball_by_ball.csv`: dismissal_type_id=190118/0, dismissal_type=190118/0, dismissed_player_id=190107/0, stroke=12/0, delivery_style=7/0, over_or_around=407/0 (column=null/empty)
- `matches 2026.csv`: first_ings_score=1/0, first_ings_wkts=1/0, second_ings_score=1/0, second_ings_wkts=1/0, match_winner=1/0, wb_runs=24/0, wb_wickets=17/0, balls_left=1/0, player_of_the_match=1/0, top_scorer=1/0, highscore=1/0, best_bowling=1/0, best_bowling_figure=1/0 (column=null/empty)
- `batting_stats2026.csv`: none (column=null/empty)
- `bowling_stats2026.csv`: none (column=null/empty)
- `fielding_stats2026.csv`: none (column=null/empty)

## Entity counts

- competitions: 141
- teams_rows: 353
- distinct_team_ids_in_teams: 38
- distinct_team_names_in_teams: 38
- matches: 883
- venues: 98
- venue_countries: 17
- players_in_mapping: 1217
- players_in_playing_eleven: 1082
- players_in_ball_by_ball: 959
- matches_in_playing_eleven: 880
- matches_with_ball_by_ball: 867

## Competition format distribution

| match_format | ipl_flag | competitions | matches | matches_with_balls | first_match | last_match |
|---|---|---|---|---|---|---|
| T20 | IPL | 5 | 371 | 367 | 2022-03-26 00:00:00 | 2026-05-31 00:00:00 |
| T20 | non-IPL | 2 | 30 | 30 | 2024-10-18 00:00:00 | 2025-11-23 00:00:00 |
| T20I | non-IPL | 134 | 482 | 470 | 2022-01-22 00:00:00 | 2026-11-01 00:00:00 |

## Relationships

| child | parent | child_rows_checked | orphan_rows | distinct_orphan_keys |
|---|---|---|---|---|
| teams(comp_id) | competitions(comp_id) | 353 | 0 | 0 |
| matches(comp_id) | competitions(comp_id) | 883 | 0 | 0 |
| matches(comp_id, home_team_id) | teams(comp_id, team_id) | 883 | 0 | 0 |
| matches(comp_id, away_team_id) | teams(comp_id, team_id) | 883 | 0 | 0 |
| matches(home_team_id) | teams(team_id) | 883 | 0 | 0 |
| matches(win_team_id) | teams(team_id) | 842 | 0 | 0 |
| matches(toss_win_team_id) | teams(team_id) | 868 | 0 | 0 |
| matches(home_team_captain_id) | mapping(player_id) | 839 | 0 | 0 |
| matches(away_team_captain_id) | mapping(player_id) | 838 | 0 | 0 |
| playing_eleven(match_id) | matches(match_id) | 28381 | 0 | 0 |
| playing_eleven(team_id) | teams(team_id) | 28381 | 0 | 0 |
| playing_eleven(player_id) | mapping(player_id) | 28381 | 0 | 0 |
| mapping(comp_id) | competitions(comp_id) | 6413 | 0 | 0 |
| mapping(comp_id, team_id) | teams(comp_id, team_id) | 6413 | 0 | 0 |
| bbb(match_id) | matches(match_id) | 200999 | 0 | 0 |
| bbb(batting_team_id) | teams(team_id) | 200999 | 0 | 0 |
| bbb(bowling_team_id) | teams(team_id) | 200999 | 0 | 0 |
| bbb(striker_id) | mapping(player_id) | 200999 | 0 | 0 |
| bbb(non_striker_id) | mapping(player_id) | 200999 | 0 | 0 |
| bbb(bowler_id) | mapping(player_id) | 200999 | 0 | 0 |
| bbb(dismissed_player_id) | mapping(player_id) | 10892 | 0 | 0 |
| bbb(match_id, striker_id) | playing_eleven(match_id, player_id) | 200999 | 83 | 6 |
| bbb(match_id, bowler_id) | playing_eleven(match_id, player_id) | 200999 | 30 | 3 |

team_id is a globally unique key: **True** (teams.csv ids with several names: 0, mapping: 0)

- playing_eleven_rows_without_mapping_for_match_comp_team_player: 5
- matches_home_team_name_differs_from_teams_table: 0
- matches_away_team_name_differs_from_teams_table: 0
- matches_without_playing_eleven_rows: 3
- bbb_batting_team_not_home_or_away: 0
- matches_where_home_team_batted_first: 409
- matches_where_away_team_batted_first: 458

## matches.csv vs ball_by_ball reconciliation

883 matches - 867 with deliveries = 16 without (identity holds: True). Status counts: {'ABANDONED': 16}. ball_by_ball match_ids absent from matches.csv: 0. Full list: `match_reconciliation.csv`.

## ball_by_ball.csv vs updated_ball_by_ball.csv

Verdict: **SAME_ROWS_SAME_KEYS_VALUES_DIFFER**; rows 200999 vs 200999; differing values per column: {'striker_name': 24, 'non_striker_name': 33, 'extras1_runs': 199980}.

## Cricsheet directories

| dir | json | spec | delta | date_min | date_max | errors |
|---|---|---|---|---|---|---|
| ipl_male_json | 1243 | 1243 | 0 | 2008-04-18 | 2026-05-31 | 0 |
| t20s_male_json | 3649 | 3649 | 0 | 2005-02-17 | 2026-11-01 | 0 |
| it20s_male_json | 240 | 240 | 0 | 2010-06-04 | 2024-05-26 | 0 |
| bbl_male_json | 662 | 662 | 0 | 2011-12-16 | 2026-01-25 | 0 |
| cpl_male_json | 445 | 445 | 0 | 2013-07-30 | 2026-09-20 | 0 |
| mlc_male_json | 109 | 109 | 0 | 2023-07-13 | 2026-07-18 | 0 |
| india_male_json | 1037 | 1037 | 0 | 2001-12-19 | 2026-11-01 | 0 |
| 2026_male_json | 1619 | 1619 | 0 | 2026-01-01 | 2026-11-03 | 0 |

Index rows 9004, distinct match ids 7993; ids in several directories: 974 ({'2026_male_json+t20s_male_json': 501, 'india_male_json+t20s_male_json': 252, '2026_male_json+ipl_male_json': 74, '2026_male_json+cpl_male_json': 38, '2026_male_json+india_male_json+t20s_male_json': 37, '2026_male_json+mlc_male_json': 34, '2026_male_json+bbl_male_json': 27, '2026_male_json+india_male_json': 11}).

IPL Cricsheet vs official CSV: csv=371, cricsheet=1243, matched keys=367, csv unmatched=4, cricsheet unmatched=876, ambiguous=0.

## Ball-by-ball totals vs Cricsheet

Original file: 1504 innings compared, formula runs+e1+e2 agrees in 0.
Updated file: 1504 innings compared, formula runs+e1+e2 agrees in 1494.

See `extras_mapping.md` for the full encoding table.

## ipl squad.csv

rows=257, teams=10, exact name matches (case-sensitive)=233, normalised=234, candidate counts={'1': 244, '0': 8, '>1': 5}.

## Problem statement PDF

2 pages, 3809 characters extracted to `problem_statement.txt`; requirements summary in `problem_statement_summary.md`.

Originals unmodified during audit: {'snapshot_identical': True, 'sha256_identical': True}

