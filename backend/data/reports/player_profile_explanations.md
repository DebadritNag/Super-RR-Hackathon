# Player profile explanations

Applies to `descriptive_batter_profiles.csv`, `descriptive_bowler_profiles.csv`, `phase7_descriptive_player_match.csv` and the `/api/v1/descriptive/*` endpoints. Version `p7_descriptive_v1`. Built by `backend/scripts/phase7_build_descriptive.py`; input hashes and row counts are in `phase7_descriptive_manifest.json`.

## 1. What a profile is

A profile is a set of counts and ratios computed from official ball-by-ball rows for one player in one format (IPL or T20I). Formats are never pooled. Each row of a CSV is one player in one format. Rows are sorted by `player_id` then `format`. There is no rank column, no score column and no ordering of players by performance anywhere in these files.

A profile describes what happened. It is not a measure of performance under pressure, and it is not an auction-suitability statement.

## 2. Window and exclusions

| Rule | Detail |
|---|---|
| Window | Matches in the TRAIN and VALIDATION periods (match dates 2022-01-22 to 2025-12-19). TEST-period matches (from 2026-01-01) are filtered out in the query and never read. |
| Formats | IPL and T20I only. `OTHER_T20` matches are outside both columns and are not profiled. |
| Innings | Innings 1 and 2 only. Innings 3 and 4 (confirmed or unverified super overs) are excluded from regulation metrics (rule `RULE_INNINGS_3_4`). |
| Ball faced | Striker present, extras type not `wide` and not `Penalty`. |
| Legal ball | Flagged legal in the official data and not the `Penalty` row. Wides, no-balls (`Overstep`) and `other` extras are not legal balls. |
| Bowler runs and wickets | Stored bowler-charged runs and bowler-credited wickets only. Run-outs and other non-bowler dismissals are not wickets. |
| Batter dismissal | A wicket where the dismissed player is the striker. Dismissals of a non-striker are not counted for that player. |
| DLS | DLS-affected rows are **not** excluded from the totals, as in `p4_player_stats`. `dls_rows` counts them per player. |
| Extras `other` | Kept (label unverified); `extras_other_rows` counts them per player. |
| Wicket-flag anomalies | Counted in `anomaly_rows`; no row is changed. |

## 3. Columns

Missing values are empty cells with a reason, never 0. A count of 0 is a real count (for example 0 balls in a phase).

### Identity and coverage (both files)

| Column | Meaning |
|---|---|
| `player_id`, `player_name` | Official player id and name from the official `players` table. |
| `format` | `IPL` or `T20I`. |
| `participation_role` | Derived only from balls actually faced or bowled in the window across both formats: `BATS_ONLY`, `BOWLS_ONLY`, `BATS_AND_BOWLS`. It is not a playing role and is not taken from any list. |
| `squad_role_listed` | Role in the pre-retention IPL squad file, where the player appears there. Empty otherwise. |
| `nationality`, `international_status` and their `_verification` columns | From the Phase 5 classification. The verification label states how the value was established (`DERIVED...`, `UNVERIFIED`). `UNKNOWN` stays unknown. No authoritative cap-status source with stable player ids has been supplied. |
| `seasons_covered` | Seasons (labels in the official data) in which the player has rows in this format, joined with `;`. |
| `matches_played` | Matches with `is_played` in the official playing-eleven data, before the TEST period. |
| `matches_with_participation` | Matches in which the player faced or bowled a ball. |
| `opportunities_innings` | Innings in which the player faced (batters) or bowled (bowlers) a ball. |

### Batter columns

| Column | Formula |
|---|---|
| `balls_faced`, `runs`, `dismissals` | Counts as defined in section 2. |
| `fours`, `sixes`, `boundary_runs` | Counts of fours and sixes hit; runs scored off those balls. |
| `strike_rate` | 100 * runs / balls_faced. Empty if no balls faced. |
| `average` | runs / dismissals. Empty if no dismissals (`NO_DISMISSALS`). |
| `balls_per_dismissal` | balls_faced / dismissals. Empty if no dismissals. |
| `boundary_run_share` | boundary_runs / runs. |
| `boundary_ball_share` | (fours + sixes) / balls_faced. |
| `dot_balls`, `dot_ball_share` | Balls faced with 0 batter runs; share of balls faced. |
| `pp_`, `mid_`, `death_` + `balls`, `runs`, `dismissals`, `strike_rate` | The same quantities within the powerplay, middle and death phases of the existing phase engine (phase is ball-based and depends on the innings limit). |
| `inn1_`, `chase_` + the same four | Same quantities in the first innings and in the second innings (the chase). |
| `vs_pace_`, `vs_spin_` + the same four | Same quantities against pace and spin bowling, from the official `pace_or_spin` field. |
| `strike_rate_ci_low`, `strike_rate_ci_high` | 95% percentile interval of the strike rate from a match-cluster bootstrap (1000 draws, seed 20260512). Empty with a reason in `strike_rate_ci_unavailable_reason` (fewer than 5 matches, or the rate undefined in many resamples). |

### Bowler columns

| Column | Formula |
|---|---|
| `legal_balls`, `overs` | Legal balls bowled; the same as completed overs and balls (`229.3` = 229 overs and 3 balls). |
| `runs_conceded`, `wickets` | Bowler-charged runs; bowler-credited wickets. |
| `economy` | 6 * runs_conceded / legal_balls. |
| `balls_per_wicket` | legal_balls / wickets. Empty if no wickets. |
| `dot_balls`, `dot_ball_share` | Legal balls on which no run of any kind was scored; share of legal balls. |
| `fours`, `sixes`, `boundary_runs`, `boundary_conceded_share` | Boundaries conceded off the bat; (fours + sixes) / legal_balls. |
| `wides`, `no_balls`, `extras_charged_runs` | Count of wides and of no-balls (`Overstep`) bowled; extra runs charged to the bowler beyond the runs off the bat. |
| `pp_`, `mid_`, `death_`, `inn1_`, `chase_` + `balls`, `runs`, `wickets`, `economy` | Same quantities by phase and innings. |
| `vs_rhb_`, `vs_lhb_` + the same four | Against right-hand and left-hand batters (official `batting_type`). |
| `economy_ci_low`, `economy_ci_high`, `economy_ci_unavailable_reason` | As for the strike rate, for economy. |
| `bowling_style_modal`, `bowling_style_modal_share`, `pace_or_spin_modal` | The most frequent official bowling type, its share of deliveries, and the most frequent pace/spin label. Ties go to the alphabetically first label. |

### Context-sample, quality and provenance columns (both files)

| Column | Meaning |
|---|---|
| `context_sample_balls`, `context_sample_matches` | Number of the player's deliveries (and matches) that fall in the provisional pressure-context definition `any|q0.75`, from the stored Phase 5 context rows. **Counts only.** They are labelled `DESCRIPTIVE_EXPERIMENTAL_COUNT_ONLY` in `context_sample_label` and say nothing about how the player performed in those deliveries. The definition is provisional and not validated. |
| `sample_sufficiency` | `OK`, `LOW_SAMPLE` (fewer than 60 balls faced or bowled) or `NO_BALLS`. A display flag. No profile is hidden. |
| `missing_value_notes` | Which empty cells are empty and why. |
| `mapping_warnings` | Identity or classification problems, for example `NAME_SHARED_WITH_OTHER_PLAYER_ID`, `NATIONALITY_UNKNOWN`. |
| `dls_rows`, `anomaly_rows`, `extras_other_rows`, `caveat_dls` | Counts of rows touched by the data-quality rules above. |
| `descriptive_version`, `window`, `state_version`, `official_db_sha256`, `analytical_store_sha256` | Versions and sha256 of the two databases the numbers came from. |

## 4. How to read a profile

1. Start with the denominators. A strike rate of 175 over 5 balls is not comparable with 150 over 460 balls. Every rate in the API comes with its balls.
2. Use the interval. It is a bootstrap over matches. It shows how much the rate moves if different matches had been drawn from the same player's matches. It does not include opposition, venue or batting-order effects.
3. Treat splits as smaller samples. A phase split is a subset of the total. Phase splits under 30 balls are marked small in the generated text.
4. Do not compare across formats. IPL and T20I rows are separate because the competition, opposition and conditions differ.
5. Check `mapping_warnings` and `missing_value_notes` before quoting a number.

## 5. What profiles cannot establish

* **Performance under pressure.** Runs and wickets are descriptive. The pressure measure was tested in Phase 6 and cannot separate individual players: between-player variance sits at the shrinkage floor in 48 of 48 contexts, the data-weight check passes in 0 of 48, pooled odd/even reliability of the provisional definition is 0.37 and the median reliability over 47 estimable contexts is 0.25. No Top 10 of pressure batters or bowlers is published, and the lists are not padded.
* **Who is better.** No endpoint or file says one player is better than another. The comparison endpoint reports a difference in a rate, its interval, and one of `SUPPORTED`, `NOT_DISTINGUISHABLE`, `LOW_SAMPLE` or `UNAVAILABLE`.
* **Auction suitability or value.** Nothing here estimates price, fit with a squad or availability.
* **Skill versus context.** A descriptive rate mixes the player with the opposition, venue, role and match situation.
* **Cap status.** Where status is `DERIVED` or `UNKNOWN` it is labelled so. It is not an official cap record.
* **Matches from 2026.** TEST-period matches are excluded by design.

## 6. Radar data

`/api/v1/descriptive/radar` returns, for batting and bowling separately, the raw value, its numerator and denominator and its percentile within a named cohort (same format and role, with at least 60 balls faced or bowled; 30 balls for phase dimensions; at least 10 players in the cohort). The percentile is the share of the cohort with a lower raw value (ties count half). It places a value inside a distribution. It does not say whether a higher or lower value is preferable, and the dimensions are never combined into one figure. A dimension that cannot be computed is returned as unavailable with a reason, not as 0.

## 7. Worked examples

**Batter: player 8, Mahendra Singh Dhoni, IPL.** 693 runs from 463 balls faced in 48 matches and 22 dismissals give a strike rate of 149.7 runs per 100 balls and an average of 31.5. The match-bootstrap interval of the strike rate is 128.3 to 173.4. Dot balls are 36.5% of balls faced and 67.8% of runs came from boundaries. The splits are very uneven (5 balls in the powerplay, 107 in the middle overs, 351 in the death overs), so the phase rates rest on different amounts of data. 266 of his deliveries fall in the provisional context definition; that count alone does not describe how he batted in them.

**Bowler: player 4722, Rashid Khan, IPL.** 1,854 runs conceded from 1,377 legal balls (229.3 overs) in 60 matches and 65 bowler-credited wickets give an economy of 8.08 runs per over; the match-bootstrap interval of the economy is 7.40 to 8.83. 30.4% of legal balls were dot balls and 14.6% of legal balls conceded a boundary. The powerplay (180 balls) and death (274 balls) economies are 8.30 and 9.37, each over fewer balls than the total. 373 balls fall in the provisional context definition.

These figures are read from the generated CSVs and can be reproduced with `scripts/phase7_build_descriptive.py`.

## 8. Generated text

`explain_player` (module `app/phase7/views.py`) writes plain sentences from a profile's own numbers: totals, rate, interval or the reason it is missing, dot-ball share, phase balls and rates, a small-sample warning where the display convention applies, and the context-sample count with the statement that it is a count only. It uses no superlatives and makes no ordering or ranking statement.
