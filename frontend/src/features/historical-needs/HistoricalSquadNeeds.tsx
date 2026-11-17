import React, { useState, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import {
  History,
  ToggleLeft,
  ToggleRight,
  ShieldAlert,
  HelpCircle,
  TrendingUp,
  BookmarkPlus,
  Scale,
  Eye,
  CheckCircle2,
  Calendar,
  AlertTriangle,
  Sparkles,
  Info,
} from 'lucide-react';
import { historicalNeedsService, HistoricalNeedsResponse } from '@/services/historicalNeedsService';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { formatScore } from '@/lib/utils';
import { Player } from '@/types';

export const HistoricalSquadNeeds: React.FC = () => {
  const {
    lastYearSuggestionActive,
    setLastYearSuggestionActive,
    openPlayerProfile,
    addToComparison,
    addPlayerToShortlist,
    addToast,
  } = useApp();

  const [selectedSeason, setSelectedSeason] = useState<string>('Combined');
  const [data, setData] = useState<HistoricalNeedsResponse | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');

  const loadData = async () => {
    const res = await historicalNeedsService.getNeeds(selectedSeason);
    setData(res);
  };

  useEffect(() => {
    loadData();
  }, [selectedSeason]);

  const handleToggle = () => {
    const nextState = !lastYearSuggestionActive;
    setLastYearSuggestionActive(nextState);
    if (nextState) {
      addToast('Last Year Suggestion enabled: Displaying Rajasthan Royals tactical needs & squad fit scores', 'success');
    } else {
      addToast('Last Year Suggestion disabled: Returning to neutral evaluation', 'info');
    }
  };

  const filteredNeeds = data?.needs.filter(n =>
    selectedCategory === 'All' ? true : n.category === selectedCategory
  ) || [];

  const filteredRecommendations = data?.recommendedPlayers.filter(rec =>
    selectedCategory === 'All' ? true : rec.matchedNeed.category === selectedCategory
  ) || [];

  return (
    <div className="space-y-5">
      {/* Top Banner: Master Toggle for 'Last Year Suggestion' */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-[#FDF3EB] text-[#D97736] px-2 py-0.5 rounded border border-[#F8DCC9]">
                Recruitment Intelligence Engine
              </span>
              <span className="text-xs text-[#777F79]">Rajasthan Royals Scouting</span>
            </div>
            <h3 className="text-lg font-bold text-[#202522] mt-1 tracking-tight">
              Historical Squad Weaknesses & Last Year Suggestion
            </h3>
            <p className="text-xs text-[#777F79] mt-0.5 max-w-2xl leading-relaxed">
              Synthesizes match situation choke points across recent IPL campaigns (2023 - 2026) to generate calibrated
              <strong> Squad Fit Scores</strong> tailored specifically to Rajasthan Royals squad composition needs.
            </p>
          </div>

          {/* Prominent Master Toggle Button */}
          <div className="flex items-center space-x-3 bg-[#F7F6F2] p-2.5 rounded-xl border border-[#E5E8E3] shrink-0">
            <div className="text-right">
              <span className="text-xs font-bold text-[#202522] block">Last Year Suggestion</span>
              <span className="text-[10px] text-[#777F79]">
                {lastYearSuggestionActive ? 'Active (RR Targeted)' : 'Inactive (Neutral Mode)'}
              </span>
            </div>
            <button
              onClick={handleToggle}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                lastYearSuggestionActive
                  ? 'bg-[#246B4B] text-white shadow-sm ring-2 ring-[#246B4B]/30'
                  : 'bg-white hover:bg-stone-100 text-[#777F79] border border-[#E5E8E3]'
              }`}
            >
              {lastYearSuggestionActive ? (
                <>
                  <ToggleRight className="w-5 h-5 text-emerald-300" />
                  <span>ENABLED</span>
                </>
              ) : (
                <>
                  <ToggleLeft className="w-5 h-5 text-gray-400" />
                  <span>DISABLED</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Historical Season Selector & Category Filter */}
        <div className="mt-4 pt-4 border-t border-[#E5E8E3] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2 overflow-x-auto">
            <span className="text-[10px] font-bold text-[#777F79] uppercase">Campaign:</span>
            {['Combined', 'IPL 2026', 'IPL 2025', 'IPL 2024', 'IPL 2023'].map(s => (
              <button
                key={s}
                onClick={() => setSelectedSeason(s)}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors cursor-pointer border ${
                  selectedSeason === s
                    ? 'bg-[#202522] text-white border-[#202522]'
                    : 'bg-[#F7F6F2] hover:bg-stone-200 text-[#202522] border-[#E5E8E3]'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-bold text-[#777F79] uppercase">Need Category:</span>
            <select
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
              className="bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1 text-xs text-[#202522] font-medium outline-none focus:border-[#246B4B]"
            >
              <option value="All">All 7 Strategic Categories</option>
              <option value="Middle-order stability against spin">Middle-order vs Spin</option>
              <option value="Pressure finishing and close-chase execution">Pressure Finishing & Close Chase</option>
              <option value="Death-over bowling">Death-over Bowling</option>
              <option value="Middle-over wicket-taking">Middle-over Wickets</option>
              <option value="Powerplay wicket-taking">Powerplay Breakthrough</option>
              <option value="Fast-bowling depth and support">Fast-bowling Depth</option>
              <option value="Genuine all-rounder depth">All-Rounder Balance</option>
            </select>
          </div>
        </div>
      </div>

      {/* STATE A: TOGGLE OFF NOTICE */}
      {!lastYearSuggestionActive ? (
        <div className="bg-white rounded-xl border border-[#E5E8E3] p-8 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-[#F7F6F2] text-[#777F79] flex items-center justify-center mx-auto">
            <History className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-bold text-[#202522]">Last Year Suggestion is Currently Switched OFF</h4>
          <p className="text-xs text-[#777F79] max-w-md mx-auto leading-relaxed">
            Switch the toggle <strong>ON</strong> above to unlock Rajasthan Royals historical squad vulnerability dossiers,
            match situation evidence, and player suggestions weighted by our dedicated <strong>Squad Fit Score</strong>.
          </p>
          <button
            onClick={handleToggle}
            className="px-4 py-2 rounded-lg bg-[#246B4B] text-white text-xs font-semibold hover:bg-[#1b533a] cursor-pointer"
          >
            Enable Last Year Suggestion
          </button>
        </div>
      ) : (
        /* STATE B: TOGGLE ON - FULL HISTORICAL EVIDENCE & SQUAD FIT RECOMMENDATIONS */
        <div className="space-y-6">
          {/* Section 1: Suggested Player Recommendations Sorted by Squad Fit Score */}
          <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#E5E8E3]">
              <div>
                <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-[#246B4B]" />
                  <span>Targeted Player Recommendations by Squad Fit Score</span>
                </h4>
                <p className="text-xs text-[#777F79] mt-0.5">
                  Distinct metric: <strong className="text-[#246B4B]">Squad Fit Score</strong> is calculated independently from Pressure Score and Auction Valuation.
                </p>
              </div>
              <span className="text-[11px] font-bold text-[#246B4B] bg-[#EBF7F1] px-2.5 py-1 rounded border border-[#C3E6D6]">
                {filteredRecommendations.length} Tailored Candidates
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredRecommendations.map((rec, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl border border-[#E5E8E3] bg-[#F7F6F2] hover:border-gray-300 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between">
                      <div>
                        <h4
                          onClick={() => openPlayerProfile(rec.player)}
                          className="font-bold text-sm text-[#202522] hover:text-[#246B4B] cursor-pointer"
                        >
                          {rec.player.name}
                        </h4>
                        <span className="text-[11px] text-[#777F79]">{rec.player.team} • {rec.player.role}</span>
                      </div>
                      {/* Squad Fit Score Badge */}
                      <div className="text-right">
                        <span className="text-xs font-black text-[#246B4B] font-mono bg-white px-2 py-0.5 rounded border border-[#C3E6D6]">
                          Fit: {rec.squadFitScore}/100
                        </span>
                      </div>
                    </div>

                    <div className="mt-2.5 p-2 rounded bg-white border border-[#E5E8E3] text-[11px]">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#D97736] block">
                        Solves Need: {rec.matchedNeed.category}
                      </span>
                      <p className="text-[#202522] mt-0.5 leading-snug">{rec.fitRationale}</p>
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-[#777F79]">
                      <div>
                        <span>Pressure Index:</span>
                        <strong className="text-[#202522] block">{formatScore(rec.player.pressureScore)}/100</strong>
                      </div>
                      <div>
                        <span>Est. Auction Price:</span>
                        <strong className="text-[#202522] block font-mono">
                          ₹{rec.player.auctionEstimatedMin ?? 1}-{rec.player.auctionEstimatedMax ?? 2} Cr
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-[#E5E8E3] flex items-center justify-between">
                    <StatusBadge status={rec.player.internationalStatus} />
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => addToComparison(rec.player.id)}
                        className="p-1.5 rounded hover:bg-stone-200 text-[#777F79] cursor-pointer"
                        title="Compare"
                      >
                        <Scale className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => addPlayerToShortlist(rec.player, `Rec: ${rec.matchedNeed.category}`)}
                        className="p-1.5 rounded bg-white hover:bg-stone-200 text-[#246B4B] border border-[#E5E8E3] cursor-pointer"
                        title="Add to Shortlist"
                      >
                        <BookmarkPlus className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section 2: Historical Evidence Panels */}
          <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-4">
            <div className="pb-3 border-b border-[#E5E8E3]">
              <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider flex items-center space-x-2">
                <History className="w-4 h-4 text-[#D97736]" />
                <span>Documented Historical Evidence & Tactical Match Context</span>
              </h4>
              <p className="text-xs text-[#777F79] mt-0.5">
                Observed match situations, performance indicators, and confidence status across seasons
              </p>
            </div>

            <div className="space-y-4">
              {filteredNeeds.map(need => (
                <div
                  key={need.id}
                  className="p-4 rounded-xl border border-[#E5E8E3] bg-[#F7F6F2] text-xs space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-[#E5E8E3] gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-sm text-[#202522]">{need.category}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-white border border-[#E5E8E3] text-[#777F79]">
                        {need.season}
                      </span>
                    </div>
                    <span className="text-[10px] font-semibold text-emerald-800 bg-[#EBF7F1] px-2 py-0.5 rounded border border-[#C3E6D6]">
                      {need.confidenceStatus}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#777F79] block mb-1">
                      Historical Observation & Choke Points
                    </span>
                    <p className="text-[#202522] leading-relaxed">{need.historicalObservation}</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                    <div className="p-2.5 rounded bg-white border border-[#E5E8E3]">
                      <span className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
                        Relevant Match Situations
                      </span>
                      <p className="text-[#202522]">{need.relevantMatchSituations}</p>
                    </div>

                    <div className="p-2.5 rounded bg-white border border-[#E5E8E3]">
                      <span className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
                        Source Reference
                      </span>
                      <p className="text-[#202522]">{need.sourceReference}</p>
                    </div>
                  </div>

                  <div className="p-2.5 rounded bg-white border border-[#E5E8E3]">
                    <span className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
                      Supporting Performance Indicators
                    </span>
                    <ul className="list-disc list-inside space-y-0.5 text-[#202522]">
                      {need.supportingIndicators.map((ind, i) => (
                        <li key={i}>{ind}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-2.5 rounded bg-[#EBF7F1]/60 border border-[#C3E6D6]">
                    <span className="text-[10px] font-bold text-[#246B4B] uppercase block">
                      Recruitment Strategy Recommendation
                    </span>
                    <p className="text-[#202522] mt-0.5 font-medium">{need.recruitmentImplication}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

