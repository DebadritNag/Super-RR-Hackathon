import React, { useState } from 'react';
import { useApp } from '@/context/AppContext';
import {
  HelpCircle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Scale,
  Shield,
  Filter,
  Trophy,
  Target,
  ArrowRight,
  Sparkles,
  Info,
} from 'lucide-react';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { Player, FailureReasonCategory } from '@/types';
import { formatScore } from '@/lib/utils';
import { PlayerRadarChart } from '@/components/charts/PlayerRadarChart';

export const WhySelectedPage: React.FC = () => {
  const { openPlayerProfile, setComparisonPlayers, setActiveSection } = useApp();

  // Active Tab: 'selected' | 'not-selected' | 'head-to-head-decider'
  const [activeTab, setActiveTab] = useState<'selected' | 'not-selected' | 'head-to-head-decider'>('selected');
  const [selectedDiscipline, setSelectedDiscipline] = useState<'all' | 'batters' | 'bowlers'>('all');
  const [failureCategoryFilter, setFailureCategoryFilter] = useState<string>('all');

  // Head-to-Head interactive decider state
  const top10Batters = MOCK_PLAYERS.filter(p => p.isSelectedTop10 && (p.role === 'Batter' || p.role === 'Wicketkeeper'));
  const top10Bowlers = MOCK_PLAYERS.filter(p => p.isSelectedTop10 && (p.role === 'Bowler' || (p.role === 'All-rounder' && p.bowlerRadar)));
  const unselectedCandidates = MOCK_PLAYERS.filter(p => !p.isSelectedTop10);

  const [selectedPlayerId, setSelectedPlayerId] = useState<string>(top10Batters[0]?.id || 'p-101');
  const [unselectedPlayerId, setUnselectedPlayerId] = useState<string>(unselectedCandidates[0]?.id || 'p-301');

  const playerSelectedObj = MOCK_PLAYERS.find(p => p.id === selectedPlayerId) || top10Batters[0];
  const playerUnselectedObj = MOCK_PLAYERS.find(p => p.id === unselectedPlayerId) || unselectedCandidates[0];

  // Selected 10 Batters & 10 Bowlers
  const selectedPlayers = MOCK_PLAYERS.filter(p => {
    if (!p.isSelectedTop10) return false;
    if (selectedDiscipline === 'batters') return p.role === 'Batter' || p.role === 'Wicketkeeper';
    if (selectedDiscipline === 'bowlers') return p.role === 'Bowler' || (p.role === 'All-rounder' && p.bowlerRadar);
    return true;
  }).sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0));

  // Not Selected candidates filter
  const filteredUnselected = unselectedCandidates.filter(p => {
    if (selectedDiscipline === 'batters') {
      const isBatter = p.role === 'Batter' || p.role === 'Wicketkeeper';
      if (!isBatter) return false;
    } else if (selectedDiscipline === 'bowlers') {
      const isBowler = p.role === 'Bowler' || (p.role === 'All-rounder' && p.bowlerRadar);
      if (!isBowler) return false;
    }
    if (failureCategoryFilter !== 'all' && p.unselectedCategory !== failureCategoryFilter) {
      return false;
    }
    return true;
  });

  const getCategoryBadge = (category?: FailureReasonCategory) => {
    switch (category) {
      case 'below-cutoff':
        return { label: 'Below Ranking Cutoff', color: 'bg-gray-100 text-gray-800 border-gray-200' };
      case 'insufficient-opportunities':
        return { label: 'Sample < 100 Balls', color: 'bg-red-50 text-red-800 border-red-200' };
      case 'insufficient-matches':
        return { label: 'Matches < 10 Gate', color: 'bg-amber-50 text-amber-800 border-amber-200' };
      case 'failed-data-weight-gate':
        return { label: 'Failed 70:30 Data Gate', color: 'bg-orange-50 text-orange-800 border-orange-200' };
      case 'missing-mapping':
        return { label: 'Entity Mapping Flag', color: 'bg-purple-50 text-purple-800 border-purple-200' };
      case 'high-uncertainty':
        return { label: 'High Variance / Wide CI', color: 'bg-yellow-50 text-yellow-800 border-yellow-200' };
      case 'extreme-variance':
        return { label: 'Extreme Leverage Swings', color: 'bg-pink-50 text-pink-800 border-pink-200' };
      default:
        return { label: 'Data Restriction', color: 'bg-gray-100 text-gray-700 border-gray-200' };
    }
  };

  return (
    <div className="space-y-6 select-none">
      {/* Top Header Card */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-[#246B4B]/10 text-[#246B4B] flex items-center justify-center font-bold">
              <HelpCircle className="w-4 h-4" />
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-[#202522] tracking-tight">
              Why Selected / Why Not Selected
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-bold bg-[#246B4B] text-white rounded">
              Audit Transparency
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#777F79] mt-1 leading-relaxed">
            Rigorous justification for the 20 selected players, detailed gate failure taxonomy for excluded candidates, and head-to-head exclusion audits.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-[#F7F6F2] p-1 rounded-lg border border-[#E5E8E3] text-xs font-semibold shrink-0">
          <button
            onClick={() => setActiveTab('selected')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'selected'
                ? 'bg-[#246B4B] text-white shadow-xs'
                : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            Selected (20)
          </button>
          <button
            onClick={() => setActiveTab('not-selected')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'not-selected'
                ? 'bg-[#246B4B] text-white shadow-xs'
                : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            Not Selected
          </button>
          <button
            onClick={() => setActiveTab('head-to-head-decider')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
              activeTab === 'head-to-head-decider'
                ? 'bg-[#246B4B] text-white shadow-xs'
                : 'text-[#777F79] hover:text-[#202522]'
            }`}
          >
            Head-to-Head Decider
          </button>
        </div>
      </div>

      {/* Filter Bar (for Tab 1 & 2) */}
      {activeTab !== 'head-to-head-decider' && (
        <div className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold text-[#777F79] uppercase">Discipline:</span>
            <div className="flex space-x-1">
              {(['all', 'batters', 'bowlers'] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setSelectedDiscipline(d)}
                  className={`px-2.5 py-1 text-xs rounded font-semibold transition-colors cursor-pointer capitalize ${
                    selectedDiscipline === d
                      ? 'bg-[#246B4B] text-white'
                      : 'bg-[#F7F6F2] text-[#777F79] hover:bg-stone-200'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {activeTab === 'not-selected' && (
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-[#777F79] uppercase">Failure Reason:</span>
              <select
                value={failureCategoryFilter}
                onChange={(e) => setFailureCategoryFilter(e.target.value)}
                aria-label="Filter by failure reason"
                className="text-xs bg-[#F7F6F2] border border-[#E5E8E3] rounded px-2.5 py-1 text-[#202522] focus:outline-none focus:border-[#246B4B] cursor-pointer"
              >
                <option value="all">All Exclusion Categories</option>
                <option value="below-cutoff">Below Ranking Cutoff</option>
                <option value="insufficient-opportunities">Sample &lt; 100 Balls Gate</option>
                <option value="insufficient-matches">Matches &lt; 10 Gate</option>
                <option value="failed-data-weight-gate">Failed 70:30 Data Gate</option>
                <option value="missing-mapping">Player Mapping Collision</option>
                <option value="extreme-variance">Extreme Leverage Variance</option>
              </select>
            </div>
          )}
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 1: SELECTED PLAYERS (10 BATTERS + 10 BOWLERS) */}
      {/* ======================================================== */}
      {activeTab === 'selected' && (
        <div className="space-y-4">
          <div className="text-xs text-[#777F79] flex items-center justify-between">
            <span>Displaying {selectedPlayers.length} verified selections</span>
            <span>All selections passed minimum 100 pressure balls and Bayesian shrinkage validation</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {selectedPlayers.map((player) => (
              <div
                key={player.id}
                className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs flex flex-col justify-between space-y-4 hover:border-[#246B4B] transition-colors"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="w-5 h-5 rounded-full bg-[#246B4B] text-white flex items-center justify-center font-bold text-[10px]">
                          ✓
                        </span>
                        <span className="text-xs font-bold uppercase tracking-wider text-[#246B4B]">
                          {player.role === 'Bowler' ? 'Pressure Bowler' : 'Pressure Batter'}
                        </span>
                        <span className="text-[10px] text-[#777F79]">({player.id})</span>
                      </div>
                      <h3 className="text-base font-bold text-[#202522] mt-1">
                        {player.name}
                      </h3>
                      <div className="text-xs text-[#777F79]">
                        {player.team} • {player.speciality} • {player.nationality}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-xl font-black text-[#246B4B]">
                        {formatScore(player.pressureScore)}
                      </div>
                      <div className="text-[9px] text-[#777F79]">
                        {player.role === 'Bowler' ? 'Residual suppression' : `+${player.adjustedPerformance}% uplift`}
                      </div>
                    </div>
                  </div>

                  {/* Quantitative Rationale */}
                  <div className="mt-3 p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] text-xs space-y-1.5">
                    <div className="font-semibold text-[#202522]">
                      Selection Rationale:
                    </div>
                    <p className="text-[#777F79] leading-relaxed">
                      {player.rankingRationale}
                    </p>
                  </div>
                </div>

                <div className="pt-3 border-t border-[#E5E8E3] flex items-center justify-between text-xs">
                  <div className="text-[#777F79] text-[11px]">
                    <strong>Sample:</strong> {player.sampleSize} balls • {player.matches} matches •{' '}
                    {player.uncertaintyInterval ? `[${player.uncertaintyInterval[0]} - ${player.uncertaintyInterval[1]}]` : 'High confidence'}
                  </div>
                  <button
                    onClick={() => openPlayerProfile(player)}
                    className="font-bold text-[#246B4B] hover:underline flex items-center space-x-1 cursor-pointer shrink-0"
                  >
                    <span>Full Profile</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 2: NOT SELECTED CANDIDATES & TAXONOMY */}
      {/* ======================================================== */}
      {activeTab === 'not-selected' && (
        <div className="space-y-4">
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-[#202522] flex items-start space-x-3">
            <Info className="w-4 h-4 text-[#D97736] shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <strong className="text-[#D97736]">Auditor Note on Excluded Candidates:</strong> An unselected player is <strong>not</strong> necessarily an ineffective player. 
              The system rigorously distinguishes between players who performed strongly but faced an insufficient sample size (&lt;100 balls), 
              players who were eligible but finished just outside the Top 10 cutoff, and players whose data failed weighting or multi-season deduplication gates.
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredUnselected.map((player) => {
              const badge = getCategoryBadge(player.unselectedCategory);
              return (
                <div
                  key={player.id}
                  className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs flex flex-col justify-between space-y-4 hover:border-gray-400 transition-colors"
                >
                  <div>
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${badge.color}`}>
                            {badge.label}
                          </span>
                          <span className="text-[10px] text-[#777F79]">({player.id})</span>
                        </div>
                        <h3 className="text-base font-bold text-[#202522] mt-1.5">
                          {player.name}
                        </h3>
                        <div className="text-xs text-[#777F79]">
                          {player.team} • {player.speciality} • {player.nationality}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-lg font-bold text-[#777F79]">
                          {player.pressureScore ?? 'N/A'}
                        </div>
                        <div className="text-[9px] text-[#C44747] font-semibold">
                          Excluded from Top 10
                        </div>
                      </div>
                    </div>

                    {/* Explicit Failure Reason Text */}
                    <div className="mt-3 p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] text-xs space-y-1.5">
                      <div className="font-semibold text-[#202522] flex items-center space-x-1.5">
                        <XCircle className="w-3.5 h-3.5 text-[#C44747]" />
                        <span>Exact Reason Not Selected:</span>
                      </div>
                      <p className="text-[#202522] leading-relaxed">
                        {player.unselectedReasonText || player.rankingRationale}
                      </p>
                      {player.unselectedMetricDetail && (
                        <p className="text-[11px] text-[#777F79] italic pt-1 border-t border-[#E5E8E3]">
                          Metric Detail: {player.unselectedMetricDetail}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="pt-3 border-t border-[#E5E8E3] flex items-center justify-between text-xs">
                    <div className="text-[#777F79] text-[11px]">
                      <strong>Observed:</strong> {player.sampleSize} balls • {player.matches} matches •{' '}
                      {player.uncertaintyInterval ? `CI: [${player.uncertaintyInterval[0]} - ${player.uncertaintyInterval[1]}]` : 'N/A'}
                    </div>
                    <button
                      onClick={() => openPlayerProfile(player)}
                      className="font-bold text-[#202522] hover:text-[#246B4B] flex items-center space-x-1 cursor-pointer shrink-0"
                    >
                      <span>Audit Record</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 3: HEAD-TO-HEAD DECIDER (SELECTED VS UNSELECTED) */}
      {/* ======================================================== */}
      {activeTab === 'head-to-head-decider' && (
        <div className="space-y-6">
          <div className="p-4 bg-white rounded-xl border border-[#E5E8E3] shadow-xs space-y-4">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
                <Scale className="w-4 h-4 text-[#246B4B]" />
                <span>Head-to-Head Cutoff Audit: Selected vs Unselected</span>
              </h2>
              <p className="text-xs text-[#777F79] mt-0.5">
                Demonstrates why Candidate A earned a Top 10 roster spot while Candidate B was excluded
              </p>
            </div>

            {/* Candidate Pickers */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-emerald-50/50 p-3.5 rounded-lg border border-emerald-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#246B4B] bg-emerald-100 px-2 py-0.5 rounded">
                    Selected Top 10 Candidate
                  </span>
                  <select
                    value={selectedPlayerId}
                    onChange={(e) => setSelectedPlayerId(e.target.value)}
                    aria-label="Select Top 10 Player"
                    className="text-xs font-semibold bg-white border border-[#E5E8E3] rounded px-2.5 py-1 text-[#202522] cursor-pointer"
                  >
                    {top10Batters.concat(top10Bowlers).map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.role} - {p.pressureScore})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <div className="text-base font-bold text-[#202522]">{playerSelectedObj.name}</div>
                    <div className="text-xs text-[#777F79]">{playerSelectedObj.team} • {playerSelectedObj.speciality}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-black text-[#246B4B]">{playerSelectedObj.pressureScore}</div>
                    <div className="text-[10px] text-emerald-800 font-semibold">{playerSelectedObj.sampleSize} balls (Qualified)</div>
                  </div>
                </div>
              </div>

              <div className="bg-red-50/50 p-3.5 rounded-lg border border-red-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#C44747] bg-red-100 px-2 py-0.5 rounded">
                    Unselected / Excluded Candidate
                  </span>
                  <select
                    value={unselectedPlayerId}
                    onChange={(e) => setUnselectedPlayerId(e.target.value)}
                    aria-label="Select Unselected Player"
                    className="text-xs font-semibold bg-white border border-[#E5E8E3] rounded px-2.5 py-1 text-[#202522] cursor-pointer"
                  >
                    {unselectedCandidates.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.role} - {p.unselectedCategory})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <div className="text-base font-bold text-[#202522]">{playerUnselectedObj.name}</div>
                    <div className="text-xs text-[#777F79]">{playerUnselectedObj.team} • {playerUnselectedObj.speciality}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-black text-gray-500">{playerUnselectedObj.pressureScore ?? 'N/A'}</div>
                    <div className="text-[10px] text-[#C44747] font-semibold">{playerUnselectedObj.eligibility}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Rigorous Comparison Statement */}
            <div className="p-4 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-2">
              <div className="text-xs font-bold text-[#202522] uppercase tracking-wider">
                Why {playerSelectedObj.name} Ranks Above {playerUnselectedObj.name}:
              </div>
              <p className="text-xs text-[#202522] leading-relaxed">
                {playerSelectedObj.name} satisfies all regulatory and statistical gates with a verified sample size of {playerSelectedObj.sampleSize} balls across {playerSelectedObj.matches} matches, yielding a tight posterior credible interval. 
                In contrast, {playerUnselectedObj.name} was excluded due to: <strong>{playerUnselectedObj.unselectedReasonText || 'insufficient qualification metrics'}</strong>. 
                Even if {playerUnselectedObj.name} displayed high raw scoring bursts, unshrinked statistics without required sample volume produce excessive sampling error.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
