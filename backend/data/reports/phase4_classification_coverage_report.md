# Phase 4 player classification coverage

Status: EXPERIMENTAL_NOT_VALIDATED. Classification version `p4_classification_v1`, as-of date `2025-12-31`. Built only from records in the data; nothing is taken from memory or outside sources.

## What the records contain
- `ipl squad.csv`: 257 rows. The `nationality` column holds Indian/Overseas. The `designation` column holds only `Captain` or blank, so **the squad file carries no capped/uncapped information**.
- `competition_team_player_mapping.csv`, `ball_by_ball.csv` and `playing_eleven.csv` carry no nationality or cap status.
- Squad rows resolved to exactly one player_id by exact name: 232 of 257; corroborated by the player's IPL 2026 team (id-keyed): 232; unresolved or ambiguous: 25.

## Coverage, all players (nationality x international status)
| nationality | international_status | players |
|---|---|---|
| Indian | Capped | 52 |
| Indian | Uncapped | 0 |
| Indian | Unknown | 112 |
| Overseas | Capped | 603 |
| Overseas | Uncapped | 0 |
| Overseas | Unknown | 3 |
| Unknown | Capped | 0 |
| Unknown | Uncapped | 0 |
| Unknown | Unknown | 447 |


Players total: 1217. Verified Uncapped players: **0**. Conflicts flagged: 0.

## Coverage, players with an eligible experimental score (403)
| nationality | international_status | players |
|---|---|---|
| Indian | Capped | 51 |
| Indian | Uncapped | 0 |
| Indian | Unknown | 35 |
| Overseas | Capped | 288 |
| Overseas | Uncapped | 0 |
| Overseas | Unknown | 1 |
| Unknown | Capped | 0 |
| Unknown | Uncapped | 0 |
| Unknown | Unknown | 28 |


## Verification labels
- nationality: {'DERIVED': 770, 'UNVERIFIED': 447}
- international status: {'DERIVED_FROM_OFFICIAL_T20I_APPEARANCES': 655, 'UNVERIFIED': 562}

## Why players are Unknown
- nationality: {'NO_SOURCE_RECORD': 445, 'SQUAD_NAME_AMBIGUOUS': 2}
- international status: {'NOT_PROVEN_CAPPED_IN_DATA': 498, 'FIRST_T20I_AFTER_AS_OF_DATE': 64}

## Rules applied
- Capped is DERIVED_FROM_OFFICIAL_T20I_APPEARANCES only: the player was listed as playing in a T20I in the data on or before the as-of date. This is derived evidence, never a verified cap list.
- Uncapped is never derived. A player absent from the T20I data stays Unknown (`NOT_PROVEN_CAPPED_IN_DATA`) because the data starts in 2022 and says nothing about earlier caps.
- Nationality comes from the squad row only when the name is unique and the team corroborates it through ids; otherwise it can be derived from T20I national-team appearances (`DERIVED_FROM_T20I_NATIONAL_TEAM`), and a franchise team never implies nationality.
- Overrides: `config/classification_overrides_v1.csv` (empty by default).
- Overrides loaded: 0.

## What is needed to populate Uncapped
An official or verified list of international caps keyed by player_id, or by player name plus team (for example a squad sheet with a capped/uncapped column), plus player_id keys for squad names that do not resolve.

## Unresolved squad names (not applied)
| squad_player | team | match_type | candidate_ids | corroborated_variant |
|---|---|---|---|---|
| Will Jacks | Mumbai Indians | NO_MATCH |  | no |
| AM Ghazanfar | Mumbai Indians | NO_MATCH |  | no |
| Tilak Varma | Mumbai Indians | NO_MATCH |  | no |
| MS Dhoni | Chennai Super Kings | NO_MATCH |  | no |
| Ayush Matre | Chennai Super Kings | NO_MATCH |  | no |
| Shivam Dubey | Chennai Super Kings | NO_MATCH |  | no |
| Zak Foulkes | Chennai Super Kings | NO_MATCH |  | no |
| Devdutt Padikal | Royal Challengers Bengaluru | NO_MATCH |  | no |
| Shahrukh Khan | Gujrat Titans | NO_MATCH |  | no |
| Nishant Sindhu | Gujrat Titans | NO_MATCH |  | no |
| Rashid Khan | Gujrat Titans | EXACT_AMBIGUOUS | 4722,20172 | no |
| Prithvi Raj | Gujrat Titans | NO_MATCH |  | no |
| Aman Rao | Rajasthan Royals | NO_MATCH |  | no |
| Lhuan-dre Pretorius | Rajasthan Royals | NO_MATCH |  | no |
| Yash Raj Punja | Rajasthan Royals | NO_MATCH |  | no |
| Nitish Kumar Reddy | Sunrisers Hyderabad | NO_MATCH |  | no |
| Pat Cummins | Sunrisers Hyderabad | NO_MATCH |  | no |
| Onkar Tarmale | Sunrisers Hyderabad | NO_MATCH |  | no |
| Harnoor Singh | Punjab Kings | NO_MATCH |  | no |
| Vijaykumar Vyshak | Punjab Kings | NO_MATCH |  | no |
| Abhishek Porel | Delhi Capitals | NO_MATCH |  | no |
| KL Rahul | Delhi Capitals | NO_MATCH |  | no |
| T Natrajan | Delhi Capitals | NO_MATCH |  | no |
| Akshat Raghuvanshi | Lucknow Super Giants | NO_MATCH |  | no |
| Abdul Samad | Lucknow Super Giants | EXACT_AMBIGUOUS | 6922,7446 | no |

