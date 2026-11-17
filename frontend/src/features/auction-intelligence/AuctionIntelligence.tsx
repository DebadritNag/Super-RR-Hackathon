import React from 'react';
import { useApp } from '@/context/AppContext';
import {
  Coins,
  Calculator,
  TrendingUp,
  Shield,
  Users,
  Target,
  ArrowRight,
  BookmarkPlus,
  Scale,
  Eye,
  Info,
  Sparkles,
} from 'lucide-react';
import { StatCard } from '@/components/shared/StatCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { formatCrore, formatScore } from '@/lib/utils';

export const AuctionIntelligence: React.FC = () => {
  const {
    hypotheticalPurseCr,
    setHypotheticalPurseCr,
    setActiveSection,
    openPlayerProfile,
    addToComparison,
    addPlayerToShortlist,
    squadCount,
  } = useApp();

  const candidates = MOCK_PLAYERS.filter(p => p.auctionEstimatedMax !== null);

  return (
    <div className="space-y-6">
      {/* Disclaimer Header */}
      <div className="p-3.5 bg-[#FDF3EB] border border-[#F8DCC9] rounded-xl flex items-start space-x-3 text-xs">
        <Coins className="w-4 h-4 text-[#D97736] shrink-0 mt-0.5" />
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-[#D97736] uppercase tracking-wider text-[10px] bg-amber-200/50 px-1.5 py-0.5 rounded">
              Demonstration Planning Module
            </span>
            <span className="font-semibold text-[#202522]">Hypothetical Auction Strategy Workspace</span>
          </div>
          <p className="text-[#777F79] mt-0.5 leading-relaxed">
            All price estimates, value-for-money ratings, and budget ranges are illustrative modeling constructs.
            Never presents invented numbers as official Rajasthan Royals bids or confidential budgets.
          </p>
        </div>
      </div>

      {/* Purse & Budget Status Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl border border-[#246B4B]/30 bg-white shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#777F79] block">
            Hypothetical Purse Budget
          </span>
          <h3 className="text-2xl font-black text-[#246B4B] mt-1 font-mono">
            {formatCrore(hypotheticalPurseCr)}
          </h3>
          <span className="text-[11px] text-[#777F79] mt-0.5 block">Configurable planning purse</span>
        </div>

        <div className="p-4 rounded-xl border border-[#E5E8E3] bg-white shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#777F79] block">
            Target Squad Slots
          </span>
          <h3 className="text-2xl font-bold text-[#202522] mt-1 font-mono">
            {squadCount} / 25
          </h3>
          <span className="text-[11px] text-[#777F79] mt-0.5 block">{25 - squadCount} slots remaining</span>
        </div>

        <div className="p-4 rounded-xl border border-[#E5E8E3] bg-white shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#777F79] block">
            Overseas Roster Cap
          </span>
          <h3 className="text-2xl font-bold text-[#202522] mt-1 font-mono">
            2 / 8
          </h3>
          <span className="text-[11px] text-[#777F79] mt-0.5 block">6 overseas slots available</span>
        </div>

        <div className="p-4 rounded-xl border border-[#D97736]/40 bg-white shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#D97736] block">
              Purse Explorer Shortcut
            </span>
            <p className="text-xs text-[#202522] font-semibold mt-1">Simulate budgets with live slider</p>
          </div>
          <button
            onClick={() => setActiveSection('purse-explorer')}
            className="mt-2 w-full py-1.5 rounded-lg bg-[#D97736] text-white text-xs font-bold hover:bg-[#b85f26] transition-colors flex items-center justify-center space-x-1 cursor-pointer"
          >
            <span>Open Purse Explorer</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Candidate Auction Cards Grid */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#E5E8E3] gap-2">
          <div>
            <h3 className="text-sm font-bold text-[#202522] uppercase tracking-wider flex items-center space-x-2">
              <Coins className="w-4 h-4 text-[#246B4B]" />
              <span>Target Player Auction Intelligence Cards</span>
            </h3>
            <p className="text-xs text-[#777F79] mt-0.5">
              Comprehensive valuation dossiers: Pressure Score vs Squad Fit vs Auction Value Rating
            </p>
          </div>
          <button
            onClick={() => setActiveSection('purse-explorer')}
            className="text-xs font-bold text-[#246B4B] hover:underline flex items-center space-x-1 cursor-pointer"
          >
            <span>Filter by Available Purse</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {candidates.map(p => (
            <div
              key={p.id}
              className="p-4 rounded-xl border border-[#E5E8E3] bg-[#F7F6F2] hover:border-gray-300 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <h4
                      onClick={() => openPlayerProfile(p)}
                      className="font-bold text-sm text-[#202522] hover:text-[#246B4B] cursor-pointer"
                    >
                      {p.name}
                    </h4>
                    <span className="text-[11px] text-[#777F79]">{p.team} • {p.role}</span>
                  </div>
                  <StatusBadge status={p.internationalStatus} />
                </div>

                {/* Triple Score Metric Bar */}
                <div className="mt-3 grid grid-cols-3 gap-1.5 p-2 rounded bg-white border border-[#E5E8E3] text-center text-xs">
                  <div>
                    <span className="text-[9px] text-[#777F79] uppercase block font-semibold">Pressure</span>
                    <strong className="text-[#246B4B] text-sm">{formatScore(p.pressureScore)}</strong>
                  </div>
                  <div>
                    <span className="text-[9px] text-[#777F79] uppercase block font-semibold">Squad Fit</span>
                    <strong className="text-[#202522] text-sm">{p.squadFitScore ?? 'N/A'}</strong>
                  </div>
                  <div>
                    <span className="text-[9px] text-[#777F79] uppercase block font-semibold">Value Score</span>
                    <strong className="text-[#D97736] text-sm">{p.auctionValueScore}</strong>
                  </div>
                </div>

                {/* Estimated Price Range */}
                <div className="mt-3 p-2.5 rounded bg-white border border-[#E5E8E3] text-xs">
                  <div className="flex justify-between items-baseline">
                    <span className="text-[10px] font-bold text-[#777F79] uppercase">Estimated Auction Range</span>
                    <span className="text-[10px] font-semibold text-emerald-700 bg-[#EBF7F1] px-1.5 py-0.2 rounded">
                      {p.auctionConfidence} Confidence
                    </span>
                  </div>
                  <div className="text-base font-black text-[#202522] font-mono mt-0.5">
                    {formatCrore(p.auctionEstimatedMin)} - {formatCrore(p.auctionEstimatedMax)}
                  </div>
                  <span className="text-[10px] text-[#777F79] block mt-0.5">
                    {p.isPriceHistoryAvailable ? 'Based on multi-season hammer prices' : 'Insufficient auction-price history to estimate market price.'}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-2.5 border-t border-[#E5E8E3] flex items-center justify-between">
                <span className="text-[11px] text-[#777F79] font-medium">{p.speciality}</span>
                <div className="flex items-center space-x-1.5">
                  <button
                    onClick={() => addToComparison(p.id)}
                    className="p-1.5 rounded hover:bg-stone-200 text-[#777F79] cursor-pointer"
                    title="Compare"
                  >
                    <Scale className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => addPlayerToShortlist(p, 'Added from Auction Intelligence')}
                    className="p-1.5 rounded bg-white hover:bg-stone-200 text-[#246B4B] border border-[#E5E8E3] cursor-pointer"
                    title="Shortlist"
                  >
                    <BookmarkPlus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => openPlayerProfile(p)}
                    className="px-2.5 py-1 rounded bg-[#246B4B] hover:bg-[#1b533a] text-white text-xs font-semibold cursor-pointer"
                  >
                    Profile
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

