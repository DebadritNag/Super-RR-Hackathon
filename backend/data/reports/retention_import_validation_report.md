# Retention import validation report

**No official retention list has been received. Real import: 0 rows.** Every fixture below is synthetic, generated inside pytest `tmp_path` and labelled synthetic in the test files. No synthetic name or status was saved under `data/` or `exploratory.duckdb`. The committed `candidate_availability.csv` contains the header only and its manifest says `NO_RETENTION_FILE_YET`.

## What was tested (synthetic CSV and XLSX)

Test files: `tests/test_phase7_retention_import.py`, `tests/test_phase7_retention_api.py`, `tests/test_phase7_retention_no_scoring_link.py`.

| Behaviour | Test result basis |
|---|---|
| CSV and XLSX (openpyxl-built workbook) parse to identical results; names, teams and statuses normalised | parametrised test, both formats |
| Blank status gives `UNKNOWN`; unrecognised status gives `UNKNOWN` plus flag, never guessed | asserted |
| Ambiguous name (two players), unmatched name, unique name without team history all go to the review queue with no id assigned | asserted, including candidate ids and the review CSV export |
| Player id matched first; id/name mismatch, unknown id and invalid id are not resolved by name | asserted |
| Alias used only with evidence; alias row without evidence ignored; evidence stored on the row | asserted |
| Missing player column, wrong extension, bad verification, bad date, `authoritative` without `OFFICIAL_VERIFIED`, missing file are rejected | asserted |
| Duplicates and conflicting statuses kept side by side and flagged | asserted |
| `RELEASED`, `TRADED`, `UNKNOWN`, absent players never confirmed available; unauthoritative or unsourced `AUCTION_AVAILABLE` not confirmed | asserted |
| Idempotency: same file twice leaves all `p7_retention_*` rows, the manifest and the raw copy unchanged | asserted (table contents compared before and after) |
| Original file stored byte-for-byte; SHA-256 equals the manifest value | asserted |
| Dry run writes no database and no file | asserted |
| Transaction: failure mid-import rolls back every table and removes the file copy | asserted with an injected failure |
| Manual resolution records resolver, evidence, timestamp and log entry; empty evidence, unknown player id and double resolution are refused; dismissal leaves the row unresolved | asserted |
| Historical records unchanged: a stand-in historical table (row count and content hash) and a stand-in source file (SHA-256) identical before and after an import; only `p7_retention_*` tables are added | asserted |
| Official database refused as a store | asserted |
| Real reference data loads read-only (1,217 players, 10 franchises); database mtime unchanged | asserted against the real official database |
| Availability output excludes `RETAINED`, sorts by name, has no score or rank column, marks conflicts, keeps unlisted players `UNKNOWN`, uses the newest snapshot, is header-only with no list and creates no database | asserted |
| Admin endpoints (preview, import, review, resolve, rebuild) answer 401 with a missing or wrong token and write nothing; 503 when no token is configured; routes exist only under `/api/v1/internal/retention` | asserted |
| CLI: missing file exits 2 and changes nothing; invalid file exits 1; dry run exits 0 | asserted |
| One-command procedure: with no file exits 0 with the explicit `NO RETENTION FILE YET` state; with a synthetic file imports, reports and regenerates; rerun is idempotent | asserted |
| No scoring, ranking, eligibility, classification, service or public route module references the retention modules or tables | static test |

## Run without a file (real workspace)

`python scripts/run_retention_procedure.py` printed `NO RETENTION FILE YET`, wrote the header-only `candidate_availability.csv`, `candidate_availability_manifest.json` (state `NO_RETENTION_FILE_YET`) and `retention_import_run_report.md`, and exited 0. `exploratory.duckdb` and `superr.duckdb` SHA-256 values were identical before and after (`7b396e42...`, `cb4077ee...`).

## Not validated, and what remains when the real file arrives

* Real column layout and spelling of the official list. The importer accepts the header names in the guide; a different layout needs a header edit or a small alias addition, which a dry run will show.
* Real match rates: how many names map by id, by name with team history, or need review.
* Whether the source qualifies as `OFFICIAL_VERIFIED` (owner decision) and therefore may carry `--authoritative`.
* Manual review of every ambiguous or unmatched row, with evidence.
* Browser-side use of the admin routes (CORS allows `GET` only; see the guide).
* The first real import changes the `exploratory.duckdb` file hash, because that is where the `p7_retention_*` tables live.

## Exact command for the real file

```powershell
cd d:\Data\backend
$env:PYTHONUTF8 = 1
python scripts/run_retention_procedure.py --file "<path to the list>" --snapshot-date 2026-11-17 --source "<official document or URL>" --verification OFFICIAL_VERIFIED --authoritative
```

Preview first with `python scripts/import_retention_list.py --file "<path>" --snapshot-date 2026-11-17 --dry-run`.
