# Phase 7 chunk 3 verification (executed by the implementer)

All commands ran in `d:/Data/backend` with `PYTHONUTF8=1`. `D:\Data` is not a git repository, so nothing was committed. No gate file existed at start.

## Design decisions and deviations
| Instruction | What was done | Reason |
|---|---|---|
| Tables in `exploratory.duckdb` with prefix `p7_retention_*` | Implemented (`p7_retention_imports`, `_rows`, `_review`, `_resolution_log`). No real import was run, so the real file is unchanged (hash below). The first real import will change its hash. | The chunk text overrides the earlier plan note that wrote files only. Documented in the guide and validation report. |
| Importer location | `app/data_pipeline/retention_importer.py`, `retention_availability.py`, `app/api/v1/routes_retention.py`, scripts `import_retention_list.py` and `run_retention_procedure.py`. | Chunk text names `app/data_pipeline`. |
| Name match "plus team context" | Unique exact normalised name AND the player has appeared for the stated team; otherwise AMBIGUOUS with one suggested candidate for human confirmation. | Conservative reading of "flagged for confirmation". Expect more review items for players who changed team. |
| Authoritative source | `--authoritative` flag (requires `OFFICIAL_VERIFIED`); owner decides what counts as official. | Not defined in the brief. |
| Admin file upload | Raw file as request body (no multipart dependency). CORS still allows only `GET`, so browser use needs a proxy or a CORS change (noted in the guide, not changed). | Changing CORS alters the API surface. |
| `tests/test_phase5_gating.py` | Retention admin routes (no ranking rows, no response model) exempted from the "every route carries gate fields" check and from the internal route count of 12. | Same kind of exemption chunk 2 made for descriptive routes. No app behaviour changed. |
| `openpyxl` | Added to `requirements.txt` (3.1.2 already installed). | Needed for `.xlsx`. |

## Commands and actual results
| Command | Actual result |
|---|---|
| `python -m pytest tests/test_phase7_retention_import.py tests/test_phase7_retention_api.py tests/test_phase7_retention_no_scoring_link.py -q` | 38 passed (first run had 2 failures from my own test/docstring wording; fixed) |
| First full `python -m pytest -q -p no:cacheprovider` (log `.agents/tasks/_p7c3_full_pytest.txt`) | 1157 passed, 1 failed in 481 s: `test_phase5_gating.py::test_every_rows_returning_route_carries_the_publication_fields` (new admin routes) |
| After the exemption: `python -m pytest tests/test_phase5_gating.py tests/test_phase7_retention_api.py -q` | 53 passed. The full suite was not rerun after this one-test edit; the other 1157 passed before it and no app code changed afterwards. Expected total 1158 (1120 before + 38 new). |
| `python -m ruff check .` | All checks passed! |
| `python -m ruff format --check .` | 339 files already formatted |
| `python scripts/run_retention_procedure.py` (no file) | printed `NO RETENTION FILE YET`, exit 0; wrote header-only `candidate_availability.csv`, `candidate_availability_manifest.json` (state `NO_RETENTION_FILE_YET`), `retention_import_run_report.md` |
| `python scripts/import_retention_list.py --file ...incoming/retention_list.xlsx --snapshot-date 2026-11-17 --dry-run` | `NO RETENTION FILE ... Nothing changed.`, exit 2 |
| `Get-FileHash` after the runs | exploratory.duckdb `7B396E42...6277D`, superr.duckdb `CB4077EE...A391D`; both equal the `phase7_prehash.json` values |
| `python scripts/phase7_protected_check.py --phase6` | prehash 218 files, 0 mismatches; phase6_prerun 146 entries, 0 unexpected, 1 expected; lock check PASS; RESULT PASS |

## What the tests cover (all synthetic, in `tmp_path`)
CSV and XLSX equality; blank status = UNKNOWN; bad status flagged; ambiguous, unmatched and team-unconfirmed rows queued with candidates; id-first matching and id/name mismatch; alias with and without evidence; rejected files and parameters; duplicates and conflicts; released/traded/unknown never confirmed available, and unauthoritative or unsourced AUCTION_AVAILABLE not confirmed; idempotent re-import (tables, manifest, raw copy); byte-exact original with SHA-256; dry run writes nothing; injected failure rolls back and removes the copy; manual resolution with resolver, evidence, timestamp, log, refusals; historical stand-in table and file unchanged (row count and hashes); official DB refused as store; real reference loads read-only (1,217 players, 10 franchises); availability excludes RETAINED, sorted by name, conflict handling, newest snapshot wins, header-only without a list; admin endpoints 401 without or with a wrong token and 503 without configuration, with nothing written; CLI exit codes 2, 1, 0; procedure with and without a file; static check that no scoring, ranking, eligibility or public module references the retention modules.

## Deliverables
`backend/data/reports/retention_list_import_guide.md`, `retention_import_validation_report.md`, `candidate_availability.csv` (header only), `candidate_availability_manifest.json`, `retention_import_run_report.md`; `backend/config/retention_aliases.csv` is not created (optional file; the importer treats absence as no aliases).

## Not done / open
* No real retention data; real import is 0 rows.
* `rr_gap_tags` column from the plan is not in `candidate_availability.csv` (chunk 4 output did not exist when this chunk ran).
* Browser access to the POST admin routes needs a CORS or proxy decision.
