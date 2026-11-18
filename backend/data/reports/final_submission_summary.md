# Final submission summary (Phase 8)

Generated 2026-11-18T06:14:05+00:00. Criteria SHA-256 `9258aa6d42ef72da578d2950d161f265c064016d6b04e095f37c4e2e8bf82b64`.

## Methodologies implemented

- **A, context-adjusted performance:** player-blind gradient-boosting expectation of runs and wicket per ball, residuals weighted by a continuous pressure intensity, REML shrinkage, match-cluster bootstrap.
- **B, leverage and win probability added:** calibrated win-probability models (first innings and chase), explicit attribution rules, WPA above what the leverage predicts.
- **C, Pressure Response Index:** components A, B and consistency weighted by data-derived reliability on fitting matches, evaluated on held-out matches.

## Which performed best and why

Selection followed the predeclared rule. Batters: approach A (split-half 0.057, out-of-time lower bound 0.017); A and C are tied within 0.001 and the choice is not a performance difference. Bowlers: approach C (split-half 0.267, out-of-time lower bound 0.027). Approach B was weakest (split-half 0.042 for batters, -0.135 for bowlers). No approach passes the PROVISIONAL threshold of 0.5 or the 0.5 data-weight gate.

## Are the Top 10 lists available, and with what status

Yes: 10 batters and 10 bowlers, ordered, none padded. Both lists, and every row, are **EXPLORATORY**; model validation status is also EXPLORATORY. The submitted ranking status and the model validation status are kept apart in the files.

**Batters:** 1. Suryakumar Yadav; 2. Tim David; 3. Heinrich Klaasen; 4. Romario Shepherd; 5. Andre Russell; 6. Tristan Stubbs; 7. David Miller; 8. Rinku Singh; 9. Nicholas Pooran; 10. Mark Chapman.

**Bowlers:** 1. Matheesha Pathirana; 2. Kuldeep Yadav; 3. Jasprit Bumrah; 4. Varun Chakravarthy; 5. Sunil Narine; 6. Akeal Hosein; 7. Rashid Khan; 8. Mohammad Nawaz; 9. Wanindu Hasaranga; 10. Abbas Afridi.

## Headline evidence

**Batters**

| rank | player | pressure matches | pressure balls | pressure level | normal baseline | difference | top-10 probability |
|---|---|---|---|---|---|---|---|
| 1 | Suryakumar Yadav | 72 | 1247 | 0.118 | 0.064 | 0.054 | 91% |
| 2 | Tim David | 74 | 961 | 0.115 | 0.223 | -0.107 | 83% |
| 3 | Heinrich Klaasen | 48 | 870 | 0.096 | 0.095 | 0.001 | 60% |
| 4 | Romario Shepherd | 53 | 613 | 0.116 | -0.326 | 0.442 | 63% |
| 5 | Andre Russell | 57 | 785 | 0.096 | n/a | n/a | 52% |
| 6 | Tristan Stubbs | 46 | 763 | 0.086 | -0.128 | 0.215 | 42% |
| 7 | David Miller | 65 | 1068 | 0.070 | -0.062 | 0.132 | 33% |
| 8 | Rinku Singh | 63 | 966 | 0.072 | 0.025 | 0.047 | 31% |
| 9 | Nicholas Pooran | 70 | 1130 | 0.066 | 0.083 | -0.018 | 23% |
| 10 | Mark Chapman | 32 | 503 | 0.103 | -0.038 | 0.141 | 41% |

**Bowlers**

| rank | player | pressure matches | pressure balls | pressure level | normal baseline | difference | top-10 probability |
|---|---|---|---|---|---|---|---|
| 1 | Matheesha Pathirana | 46 | 930 | 0.089 | -0.015 | 0.096 | 86% |
| 2 | Kuldeep Yadav | 64 | 973 | 0.121 | 0.024 | 0.089 | 56% |
| 3 | Jasprit Bumrah | 51 | 636 | 0.142 | 0.054 | 0.080 | 56% |
| 4 | Varun Chakravarthy | 69 | 999 | 0.093 | 0.039 | 0.045 | 45% |
| 5 | Sunil Narine | 48 | 713 | 0.103 | 0.008 | 0.087 | 57% |
| 6 | Akeal Hosein | 47 | 486 | 0.083 | -0.017 | 0.092 | 54% |
| 7 | Rashid Khan | 88 | 1340 | 0.055 | 0.066 | -0.018 | 27% |
| 8 | Mohammad Nawaz | 40 | 467 | 0.088 | 0.004 | 0.075 | 49% |
| 9 | Wanindu Hasaranga | 70 | 1069 | 0.051 | 0.042 | 0.001 | 14% |
| 10 | Abbas Afridi | 19 | 223 | 0.139 | 0.022 | 0.108 | 44% |

## Limitations

The data do not reliably separate players on pressure performance (Phase 6 finding, confirmed with a richer method); the pressure definition is unvalidated; the Top 10 membership moves with the definition and the shrinkage assumption; IPL and T20I results do not agree enough to combine; the 2026 matches are unused. See methodology section 13.

## Phase 6 findings

Between-player variance at the shrinkage floor in all 48 contexts; pooled odd/even reliability 0.37 (0.3656), median 0.25; 0 of 48 contexts pass the 0.5 data-weight gate; no definition passed the predeclared criteria. None of these gates or the shrinkage method was changed.

## Does the AI pipeline genuinely train and predict?

Yes. 9 versioned artefacts exist in `backend/data/models/`. Retraining the batter-runs and bowler-wicket models from scratch on TRAIN reproduced the stored artefacts exactly (maximum prediction difference 0.0), and the win-probability chase model re-scored on 20,040 validation deliveries gives Brier 0.1167 against 0.2506 for a constant. Gains of the expected-outcome models over a constant are 1.5% to 3.1%. Predictions come from the stored artefacts. The experimental Top 10 files are served only by the token-protected route and are labelled EXPERIMENTAL_NOT_VALIDATED; their split-half reliability is about 0.2. Technical success is not reliability.

## Tests

`python -m pytest -q`: not recorded (passed 0, failed 0, errors 0). `ruff check .` exit 0; `ruff format --check .` exit 0; `npm run build` exit 0; `npm run lint` exit 0. Protected files: {"checked": 234, "ok": true, "unexpected_changes": [], "documented_changes": [{"file": "d:/Data/backend/data/reports/phase7_model_registry.json", "state": "changed", "note": "intentional Phase 8 chunk 6 change: output keys renamed to the preserved *_phase7_aborted.csv names (content hashes of those files verified equal); see phase8_chunk6_verification.md"}]}. Details in `submission_test_report.md`.

## What remains incomplete

No validated or provisional ranking exists. The 2026 matches are unused. The 42 late-dated T20I matches are unverified. Frontend unit tests do not exist; the unlocked AI page and keyboard-only use were not visually verified. Full list in `submission_readiness_audit.md`.

## What the owner must do

1. Confirm the status-label wording (EXPLORATORY, with the plain-language banner).
2. Optionally verify the 42 late T20I dates against an official source.
3. Decide whether the 2026 matches may be used as a labelled non-pristine diagnostic.
4. Enter the two lists in the competition's dropdowns and check the required format of the methodology document.
