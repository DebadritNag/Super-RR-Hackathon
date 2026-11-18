# Phase 9 summary

## What changed
- All 2026 matches (IPL 74, T20I 70, including the 42 late-dated T20I matches) are now in scoring and training, by owner decision D1 (owner attestation, not third-party verification; cross-source check: 36 of 42 consistent, 6 single-source, 0 conflicts). The TEST lock was released with a logged RELEASE record (`phase9_lock_release_log.json`). No pristine hold-out remains.
- Window is 2022-01-22 to 2026-11-01. 137 of the 144 2026 matches contribute scored deliveries (31,996 of 33,086 deliveries); 40 of the 42 late T20I matches contribute. The rest are removed by the existing restrictions (unreconstructable DLS, innings 3/4 and Super Over, out-of-scope competition).
- "EXPLORATORY" was removed from the frontend (decision D2).

## Training scheme
Expected-outcome GBMs (8) and win-probability models W1/W2 were refitted on matches to 2025-12-31 with the Phase 8 hyperparameters (no new tuning). 2026 balls are scored by those fits; earlier balls are scored out of fold (`match_id % 5`), so no ball is scored by a model that saw its own match. Artefacts are `p9_*` (p8_* untouched).

## 2026 out-of-time check (data previously held out, released by owner decision; nothing tuned on it)
Gain vs constant: batter runs 1.7%, wicket 1.7%, dot 3.2%, boundary 3.1%; bowler runs 1.6%, wicket 1.5%, dot 3.2%, boundary 3.1%. Calibration slopes 0.91 to 0.98 for the binary models. W1 Brier 0.239 vs 0.252 constant, slope 0.621, which fails the declared 0.8 to 1.2 gate, so first-innings win-probability credit is withheld under the unchanged Approach B rule. W2 Brier 0.123 vs 0.254, slope 1.076, gate passed.

## Reliability and the label each list earned
Criteria file unchanged (SHA-256 `9258aa6d...b82b64`). Labels are what the thresholds give.
| role | approach | split-half | interval | out-of-time lower bound | label earned |
|---|---|---|---|---|---|
| batter | A | 0.019 | -0.184 to 0.359 | -0.054 | EXPLORATORY |
| bowler | C | 0.319 | -0.107 to 0.386 | 0.059 | EXPLORATORY |

Both lists are still EXPLORATORY in the data, CSV/JSON and reports: PROVISIONAL needs split-half of at least 0.5 and VALIDATED at least 0.7. They are not validated rankings; the frontend simply no longer shows the word.

## Top 10 (Top-10 probability; 95% rank intervals are in the CSV columns `rank_interval_low`/`rank_interval_high`)
Batters (A): 1 Suryakumar Yadav 88%; 2 Tim David 87%; 3 Heinrich Klaasen 51%; 4 David Miller 38%; 5 Rinku Singh 38%; 6 Andre Russell 51%; 7 Romario Shepherd 54%; 8 Tristan Stubbs 38%; 9 Shreyas Iyer 30%; 10 Shivam Dube 16%.
Bowlers (C): 1 Sunil Narine 98%; 2 Matheesha Pathirana 86%; 3 Kuldeep Yadav 64%; 4 Jasprit Bumrah 70%; 5 Varun Chakravarthy 51%; 6 Abrar Ahmed 48%; 7 Rashid Khan 17%; 8 Akeal Hosein 35%; 9 Wanindu Hasaranga 20%; 10 Mohammad Nawaz 36%.

## Phase 8 vs Phase 9
- Batters: 8 of 10 shared; Shreyas Iyer and Shivam Dube entered, Nicholas Pooran and Mark Chapman left; Spearman over shared players 0.619. Split-half 0.057 to 0.019.
- Bowlers: 9 of 10 shared; Abrar Ahmed entered, Abbas Afridi left; Narine moved from 5 to 1; Spearman over shared players 0.800. Split-half 0.267 to 0.319.
- Details: `phase9_comparison.md`. Phase 8 outputs are kept as `*_phase8.*`.

## Frontend
No occurrence of "exploratory" (any case) remains in `frontend/src`; ranking-status banners and pills were removed as per D2, and evidence displays (Top-10 probability, rank intervals, sample sizes, reliability figures) remain. Not visually verified in a browser in this step (build, lint and the API check only).

## Tests actually run (fresh, this step)
pytest 1483 passed; ruff check and format check clean; npm build passed; npm lint 0 errors, 3 pre-existing warnings; `check_frontend_api.py` 21 of 21 on port 8010. Details in `.agents/tasks/phase9_verification.md`.

## Files changed
New: `phase9.duckdb`, `p9_*` model artefacts, `phase9_owner_decisions.md`, `phase9_lock_release_log.json`, `phase9_comparison.md`, `phase9_build_manifest.json`, `phase9_summary.md`, `*_phase8.*` copies. Regenerated: pressure Top-10 csv/json, `pressure_top10_status.md`, descriptive profiles, experimental AI csvs, methodology and submission docs, `README.md`, `submission/` bundle and its SHA-256 manifest, frontend source.

## Owner to-dos
- Restart the backend on port 8000 to serve the Phase 9 data; I did not touch your running processes.
- If you run the Phase 8 tests in a shell with `SUPERR_PHASE=phase9` set, six of them fail by design; unset it.
- Be aware the 2026 check is not independent (no hold-out remains), and the 2026 data rest on your attestation.
