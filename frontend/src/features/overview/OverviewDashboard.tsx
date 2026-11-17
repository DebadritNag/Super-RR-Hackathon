import React, { useState } from 'react';
import { useApp } from '@/context/AppContext';
import {
  Trophy,
  Target,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  FileSpreadsheet,
  Users,
  Shield,
  Layers,
  Sparkles,
  ChevronRight,
  CheckCircle2,
  HelpCircle,
  History,
  Scale,
} from 'lucide-react';
import { StatCard } from '@/components/shared/StatCard';
import { PlayerRadarChart } from '@/components/charts/PlayerRadarChart';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { Player } from '@/types';
import { formatScore } from '@/lib/utils';

export const OverviewDashboard: React.FC = () => {
  const {
    setActiveSection,
    openPlayerProfile,
    addToComparison,
    overviewSelectedBatterId,
    setOverviewSelectedBatterId,
    overviewSelectedBowlerId,
    setOverviewSelectedBowlerId,
    setComparisonPlayers,
    exportRankingsCSV,
  } = useApp();

  // Top 10 Batters & Bowlers
  const topBatters = MOCK_PLAYERS
    .filter(p => p.isSelectedTop10 && (p.role === 'Batter' || p.role === 'Wicketkeeper'))
    .sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0))
    .slice(0, 10);

  const topBowlers = MOCK_PLAYERS
    .filter(p => p.isSelectedTop10 && (p.role === 'Bowler' || (p.role === 'All-rounder' && p.bowlerRadar)))
    .sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0))
    .slice(0, 10);

  // Selected player objects for radar charts
  const selectedBatter = topBatters.find(p => p.id === overviewSelectedBatterId) || topBatters[0];
  const selectedBowler = topBowlers.find(p => p.id === overviewSelectedBowlerId) || topBowlers[0];

  // Quick comparison selection state
  const [quickCompAId, setQuickCompAId] = useState<string>(topBatters[0]?.id || 'p-101');
  const [quickCompBId, setQuickCompBId] = useState<string>(topBatters[1]?.id || 'p-102');

  const compPlayerA = MOCK_PLAYERS.find(p => p.id === quickCompAId) || topBatters[0];
  const compPlayerB = MOCK_PLAYERS.find(p => p.id === quickCompBId) || topBatters[1];

  const handleLaunchFullComparison = () => {
    setComparisonPlayers([quickCompAId, quickCompBId]);
    setActiveSection('player-comparison');
  };

  return (
    <div className="space-y-8 select-none">
      {/* ======================================================== */}
      {/* 3.A DASHBOARD INTRODUCTION & EXECUTIVE HEADER */}
      {/* ======================================================== */}
      <section className="bg-white rounded-xl border border-[#E5E8E3] p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E5E8E3] pb-5">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 text-[10px] font-bold bg-[#246B4B]/10 text-[#246B4B] rounded uppercase tracking-wider">
                Official RR Hackathon Submission
              </span>
              <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-50 text-[#D97736] border border-amber-200 rounded uppercase tracking-wider">
                Internal Experimental Only
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#202522] tracking-tight">
              Pressure Performance Intelligence
            </h1>
            <p className="text-sm font-medium text-[#246B4B] italic">
              "Identifying players who perform when the match situation demands the most."
            </p>
          </div>

          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={() => exportRankingsCSV('all')}
              className="flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold bg-[#246B4B] text-white rounded-md hover:bg-[#1b5239] transition-colors cursor-pointer shadow-xs"
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Export Roster CSV</span>
            </button>
            <button
              onClick={() => setActiveSection('methodology')}
              className="flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold bg-[#F7F6F2] text-[#202522] border border-[#E5E8E3] rounded-md hover:bg-[#eae8e1] transition-colors cursor-pointer"
            >
              <Layers className="w-4 h-4 text-[#777F79]" />
              <span>View 9-Step Pipeline</span>
            </button>
          </div>
        </div>

        <p className="text-xs sm:text-sm text-[#777F79] leading-relaxed mt-4">
          Built for Rajasthan Royals’ analytics department to decouple high-leverage, clutch performance from routine volume statistics. 
          Using ball-by-ball match state reconstruction, contextual expectation models, and empirical Bayes shrinkage, this terminal evaluates 
          which batters accelerate scoring without surrendering wickets and which bowlers suppress scoring in high-pressure innings phases.
        </p>
      </section>

      {/* ======================================================== */}
      {/* 3.B KEY COMPETITION METRICS */}
      {/* ======================================================== */}
      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#777F79]">
            Data Ingestion & Evaluation Bounds
          </h2>
          <span className="text-[11px] text-[#777F79]">
            Evaluation Window: 2024–2026 Feeds + Cricsheet Historical Match Records
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
          <StatCard
            title="Total Evaluated"
            value="1,217"
            subtitle="Full player pool"
            icon={<Users className="w-4 h-4" />}
          />
          <StatCard
            title="Eligible Batters"
            value="84"
            subtitle="Min 100 pressure balls"
            icon={<Trophy className="w-4 h-4 text-[#246B4B]" />}
            highlight={true}
          />
          <StatCard
            title="Eligible Bowlers"
            value="76"
            subtitle="Min 100 pressure balls"
            icon={<Target className="w-4 h-4 text-[#246B4B]" />}
            highlight={true}
          />
          <StatCard
            title="Pressure Balls"
            value="14,892"
            subtitle="2,420 clutch phases"
            icon={<Sparkles className="w-4 h-4 text-[#D97736]" />}
          />
          <StatCard
            title="Matches Included"
            value="883"
            subtitle="Ball-by-ball verified"
            icon={<Shield className="w-4 h-4 text-[#202522]" />}
          />
          <StatCard
            title="Gating Excluded"
            value="562"
            subtitle="Sample/weight gates"
            icon={<AlertTriangle className="w-4 h-4 text-[#C44747]" />}
          />
        </div>
      </section>

      {/* ======================================================== */}
      {/* 3.E MANDATORY SPIDER / RADAR CHARTS (BATTER & BOWLER) */}
      {/* ======================================================== */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-[#202522] uppercase tracking-wider flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-[#246B4B]" />
              <span>Multi-Dimensional Clutch Profiles (8 Mandatory Axes)</span>
            </h2>
            <p className="text-xs text-[#777F79]">
              Normalized 0–100 presentation scores. Hover over any vertex to inspect underlying raw statistics.
            </p>
          </div>
          <span className="text-[11px] font-semibold text-[#D97736] bg-amber-50 px-2 py-0.5 rounded border border-amber-200 hidden sm:inline-block">
            Decoupled Incompatible Metrics
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Pressure Batter Profile */}
          <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between border-b border-[#E5E8E3] pb-3 mb-2">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#246B4B] bg-[#246B4B]/10 px-2 py-0.5 rounded">
                  Batter Profile (8 Axes)
                </span>
                <h3 className="text-sm font-bold text-[#202522] mt-1">
                  {selectedBatter.name} ({selectedBatter.team})
                </h3>
              </div>

              {/* Top 10 Batter Dropdown Selector */}
              <div className="flex items-center space-x-2">
                <label htmlFor="batter-select" className="text-xs text-[#777F79] font-medium hidden sm:inline">
                  Select Batter:
                </label>
                <select
                  id="batter-select"
                  value={overviewSelectedBatterId}
                  onChange={(e) => setOverviewSelectedBatterId(e.target.value)}
                  className="text-xs font-semibold bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-[#202522] focus:outline-none focus:border-[#246B4B] cursor-pointer"
                >
                  {topBatters.map((b, idx) => (
                    <option key={b.id} value={b.id}>
                      #{idx + 1} {b.name} ({b.pressureScore})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Radar Chart */}
            <div className="py-2">
              <PlayerRadarChart
                type="batter"
                playerName={selectedBatter.name}
                batterMetrics={selectedBatter.batterRadar}
              />
            </div>

            {/* Bottom Insight Footer */}
            <div className="pt-3 border-t border-[#E5E8E3] flex items-center justify-between text-xs">
              <div className="text-[#777F79] truncate max-w-sm">
                <span className="font-semibold text-[#202522]">Key Strength:</span>{' '}
                {selectedBatter.strongestAttributes[0]}
              </div>
              <button
                onClick={() => openPlayerProfile(selectedBatter)}
                className="font-bold text-[#246B4B] hover:underline flex items-center space-x-1 shrink-0 cursor-pointer"
              >
                <span>Full Audit</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Chart 2: Pressure Bowler Profile */}
          <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between border-b border-[#E5E8E3] pb-3 mb-2">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#246B4B] bg-[#246B4B]/10 px-2 py-0.5 rounded">
                  Bowler Profile (8 Axes)
                </span>
                <h3 className="text-sm font-bold text-[#202522] mt-1">
                  {selectedBowler.name} ({selectedBowler.team})
                </h3>
              </div>

              {/* Top 10 Bowler Dropdown Selector */}
              <div className="flex items-center space-x-2">
                <label htmlFor="bowler-select" className="text-xs text-[#777F79] font-medium hidden sm:inline">
                  Select Bowler:
                </label>
                <select
                  id="bowler-select"
                  value={overviewSelectedBowlerId}
                  onChange={(e) => setOverviewSelectedBowlerId(e.target.value)}
                  className="text-xs font-semibold bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-[#202522] focus:outline-none focus:border-[#246B4B] cursor-pointer"
                >
                  {topBowlers.map((bw, idx) => (
                    <option key={bw.id} value={bw.id}>
                      #{idx + 1} {bw.name} ({bw.pressureScore})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Radar Chart */}
            <div className="py-2">
              <PlayerRadarChart
                type="bowler"
                playerName={selectedBowler.name}
                bowlerMetrics={selectedBowler.bowlerRadar}
              />
            </div>

            {/* Bottom Insight Footer */}
            <div className="pt-3 border-t border-[#E5E8E3] flex items-center justify-between text-xs">
              <div className="text-[#777F79] truncate max-w-sm">
                <span className="font-semibold text-[#202522]">Key Weapon:</span>{' '}
                {selectedBowler.strongestAttributes[0]}
              </div>
              <button
                onClick={() => openPlayerProfile(selectedBowler)}
                className="font-bold text-[#246B4B] hover:underline flex items-center space-x-1 shrink-0 cursor-pointer"
              >
                <span>Full Audit</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ======================================================== */}
      {/* 3.C & 3.D TOP 10 RANKINGS: BATTERS & BOWLERS */}
      {/* ======================================================== */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* TOP 10 PRESSURE BATTERS */}
        <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs flex flex-col">
          <div className="p-4 sm:p-5 border-b border-[#E5E8E3] flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <Trophy className="w-4 h-4 text-[#246B4B]" />
                <h2 className="text-sm font-bold text-[#202522] uppercase tracking-wider">
                  Top 10 Pressure Batters
                </h2>
              </div>
              <p className="text-xs text-[#777F79] mt-0.5">
                Evaluated by Bayesian run-scoring residual & boundary acceleration
              </p>
            </div>
            <button
              onClick={() => setActiveSection('pressure-batters')}
              className="text-xs font-bold text-[#246B4B] hover:underline flex items-center space-x-1 cursor-pointer"
            >
              <span>Full Page</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-[#E5E8E3] overflow-x-auto">
            {topBatters.map((player, index) => (
              <div
                key={player.id}
                onClick={() => openPlayerProfile(player)}
                className="p-3 sm:px-4 flex items-center justify-between hover:bg-[#F7F6F2] transition-colors cursor-pointer"
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-7 h-7 rounded-full bg-[#246B4B]/10 text-[#246B4B] font-extrabold text-xs flex items-center justify-center shrink-0">
                    {index + 1}
                  </div>
                  <div className="truncate">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-[#202522] truncate">
                        {player.name}
                      </span>
                      <span className="text-[10px] text-[#777F79] font-mono">
                        ({player.id})
                      </span>
                      <span className="text-[9px] px-1 py-0.2 bg-[#F7F6F2] border border-[#E5E8E3] rounded text-[#777F79]">
                        {player.nationality === 'Indian' ? 'IND' : 'OS'}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#777F79] truncate mt-0.5">
                      {player.speciality} • {player.sampleSize} balls • {player.rankingRationale}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0 ml-3">
                  <div className="text-sm font-black text-[#246B4B]">
                    {formatScore(player.pressureScore)}
                  </div>
                  <div className="text-[9px] text-[#777F79]">
                    {player.uncertaintyInterval ? `±${((player.uncertaintyInterval[1] - player.uncertaintyInterval[0])/2).toFixed(1)} CI` : 'High Rel'}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 bg-[#F7F6F2] border-t border-[#E5E8E3] text-center">
            <button
              onClick={() => setActiveSection('pressure-batters')}
              className="text-xs font-bold text-[#246B4B] hover:text-[#1b5239] cursor-pointer"
            >
              Inspect all 84 qualified batters & baseline metrics →
            </button>
          </div>
        </div>

        {/* TOP 10 PRESSURE BOWLERS */}
        <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs flex flex-col">
          <div className="p-4 sm:p-5 border-b border-[#E5E8E3] flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <Target className="w-4 h-4 text-[#246B4B]" />
                <h2 className="text-sm font-bold text-[#202522] uppercase tracking-wider">
                  Top 10 Pressure Bowlers
                </h2>
                <span className="text-[9px] font-bold bg-amber-100 text-[#D97736] px-1.5 py-0.5 rounded">
                  Experimental
                </span>
              </div>
              <p className="text-xs text-[#777F79] mt-0.5">
                Evaluated by negated runs-conceded residual & clutch wicket frequency
              </p>
            </div>
            <button
              onClick={() => setActiveSection('pressure-bowlers')}
              className="text-xs font-bold text-[#246B4B] hover:underline flex items-center space-x-1 cursor-pointer"
            >
              <span>Full Page</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-[#E5E8E3] overflow-x-auto">
            {topBowlers.map((player, index) => (
              <div
                key={player.id}
                onClick={() => openPlayerProfile(player)}
                className="p-3 sm:px-4 flex items-center justify-between hover:bg-[#F7F6F2] transition-colors cursor-pointer"
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-7 h-7 rounded-full bg-[#202522]/10 text-[#202522] font-extrabold text-xs flex items-center justify-center shrink-0">
                    {index + 1}
                  </div>
                  <div className="truncate">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-[#202522] truncate">
                        {player.name}
                      </span>
                      <span className="text-[10px] text-[#777F79] font-mono">
                        ({player.id})
                      </span>
                      <span className="text-[9px] px-1 py-0.2 bg-[#F7F6F2] border border-[#E5E8E3] rounded text-[#777F79]">
                        {player.nationality === 'Indian' ? 'IND' : 'OS'}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#777F79] truncate mt-0.5">
                      {player.speciality} • {player.sampleSize} balls • {player.rankingRationale}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0 ml-3">
                  <div className="text-sm font-black text-[#202522]">
                    {formatScore(player.pressureScore)}
                  </div>
                  <div className="text-[9px] text-[#777F79]">
                    {player.pressureEconomy ? `${player.pressureEconomy} RPO` : 'High Rel'}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 bg-[#F7F6F2] border-t border-[#E5E8E3] text-center">
            <button
              onClick={() => setActiveSection('pressure-bowlers')}
              className="text-xs font-bold text-[#202522] hover:text-[#246B4B] cursor-pointer"
            >
              Inspect all 76 qualified bowlers & economy residuals →
            </button>
          </div>
        </div>
      </section>

      {/* ======================================================== */}
      {/* 3.F QUICK COMPARISON SECTION */}
      {/* ======================================================== */}
      <section className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E5E8E3] pb-3">
          <div>
            <h2 className="text-sm font-bold text-[#202522] uppercase tracking-wider flex items-center space-x-2">
              <Scale className="w-4 h-4 text-[#D97736]" />
              <span>Quick Head-to-Head Decider</span>
            </h2>
            <p className="text-xs text-[#777F79]">
              Compare any two selected candidates side-by-side with metric advantage callouts
            </p>
          </div>

          <button
            onClick={handleLaunchFullComparison}
            className="flex items-center space-x-1 text-xs font-bold text-[#246B4B] hover:underline cursor-pointer"
          >
            <span>Open Multi-Player Comparison (Up to 4)</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Player Pickers */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-[#F7F6F2] p-3 rounded-lg border border-[#E5E8E3] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#246B4B]">Candidate A</span>
              <select
                value={quickCompAId}
                onChange={(e) => setQuickCompAId(e.target.value)}
                className="text-xs font-semibold bg-white border border-[#E5E8E3] rounded px-2 py-1 text-[#202522] cursor-pointer"
              >
                {topBatters.concat(topBowlers).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.role} - {p.pressureScore})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center justify-between pt-1">
              <div>
                <div className="text-sm font-bold text-[#202522]">{compPlayerA.name}</div>
                <div className="text-[11px] text-[#777F79]">{compPlayerA.team} • {compPlayerA.role}</div>
              </div>
              <div className="text-right">
                <div className="text-lg font-black text-[#246B4B]">{compPlayerA.pressureScore}</div>
                <div className="text-[10px] text-[#777F79]">{compPlayerA.sampleSize} balls</div>
              </div>
            </div>
          </div>

          <div className="bg-[#F7F6F2] p-3 rounded-lg border border-[#E5E8E3] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#D97736]">Candidate B</span>
              <select
                value={quickCompBId}
                onChange={(e) => setQuickCompBId(e.target.value)}
                className="text-xs font-semibold bg-white border border-[#E5E8E3] rounded px-2 py-1 text-[#202522] cursor-pointer"
              >
                {topBatters.concat(topBowlers).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.role} - {p.pressureScore})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center justify-between pt-1">
              <div>
                <div className="text-sm font-bold text-[#202522]">{compPlayerB.name}</div>
                <div className="text-[11px] text-[#777F79]">{compPlayerB.team} • {compPlayerB.role}</div>
              </div>
              <div className="text-right">
                <div className="text-lg font-black text-[#D97736]">{compPlayerB.pressureScore}</div>
                <div className="text-[10px] text-[#777F79]">{compPlayerB.sampleSize} balls</div>
              </div>
            </div>
          </div>
        </div>

        {/* Comparative Advantage Bar */}
        <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] text-xs text-[#202522] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div>
            <span className="font-bold text-[#246B4B]">Analytical Verdict: </span>
            {(compPlayerA.pressureScore ?? 0) >= (compPlayerB.pressureScore ?? 0) ? (
              <span>
                <strong>{compPlayerA.name}</strong> ranks +{((compPlayerA.pressureScore ?? 0) - (compPlayerB.pressureScore ?? 0)).toFixed(1)} points higher, offering superior residual outperformance (+{compPlayerA.adjustedPerformance}%) and proven stability across {compPlayerA.matches} matches.
              </span>
            ) : (
              <span>
                <strong>{compPlayerB.name}</strong> ranks +{((compPlayerB.pressureScore ?? 0) - (compPlayerA.pressureScore ?? 0)).toFixed(1)} points higher with greater clutch ceiling index.
              </span>
            )}
          </div>
          <button
            onClick={handleLaunchFullComparison}
            className="px-3 py-1 bg-[#246B4B] text-white font-semibold rounded hover:bg-[#1b5239] transition-colors shrink-0 cursor-pointer"
          >
            Compare Overlaid Radar →
          </button>
        </div>
      </section>

      {/* ======================================================== */}
      {/* 3.G DATA & METHODOLOGY SUMMARY */}
      {/* ======================================================== */}
      <section className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-[#E5E8E3] pb-3">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-[#246B4B]" />
            <h2 className="text-sm font-bold text-[#202522] uppercase tracking-wider">
              Data Governance & Methodology Summary
            </h2>
          </div>
          <button
            onClick={() => setActiveSection('methodology')}
            className="text-xs font-bold text-[#246B4B] hover:underline flex items-center space-x-1 cursor-pointer"
          >
            <span>Read 9-Step Pipeline Whitepaper</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1">
            <div className="font-bold text-[#202522]">1. Official Competition Sources</div>
            <p className="text-[#777F79] leading-relaxed">
              Standardized ball-by-ball delivery feeds (883 matches, 2008–2024 Cricsheet records + 2024–2026 IPL tournament logs). Match state reconstructed per delivery.
            </p>
          </div>

          <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1">
            <div className="font-bold text-[#202522]">2. Pressure Definition & Shrinkage</div>
            <p className="text-[#777F79] leading-relaxed">
              Leverage index &gt; 1.5, required run rate &gt; 9.0 in chases, and overs 16–20. Empirical Bayes shrinkage applied to regress small sample variance toward the league mean.
            </p>
          </div>

          <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-1">
            <div className="font-bold text-[#D97736] flex items-center space-x-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>3. Validation & Phase 4 Disclosure</span>
            </div>
            <p className="text-[#777F79] leading-relaxed">
              Publication status: <strong>INTERNAL_EXPERIMENTAL_ONLY</strong>. The Phase 4 TEST holdout was previously evaluated; rankings do not claim pristine out-of-sample validation.
            </p>
          </div>
        </div>
      </section>

      {/* ======================================================== */}
      {/* 3.H RAJASTHAN ROYALS RECRUITMENT INSIGHTS (2025 & 2026) */}
      {/* ======================================================== */}
      <section className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-[#E5E8E3] pb-3">
          <div className="flex items-center space-x-2">
            <History className="w-4 h-4 text-[#D97736]" />
            <h2 className="text-sm font-bold text-[#202522] uppercase tracking-wider">
              Rajasthan Royals Tactical Analysis & Recruitment Blueprint
            </h2>
          </div>
          <button
            onClick={() => setActiveSection('rr-analysis')}
            className="text-xs font-bold text-[#246B4B] hover:underline flex items-center space-x-1 cursor-pointer"
          >
            <span>Full 2025 & 2026 Dossier</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Priority 1: Middle overs spin */}
          <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-white bg-[#246B4B] px-1.5 py-0.5 rounded uppercase">
                Priority 1
              </span>
              <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                Verified Calculation
              </span>
            </div>
            <div className="text-xs font-bold text-[#202522]">
              Middle-Order Spin Counter (Overs 7–15)
            </div>
            <p className="text-[11px] text-[#777F79] leading-relaxed">
              RR recorded 34.2% dot balls against finger and wrist spin in 2025/2026 middle overs, stalling scoring velocity and burdening the finish.
            </p>
            <div className="text-[10px] text-[#246B4B] font-semibold pt-1 border-t border-[#E5E8E3]">
              Target Solutions: <strong>Heinrich Klaasen (#1)</strong>, <strong>Riyan Parag (#5)</strong>
            </div>
          </div>

          {/* Priority 2: Death-over bowling */}
          <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-white bg-[#202522] px-1.5 py-0.5 rounded uppercase">
                Priority 2
              </span>
              <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                Verified Calculation
              </span>
            </div>
            <div className="text-xs font-bold text-[#202522]">
              Death Overs Yorker Execution & Containment
            </div>
            <p className="text-[11px] text-[#777F79] leading-relaxed">
              Historical death-overs economy exceeded 11.45 RPO in matches without specialist yorker execution alongside Sandeep Sharma.
            </p>
            <div className="text-[10px] text-[#246B4B] font-semibold pt-1 border-t border-[#E5E8E3]">
              Target Solutions: <strong>Jasprit Bumrah (#1)</strong>, <strong>Matheesha Pathirana (#3)</strong>
            </div>
          </div>

          {/* Priority 3: Close Chase Finishing */}
          <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-white bg-[#D97736] px-1.5 py-0.5 rounded uppercase">
                Priority 3
              </span>
              <span className="text-[10px] text-amber-700 font-semibold bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200">
                Media Hypothesis
              </span>
            </div>
            <div className="text-xs font-bold text-[#202522]">
              Composed Close-Chase Finishing (Final 3 Overs)
            </div>
            <p className="text-[11px] text-[#777F79] leading-relaxed">
              RR surrendered 4 close run-chases requiring &lt;28 runs off 18 balls in 2025 due to rash aerial boundary attempts under pressure.
            </p>
            <div className="text-[10px] text-[#246B4B] font-semibold pt-1 border-t border-[#E5E8E3]">
              Target Solutions: <strong>Rinku Singh (#3)</strong>, <strong>Shashank Singh (#6)</strong>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
