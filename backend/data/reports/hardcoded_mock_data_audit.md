# Hardcoded / mock data audit (backend section)

Scope of this section: `backend/app/**` (routes, services, analytics, schemas) and `backend/scripts/**`. Frontend entries are added later in Phase 7 chunk 6.

How it was checked (executed in Phase 7 chunk 1):
- A scan of every `app/**/*.py` file for (a) each of the 257 player names in `ipl squad.csv` as a quoted literal, (b) random or mock generators (`random.*`, `np.random.rand/choice/...`, `faker`, `MOCK_`, `DEMO_`, `fake_`, `dummy_`, `lorem`), (c) hard-coded rank or score literals and top-10 array literals.
- A grep of `scripts/*.py` for the same random and mock tokens.
- The scan is now a permanent test: `backend/tests/test_phase7_no_mock_in_production.py` (5 tests, includes a self-check that the patterns fire on planted violations).

Result: **no hardcoded player names, rankings, scores, predictions, random scores, demo fixtures or mock fallbacks were found in backend production paths. Nothing needed removal.**

| Path | What it is | Decision |
|---|---|---|
| `app/analytics/baseline_engine.py`, `confidence_engine.py`, `pressure_eligibility.py`, `phase4/engine.py`, `phase4/shrink.py`, `phase5/reliability.py`, `phase6/definition_compare.py`, `phase6/split_half.py` | `np.random.default_rng(seed)` / `SeedSequence(seed)` for seeded bootstrap and split-half resampling (seed 20260512 family). Not score generation. | Retained; allow-listed by pattern in the test (only `default_rng`/`SeedSequence` pass, `rand`, `choice`, `normal`... fail) |
| `app/main.py`, `app/services/phase4_service.py` (`gate_inputs`) | Constructor argument that lets tests inject synthetic gate states. Not reachable from environment or request. | Retained (documented in code) |
| `app/phase4/eligibility.py` (`PLACEHOLDERS`, `LABEL_FALLBACK`) | Phase 3 placeholder thresholds kept as labelled candidates; a named fallback label. | Retained (methodology constants, labelled) |
| `app/phase4/baseline.py`, `app/analytics/pressure_features.py` (fallback to coarser cells) | Documented baseline hierarchy fallback, part of method B0. | Retained |
| `app/phase4/uncapped.py`, `app/schemas/phase5.py` (`VERIFIED_UNCAPPED`) | Disabled placeholder value; never an established status. | Retained |
| `config/phase4_selection_presets_v1.json` served by `GET /selection/presets` | Parameter templates, no player rows. | Retained |
| `scripts/phase5_dynamic_demo.py` | Name contains "demo", but it calls the real app over the real store and writes `phase5_dynamic_examples.json`; it holds no invented data. | Retained (historical Phase 5 script, not part of the serving path) |
| `app/phase4/*`, `app/phase5/*`, `app/schemas/*` mentions of "top 10" | Stability analysis and schema text about the list size; no stored player lists. | Retained |
| `tests/phase4_api_helpers.py` and other `tests/**` | Synthetic stores with names such as "Player 01" ... "Player 24". | Retained as test fixtures; clearly synthetic; outside `app/` |

Frontend: not covered here (the whole current frontend uses fabricated data; see the chunk 6 additions).
