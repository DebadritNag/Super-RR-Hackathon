# Chunk 4 review: classification, selection, uncapped rankings, API, docs

**Verdict**: APPROVED

Chunk 4 adds player classification with per-field provenance, a header-only validated override loader, an exact DP selection optimiser, six presets, uncapped filters and rankings, profile data, a FastAPI /api/v1 layer and two docs. The verification file records 488 tests passing, ruff check and format clean, unchanged superr.duckdb hash, and independent pandas spot checks. Watch for: with no cap source in the data, every verified-uncapped ranking and preset is empty or POOL_TOO_SMALL (confirmed); this is the honest outcome and not a defect.

## High-level view
Nationality and international status are independent fields, each with its own verification status. Capped is derived only from T20I appearances and labelled DERIVED_FROM_OFFICIAL_T20I_APPEARANCES. Uncapped is never derived (classification.py header), so verified Uncapped is 0. Nothing is fabricated: unresolved and ambiguous names stay Unknown.

Uncapped rankings filter the same experimental frame produced in Chunk 3 (uncapped.py header: filters never recompute scores or thresholds). Scores carry EXPERIMENTAL_NOT_VALIDATED. The API refuses official requests with 403 (deps.refuse_official on the public router; body.official checked on POST routes). Admin routes require a token compared with hmac.compare_digest (503 if unset, 401 on mismatch). No frontend files exist in the backend tree.

The optimiser is checked against brute-force enumeration and returns infeasibility explanations instead of padding.

## Evidence check
Verification file present with commands, counts and six independent spot checks. I did not re-run suites. I spot-checked deps.py, routes.py, classification.py, views.py and searched the backend tree for frontend file types (none).

## Issues (non-blocking)
1. Squad file has 25 unresolved and 2 ambiguous names, kept Unknown. A verified cap list keyed by player_id is needed from the user (confirmed).
2. standardised_score uses the eligible-pool mean and sd of the pre-test table, not train-only parameters. No test outcome is involved. Record as an open decision (confirmed, disclosed).
3. Profile descriptive stats do not exclude DLS rows. Disclosed in the restrictions column (confirmed).
4. Admin protection is a single shared token, acceptable for this phase (confirmed).
5. Overseas nationality is DERIVED from national-team evidence, labelled as such, and a verified-only basis treats it as Unknown (confirmed).
