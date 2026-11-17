import React, { useState, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import {
  Scale,
  Plus,
  Trash2,
  AlertTriangle,
  Sparkles,
  Info,
  ChevronRight,
  Shield,
  Trophy,
  Target,
  ArrowRight,
  X,
} from 'lucide-react';
import { comparisonService, ComparisonResult } from '@/services/comparisonService';
import { ComparisonRadarChart } from '@/components/charts/ComparisonRadarChart';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { Player } from '@/types';
import { formatScore } from '@/lib/utils';

export const PlayerComparison: React.FC = () => {
  const {
    comparisonPlayerIds,
    addToComparison,
    removeFromComparison,
    setComparisonPlayers,
    clearComparison,
    openPlayerProfile,
  } = useApp();

  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);

  const loadComparison = async () => {
    const res = await comparisonService.comparePlayers(comparisonPlayerIds);
    setComparisonResult(res);
  };

  useEffect(() => {
    loadComparison();
  }, [comparisonPlayerIds]);

  // Candidates available to add (must be compatible with current selection)
  const currentFirstPlayer = MOCK_PLAYERS.find(p => p.id === comparisonPlayerIds[0]);
  const isBattingComparison = currentFirstPlayer
    ? currentFirstPlayer.role === 'Batter' || currentFirstPlayer.role === 'Wicketkeeper'
    : true;

  const candidatesToAdd = MOCK_PLAYERS.filter(p => {
    if (comparisonPlayerIds.includes(p.id)) return false;
    if (comparisonPlayerIds.length === 0) return true;
    const isBatter = p.role === 'Batter' || p.role === 'Wicketkeeper';
    return isBattingComparison ? isBatter : !isBatter;
  });

  return (
    <div className="space-y-6 select-none">
      {/* Top Header Card */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 sm:p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-[#D97736]/10 text-[#D97736] flex items-center justify-center font-bold">
              <Scale className="w-4 h-4" />
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-[#202522] tracking-tight">
              Player Head-to-Head Comparison
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-bold bg-[#246B4B] text-white rounded">
              2 to 4 Players
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#777F79] mt-1 leading-relaxed">
            Multi-dimensional overlaid spider charts and metric differentials for compatible player disciplines.
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={() => setIsAddModalOpen(true)}
            disabled={comparisonPlayerIds.length >= 4}
            className="flex items-center space-x-1 px-3 py-2 text-xs font-semibold bg-[#246B4B] text-white rounded-md hover:bg-[#1b5239] disabled:opacity-50 transition-colors cursor-pointer shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Player ({comparisonPlayerIds.length}/4)</span>
          </button>
          {comparisonPlayerIds.length > 0 && (
            <button
              onClick={clearComparison}
              className="flex items-center space-x-1 px-3 py-2 text-xs font-semibold bg-[#F7F6F2] text-[#777F79] hover:text-[#C44747] border border-[#E5E8E3] rounded-md hover:bg-[#eae8e1] transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Selected Players Chips Bar */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#777F79]">
            Active Comparison Roster:
          </span>
          <span className="text-[11px] text-[#777F79]">
            Discipline: <strong>{isBattingComparison ? 'Batting & Power-Hitting' : 'Bowling & Death Containment'}</strong>
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          {comparisonResult?.players.map((p, idx) => (
            <div
              key={p.id}
              className="flex items-center space-x-2 pl-3 pr-2 py-1.5 rounded-lg bg-[#F7F6F2] border border-[#E5E8E3] text-xs font-medium"
            >
              <span className="w-2.5 h-2.5 rounded-full" style={{
                backgroundColor: ['#246B4B', '#D97736', '#202522', '#27845B'][idx % 4]
              }} />
              <span className="font-bold text-[#202522]">{p.name}</span>
              <span className="text-[10px] text-[#777F79]">({p.pressureScore} pts)</span>
              <button
                onClick={() => removeFromComparison(p.id)}
                className="text-[#777F79] hover:text-[#C44747] p-0.5 cursor-pointer"
                title="Remove from comparison"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}

          {comparisonPlayerIds.length < 2 && (
            <div className="text-xs text-[#D97736] flex items-center space-x-1.5 py-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Select at least 2 players to compute overlaid analytics</span>
            </div>
          )}
        </div>
      </div>

      {/* Incompatibility Warning Guard */}
      {!comparisonResult?.isCompatible && comparisonPlayerIds.length >= 2 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-xs text-[#C44747] flex items-start space-x-3">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-sm">Discipline Incompatibility Detected</div>
            <p className="mt-1 leading-relaxed">
              {comparisonResult?.compatibilityMessage || 'Cannot compare pure batter radar metrics directly against pure bowler metrics.'}
            </p>
          </div>
        </div>
      )}

      {/* Main Analysis Container (When Compatible and >= 2 players) */}
      {comparisonResult?.isCompatible && (
        <div className="space-y-6">
          {/* Overlaid Radar Chart & Head-to-Head Rationale */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Overlaid Spider Chart (7 Cols) */}
            <div className="lg:col-span-7 bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between border-b border-[#E5E8E3] pb-3 mb-2">
                <div>
                  <h2 className="text-xs font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-[#246B4B]" />
                    <span>Overlaid 8-Axis Multi-Player Profile</span>
                  </h2>
                  <p className="text-[11px] text-[#777F79] mt-0.5">
                    Compare relative shape across 8 normalized 0-100 dimensions
                  </p>
                </div>
              </div>

              <div className="py-2">
                <ComparisonRadarChart
                  players={comparisonResult.players}
                  type={comparisonResult.comparisonType === 'batting' ? 'batting' : 'bowling'}
                />
              </div>

              <div className="pt-3 border-t border-[#E5E8E3] text-[10px] text-[#777F79] flex items-center justify-between">
                <span>*Axes represent normalized 0-100 indices calibrated to tournament pool</span>
                <span>Hover over vertices to view exact comparative values</span>
              </div>
            </div>

            {/* "Why Player A ranks above Player B" Rationale Box (5 Cols) */}
            <div className="lg:col-span-5 bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center space-x-2 border-b border-[#E5E8E3] pb-3">
                  <div className="w-7 h-7 rounded-lg bg-[#246B4B]/10 text-[#246B4B] flex items-center justify-center font-bold">
                    <Trophy className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#202522]">
                      Analytical Verdict & Rationale
                    </h3>
                    <p className="text-[10px] text-[#777F79]">
                      Mathematical explanation of head-to-head rankings
                    </p>
                  </div>
                </div>

                <div className="mt-4 p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-2">
                  <div className="text-xs font-extrabold text-[#246B4B]">
                    {comparisonResult.verdict.summary}
                  </div>
                  <p className="text-xs text-[#202522] leading-relaxed">
                    {comparisonResult.verdict.detailedRationale}
                  </p>
                  <div className="pt-2 border-t border-[#E5E8E3] flex items-center justify-between text-[11px] text-[#777F79]">
                    <span>Statistical Confidence:</span>
                    <span className="font-bold text-[#246B4B] bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      {comparisonResult.verdict.confidence} Evidence
                    </span>
                  </div>
                </div>
              </div>

              {/* Player Attributes Quick Cards */}
              <div className="space-y-2 pt-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#777F79]">
                  Qualitative Attributes Comparison
                </span>
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {comparisonResult.players.map((p) => (
                    <div key={p.id} className="p-2.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] text-xs">
                      <div className="font-bold text-[#202522] flex items-center justify-between">
                        <span>{p.name}</span>
                        <span className="text-[10px] text-[#777F79] font-normal">{p.speciality}</span>
                      </div>
                      <div className="text-[10px] text-emerald-800 font-medium mt-1 truncate">
                        + {p.strongestAttributes[0]}
                      </div>
                      <div className="text-[10px] text-[#C44747] truncate">
                        - {p.weaknesses[0]}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Metric-By-Metric Comparison Tables */}
          <div className="space-y-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#202522] flex items-center space-x-2">
              <Shield className="w-4 h-4 text-[#246B4B]" />
              <span>Metric-by-Metric Granular Audit</span>
            </h2>

            {comparisonResult.sections.map((section, sIdx) => (
              <div key={sIdx} className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs overflow-hidden">
                <div className="p-3.5 bg-[#F7F6F2] border-b border-[#E5E8E3]">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#202522]">
                    {section.title}
                  </h3>
                  <p className="text-[10px] text-[#777F79] mt-0.5">
                    {section.description}
                  </p>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-white border-b border-[#E5E8E3] text-[#777F79] font-bold uppercase tracking-wider text-[10px]">
                        <th className="py-2.5 px-4">Metric Dimension</th>
                        {comparisonResult.players.map(p => (
                          <th key={p.id} className="py-2.5 px-4 text-right">
                            {p.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E5E8E3]">
                      {section.metrics.map((m, mIdx) => {
                        // Find highest normalized score for highlighting
                        const maxVal = Math.max(...m.values.map(v => v.normalizedScore));
                        return (
                          <tr key={mIdx} className="hover:bg-[#F7F6F2] transition-colors">
                            <td className="py-2.5 px-4 font-semibold text-[#202522]">
                              {m.name}
                            </td>
                            {m.values.map(v => {
                              const isLeader = v.normalizedScore === maxVal && m.values.length > 1;
                              return (
                                <td key={v.playerId} className="py-2.5 px-4 text-right">
                                  <span
                                    className={`inline-block font-mono text-xs ${
                                      isLeader ? 'font-bold text-[#246B4B] bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200' : 'text-[#777F79]'
                                    }`}
                                  >
                                    {v.displayValue}
                                  </span>
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add Player Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-2xl max-w-md w-full p-5 space-y-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-[#E5E8E3] pb-3">
              <div>
                <h3 className="text-sm font-bold text-[#202522] uppercase tracking-wider">
                  Add Candidate to Comparison
                </h3>
                <p className="text-xs text-[#777F79]">
                  Filtered for {isBattingComparison ? 'Batters & Wicketkeepers' : 'Bowlers & Pace Specialists'}
                </p>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-[#777F79] hover:text-[#202522] p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-[#E5E8E3] pr-1">
              {candidatesToAdd.map(player => (
                <div
                  key={player.id}
                  onClick={() => {
                    addToComparison(player.id);
                    setIsAddModalOpen(false);
                  }}
                  className="p-3 flex items-center justify-between hover:bg-[#F7F6F2] transition-colors cursor-pointer rounded"
                >
                  <div>
                    <div className="font-bold text-xs text-[#202522]">{player.name}</div>
                    <div className="text-[10px] text-[#777F79]">
                      {player.team} • {player.speciality} • {player.sampleSize} balls
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-black text-[#246B4B]">
                      {player.pressureScore ?? 'N/A'}
                    </div>
                    <span className="text-[9px] text-[#777F79]">Clutch score</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-[#E5E8E3] text-right">
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="px-3 py-1.5 bg-[#F7F6F2] text-xs font-semibold text-[#202522] rounded hover:bg-[#eae8e1] cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
