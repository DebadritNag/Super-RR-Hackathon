import React, { useState } from 'react';
import {
  BookOpen,
  Database,
  Layers,
  ShieldCheck,
  AlertTriangle,
  FileText,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  Code,
  Info,
  Scale,
} from 'lucide-react';
import { OrganizerSourceFile } from '@/types';

export const DataMethodologyPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'sources' | 'why-data' | 'pipeline' | 'gates' | 'train-val-test' | 'limitations'>('pipeline');

  // A. Actual Organizer-Provided Source Files
  const sourceFiles: OrganizerSourceFile[] = [
    {
      fileName: 'ipl_deliveries.csv / ipl_matches.csv',
      dataType: 'Ball-by-Ball Match Events',
      recordCount: '243,820 deliveries across 883 matches',
      keyFields: ['match_id', 'inning', 'over', 'ball', 'batter', 'bowler', 'runs_off_bat', 'extras', 'wicket_type', 'player_dismissed'],
      purpose: 'Primary match-state reconstruction, balls remaining, target delta, and innings leverage index calculation.',
      selectionJustification: 'Granular ball-by-ball delivery logging is the foundational requirement to compute pressure metrics.',
      inclusionStatus: 'Primary Calculation',
    },
    {
      fileName: 'ipl_squads_2024_2026.csv',
      dataType: 'Roster & Official Squad Registry',
      recordCount: '257 auction pool players & franchise retained rosters',
      keyFields: ['player_name', 'ipl_team', 'player_role', 'speciality', 'capped_status', 'auction_category'],
      purpose: 'Verification of player franchise affiliation, primary position designations, and eligibility screening.',
      selectionJustification: 'Ensures player entity identification aligns exactly with official IPL franchise registration records.',
      inclusionStatus: 'Primary Calculation',
    },
    {
      fileName: 'player_mapping_registry.json',
      dataType: 'Cross-Source Entity Mapping',
      recordCount: '1,217 deduplicated player identities',
      keyFields: ['canonical_player_id', 'cricsheet_id', 'ipl_official_id', 'full_name', 'alternate_names'],
      purpose: 'Eliminates identifier collisions and ensures delivery attribution links correctly to historical careers.',
      selectionJustification: 'Without canonical entity mapping, multi-season spelling variations corrupt cumulative sample size.',
      inclusionStatus: 'Primary Calculation',
    },
    {
      fileName: 'supplementary_t20_historical.json',
      dataType: 'T20 Domestic & International Feeds',
      recordCount: '48,200 non-IPL deliveries (Syed Mushtaq Ali & T20Is)',
      keyFields: ['event_type', 'date', 'batter_id', 'bowler_id', 'runs', 'phase'],
      purpose: 'Secondary baseline calibration for emerging uncapped candidates with limited IPL exposure.',
      selectionJustification: 'Used exclusively under Section 5.3 data-weight gating rules (70:30 combined weighting).',
      inclusionStatus: 'Supplementary Check',
    },
  ];

  // C. 9-Step Methodology Flow
  const pipelineSteps = [
    {
      step: 1,
      title: 'Raw Match & Delivery Ingestion',
      desc: 'Ingests verified ball-by-ball records (883 matches) from official tournament archives, validating delivery timestamps, extras, and wicket tags.',
    },
    {
      step: 2,
      title: 'Match-State Reconstruction',
      desc: 'Reconstructs continuous game state at every ball: current score, wickets fallen, balls remaining, target score, required run rate, and current run rate.',
    },
    {
      step: 3,
      title: 'Pressure Situation Identification',
      desc: 'Filters high-leverage deliveries using a composite condition: Leverage Index > 1.5, required run rate > 9.0 in chases, or overs 16–20 in close contests.',
    },
    {
      step: 4,
      title: 'Context-Adjusted Baseline Estimation',
      desc: 'Calculates the expected run rate and expected wicket probability for every delivery based on venue scoring par, innings phase, and bowling discipline.',
    },
    {
      step: 5,
      title: 'Player Performance Residuals',
      desc: 'Decouples actual outcome from expectation: Batters receive scoring residual above par (+runs); Bowlers receive negated run suppression residual (-runs).',
    },
    {
      step: 6,
      title: 'Sample-Size & Reliability Controls',
      desc: 'Applies Empirical Bayes shrinkage to regress low-volume noise toward tournament prior, penalizing players with small or high-variance samples.',
    },
    {
      step: 7,
      title: 'Regulatory & Data-Weight Gating',
      desc: 'Enforces minimum 100 pressure balls, 10 distinct matches, and strict 70:30 domestic-to-IPL sample weighting before ranking eligibility.',
    },
    {
      step: 8,
      title: 'Batter & Bowler Scoring Systems',
      desc: 'Generates decoupled composite scores: Batters scored on run volume, SR uplift & dot avoidance; Bowlers scored on economy suppression & death wickets.',
    },
    {
      step: 9,
      title: 'Final Ranking & Roster Generation',
      desc: 'Produces final Top 10 Batters and Top 10 Bowlers rosters, complete with 90% Bayesian credible intervals and explicit failure audit trails.',
    },
  ];

  // D. Gating Status Dashboard
  const gates = [
    {
      name: 'Minimum Pressure Opportunities Gate',
      requirement: '≥ 100 deliveries faced or bowled in high-leverage situations',
      status: 'PASSED',
      passed: true,
      notes: 'All 20 selected players exceed 180+ balls; unselected players under 100 balls isolated in audit log.',
    },
    {
      name: 'Distinct Matches Requirement',
      requirement: '≥ 10 distinct match appearances across evaluation window',
      status: 'PASSED',
      passed: true,
      notes: 'Eliminates single-match wonder bias; protects against high-variance tournament outliers.',
    },
    {
      name: 'Data-Weight Gate (70:30 Combined)',
      requirement: 'IPL primary weight ≥ 70%, domestic supplementary weight ≤ 30%',
      status: 'EXPERIMENTAL',
      passed: false,
      isWarning: true,
      notes: 'Strict data-weight gate passed for Top 10 core, but full cross-dataset reliability remains provisional.',
    },
    {
      name: 'Strict Classification Gate',
      requirement: 'Verified Capped vs Derived Capped vs Unknown distinction',
      status: 'PASSED',
      passed: true,
      notes: 'No Unknown players labelled as uncapped; capped status derived only from verified T20I appearances.',
    },
    {
      name: 'Methodology Validation Gate',
      requirement: 'Independent out-of-sample holdout validation without leakage',
      status: 'EXPERIMENTAL_NOT_VALIDATED',
      passed: false,
      isDanger: true,
      notes: 'Phase 4 test set was previously evaluated; system is transparently labelled as unvalidated.',
    },
  ];

  return (
    <div className="space-y-6 select-none">
      {/* Top Header Card */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-[#246B4B]/10 text-[#246B4B] flex items-center justify-center font-bold">
              <BookOpen className="w-4 h-4" />
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-[#202522] tracking-tight">
              Data Governance & 9-Step Methodology
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-bold bg-[#D97736] text-white rounded">
              Auditor Report
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#777F79] mt-1 leading-relaxed">
            Full technical transparency: official sources, mathematical formulations, Bayesian shrinkage, gating audit, and Phase 4 disclosure.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-[#F7F6F2] p-1 rounded-lg border border-[#E5E8E3] text-xs font-semibold shrink-0 overflow-x-auto">
          <button
            onClick={() => setActiveTab('pipeline')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'pipeline' ? 'bg-[#246B4B] text-white' : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            9-Step Pipeline
          </button>
          <button
            onClick={() => setActiveTab('sources')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'sources' ? 'bg-[#246B4B] text-white' : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            Data Sources
          </button>
          <button
            onClick={() => setActiveTab('why-data')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'why-data' ? 'bg-[#246B4B] text-white' : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            Why This Data?
          </button>
          <button
            onClick={() => setActiveTab('gates')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'gates' ? 'bg-[#246B4B] text-white' : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            Gating Status
          </button>
          <button
            onClick={() => setActiveTab('train-val-test')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'train-val-test' ? 'bg-[#246B4B] text-white' : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            Train / Val / Test
          </button>
          <button
            onClick={() => setActiveTab('limitations')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'limitations' ? 'bg-[#246B4B] text-white' : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            Limitations
          </button>
        </div>
      </div>

      {/* ======================================================== */}
      {/* SECTION 1: 9-STEP METHODOLOGY PIPELINE FLOW */}
      {/* ======================================================== */}
      {activeTab === 'pipeline' && (
        <div className="space-y-6">
          <div className="p-4 bg-white rounded-xl border border-[#E5E8E3] shadow-xs">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
              <Layers className="w-4 h-4 text-[#246B4B]" />
              <span>Pressure Performance Pipeline Architecture</span>
            </h2>
            <p className="text-xs text-[#777F79] mt-0.5">
              Visual overview of the mathematical transformation from raw delivery telemetry to final ranked rosters
            </p>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              {pipelineSteps.map((step) => (
                <div
                  key={step.step}
                  className="bg-[#F7F6F2] p-4 rounded-xl border border-[#E5E8E3] space-y-2 relative"
                >
                  <div className="flex items-center justify-between">
                    <span className="w-6 h-6 rounded-full bg-[#246B4B] text-white flex items-center justify-center font-bold text-xs">
                      {step.step}
                    </span>
                    <span className="text-[10px] font-bold text-[#777F79] uppercase">
                      Stage {step.step}/9
                    </span>
                  </div>
                  <h3 className="text-xs font-bold text-[#202522]">
                    {step.title}
                  </h3>
                  <p className="text-[11px] text-[#777F79] leading-relaxed">
                    {step.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Mathematical Formulations Callout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-2 text-xs">
              <div className="font-bold text-[#202522] uppercase tracking-wider text-xs">
                Batter Pressure Score Formulation
              </div>
              <div className="font-mono bg-[#F7F6F2] p-2.5 rounded border border-[#E5E8E3] text-[#202522] text-[11px] leading-relaxed">
                Score(Batter) = w1·Residual(Runs) + w2·Uplift(SR) + w3·(1 - DotRate) + w4·BoundaryRate
              </div>
              <div className="text-[11px] text-[#777F79] pt-2 border-t border-[#E5E8E3]">
                Shrunk via Empirical Bayes: theta_hat_i = B_i · y_bar + (1 - B_i) · y_i, where shrinkage factor B_i = sigma^2 / (sigma^2 + tau^2 · n_i).
              </div>
            </div>

            <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-2 text-xs">
              <div className="font-bold text-[#202522] uppercase tracking-wider text-xs">
                Bowler Pressure Score Formulation (Negated Residual)
              </div>
              <div className="font-mono bg-[#F7F6F2] p-2.5 rounded border border-[#E5E8E3] text-[#202522] text-[11px] leading-relaxed">
                Score(Bowler) = w1·(-Residual(RunsConceded)) + w2·DotRate + w3·ClutchWickets
              </div>
              <div className="text-[11px] text-[#777F79] pt-2 border-t border-[#E5E8E3]">
                Suppression residual is negated so that bowlers who concede fewer runs than the contextual phase expectation receive positive scores.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 2: ORGANIZER-PROVIDED SOURCE FILES */}
      {/* ======================================================== */}
      {activeTab === 'sources' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs overflow-hidden">
            <div className="p-4 border-b border-[#E5E8E3]">
              <h2 className="text-sm font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
                <Database className="w-4 h-4 text-[#246B4B]" />
                <span>Organizer-Provided Data Files Used</span>
              </h2>
              <p className="text-xs text-[#777F79] mt-0.5">
                Exact file inventory, record dimensions, schema fields, and roles in primary vs supplementary calculation
              </p>
            </div>

            <div className="divide-y divide-[#E5E8E3]">
              {sourceFiles.map((file, idx) => (
                <div key={idx} className="p-4 sm:p-5 hover:bg-[#F7F6F2] transition-colors space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono font-bold text-xs text-[#202522]">
                          {file.fileName}
                        </span>
                        <span
                          className={`text-[9px] font-bold px-2 py-0.5 rounded ${
                            file.inclusionStatus === 'Primary Calculation'
                              ? 'bg-emerald-100 text-[#246B4B]'
                              : 'bg-amber-100 text-[#D97736]'
                          }`}
                        >
                          {file.inclusionStatus}
                        </span>
                      </div>
                      <div className="text-xs text-[#777F79] mt-0.5">{file.dataType} • {file.recordCount}</div>
                    </div>
                  </div>

                  <div className="text-xs text-[#202522] leading-relaxed">
                    <strong>Model Purpose:</strong> {file.purpose}
                  </div>

                  <div className="text-xs text-[#777F79] leading-relaxed">
                    <strong>Selection Justification:</strong> {file.selectionJustification}
                  </div>

                  <div className="pt-2 border-t border-[#E5E8E3] flex flex-wrap gap-1">
                    <span className="text-[10px] font-bold text-[#777F79] mr-2">Key Fields:</span>
                    {file.keyFields.map((field, fIdx) => (
                      <span key={fIdx} className="text-[10px] font-mono bg-white border border-[#E5E8E3] px-1.5 py-0.5 rounded text-[#202522]">
                        {field}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 3: WHY THIS DATA? */}
      {/* ======================================================== */}
      {activeTab === 'why-data' && (
        <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-5 text-xs">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
              <HelpCircle className="w-4 h-4 text-[#246B4B]" />
              <span>Data Selection Justification & Data Hygiene Principles</span>
            </h2>
            <p className="text-xs text-[#777F79] mt-0.5">
              Why specific data sources were required and how data integrity was protected
            </p>
          </div>

          <div className="space-y-4">
            <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1.5">
              <div className="font-bold text-[#202522]">1. Why Ball-by-Ball Telemetry is Mandatory</div>
              <p className="text-[#777F79] leading-relaxed">
                Aggregate season totals (runs, wickets, strike rate, economy) blend junk-time runs with high-leverage deliveries. 
                Only ball-by-ball records enable calculating the exact required run rate, balls remaining, wickets in hand, and context at the moment the ball is delivered.
              </p>
            </div>

            <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1.5">
              <div className="font-bold text-[#202522]">2. Role of Playing XI & Player Mapping</div>
              <p className="text-[#777F79] leading-relaxed">
                Over an 18-season evaluation span, player name spelling variants (e.g. "Sandeep Sharma" vs "S Sharma", "N Pooran" vs "Nicholas Pooran") cause severe identity fragmentations. 
                A single canonical player registry is mandatory so that career delivery samples do not fragment across duplicate entities.
              </p>
            </div>

            <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1.5">
              <div className="font-bold text-[#202522]">3. Strict Prohibition Against Uncontrolled Supplementary Data</div>
              <p className="text-[#777F79] leading-relaxed">
                Supplementary domestic leagues (e.g. state T20 tournaments) feature disparate quality baselines, smaller ground dimensions, and variable bowling attacks. 
                Allowing supplementary records to silently dilute official IPL records corrupts rankings. Therefore, external data is strictly restricted to secondary validation under the 70:30 data-weight gate.
              </p>
            </div>

            <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1.5">
              <div className="font-bold text-[#202522]">4. Treatment of Missing, Unresolved, or Inconsistent Records</div>
              <p className="text-[#777F79] leading-relaxed">
                Where match records feature missing ball coordinates or ambiguous run attribution, deliveries are flagged as provisional. If a player’s identity cannot be resolved against the official auction registry, they are quarantined in the exclusion audit log rather than assigned fabricated estimates.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 4: GATING & RELIABILITY DASHBOARD */}
      {/* ======================================================== */}
      {activeTab === 'gates' && (
        <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs overflow-hidden">
          <div className="p-4 border-b border-[#E5E8E3]">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-[#246B4B]" />
              <span>Gating Verification Status & Reliability Bounds</span>
            </h2>
            <p className="text-xs text-[#777F79] mt-0.5">
              Live audit status for each regulatory gate mandated by competition contracts
            </p>
          </div>

          <div className="divide-y divide-[#E5E8E3]">
            {gates.map((gate, idx) => (
              <div key={idx} className="p-4 sm:p-5 hover:bg-[#F7F6F2] transition-colors space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {gate.passed ? (
                      <CheckCircle2 className="w-4 h-4 text-[#246B4B]" />
                    ) : (
                      <AlertTriangle className={`w-4 h-4 ${gate.isDanger ? 'text-[#C44747]' : 'text-[#D97736]'}`} />
                    )}
                    <h3 className="text-xs font-bold text-[#202522]">
                      {gate.name}
                    </h3>
                  </div>

                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                      gate.passed
                        ? 'bg-emerald-50 text-[#246B4B] border-emerald-200'
                        : gate.isDanger
                        ? 'bg-red-50 text-[#C44747] border-red-200'
                        : 'bg-amber-50 text-[#D97736] border-amber-200'
                    }`}
                  >
                    {gate.status}
                  </span>
                </div>

                <div className="text-xs text-[#777F79]">
                  <strong>Requirement:</strong> {gate.requirement}
                </div>

                <p className="text-xs text-[#202522] leading-relaxed">
                  {gate.notes}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 5: TRAIN / VAL / TEST PHASE 4 DISCLOSURE */}
      {/* ======================================================== */}
      {activeTab === 'train-val-test' && (
        <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-5 text-xs">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
              <Scale className="w-4 h-4 text-[#D97736]" />
              <span>Dataset Split & Phase 4 Holdout Disclosure</span>
            </h2>
            <p className="text-xs text-[#777F79] mt-0.5">
              Transparent report on model partition state and previous test set access
            </p>
          </div>

          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2 text-[#202522]">
            <div className="flex items-center space-x-2 font-bold text-amber-900 text-sm">
              <AlertTriangle className="w-4 h-4 text-[#D97736]" />
              <span>Mandatory Disclosure: Previous TEST Holdout Access</span>
            </div>
            <p className="leading-relaxed">
              We explicitly disclose to competition evaluators that the previous <strong>TEST holdout set was accessed in Phase 4</strong> of model development. 
              Consequently, the final refit cannot be claimed as an independent, untouched out-of-sample validation. 
              The rankings are presented with full integrity as <strong>provisional and experimental</strong>.
            </p>
          </div>

          {/* Status Indicators for Splits */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] text-center space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-[#777F79]">TRAIN Split</div>
              <div className="text-sm font-black text-[#202522]">2008–2023</div>
              <div className="text-[10px] text-emerald-700 font-semibold">Completed</div>
            </div>

            <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] text-center space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-[#777F79]">VALIDATION Split</div>
              <div className="text-sm font-black text-[#202522]">2024 Early Season</div>
              <div className="text-[10px] text-emerald-700 font-semibold">Completed</div>
            </div>

            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-center space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-[#D97736]">TEST Split</div>
              <div className="text-sm font-black text-[#D97736]">2024 Playoff / 2025</div>
              <div className="text-[10px] text-amber-800 font-semibold">Accessed (Phase 4)</div>
            </div>

            <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] text-center space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-[#777F79]">FINAL REFIT</div>
              <div className="text-sm font-black text-[#202522]">Provisional 70:30</div>
              <div className="text-[10px] text-[#246B4B] font-semibold">Active Submission</div>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 6: METHODOLOGY LIMITATIONS */}
      {/* ======================================================== */}
      {activeTab === 'limitations' && (
        <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-5 text-xs">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-[#C44747]" />
              <span>Documented Methodology Limitations & Residual Risks</span>
            </h2>
            <p className="text-xs text-[#777F79] mt-0.5">
              Explicit engineering caveats and statistical boundaries
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1">
              <div className="font-bold text-[#202522]">Low Split-Half Reliability</div>
              <p className="text-[#777F79] leading-relaxed">
                T20 cricket is inherently subject to small sample sizes in extreme leverage overs. Split-half cross validation yields an r ≈ 0.42 correlation, indicating that clutch variance remains partially noisy despite shrinkage.
              </p>
            </div>

            <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1">
              <div className="font-bold text-[#202522]">Pressure Definition Sensitivity</div>
              <p className="text-[#777F79] leading-relaxed">
                Altering the leverage cutoff (e.g. LI &gt; 1.5 vs LI &gt; 1.8) results in minor rank shifts for fringe candidates (Ranks 8–12), demonstrating moderate sensitivity to definition boundaries.
              </p>
            </div>

            <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1">
              <div className="font-bold text-[#202522]">Shrinkage-Floor Behaviour</div>
              <p className="text-[#777F79] leading-relaxed">
                For emerging players with exactly 100–120 balls, Empirical Bayes shrinkage regresses scores heavily toward the prior, which may slightly underestimate high-ceiling newcomers like Ashutosh Sharma or Priyansh Arya.
              </p>
            </div>

            <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1">
              <div className="font-bold text-[#202522]">Absence of Fielding & Fitness Telemetry</div>
              <p className="text-[#777F79] leading-relaxed">
                Rankings currently evaluate delivery-level bat and ball events only. Catches dropped under pressure, ground fielding saves, and physical workload endurance are not modeled in the current phase.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
