import React, { useState, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import {
  Trophy,
  Filter,
  AlertTriangle,
  Info,
  ArrowRight,
  BookmarkPlus,
  Scale,
  Eye,
  Sliders,
  ChevronDown,
  Layers,
} from 'lucide-react';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { rankingService, RankingFilterParams, RankedPlayerItem, ExcludedPlayerItem } from '@/services/rankingService';
import { Nationality, InternationalStatus, PressureSituation } from '@/types';
import { formatPercent, formatScore } from '@/lib/utils';

export const PressureRankings: React.FC = () => {
  const { openPlayerProfile, addToComparison, addPlayerToShortlist } = useApp();

  // Category Tab
  const [category, setCategory] = useState<'Batters' | 'Bowlers'>('Batters');

  // Filters
  const [nationality, setNationality] = useState<Nationality | 'All'>('All');
  const [internationalStatus, setInternationalStatus] = useState<InternationalStatus | 'All'>('All');
  const [pressureDefinition, setPressureDefinition] = useState<
    'Standard Leverage Index' | 'Death Overs Closeness' | 'Chasing High RRR' | 'Early Wicket Collapse'
  >('Standard Leverage Index');
  const [matchSituation, setMatchSituation] = useState<PressureSituation | 'All'>('All');
  const [minSample, setMinSample] = useState<number>(100);

  // Results State
  const [rankedPlayers, setRankedPlayers] = useState<RankedPlayerItem[]>([]);
  const [excludedPlayers, setExcludedPlayers] = useState<ExcludedPlayerItem[]>([]);
  const [matchingCount, setMatchingCount] = useState<number>(0);
  const [eligibleCount, setEligibleCount] = useState<number>(0);
  const [showExcluded, setShowExcluded] = useState<boolean>(false);

  const loadRankings = async () => {
    const params: RankingFilterParams = {
      category,
      nationality,
      internationalStatus,
      pressureDefinition,
      matchSituation,
      minSample,
    };

    const res = await rankingService.getRankings(params);
    setRankedPlayers(res.rankedPlayers);
    setExcludedPlayers(res.excludedPlayers);
    setMatchingCount(res.matchingCount);
    setEligibleCount(res.eligibleCount);
  };

  useEffect(() => {
    loadRankings();
  }, [category, nationality, internationalStatus, pressureDefinition, matchSituation, minSample]);

  return (
    <div className="space-y-5">
      {/* Disclaimer Banner: Experimental Methodology Indicator */}
      <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl flex items-start space-x-3 text-xs">
        <AlertTriangle className="w-4 h-4 text-[#D97736] shrink-0 mt-0.5" />
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-amber-900 uppercase tracking-wider text-[10px] bg-amber-200/60 px-1.5 py-0.5 rounded">
              Experimental Methodology
            </span>
            <span className="text-[#D97736] font-semibold">Not approved for official franchise decision-making</span>
          </div>
          <p className="text-amber-800/80 mt-1 leading-relaxed">
            All rankings are dynamically computed from candidate ball-by-ball samples using Bayesian shrinkage.
            Adjusting filters recalculates true ranks dynamically without artificial placeholder filling.
          </p>
        </div>
      </div>

      {/* Category Tabs & Filter Header */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs space-y-4">
        {/* Category Selector */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#E5E8E3] gap-3">
          <div className="flex items-center rounded-lg bg-[#F7F6F2] p-1 border border-[#E5E8E3]">
            <button
              onClick={() => setCategory('Batters')}
              className={`px-4 py-2 rounded-md text-xs font-bold transition-all cursor-pointer ${
                category === 'Batters'
                  ? 'bg-[#246B4B] text-white shadow-xs'
                  : 'text-[#777F79] hover:text-[#202522]'
              }`}
            >
              Pressure Batters ({category === 'Batters' ? eligibleCount : '...'})
            </button>
            <button
              onClick={() => setCategory('Bowlers')}
              className={`px-4 py-2 rounded-md text-xs font-bold transition-all cursor-pointer ${
                category === 'Bowlers'
                  ? 'bg-[#246B4B] text-white shadow-xs'
                  : 'text-[#777F79] hover:text-[#202522]'
              }`}
            >
              Pressure Bowlers ({category === 'Bowlers' ? eligibleCount : '...'})
            </button>
          </div>

          <div className="text-xs text-[#777F79]">
            Active Pool: <strong className="text-[#202522]">{matchingCount}</strong> matched |{' '}
            <strong className="text-[#246B4B]">{eligibleCount} eligible & ranked</strong>
          </div>
        </div>

        {/* Dynamic Ranking Filters */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
          {/* Pressure Model Definition */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
              Leverage Model
            </label>
            <select
              value={pressureDefinition}
              onChange={e => setPressureDefinition(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] font-medium outline-none focus:border-[#246B4B]"
            >
              <option value="Standard Leverage Index">Standard Leverage Index</option>
              <option value="Death Overs Closeness">Death Overs Closeness (Overs 16-20)</option>
              <option value="Chasing High RRR">Chasing High RRR (&gt;10 RPO)</option>
              <option value="Early Wicket Collapse">Top-Order Collapse Scenario</option>
            </select>
          </div>

          {/* Nationality */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
              Nationality
            </label>
            <select
              value={nationality}
              onChange={e => setNationality(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] font-medium outline-none focus:border-[#246B4B]"
            >
              <option value="All">All Nationalities</option>
              <option value="Indian">Indian Only</option>
              <option value="Overseas">Overseas Only</option>
            </select>
          </div>

          {/* International Status */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
              Capped Status
            </label>
            <select
              value={internationalStatus}
              onChange={e => setInternationalStatus(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] font-medium outline-none focus:border-[#246B4B]"
            >
              <option value="All">All Statuses</option>
              <option value="Verified Capped">Verified Capped</option>
              <option value="Derived Capped">Derived Capped</option>
              <option value="Uncapped">Uncapped Only</option>
            </select>
          </div>

          {/* Match Situation */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
              Match Situation
            </label>
            <select
              value={matchSituation}
              onChange={e => setMatchSituation(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] font-medium outline-none focus:border-[#246B4B]"
            >
              <option value="All">All Match Contexts</option>
              <option value="Chase">Chase Phase</option>
              <option value="Defend">Defending Total</option>
              <option value="Death overs">Death Overs</option>
              <option value="High required run rate">High Required Run Rate</option>
            </select>
          </div>

          {/* Minimum Sample Threshold */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
              Min Pressure Sample
            </label>
            <select
              value={minSample}
              onChange={e => setMinSample(Number(e.target.value))}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] font-medium outline-none focus:border-[#246B4B]"
            >
              <option value={50}>≥ 50 balls (Relaxed)</option>
              <option value={100}>≥ 100 balls (Standard Gate)</option>
              <option value={200}>≥ 200 balls (High Sample)</option>
              <option value={400}>≥ 400 balls (Elite Sample)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Ranking Table */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs overflow-hidden">
        <div className="p-4 border-b border-[#E5E8E3] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Trophy className="w-4 h-4 text-[#246B4B]" />
            <h3 className="font-bold text-sm text-[#202522] tracking-tight">
              Calibrated {category} Pressure Hierarchy ({rankedPlayers.length} Qualifiers)
            </h3>
          </div>
          <span className="text-[11px] text-[#777F79]">
            Rank recalculated dynamically • Zero placeholder padding
          </span>
        </div>

        {rankedPlayers.length === 0 ? (
          <div className="p-12 text-center text-xs text-[#777F79]">
            No players qualified under the strict minimum sample ({minSample} balls) and filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F7F6F2] border-b border-[#E5E8E3] text-[#777F79] uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="p-3 w-12 text-center">Rank</th>
                  <th className="p-3">Player</th>
                  <th className="p-3">Role & Speciality</th>
                  <th className="p-3">Nationality</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Pressure Score</th>
                  <th className="p-3 text-right">Baseline</th>
                  <th className="p-3 text-right">Adjusted Uplift</th>
                  <th className="p-3 text-right">Opportunities</th>
                  <th className="p-3">Reliability</th>
                  <th className="p-3">Uncertainty</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E8E3]">
                {rankedPlayers.map(item => (
                  <tr key={item.player.id} className="hover:bg-[#F7F6F2]/70 transition-colors">
                    <td className="p-3 text-center">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs ${
                        item.rank === 1
                          ? 'bg-amber-400 text-stone-900 shadow-xs'
                          : item.rank === 2
                          ? 'bg-stone-300 text-stone-900'
                          : item.rank === 3
                          ? 'bg-amber-700/70 text-white'
                          : 'bg-[#F7F6F2] text-[#202522] border border-[#E5E8E3]'
                      }`}>
                        {item.rank}
                      </span>
                    </td>
                    <td className="p-3">
                      <div
                        onClick={() => openPlayerProfile(item.player)}
                        className="font-bold text-[#202522] hover:text-[#246B4B] cursor-pointer"
                      >
                        {item.player.name}
                      </div>
                      <span className="text-[10px] text-[#777F79]">{item.player.team}</span>
                    </td>
                    <td className="p-3">
                      <span className="font-semibold text-[#202522]">{item.player.role}</span>
                      <span className="text-[10px] text-[#777F79] block">{item.player.speciality}</span>
                    </td>
                    <td className="p-3 text-[#202522]">{item.player.nationality}</td>
                    <td className="p-3">
                      <StatusBadge status={item.player.internationalStatus} />
                    </td>
                    <td className="p-3 text-right font-mono">
                      <span className="font-black text-sm text-[#246B4B]">
                        {formatScore(item.pressureScore)}
                      </span>
                    </td>
                    <td className="p-3 text-right font-mono text-[#777F79]">
                      {formatScore(item.baselineScore)}
                    </td>
                    <td className="p-3 text-right font-mono font-bold text-[#27845B]">
                      {formatPercent(item.adjustedPerformance)}
                    </td>
                    <td className="p-3 text-right font-mono text-[#202522]">
                      {item.opportunities} <span className="text-[10px] text-[#777F79]">balls</span>
                    </td>
                    <td className="p-3">
                      <StatusBadge status={item.reliability} />
                    </td>
                    <td className="p-3 font-mono text-[11px] text-[#777F79]">
                      {item.uncertainty}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end space-x-1">
                        <button
                          onClick={() => addToComparison(item.player.id)}
                          title="Compare"
                          className="p-1 rounded hover:bg-stone-200 text-[#777F79] hover:text-[#202522] cursor-pointer"
                        >
                          <Scale className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => addPlayerToShortlist(item.player)}
                          title="Shortlist"
                          className="p-1 rounded hover:bg-stone-200 text-[#777F79] hover:text-[#246B4B] cursor-pointer"
                        >
                          <BookmarkPlus className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => openPlayerProfile(item.player)}
                          title="Inspect Profile"
                          className="p-1 rounded bg-[#F7F6F2] hover:bg-stone-200 text-[#246B4B] cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Excluded Players Audit Accordion */}
      {excludedPlayers.length > 0 && (
        <div className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs">
          <div
            className="flex items-center justify-between cursor-pointer select-none"
            onClick={() => setShowExcluded(prev => !prev)}
          >
            <div className="flex items-center space-x-2">
              <Info className="w-4 h-4 text-[#777F79]" />
              <h4 className="text-xs font-bold text-[#202522]">
                Excluded Candidates Audit ({excludedPlayers.length} players excluded by active filters)
              </h4>
            </div>
            <button className="text-xs text-[#246B4B] font-semibold flex items-center space-x-1 cursor-pointer">
              <span>{showExcluded ? 'Hide Excluded' : 'View Audit Log'}</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showExcluded ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {showExcluded && (
            <div className="mt-3 pt-3 border-t border-[#E5E8E3] space-y-2">
              <p className="text-[11px] text-[#777F79]">
                These candidates were eliminated by the criteria specified above:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {excludedPlayers.map((item, idx) => (
                  <div key={idx} className="p-2.5 rounded bg-[#F7F6F2] border border-[#E5E8E3] text-xs">
                    <div className="flex justify-between font-bold text-[#202522]">
                      <span>{item.player.name}</span>
                      <span className="text-[10px] text-[#777F79]">{item.player.role}</span>
                    </div>
                    <p className="text-[11px] text-[#C44747] mt-1 font-medium">
                      Excluded: {item.reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

