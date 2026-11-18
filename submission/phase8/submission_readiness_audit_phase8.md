# Submission readiness audit

Stamp (UTC): 2026-11-18T06:14:05+00:00.

## 1. Verdict

Ready to submit as an honestly labelled **exploratory** analysis: 10 batters and 10 bowlers are listed in order, each with evidence, uncertainty and a status label. Not ready to claim as a validated or provisional ranking, because no approach reached the declared reliability thresholds (batters 0.057, bowlers 0.267 split-half against 0.5 needed).

## 2. Deliverable checklist

| deliverable | content | state |
|---|---|---|
| pressure_batters_top10.csv | Top 10 batters (ordered, status-labelled) | present |
| pressure_batters_top10.json | Top 10 batters, JSON | present |
| pressure_bowlers_top10.csv | Top 10 bowlers (ordered, status-labelled) | present |
| pressure_bowlers_top10.json | Top 10 bowlers, JSON | present |
| pressure_top10_status.md | Status banner and label definitions for both lists | present |
| submission_methodology.md | Methodology report | present |
| submission_executive_summary.md | One-page plain-English summary | present |
| methodology_comparison.md | Comparison of the three approaches | present |
| pressure_methodology_research.md | What was tried, what failed, why | present |
| player_selection_explanations.md | Why selected and why not selected, per player | present |
| descriptive_batter_profiles.csv | Descriptive batter profiles (no composite, no rank) | present |
| descriptive_bowler_profiles.csv | Descriptive bowler profiles (no composite, no rank) | present |
| ai_pipeline_verification.md | Independent AI/ML pipeline audit | present |
| submission_test_report.md | Real test, lint and build outputs | present |
| submission_readiness_audit.md | Deliverable checklist and open items | written by this run |
| final_submission_summary.md | Final summary for the owner | present |
| phase8_build_manifest.json | Input hashes, output provenance, versions | written by this run |

The same files, plus a SHA-256 manifest, are copied to `d:/Data/submission/` by `scripts/run_phase8.py`.

## 3. Requirements check

| requirement | evidence | state |
|---|---|---|
| Top 10 batters, ordered, real data | 10 rows, rank 1 to 10, deterministic tie-break by player id | met |
| Top 10 bowlers, ordered, real data | 10 rows, rank 1 to 10 | met |
| Pressure definition and rationale | section 3 of the methodology | met (definition not validated) |
| Batter and bowler metrics, baselines, context adjustment | sections 4 to 6 | met |
| IPL against T20I comparison | section 7, per-format columns in both CSVs | met (combination unsupported) |
| Eligibility, shrinkage, uncertainty | sections 8 and 9 | met |
| Reliability validation | section 10, split-half, out-of-time, ICC | met; thresholds not reached |
| Sensitivity analysis | section 11 | met; Top 10 membership is sensitive |
| Player-level evidence and exclusions | `player_selection_explanations.md` | met |
| Phase 6 findings respected, no gate lowered | gate reported unchanged; no shrinkage change | met |
| Experimental AI kept separate | token-protected route, separate CSVs, banner | met |
| Frontend with ten navigation items | built and type-checked | met |

## 4. Verification state

- pytest: no output recorded.
- ruff check exit 0, ruff format exit 0, npm build exit 0, npm lint exit 0.
- Protected-file check: {"checked": 234, "ok": true, "unexpected_changes": [], "documented_changes": [{"file": "d:/Data/backend/data/reports/phase7_model_registry.json", "state": "changed", "note": "intentional Phase 8 chunk 6 change: output keys renamed to the preserved *_phase7_aborted.csv names (content hashes of those files verified equal); see phase8_chunk6_verification.md"}]}.

## 5. What is incomplete or weak

1. **No validated or provisional ranking.** Split-half reliability is below 0.5 for both roles and every interval includes 0. This is the central limitation and it is stated on every list.
2. **Pressure definition not validated.** The monotonic trend test fails for all seven candidates; P4 is the best available.
3. **IPL and T20I not combinable by the declared rule.** The combined estimate is labelled unsupported.
4. **Bowler index is a consistency share.** Components A and B received zero weight by the data-derived rule.
5. **2026 matches unused.** The period was opened once earlier and is not pristine; using it needs an owner decision.
6. **42 late-dated T20I matches** remain excluded and unverified against an official source.
7. **AI audit depth.** Two of eight expected-outcome models were refit from scratch and the win-probability bundle was re-scored; the other six were checked for existence, metadata and loading only.
8. **Frontend checks.** No unit tests. Not visually verified: the unlocked AI page, keyboard-only use, automated contrast. The linter reports warnings (see the test report).
9. **Reproducibility of the timing columns.** Test durations vary between runs; every ranking, table and hash in the reports does not.

## 6. Owner actions

1. Confirm the wording of the status labels and banners.
2. Decide whether to apply the 2026 matches as a labelled, non-pristine diagnostic.
3. Optionally verify the 42 late-dated T20I matches against an official source.
4. Enter the two lists in the competition's selection form and check the document format required for the methodology report.
