import React, { useState, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import {
  Calculator,
  Coins,
  TrendingUp,
  AlertTriangle,
  Sparkles,
  Plus,
  Minus,
  RotateCcw,
  CheckCircle2,
  BookmarkPlus,
  Scale,
  Eye,
  ArrowRight,
  ShieldAlert,
  Layers,
  ArrowUpRight,
} from 'lucide-react';
import { auctionService, BudgetQueryResult } from '@/services/auctionService';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { formatCrore, formatScore } from '@/lib/utils';
import { Player } from '@/types';

export const AuctionPurseExplorer: React.FC = () => {
  const {
    hypotheticalPurseCr,
    setHypotheticalPurseCr,
    openPlayerProfile,
    addToComparison,
    addPlayerToShortlist,
    addToast,
  } = useApp();

  const [purseInput, setPurseInput] = useState<string>(hypotheticalPurseCr.toString());
  const [queryResult, setQueryResult] = useState<BudgetQueryResult | null>(null);
  const [activeTab, setActiveTab] = useState<'within-budget' | 'value' | 'premium' | 'uncapped' | 'combinations'>('within-budget');

  const updatePurse = (amount: number) => {
    const clamped = Math.max(0, Math.min(35, Number(amount.toFixed(1))));
    setHypotheticalPurseCr(clamped);
    setPurseInput(clamped.toString());
  };

  const handleInputChange = (val: string) => {
    setPurseInput(val);
    const num = parseFloat(val);
    if (!isNaN(num) && num >= 0 && num <= 35) {
      setHypotheticalPurseCr(Number(num.toFixed(1)));
    }
  };

  const loadBudgetResults = async () => {
    const res = await auctionService.queryByBudget(hypotheticalPurseCr);
    setQueryResult(res);
  };

  useEffect(() => {
    loadBudgetResults();
  }, [hypotheticalPurseCr]);

  return (
    <div className="space-y-6">
      {/* SECTION 1: MANDATORY INTERACTIVE PURSE SLIDER HERO */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-6 shadow-sm space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-[#E5E8E3] pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-[#246B4B] text-white px-2 py-0.5 rounded">
                Interactive Simulator
              </span>
              <span className="text-xs text-[#777F79]">Auction Budget Optimizer</span>
            </div>
            <h2 className="text-xl font-black text-[#202522] tracking-tight mt-1">
              How much purse do you have?
            </h2>
            <p className="text-xs text-[#777F79] mt-0.5">
              Explore which players you should target within your available auction budget.
            </p>
          </div>

          {/* Quick Increment Controls & Reset */}
          <div className="flex items-center space-x-1.5 self-start md:self-auto">
            <button
              onClick={() => updatePurse(hypotheticalPurseCr - 1)}
              className="px-2.5 py-1.5 rounded-lg bg-[#F7F6F2] hover:bg-stone-200 border border-[#E5E8E3] text-xs font-bold text-[#202522] transition-colors cursor-pointer"
              title="-1 Cr"
            >
              -1 Cr
            </button>
            <button
              onClick={() => updatePurse(hypotheticalPurseCr + 1)}
              className="px-2.5 py-1.5 rounded-lg bg-[#F7F6F2] hover:bg-stone-200 border border-[#E5E8E3] text-xs font-bold text-[#202522] transition-colors cursor-pointer"
              title="+1 Cr"
            >
              +1 Cr
            </button>
            <button
              onClick={() => updatePurse(15.0)}
              className="p-1.5 rounded-lg bg-[#F7F6F2] hover:bg-stone-200 border border-[#E5E8E3] text-[#777F79] hover:text-[#202522] transition-colors cursor-pointer"
              title="Reset to ₹15 Cr default"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Synchronized Slider and Numeric Input Bar */}
        <div className="bg-[#F7F6F2] p-5 rounded-xl border border-[#E5E8E3] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-baseline space-x-3">
              <span className="text-xs font-bold text-[#777F79] uppercase tracking-wider">
                Target Available Purse:
              </span>
              <div className="flex items-center space-x-2">
                <span className="text-3xl font-black text-[#246B4B] font-mono tracking-tight">
                  ₹{hypotheticalPurseCr.toFixed(1)}
                </span>
                <span className="text-lg font-bold text-[#202522]">Crore</span>
              </div>
            </div>

            {/* Direct Synchronized Numeric Input */}
            <div className="flex items-center space-x-2">
              <label className="text-xs text-[#777F79] font-medium">Exact Input (₹ Cr):</label>
              <input
                type="number"
                min="0"
                max="35"
                step="0.5"
                value={purseInput}
                onChange={e => handleInputChange(e.target.value)}
                className="w-24 px-3 py-1.5 bg-white border border-[#E5E8E3] rounded-lg text-sm font-bold text-[#202522] font-mono text-center outline-none focus:border-[#246B4B]"
              />
            </div>
          </div>

          {/* Interactive Range Slider (0 to 30+ Cr) */}
          <div className="space-y-1.5 pt-1">
            <input
              type="range"
              min="0"
              max="30"
              step="0.5"
              value={hypotheticalPurseCr}
              onChange={e => updatePurse(parseFloat(e.target.value))}
              className="w-full h-2.5 bg-stone-300 rounded-lg appearance-none cursor-pointer accent-[#246B4B]"
            />
            <div className="flex justify-between text-[10px] font-mono text-[#777F79]">
              <span>₹0 Cr</span>
              <span>₹5 Cr</span>
              <span>₹10 Cr</span>
              <span>₹15 Cr</span>
              <span>₹20 Cr</span>
              <span>₹25 Cr</span>
              <span>₹30 Cr</span>
            </div>
          </div>
        </div>

        {/* Live Filter Summary Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          <span className="text-[11px] text-[#777F79] font-medium">Current Purse Affordability:</span>
          <span className="px-2.5 py-0.5 rounded-full bg-[#EBF7F1] text-[#246B4B] font-bold border border-[#C3E6D6]">
            {queryResult?.bestWithinBudget.length ?? 0} Players Within Budget
          </span>
          <span className="px-2.5 py-0.5 rounded-full bg-[#FDF3EB] text-[#D97736] font-bold border border-[#F8DCC9]">
            {queryResult?.premiumTargets.length ?? 0} Premium Targets Above Budget
          </span>
          <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 font-bold border border-blue-200">
            {queryResult?.uncappedOpportunities.indianUncapped.length ?? 0} Indian Uncapped Options
          </span>
        </div>
      </div>

      {/* SECTION 2: BUDGET RESULTS TABS & CONTENT */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs overflow-hidden">
        {/* Navigation Tabs */}
        <div className="flex items-center space-x-1 p-3 bg-[#F7F6F2] border-b border-[#E5E8E3] overflow-x-auto">
          {[
            { id: 'within-budget', label: `Best Within Budget (${queryResult?.bestWithinBudget.length ?? 0})` },
            { id: 'value', label: `Best Value-for-Money (${queryResult?.bestValueForMoney.length ?? 0})` },
            { id: 'premium', label: `Premium Targets (${queryResult?.premiumTargets.length ?? 0})` },
            { id: 'uncapped', label: 'Uncapped Opportunities' },
            { id: 'combinations', label: 'Build My Auction Combination' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-white text-[#246B4B] shadow-xs border border-[#E5E8E3]'
                  : 'text-[#777F79] hover:text-[#202522]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab 1: Best Within Budget */}
        {activeTab === 'within-budget' && (
          <div className="p-5 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#E5E8E3]">
              <div>
                <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider">
                  Candidates Fitting Under ₹{hypotheticalPurseCr.toFixed(1)} Cr Maximum Estimate
                </h4>
                <p className="text-xs text-[#777F79]">Ranked by clutch pressure index</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {queryResult?.bestWithinBudget.map(p => (
                <PlayerAuctionCard
                  key={p.id}
                  player={p}
                  currentPurse={hypotheticalPurseCr}
                  onProfile={() => openPlayerProfile(p)}
                  onShortlist={() => addPlayerToShortlist(p, `Targeted within ₹${hypotheticalPurseCr} Cr budget`)}
                  onCompare={() => addToComparison(p.id)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Tab 2: Best Value for Money */}
        {activeTab === 'value' && (
          <div className="p-5 space-y-4">
            <div className="pb-2 border-b border-[#E5E8E3]">
              <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider">
                High Value-for-Money Prospects
              </h4>
              <p className="text-xs text-[#777F79]">
                Players delivering exceptional pressure output relative to their estimated acquisition cost
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {queryResult?.bestValueForMoney.map(p => (
                <PlayerAuctionCard
                  key={p.id}
                  player={p}
                  currentPurse={hypotheticalPurseCr}
                  onProfile={() => openPlayerProfile(p)}
                  onShortlist={() => addPlayerToShortlist(p, `Value pick at ₹${hypotheticalPurseCr} Cr`)}
                  onCompare={() => addToComparison(p.id)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Premium Targets (Above Budget + Deficit Needed) */}
        {activeTab === 'premium' && (
          <div className="p-5 space-y-5">
            <div className="pb-2 border-b border-[#E5E8E3]">
              <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider">
                Premium Targets Exceeding Current Budget
              </h4>
              <p className="text-xs text-[#777F79]">
                Shows top-tier marquee players and the exact additional purse required to acquire them
              </p>
            </div>

            <div className="space-y-3">
              {queryResult?.premiumTargets.map((pt, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl border border-rose-200 bg-rose-50/40 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-[#202522] text-white flex items-center justify-center font-bold shrink-0">
                      {pt.player.name.charAt(0)}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h4
                          onClick={() => openPlayerProfile(pt.player)}
                          className="font-bold text-sm text-[#202522] hover:text-[#246B4B] cursor-pointer"
                        >
                          {pt.player.name}
                        </h4>
                        <StatusBadge status={pt.player.internationalStatus} />
                      </div>
                      <span className="text-[#777F79]">{pt.player.team} • {pt.player.role} ({pt.player.speciality})</span>
                      <div className="mt-1 font-mono font-semibold text-[#202522]">
                        Est. Cost: {formatCrore(pt.player.auctionEstimatedMin)} - {formatCrore(pt.player.auctionEstimatedMax)}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 self-end md:self-auto">
                    <div className="text-right">
                      <span className="text-[10px] uppercase font-bold text-[#C44747] block">Purse Deficit</span>
                      <span className="text-base font-black text-[#C44747] font-mono">
                        +{formatCrore(pt.surplusNeededCr)} needed
                      </span>
                    </div>

                    <button
                      onClick={() => openPlayerProfile(pt.player)}
                      className="px-3 py-1.5 rounded-lg bg-white border border-[#E5E8E3] text-[#202522] font-semibold hover:bg-stone-100 cursor-pointer"
                    >
                      Inspect Profile
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Alternative Targets Panel */}
            <div className="mt-6 pt-4 border-t border-[#E5E8E3]">
              <h5 className="text-xs font-bold text-[#202522] uppercase tracking-wider mb-2">
                Suggested Lower-Cost Alternatives
              </h5>
              <p className="text-xs text-[#777F79] mb-3">
                If the above marquee targets exceed your purse limit, consider these statistically comparable options:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {queryResult?.alternativeTargets.map((alt, i) => (
                  <div key={i} className="p-3 rounded-lg border border-[#E5E8E3] bg-[#F7F6F2] text-xs">
                    <span className="text-[10px] text-[#777F79] uppercase block font-semibold">
                      Instead of Premium Target: <strong className="text-[#202522]">{alt.original.name}</strong>
                    </span>
                    <div className="mt-2 space-y-1.5">
                      {alt.alternatives.map(a => (
                        <div key={a.id} className="p-2 rounded bg-white border border-[#E5E8E3] flex justify-between items-center">
                          <div>
                            <span className="font-bold text-[#202522] block">{a.name}</span>
                            <span className="text-[10px] text-[#777F79]">{a.team} • {a.role}</span>
                          </div>
                          <div className="text-right">
                            <span className="font-bold text-[#246B4B] block">{formatScore(a.pressureScore)}/100</span>
                            <span className="font-mono text-[10px] text-[#777F79]">
                              ₹{a.auctionEstimatedMin}-{a.auctionEstimatedMax} Cr
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Uncapped Opportunities */}
        {activeTab === 'uncapped' && (
          <div className="p-5 space-y-5">
            <div className="pb-2 border-b border-[#E5E8E3]">
              <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider">
                Uncapped Opportunities (Indian vs Overseas)
              </h4>
              <p className="text-xs text-[#777F79]">
                High-ceiling recruits under ₹{hypotheticalPurseCr.toFixed(1)} Cr without international caps
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Indian Uncapped */}
              <div className="space-y-3">
                <span className="text-xs font-bold text-[#246B4B] uppercase tracking-wider block border-b border-emerald-200 pb-1">
                  Indian Uncapped Prospects ({queryResult?.uncappedOpportunities.indianUncapped.length})
                </span>
                {queryResult?.uncappedOpportunities.indianUncapped.map(p => (
                  <div key={p.id} className="p-3 rounded-lg border border-[#E5E8E3] bg-[#F7F6F2] flex justify-between items-center text-xs">
                    <div>
                      <strong className="text-sm text-[#202522] block hover:text-[#246B4B] cursor-pointer" onClick={() => openPlayerProfile(p)}>
                        {p.name}
                      </strong>
                      <span className="text-[10px] text-[#777F79]">{p.team} • {p.role} ({p.speciality})</span>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-black text-[#246B4B] block">{formatScore(p.pressureScore)}</span>
                      <span className="text-[10px] text-[#777F79] font-mono">
                        ₹{p.auctionEstimatedMin}-{p.auctionEstimatedMax} Cr
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Overseas Uncapped */}
              <div className="space-y-3">
                <span className="text-xs font-bold text-[#D97736] uppercase tracking-wider block border-b border-amber-200 pb-1">
                  Overseas Uncapped Prospects ({queryResult?.uncappedOpportunities.overseasUncapped.length})
                </span>
                {queryResult?.uncappedOpportunities.overseasUncapped.map(p => (
                  <div key={p.id} className="p-3 rounded-lg border border-[#E5E8E3] bg-[#F7F6F2] flex justify-between items-center text-xs">
                    <div>
                      <strong className="text-sm text-[#202522] block hover:text-[#246B4B] cursor-pointer" onClick={() => openPlayerProfile(p)}>
                        {p.name}
                      </strong>
                      <span className="text-[10px] text-[#777F79]">{p.team} • {p.role} ({p.speciality})</span>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-black text-[#246B4B] block">{formatScore(p.pressureScore)}</span>
                      <span className="text-[10px] text-[#777F79] font-mono">
                        ₹{p.auctionEstimatedMin}-{p.auctionEstimatedMax} Cr
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Build My Auction Combination */}
        {activeTab === 'combinations' && (
          <div className="p-5 space-y-4">
            <div className="pb-2 border-b border-[#E5E8E3]">
              <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider flex items-center space-x-1.5">
                <Layers className="w-4 h-4 text-[#246B4B]" />
                <span>Build My Auction Combination</span>
              </h4>
              <p className="text-xs text-[#777F79]">
                Pre-calibrated multi-target strategic packages tested against your ₹{hypotheticalPurseCr.toFixed(1)} Cr purse
              </p>
            </div>

            <div className="space-y-4">
              {queryResult?.recommendedCombinations.map(combo => (
                <div
                  key={combo.id}
                  className={`p-4 rounded-xl border transition-all text-xs space-y-3 ${
                    combo.affordable
                      ? 'border-[#246B4B]/40 bg-[#EBF7F1]/30'
                      : 'border-[#E5E8E3] bg-[#F7F6F2] opacity-80'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-gray-200 gap-2">
                    <div>
                      <h4 className="text-sm font-bold text-[#202522]">{combo.title}</h4>
                      <p className="text-[11px] text-[#777F79]">{combo.description}</p>
                    </div>

                    <div className="text-right">
                      {combo.affordable ? (
                        <span className="text-xs font-bold text-[#246B4B] bg-[#EBF7F1] px-2.5 py-1 rounded border border-[#C3E6D6]">
                          ✓ Affordable (₹{combo.remainingPurseCr} Cr buffer)
                        </span>
                      ) : (
                        <span className="text-xs font-bold text-[#C44747] bg-rose-50 px-2.5 py-1 rounded border border-rose-200">
                          Exceeds Purse
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="p-2.5 rounded bg-white border border-[#E5E8E3]">
                      <span className="text-[10px] font-bold uppercase text-[#777F79] block mb-1">Total Estimated Cost</span>
                      <span className="text-base font-black text-[#202522] font-mono">
                        ₹{combo.estimatedTotalMin} - ₹{combo.estimatedTotalMax} Cr
                      </span>
                    </div>

                    <div className="p-2.5 rounded bg-white border border-[#E5E8E3]">
                      <span className="text-[10px] font-bold uppercase text-[#777F79] block mb-1">Tactical Coverage</span>
                      <span className="font-semibold text-[#202522] block">{combo.roleCoverage}</span>
                      <span className="text-[10px] text-[#777F79]">{combo.nationalityComposition}</span>
                    </div>

                    <div className="p-2.5 rounded bg-white border border-[#E5E8E3]">
                      <span className="text-[10px] font-bold uppercase text-[#777F79] block mb-1">Key Strengths</span>
                      <p className="text-[#202522] text-[11px] leading-snug">{combo.strengths}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Sub-component for candidate auction cards
const PlayerAuctionCard: React.FC<{
  player: Player;
  currentPurse: number;
  onProfile: () => void;
  onShortlist: () => void;
  onCompare: () => void;
}> = ({ player, currentPurse, onProfile, onShortlist, onCompare }) => {
  return (
    <div className="p-4 rounded-xl border border-[#E5E8E3] bg-[#F7F6F2] hover:border-gray-300 transition-all flex flex-col justify-between text-xs">
      <div>
        <div className="flex items-start justify-between">
          <div>
            <h4 onClick={onProfile} className="font-bold text-sm text-[#202522] hover:text-[#246B4B] cursor-pointer">
              {player.name}
            </h4>
            <span className="text-[11px] text-[#777F79]">{player.team} • {player.role}</span>
          </div>
          <StatusBadge status={player.internationalStatus} />
        </div>

        <div className="mt-3 p-2.5 rounded bg-white border border-[#E5E8E3] space-y-1">
          <div className="flex justify-between items-baseline">
            <span className="text-[10px] uppercase font-bold text-[#777F79]">Est. Price</span>
            <span className="font-mono font-bold text-[#202522]">
              ₹{player.auctionEstimatedMin}-{player.auctionEstimatedMax} Cr
            </span>
          </div>
          <div className="flex justify-between items-baseline">
            <span className="text-[10px] uppercase font-bold text-[#777F79]">Pressure Score</span>
            <span className="font-black text-[#246B4B]">{formatScore(player.pressureScore)}/100</span>
          </div>
          <div className="flex justify-between items-baseline">
            <span className="text-[10px] uppercase font-bold text-[#777F79]">Value Score</span>
            <span className="font-bold text-[#D97736]">{player.auctionValueScore}/100</span>
          </div>
        </div>
      </div>

      <div className="mt-3 pt-2.5 border-t border-[#E5E8E3] flex items-center justify-between">
        <button
          onClick={onCompare}
          className="p-1.5 rounded hover:bg-stone-200 text-[#777F79] cursor-pointer"
          title="Compare"
        >
          <Scale className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={onShortlist}
          className="p-1.5 rounded bg-white hover:bg-stone-200 text-[#246B4B] border border-[#E5E8E3] cursor-pointer"
          title="Shortlist"
        >
          <BookmarkPlus className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={onProfile}
          className="px-2.5 py-1 rounded bg-[#246B4B] hover:bg-[#1b533a] text-white font-semibold cursor-pointer"
        >
          Inspect
        </button>
      </div>
    </div>
  );
};

