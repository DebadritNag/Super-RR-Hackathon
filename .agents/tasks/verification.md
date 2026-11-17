# Phase 1 verification evidence

Workspace: `D:\Data` (raw data, read-only). Code and outputs: `D:\Data\backend`. No `review.json` existed, so this is the first iteration. `D:\Data` is not a git repository, so nothing was committed.

## 1. Audit script run end to end

Command (PowerShell, `D:\Data\backend`): `python scripts\audit_datasets.py` (about 4 minutes). Exit code 0. Final line printed:

```
audit complete: 16 matches without deliveries; originals unmodified: {'snapshot_identical': True, 'sha256_identical': True}
```

Log line from the same run: `reconciliation: 883 - 867 = 16 rows (identity True)`.

## 2. Output files exist and are non-empty (`backend\data\audit\`)

| file | bytes |
|---|---|
| dataset_audit.json | 182803 (valid JSON) |
| dataset_audit.csv | 9743 |
| dataset_audit.md | 8272 |
| schema_report.json | 24404 (valid JSON) |
| data_quality_report.json | 30080 (valid JSON) |
| extras_mapping.md | 5720 |
| match_reconciliation.csv | 4100 (16 data rows) |
| cricsheet_overlap_report.json | 51291 (valid JSON) |
| directory_tree.txt | 2595 |
| proposed_schema.sql | 21131 (executed in an in-memory DuckDB: 39 tables created, all 31 required logical tables + 7 raw tables present, `competition_teams` added) |
| problem_statement.txt | 3849 (2 pages) |
| problem_statement_summary.md | 3690 (hand-written from the extracted text) |

Extra outputs: `ball_by_ball_inspection.json`, `cricsheet_validation_original.csv`, `cricsheet_validation_updated.csv`, `extras_crosstab_original.csv`, `extras_crosstab_updated.csv`, `official_to_cricsheet_candidate_links.csv`. `data\staging\cricsheet_index.parquet` is a generated cache.

## 3. pytest

Command: `python -m pytest -v` from `D:\Data\backend`.

```
collected 19 items
tests/test_dataset_audit.py::test_compare_schema_missing_extra_reorder PASSED
tests/test_dataset_audit.py::test_duplicate_rows_and_keys PASSED
tests/test_dataset_audit.py::test_invalid_ids PASSED
tests/test_dataset_audit.py::test_value_counts_and_date_range PASSED
tests/test_dataset_audit.py::test_fk_orphans PASSED
tests/test_dataset_audit.py::test_team_id_uniqueness_detects_shared_id PASSED
tests/test_dataset_audit.py::test_discover_datasets_flags_missing_and_extras PASSED
tests/test_dataset_audit.py::test_compare_ball_files_identical_changed_extra_row PASSED
tests/test_dataset_audit.py::test_classify_result[...7 parametrised cases] PASSED
tests/test_dataset_audit.py::test_reconcile_matches_lists_every_match_without_balls PASSED
tests/test_dataset_audit.py::test_path_with_space_and_quote PASSED
tests/test_dataset_audit.py::test_ipl_overlap_report_shapes PASSED
tests/test_dataset_audit.py::test_real_competitions_row_count_smoke PASSED
============================= 19 passed in 2.43s ==============================
```

## 4. ruff

```
> python -m ruff check .
All checks passed!
> python -m ruff format --check .
23 files already formatted
```

Config (`pyproject.toml`): line length 100, rules E, F, I, W, with E501 ignored (long SQL and report strings are left unwrapped on purpose).

## 5. Independent spot checks (second method in parentheses)

| number | audit value (DuckDB / audit code) | independent value |
|---|---|---|
| ball_by_ball.csv rows | 200999 | 200999 (PowerShell `ReadAllLines` count minus header; also raw newline count stored in the audit JSON) |
| matches.csv rows | 883 | 883 (PowerShell `ReadAllLines` minus header) |
| matches in matches.csv with no deliveries | 16 | 16 (Python `csv` module set difference) |
| distinct match_ids in ball_by_ball | 867 | 867 (Python `csv` module) |
| distinct team_ids in teams.csv | 38 | 38 (Python `csv` module) |
| `Match Abandoned` results in matches.csv | 19 (result_classes ABANDONED) | 19 (Python `csv` module) |
| rows where extras1_runs differs, original vs updated | 199980 | 199980 (positional zip in Python `csv` module) |
| JSON files per directory ipl/t20s/it20s/bbl/cpl/mlc/india/2026 | 1243/3649/240/662/445/109/1037/1619 | same, from `Get-ChildItem -Filter *.json` per directory |
| match 13511 innings 1 total (runs+extras1+extras2) | 100+3+0 = 103 in cricsheet_validation_updated.csv | 103 (Python `csv` module sum over updated_ball_by_ball.csv); Cricsheet total is also 103 |

## 6. Originals unmodified

SHA-256 of the 7 ball/core CSVs was taken before and after the audit by the code (`sha256_identical: True`), and again by `Get-FileHash` after the final run. The values match the ones taken at the start of the session (e.g. ball_by_ball.csv `A3926F49...E9889`, updated_ball_by_ball.csv `01E2B437...2B396E`). File size and mtime snapshot of the whole root is identical before and after (`snapshot_identical: True`).

## 7. Determinism

The audit was run twice (second run to a different `--output-dir`). `schema_report.json`, `cricsheet_overlap_report.json`, `ball_by_ball_inspection.json`, `match_reconciliation.csv`, `extras_mapping.md`, `dataset_audit.csv` and `cricsheet_validation_updated.csv` are byte-identical (same SHA-256 prefix). `dataset_audit.json`, `data_quality_report.json` and `dataset_audit.md` differ only in `generated_at` and in the output-directory path strings, checked by a recursive diff. A first pair of runs exposed an unordered `string_agg` (a sample list printed `28978,27373` vs `27373,28978`); it was fixed with `ORDER BY` and the pair above was run afterwards.

## 8. Things that were not verified or are known limits

- Run semantics were checked against Cricsheet only for the 759 official matches that could be linked by exact date and team names (1504 innings of 759 matches are in the comparison; the other 108 matches with deliveries could not be linked). The rest is UNVERIFIED against Cricsheet.
- 10 innings do not match the Cricsheet total under runs+extras1+extras2. They are listed in `cricsheet_overlap_report.json` and their cause is not established.
- The PDF summary is hand-written from the extracted text; the keyword hints in the JSON are only a pointer.
- Pytest tests use synthetic CSVs; only one smoke test touches real data (competitions row count 141).
