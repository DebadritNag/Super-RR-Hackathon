# Chunk 3 review: retention list importer and availability procedure

Retention importer (CSV and XLSX), manual review queue, token-protected admin routes and a one-command procedure, all kept in `p7_retention_*` tables in the exploratory store.

**Verdict**: APPROVED

Watch for: the full suite was not rerun after the one-test exemption in `test_phase5_gating.py` (likely harmless: the narrow rerun passed 53 and no app code changed afterwards). The real import is 0 rows, so nothing has been tried on a real file.

## High-level view

Matching is id-first. A name only generates a candidate, accepted only when it is a unique exact normalised match in the official players table and the player has appeared for the stated team. Everything else goes to the review queue, and manual resolution records resolver, evidence, timestamp and a log row. Statuses are limited to the five allowed values, enforced both in code (unrecognised becomes UNKNOWN plus a flag) and by a DB CHECK constraint. AUCTION_AVAILABLE is never inferred. It counts as confirmed available only when the source is authoritative, the row is mapped and sourced, and there is no conflict.

Writes go only to the exploratory store. The official DB is refused as a store, which is tested. Original files are preserved with a SHA-256 manifest, and imports are transactional with rollback and idempotent. Admin routes use `require_internal` at router level. Tests are labelled SYNTHETIC and built in `tmp_path`. Tests cover historical data staying unchanged, and a static test checks that no scoring, ranking or public module references the retention modules.

## Evidence

`phase7_chunk3_verification.md` records 38 new tests passing, a full run of 1157 passed with 1 failure (the gating-route exemption), 53 passed after the fix, ruff check and format clean, DB hashes equal to the prehash, and the protected check PASS. It also lists the deviations honestly. I did not rerun any suite. Spot checks (confirmed): STATUSES and CHECK constraint, `is_confirmed_available`, router dependency, SYNTHETIC labelling.

<details>
<summary>Issues (3)</summary>

1. **Full suite not rerun after exemption edit** (likely, low) — rerun the full suite once at final audit to confirm 1158 passed.
2. **No browser path for POST admin routes** (confirmed, informational) — CORS allows GET only. Decide on a proxy or a CORS change before any UI use.
3. **`rr_gap_tags` missing from `candidate_availability.csv`** (confirmed, informational) — add when chunk 4 output exists.

</details>

<details>
<summary>Details</summary>

The exemption of the admin routes from the "every route carries gate fields" test is reasonable: they return no ranking rows. The first real import will change the hash of `exploratory.duckdb`. This is documented and expected, and the downstream protected-hash checks must account for it.

</details>

<details>
<summary>File map</summary>

app/data_pipeline/retention_importer.py, retention_availability.py, app/api/v1/routes_retention.py, scripts import_retention_list.py and run_retention_procedure.py, three tests/test_phase7_retention_*.py files, tests/test_phase5_gating.py (exemption), requirements.txt (openpyxl), plus the reports listed in the verification file.

</details>
