# Phase 3 data-quality application report

## 1. Status

Every figure below is an EXPLORATORY PROXY calculation from DuckDB. No pressure score is validated, no official ranking is produced, no ML model is trained, 70:30 stays a provisional default. The restriction register (`data_quality_restrictions_v1.json`, 26 rules, `global_exclusion: false`) is applied at metric and feature level only. No official record was changed or deleted; the source deliveries of innings 3 and 4 remain in `deliveries`.

## 2. Unverified innings 3/4 (RULE_INNINGS_3_4)

38 rows in 6 matches (by innings: {'3': 25, '4': 13}). Reason codes: {'UNVERIFIED_INNINGS_ROLE': 22, 'CONFIRMED_SUPER_OVER_BY_CRICSHEET': 16}. Matches by reason: {'CONFIRMED_SUPER_OVER_BY_CRICSHEET': [34429, 45512, 50359], 'UNVERIFIED_INNINGS_ROLE': [40725, 48027, 48029]}. Rows excluded by the batter-pressure mask: 38; bowler-pressure mask: 38. Rows still present in the official `deliveries` table: 38. Any of these rows inside a pressure population: False.

## 3. Unknown extras never silently zero

| Category | Rows |
|---|---|
| None | 189,165 |
| wide | 7,714 |
| legbyes | 2,748 |
| Overstep | 576 |
| byes | 529 |
| other | 264 |
| None_with_runs | 2 |
| Penalty | 1 |


`other` rows mapped to None: 0; Penalty mapped to None: 0; None-type rows with runs (kept as `None_with_runs`): 2; rows with an unverified label: 265. Penalty rows removed from ball-count masks: {'batter_balls_faced': 1, 'bowler_legal_balls': 1}. Rows with secondary extras runs: 36 (field guard blocks it in bowler economy: True).

## 4. Wicket-flag disagreements (dismissal metrics only)

Rows with a dismissed player but `is_wicket` false: 12 (regulation: 12). Rows with `is_wicket` true and no dismissed player: 1 (regulation: 1). State rows where the two wicket counts differ: 739; state features drop 0 rows. Primary dismissal-metric rows excluded: {'wicket_event_label': 1, 'batter_dismissal_rate': 39, 'bowler_wicket_rate': 38}.

## 5. DLS matches (RULE_DLS_TARGETS)

34 matches with revised fields (4433 rows). Rows whose revised state is not reconstructable: 3404 in 34 matches. DLS rows inside the primary chase population: 0; of these flagged `dls_exclude_primary`: 0.

## 6. Duplicate names (RULE_DUPLICATE_NAMES)

14 players share a name (7 names). Of 958 player ids in deliveries, a join on name would turn 958 rows into 968 and would merge 10 ids. The pipeline joins on `player_id` only; the guard raises on name columns: True.

## 7. Duplicate squad records (RULE_XI_DUPLICATES)

`match_squads` has 28381 rows, 75 flagged duplicates, 28341 after dedup. The chase pressure batter sample has 89589 rows without a squad join, 89589 with the deduplicated join (per-player counts identical: True), and 89964 with a naive join (375 extra rows). The pipeline does not use `match_squads`.

## 8. Exclusion ledger: rule x metric

`rows_excluded` is non-zero only for EXCLUDE_ROWS_FROM_METRIC. Other effects report `rows_in_metric_scope` as flagged rows that are handled by a variant, guard or note. Rules without a row-level predicate show the official-table count.

| Rule | Metric | Effect | Flagged / official count | In metric scope | Excluded | Matches | Players |
|---|---|---|---|---|---|---|---|
| RULE_INNINGS_3_4 | batter_balls_faced | EXCLUDE_ROWS_FROM_METRIC | 38 | 34 | 34 | 6 | 22 |
| RULE_INNINGS_3_4 | batter_runs_per_ball | EXCLUDE_ROWS_FROM_METRIC | 38 | 34 | 34 | 6 | 22 |
| RULE_INNINGS_3_4 | batter_strike_rate | EXCLUDE_ROWS_FROM_METRIC | 38 | 34 | 34 | 6 | 22 |
| RULE_INNINGS_3_4 | batter_dismissal_rate | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 23 |
| RULE_INNINGS_3_4 | bowler_legal_balls | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 11 |
| RULE_INNINGS_3_4 | bowler_economy | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 11 |
| RULE_INNINGS_3_4 | bowler_wicket_rate | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 11 |
| RULE_INNINGS_3_4 | innings_total_runs | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 34 |
| RULE_INNINGS_3_4 | chase_target_features | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 34 |
| RULE_INNINGS_3_4 | win_probability_features | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 34 |
| RULE_INNINGS_3_4 | pressure_state_label | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 34 |
| RULE_INNINGS_3_4 | batter_pressure_sample | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 23 |
| RULE_INNINGS_3_4 | bowler_pressure_sample | EXCLUDE_ROWS_FROM_METRIC | 38 | 38 | 38 | 6 | 11 |
| RULE_EXTRAS_OTHER | extras_type_features | REPORT_WITH_SENSITIVITY | 264 | 264 | 0 | 215 | 278 |
| RULE_EXTRAS_OTHER | bowler_economy | REPORT_WITH_SENSITIVITY | 264 | 264 | 0 | 215 | 145 |
| RULE_EXTRAS_OTHER | bowler_legal_balls | REPORT_WITH_SENSITIVITY | 264 | 264 | 0 | 215 | 145 |
| RULE_EXTRAS_OTHER | batter_balls_faced | REPORT_WITH_SENSITIVITY | 264 | 264 | 0 | 215 | 162 |
| RULE_EXTRAS_PENALTY | batter_balls_faced | EXCLUDE_ROWS_FROM_METRIC | 1 | 0 | 0 | 0 | 0 |
| RULE_EXTRAS_PENALTY | bowler_legal_balls | EXCLUDE_ROWS_FROM_METRIC | 1 | 1 | 1 | 1 | 1 |
| RULE_EXTRAS_PENALTY | bowler_economy | EXCLUDE_ROWS_FROM_METRIC | 1 | 1 | 1 | 1 | 1 |
| RULE_EXTRAS_PENALTY | extras_type_features | EXCLUDE_ROWS_FROM_METRIC | 1 | 1 | 1 | 1 | 2 |
| RULE_EXTRAS_SECONDARY | bowler_economy | DO_NOT_INTERPRET_FIELD | 36 | 36 | 0 | 36 | 31 |
| RULE_EXTRAS_SECONDARY | extras_type_features | DO_NOT_INTERPRET_FIELD | 36 | 36 | 0 | 36 | 64 |
| RULE_EXTRAS_SECONDARY | innings_total_runs | DO_NOT_INTERPRET_FIELD | 36 | 36 | 0 | 36 | 64 |
| RULE_XI_DUPLICATES | team_composition_features | DO_NOT_INFER_FROM_SQUAD | 75 | n/a | 0 | n/a | n/a |
| RULE_XI_DUPLICATES | squad_membership_features | DO_NOT_INFER_FROM_SQUAD | 75 | n/a | 0 | n/a | n/a |
| RULE_XI_DUPLICATES | batting_order_features | DO_NOT_INFER_FROM_SQUAD | 75 | n/a | 0 | n/a | n/a |
| RULE_NO_XI_MATCHES | team_composition_features | EXCLUDE_ROWS_FROM_METRIC | 0 | 0 | 0 | 0 | 0 |
| RULE_NO_XI_MATCHES | squad_membership_features | EXCLUDE_ROWS_FROM_METRIC | 0 | 0 | 0 | 0 | 0 |
| RULE_NO_MAPPING_ROW | squad_membership_features | DOCUMENT_ONLY | 5 | n/a | 0 | n/a | n/a |
| RULE_STRIKER_NOT_IN_SQUAD | squad_membership_features | DO_NOT_INFER_FROM_SQUAD | 83 | 83 | 0 | 3 | 17 |
| RULE_BOWLER_NOT_IN_SQUAD | squad_membership_features | DO_NOT_INFER_FROM_SQUAD | 30 | 30 | 0 | 3 | 8 |
| RULE_DISMISSED_NO_FLAG | wicket_event_label | SENSITIVITY_EXCLUDE | 12 | 12 | 0 | 12 | 24 |
| RULE_DISMISSED_NO_FLAG | batter_dismissal_rate | SENSITIVITY_EXCLUDE | 12 | 12 | 0 | 12 | 12 |
| RULE_DISMISSED_NO_FLAG | bowler_wicket_rate | SENSITIVITY_EXCLUDE | 12 | 12 | 0 | 12 | 12 |
| RULE_WICKET_NO_DISMISSED | wicket_event_label | EXCLUDE_ROWS_FROM_METRIC | 1 | 1 | 1 | 1 | 2 |
| RULE_WICKET_NO_DISMISSED | batter_dismissal_rate | EXCLUDE_ROWS_FROM_METRIC | 1 | 1 | 1 | 1 | 1 |
| RULE_MOM_SENTINEL | player_match_of_match_label | DO_NOT_USE_AS_LABEL | 119 | n/a | 0 | n/a | n/a |
| RULE_UTC_SUFFIX | delivery_timestamp_features | DO_NOT_INTERPRET_FIELD | 200999 | n/a | 0 | n/a | n/a |
| RULE_MIDNIGHT_TIMES | delivery_timestamp_features | DO_NOT_INTERPRET_FIELD | 42 | n/a | 0 | n/a | n/a |
| RULE_DUPLICATE_NAMES | player_identity_join | NO_JOIN_ON_NAME | 14 | n/a | 0 | n/a | n/a |
| RULE_CRICSHEET_TOTALS | innings_total_runs | SENSITIVITY_EXCLUDE | 1221 | 1221 | 0 | 6 | 86 |
| RULE_CRICSHEET_TOTALS | batter_runs_per_ball | SENSITIVITY_EXCLUDE | 1221 | 1174 | 0 | 6 | 65 |
| RULE_CRICSHEET_TOTALS | bowler_economy | SENSITIVITY_EXCLUDE | 1221 | 1221 | 0 | 6 | 47 |
| RULE_CRICSHEET_TOTALS | chase_target_features | SENSITIVITY_EXCLUDE | 1221 | 1221 | 0 | 6 | 86 |
| RULE_UNLINKABLE_MATCHES | cricsheet_validation_coverage | DOCUMENT_ONLY | n/a | n/a | 0 | n/a | n/a |
| RULE_NO_RESULT_MATCHES | match_outcome_label | EXCLUDE_ROWS_FROM_METRIC | 1753 | 1753 | 1,753 | 24 | 183 |
| RULE_NO_RESULT_MATCHES | win_probability_features | EXCLUDE_ROWS_FROM_METRIC | 1753 | 1753 | 1,753 | 24 | 183 |
| RULE_DLS_TARGETS | chase_target_features | REQUIRE_REVISED_FIELDS | 4433 | 4433 | 0 | 34 | 303 |
| RULE_DLS_TARGETS | win_probability_features | REQUIRE_REVISED_FIELDS | 4433 | 4433 | 0 | 34 | 303 |
| RULE_XI_COUNT | team_composition_features | DO_NOT_INFER_FROM_SQUAD | 569 | n/a | 0 | n/a | n/a |
| RULE_FIRST_INNINGS_TEAM | innings_order_features | DOCUMENT_ONLY | n/a | n/a | 0 | n/a | n/a |
| RULE_INFO_NO_DELIVERY_MATCHES | match_coverage_denominators | DOCUMENT_ONLY | 16 | n/a | 0 | n/a | n/a |
| RULE_INFO_RESULT_STATUS | match_outcome_label | DOCUMENT_ONLY | 50 | n/a | 0 | n/a | n/a |
| RULE_INFO_COMP_TYPE | format_assignment | DOCUMENT_ONLY | 30 | n/a | 0 | n/a | n/a |
| RULE_INFO_IPL_FORMAT | format_assignment | DOCUMENT_ONLY | 0 | n/a | 0 | n/a | n/a |
| RULE_INFO_EXTRAS1_COMPARISON | extras_type_features | DOCUMENT_ONLY | 57 | n/a | 0 | n/a | n/a |


Official-table counts for rules without a frame predicate:

| Rule | Count |
|---|---|
| RULE_XI_DUPLICATES | 75 |
| RULE_NO_MAPPING_ROW | 5 |
| RULE_MOM_SENTINEL | 119 |
| RULE_UTC_SUFFIX | 200,999 |
| RULE_MIDNIGHT_TIMES | 42 |
| RULE_DUPLICATE_NAMES | 14 |
| RULE_XI_COUNT | 569 |
| RULE_INFO_NO_DELIVERY_MATCHES | 16 |
| RULE_INFO_RESULT_STATUS | 50 |
| RULE_INFO_COMP_TYPE | 30 |
| RULE_INFO_IPL_FORMAT | 0 |
| RULE_INFO_EXTRAS1_COMPARISON | 57 |


## 9. Sensitivity: effect on exploratory pressure samples

Sample: chase rows with a valid RRR in IPL/T20I, minus rows the register excludes. Score: raw residual per ball against a comp x phase x wickets cell mean, unshrunk (proxy, not the Stage 4 baseline). Minimum balls are the Stage 5 exploratory thresholds. `spearman_common` is over players eligible in both runs.

### batter: RULE_EXTRAS_OTHER (drop other rows)

Rows dropped / added: 118.

| Competition | Min balls | Rows primary | Rows variant | Eligible primary | Eligible variant | In both | Spearman | Max abs change |
|---|---|---|---|---|---|---|---|---|
| IPL | 24 | 39,646 | 39,585 | 180 | 180 | 180 | 0.999 | 0.0757 |
| T20I | 24 | 46,552 | 46,495 | 329 | 329 | 329 | 1.000 | 0.0367 |


### batter: RULE_CRICSHEET_TOTALS (drop ten innings)

Rows dropped / added: 350.

| Competition | Min balls | Rows primary | Rows variant | Eligible primary | Eligible variant | In both | Spearman | Max abs change |
|---|---|---|---|---|---|---|---|---|
| IPL | 24 | 39,646 | 39,646 | 180 | 180 | 180 | 1.000 | 0.0000 |
| T20I | 24 | 46,552 | 46,218 | 329 | 328 | 328 | 0.999 | 0.2718 |


### batter: RULE_DLS_TARGETS (force DLS rows into sample, diagnostic only)

Rows dropped / added: 1763.

| Competition | Min balls | Rows primary | Rows variant | Eligible primary | Eligible variant | In both | Spearman | Max abs change |
|---|---|---|---|---|---|---|---|---|
| IPL | 24 | 39,646 | 40,106 | 180 | 180 | 180 | 0.997 | 0.0796 |
| T20I | 24 | 46,552 | 47,785 | 329 | 333 | 329 | 0.987 | 0.3955 |


### bowler: RULE_EXTRAS_OTHER (drop other rows)

Rows dropped / added: 118.

| Competition | Min balls | Rows primary | Rows variant | Eligible primary | Eligible variant | In both | Spearman | Max abs change |
|---|---|---|---|---|---|---|---|---|
| IPL | 32 | 41,275 | 41,214 | 167 | 167 | 167 | 0.999 | 0.0262 |
| T20I | 36 | 48,314 | 48,257 | 263 | 263 | 263 | 1.000 | 0.0957 |


### bowler: RULE_CRICSHEET_TOTALS (drop ten innings)

Rows dropped / added: 350.

| Competition | Min balls | Rows primary | Rows variant | Eligible primary | Eligible variant | In both | Spearman | Max abs change |
|---|---|---|---|---|---|---|---|---|
| IPL | 32 | 41,275 | 41,275 | 167 | 167 | 167 | 1.000 | 0.0000 |
| T20I | 36 | 48,314 | 47,964 | 263 | 263 | 263 | 0.998 | 0.1353 |


### bowler: RULE_DLS_TARGETS (force DLS rows into sample, diagnostic only)

Rows dropped / added: 1763.

| Competition | Min balls | Rows primary | Rows variant | Eligible primary | Eligible variant | In both | Spearman | Max abs change |
|---|---|---|---|---|---|---|---|---|
| IPL | 32 | 41,275 | 41,761 | 167 | 167 | 167 | 0.995 | 0.1641 |
| T20I | 36 | 48,314 | 49,590 | 263 | 268 | 263 | 0.990 | 0.2302 |


### Dismissal metric: wicket-flag variants

Striker dismissals primary 10594, with the dismissed-without-flag rows 10603; players whose count changes: 9; rows removed by RULE_WICKET_NO_DISMISSED: 1.

## 10. Feature dictionary

`pressure_feature_dictionary.json` lists 99 features: {'PRE_DELIVERY': 55, 'PARTIAL_PRE_DELIVERY': 13, 'OUTCOME_OF_DELIVERY': 11, 'OUTCOME_CONDITIONED_DENOMINATOR_FLAG': 10, 'POST_INNINGS': 5, 'POST_MATCH': 5}. All are exploratory; none is validated.

## 11. Stop point

Nothing here is a validated pressure result. Full pressure scoring, official rankings and ML training wait for explicit approval.
