# SupeRR Selector Season 2: Phase 1 data audit (summary)

Phase 1 is an audit only. There is no ingestion, no pressure metric, no ranking and no frontend. Every number below was produced by `scripts\audit_datasets.py`. Raw files in `D:\Data` were not modified (SHA-256 and size/mtime identical before and after). `D:\Data` is not a git repository, so nothing was committed. Full detail is in `D:\Data\backend\data\audit\`.

## Decisions needed from you

1. **Which ball-by-ball file is authoritative?** `ball_by_ball.csv` and `updated_ball_by_ball.csv` have the same 200,999 rows and the same keys. They differ in `extras1_runs` (199,980 rows), and in `striker_name` (24 rows) and `non_striker_name` (33 rows; "AHT Donald" vs "Aneurin Donald"). In the original, `extras1_runs` is a category code, not a run count. Using it as runs gives the wrong innings totals (0 of 1,504 innings agree with Cricsheet). In the updated file, `runs + extras1_runs + extras_2_runs` equals the Cricsheet innings total in 1,494 of 1,504 innings. **Recommendation: use `updated_ball_by_ball.csv`.** I have not picked one; the schema keeps a `source_file` column so either can be loaded.
2. **Are `matches 2026.csv` and the `*_stats2026.csv` files needed?** They have no ids and use team abbreviations. They look redundant: batting stats match ball-by-ball exactly for the 13 of 15 players whose names appear verbatim (runs and balls faced, IPL 2026 matches up to 2026-04-27), and 22 of 23 single-match dates have identical scores and wickets. The one exception is an abandoned match (no score in the file, 25 runs in ball-by-ball). **Recommendation: do not ingest them; the official CSVs already cover IPL 2026 (74 matches, all with deliveries).** Decision is yours.
3. **May Cricsheet be used for the ranking?** The PDF says rankings must be supported by analysis of "the supplied data" and lists only the CSV files. Cricsheet is useful for validation (it was used here to verify run semantics). Whether it may feed the ranking is not stated.
4. **IPL vs T20I weighting** is in your brief but not in the PDF. The PDF only asks to explain how IPL and T20I data are used. No minimum sample, eligibility rule or formula is given in the PDF.
5. **Data runs to 2026-11-01** (latest match date in `matches.csv`; latest delivery timestamp 2026-11-01 16:50 UTC). Cricsheet files reach 2026-11-03. Your brief says "to November 2026", so this agrees, but I did not assume it; it is what the files contain.
6. **`playing_eleven.csv` has repeated keys** (35 `(match_id, team_id, player_id)` groups, 75 rows, in 3 matches, none with super overs). Cause not established (UNVERIFIED).

## Environment

`python` is 3.11.0 (`python3` does not exist here). `pip install -r requirements.txt` succeeded; packages: fastapi 0.111.0, pydantic 2.13.5, pydantic-settings 2.15.0, sqlalchemy 2.0.40, pandas 2.2.3, numpy 1.26.4, scipy 1.15.2, duckdb 2.0.0, pyarrow 22.0.0, scikit-learn 1.6.1, pytest 8.4.2, httpx 0.28.1, pypdf 7.1.0, ruff 0.17.5. Pip printed an "invalid distribution ~vicorn" warning for a damaged global uvicorn folder; it did not block installs or imports.

## Directory tree

Workspace root (`D:\Data`):

```
.agents/  backend/
2026_male_json/ (1621 files, 1619 .json)   bbl_male_json/ (664, 662)    cpl_male_json/ (447, 445)
india_male_json/ (1039, 1037)               ipl_male_json/ (1245, 1243)  it20s_male_json/ (242, 240)
mlc_male_json/ (111, 109)                   t20s_male_json/ (3651, 3649)
ball_by_ball.csv  updated_ball_by_ball.csv  competitions.csv  teams.csv  matches.csv
playing_eleven.csv  competition_team_player_mapping.csv  ipl squad.csv  matches 2026.csv
batting_stats2026.csv  bowling_stats2026.csv  fielding_stats2026.csv
Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf
```

(The 2 extra files in each JSON directory are `LICENSE.txt` and `README.txt`.)

Backend (`D:\Data\backend`):

```
app/core/ (config.py, logging.py)
app/data_pipeline/ (dataset_discovery, schema_validator, data_quality, ball_by_ball_inspector,
                    cricsheet_auditor, squad_auditor, pdf_extractor, audit_runner)
app/utils/ (jsonio.py, paths.py)   scripts/audit_datasets.py   tests/test_dataset_audit.py
data/audit/ (reports)  data/staging/ (cricsheet_index.parquet, run logs)  data/raw data/processed data/database
.env.example  .gitignore  pyproject.toml  requirements.txt  README.md
```

The complete listing is `data/audit/directory_tree.txt`.

## CSV files: rows and columns against your spec

| file | rows | spec | columns | notes |
|---|---|---|---|---|
| competitions.csv | 141 | 141 | 4 | schema exact |
| teams.csv | 353 | 353 | 3 | schema exact |
| matches.csv | 883 | 883 | 22 | schema exact |
| playing_eleven.csv | 28,381 | 28,381 | 9 | schema exact |
| competition_team_player_mapping.csv | 6,413 | 6,413 | 6 | schema exact |
| ball_by_ball.csv | 200,999 | about 200,999 | 33 | same columns as the brief, different order |
| updated_ball_by_ball.csv | 200,999 | none | 33 | same columns and order as ball_by_ball.csv |
| ipl squad.csv | 257 | none | 6 | team_no, team_name, player, nationality, role, designation |
| matches 2026.csv | 39 | none | 23 | different schema, no comp_id, abbreviations |
| batting_stats2026.csv / bowling_stats2026.csv | 15 each | none | 17 each | no player_id |
| fielding_stats2026.csv | 15 | none | 6 | no player_id |

`ball_by_ball.csv` column order: match_id, innings, overid, over_ball_num, innings_ball_num, batting_team_id, bowling_team_id, striker_id, striker_name, non_striker_id, non_striker_name, bowler_id, bowler_name, batting_type, bowling_type, batting_order, runs, is_four, is_six, is_wicket, dismissal_type_id, dismissal_type, dismissed_player_id, extras_type, extras1_runs, extras_2_runs, pace_or_spin, bowl_speed, stroke, delivery_style, over_or_around, on_or_off, delivery_ist_time. No exact duplicate rows or duplicate keys in any core file except `playing_eleven.csv` (see decision 6).

Entities: 141 competitions, 883 matches, 98 venues in 17 countries, 38 distinct teams, 1,217 players in the mapping, 959 players appear in ball-by-ball, 867 matches have deliveries. Competitions: 5 IPL seasons (IPL 2022 to 2026; 371 matches, 367 with deliveries), 2 other T20 competitions (30 matches, Asia Cup Emerging/Rising Stars), 134 T20I competitions (482 matches, 470 with deliveries). IPL is identified by `comp_name` starting "IPL" (there is no "Indian Premier League" string in `competitions.csv`).

## Missing-value highlights (null counts)

- matches.csv: `first_inn_revised_overs` 858, `second_inn_revised_overs` 858, `revised_target` 860 (so 23 to 25 matches have DLS-style data), `win_team_id` 41, `toss_win_team_id` 15, `toss_opted` 15, captain ids 44 and 45.
- playing_eleven.csv: `batting_order` 8,678, `is_captain` 8,667, `is_wk` 8,667 (the 8,667 rows with `is_played=false` have no captain/wk flags).
- ball_by_ball: `dismissal_type_id`/`dismissal_type` 190,118, `dismissed_player_id` 190,107 (12 rows with `is_wicket=false` carry a dismissed_player_id and no dismissal type; 1 wicket row, a Retire Out, has none), `stroke` 12, `delivery_style` 7, `over_or_around` 407. The text "None" in `extras_type` is a literal string, not a null.
- competitions, teams, mapping: no missing values.

## Relationship validation

- **`team_id` is globally unique:** 38 team_ids map to 38 team names in `teams.csv`; no id has two names in `teams.csv` or the mapping file. The schema therefore keys `teams` on `team_id`.
- All foreign keys resolve with 0 orphans: teams/matches/mapping to competitions, matches home/away/win/toss team to teams (also by `(comp_id, team_id)`), captains to mapping, playing_eleven to matches/teams/mapping, ball-by-ball match, teams, striker, non-striker, bowler and dismissed player to the reference tables. Team names in matches agree with `teams.csv` (0 differences).
- Exceptions: 83 delivery rows (6 distinct match/striker pairs) and 30 rows (3 bowler pairs) have a striker/bowler who is not listed in that match's `playing_eleven`. 5 `playing_eleven` rows have no mapping row for that match's competition and team. 3 matches have no `playing_eleven` rows.
- Player identity: no `player_id` has two names. 7 names map to two ids each (Abdul Samad, Bashir Ahmad, Basil Hameed, Haider Ali, Mohammad Ali, Muhammad Farooq, Rashid Khan). They must not be merged by name. Ball-by-ball names equal the mapping names for the same id.
- Batting order is not home/away: in 867 matches the home team batted first in 409 and the away team in 458.
- `playing_eleven`: players marked played per team-match is 11 in 1,168 cases, 12 in 556, 10/13/16/17/19/20 in 13 team-matches, and 0 in 23 team-matches. 558 rows are impact-in and 558 impact-out. Abandoned matches can still show `is_played=true` rows.

## Ball-by-ball findings (see `extras_mapping.md`)

Verified against Cricsheet by linking official matches on exact date and team names (759 matches, 1,504 innings; 108 matches with deliveries could not be linked: 79 T20I and 29 T20, mostly Asia Cup Emerging/Rising Stars and Afghanistan matches; the reason is not established).

| field | meaning | evidence | status |
|---|---|---|---|
| `runs` | runs off the bat only | equals Cricsheet batter runs in 1,488 of 1,504 innings; equals the team total in only 16 | VERIFIED |
| `extras1_runs` (updated file) | runs from the primary extra (wide, no-ball, bye, leg-bye, penalty) | runs+extras1+extras2 = Cricsheet total in 1,494 of 1,504 innings; extras1 on wides = Cricsheet wides in 1,498 | VERIFIED |
| `extras1_runs` (original file) | category code: 6 None, 2 wide, 3 legbyes, 4 byes, 1 Overstep, 5 other, 7 Penalty (one code per `extras_type`) | formula agrees in 0 innings | VERIFIED |
| `extras_2_runs` | additional extra runs on the same ball (for example byes off a no-ball) | only the sum extras1+extras2 equals Cricsheet extras (1,491 of 1,504); the split is not validated | UNVERIFIED (split) |
| `extras_type` `wide`, `Overstep`, `other` | not legal balls. `Overstep` is a no-ball. `other` behaves as a no-ball (adding it raises Cricsheet no-ball agreement from 1,290 to 1,502 innings), its label is unknown | legal rule below | VERIFIED behaviour, label UNVERIFIED |
| `extras_type` `byes`, `legbyes` | legal balls | agree with Cricsheet in 1,475 (byes) and 1,473 (leg-byes) of 1,504 innings | VERIFIED |
| `Penalty` | 1 row in the whole file, none in Cricsheet-linked matches | none | UNVERIFIED |
| legal delivery | `extras_type NOT IN ('wide','Overstep','other')` | equals Cricsheet legal balls in 1,497 of 1,504 innings | VERIFIED |
| `innings_ball_num`, `over_ball_num`, `overid` | row counters, not legal-ball counters. `innings_ball_num` is exactly 1..n in all 1,724 innings; `over_ball_num` is exactly 1..rows in all 32,350 overs and can reach 13; `overid` is the 1-based over (max 20) | profile | VERIFIED (internal) |
| innings 3 and 4 | 6 matches, 25 and 13 rows, `overid` always 1 (super overs). Cricsheet super-over flags were not checked separately | profile | UNVERIFIED |
| `is_wicket` | a wicket on the ball | equals Cricsheet wickets in 1,483 of 1,504 innings. Dismissal types: Caught 7,557, Bowled 1,775, LBW 709, RunOut 600, Stump 214, Hit Wicket 17, Retire Out 6, Obstructing the field 3 (two spellings). Where a dismissed player is given, it is the striker 10,606 times and the non-striker 274 times | VERIFIED (count), partial |

10 innings (matches 14130, 14164, 32618, 37349, 37352, 50504) disagree with Cricsheet totals; some show different delivery counts (for example match 37352: 123 rows vs 30 Cricsheet deliveries). Cause not established. The list is in `cricsheet_overlap_report.json`.

`delivery_ist_time` is a UTC timestamp string; 42 rows are date-only (`00:00:00`). Wide `extras_type` rows have `runs` 0.

## Cricsheet JSON audit

| directory | .json files | spec | date range | match_type | team_type | notes |
|---|---|---|---|---|---|---|
| ipl_male_json | 1,243 | 1,243 | 2008-04-18 to 2026-05-31 | T20 | club | event "Indian Premier League" |
| t20s_male_json | 3,649 | 3,649 | 2005-02-17 to 2026-11-01 | T20 | international | 427 event names; 392 files carry a `missing` key |
| it20s_male_json | 240 | 240 | 2010-06-04 to 2024-05-26 | IT20 | international | |
| bbl_male_json | 662 | 662 | 2011-12-16 to 2026-01-25 | T20 | club | Big Bash League |
| cpl_male_json | 445 | 445 | 2013-07-30 to 2026-09-20 | T20 | club | |
| mlc_male_json | 109 | 109 | 2023-07-13 to 2026-07-18 | T20 | club | |
| india_male_json | 1,037 | 1,037 | 2001-12-19 to 2026-11-01 | ODI 529, T20 289, Test 219 | international | not T20-only |
| 2026_male_json | 1,619 | 1,619 | 2026-01-01 to 2026-11-03 | T20 1,109, MDM 202, ODM 175, ODI 110, Test 23 | club 920, international 699 | includes County Championship and other non-T20 events |

All files parse (0 read errors). All have `meta.data_version` 1.3.0, gender male. Key variations: `info.event` missing in 62 t20s and 17 india files; `overs` missing in 219 india and 225 2026 files; `officials`, `city`, `player_of_match` optional; `missing`, `supersubs`, `bowl_out` appear in a few directories; outcomes come as `by+winner`, `by+method+winner` (DLS), `result` only, `eliminator+result`, `method+result`, `bowl_out+result`. Super-over innings: ipl 34, t20s 70, bbl 8, cpl 4, india 8, 2026 14.

Overlap: 9,004 files, 7,993 distinct match ids; 974 ids sit in more than one directory (2026+t20s 501, india+t20s 252, 2026+ipl 74, 2026+cpl 38, 2026+india+t20s 37, 2026+mlc 34, 2026+bbl 27, 2026+india 11). No duplicate id inside a directory. IPL Cricsheet vs official CSV: 371 official IPL matches, 367 match a Cricsheet IPL file by date+teams (0 ambiguous); the 4 unmatched are abandoned matches with no deliveries. Cricsheet has 1,243 IPL matches; 876 are outside the official data (2008 to 2021).

## Unmatched matches (matches.csv without deliveries)

883 matches - 867 with deliveries = 16 (identity holds). All 16 are classified `ABANDONED` from the `result` text (`Match Abandoned`), none has `win_team_id`, all have `knock_out = 0`. Full list: `match_reconciliation.csv`. By date: 2024-05-13/16/19/20/22/28, 2024-09-15, 2024-12-14, 2025-05-17, 2025-06-12/14, 2025-09-14/19, 2025-12-17, 2026-01-10, 2026-04-29. Note: 19 matches say "Match Abandoned" overall (3 have deliveries) and 21 say "No Result" (all have deliveries). Every ball-by-ball match id exists in `matches.csv`. `matches.csv` result text has many spellings ("Won by", "won by", "Wkts", "D/L Method", Super Over wording); the classifier maps them to COMPLETED 833, NO_RESULT 21, ABANDONED 19, TIED_DECIDED_BY_TIEBREAK 9, TIED 1.

## ipl squad.csv

257 players, 10 teams, no duplicate rows. Against the mapping: 233 exact case-sensitive name matches, 234 after whitespace/case normalisation, candidate counts 244 with one candidate id, 8 with none, 5 with several. Unmatched examples: "Tilak Varma", "Ayush Matre", "Devdutt Padikal", "Prithvi Raj", "Aman Rao", "Vijaykumar Vyshak", "KL Rahul", "T Natrajan". These are candidates only; no identity was asserted.

## Problem statement PDF (2 pages)

Required: two ordered lists (top 10 batters, top 10 bowlers, selected from dropdowns on Unstop) and a methodology report covering the pressure definition, performance measurement (metrics, baselines, rating logic), fair comparisons (sample size, eligibility, match context, IPL and T20I use), evidence for the top 10, and reliability and limitations. Data is IPL and T20I from 2022 onwards. Pressure is for the participant to define and must work for both batting and bowling. Rankings must come from the supplied data. The journey video or photos are optional. Conflicts with your brief: the PDF gives no weighting, eligibility threshold or formula, no Cricsheet mention, no end date, and nothing about APIs or franchise/valuation tables. Details: `problem_statement_summary.md`.

## Proposed schema

`data/audit/proposed_schema.sql` (executes in DuckDB; Postgres-friendly types). 39 tables: the 31 you listed, `competition_teams` (needed because `teams` is keyed by `team_id`), and 7 raw tables (`raw_ball_by_ball`, `raw_ball_by_ball_updated`, `raw_matches_2026`, `raw_batting_stats_2026`, `raw_bowling_stats_2026`, `raw_fielding_stats_2026`, `raw_cricsheet_matches`). Findings that shaped it: `team_id` as sole team key; `match_squads` carries a `squad_row_no` because of the repeated keys; `deliveries` has `source_file`, `batter_runs`, `extras_primary_runs`, `extras_secondary_runs` and a derived `is_legal_ball`; `source_match_mapping` and `source_player_mapping` hold link status instead of assuming identity; every derived table carries a `model_version_id`. Not loaded and not used by any code yet.

## Files created

`D:\Data\backend\`: `app\core\{config,logging}.py`, `app\data_pipeline\{dataset_discovery,schema_validator,data_quality,ball_by_ball_inspector,cricsheet_auditor,squad_auditor,pdf_extractor,audit_runner}.py`, `app\utils\{jsonio,paths}.py`, `scripts\audit_datasets.py`, `tests\test_dataset_audit.py`, `.env.example`, `.gitignore`, `pyproject.toml`, `requirements.txt`, `README.md`, and the reports in `data\audit\`. Also `D:\Data\.agents\tasks\verification.md` and this file.

## Commands

```powershell
cd D:\Data\backend
$env:PYTHONUTF8 = 1
python scripts\audit_datasets.py        # about 4 minutes; add --skip-cricsheet for CSV-only
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

## Real results

- Audit run: exit code 0; `audit complete: 16 matches without deliveries; originals unmodified: {'snapshot_identical': True, 'sha256_identical': True}`. Two runs produced identical reports apart from timestamps and the output path.
- pytest: `19 passed in 2.43s` (tests use synthetic CSVs plus one smoke test on `competitions.csv`).
- ruff: `All checks passed!` and `23 files already formatted`. Config ignores E501 (long SQL strings).
- Spot checks against an independent method (raw line counts, Python `csv` module, `Get-ChildItem`) agree for 9 numbers; see `verification.md`.

## Known limits

Cricsheet checks cover only matches linkable by exact date and team names. The unexplained 10 innings, the 108 unlinked matches, the repeated `playing_eleven` keys, the `other` and `Penalty` labels, and the super-over meaning of innings 3 and 4 are open. The 2026 stats comparison matches 13 of 15 players by exact name only.
