import React, { useState } from 'react';
import { useApp } from '@/context/AppContext';
import {
  X,
  Scale,
  TrendingUp,
  AlertCircle,
  HelpCircle,
  User,
  Shield,
  Trophy,
  Target,
  Sparkles,
} from 'lucide-react';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PlayerRadarChart } from '@/components/charts/PlayerRadarChart';
import { formatPercent, formatScore } from '@/lib/utils';

export const PlayerProfileModal: React.FC = () => {
  const {
    selectedPlayerForProfile,
    closePlayerProfile,
    addToComparison,
    comparisonPlayerIds,
  } = useApp();

  const [activeTab, setActiveTab] = useState<'overview' | 'radar' | 'splits' | 'explanation'>('overview');

  if (!selectedPlayerForProfile) return null;

  const player = selectedPlayerForProfile;
  const isBatter = player.role === 'Batter' || player.role === 'Wicketkeeper' || (player.role === 'All-rounder' && !!player.batterRadar);
  const isBowler = player.role === 'Bowler' || (player.role === 'All-rounder' && !!player.bowlerRadar);
  const isInComparison = comparisonPlayerIds.includes(player.id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl border border-[#E5E8E3] max-w-4xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in duration-150">
        {/* Top Header */}
        <div className="p-4 sm:p-5 border-b border-[#E5E8E3] bg-[#F7F6F2] flex items-start justify-between">
          <div className="flex items-start space-x-4">
            <div className="w-14 h-14 rounded-lg bg-[#202522] border border-gray-700 flex items-center justify-center text-white font-bold text-lg shrink-0 shadow-sm relative overflow-hidden">
              {player.photoUrl ? (
                <img src={player.photoUrl} alt={player.name} className="w-full h-full object-cover" />
              ) : (
                <User className="w-7 h-7 text-gray-400" />
              )}
              {player.designation === 'Captain' && (
                <span className="absolute bottom-0 inset-x-0 bg-amber-500 text-[8px] text-white font-bold text-center tracking-wider uppercase py-0.2">
                  CPT
                </span>
              )}
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <h2 className="text-lg sm:text-xl font-bold text-[#202522] tracking-tight">{player.name}</h2>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-white border border-[#E5E8E3] text-[#777F79]">
                  {player.team}
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#246B4B]/10 text-[#246B4B]">
                  {player.internationalStatus}
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-50 text-[#D97736] border border-amber-200">
                  {player.dataStatus}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#777F79] mt-1.5">
                <span>Role: <strong className="text-[#202522]">{player.role}</strong> ({player.speciality})</span>
                <span>•</span>
                <span>Nationality: <strong className="text-[#202522]">{player.nationality}</strong></span>
                <span>•</span>
                <span>Player ID: <strong className="font-mono text-[#202522]">{player.id}</strong></span>
                <span>•</span>
                <span>Style: <strong className="text-[#202522]">{player.battingStyle}</strong> {player.bowlingStyle && `/ ${player.bowlingStyle}`}</span>
              </div>
            </div>
          </div>

          <button
            onClick={closePlayerProfile}
            className="p-1.5 rounded-md hover:bg-stone-200 text-[#777F79] hover:text-[#202522] transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Bar & Tabs */}
        <div className="px-5 py-2.5 bg-white border-b border-[#E5E8E3] flex flex-wrap items-center justify-between gap-2">
          {/* Tabs */}
          <div className="flex items-center space-x-1 sm:space-x-2">
            {[
              { id: 'overview', label: 'Analytics Overview' },
              { id: 'radar', label: '8-Axis Radar Profile' },
              { id: 'splits', label: 'Match Splits' },
              { id: 'explanation', label: 'Scouting Rationale' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                  activeTab === tab.id
                    ? 'bg-[#246B4B] text-white'
                    : 'text-[#777F79] hover:bg-[#F7F6F2] hover:text-[#202522]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => addToComparison(player.id)}
              disabled={isInComparison}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold border transition-colors cursor-pointer ${
                isInComparison
                  ? 'bg-stone-100 text-stone-400 border-stone-200 cursor-not-allowed'
                  : 'bg-[#246B4B] text-white hover:bg-[#1b5239] border-transparent'
              }`}
            >
              <Scale className="w-3.5 h-3.5" />
              <span>{isInComparison ? 'In Comparison' : 'Add to Comparison'}</span>
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto flex-1 bg-white">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-5">
              {/* Key Metric Tiles */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg border border-[#246B4B]/30 bg-[#EBF7F1]/40">
                  <span className="text-[10px] font-bold text-[#246B4B] uppercase tracking-wider block">
                    Pressure Index
                  </span>
                  <div className="flex items-baseline space-x-1 mt-1">
                    <span className="text-2xl font-black text-[#246B4B]">
                      {formatScore(player.pressureScore)}
                    </span>
                    <span className="text-xs text-[#777F79]">/ 100</span>
                  </div>
                  <span className="text-[10px] text-[#777F79] mt-0.5 block">
                    Uncertainty: {player.uncertaintyInterval ? `[${player.uncertaintyInterval[0]} - ${player.uncertaintyInterval[1]}]` : 'N/A'}
                  </span>
                </div>

                <div className="p-3 rounded-lg border border-[#E5E8E3] bg-[#F7F6F2]">
                  <span className="text-[10px] font-bold text-[#777F79] uppercase tracking-wider block">
                    Baseline Rating
                  </span>
                  <div className="flex items-baseline space-x-1 mt-1">
                    <span className="text-2xl font-bold text-[#202522]">
                      {isBowler ? `${player.baselineEconomy ?? 7.8} RPO` : formatScore(player.baselineScore)}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#777F79] mt-0.5 block">Context-adjusted standard</span>
                </div>

                <div className="p-3 rounded-lg border border-[#E5E8E3] bg-[#F7F6F2]">
                  <span className="text-[10px] font-bold text-[#777F79] uppercase tracking-wider block">
                    Residual Impact
                  </span>
                  <div className="flex items-baseline space-x-1 mt-1">
                    <span className="text-2xl font-bold text-[#27845B]">
                      {formatPercent(player.adjustedPerformance)}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#777F79] mt-0.5 block">Bayesian residual vs baseline</span>
                </div>

                <div className="p-3 rounded-lg border border-[#E5E8E3] bg-[#F7F6F2]">
                  <span className="text-[10px] font-bold text-[#777F79] uppercase tracking-wider block">
                    Pressure Sample
                  </span>
                  <div className="flex items-baseline space-x-1 mt-1">
                    <span className="text-2xl font-bold text-[#202522]">
                      {player.sampleSize}
                    </span>
                    <span className="text-xs text-[#777F79]">balls</span>
                  </div>
                  <span className="text-[10px] text-[#777F79] mt-0.5 block">Across {player.matches} distinct matches</span>
                </div>
              </div>

              {/* Tactical Rationale Summary */}
              <div className="p-4 rounded-lg bg-[#F7F6F2] border border-[#E5E8E3] space-y-2">
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-[#246B4B]" />
                  <span className="text-xs font-bold text-[#202522] uppercase tracking-wider">
                    Core Competition Justification
                  </span>
                </div>
                <p className="text-xs text-[#202522] leading-relaxed">
                  {player.rankingRationale}
                </p>
                {player.squadFitReason && (
                  <p className="text-xs text-[#246B4B] font-semibold pt-1 border-t border-[#E5E8E3]">
                    RR Tactical Fit: {player.squadFitReason}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: RADAR PROFILE */}
          {activeTab === 'radar' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-[#777F79]">
                <span>Normalized 0–100 Presentation Metrics</span>
                <span>Hover over vertices to view underlying cricket statistics</span>
              </div>
              <div className="bg-[#F7F6F2] p-4 rounded-xl border border-[#E5E8E3]">
                {isBatter && (
                  <PlayerRadarChart
                    type="batter"
                    playerName={player.name}
                    batterMetrics={player.batterRadar}
                  />
                )}
                {isBowler && !isBatter && (
                  <PlayerRadarChart
                    type="bowler"
                    playerName={player.name}
                    bowlerMetrics={player.bowlerRadar}
                  />
                )}
              </div>
            </div>
          )}

          {/* TAB 3: SITUATION SPLITS */}
          {activeTab === 'splits' && (
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-2">
                  <span className="font-bold text-[#202522] uppercase tracking-wider text-[11px]">
                    Excels in Situations
                  </span>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {player.excelsInSituations.map((sit, idx) => (
                      <span key={idx} className="bg-white border border-[#E5E8E3] px-2 py-1 rounded text-[#202522] font-semibold">
                        {sit}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3.5 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-2">
                  <span className="font-bold text-[#202522] uppercase tracking-wider text-[11px]">
                    Key Strengths
                  </span>
                  <ul className="list-disc list-inside space-y-1 text-[#777F79]">
                    {player.strongestAttributes.map((attr, idx) => (
                      <li key={idx}><strong className="text-[#202522]">{attr}</strong></li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="p-3.5 bg-red-50/50 rounded-lg border border-red-200 space-y-1">
                <span className="font-bold text-[#C44747] uppercase tracking-wider text-[11px]">
                  Known Vulnerabilities
                </span>
                <p className="text-xs text-[#202522]">
                  {player.weaknesses.join('; ')}
                </p>
              </div>
            </div>
          )}

          {/* TAB 4: SCOUTING RATIONALE & DATA LIMITATIONS */}
          {activeTab === 'explanation' && (
            <div className="space-y-4 text-xs">
              <div className="p-4 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] space-y-2">
                <div className="font-bold text-[#202522] uppercase tracking-wider">
                  Data Sample & Credible Interval Bounds
                </div>
                <p className="text-[#777F79] leading-relaxed">
                  {player.dataLimitations}
                </p>
                <div className="text-[11px] text-[#202522] pt-2 border-t border-[#E5E8E3]">
                  <strong>Reliability Tier:</strong> {player.reliability} • <strong>Eligibility:</strong> {player.eligibility}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-[#E5E8E3] bg-[#F7F6F2] flex items-center justify-between text-xs">
          <span className="text-[#777F79]">
            SupeRR Selector Season 2 • Confidential Competition Record
          </span>
          <button
            onClick={closePlayerProfile}
            className="px-4 py-1.5 bg-white border border-[#E5E8E3] text-[#202522] font-semibold rounded hover:bg-stone-100 transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
