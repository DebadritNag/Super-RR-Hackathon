# Retention list import guide

Status: tooling ready. **No official retention list has been received.** The list is expected on 17 November 2026. Nothing in this repository is, or may be mistaken for, real retention data.

Availability is descriptive context. It never changes a pressure score, eligibility decision, data-weight gate or capped status, and retained players stay in every historical training and analysis table. Retention only changes the final availability-aware candidate output.

## 1. Accepted files

`.csv` (UTF-8) or `.xlsx` (first sheet unless `--sheet`). Maximum 10 MB. Header names are case-insensitive; spaces count as underscores.

| Meaning | Accepted header names | Required |
|---|---|---|
| Player name | `player`, `player_name`, `name` | name or id |
| Stable player id | `player_id`, `id` | name or id |
| Team | `team`, `franchise` | recommended (needed for RETAINED/TRADED) |
| Status | `status` | no (blank = `UNKNOWN`) |
| Source / reference | `source`, `reference`, `source_reference` | no (falls back to `--source`) |
| Notes | `notes`, `note` | no |

Allowed statuses, exactly: `RETAINED`, `RELEASED`, `TRADED`, `AUCTION_AVAILABLE`, `UNKNOWN`. Accepted spellings: `retain`, `release`, `trade`, and spaces or hyphens in place of underscores (for example `auction available`). Any other text becomes `UNKNOWN` with the flag `STATUS_UNRECOGNISED`. A status is never guessed, and `AUCTION_AVAILABLE` is never derived from `RELEASED`, `TRADED`, `UNKNOWN` or a missing row.

## 2. How players are matched

1. A stable `player_id` is matched first. It must exist in the official `players` table. If a name is also given and does not belong to that id, the row is `AMBIGUOUS` (`ID_NAME_MISMATCH`). An unknown id is `UNMATCHED` and there is no fallback to the name.
2. Without an id, the name is normalised (whitespace, case, accents, dots, hyphens) and compared with the official names and variants. The match is accepted only when exactly one player has that name **and** that player has appeared for the stated team in the official mapping.
3. Several players with the name: `AMBIGUOUS`, with all candidates listed. A single player without history for the stated team: `AMBIGUOUS` (`NAME_UNIQUE_TEAM_NOT_CONFIRMED`), one suggested candidate, to be confirmed by a person.
4. An alias is used only when `backend/config/retention_aliases.csv` (`alias,player_id,evidence`) holds a row with non-empty evidence. The row records `match_method = ALIAS` and the evidence.
5. No fuzzy matching. No id is ever guessed.

Ambiguous and unmatched rows go to the manual-review queue (table `p7_retention_review`, file `backend/data/reports/retention_review_queue.csv`) and the player stays unresolved until a person decides.

## 3. Manual resolution

Each decision records resolver, evidence and timestamp (`p7_retention_review`, `p7_retention_resolution_log`).

* Resolve: `POST /api/v1/internal/retention/review/{id}/resolve` with `{"resolver": "...", "evidence": "...", "player_id": 123}`. The row becomes `RESOLVED_MANUAL`.
* Dismiss: same route with `{"resolver": "...", "evidence": "...", "dismiss": true}`. The row stays unresolved.
* List open items: `GET /api/v1/internal/retention/review`.

All admin routes need the header `X-Admin-Token` (value of `SUPERR_ADMIN_TOKEN`). Missing or wrong token: HTTP 401; no token configured on the server: HTTP 503.

## 4. Preview before import (dry run)

* CLI: add `--dry-run`. Nothing is written, no file is copied.
* API: `POST /api/v1/internal/retention/preview?filename=list.xlsx&snapshot_date=2026-11-17&source=...` with the raw file as the request body (content type `application/octet-stream`). Returns each row with its mapping, flags and review reason. `.../import` uses the same parameters and writes.

## 5. What an import stores

* The original file is copied to `backend/data/raw/retention/<sha12>_<name>`; `import_manifest.json` in that folder lists SHA-256, snapshot date, source and time.
* Tables in `exploratory.duckdb` (never the official database): `p7_retention_imports`, `p7_retention_rows`, `p7_retention_review`, `p7_retention_resolution_log`.
* One transaction per import; a failure rolls back and removes the copy.
* Idempotent: importing a file with a hash already stored changes nothing and reports `ALREADY_IMPORTED`.
* A later file with another hash is a new snapshot. The newest snapshot (by `--snapshot-date`, then import order) drives the availability output. Earlier snapshots are kept.
* Duplicates stay side by side and are flagged `DUPLICATE_ROW`; different statuses for one player are flagged `CONFLICTING_STATUS` and the player shows as `CONFLICT`, never as available.

Importing writes to `exploratory.duckdb`, so its file hash will change on the first real import. That is expected and is the only change. The official database and the historical tables are not touched.

## 6. Availability rules

* `RETAINED`: excluded from `candidate_availability.csv`. Rows of the list that are still unresolved may name retained players who are not yet excluded; the manifest states the count and a warning.
* `confirmed_available = True` only when all of these hold: status `AUCTION_AVAILABLE` stated in the file, player mapped, a source on the row or in `--source`, the import marked `--authoritative` (which requires `--verification OFFICIAL_VERIFIED`), and no conflict.
* `RELEASED`, `TRADED`, `UNKNOWN` and players not in the file keep their own status and are not confirmed available.
* Output rows are sorted by player name. No score, rank or order of merit exists in the file.

## 7. One-command procedure for 17 November

Replace the path, source text and date with the real ones. Run from `d:\Data\backend`:

```powershell
$env:PYTHONUTF8 = 1
python scripts/run_retention_procedure.py --file "d:\Data\backend\data\incoming\retention_list.xlsx" --snapshot-date 2026-11-17 --source "<official document or URL>" --verification OFFICIAL_VERIFIED --authoritative
```

Use `--verification SINGLE_SOURCE` or `UNVERIFIED` and omit `--authoritative` if the list is not an official document. Steps: import, write `retention_import_run_report.md` and `retention_review_queue.csv`, regenerate `candidate_availability.csv` and `candidate_availability_manifest.json`. Review the queue, resolve items, then rebuild with `POST /api/v1/internal/retention/availability/rebuild` or rerun the command (rerun is safe).

Without a file the same command prints `NO RETENTION FILE YET`, writes a header-only `candidate_availability.csv`, and exits 0.

Single steps: `python scripts/import_retention_list.py --file <path> --snapshot-date <date> [--dry-run]` (exit 0 ok, 1 invalid file or parameters, 2 file not found).

## 8. What it never does

It never invents or infers a retention list, never uses the pre-retention squad file as availability, never changes a pressure score, rank or eligibility, never removes a player from historical data, and never writes to the official database.

## 9. Notes for the frontend

The admin routes are POST routes behind the token. The API's CORS policy currently allows `GET` only, so a browser page calling preview/import/resolve needs a same-origin proxy or a CORS change. That change was not made here because it alters the public API surface.
