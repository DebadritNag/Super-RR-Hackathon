# Cricsheet Super Over validation (innings 3 and 4)

## 1. Interpretation and status

- Validation only. Cricsheet JSON was read from disk; nothing was loaded into DuckDB, no official record was changed and no innings was relabelled.
- proxy_run: yes; pressure_status: PENDING_PHASE3; not_for_publication: yes.
- Official matches with innings 3/4: 6. CONFIRMED_SUPER_OVER: 3, UNCONFIRMED: 3, CONFLICTING: 0.

How Cricsheet represents a Super Over: Cricsheet marks a Super Over as extra entries in the top-level `innings` list, appended after the regulation innings, each carrying `"super_over": true`, a `team`, and `overs` numbered from 0. A tied match also carries `info.outcome.eliminator` (the winning team) next to `result: tie`; a bowl-out would appear as `info.outcome.bowl_out`.

## 2. Classification per official match

| match | date | type | teams | mapping | cricsheet id | class | reasons | proposed status (not written) |
|---|---|---|---|---|---|---|---|---|
| 34429 | 2024-07-30 | T20I | Sri Lanka v India | MAPPED_UNIQUE | 1442989 | CONFIRMED_SUPER_OVER | none | CONFIRMED_SUPER_OVER_BY_CRICSHEET |
| 40725 | 2025-04-16 | IPL | Delhi Capitals v Rajasthan Royals | MAPPED_UNIQUE | 1473469 | UNCONFIRMED | MAPPING_SANITY_FAILED | UNCONFIRMED_INNINGS_3_4 |
| 45512 | 2025-09-26 | T20I | India v Sri Lanka | MAPPED_UNIQUE | 1496937 | CONFIRMED_SUPER_OVER | none | CONFIRMED_SUPER_OVER_BY_CRICSHEET |
| 48027 | 2025-11-21 | OTHER_T20 | Bangladesh A v India A | NOT_FOUND | none | UNCONFIRMED | MAPPING_NOT_FOUND | UNCONFIRMED_INNINGS_3_4 |
| 48029 | 2025-11-23 | OTHER_T20 | Bangladesh A v Pakistan A | NOT_FOUND | none | UNCONFIRMED | MAPPING_NOT_FOUND | UNCONFIRMED_INNINGS_3_4 |
| 50359 | 2026-04-26 | IPL | Lucknow Super Giants v Kolkata Knight Riders | MAPPED_UNIQUE | 1529281 | CONFIRMED_SUPER_OVER | none | CONFIRMED_SUPER_OVER_BY_CRICSHEET |

## 3. Evidence per match

### Match 34429 (India in Sri Lanka T20I Series 2024, 2024-07-30)

Official result status: TIED_DECIDED_BY_TIEBREAK; result text: India Tied with Srilanka (India Won the Super Over by 2 wickets).
Regulation-innings sanity: passed (no failures); competition check: passed.
Cricsheet file t20s_male_json/1442989.json; outcome {"result": "tie", "eliminator": "India"}; event {"name": "India tour of Sri Lanka", "match_number": 3}.

| innings | batting team | deliveries | legal | runs | wickets | official role status |
|---|---|---|---|---|---|---|
| 3 | Sri Lanka | 4 | 3 | 2 | 2 | UNVERIFIED |
| 4 | India | 1 | 1 | 4 | 0 | UNVERIFIED |

| cricsheet innings | team | super_over | deliveries | legal | runs | wickets |
|---|---|---|---|---|---|---|
| 1 | India | no | 125 | 120 | 137 | 9 |
| 2 | Sri Lanka | no | 127 | 120 | 137 | 8 |
| 3 | Sri Lanka | yes | 4 | 3 | 2 | 2 |
| 4 | India | yes | 1 | 1 | 4 | 0 |

### Match 40725 (IPL 2025, 2025-04-16)

Official result status: TIED_DECIDED_BY_TIEBREAK; result text: Delhi Capitals Tied with Rajasthan Royals (DC won the Super Over).
Regulation-innings sanity: FAILED (REG2_WICKETS); competition check: passed.
Note: REG2_WICKETS gap of 1 equals the official rows with a dismissed player but is_wicket false (open_dismissed_player_without_wicket_flag); the failure is kept, not waived.
Context only, not used for the verdict: Super Over fields agree with Cricsheet if the mapping were trusted: yes.
Cricsheet file ipl_male_json/1473469.json; outcome {"result": "tie", "eliminator": "Delhi Capitals"}; event {"name": "Indian Premier League", "match_number": 32}.

| innings | batting team | deliveries | legal | runs | wickets | official role status |
|---|---|---|---|---|---|---|
| 3 | Rajasthan Royals | 6 | 5 | 11 | 2 | UNVERIFIED |
| 4 | Delhi Capitals | 4 | 4 | 13 | 0 | UNVERIFIED |

| cricsheet innings | team | super_over | deliveries | legal | runs | wickets |
|---|---|---|---|---|---|---|
| 1 | Delhi Capitals | no | 128 | 120 | 188 | 5 |
| 2 | Rajasthan Royals | no | 124 | 120 | 188 | 5 |
| 3 | Rajasthan Royals | yes | 6 | 5 | 11 | 2 |
| 4 | Delhi Capitals | yes | 4 | 4 | 13 | 0 |

### Match 45512 (Asia Cup 2025, 2025-09-26)

Official result status: TIED_DECIDED_BY_TIEBREAK; result text: India won the Super Over(Match Tied).
Regulation-innings sanity: passed (no failures); competition check: passed.
Cricsheet file t20s_male_json/1496937.json; outcome {"result": "tie", "eliminator": "India"}; event {"name": "Men's T20 Asia Cup", "match_number": 18}.

| innings | batting team | deliveries | legal | runs | wickets | official role status |
|---|---|---|---|---|---|---|
| 3 | Sri Lanka | 6 | 5 | 2 | 2 | UNVERIFIED |
| 4 | India | 1 | 1 | 3 | 0 | UNVERIFIED |

| cricsheet innings | team | super_over | deliveries | legal | runs | wickets |
|---|---|---|---|---|---|---|
| 1 | India | no | 129 | 120 | 202 | 5 |
| 2 | Sri Lanka | no | 124 | 120 | 202 | 5 |
| 3 | Sri Lanka | yes | 6 | 5 | 2 | 2 |
| 4 | India | yes | 1 | 1 | 3 | 0 |

### Match 48027 (Asia Cup Rising Stars 2025, 2025-11-21)

Official result status: TIED_DECIDED_BY_TIEBREAK; result text: Bangladesh A Won The Super Over.

| innings | batting team | deliveries | legal | runs | wickets | official role status |
|---|---|---|---|---|---|---|
| 3 | India A | 2 | 2 | 0 | 2 | UNVERIFIED |
| 4 | Bangladesh A | 2 | 1 | 1 | 1 | UNVERIFIED |

No Cricsheet counterpart was found, so no side-by-side evidence exists.

### Match 48029 (Asia Cup Rising Stars 2025, 2025-11-23)

Official result status: TIED_DECIDED_BY_TIEBREAK; result text: Pakistan A Won the super over.

| innings | batting team | deliveries | legal | runs | wickets | official role status |
|---|---|---|---|---|---|---|
| 3 | Bangladesh A | 4 | 3 | 6 | 2 | UNVERIFIED |
| 4 | Pakistan A | 4 | 4 | 7 | 0 | UNVERIFIED |

No Cricsheet counterpart was found, so no side-by-side evidence exists.

### Match 50359 (IPL 2026, 2026-04-26)

Official result status: TIED_DECIDED_BY_TIEBREAK; result text: Kolkata Knight Riders Won by Super over (Match Tied).
Regulation-innings sanity: passed (no failures); competition check: passed.
Cricsheet file ipl_male_json/1529281.json; outcome {"result": "tie", "eliminator": "Kolkata Knight Riders"}; event {"name": "Indian Premier League", "match_number": 38}.

| innings | batting team | deliveries | legal | runs | wickets | official role status |
|---|---|---|---|---|---|---|
| 3 | Lucknow Super Giants | 3 | 3 | 1 | 2 | UNVERIFIED |
| 4 | Kolkata Knight Riders | 1 | 1 | 4 | 0 | UNVERIFIED |

| cricsheet innings | team | super_over | deliveries | legal | runs | wickets |
|---|---|---|---|---|---|---|
| 1 | Kolkata Knight Riders | no | 127 | 120 | 155 | 7 |
| 2 | Lucknow Super Giants | no | 125 | 120 | 155 | 8 |
| 3 | Lucknow Super Giants | yes | 3 | 3 | 1 | 2 |
| 4 | Kolkata Knight Riders | yes | 1 | 1 | 4 | 0 |

## 4. Converse check

Official matches that map reliably, where Cricsheet shows a Super Over and the official data has no innings 3/4: 2 of 867 official matches with deliveries. Mapping status counts: {"MAPPED_UNIQUE": 759, "NOT_FOUND": 108}.

| match | date | cricsheet id | sanity passed |
|---|---|---|---|
| 13613 | 2022-02-13 | 1263472 | yes |
| 21176 | 2023-04-02 | 1322362 | yes |

## 5. Cricsheet context and limits

Index rows 9004; distinct Cricsheet ids 7993; ids present in several directories 974; ids whose copies disagree 0; matches with a Super Over innings 58.

- Official matches not found in Cricsheet cannot be checked and stay UNCONFIRMED.
- Cricsheet match/venue naming is not compared: the official venue table only has venue_id and venue_country, so venues are not used for mapping.
- Official `innings_role_status` stays UNVERIFIED for every innings 3/4; the proposed values exist only in this report and are not written anywhere.

## 6. Phase 3 treatment

Phase 3 excludes innings 3 and 4 from regulation-pressure metrics by a per-metric restriction (open_innings_3_4_role_unverified), whatever the Cricsheet verdict. Cricsheet evidence is context for a later human decision on relabelling, not an automatic relabel.

## 7. Preservation

Official CSV hashes, official table hashes and Cricsheet manifests unchanged: yes.
