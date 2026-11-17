# Phase 2 review: DuckDB schema and official CSV ingestion

DuckDB schema and transactional, idempotent ingestion of the official CSVs, built per the brief and plan. The scope is correct and every reported number is backed by raw output in the verification file. The one cross-check I made (legal-ball rule) matched the code. **Verdict**: APPROVED

Watch for: no blocking concerns. The OPEN data-quality items are preserved by design. The sensitivity grid for decision 4 is not defined in the brief, and the coder says so openly (confirmed).

## High-level view

Scope held. The work covers the schema, ingestion, validation and tests only. There is no Cricsheet load, no pressure or ranking calculation, and no API or frontend. The two Cricsheet OPEN items are carried over from Phase 1 as constants and labelled as such.

The honesty evidence is strong. The verification file holds raw outputs for the first load (run 1, SUCCESS), the second load (NO_CHANGE), `verify_database.py` (45 PASS, 0 FAIL), pytest (58 passed), ruff check and ruff format. The counts in the user summary match this output: 141, 353, 883, 28,381, 6,413 and 200,999. The extras_type distribution and the original-vs-updated difference counts also match. The summary says `--force` was not run against the project database and points to the test that covers it, which is an honest disclosure.

User decisions are all implemented, based on the code and the test names.
- `updated_ball_by_ball.csv` feeds `deliveries` and `innings`. The original is kept raw, with comparison tables.
- `matches 2026.csv` and the three `*_stats2026.csv` files are `SKIPPED_BY_DECISION` in lineage, with hash and row count only.
- The 0.70/0.30 weights are validated in config and stored in `model_versions` (`test_weights_*`, `test_model_versions_and_metric_definitions`). No sensitivity calculation was run.
- Innings 3 and 4 get `innings_role_status = UNVERIFIED`, and no `is_super_over` column exists. The verifier checks both.
- `extras_type` is stored verbatim, with `extras_label_unverified` for `other` and `Penalty`. The legal-ball rule is `extras_type IS NULL OR NOT IN ('wide','Overstep','other')`. `batter_runs` is stored, and `has_extra` is kept for the `'None'` string.
- The 75 duplicate playing-XI rows in 35 groups are preserved, and `squad_row_no` is part of the key. Players are not merged by name (7 shared names flagged).
- Provenance columns are present on every record.
- The load runs in one transaction with rollback, a FAILED run recorded, and an `ingestion_errors` table. Idempotency uses sha256 hashes plus `--force`.
- 26 foreign keys are enforced with orphan counts. Deliberate non-FK relations carry check rows.
- All Phase 1 issues are stored as OPEN `data_quality_results` rows with recomputed counts, and the original data files were verified unmodified.

The required tests are present. They cover idempotency, rollback, header mismatch, non-numeric keys, duplicate playing XI, extras, the innings 3/4 status and the real-data load.

## Issues (non-blocking)

1. **Sensitivity grid undefined** (confirmed). Only the weight configuration is stored, since the grid is not specified and calculations are barred. Define the grid before Phase 3.
2. **NO_CHANGE skips revalidation** (confirmed). Use `--validate-only` to refresh the reports.
3. **Cricsheet OPEN counts hard-coded** (confirmed). They are carried from Phase 1 and labelled as such.
4. **Drop-and-recreate instead of row-level replace** (confirmed). This is justified by the DuckDB FK limitation and covered by regression tests.
