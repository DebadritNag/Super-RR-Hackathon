# SupeRR Selector Season 2: Pressure Performance & Player Intelligence

Analysis of which IPL and T20I batters and bowlers perform best under pressure, built on the official ball-by-ball data supplied for SupeRR Selector Season 2 (Round 1).

The challenge asks for three things:

1. An ordered Top 10 of batters who perform best under pressure.
2. An ordered Top 10 of bowlers who perform best under pressure.
3. A methodology explaining how pressure is defined, how players are measured, why they were selected and how reliable the conclusions are.

This repository contains the full pipeline: data ingestion and auditing, a pre-delivery match-state engine, descriptive player profiles, three pressure methodologies compared under criteria fixed in advance, trained expected-outcome and win-probability models, the two Top 10 lists with uncertainty, a FastAPI backend and a React dashboard.

> **Status of the results.** Both Top 10 lists are labelled **EXPLORATORY**: they are the best-supported ordering the data allow, not a statistically validated ranking. The reasons are explained in [Reliability](#9-reliability-how-far-the-results-can-be-trusted). The label was earned under thresholds written down and hashed before any player was ranked.

---

## Contents

1. [Results](#1-results)
2. [Data](#2-data)
3. [Repository layout](#3-repository-layout)
4. [Running the project](#4-running-the-project)
5. [Descriptive player profiles](#5-descriptive-player-profiles)
6. [Defining pressure](#6-defining-pressure)
7. [How the pressure ranking was built](#7-how-the-pressure-ranking-was-built)
8. [How the models were trained](#8-how-the-models-were-trained)
9. [Reliability: how far the results can be trusted](#9-reliability-how-far-the-results-can-be-trusted)
10. [How the project evolved](#10-how-the-project-evolved)
11. [Limitations](#11-limitations)
12. [Testing and reproducibility](#12-testing-and-reproducibility)
13. [Key documents](#13-key-documents)

---

## 1. Results

Window: matches from 22 January 2022 to 19 December 2025 (the 2026 matches are held out, see [section 8](#8-how-the-models-were-trained)). Higher score is better. "Top-10 probability" is the share of 1,000 resamples of whole matches in which the player stays in the Top 10. The "rank interval" is the 95% range of the player's rank across those resamples.

### Top 10 batters under pressure (Approach A: context-adjusted performance)

| Rank | Player | Pressure innings | Pressure balls | Top-10 probability | Rank interval |
|---|---|---|---|---|---|
| 1 | Suryakumar Yadav | 72 | 1,247 | 91% | 1 to 17 |
| 2 | Tim David | 74 | 961 | 83% | 1 to 33 |
| 3 | Heinrich Klaasen | 48 | 870 | 60% | 2 to 42 |
| 4 | Romario Shepherd | 53 | 613 | 63% | 1 to 58 |
| 5 | Andre Russell | 57 | 785 | 52% | 1 to 80 |
| 6 | Tristan Stubbs | 46 | 763 | 42% | 2 to 86 |
| 7 | David Miller | 65 | 1,068 | 33% | 2 to 110 |
| 8 | Rinku Singh | 63 | 966 | 31% | 2 to 108 |
| 9 | Nicholas Pooran | 70 | 1,130 | 23% | 2 to 123 |
| 10 | Mark Chapman | 32 | 503 | 41% | 1 to 114 |

### Top 10 bowlers under pressure (Approach C: Pressure Response Index)

| Rank | Player | Pressure spells | Pressure balls | Top-10 probability | Rank interval |
|---|---|---|---|---|---|
| 1 | Matheesha Pathirana | 46 | 930 | 86% | 1 to 26 |
| 2 | Kuldeep Yadav | 64 | 973 | 56% | 1 to 51 |
| 3 | Jasprit Bumrah | 51 | 636 | 56% | 1 to 56 |
| 4 | Varun Chakravarthy | 69 | 999 | 45% | 1 to 64 |
| 5 | Sunil Narine | 48 | 713 | 57% | 1 to 58 |
| 6 | Akeal Hosein | 47 | 486 | 54% | 1 to 56 |
| 7 | Rashid Khan | 88 | 1,340 | 27% | 2 to 75 |
| 8 | Mohammad Nawaz | 40 | 467 | 49% | 1 to 69 |
| 9 | Wanindu Hasaranga | 70 | 1,069 | 14% | 3 to 107 |
| 10 | Abbas Afridi | 19 | 223 | 44% | 1 to 81 |

**How to read the lists.**

- The top two or three in each list are fairly stable (Top-10 probability 56% to 91%). Below that the rank intervals are wide, so the exact order of ranks 4 to 10 should not be taken literally.
- A high rank means the player beat the model's expectation in pressure situations. It does not always mean the player improved on their own normal level: Tim David, Nicholas Pooran and Rashid Khan perform slightly below their own normal-play baseline under pressure. Each player's explanation says which case applies.
- Full columns (scores, intervals, normal baseline, pressure-versus-baseline difference, IPL and T20I split, flags, versions) are in `backend/data/reports/pressure_batters_top10.csv` and `pressure_bowlers_top10.csv`.

---

## 2. Data

Only the official competition data are used for analysis.

| File | Role |
|---|---|
| `updated_ball_by_ball.csv` | **Authoritative** delivery-level data (200,999 deliveries) |
| `ball_by_ball.csv` | Original version, kept for comparison only |
| `matches.csv` | Match metadata (883 matches, 867 with deliveries) |
| `competitions.csv`, `teams.csv` | Competition and team reference data |
| `playing_eleven.csv` | Match squads and participation |
| `competition_team_player_mapping.csv` | Player identity mapping (1,217 players) |

Key data decisions, all checked during the audit phase:

- **Why the updated file.** In `ball_by_ball.csv`, `extras1_runs` holds a category code, not a run count. Using it as runs gives innings totals that match Cricsheet in 0 of 1,504 innings. In `updated_ball_by_ball.csv`, `runs + extras1_runs + extras_2_runs` matches the Cricsheet total in 1,494 of 1,504 innings.
- **`runs` is runs off the bat only** (verified against Cricsheet batter runs in 1,488 of 1,504 innings).
- **Legal ball rule:** a ball is legal unless `extras_type` is `wide`, `Overstep` (no-ball) or `other`. This matches Cricsheet legal-ball counts in 1,497 of 1,504 innings.
- **Super Overs excluded.** Innings 3 and 4 (six matches) are kept in the database but excluded from regulation calculations.
- **42 late-dated T20I matches** remain excluded from primary evaluation until their dates are officially verified. Original dates are never altered.
- **Not used as sources:** `matches 2026.csv`, `*_stats2026.csv`, `ipl squad.csv` for analysis, and the Cricsheet JSON folders. Cricsheet was used only to *validate* the official data (run semantics, Super Over identification), never as a feature, model input or ranking source.
- **Missing values are never treated as zero.** All data-quality issues (26 in total) are kept in a register (`backend/config/data_quality_restrictions_v1.json`) and applied only to the metrics they affect. No match is deleted globally.

Source files are read-only. Their SHA-256 hashes are recorded before and after every pipeline run.

---

## 3. Repository layout

```text
d:/Data/
├── *.csv, *_json/            Official data and Cricsheet folders (read-only, git-ignored)
├── backend/
│   ├── app/
│   │   ├── core/             Settings, database access, logging
│   │   ├── data_pipeline/    Ingestion, schema validation, data-quality checks
│   │   ├── analytics/        Pre-delivery state engine, phases, baselines, restriction service
│   │   ├── phase4 … phase8/  Each stage of the methodology (phase8 = final submission)
│   │   └── api/v1/           FastAPI routes (public submission API, token-protected internal routes)
│   ├── config/               Versioned configuration (split, criteria, restrictions, weights)
│   ├── data/
│   │   ├── database/         superr.duckdb (official), exploratory.duckdb, phase8.duckdb
│   │   ├── models/           Trained model files (.joblib) and their metadata (.json)
│   │   └── reports/          All reports, CSV outputs and audit files
│   ├── scripts/              Reproducible pipeline scripts (run_phase8.py is the final one)
│   └── tests/                Pytest suite
├── frontend/                 React + TypeScript dashboard (Vite)
└── submission/               Final submission bundle with a SHA-256 manifest
```

---

## 4. Running the project

Requirements: Python 3.11 and Node.js. On Windows PowerShell:

```powershell
# Backend
cd d:\Data\backend
pip install -r requirements.txt
$env:PYTHONUTF8 = 1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (second terminal)
cd d:\Data\frontend
npm install
npm run dev          # opens on http://localhost:5173
```

The frontend reads the API from `http://localhost:8000` by default (override with `VITE_API_ORIGIN`).

The **Experimental AI Predictions** page needs an internal token. Start the backend with `$env:SUPERR_ADMIN_TOKEN = "<your secret>"` and enter the same value on the page. Without it the page stays locked.

To rebuild the final results from the data:

```powershell
cd d:\Data\backend
$env:PYTHONUTF8 = 1
python scripts\run_phase8.py        # deterministic, fixed seed 20260512
python -m pytest -q                 # full test suite
python scripts\check_frontend_api.py   # checks every endpoint the dashboard uses (backend must be running)
```

### Dashboard pages

Overview, Top 10 Batters, Top 10 Bowlers, Batter Profiles, Bowler Profiles, Player Comparison, Why Selected / Why Not Selected, Pressure Methodology, Data & Validation, and Experimental AI Predictions (token-protected). Every value comes from the backend; nothing is hard-coded.

---

## 5. Descriptive player profiles

### What they are

`backend/data/reports/descriptive_batter_profiles.csv` (920 rows) and `descriptive_bowler_profiles.csv` (672 rows) describe what each player actually did, one row per player per format. They feed the profile and comparison pages and the radar charts.

### Which methodology, and why

The profiles use **plain descriptive statistics with honest uncertainty**: counts and rates from the official deliveries, split by phase, innings and opponent type, each with its denominator and a bootstrap interval. They deliberately contain **no rank, no score and no composite rating**.

The reason: early in the project (Phase 6) the pressure measure was shown to be too noisy to separate individual players reliably. Turning raw statistics into a single score would have presented ordinary averages as if they were pressure conclusions. The profiles therefore answer "what happened, and how much evidence is there?" and leave "who is better under pressure?" to the separate, explicitly labelled pressure ranking.

### How it works

1. **Window and scope.** Matches from 2022-01-22 to 2025-12-19, IPL and T20I kept separate (never pooled), innings 1 and 2 only.
2. **Cricket definitions** (verified in the audit):
   - *Ball faced:* any delivery to the striker except a wide or the penalty row.
   - *Legal ball:* excludes wides, no-balls and the unverified `other` extras.
   - *Bowler runs* are only runs charged to the bowler. *Bowler wickets* are only bowler-credited dismissals: run-outs, retirements and obstructions do not count.
3. **Metrics.**
   - *Batters:* runs, balls, strike rate, average, balls per dismissal, fours, sixes, boundary share, dot-ball share.
   - *Bowlers:* overs, runs conceded, wickets, economy, balls per wicket, dot-ball share, boundaries conceded, wides and no-balls.
4. **Splits.**
   - *All players:* powerplay, middle and death overs (phase is based on legal balls and adjusts to shortened innings), and first innings against chase.
   - *Batters:* against pace and spin.
   - *Bowlers:* against right-handed and left-handed batters.
5. **Uncertainty.** Strike rate (batters) and economy (bowlers) carry a 95% interval from a bootstrap that resamples whole matches (1,000 draws, seed 20260512), because balls within a match are not independent. Where a rate cannot be estimated (fewer than 5 matches) the cell is empty with a reason.
6. **Small samples are flagged, never hidden** (`LOW_SAMPLE` below 60 balls). Missing values are empty with a stated reason, never 0.
7. **Radar charts** place each raw value as a percentile within a named cohort (same format and role, minimum 60 balls, at least 10 players). The dimensions are shown separately and are never combined into a single score.

Full column definitions and interpretation rules: `backend/data/reports/player_profile_explanations.md`.

---

## 6. Defining pressure

Pressure here means **observable difficulty of the match situation**, not a psychological state. Ball-by-ball data can show how a player performs in hard situations. They cannot show what the player feels.

Every delivery is described using **only what was known before it was bowled**: score, wickets lost, balls left, target, runs required, required and current run rate, phase, innings and batting order. Automated leakage tests confirm that changing later deliveries or the match result never changes the state of an earlier ball.

Seven pressure-intensity definitions (P0 to P6) were declared in advance and tested on deliveries before any player was ranked. A good definition should show that high-pressure balls really are harder:

- (a) fewer runs per ball,
- (b) a higher chance of a wicket,
- (c) more variable outcomes,
- (d) larger swings in win probability,
- (e) a steady trend across ten intensity bands.

**Chosen definition: P4, resource scarcity.** Pressure intensity (0 to 1) is the share of wickets already lost multiplied by the share of the innings already used, in both innings. Wickets in hand and balls remaining are the two resources a batting side spends, and running short of both is what pressure looks like on the field.

- Balls at intensity 0.5 or above form the pressure sample. Each counts in proportion to its intensity, so a very high-pressure ball counts more than a borderline one.
- Balls below 0.5 define the player's normal play.
- At P4, pressure balls have 0.192 fewer runs per ball and a 0.057 higher wicket probability than low-pressure balls.

No definition passed all five tests (the steady-trend test failed for every candidate). P4 passed the most tests across both innings, so it is the **best available, not validated** definition. This alone caps both lists at EXPLORATORY. Thresholds such as "last five overs" or "a close chase" were deliberately not assumed.

---

## 7. How the pressure ranking was built

Three genuinely different approaches were built and compared. Batters and bowlers are always evaluated separately.

### Approach A: context-adjusted performance (used for batters)

*How much better or worse than expected did the player do, given the situation?*

1. A **player-blind** model predicts, for every ball, the expected runs and the chance of a wicket from the pre-delivery situation alone (see [section 8](#8-how-the-models-were-trained)).
2. For each pressure ball: *actual runs minus expected runs*, and *expected minus actual dismissal* (so surviving counts as better). Each is standardised and averaged.
3. Residuals are weighted by pressure intensity and summed per player per innings. **The innings is the unit**, because balls in the same innings are not independent.
4. Player estimates are **shrunk towards the average** with a random-effects model fitted by REML, so a player with few pressure innings is pulled further towards the mean. This prevents one exceptional innings from producing a top rank.
5. Each player's pressure level is compared with their **normal-play baseline** (the same residual on low-pressure balls). This shows whether the player rises under pressure or is simply good all the time.

### Approach B: win probability added (WPA)

*How much did the player move the match?*

1. Two win-probability models were trained, one for the first innings and one for chases (see [section 8](#8-how-the-models-were-trained)).
2. For each ball, the change in win probability before and after the delivery is attributed by explicit rules:
   - the striker takes the effect of runs off the bat;
   - the bowler takes the runs charged to them and the wickets credited to them;
   - run-outs and other non-bowler dismissals are never credited to the bowler;
   - byes and leg-byes go to the batting side as a whole.
3. **Leverage** (how much the next ball could swing the match, known in advance) is kept separate from **realised impact**, so a high-impact ball is not automatically treated as a high-pressure ball.
4. Players are scored on win probability added above what the leverage of their situations predicts.

### Approach C: Pressure Response Index (used for bowlers)

*An original framework: how consistently does the player beat expectation when the situation becomes difficult?*

1. **Inputs.** It combines three components: the Approach A residual, the Approach B impact, and *consistency*, the share of a player's pressure appearances in which they beat the model's expectation.
2. **Weights.** Component weights are **not chosen by hand**. Each component is weighted by its own measured reliability on one half of the matches, and the index is evaluated on the other half.
3. **What it reduced to.** In practice components A and B showed no reliable player-to-player signal, so they received zero weight and the index reduces to the **consistency component**. The bowler ranking is therefore a measure of how often a bowler beat expectation in pressure spells, not of the size of their impact.
4. **Shrinkage and uncertainty** are applied as in Approach A.

### Choosing the approach and building the lists

The selection rules were written to `backend/config/phase8_selection_criteria_v1.json` and its SHA-256 hash (`9258aa6d…`) was logged **before** any comparison result existed. The hash was checked before every comparison step. The rule uses only approach-level evidence: split-half and out-of-time reliability, inclusion stability and an explainability checklist. It never looks at which players an approach promotes.

- **Batters:** Approach A was chosen. A and C were within 0.001 on reliability, so this is not a meaningful performance difference.
- **Bowlers:** Approach C was chosen, leading on split-half and out-of-time reliability.
- **Approach B** was the weakest for both roles.

Eligibility floors (also declared in advance) are:

- at least 8 matches;
- at least 60 balls faced or 72 bowled;
- at least 8 high-intensity innings or spells;
- an effective sample of at least 60;
- at least 4 matches in 2025.

225 batters and 221 bowlers qualified. Players below a floor are marked `INSUFFICIENT_EVIDENCE`, which says nothing about their quality, and no list is padded.

**IPL and T20I.** The default 70:30 weighting from earlier phases was not assumed. The project tested whether players' IPL and T20I results agree enough to justify a single combined score. They do not: the cross-format correlation is close to 0 for every approach. Each player-innings is therefore weighted by its own precision, with no fixed format split, the result is flagged `FORMAT_COMBINATION_UNSUPPORTED`, and IPL and T20I contributions and ranks are shown separately for every listed player.

Each player's evidence, including near-misses and players with strong raw statistics who were not selected, is in `backend/data/reports/player_selection_explanations.md`.

---

## 8. How the models were trained

### Data split

The split is chronological at match level, so every delivery of a match stays in the same period. Boundaries are fixed in `backend/config/phase4_split_v1.json`.

| Period | Dates | Use |
|---|---|---|
| TRAIN | up to 2024-12-31 (487 matches) | Fit all models, baselines and shrinkage parameters |
| VALIDATION | calendar 2025 (188 matches) | Check calibration and accuracy, compare approaches |
| TEST | 2026 onward | **Not used.** It was opened once in an earlier phase, so it is no longer a pristine hold-out. It is not used for tuning and no out-of-sample claim rests on it |

### Expected-outcome models (used by Approaches A and C)

- **Algorithm:** gradient boosting (scikit-learn `HistGradientBoostingRegressor` / `Classifier`), seed 20260512, compared against a constant prediction and a lookup-table baseline.
- **Targets (eight models):** batter runs, batter dismissal, dot ball and boundary, and the same four from the bowler's side.
- **Features (pre-delivery only):** innings and chase flag, score and wickets before the ball, balls bowled and remaining, innings length, current and required run rate, runs required, phase, batting order, the batter's and bowler's earlier figures in the innings, competition type, stage, knockout flag, and team-strength and par estimates built from **strictly earlier matches only**.
- **Features never used:** player identity and any outcome column. The models are player-blind on purpose: they describe what a typical player would do in that situation.
- **Leakage control:** TRAIN balls are scored out of fold (by match), so no ball is predicted by a model that saw its own match.
- **Validation results:** the models beat a constant prediction by 1.5% to 3.1%. For example, the batter-runs model has a VALIDATION RMSE of 1.729 against 1.757 for the constant. Ball outcomes are mostly chance given the situation, which limits how much of any residual can be credited to the player.

### Win-probability models (used by Approach B)

- **Algorithm:** `HistGradientBoostingClassifier`.
- **W1** (first innings): predicts whether the batting side wins, from score, wickets, balls remaining, run rate, projected total and par.
- **W2** (chase): predicts whether the chasing side wins, from runs required, balls remaining, wickets remaining and required and current run rate.
- **VALIDATION results:**

| Model | Brier score | Constant baseline | Logistic baseline | Calibration slope |
|---|---|---|---|---|
| W1 (first innings) | 0.215 | 0.251 | 0.223 | 0.886 |
| W2 (chase) | 0.117 | 0.251 | 0.122 | 1.134 |

Both beat a constant and a logistic baseline and passed the declared calibration checks. Within TRAIN, the first-innings model is over-confident (out-of-fold slope 0.57), so first-innings win-probability results are reported with that caveat.

### Model files and verification

All 9 trained models are saved in `backend/data/models/` as `.joblib` files. Each has a `.json` metadata file with the algorithm, parameters, features, target, training period, row counts, metrics, data hash, seed and timestamp. Retraining from scratch reproduced the stored models exactly (maximum prediction difference 0.0). Details: `backend/data/reports/ai_pipeline_verification.md`.

An **experimental AI Top 10**, ranked directly on model outputs, is kept separate from the submitted lists and served only through the token-protected page. Its reliability is low (split-half about 0.2). A working model pipeline shows that training and prediction run; it does not show that players can be ranked reliably.

---

## 9. Reliability: how far the results can be trusted

The project tested whether each method gives the **same order twice**.

- **Split-half test:** each player's matches are split into two halves (odd and even matches by date, and early against late), each half is scored independently and the two orders are compared. The correlation is corrected to full length (Spearman-Brown) and its interval comes from a bootstrap over matches.
- **Out-of-time test:** TRAIN-period estimates are correlated with VALIDATION-period estimates.

| Role (submitted approach) | Split-half reliability | 95% interval | Out-of-time correlation |
|---|---|---|---|
| Batters (A) | 0.057 | −0.22 to 0.36 | 0.199 |
| Bowlers (C) | 0.267 | −0.08 to 0.39 | 0.199 |

The thresholds declared in advance were **0.5 for PROVISIONAL** and **0.7 for VALIDATED**. Both lists fall well short and both intervals include 0, so both are **EXPLORATORY**.

The variance between players is also tiny compared with ball-to-ball noise. None of the three approaches passes the 0.5 data-weight check carried over from earlier phases, and that check was not lowered.

**The honest conclusion.** Four seasons of ball-by-ball data do not separate players on pressure performance with statistical confidence. The lists are a transparent, reproducible description of who beat the expectation most in difficult situations from 2022 to 2025, with every player's evidence shown. They are not proof that these players are reliably better under pressure than those just below them.

### Sensitivity

- **Stable** to the eligibility floors: halving or doubling them keeps the same Top 10.
- **Moderately stable** to format (IPL-only and T20I-only) and calendar window.
- **Changes substantially** with the pressure definition, the shrinkage assumption and the components used.

The full tables are in `submission_methodology.md`, section 11.

---

## 10. How the project evolved

| Phase | What was done |
|---|---|
| 1 | Audit of every file: schemas, row counts, extras encoding, cross-checks against Cricsheet |
| 2 | Idempotent, transactional DuckDB ingestion of the official CSVs, with provenance on every row |
| 2.5 | Format-weight and eligibility harnesses, Super Over validation, data-quality impact register |
| 3 | Pre-delivery match-state engine with leakage tests, pressure feature distributions, baselines |
| 4 | Chronological split, strictly-prior par scores, shrinkage, experimental scoring, test lock |
| 5 | Classification (capped status kept as Verified / Derived / Unknown), date verification, publication gates, filter-driven ranking engine |
| 6 | Reliability investigation: the original percentile-cutoff pressure measure could not separate players (between-player variance at the floor in all 48 contexts) |
| 7 | Submission finalisation and descriptive profiles (recruitment and retention work was later dropped after the organiser's scope clarification) |
| 8 | Independent methodology: continuous pressure intensity, gradient-boosting expected outcomes, win-probability models, three approaches compared under hashed criteria, final Top 10 lists, dashboard |

Phase 8 deliberately tried a richer method to see whether the Phase 6 finding could be overturned. The models improved technically, but the central finding held. The full account of what was tried and why is in `backend/data/reports/pressure_methodology_research.md`.

---

## 11. Limitations

- **No approach reached the PROVISIONAL threshold.** Rank orders, especially below the top three, are not shown to separate players beyond noise.
- **The pressure definition is the best available, not validated.**
- **Top 10 membership depends on choices.** It changes with the pressure definition and the shrinkage assumption.
- **The bowler index rests on consistency.** It reflects how often a bowler beat expectation, not the size of their impact.
- **Formats are not combined into one skill.** IPL and T20I results are too weakly related.
- **Expected-outcome models explain little.** Each ball's outcome is largely chance given the situation.
- **Some matches are left out.** 2026 matches are not used, the 42 late-dated T20I matches are excluded pending verification, and DLS rows that cannot be reconstructed are excluded without imputing values.
- **Capped status is not authoritative.** No official cap-status source was available, so it stays Derived or Unknown, never guessed.
- **The dashboard has no frontend unit tests.** It was checked through the build, lint and a live API connection check.

---

## 12. Testing and reproducibility

- **Backend tests.** The suite has about 1,440 pytest tests. They cover:
  - cricket calculations, legal balls and extras;
  - pre-delivery state and leakage;
  - chronological split integrity, attribution rules, shrinkage and reliability estimators;
  - eligibility, deterministic ranking and tie-breaks, and the hash check on the selection criteria;
  - API schemas and token protection, the absence of hard-coded data, and preservation of protected files.
- **Lint.** `ruff check` and `ruff format --check` are clean. The frontend `npm run build` and `npm run lint` pass.
- **Determinism.** All random steps use seed 20260512, and rerunning the pipeline reproduces the outputs byte for byte.
- **Provenance.** Every output row carries the methodology version, data-version hashes, criteria hash and generation time. `backend/data/reports/phase8_build_manifest.json` records input hashes and output provenance. The `submission/` folder has a SHA-256 manifest of every submitted file.

---

## 13. Key documents

All under `backend/data/reports/` (copies of the submission files are in `submission/`):

| Document | Contents |
|---|---|
| `submission_methodology.md` | Full methodology report for judges, with technical detail |
| `submission_executive_summary.md` | One-page plain-English summary |
| `pressure_batters_top10.csv` / `pressure_bowlers_top10.csv` | The two submitted lists (JSON versions alongside) |
| `pressure_top10_status.md` | What the EXPLORATORY status means for each list |
| `player_selection_explanations.md` | Evidence for every listed player, plus near-misses and exclusions |
| `methodology_comparison.md` | Approaches A, B and C compared under the predeclared criteria |
| `pressure_methodology_research.md` | Research narrative: what was tried, what failed and why |
| `descriptive_batter_profiles.csv` / `descriptive_bowler_profiles.csv` | Descriptive profiles (no ranks or scores) |
| `player_profile_explanations.md` | How to read the profiles |
| `ai_pipeline_verification.md` | Model training, validation and prediction verification |
| `submission_test_report.md` | Actual test command outputs |
| `submission_readiness_audit.md` | Checklist of deliverables and open items |
