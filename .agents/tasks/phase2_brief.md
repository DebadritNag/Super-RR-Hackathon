All four decisions are confirmed. Proceed with Phase 2: DuckDB schema design and idempotent official CSV ingestion.

1. Use `updated_ball_by_ball.csv` as the authoritative delivery-level dataset. Retain the original `ball_by_ball.csv` for comparison and provenance.

2. Skip `matches 2026.csv` and all `*_stats2026.csv` files from the primary ingestion. The official competition CSVs remain the source of truth.

3. Cricsheet is restricted to validation and supplementary historical context. Do not add Cricsheet-only matches or deliveries to the official competition rankings.

4. Use configurable IPL/T20I weighting, with 70% IPL and 30% T20I as the provisional default. Run the specified sensitivity tests and retain separate format-specific scores.

Additional requirements:

- Preserve all unresolved data-quality issues.
- Do not silently remove duplicate playing XI records.
- Do not classify innings 3 and 4 as Super Overs without verification.
- Do not assume meanings for `other` and `Penalty` extras.
- Keep source provenance for every imported record.
- Make ingestion idempotent and transactional where possible.
- Validate primary keys, foreign keys, row counts, and match reconciliation.
- Write tests and run the complete test suite before declaring Phase 2 complete.

First show me the proposed DuckDB schema and ingestion plan. Then implement it, run the ingestion, and report actual results, errors, and validation outcomes. Do not proceed to pressure-ranking calculations yet.
