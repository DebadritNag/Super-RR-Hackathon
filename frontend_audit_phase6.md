# SupeRR Selector Season 2 — Frontend UI Audit & Implementation Evidence (Phase 6)

**Audit Date:** 2026-11-17  
**Auditor:** DeepMind Antigravity AI Assistant  
**Workspace:** `D:\Data` (`frontend/` & `backend/`)  
**Status:** `INTERNAL_EXPERIMENTAL_ONLY` / Read-Only Audit (Zero modifications made)

---

## 1. Executive Summary

This document provides a comprehensive, evidence-based technical audit of the **SupeRR Selector Season 2** frontend codebase located in `D:\Data\frontend`.

### Key Findings
1. **Frontend Architecture:** Built with **Vite 8.3.5**, **React 19.3.1**, **TypeScript 7.0.2**, **Tailwind CSS v4** (`@tailwindcss/vite`), **Recharts 3.10.1**, and **Lucide React**. It compiles cleanly to production (`tsc -b && vite build` completed in 1.72s).
2. **Navigation Model:** Single-Page Application (SPA) utilizing internal state-based routing (`AppContext.tsx` managing `activeSection: NavigationId`). There is no `react-router` dependency.
3. **Data Layer Reality:** The frontend is **100% decoupled from the backend API**. There are zero HTTP network calls (`fetch` or `axios`). All data is provided via a static mock layer (`src/data/mock/players.ts`, `historicalNeeds.ts`, etc.) and `localStorage` (`src/lib/storage.ts`).
4. **Active UI Focus:** The UI is currently configured around a **7-section competition submission revamp**:
   - `overview` (`OverviewDashboard.tsx`)
   - `pressure-batters` (`PressureBattersPage.tsx`)
   - `pressure-bowlers` (`PressureBowlersPage.tsx`)
   - `player-comparison` (`PlayerComparison.tsx`)
   - `selection-reasons` (`WhySelectedPage.tsx`)
   - `methodology` (`DataMethodologyPage.tsx`)
   - `rr-analysis` (`RRAnalysisPage.tsx`)
5. **Phase 6 Compliance:**
   - **Disclaimers & Badges:** Prominently displays `EXPERIMENTAL_NOT_VALIDATED`, `INTERNAL_EXPERIMENTAL_ONLY`, and Phase 4 TEST holdout access disclosures across the header, topbar, and methodology sections.
   - **Gating Enforcement:** Strictly segregates players failing the 100-ball sample gate, 10-match gate, or 70:30 data-weight gate into an explicit failure taxonomy.
   - **Backend Decoupling:** In the backend, public ranking endpoints answer `403 PUBLICATION_GATE_NOT_SATISFIED`. The frontend functions as an internal franchise research terminal rather than an unvalidated public portal.
   - **Missing Capabilities:** The **Retention Importer** is completely absent from the frontend (the backend only contains an empty DuckDB stub `p6_retention_status_stub`). Live AI model training and dynamic predictions are not implemented.

---

## 2. Feature-by-Feature Status Table

Classification rubric:
- **1. Implemented and working:** Functional with real or fully simulated production behavior.
- **2. Implemented but using mock/hardcoded data:** Functional UI components backed by static in-memory data rather than live backend endpoints.
- **3. Partially implemented:** Incomplete feature set, unrouted components, or partial integration.
- **4. Designed but not implemented:** Schemas, designs, or formulas documented, but no interactive UI.
- **5. Missing:** No frontend code, component, or interface exists.

| # | Requested Feature | Implementation Status | Primary File Path | Primary Component / Module | Data Provenance |
|---|---|---|---|---|---|
| **1** | **Overview Dashboard** | **2. Implemented (Mock Data)** | `src/features/overview/OverviewDashboard.tsx` | `OverviewDashboard` | `MOCK_PLAYERS` array (`players.ts`) |
| **2** | **Top 10 Pressure Batters** | **2. Implemented (Mock Data)** | `src/features/pressure-batters/PressureBattersPage.tsx` | `PressureBattersPage` | `MOCK_PLAYERS` array (`players.ts`) |
| **3** | **Top 10 Pressure Bowlers** | **2. Implemented (Mock Data)** | `src/features/pressure-bowlers/PressureBowlersPage.tsx` | `PressureBowlersPage` | `MOCK_PLAYERS` array (`players.ts`) |
| **4** | **Descriptive Batter Profiles** | **2. Implemented (Mock Data)** | `src/features/player-profile/PlayerProfileModal.tsx` | `PlayerProfileModal` | `MOCK_PLAYERS` array (`players.ts`) |
| **5** | **Descriptive Bowler Profiles** | **2. Implemented (Mock Data)** | `src/features/player-profile/PlayerProfileModal.tsx` | `PlayerProfileModal` | `MOCK_PLAYERS` array (`players.ts`) |
| **6** | **Radar / Spider Charts (8 Axes)** | **1. Implemented & Working** | `src/components/charts/PlayerRadarChart.tsx` | `PlayerRadarChart`, `ComparisonRadarChart` | Props passed from parent mock data |
| **7** | **Player Comparison (2–4 Players)** | **2. Implemented (Mock Data)** | `src/features/player-comparison/PlayerComparison.tsx` | `PlayerComparison` | `comparisonService.ts` / `MOCK_PLAYERS` |
| **8** | **Why Selected / Why Not Selected** | **2. Implemented (Mock Data)** | `src/features/selection-reasons/WhySelectedPage.tsx` | `WhySelectedPage` | `MOCK_PLAYERS` failure taxonomy fields |
| **9** | **Methodology & Data Provenance** | **2. Implemented (Mock Data)** | `src/features/methodology/DataMethodologyPage.tsx` | `DataMethodologyPage` | Static documentation in TSX |
| **10** | **RR Recruitment-Gap Analysis** | **2. Implemented (Mock Data)** | `src/features/rr-analysis/RRAnalysisPage.tsx` | `RRAnalysisPage` | Static analysis + `historicalNeeds.ts` |
| **11** | **Retention Importer** | **5. Missing** | N/A | None | Backend has empty stub `retention_stub.py` |
| **12** | **Experimental AI Predictions** | **4. Designed / Static Only** | `src/data/mock/players.ts` | Precomputed static scores | Static Bayesian estimates (No inference API) |
| **13** | **Model Training / Validation Status** | **2. Implemented (Mock Data)** | `src/features/methodology/DataMethodologyPage.tsx` | `DataMethodologyPage` (Tabs 4 & 5) | Static TSX disclosure badges |
| **14** | **Responsive Desktop & Mobile Layout** | **1. Implemented & Working** | `src/components/layout/Shell.tsx` | `Shell`, `Sidebar`, `Topbar` | Tailwind CSS responsive breakpoints |
| **15** | **Public Descriptive Player Directory** | **3. Partially Implemented** | `src/features/player-explorer/PlayerExplorer.tsx` | `PlayerExplorer` | Exists in code, but currently unrouted |
| **16** | **Live Backend API Integration** | **5. Missing** | `src/services/*.ts` | All service adapters | Decoupled; zero network calls |

---

## 3. Detailed Implementation Evidence

### 3.1 Overview Dashboard
- **File:** `D:\Data\frontend\src\features\overview\OverviewDashboard.tsx`
- **Route / Section:** `overview` (active by default in `Shell.tsx`)
- **Backend Equivalent:** None directly (aggregates data from `/api/v1/internal/rankings/batter`, `/api/v1/internal/rankings/bowler`, and `/api/v1/meta/capabilities`)
- **Observed UI Components:**
  - Executive introduction banner: Title *"Pressure Performance Intelligence"* with subtitle *"Identifying players who perform when the match situation demands the most."*
  - 6 Key KPI Cards: Total Evaluated (`1,217`), Eligible Batters (`84`), Eligible Bowlers (`76`), Pressure Balls Analyzed (`14,892`), Matches Included (`883`), Gating Excluded (`562`).
  - Dual 8-Axis Radar Charts: Left chart for Batters with live dropdown selector; Right chart for Bowlers with live dropdown selector.
  - Top 10 Batters and Top 10 Bowlers ranking lists with rank badges, player names, IDs, scores, and uncertainty/residual metrics.
  - Quick Head-to-Head Comparison card with candidate selectors and differential advantage narrative.
  - Data Governance Summary card linking to the 9-step pipeline.
  - Rajasthan Royals 2025/2026 Recruitment Blueprint card highlighting top 3 priority gaps.
- **Data Reality:** Mock data hardcoded in `src/data/mock/players.ts`.

### 3.2 Top 10 Pressure Batters
- **File:** `D:\Data\frontend\src\features\pressure-batters\PressureBattersPage.tsx`
- **Route / Section:** `pressure-batters`
- **Backend Equivalent:** `GET /api/v1/internal/rankings/batter?format=IPL&sort_by=score&order=desc`
- **Observed UI Components:**
  - Table Columns: `Rank`, `Player`, `ID`, `Role`, `Nat`, `Score` (sortable), `Base`, `Uplift`, `Balls`, `Matches`, `CI`, `Status`.
  - Filters: Text search (`searchTerm`), Nationality dropdown (`All`, `Indian`, `Overseas`), International Status dropdown (`All`, `Verified Capped`, `Derived Capped`, `Unknown`).
  - Interactive Selection: Clicking any row updates the right-hand inspection drawer.
  - Inspection Drawer: Displays player summary, quantitative pressure breakdown (pressure average, SR, boundary %, dot %, chase average), complete 8-axis radar chart with secondary comparison overlay selector, and evidence-based *"Why This Batter?"* scouting rationale.
  - CSV Export: `exportRankingsCSV('batters')` triggers client-side CSV generation.
- **Data Reality:** Hardcoded array of 10 selected batters in `players.ts` (Heinrich Klaasen 94.8, Suryakumar Yadav 93.9, Rinku Singh 93.2, Nicholas Pooran 91.8, Riyan Parag 89.6, Shashank Singh 88.4, Shimron Hetmyer 87.2, Ashutosh Sharma 86.4, Dhruv Jurel 85.8, Priyansh Arya 84.7).

### 3.3 Top 10 Pressure Bowlers
- **File:** `D:\Data\frontend\src\features\pressure-bowlers\PressureBowlersPage.tsx`
- **Route / Section:** `pressure-bowlers`
- **Backend Equivalent:** `GET /api/v1/internal/rankings/bowler?format=IPL&sort_by=score&order=desc`
- **Observed UI Components:**
  - Table Columns: `Rank`, `Player`, `ID`, `Role`, `Nat`, `Score` (negated runs-conceded residual), `Base Econ`, `Residual %`, `Wkts`, `Balls`, `Matches`, `CI`.
  - Amber badge: `Experimental Roster` (complying with Phase 6 unvalidated ranking rules).
  - Inspection Drawer: Displays bowling-specific breakdown (pressure economy, clutch wickets, dot ball %, death overs 16–20 economy, chase defence economy), 8-axis bowler radar chart with secondary comparison overlay, and evidence-based *"Why This Bowler?"* rationale.
  - CSV Export: `exportRankingsCSV('bowlers')`.
- **Data Reality:** Hardcoded array of 10 selected bowlers in `players.ts` (Jasprit Bumrah 96.4, Sandeep Sharma 92.8, Matheesha Pathirana 91.5, Arshdeep Singh 90.1, Axar Patel 89.2, Yuzvendra Chahal 88.5, Harshit Rana 87.0, Yash Dayal 86.1, Mayank Yadav 85.5, Andre Russell 84.8).

### 3.4 Descriptive Batter & Bowler Profiles
- **Files:**
  - `D:\Data\frontend\src\features\player-profile\PlayerProfileModal.tsx` (Global modal)
  - `D:\Data\frontend\src\features\player-explorer\PlayerExplorer.tsx` (Unrouted directory component)
- **Backend Equivalent:** `GET /api/v1/players/{player_id}` (Public descriptive) & `GET /api/v1/internal/players/{player_id}/profile` (Internal detailed)
- **Observed UI Components in `PlayerProfileModal`:**
  - Header: Photo placeholder, captain badge, player name, franchise team, international status badge (`Verified Capped` / `Derived Capped` / `Unknown`), data status badge (`Experimental`), speciality, batting/bowling style.
  - Tab 1: *Analytics Overview* — Pressure index, baseline rating, residual impact, effective sample balls, core competition justification, RR squad fit score/reason.
  - Tab 2: *8-Axis Radar Profile* — Dedicated `PlayerRadarChart` rendering all 8 metrics with raw stats tooltips.
  - Tab 3: *Match Splits* — Situations where player excels, key strengths, known vulnerabilities.
  - Tab 4: *Scouting Rationale* — Sample size bounds, data limitations, reliability tier, data eligibility.
  - Action button: *"Add to Comparison"*.
- **Data Reality:** Rendered purely from the in-memory `Player` object passed into `openPlayerProfile(player)`.

### 3.5 Radar / Spider Charts
- **Files:**
  - `D:\Data\frontend\src\components\charts\PlayerRadarChart.tsx`
  - `D:\Data\frontend\src\components\charts\ComparisonRadarChart.tsx`
- **Backend Equivalent:** `GET /api/v1/internal/players/{player_id}/profile` (`radar.axes[]`)
- **Observed Implementation:**
  - Implemented using SVG-based Recharts (`RadarChart`, `PolarGrid`, `PolarAngleAxis`, `PolarRadiusAxis`, `Radar`, `Tooltip`).
  - Batter Radar (8 Axes):
    1. Run Scoring (`pressureRunScoring`)
    2. Strike Rate (`strikeRatePerformance`)
    3. Boundaries (`boundaryContribution`)
    4. Chase Impact (`chasePerformance`)
    5. Middle Overs vs Spin (`middleOverPerformance`)
    6. Death Overs (`deathOverPerformance`)
    7. Wicket Preservation / Dot Avoidance (`wicketPreservation`)
    8. Consistency (`consistency`)
  - Bowler Radar (8 Axes):
    1. Wicket Threat (`pressureWicketTaking`)
    2. Economy Rate (`economyUnderPressure`)
    3. Dot Balls (`dotBallContribution`)
    4. Powerplay (`powerplayEffectiveness`)
    5. Middle Phase (`middleOverEffectiveness`)
    6. Death Phase (`deathOverEffectiveness`)
    7. Chase Defence (`chaseDefence`)
    8. Consistency (`consistency`)
  - Tooltips: Custom tooltip renders both the normalized 0–100 score AND the underlying raw cricket stat (e.g. `191.6 SR`, `28.4% Boundary balls`, `6.58 RPO in pressure`).
  - Comparison Overlay: `ComparisonRadarChart` overlays up to 4 players simultaneously with distinct palette colors (`#246B4B`, `#D97736`, `#202522`, `#27845B`).

### 3.6 Player Comparison
- **File:** `D:\Data\frontend\src\features\player-comparison\PlayerComparison.tsx`
- **Service:** `D:\Data\frontend\src\services\comparisonService.ts`
- **Route / Section:** `player-comparison`
- **Backend Equivalent:** `GET /api/v1/internal/compare?player_ids=1,2,3`
- **Observed UI Components:**
  - Roster Queue: Supports 2 to 4 players with individual remove tags and a "Clear" button.
  - Role Compatibility Guard: Detects and rejects mixing pure batters with pure bowlers; displays an error banner if incompatible roles are queued.
  - Overlaid 8-Axis Radar Chart: Compares the multi-dimensional polygon shapes of all queued candidates.
  - Analytical Verdict Card: Displays an evidence statement answering *"Why Player A ranks above Player B"* with statistical confidence level (`High`, `Moderate`, `Low`, `Inconclusive`).
  - Metric-by-Metric Granular Audit Table: Shows side-by-side values with leader highlights across Core Pressure & Reliability, Phase Execution (batting), and Phase Restriction (bowling).
  - Add Player Modal: Filtered strictly for candidates matching the active comparison discipline.
- **Data Reality:** Computed dynamically on the client by `comparisonService.comparePlayers(playerIds)` using mock records.

### 3.7 Why Selected / Why Not Selected
- **File:** `D:\Data\frontend\src\features\selection-reasons\WhySelectedPage.tsx`
- **Route / Section:** `selection-reasons`
- **Backend Equivalent:** None directly (synthesizes qualification criteria and failure audits)
- **Observed UI Components:**
  - Three distinct tabs:
    1. *Selected (20)*: Displays cards for all 20 qualified candidates (10 batters, 10 bowlers) with scores, residual uplifts, sample sizes, and mathematical rationale.
    2. *Not Selected*: Displays excluded candidates categorized by explicit failure reason badges:
       - `below-cutoff`: Sameer Rizvi (Rank 14, 82.5 pts), Shahrukh Khan (Rank 11, 83.4 pts).
       - `insufficient-opportunities`: Aman Rao (68 pressure balls faced, below the 100-ball threshold).
       - `insufficient-matches`: Dewald Brevis (9 matches, below the 10-match gate; wide CI $\pm 8.8$), Mohsin Khan (8 matches).
       - `failed-data-weight-gate`: Kartik Sharma (domestic weight ratio failed the 70:30 reliability criteria).
       - `missing-mapping`: Rahul Chahar (multi-season entity deduplication collision flag).
       - `extreme-variance`: Tushar Deshpande (extreme variance between low and high leverage situations).
    3. *Head-to-Head Decider*: Interactive dropdowns selecting 1 Selected Candidate vs 1 Unselected Candidate with an automated mathematical explanation of why one qualified and the other was rejected.

### 3.8 Methodology and Data Provenance
- **File:** `D:\Data\frontend\src\features\methodology\DataMethodologyPage.tsx`
- **Route / Section:** `methodology`
- **Backend Equivalent:** `GET /api/v1/meta/publication-gates`, `GET /api/v1/meta/classification-coverage`, `GET /api/v1/meta/capabilities`
- **Observed UI Components:**
  - Tab 1: *9-Step Pipeline* — Visual architecture cards from raw ingestion to final ranked rosters, including mathematical formula representations for batter scoring and negated bowler residuals ($\hat{\theta}_i = B_i \bar{y} + (1 - B_i) y_i$).
  - Tab 2: *Data Sources* — Inventory table of actual organizer files used (`ipl_deliveries.csv`, `ipl_matches.csv`, `ipl_squads_2024_2026.csv`, `player_mapping_registry.json`, `supplementary_t20_historical.json`), record counts, key fields, and primary vs supplementary classification.
  - Tab 3: *Why This Data?* — Narrative defending ball-by-ball telemetry, player identity deduplication, prohibition of silent domestic dilution, and handling of missing records.
  - Tab 4: *Gating Status* — Live verification audit for Minimum Opportunities Gate (Passed), Distinct Matches Gate (Passed), Data-Weight Gate 70:30 (Experimental), Strict Classification Gate (Passed), and Methodology Validation Gate (`EXPERIMENTAL_NOT_VALIDATED`).
  - Tab 5: *Train / Val / Test* — Partition status indicators (TRAIN 2008–2023, VALIDATION 2024 Early Season, TEST Accessed in Phase 4, FINAL REFIT Provisional 70:30) with mandatory disclosure of previous Phase 4 test set access.
  - Tab 6: *Limitations* — Explicit caveats covering low split-half reliability ($r \approx 0.42$), pressure definition sensitivity, shrinkage-floor conservatism, and absence of fielding/fitness telemetry.

### 3.9 Rajasthan Royals Recruitment-Gap Analysis
- **File:** `D:\Data\frontend\src\features\rr-analysis\RRAnalysisPage.tsx`
- **Route / Section:** `rr-analysis`
- **Backend Equivalent:** None directly (analytical debrief based on competition brief)
- **Observed UI Components:**
  - Season filter: `Combined Audit`, `2026 Campaign`, `2025 Campaign`.
  - Campaign outcomes summary:
    - 2026: 5th place finish (8-6 record), stalled by middle-overs spin squeeze on gripping tracks.
    - 2025: Qualifier 2 exit, plagued by 4 close-chase heartbreaks ($<28$ runs off 18 balls).
  - Batting Vulnerabilities: Middle-overs spin stagnation (34.2% dot balls in overs 7–15 vs spin), composure breakdown in chases, collapse vulnerability after early powerplay wickets.
  - Bowling Vulnerabilities: Death-overs economy leakage (11.45 RPO in overs 16–20), powerplay wicket drought when Boult went wicketless, sixth bowler spin over-reliance.
  - Source Transparency: Every finding is tagged with an explicit evidence badge: **Organizer Data Calculation**, **Media Observation**, or **Analytical Interpretation**.
  - Direct Recruitment Blueprint: Interactive cards mapping the Top 10 Batters (Klaasen, Parag, Rinku, Shashank) and Top 10 Bowlers (Bumrah, Sandeep, Pathirana, Arshdeep) directly into RR tactical vacancy slots.

### 3.10 Retention Importer
- **Status:** **5. Missing**
- **Evidence:**
  - Full codebase grep for `retention` across `D:\Data\frontend\src` yielded **zero matches**.
  - No file, route, component, modal, or input form exists in the frontend for importing retention lists, parsing retained player CSVs, or reviewing retention statuses.
  - In the backend, `D:\Data\backend\app\phase6\retention_stub.py` contains only an empty table creation DDL (`create_stub()` for `p6_retention_status_stub`) with columns `(player_id, team, season, status, source, snapshot_date, verification_status, mapping_status, ambiguity_note)`. The docstring explicitly notes: *"no data is imported in Phase 6. The table lives only in the analytical store (exploratory.duckdb). No scoring, ranking, API, service or schema module reads it"*.

### 3.11 Experimental AI Predictions
- **Status:** **4. Designed / Static Only**
- **Evidence:**
  - Precomputed static estimates (`pressureScore`, `baselineScore`, `adjustedPerformance`, `uncertaintyInterval`) exist in `src/data/mock/players.ts`.
  - The mathematical formulas for Empirical Bayes shrinkage and context-adjusted baselines are documented in `DataMethodologyPage.tsx`.
  - However, there are no interactive prediction views, dynamic model parameter sliders, or API connections to trigger machine learning inference.

### 3.12 Model Training / Validation Status
- **Status:** **2. Implemented (Mock Data)**
- **Evidence:**
  - Located in `D:\Data\frontend\src\features\methodology\DataMethodologyPage.tsx` under tabs `'gates'` and `'train-val-test'`.
  - Status indicators display TRAIN, VALIDATION, and TEST statuses, and prominently feature the mandatory disclaimer:
    > *"We explicitly disclose to competition evaluators that the previous TEST holdout set was accessed in Phase 4 of model development. Consequently, the final refit cannot be claimed as an independent, untouched out-of-sample validation. The rankings are presented with full integrity as provisional and experimental."*
  - Topbar contains an amber warning pill: `EXPERIMENTAL (UNVALIDATED)`.
  - `DemoBanner.tsx` displays: `Methodology Status: INTERNAL_EXPERIMENTAL_ONLY. Previous TEST holdout accessed in Phase 4. Rankings provisional under 70:30 combined criteria.`
  - Data reality: All status indicators are hardcoded in the TSX template rather than queried from backend endpoints (`/meta/publication-gates`).

### 3.13 Responsive Desktop and Mobile Layouts
- **Status:** **1. Implemented & Working**
- **Evidence:**
  - Layout shell in `D:\Data\frontend\src\components\layout\Shell.tsx`.
  - Sidebar in `D:\Data\frontend\src\components\layout\Sidebar.tsx`:
    - Desktop: Persistent, collapsible sidebar with width toggle (`w-64` vs `w-16`).
    - Mobile: Hidden by default (`hidden md:block`), slides in as an overlay drawer (`isMobileDrawerOpen`) with a semi-transparent backdrop.
  - Topbar in `D:\Data\frontend\src\components\layout\Topbar.tsx`:
    - Responsive header with hamburger menu button for mobile screens (`md:hidden`).
    - Compact search input (`w-36 sm:w-56 md:w-64`).
    - Data window indicators hide on smaller viewports (`hidden lg:flex`).
  - Breakpoints: Standard Tailwind breakpoints (`sm:`, `md:`, `lg:`, `xl:`) applied across cards and tables.

---

## 4. Phase 6 Governance & Compliance Audit

Phase 6 backend documentation (`backend_implementation_spec.md`, `phase6_design.md`, and `frontend_backend_contracts.md`) establishes five non-negotiable rules. The frontend was audited against each:

### 1. No Unvalidated Public Pressure Rankings
- **Rule:** The public API answers `403 PUBLICATION_GATE_NOT_SATISFIED` with no rows unless every publication gate passes.
- **Frontend Audit Finding:**
  - The frontend is completely decoupled from the backend and displays Top 10 Batters and Bowlers rankings.
  - **Compliance Mitigations in Place:**
    - The UI does not claim these rankings are official or validated.
    - Every ranking view is prominently stamped with `EXPERIMENTAL_NOT_VALIDATED` and `INTERNAL_EXPERIMENTAL_ONLY`.
    - The top banner and methodology pages explicitly disclose that the test holdout was accessed in Phase 4.
  - **Gap:** If connected directly to the public backend router (`/api/v1/rankings/...`), the requests would be rejected with HTTP 403. The frontend is currently operating in "internal terminal" mode rather than consuming public endpoints.

### 2. No Bypassing Eligibility or Data-Weight Gates
- **Rule:** Minimum 100 pressure balls, 10 distinct matches, and 70:30 data-weight gate must be strictly enforced.
- **Frontend Audit Finding:** **Compliant.**
  - In `WhySelectedPage.tsx` and `DataMethodologyPage.tsx`, players who failed the 100-ball sample gate (Aman Rao, 68 balls), 10-match gate (Dewald Brevis, 9 matches; Mohsin Khan, 8 matches), or 70:30 data-weight gate (Kartik Sharma) are strictly barred from the Top 10 and classified in the failure audit log.

### 3. Public `/players` Remains Descriptive-Only
- **Rule:** In Phase 6, public `GET /api/v1/players` returns only `PublicPlayerRow` (identity, classification, matches; no scores, no rank, no intervals, no eligibility).
- **Frontend Audit Finding:**
  - The dedicated descriptive directory component `src/features/player-explorer/PlayerExplorer.tsx` exists in the codebase but includes a `pressureScore` column.
  - However, `PlayerExplorer.tsx` is **not included in the active navigation** (`Shell.tsx`).
  - **Action Required for Backend Integration:** If a public `/players` view is exposed, its table must remove `pressureScore`, `reliability`, and `eligibility` columns to conform to `PublicPlayerRow`.

### 4. Internal Predictions Remain Protected
- **Rule:** Token protection (`require_internal` / `X-Admin-Token`) required to view scores, ranks, and intervals.
- **Frontend Audit Finding:**
  - The frontend currently has no token configuration, login screen, or `X-Admin-Token` header injection.
  - All data is bundled in static mock files and rendered in client-side memory.

### 5. No Fake or Fabricated Player Metrics
- **Rule:** Mock statistics must not be claimed as actual verified cricket statistics.
- **Frontend Audit Finding:** **Compliant.**
  - `DemoBanner.tsx` and the page headers explicitly state that all statistics, rankings, and indices are demonstration/illustrative research estimates.

---

## 5. Backend vs. Frontend Integration Gap Analysis

| Backend Component / Endpoint | Frontend Consumer | Integration Status | Notes / Gaps |
|---|---|---|---|
| `GET /api/v1/players` (Public) | `playerService.getPlayers()` | **Disconnected** | Service reads static `MOCK_PLAYERS` array; does not invoke `/api/v1/players`. |
| `GET /api/v1/players/{id}` (Public) | `playerService.getPlayerById()` | **Disconnected** | Service filters local array. |
| `GET /api/v1/internal/players/{id}/profile` | `PlayerProfileModal.tsx` | **Disconnected** | Modal consumes in-memory `Player` object directly. |
| `GET /api/v1/internal/rankings/{role}` | `rankingService.getRankings()` | **Disconnected** | Service sorts local array; backend returns 403 on public router. |
| `GET /api/v1/internal/compare` | `comparisonService.comparePlayers()` | **Disconnected** | Comparison logic runs entirely client-side. |
| `POST /api/v1/internal/selection/custom` | `CustomTop10Builder.tsx` | **Disconnected** | Component exists in repo, but is currently unrouted in `Shell.tsx`. |
| `GET /api/v1/meta/publication-gates` | `DataMethodologyPage.tsx` | **Disconnected** | Gating dashboard displays hardcoded TSX cards. |
| `GET /api/v1/meta/classification-coverage` | `DataMethodologyPage.tsx` | **Disconnected** | Coverage counts displayed are hardcoded. |
| `POST /api/v1/admin/classification/reload` | None | **Missing** | No admin reload UI exists in frontend. |
| `p6_retention_status_stub` (DuckDB) | None | **Missing** | No retention interface or API exists. |

---

## 6. Summary of Missing Work

1. **Retention Importer:**
   - No UI exists to upload, parse, or view player retention CSVs.
   - Backend has only the DuckDB table stub `p6_retention_status_stub` (`retention_stub.py`).
2. **Live Backend API Adapter:**
   - No HTTP client (`fetch`/`axios`), base URL configuration, or API error handling is wired up to `http://localhost:8000/api/v1`.
3. **Internal Token Header Configuration:**
   - No mechanism in the UI (e.g. settings input or environment variable `VITE_ADMIN_TOKEN`) to send `X-Admin-Token` to internal backend routes.
4. **Descriptive-Only Public Player Directory:**
   - `PlayerExplorer.tsx` is unrouted in `Shell.tsx`. To provide a public directory, it should be routed and stripped of score columns to match `PublicPlayerRow`.
5. **Dynamic AI Model Predictions:**
   - No interactive prediction sandbox or live inference trigger is implemented.

---

## 7. Recommended Minimal Fixes (Pending User Approval)

If live backend integration or retention functionality is desired in a future step, the recommended minimal changes are:

1. **Create an API Client Layer (`src/lib/api.ts`):**
   - Provide a clean `fetch` wrapper configured with `VITE_API_BASE_URL` (defaulting to `http://localhost:8000/api/v1`) and optional `X-Admin-Token` header.
   - Fall back gracefully to `MOCK_PLAYERS` if the backend is unreachable.
2. **Wire Live Gating & Metadata:**
   - In `DataMethodologyPage.tsx`, query `/api/v1/meta/publication-gates` and `/api/v1/meta/classification-coverage` to display real-time gate statuses from DuckDB.
3. **Add Retention Importer Component (`src/features/retention/RetentionImporter.tsx`):**
   - Provide a drag-and-drop CSV importer for official franchise retention lists, validating columns against `p6_retention_status_stub` schema (`player_id, team, season, status, source, verification_status`).
4. **Expose Public Descriptive Directory:**
   - Add a "Player Directory" navigation item routing to `PlayerExplorer.tsx`, with a toggle hiding pressure scores unless internal mode is active.

---

*End of Audit Report. No files or code have been modified.*
