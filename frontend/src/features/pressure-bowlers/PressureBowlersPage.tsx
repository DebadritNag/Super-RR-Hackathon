import React, { useState } from 'react';
import { useApp } from '@/context/AppContext';
import {
  Target,
  Search,
  Filter,
  ArrowUpDown,
  FileSpreadsheet,
  AlertTriangle,
  Sparkles,
  ChevronRight,
  X,
} from 'lucide-react';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { Player, Nationality, InternationalStatus } from '@/types';
import { PlayerRadarChart } from '@/components/charts/PlayerRadarChart';
import { formatScore } from '@/lib/utils';

export const PressureBowlersPage: React.FC = () => {
  const { openPlayerProfile, exportRankingsCSV, setComparisonPlayers, setActiveSection } = useApp();

  // Filters state
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [nationalityFilter, setNationalityFilter] = useState<Nationality | 'All'>('All');
  const [statusFilter, setStatusFilter] = useState<InternationalStatus | 'All'>('All');
  const [sortField, setSortField] = useState<'pressureScore' | 'sampleSize' | 'adjustedPerformance'>('pressureScore');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  // Bowlers pool
  const allBowlers = MOCK_PLAYERS.filter(
    p => p.role === 'Bowler' || (p.role === 'All-rounder' && p.bowlerRadar)
  );

  const top10Bowlers = allBowlers
    .filter(p => p.isSelectedTop10)
    .sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0));

  const [selectedPlayer, setSelectedPlayer] = useState<Player>(top10Bowlers[0] || allBowlers[0]);
  const [comparisonBowlerId, setComparisonBowlerId] = useState<string>(top10Bowlers[1]?.id || '');

  const comparisonBowler = top10Bowlers.find(p => p.id === comparisonBowlerId);

  // Filtered & sorted table list
  const filteredBowlers = allBowlers
    .filter(p => {
      const matchesSearch =
        p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.team.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesNat = nationalityFilter === 'All' || p.nationality === nationalityFilter;
      const matchesStatus = statusFilter === 'All' || p.internationalStatus === statusFilter;
      return matchesSearch && matchesNat && matchesStatus;
    })
    .sort((a, b) => {
      const valA = a[sortField] ?? 0;
      const valB = b[sortField] ?? 0;
      return sortAsc ? valA - valB : valB - valA;
    });

  const handleLaunchComparison = (playerB: Player) => {
    setComparisonPlayers([selectedPlayer.id, playerB.id]);
    setActiveSection('player-comparison');
  };

  return (
    <div className="space-y-6 select-none">
      {/* Top Header Card */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-[#202522]/10 text-[#202522] flex items-center justify-center font-bold">
              <Target className="w-4 h-4" />
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-[#202522] tracking-tight">
              Top 10 Pressure Bowlers
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-bold bg-[#D97736] text-white rounded">
              Experimental Roster
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#777F79] mt-1 leading-relaxed">
            Evaluated by negated runs-conceded residuals, dot-ball suppression, and clutch wicket frequency in death and high-RRR phases.
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={() => exportRankingsCSV('bowlers')}
            className="flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold bg-[#202522] text-white rounded-md hover:bg-[#2d3430] transition-colors cursor-pointer shadow-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Export Bowlers CSV</span>
          </button>
        </div>
      </div>

      {/* Main Layout: Table on Left / Drawer on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Full Ranking Table (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Table Controls / Filters */}
          <div className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs space-y-3">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 text-[#777F79] absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter by name, team, or player ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-[#F7F6F2] border border-[#E5E8E3] rounded-md focus:outline-none focus:border-[#246B4B]"
                />
              </div>

              <div className="flex items-center space-x-2">
                <select
                  value={nationalityFilter}
                  onChange={(e) => setNationalityFilter(e.target.value as any)}
                  aria-label="Filter by Nationality"
                  className="text-xs bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-[#202522] focus:outline-none focus:border-[#246B4B] cursor-pointer"
                >
                  <option value="All">All Nationalities</option>
                  <option value="Indian">Indian Only</option>
                  <option value="Overseas">Overseas Only</option>
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as any)}
                  aria-label="Filter by International Status"
                  className="text-xs bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-[#202522] focus:outline-none focus:border-[#246B4B] cursor-pointer"
                >
                  <option value="All">All Statuses</option>
                  <option value="Verified Capped">Verified Capped</option>
                  <option value="Derived Capped">Derived Capped</option>
                  <option value="Unknown">Unknown Status</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-[#777F79] pt-1 border-t border-[#E5E8E3]">
              <span>Showing {filteredBowlers.length} evaluated bowlers</span>
              <span>Click any bowler row to inspect economy residuals & radar</span>
            </div>
          </div>

          {/* Full Ranking Table */}
          <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#F7F6F2] border-b border-[#E5E8E3] text-[#777F79] font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-2.5 px-3 w-10 text-center">Rank</th>
                    <th className="py-2.5 px-3">Player</th>
                    <th className="py-2.5 px-2">ID</th>
                    <th className="py-2.5 px-2">Role</th>
                    <th className="py-2.5 px-2">Nat</th>
                    <th
                      className="py-2.5 px-2 text-right cursor-pointer hover:text-[#202522]"
                      onClick={() => {
                        setSortField('pressureScore');
                        setSortAsc(!sortAsc);
                      }}
                    >
                      <div className="flex items-center justify-end space-x-1">
                        <span>Score</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-2.5 px-2 text-right">Base Econ</th>
                    <th className="py-2.5 px-2 text-right">Residual</th>
                    <th className="py-2.5 px-2 text-right">Wkts</th>
                    <th className="py-2.5 px-2 text-right">Balls</th>
                    <th className="py-2.5 px-2 text-right">Matches</th>
                    <th className="py-2.5 px-2 text-center">CI</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E8E3]">
                  {filteredBowlers.map((player, idx) => {
                    const isSelected = selectedPlayer.id === player.id;
                    const isTop10 = player.isSelectedTop10;
                    return (
                      <tr
                        key={player.id}
                        onClick={() => setSelectedPlayer(player)}
                        className={`hover:bg-[#F7F6F2] transition-colors cursor-pointer ${
                          isSelected ? 'bg-[#202522]/10 font-medium' : ''
                        }`}
                      >
                        <td className="py-2.5 px-3 text-center font-bold text-[#202522]">
                          {isTop10 ? (
                            <span className="w-5 h-5 rounded-full bg-[#202522] text-white inline-flex items-center justify-center text-[10px]">
                              {idx + 1}
                            </span>
                          ) : (
                            <span className="text-[#777F79]">{idx + 1}</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="font-bold text-[#202522]">{player.name}</div>
                          <div className="text-[10px] text-[#777F79]">{player.team}</div>
                        </td>
                        <td className="py-2.5 px-2 font-mono text-[10px] text-[#777F79]">
                          {player.id}
                        </td>
                        <td className="py-2.5 px-2 text-[10px] text-[#777F79]">
                          {player.speciality}
                        </td>
                        <td className="py-2.5 px-2">
                          <span className="text-[9px] px-1 py-0.5 rounded border border-[#E5E8E3] bg-white text-[#777F79]">
                            {player.nationality === 'Indian' ? 'IND' : 'OS'}
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-right font-black text-[#202522] text-xs">
                          {formatScore(player.pressureScore)}
                        </td>
                        <td className="py-2.5 px-2 text-right text-[11px] text-[#777F79]">
                          {player.baselineEconomy ? `${player.baselineEconomy} RPO` : 'N/A'}
                        </td>
                        <td className="py-2.5 px-2 text-right text-[11px] font-semibold text-emerald-700">
                          {player.adjustedPerformance}%
                        </td>
                        <td className="py-2.5 px-2 text-right text-[11px] font-bold text-[#246B4B]">
                          {player.pressureWickets ?? 'N/A'}
                        </td>
                        <td className="py-2.5 px-2 text-right text-[11px] font-mono text-[#202522]">
                          {player.sampleSize}
                        </td>
                        <td className="py-2.5 px-2 text-right text-[11px] text-[#777F79]">
                          {player.matches}
                        </td>
                        <td className="py-2.5 px-2 text-center text-[10px] text-[#777F79] whitespace-nowrap">
                          {player.uncertaintyInterval
                            ? `±${((player.uncertaintyInterval[1] - player.uncertaintyInterval[0])/2).toFixed(1)}`
                            : 'N/A'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Bowler Analytics & Radar (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-5">
            {/* Player Quick Summary */}
            <div className="flex items-start justify-between border-b border-[#E5E8E3] pb-4">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-[#202522] text-white px-2 py-0.5 rounded">
                    {selectedPlayer.isSelectedTop10 ? 'Top 10 Selected' : 'Evaluated Candidate'}
                  </span>
                  <span className="text-[10px] font-medium bg-[#F7F6F2] border border-[#E5E8E3] px-1.5 py-0.5 rounded text-[#777F79]">
                    {selectedPlayer.internationalStatus}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-[#202522] mt-1.5">
                  {selectedPlayer.name}
                </h2>
                <div className="text-xs text-[#777F79]">
                  {selectedPlayer.team} • {selectedPlayer.speciality} • {selectedPlayer.bowlingStyle || 'Bowler'}
                </div>
              </div>

              <div className="text-right">
                <div className="text-2xl font-black text-[#202522]">
                  {formatScore(selectedPlayer.pressureScore)}
                </div>
                <div className="text-[10px] text-[#777F79] font-medium">
                  Negated Residual Score
                </div>
              </div>
            </div>

            {/* Performance Under Pressure Breakdown */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#777F79]">
                Bowling Pressure Metrics
              </h3>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-[#F7F6F2] p-2.5 rounded border border-[#E5E8E3]">
                  <div className="text-[10px] text-[#777F79]">Pressure Economy</div>
                  <div className="text-sm font-bold text-[#202522]">
                    {selectedPlayer.bowlerRadar?.rawValues.pressureEconomy ?? 'N/A'} RPO
                  </div>
                  <div className="text-[10px] text-emerald-700 font-medium">
                    Residual: {selectedPlayer.adjustedPerformance}% vs par
                  </div>
                </div>

                <div className="bg-[#F7F6F2] p-2.5 rounded border border-[#E5E8E3]">
                  <div className="text-[10px] text-[#777F79]">Clutch Wickets</div>
                  <div className="text-sm font-bold text-[#246B4B]">
                    {selectedPlayer.bowlerRadar?.rawValues.wicketsUnderPressure ?? 'N/A'} wkts
                  </div>
                  <div className="text-[10px] text-[#777F79]">
                    Total balls: {selectedPlayer.sampleSize}
                  </div>
                </div>

                <div className="bg-[#F7F6F2] p-2.5 rounded border border-[#E5E8E3]">
                  <div className="text-[10px] text-[#777F79]">Dot Ball Percentage</div>
                  <div className="text-sm font-bold text-[#202522]">
                    {selectedPlayer.bowlerRadar?.rawValues.dotBallPercent ?? 'N/A'}%
                  </div>
                  <div className="text-[10px] text-[#777F79]">
                    PP Econ: {selectedPlayer.bowlerRadar?.rawValues.powerplayEconomy ?? 'N/A'}
                  </div>
                </div>

                <div className="bg-[#F7F6F2] p-2.5 rounded border border-[#E5E8E3]">
                  <div className="text-[10px] text-[#777F79]">Death Overs Economy (16-20)</div>
                  <div className="text-sm font-bold text-[#202522]">
                    {selectedPlayer.bowlerRadar?.rawValues.deathEconomy ?? 'N/A'} RPO
                  </div>
                  <div className="text-[10px] text-[#777F79]">
                    Defence Econ: {selectedPlayer.bowlerRadar?.rawValues.chaseDefenceEconomy ?? 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            {/* Complete 8-Axis Bowler Radar Chart with Comparison Picker */}
            <div className="space-y-2 pt-2 border-t border-[#E5E8E3]">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#777F79]">
                  8-Axis Profile & Comparison
                </h3>
                <div className="flex items-center space-x-1">
                  <select
                    value={comparisonBowlerId}
                    onChange={(e) => setComparisonBowlerId(e.target.value)}
                    aria-label="Compare against bowler"
                    className="text-[11px] bg-[#F7F6F2] border border-[#E5E8E3] rounded px-2 py-1 text-[#202522] cursor-pointer"
                  >
                    <option value="">Compare with...</option>
                    {top10Bowlers
                      .filter(b => b.id !== selectedPlayer.id)
                      .map(b => (
                        <option key={b.id} value={b.id}>
                          vs {b.name}
                        </option>
                      ))}
                  </select>
                  {comparisonBowlerId && (
                    <button
                      onClick={() => setComparisonBowlerId('')}
                      className="p-1 text-[#777F79] hover:text-[#202522] cursor-pointer"
                      title="Clear comparison overlay"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              <div className="bg-[#F7F6F2] rounded-lg p-2 border border-[#E5E8E3]">
                <PlayerRadarChart
                  type="bowler"
                  playerName={selectedPlayer.name}
                  bowlerMetrics={selectedPlayer.bowlerRadar}
                  comparisonMetrics={comparisonBowler?.bowlerRadar}
                  comparisonName={comparisonBowler?.name}
                />
              </div>
            </div>

            {/* "Why this bowler?" Comprehensive Evidence Rationale */}
            <div className="space-y-2 pt-3 border-t border-[#E5E8E3]">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-1">
                <Sparkles className="w-3.5 h-3.5 text-[#246B4B]" />
                <span>Why This Bowler? (Scouting Rationale)</span>
              </h3>

              <div className="bg-[#F7F6F2] p-3 rounded-lg border border-[#E5E8E3] text-xs space-y-2">
                <p className="text-[#202522] leading-relaxed">
                  <strong>Core Justification:</strong> {selectedPlayer.rankingRationale}
                </p>

                <div className="space-y-1 text-[11px] text-[#777F79]">
                  <div>
                    <span className="font-semibold text-[#202522]">Key Weapons:</span>{' '}
                    {selectedPlayer.strongestAttributes.join(' • ')}
                  </div>
                  <div>
                    <span className="font-semibold text-[#202522]">Peak Leverage Phase:</span> Excels in{' '}
                    {selectedPlayer.excelsInSituations.join(', ')}
                  </div>
                  <div>
                    <span className="font-semibold text-[#202522]">Sample Reliability:</span>{' '}
                    {selectedPlayer.sampleSize} pressure balls bowled across {selectedPlayer.matches} matches. Credible interval:{' '}
                    {selectedPlayer.uncertaintyInterval ? `[${selectedPlayer.uncertaintyInterval[0]} - ${selectedPlayer.uncertaintyInterval[1]}]` : 'High confidence'}.
                  </div>
                  <div>
                    <span className="font-semibold text-[#C44747]">Known Vulnerability:</span>{' '}
                    {selectedPlayer.weaknesses.join('; ')}
                  </div>
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="pt-2 flex items-center justify-between">
              <button
                onClick={() => openPlayerProfile(selectedPlayer)}
                className="text-xs font-semibold text-[#246B4B] hover:underline cursor-pointer"
              >
                Inspect Technical Dossier →
              </button>
              {comparisonBowler && (
                <button
                  onClick={() => handleLaunchComparison(comparisonBowler)}
                  className="px-3 py-1.5 bg-[#202522] text-white text-xs font-semibold rounded hover:bg-[#2d3430] transition-colors cursor-pointer"
                >
                  Deep Compare with {comparisonBowler.name}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
