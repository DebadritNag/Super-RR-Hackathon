# Implementation Plan: Phase 1 (workspace inspection and data audit)

Scope: audit only. No ingestion, pressure metrics or rankings. Raw files in D:\Data are read-only. All code lives in D:\Data\backend. Every number in a report comes from running code.

## Observations from workspace inspection (facts to build on)

- `python` is 3.11.0, pip 26.2.1. `python3` is absent, so use `python` in every command and in README.
- Already installed globally: fastapi 0.111.0, pandas 2.2.3, pyarrow 22, pydantic 2.13.5, pydantic-settings 2.15, pytest 8.4.2. PyPDF2 3.0.1 is present, `pypdf` is not verified. duckdb, scipy, scikit-learn, sqlalchemy, uvicorn, httpx, ruff, numpy and pypdf were not listed in the filtered output, so assume they must be installed.
- Decision: install into the active Python with `python -m pip install -r requirements.txt`. If a conflict arises (the global environment has playwright and others), create `backend\.venv` and rerun. Report any failure.
- File sizes: ball_by_ball.csv 41,071,609 bytes. updated_ball_by_ball.csv 41,071,837 bytes (228 bytes larger, so likely a same-row-count correction, not a superset; verify by code). Other CSVs are under 1 MB.
- Headers confirmed. ball_by_ball and updated_ball_by_ball share the same 33 columns, in an order that differs from the spec (`batting_team_id` follows `innings_ball_num`; `delivery_ist_time` is last).
- First data row differs between the two files: original has `extras_type=None, extras1_runs=6, extras_2_runs=0, runs=0`, updated has `extras1_runs=0`. The literal string "None" is used in extras_type. This is a strong lead that the original `extras1_runs` is corrupted on some rows. Treat as a hypothesis until the diff step proves it.
- matches.csv has `win_team_id` and `result` as free text ("West Indies Won by 9 Wickets"). `playing_eleven.is_played` is the text `true`/`false`, while `is_impact`/`is_impact_off` are 0/1. Read booleans explicitly as VARCHAR first, then map.
- `delivery_ist_time` looks like "2022-01-23 00:00:00 UTC" with a midnight time, so it may be date-only in practice. Check before using it.
- `matches 2026.csv` uses a different schema (match_id 1.., date like "March 28, 2026", team abbreviations such as RCB, no comp_id). Its match_id is NOT the matches.csv match_id. The 2026 stats CSVs are tiny aggregates (batting/bowling/fielding) with team abbreviations and no player_id.
- `ipl squad.csv`: team_no, team_name, player, nationality, role, designation.
- `D:\Data\.agents` existed only as the target of this plan. The 8 JSON dirs are present. `backend` does not exist yet.
- Path pitfalls: `Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf`, `ipl squad.csv` and `matches 2026.csv` contain spaces. Use `pathlib.Path` everywhere, and `-LiteralPath` in PowerShell. Pass paths to DuckDB as parameters or with single quotes and forward slashes (`Path.as_posix()`), escaping `'` by doubling.

## Module list and signatures

All under `D:\Data\backend\app\`. Use type hints, `logging` (no `print` in library code), and `from __future__ import annotations`.

1. `core/config.py`
   - `class Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_prefix="SUPERR_", env_file=".env", extra="ignore")`.
   - Fields: `data_root: Path = Path("D:/Data")`, `cricsheet_root: Path = Path("D:/Data")`, `squad_csv: Path = Path("D:/Data/ipl squad.csv")`, `problem_statement_pdf: Path | None = None` (discovered), `backend_root: Path` (derived from `__file__`), `duckdb_path` (default `<backend>/data/database/superr.duckdb`), `audit_dir`, `reports_dir`, `staging_dir`, `processed_dir`, `log_level: str = "INFO"`.
   - `def get_settings() -> Settings` (`functools.lru_cache`).
2. `core/logging.py`: `def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None`; `def get_logger(name: str) -> logging.Logger`.
3. `data_pipeline/dataset_discovery.py`
   - `EXPECTED_CSVS: dict[str, ExpectedFile]` (name, expected rows, expected cols), `EXPECTED_JSON_DIRS: dict[str, int]` (spec counts 1243, 3649, 240, 662, 445, 109, 1037, 1619, in the order ipl, t20s, it20s, bbl, cpl, mlc, india, 2026).
   - `@dataclass class DiscoveryResult` with `found`, `missing`, `extras`, `json_dirs` (path, file_count, txt_files).
   - `def discover_datasets(root: Path, cricsheet_root: Path) -> DiscoveryResult`. Scan `root` with `iterdir`, match names case-insensitively. Anything CSV/PDF/dir not expected goes to `extras`.
   - `def find_problem_statement_pdf(root: Path) -> Path | None` (glob `*.pdf`, no hard-coded name).
4. `data_pipeline/schema_validator.py`
   - `EXPECTED_SCHEMAS: dict[str, list[str]]` for the 6 core CSVs, the 5 extras and the squad file.
   - `def read_csv_header(path: Path) -> list[str]` (`encoding="utf-8-sig"`).
   - `def compare_schema(actual: list[str], expected: list[str]) -> dict` returning `missing`, `unexpected`, `order_differs`.
   - `def describe_file(con: duckdb.DuckDBPyConnection, path: Path) -> dict` returning row count, columns, DuckDB types, and per-column null count, empty-string count and distinct count.
5. `data_pipeline/data_quality.py` (all take a DuckDB connection with CSVs registered as views, see "Large files")
   - `def register_csv_views(con, files: dict[str, Path]) -> None`
   - `def duplicate_rows(con, view: str) -> int`
   - `def duplicate_keys(con, view: str, key_cols: list[str]) -> dict` (count plus up to 20 samples)
   - `def invalid_ids(con, view: str, col: str) -> dict` (null, non-numeric, non-positive)
   - `def value_counts(con, view: str, col: str, limit: int = 50) -> list[tuple]`
   - `def date_range(con, view: str, col: str) -> dict`
   - `def fk_orphans(con, child: str, child_cols: list[str], parent: str, parent_cols: list[str]) -> dict` (orphan row count, distinct orphan values, samples)
   - `def team_id_uniqueness(con) -> dict` (does one team_id map to multiple team_name values in teams.csv and the mapping file?)
   - `def reconcile_matches(con) -> pandas.DataFrame`. For every match_id in matches.csv without any ball_by_ball rows, output match_id, date, comp_id, comp_name, stage, result, win_team_id, knock_out, plus `status`. Status is derived from `result` text patterns plus `win_team_id`, `first_inn_revised_overs`, `revised_target` and playing_eleven presence (for example `NO_RESULT`, `ABANDONED`, `TIED`, `COMPLETED_NO_BALLS`, `UNKNOWN`). First list the distinct `result` strings with counts and write rules from what is actually there. Anything that does not match a rule is `UNKNOWN`, never guessed. Also list ball_by_ball match_ids absent from matches.csv.
6. `data_pipeline/ball_by_ball_inspector.py`
   - `def profile_columns(con, view: str) -> dict` (distinct values and frequencies for extras_type, extras1_runs, extras_2_runs, runs, is_wicket, dismissal_type_id, dismissal_type, overid, innings, dismissed_player_id; min/max for innings_ball_num and over_ball_num).
   - `def extras_crosstab(con, view: str) -> pandas.DataFrame` (extras_type x extras1_runs x extras_2_runs x runs, with counts).
   - `def ball_counter_behaviour(con, view: str) -> dict`. Per (match_id, innings): is innings_ball_num strictly increasing by 1, does it skip or repeat on wides/no-balls, does over_ball_num exceed 6, how many rows per over by extras_type.
   - `def compare_ball_files(con, a: str, b: str) -> dict`. Row counts, match_id sets, key `(match_id, innings, innings_ball_num, overid, over_ball_num)` uniqueness, then count and per-column breakdown of differing rows on the join. Determine superset, same-row-different-values, or row-level corrections.
   - `def cricsheet_innings_totals(json_paths) -> dict`. Total runs, extras, wides, noballs, legal balls per innings from Cricsheet.
   - `def validate_against_cricsheet(con, view, matches_df, cricsheet_index, n: int = 20) -> pandas.DataFrame`. Pick matches (IPL, with the date+teams join from step 6; deterministic selection such as the first N by match_id) and compare candidate formulas for innings total: `sum(runs)`, `sum(runs + extras1_runs + extras_2_runs)`, `sum(runs + extras1_runs)`, etc. Report which formula matches how many matches. Use the same data for the original and updated files.
   - `def build_extras_mapping(...) -> list[dict]`. Each entry has code, meaning, evidence (counts, matches checked), confidence (HIGH/MEDIUM/LOW), status (`VERIFIED` or `UNVERIFIED`). Anything not demonstrated stays `UNVERIFIED`.
7. `data_pipeline/cricsheet_auditor.py`
   - `def iter_match_files(dir: Path)` (files named `<id>.json`; ignore .txt).
   - `def audit_cricsheet_dir(dir: Path, expected: int) -> dict`. Single pass with `json.load`, collecting file count, `meta.data_version` and `meta.revision` distribution, set of top-level keys, `info` keys and their frequency, outcome variant keys (`winner`, `result`, `by`, `method`, `eliminator`, `bowl_out`), presence of `replacements`, `powerplays`, super-over innings (`super_over` key), `target`, DLS `method`, `registry`, date range (`info.dates`), `info.event.name`, `info.gender`, `info.team_type`, `info.match_type`. Cache a lightweight per-match record (id, date, teams sorted, event, match_type, venue, outcome summary) to `backend/data/staging/cricsheet_index.parquet` so overlap steps do not re-parse 8,000+ files. Handle read errors per file (log, count, continue). Open with `encoding="utf-8"`.
   - `def cross_directory_overlap(index: pandas.DataFrame) -> dict`. By file name id across directories, and by (date, frozenset(teams)). Pay specific attention to india_male_json and 2026_male_json against the others. Note that an ID collision by file name across dirs is not an identity match; Cricsheet ids are global, so a repeated id is a real overlap.
   - `def ipl_overlap_with_csv(index, matches_df, comps_df, teams_df) -> dict`. Cricsheet ipl_male_json matches versus official IPL matches (comp_name contains "Indian Premier League" or "IPL"; confirm from the data) by date plus normalised team names. Report matched, unmatched either side, and ambiguous (several matches same day and teams). Report only; no mapping tables.
8. `data_pipeline/squad_auditor.py`: `def audit_squad(squad_csv: Path, mapping_df) -> dict`. Schema, rows, team count, role, nationality and designation distributions, Rajasthan Royals rows, exact (case-insensitive and whitespace-normalised, reported separately) match counts versus mapping `player_name`, plus counts of squad names with 0, 1 or more than 1 candidate mapping player_id. Candidate generation only.
9. `data_pipeline/pdf_extractor.py`: `def extract_pdf_text(pdf: Path, out_txt: Path) -> dict` using `pypdf.PdfReader` (fallback to PyPDF2 if pypdf import fails), UTF-8 output, page-count and character-count return. `def find_requirement_hints(text: str) -> dict` is keyword-based only (deliverables, pressure, eligibility, IPL, T20I, weighting, date window, output format). The written summary of requirements is produced by reading the saved text, not by regex alone.
10. `data_pipeline/audit_runner.py`: `def run_full_audit(settings) -> AuditBundle` orchestrating all of the above, and writers: `write_json`, `write_csv`, `write_markdown`. JSON via a helper that converts numpy/pandas/Path/Timestamp types.
11. `data_pipeline/schema_proposal.py` (optional): `def write_proposed_schema(path: Path, findings: dict) -> None`. Alternatively write `proposed_schema.sql` by hand after the findings are known (preferred, since keys depend on the results).
12. `utils/`: `paths.py` (`posix(path) -> str`, `sql_quote(s) -> str`), `jsonio.py` (`to_jsonable(obj)`).

Empty `__init__.py` in every package folder.

## Large files and encoding

- ball_by_ball is about 41 MB and about 201k rows, which is small for DuckDB. Use `read_csv(path, header=true, all_varchar=true)` for the profiling pass so nothing is silently coerced, then `TRY_CAST` where typed analysis is needed. Run a second typed view with `read_csv_auto(path, sample_size=-1)` and record the inferred types, so schema_report shows the inference result across the full file.
- `delivery_ist_time`, boolean columns ("true"/"false") and ID columns with blanks are the typing risks. Report type inference conflicts rather than hide them.
- Use one in-memory DuckDB connection for the audit (`duckdb.connect()`), separate from the persistent `superr.duckdb`. Do not write the audit into the persistent database in this phase.
- Pandas is used only for small results and for the Cricsheet index. Any pandas read of CSVs uses `dtype=str, keep_default_na=False, encoding="utf-8-sig"`. Fall back to `latin-1` only if a UTF-8 decode error is logged, and report it.
- Windows: write output files with `encoding="utf-8", newline="\n"`. In PowerShell, set `$env:PYTHONUTF8=1` before running. Avoid Unicode box characters in console prints (cp1252 console).
- Cricsheet parsing: about 8,000 small files, roughly a minute or two. Use `json.load` in a plain loop. Do not use multiprocessing unless it is clearly too slow.

## Order of work

1. Create folder skeleton, `__init__.py` files, `.gitignore` (ignore `.venv`, `__pycache__`, `data/database/*.duckdb`, `data/staging`, `data/processed`, `.env`, `.ruff_cache`), `.env.example` (all `SUPERR_*` variables), `requirements.txt`, `README.md` skeleton. `data/raw` is a placeholder only: do not copy or move originals into it (note it in README).
   Verify: `Get-ChildItem -Recurse D:\Data\backend -Directory` lists all required folders.
2. Install requirements. Verify: `python -c "import fastapi, uvicorn, pydantic_settings, sqlalchemy, pandas, numpy, scipy, duckdb, pyarrow, sklearn, pytest, httpx, pypdf"` exits 0. Record versions in the README or final report; report any failed package.
3. Write `core/config.py`, `core/logging.py`, `utils/*`. Verify: `python -c "from app.core.config import get_settings; print(get_settings())"` run from `D:\Data\backend`, and again with `$env:SUPERR_DATA_ROOT='X:/nope'` to confirm the override.
4. Write `dataset_discovery.py`. Verify: a run prints found 7 CSVs (6 core plus `ipl squad.csv`), 5 extras, 8 JSON dirs, 1 PDF, and no missing files.
5. Write `schema_validator.py` and `data_quality.py`; run on the six core CSVs plus squad. Verify: actual row counts versus spec (competitions 141, teams 353, matches 883x22, playing_eleven 28,381x9, mapping 6,413, ball_by_ball ~200,999x33), reported side by side with deltas.
6. Write `ball_by_ball_inspector.py` (profiling, counter behaviour, original versus updated comparison). Do this before the Cricsheet total validation. Verify: `extras_crosstab` output saved to the audit folder; the diff result states plainly whether updated is superset, same-key correction, or other.
7. Write `cricsheet_auditor.py`; build the index parquet; run overlap. Then run `validate_against_cricsheet` (needs the date+teams link) and `reconcile_matches`. Verify: per-directory counts versus the spec numbers; the validation table shows N matches checked and which formula matches each.
8. Write `squad_auditor.py` and `pdf_extractor.py`. Verify: `problem_statement.txt` exists, is non-empty, and the page count is printed. Read it and write the requirements summary and the list of conflicts with the spec (for example "Top 10", weighting, formulas).
9. Write `audit_runner.py` and `scripts/audit_datasets.py` (argparse: `--skip-cricsheet`, `--output-dir`; adds `backend` to `sys.path`). Produce all outputs in `backend/data/audit/`: dataset_audit.json/.csv/.md, schema_report.json, data_quality_report.json, extras_mapping.md, match_reconciliation.csv, cricsheet_overlap_report.json, directory_tree.txt, problem_statement.txt. Verify: every file exists and is non-empty; `python -c "import json;json.load(open(...))"` for each JSON.
10. Write `proposed_schema.sql` using the findings (team_id uniqueness decides whether `teams` has key `(comp_id, team_id)` or `team_id` alone; the ball-file decision may add `source_file` columns). Include all 31 named logical tables plus raw source tables (`raw_ball_by_ball`, `raw_ball_by_ball_updated`, `raw_matches_2026`, `raw_batting_stats_2026`, `raw_bowling_stats_2026`, `raw_fielding_stats_2026`, `raw_cricsheet_matches`). Verify: execute the whole file in an in-memory DuckDB (`duckdb.connect().execute(sql)`) with no errors; keep Postgres-friendly types (`INTEGER`, `BIGINT`, `VARCHAR`, `DATE`, `BOOLEAN`, `DOUBLE`, `TIMESTAMP`) and avoid DuckDB-only syntax unless commented.
11. Write `tests/test_dataset_audit.py` (see below). Run `python -m pytest D:\Data\backend\tests -q` from `D:\Data\backend`.
12. `python -m ruff check D:\Data\backend` and `python -m ruff format --check`. Add `pyproject.toml` with `[tool.ruff]` (line-length 100, target py311) and `[tool.pytest.ini_options]` (`pythonpath = ["."]`, `testpaths = ["tests"]`). Fix all findings.
13. Generate `directory_tree.txt` last (so it lists the finished output; exclude `.venv`, `__pycache__`). Finally confirm originals are unmodified: compare `LastWriteTime` and sizes of the root files captured at the start (store a before-snapshot in the audit JSON; also `Get-FileHash` for the six core CSVs before and after).

## Tests (`backend/tests/test_dataset_audit.py`)

Use small synthetic CSVs created in `tmp_path` (not the real data) with an in-memory DuckDB connection. Cover: `compare_schema` (missing, extra, reorder), `duplicate_rows`, `duplicate_keys`, `fk_orphans`, `value_counts`, `team_id_uniqueness` (a shared id with two names), `discover_datasets` on a temp dir (extras and missing flagged), `compare_ball_files` (identical, one changed value, one extra row), `reconcile_matches` status rules, and path handling with a space in the filename. Add one light smoke test, skipped if `D:/Data/competitions.csv` is absent, that the row count equals 141 as measured. Report the actual pytest output (passed, failed, skipped counts) in the final summary.

## How to verify each output

- Every report number is produced by `run_full_audit`; no hand-typed numbers. After the run, spot-check three numbers per report against an independent DuckDB `SELECT count(*)` in a shell.
- extras_mapping.md: each row shows code, evidence counts, the Cricsheet match count backing it, confidence and VERIFIED/UNVERIFIED. Penalty runs, "Overstep" and any other unseen label stay UNVERIFIED if fewer than a handful of examples exist.
- match_reconciliation.csv: row count must equal (distinct matches.csv match_ids) minus (distinct matches.csv match_ids present in ball_by_ball); print this identity in the run log.
- cricsheet_overlap_report.json: per-directory counts sum to the total index rows; the overlap counts are symmetric.
- Re-run the audit twice; compare the file hashes of the JSON outputs (excluding a `generated_at` field) to confirm determinism.

## Blockers and decisions to flag in the final report (do not resolve silently)

- Which ball-by-ball file is authoritative (`ball_by_ball.csv` versus `updated_ball_by_ball.csv`). Give the evidence from the diff and Cricsheet validation, then recommend; leave the decision to the user.
- Whether `matches 2026.csv` and the `*_stats2026.csv` files should be used. They have no ids and use abbreviations, so they can only be linked by name. Recommend after comparing, for example, with `matches.csv` 2026 rows and Cricsheet 2026.
- The brief's "Jan 2022 to Nov 2026" date range and 2026 data: report the actual maximum match date from the files; do not assume it.
- The spec says python3; only `python` exists. Document this in README.
- The PDF is the source for the real requirements; where it conflicts with the brief, list both and ask the user.
- Package install failures, if any (global environment conflicts; fall back to `.venv`).

## Final deliverable (written summary by the executing agent)

Directory tree; CSV schemas and actual versus spec row counts; JSON schema variations and counts; missing-value highlights; relationship validation results; extras interpretation with confidence; overlap findings; unmatched-match reconciliation; PDF requirements and conflicts; proposed schema overview; blockers and decisions; list of files created; commands to run (`cd D:\Data\backend; python scripts\audit_datasets.py`, `python -m pytest -q`, `python -m ruff check .`); real test and ruff results.
