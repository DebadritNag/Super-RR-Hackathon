# Submission readiness audit (Phase 9)

Stamp (UTC): 2026-11-18T13:31:34+00:00.

## 1. Verdict

10 batters and 10 bowlers are listed in order with evidence, uncertainty and a status label. Label earned: EXPLORATORY. Split-half reliability: batters 0.019, bowlers 0.319 against 0.5 needed for PROVISIONAL. The lists are not claimed as validated or provisional rankings.

## 2. Deliverable checklist

| deliverable | content | state |
|---|---|---|
| pressure_batters_top10.csv | Top 10 batters (ordered, status-labelled) | present |
| pressure_batters_top10.json | Top 10 batters, JSON | present |
| pressure_bowlers_top10.csv | Top 10 bowlers (ordered, status-labelled) | present |
| pressure_bowlers_top10.json | Top 10 bowlers, JSON | present |
| pressure_top10_status.md | Status and label definitions for both lists | present |
| submission_methodology.md | Methodology report (Phase 9) | present |
| submission_executive_summary.md | One-page plain-English summary | present |
| methodology_comparison.md | Comparison of the three approaches (Phase 9 section + Phase 8) | present |
| pressure_methodology_research.md | What was tried, what failed, why (with Phase 9 notice) | present |
| player_selection_explanations.md | Why selected and why not selected, per player | present |
| descriptive_batter_profiles.csv | Descriptive batter profiles, window to 2026-11-01 | present |
| descriptive_bowler_profiles.csv | Descriptive bowler profiles, window to 2026-11-01 | present |
| ai_pipeline_verification.md | Audit of the p9 AI/ML pipeline | present |
| submission_test_report.md | Real test, lint and build outputs | present |
| submission_readiness_audit.md | Deliverable checklist and open items | written by this run |
| final_submission_summary.md | Summary for the owner | present |
| phase9_owner_decisions.md | Owner decisions D1 and D2 | present |
| phase9_lock_release_log.json | Append-only record of the TEST release | present |
| phase9_comparison.md | Phase 8 against Phase 9 | present |
| phase9_build_manifest.json | Input hashes, output provenance, versions | written by this run |

The same files, plus a SHA-256 manifest and the `phase8/` copies, are in `d:/Data/submission/`.

## 3. Verification state

- pytest: 1483 passed, 4 warnings in 872.52s (0:14:32).
- ruff check exit 0, ruff format exit 0, npm build exit 0, npm lint exit 0.
- Protected files: {"checked": 35, "ok": true, "phase8_copies_checked": 18, "phase8_copies_identical_to_pre_phase9": true}.

## 4. What is incomplete or weak

1. **Label.** EXPLORATORY: reliability thresholds for PROVISIONAL were not met; this is stated in every list.
2. **Pressure definition not validated.** P4 is the best available.
3. **No pristine hold-out.** 2026 is included by owner decision D1; the 2026 model check is not an independent test.
4. **2026 data rest on an owner attestation**, not an official verification (36 of 42 late-dated T20I matches consistent across sources, 6 single-source, 0 conflicts).
5. **Also done in Phase 9:** API source switch (`SUPERR_SUBMISSION_SOURCE`, Phase 9 by default), frontend status-word removal (decision D2), README update and bundle refresh; details in `.agents/tasks/phase9_chunk2_verification.md`.
6. **Window floor.** The floor named `min_matches_2025_window` is applied to the 2025-2026 window; a calendar-2025-only variant was not run.

## 5. Owner actions

1. Restart the backend on port 8000 (and reload the dashboard) so it serves the Phase 9 data.
2. Optionally verify the 42 late-dated T20I matches against an official source.
