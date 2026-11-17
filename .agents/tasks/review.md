# Review: Phase 1 data audit for the SupeRR Selector Season 2 backend

Phase 1 delivers a data audit only, and the evidence supports its claims. All required outputs exist, the extras mapping separates verified from unverified items, and the file-authority and 2026-file choices are left to the user. No blocking concerns.

Watch for: (1) 10 innings still disagree with Cricsheet and the cause is unexplained (confirmed, disclosed). (2) The `extras_type = 'other'` label and the `Penalty` handling are unverified (confirmed, disclosed). (3) The raw tables in `proposed_schema.sql` have no primary keys (confirmed, acceptable for staging).

**Verdict**: APPROVED

## High-level view

Scope is clean. The backend contains config, logging, discovery, schema validation, data quality, ball-by-ball inspection, Cricsheet auditing, squad auditing, PDF extraction and an audit runner. A search of the app and scripts code found no pressure, ranking, API or ingestion code. Originals were checked by SHA-256 and by size and mtime before and after the run.

The extras mapping is honest. `runs` is shown to be batter runs. In the original file `extras1_runs` is a category code, so it fails the Cricsheet total check in 0 of 1,504 innings. In the updated file it is a run count and agrees in 1,494 of 1,504 innings. The split between `extras1_runs` and `extras_2_runs`, the label for `other`, `Penalty`, and the super-over meaning of innings 3 and 4 are marked UNVERIFIED. The recommendation to use the updated file is written down, but the choice is left to the user.

Match reconciliation covers all 16 matches without deliveries. The count is the identity 883 − 867 = 16. Each status comes from the `result` text and the squad and played counts, not from guesses.

The schema file runs in DuckDB and creates 39 tables, matching the plan's 31 logical tables, `competition_teams` and 7 raw tables. Every non-raw table has a primary key.

<details>
<summary>Issues (4)</summary>

1. **Unexplained Cricsheet mismatches** (confirmed) — 10 innings (matches 14130, 14164, 32618, 37349, 37352, 50504) do not match Cricsheet totals. Investigate before the updated file is trusted for those matches in Phase 2.
2. **Unverified extras labels** (confirmed) — `other` and `Penalty` meanings and the `extras1`/`extras2` split are UNVERIFIED. Treat `other` as a no-ball-like, non-legal delivery and keep the unverified flag.
3. **Unlinked matches** (confirmed) — 108 matches with deliveries could not be linked to Cricsheet, so the run semantics are unchecked for them. Resolve the team-name linking or accept the limit.
4. **Raw tables without keys** (confirmed) — the 6 raw staging tables in `proposed_schema.sql` have no primary key. This is fine for staging, but note it for the Phase 2 loader.

</details>

<details>
<summary>Details</summary>

### Scope and data safety

The checked app and script code has no pressure metric, ranking, FastAPI route, ingestion step or frontend. `README.md` states Phase 1 is audit only. `data/raw` is an empty placeholder. The audit used an in-memory DuckDB and did not write to the persistent database. The code and outputs sit under `backend/`, and the two task files are under `.agents/`. The audit's own before and after snapshot shows the originals unchanged.

### Extras and file authority

The extras mapping gives counts of matches and innings for each claim, and each row has a confidence and a VERIFIED or UNVERIFIED status. The `other` row is labelled "VERIFIED as no-ball-like; label meaning UNVERIFIED", which is the right way to record behaviour evidence without a name. A mixed status of this kind is the closest thing to a weakness here. The linked coverage is 759 of 867 matches, so some of the VERIFIED statuses hold only for the matches that could be linked, and the file states that.

### Match reconciliation

`match_reconciliation.csv` has 16 data rows plus a header. It carries the result text, a derived `result_class`, `has_winner_id`, squad and played row counts, and a note per row. The summary points out that 19 matches say "Match Abandoned" but only 16 lack deliveries, which shows the status was derived from fields rather than assumed. Several of the abandoned matches have played rows (for example match 31288, 22 played rows), and this is shown in the data instead of being hidden.

### Schema

`proposed_schema.sql` creates cleanly. `teams` is keyed by `team_id` because the audit found 38 team ids with 38 names. `source_file` and the derived `is_legal_ball` support either ball file. `match_squads` carries a `squad_row_no` because `playing_eleven.csv` has repeated keys. The audit did not establish why those repeats exist, and it says so.

### Tests and quality

The coder's evidence shows 19 tests passed and ruff check and format checks clean. As instructed, I did not re-run them. The tests use synthetic CSVs and one smoke test on the real competitions file. They cover schema comparison, duplicate detection, orphan detection, team-id uniqueness, discovery, ball-file comparison, reconciliation rules and paths with spaces. They do not cover the Cricsheet auditor or the PDF extractor, which only the full audit run exercises. This is acceptable for a Phase 1 audit.

### User summary

`user_summary.md` has the directory tree, row counts against the spec, missing-value highlights, relationship checks, extras interpretation, JSON variations, overlap findings, reconciliation, PDF requirements and conflicts with the brief, schema overview, files created, commands, real test and ruff results, known limits, and a numbered "Decisions needed from you" section. The decisions cover the authoritative ball file, the 2026 files, Cricsheet use for ranking, IPL versus T20I weighting, the date range, and the repeated `playing_eleven` keys.

### Files

| file | role |
|---|---|
| `backend/app/**` | audit modules |
| `backend/scripts/audit_datasets.py` | audit entry point |
| `backend/tests/test_dataset_audit.py` | 19 tests |
| `backend/data/audit/*` | all required reports plus extra evidence files |
| `.agents/tasks/verification.md`, `user_summary.md` | coder evidence and summary |

</details>
