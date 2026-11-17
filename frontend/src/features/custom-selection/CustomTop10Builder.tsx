import React, { useState, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import {
  Sliders,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Save,
  Download,
  Scale,
  BookmarkPlus,
  RotateCcw,
  Info,
  Check,
  ChevronDown,
} from 'lucide-react';
import { CustomConstraints, ConstraintReport, Player } from '@/types';
import { MOCK_PRESETS, PresetConfig } from '@/data/mock/presets';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PlayerRadarChart } from '@/components/charts/PlayerRadarChart';
import { exportToCSV, formatScore } from '@/lib/utils';
import { shortlistService } from '@/services/shortlistService';

export const CustomTop10Builder: React.FC = () => {
  const { openPlayerProfile, addToComparison, addPlayerToShortlist, addToast } = useApp();

  const [activePresetId, setActivePresetId] = useState<string>('preset-1');
  const [rankingTitle, setRankingTitle] = useState<string>('Best Indian Uncapped XI');

  // Independent Constraint Controls
  const [nationality, setNationality] = useState<'Indian only' | 'Overseas only' | 'Mixed' | 'No restriction'>('Indian only');
  const [internationalStatus, setInternationalStatus] = useState<'Capped only' | 'Uncapped only' | 'Mixed' | 'No restriction'>('Uncapped only');
  const [role, setRole] = useState<'Batter' | 'Bowler' | 'All-rounder' | 'Wicketkeeper' | 'Any role'>('Any role');
  const [selectionCount, setSelectionCount] = useState<number>(10);
  const [isStrictMode, setIsStrictMode] = useState<boolean>(false);

  // Advanced numeric constraints
  const [minIndian, setMinIndian] = useState<number | undefined>(undefined);
  const [maxOverseas, setMaxOverseas] = useState<number | undefined>(undefined);
  const [minCapped, setMinCapped] = useState<number | undefined>(undefined);
  const [minUncapped, setMinUncapped] = useState<number | undefined>(undefined);
  const [minBatters, setMinBatters] = useState<number | undefined>(undefined);
  const [minBowlers, setMinBowlers] = useState<number | undefined>(undefined);

  // Selected Result & Report
  const [selectedPlayers, setSelectedPlayers] = useState<Player[]>([]);
  const [constraintReport, setConstraintReport] = useState<ConstraintReport>({
    satisfied: true,
    messages: [],
    unmetCount: 0,
  });

  // Apply Preset
  const handleApplyPreset = (preset: PresetConfig) => {
    setActivePresetId(preset.id);
    setRankingTitle(preset.name);
    setNationality(preset.constraints.nationality);
    setInternationalStatus(preset.constraints.internationalStatus);
    setRole(preset.constraints.role);
    setSelectionCount(preset.constraints.selectionCount);
    setIsStrictMode(preset.constraints.isStrictMode);
    setMinIndian(preset.constraints.minIndian);
    setMaxOverseas(preset.constraints.maxOverseas);
    setMinCapped(preset.constraints.minCapped);
    setMinUncapped(preset.constraints.minUncapped);
    setMinBatters(preset.constraints.minBatters);
    setMinBowlers(preset.constraints.minBowlers);
    addToast(`Preset applied: ${preset.name}`, 'info');
  };

  // Constraint Solver
  const solveComposition = () => {
    const reportMessages: ConstraintReport['messages'] = [];
    let unmetCount = 0;

    // Filter candidate pool
    let pool = [...MOCK_PLAYERS].filter(p => p.eligibility === 'Eligible' && p.pressureScore !== null);

    // Apply primary constraints
    if (nationality === 'Indian only') {
      pool = pool.filter(p => p.nationality === 'Indian');
    } else if (nationality === 'Overseas only') {
      pool = pool.filter(p => p.nationality === 'Overseas');
    }

    if (internationalStatus === 'Capped only') {
      pool = pool.filter(p => p.internationalStatus === 'Verified Capped' || p.internationalStatus === 'Derived Capped');
    } else if (internationalStatus === 'Uncapped only') {
      pool = pool.filter(p => p.internationalStatus === 'Uncapped');
    }

    if (role !== 'Any role') {
      pool = pool.filter(p => p.role === role);
    }

    // Sort pool by pressure score
    pool.sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0));

    // Selection
    let chosen: Player[] = [];

    if (isStrictMode) {
      // In strict mode, take directly up to count
      chosen = pool.slice(0, selectionCount);

      if (chosen.length < selectionCount) {
        unmetCount++;
        reportMessages.push({
          rule: `Requested ${selectionCount} players`,
          status: 'failed',
          detail: `Only ${chosen.length} players satisfied all strict criteria simultaneously. No relaxations applied.`,
        });
      } else {
        reportMessages.push({
          rule: `Target Selection Count (${selectionCount})`,
          status: 'passed',
          detail: `Exactly ${chosen.length} players matched all strict constraints.`,
        });
      }

      if (minIndian !== undefined) {
        const indCount = chosen.filter(p => p.nationality === 'Indian').length;
        if (indCount < minIndian) {
          unmetCount++;
          reportMessages.push({
            rule: `Minimum Indian Players (≥${minIndian})`,
            status: 'failed',
            detail: `Found only ${indCount} Indian players in strict pool.`,
          });
        } else {
          reportMessages.push({
            rule: `Minimum Indian Players (≥${minIndian})`,
            status: 'passed',
            detail: `Satisfied: ${indCount} Indian players selected.`,
          });
        }
      }
    } else {
      // In flexible mode, try to satisfy count and explain compromises
      chosen = pool.slice(0, selectionCount);

      if (chosen.length < selectionCount) {
        // Backfill from general pool with clear warning
        const remainingNeeded = selectionCount - chosen.length;
        const fallbackPool = MOCK_PLAYERS
          .filter(p => !chosen.some(c => c.id === p.id) && p.pressureScore !== null)
          .sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0))
          .slice(0, remainingNeeded);

        chosen = [...chosen, ...fallbackPool];
        unmetCount++;
        reportMessages.push({
          rule: 'Target Count Fill (Flexible Compromise)',
          status: 'warning',
          detail: `Original filter provided ${pool.length} candidates. Added ${fallbackPool.length} closest-fit players to meet target of ${selectionCount}.`,
        });
      } else {
        reportMessages.push({
          rule: `Target Selection Count (${selectionCount})`,
          status: 'passed',
          detail: `Complete roster of ${chosen.length} players populated.`,
        });
      }
    }

    setSelectedPlayers(chosen);
    setConstraintReport({
      satisfied: unmetCount === 0,
      messages: reportMessages,
      unmetCount,
    });
  };

  useEffect(() => {
    solveComposition();
  }, [
    nationality,
    internationalStatus,
    role,
    selectionCount,
    isStrictMode,
    minIndian,
    maxOverseas,
    minCapped,
    minUncapped,
    minBatters,
    minBowlers,
  ]);

  const handleSaveRanking = async () => {
    const ids = selectedPlayers.map(p => p.id);
    await shortlistService.addCustomRanking(
      rankingTitle,
      ids,
      `Configured with ${isStrictMode ? 'Strict' : 'Flexible'} solver. Count: ${selectedPlayers.length}`
    );
    addToast(`Saved ranking: "${rankingTitle}" to shortlists`, 'success');
  };

  const handleExportCSV = () => {
    const headers = ['Rank', 'Player Name', 'Team', 'Role', 'Nationality', 'International Status', 'Pressure Score', 'Sample Size'];
    const rows = selectedPlayers.map((p, idx) => [
      idx + 1,
      p.name,
      p.team,
      p.role,
      p.nationality,
      p.internationalStatus,
      p.pressureScore ?? 'N/A',
      p.sampleSize,
    ]);
    exportToCSV(`custom_top10_${rankingTitle.replace(/\s+/g, '_').toLowerCase()}`, headers, rows);
    addToast('Exported ranking to CSV', 'success');
  };

  return (
    <div className="space-y-5">
      {/* Top Presets Ribbon */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-[#E5E8E3]">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-[#D97736]" />
            <h3 className="text-xs font-bold text-[#202522] uppercase tracking-wider">
              Recruitment Presets (10 Independent Configurations)
            </h3>
          </div>
          <span className="text-[11px] text-[#777F79]">Presets populate filters, not fixed rankings</span>
        </div>

        <div className="flex items-center space-x-2 overflow-x-auto pt-3 pb-1">
          {MOCK_PRESETS.map(preset => (
            <button
              key={preset.id}
              onClick={() => handleApplyPreset(preset)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all border cursor-pointer ${
                activePresetId === preset.id
                  ? 'bg-[#246B4B] text-white border-[#246B4B] shadow-xs'
                  : 'bg-[#F7F6F2] hover:bg-stone-200 text-[#202522] border-[#E5E8E3]'
              }`}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Constraints Configurator & Solver */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Configuration Form (5 Cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#E5E8E3]">
            <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider flex items-center space-x-1.5">
              <Sliders className="w-4 h-4 text-[#246B4B]" />
              <span>Composition Settings</span>
            </h4>
            <div className="flex items-center space-x-1.5">
              <span className="text-[10px] text-[#777F79] font-medium">Solver:</span>
              <button
                onClick={() => setIsStrictMode(prev => !prev)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold border transition-colors cursor-pointer ${
                  isStrictMode
                    ? 'bg-rose-100 text-[#C44747] border-rose-300'
                    : 'bg-[#EBF7F1] text-[#246B4B] border-[#C3E6D6]'
                }`}
              >
                {isStrictMode ? 'Strict Mode' : 'Flexible Mode'}
              </button>
            </div>
          </div>

          <div className="space-y-3 text-xs">
            {/* Title */}
            <div>
              <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Ranking Title</label>
              <input
                type="text"
                value={rankingTitle}
                onChange={e => setRankingTitle(e.target.value)}
                className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] font-semibold outline-none focus:border-[#246B4B]"
              />
            </div>

            {/* Nationality */}
            <div>
              <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Nationality Restriction</label>
              <select
                value={nationality}
                onChange={e => setNationality(e.target.value as any)}
                className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] outline-none"
              >
                <option value="Indian only">Indian only</option>
                <option value="Overseas only">Overseas only</option>
                <option value="Mixed">Mixed</option>
                <option value="No restriction">No restriction</option>
              </select>
            </div>

            {/* International Status */}
            <div>
              <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Capped / Uncapped Status</label>
              <select
                value={internationalStatus}
                onChange={e => setInternationalStatus(e.target.value as any)}
                className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] outline-none"
              >
                <option value="Uncapped only">Uncapped only</option>
                <option value="Capped only">Capped only</option>
                <option value="Mixed">Mixed</option>
                <option value="No restriction">No restriction</option>
              </select>
            </div>

            {/* Role */}
            <div>
              <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Role Constraint</label>
              <select
                value={role}
                onChange={e => setRole(e.target.value as any)}
                className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2.5 py-1.5 text-xs text-[#202522] outline-none"
              >
                <option value="Any role">Any role</option>
                <option value="Batter">Batter Only</option>
                <option value="Bowler">Bowler Only</option>
                <option value="All-rounder">All-rounder Only</option>
                <option value="Wicketkeeper">Wicketkeeper Only</option>
              </select>
            </div>

            {/* Selection Count */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-[10px] font-bold text-[#777F79] uppercase">Target Count</label>
                <span className="font-bold text-[#202522] font-mono">{selectionCount} Players</span>
              </div>
              <input
                type="range"
                min={3}
                max={15}
                value={selectionCount}
                onChange={e => setSelectionCount(Number(e.target.value))}
                className="w-full accent-[#246B4B] cursor-pointer"
              />
            </div>
          </div>

          {/* Solver Explanation */}
          <div className="p-3 bg-[#F7F6F2] border border-[#E5E8E3] rounded-lg text-[11px] text-[#777F79] space-y-1">
            <span className="font-bold text-[#202522] block">Mode Specification:</span>
            {isStrictMode ? (
              <p className="text-[#C44747]">
                <strong>Strict Mode:</strong> Will strictly reject any player not meeting 100% of the constraints. If fewer qualify, list will display only those who pass.
              </p>
            ) : (
              <p className="text-[#246B4B]">
                <strong>Flexible Mode:</strong> Will attempt to fill the target count with closest statistical equivalents while transparently logging compromises.
              </p>
            )}
          </div>
        </div>

        {/* Right: Generated Ranking & Satisfaction Report (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#E5E8E3]">
              <div>
                <h3 className="font-bold text-sm text-[#202522] tracking-tight">{rankingTitle}</h3>
                <span className="text-[11px] text-[#777F79]">
                  {selectedPlayers.length} players selected • {constraintReport.satisfied ? 'All constraints passed' : 'Compromises active'}
                </span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={handleSaveRanking}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#246B4B] hover:bg-[#1b533a] text-white text-xs font-semibold transition-colors cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save</span>
                </button>
                <button
                  onClick={handleExportCSV}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#F7F6F2] hover:bg-stone-200 border border-[#E5E8E3] text-[#202522] text-xs font-semibold transition-colors cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5 text-[#246B4B]" />
                  <span>CSV</span>
                </button>
              </div>
            </div>

            {/* Constraint Report Messages */}
            <div className="my-3 space-y-1.5">
              {constraintReport.messages.map((m, i) => (
                <div
                  key={i}
                  className={`p-2 rounded text-xs flex items-start space-x-2 border ${
                    m.status === 'passed'
                      ? 'bg-[#EBF7F1]/60 text-[#246B4B] border-[#C3E6D6]'
                      : m.status === 'warning'
                      ? 'bg-[#FDF3EB] text-[#D97736] border-[#F8DCC9]'
                      : 'bg-rose-50 text-[#C44747] border-rose-200'
                  }`}
                >
                  {m.status === 'passed' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  ) : m.status === 'warning' ? (
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <strong className="block">{m.rule}</strong>
                    <span className="text-[11px] leading-snug">{m.detail}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Selected Roster Table */}
            <div className="overflow-x-auto mt-3">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F7F6F2] border-b border-[#E5E8E3] text-[#777F79] uppercase font-bold text-[10px]">
                  <tr>
                    <th className="p-2 w-8 text-center">#</th>
                    <th className="p-2">Player</th>
                    <th className="p-2">Role</th>
                    <th className="p-2">Nationality</th>
                    <th className="p-2">Status</th>
                    <th className="p-2 text-right">Pressure Score</th>
                    <th className="p-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E8E3]">
                  {selectedPlayers.map((p, idx) => (
                    <tr key={p.id} className="hover:bg-[#F7F6F2]/60">
                      <td className="p-2 text-center font-bold font-mono text-[#777F79]">{idx + 1}</td>
                      <td className="p-2 font-bold text-[#202522]">
                        <span onClick={() => openPlayerProfile(p)} className="hover:text-[#246B4B] cursor-pointer">
                          {p.name}
                        </span>
                        <span className="text-[10px] text-[#777F79] font-normal block">{p.team}</span>
                      </td>
                      <td className="p-2 text-[#777F79]">{p.role}</td>
                      <td className="p-2">{p.nationality}</td>
                      <td className="p-2">
                        <StatusBadge status={p.internationalStatus} />
                      </td>
                      <td className="p-2 text-right font-mono font-bold text-[#246B4B]">
                        {formatScore(p.pressureScore)}
                      </td>
                      <td className="p-2 text-right">
                        <div className="flex items-center justify-end space-x-1">
                          <button
                            onClick={() => addToComparison(p.id)}
                            title="Compare"
                            className="p-1 rounded hover:bg-stone-200 text-[#777F79] cursor-pointer"
                          >
                            <Scale className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => addPlayerToShortlist(p)}
                            title="Shortlist"
                            className="p-1 rounded hover:bg-stone-200 text-[#246B4B] cursor-pointer"
                          >
                            <BookmarkPlus className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

