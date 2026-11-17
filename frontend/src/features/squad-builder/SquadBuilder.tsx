import React, { useState, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import {
  ShieldCheck,
  Users,
  AlertTriangle,
  AlertCircle,
  Plus,
  Trash2,
  BookmarkPlus,
  Scale,
  Eye,
  SlidersHorizontal,
  Coins,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { squadService, SquadEvaluation, DEFAULT_SQUAD_RULES } from '@/services/squadService';
import { SquadBalanceChart } from '@/components/charts/SquadBalanceChart';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { Player, SquadSlotRule } from '@/types';
import { formatCrore, formatScore } from '@/lib/utils';

export const SquadBuilder: React.FC = () => {
  const { openPlayerProfile, addToComparison, addToast } = useApp();

  const [squad, setSquad] = useState<Player[]>([]);
  const [evaluation, setEvaluation] = useState<SquadEvaluation | null>(null);
  const [rules, setRules] = useState<SquadSlotRule>(DEFAULT_SQUAD_RULES);
  const [isRulesModalOpen, setIsRulesModalOpen] = useState<boolean>(false);
  const [addPlayerDrawerOpen, setAddPlayerDrawerOpen] = useState<boolean>(false);

  const loadSquad = async () => {
    const list = await squadService.getSelectedSquad();
    setSquad(list);
    const evalResult = squadService.evaluateSquad(list, rules);
    setEvaluation(evalResult);
  };

  useEffect(() => {
    loadSquad();
  }, [rules]);

  const handleRemove = async (id: string, name: string) => {
    const updated = await squadService.removePlayerFromSquad(id);
    setSquad(updated);
    setEvaluation(squadService.evaluateSquad(updated, rules));
    addToast(`${name} removed from squad`, 'info');
  };

  const handleAdd = async (player: Player) => {
    if (squad.some(p => p.id === player.id)) {
      addToast('Player is already in squad', 'info');
      return;
    }
    if (squad.length >= rules.maxSquadSize) {
      addToast(`Squad roster limit reached (max ${rules.maxSquadSize})`, 'warning');
      return;
    }
    const updated = await squadService.addPlayerToSquad(player.id);
    setSquad(updated);
    setEvaluation(squadService.evaluateSquad(updated, rules));
    addToast(`${player.name} added to squad`, 'success');
  };

  const availableToAdd = MOCK_PLAYERS.filter(p => !squad.some(s => s.id === p.id));

  return (
    <div className="space-y-6">
      {/* Top Header & Slot Summary */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#E5E8E3] gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold uppercase tracking-wider bg-[#246B4B] text-white px-2 py-0.5 rounded">
                Tactical Architect
              </span>
              <span className="text-xs text-[#777F79]">Rajasthan Royals Squad Construction</span>
            </div>
            <h2 className="text-lg font-bold text-[#202522] tracking-tight mt-1">
              Hypothetical Squad Builder & Balance Matrix
            </h2>
            <p className="text-xs text-[#777F79] mt-0.5">
              Build a 25-player roster and evaluate phase balance, death-overs resilience and budget caps.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setAddPlayerDrawerOpen(prev => !prev)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#246B4B] text-white text-xs font-semibold hover:bg-[#1b533a] cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Player</span>
            </button>

            <button
              onClick={() => setIsRulesModalOpen(prev => !prev)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#F7F6F2] hover:bg-stone-200 border border-[#E5E8E3] text-xs font-semibold text-[#202522] cursor-pointer"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-[#777F79]" />
              <span>Squad Rules</span>
            </button>
          </div>
        </div>

        {/* Quick Slot Counts Bar */}
        {evaluation && (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 mt-4 text-xs">
            <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3]">
              <span className="text-[10px] text-[#777F79] uppercase block font-semibold">Roster Slots</span>
              <strong className="text-lg text-[#202522] block font-mono">{evaluation.totalPlayers} / {rules.maxSquadSize}</strong>
              <span className="text-[10px] text-[#777F79]">{rules.maxSquadSize - evaluation.totalPlayers} spots open</span>
            </div>

            <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3]">
              <span className="text-[10px] text-[#777F79] uppercase block font-semibold">Overseas Limit</span>
              <strong className="text-lg text-[#202522] block font-mono">{evaluation.overseasCount} / {rules.maxOverseas}</strong>
              <span className="text-[10px] text-[#777F79]">Max 8 allowed</span>
            </div>

            <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3]">
              <span className="text-[10px] text-[#777F79] uppercase block font-semibold">Indian Players</span>
              <strong className="text-lg text-[#246B4B] block font-mono">{evaluation.indianCount}</strong>
              <span className="text-[10px] text-[#777F79]">Min {rules.minIndian} required</span>
            </div>

            <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3]">
              <span className="text-[10px] text-[#777F79] uppercase block font-semibold">Capped / Uncapped</span>
              <strong className="text-lg text-[#202522] block font-mono">{evaluation.cappedCount} / {evaluation.uncappedCount}</strong>
              <span className="text-[10px] text-[#777F79]">{evaluation.unknownStatusCount} unknown</span>
            </div>

            <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3]">
              <span className="text-[10px] text-[#777F79] uppercase block font-semibold">Role Split</span>
              <span className="font-semibold text-xs text-[#202522] block mt-1">
                {evaluation.batterCount}B • {evaluation.bowlerCount}P • {evaluation.allRounderCount}A • {evaluation.keeperCount}W
              </span>
            </div>

            <div className="p-3 bg-[#FDF3EB] rounded-lg border border-[#F8DCC9]">
              <span className="text-[10px] text-[#D97736] uppercase block font-semibold">Est. Purse Spent</span>
              <strong className="text-lg text-[#D97736] block font-mono">₹{evaluation.totalEstimatedCostMax} Cr</strong>
              <span className="text-[10px] text-[#777F79]">Remaining: ₹{evaluation.remainingBudget} Cr</span>
            </div>
          </div>
        )}

        {/* Drawer: Add Player to Squad */}
        {addPlayerDrawerOpen && (
          <div className="mt-4 pt-3 border-t border-[#E5E8E3] bg-[#F7F6F2] p-3 rounded-lg text-xs">
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-[#202522]">Select Candidate to Add to Hypothetical Squad</span>
              <button
                onClick={() => setAddPlayerDrawerOpen(false)}
                className="text-[#777F79] hover:text-[#202522] font-semibold cursor-pointer"
              >
                Close
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 max-h-52 overflow-y-auto">
              {availableToAdd.map(p => (
                <div
                  key={p.id}
                  className="p-2.5 rounded bg-white border border-[#E5E8E3] flex justify-between items-center"
                >
                  <div className="min-w-0 pr-1">
                    <span className="font-bold text-[#202522] block truncate">{p.name}</span>
                    <span className="text-[10px] text-[#777F79]">{p.role} • {p.team}</span>
                  </div>
                  <button
                    onClick={() => handleAdd(p)}
                    className="p-1 rounded bg-[#246B4B] text-white hover:bg-[#1b533a] cursor-pointer"
                    title="Add to Squad"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Warnings & Composition Alerts */}
      {evaluation && evaluation.warnings.length > 0 && (
        <div className="space-y-2">
          {evaluation.warnings.map(w => (
            <div
              key={w.id}
              className={`p-3 rounded-lg border text-xs flex items-center space-x-2.5 ${
                w.level === 'error'
                  ? 'bg-rose-50 text-[#C44747] border-rose-200'
                  : w.level === 'warning'
                  ? 'bg-amber-50 text-amber-900 border-amber-200'
                  : 'bg-blue-50 text-blue-800 border-blue-200'
              }`}
            >
              {w.level === 'error' ? (
                <AlertCircle className="w-4 h-4 shrink-0 text-[#C44747]" />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0 text-[#D97736]" />
              )}
              <span className="font-medium">{w.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* Main Grid: Squad Balance Radar & Selected Roster Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Squad Balance Radar Chart (5 Cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#E5E8E3]">
              <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider">
                Squad Phase Coverage Radar
              </h4>
              <span className="text-[10px] text-[#D97736] font-semibold bg-[#FDF3EB] px-2 py-0.5 rounded border border-[#F8DCC9]">
                0-100 Rating
              </span>
            </div>

            {evaluation && (
              <div className="mt-3">
                <SquadBalanceChart evaluation={evaluation} />
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-[#E5E8E3] text-xs text-[#777F79] space-y-1">
            <p><strong>Evaluation Framework:</strong> Considers death bowling (16-20), batting strike-power down to #7, and early wicket security.</p>
          </div>
        </div>

        {/* Selected Roster Table (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#E5E8E3]">
            <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider">
              Selected Squad Roster ({squad.length} Players)
            </h4>
            <span className="text-[11px] text-[#777F79]">Click player to inspect full profile</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F7F6F2] border-b border-[#E5E8E3] text-[#777F79] uppercase font-bold text-[10px]">
                <tr>
                  <th className="p-2 w-8 text-center">#</th>
                  <th className="p-2">Player</th>
                  <th className="p-2">Role</th>
                  <th className="p-2">Nationality</th>
                  <th className="p-2">Status</th>
                  <th className="p-2 text-right">Pressure</th>
                  <th className="p-2 text-right">Est. Price</th>
                  <th className="p-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E8E3]">
                {squad.map((p, idx) => (
                  <tr key={p.id} className="hover:bg-[#F7F6F2]/60 transition-colors">
                    <td className="p-2 text-center font-mono font-bold text-[#777F79]">{idx + 1}</td>
                    <td className="p-2">
                      <span
                        onClick={() => openPlayerProfile(p)}
                        className="font-bold text-[#202522] hover:text-[#246B4B] cursor-pointer"
                      >
                        {p.name}
                      </span>
                      <span className="text-[10px] text-[#777F79] block">{p.team}</span>
                    </td>
                    <td className="p-2">
                      <span className="font-semibold text-[#202522]">{p.role}</span>
                      <span className="text-[10px] text-[#777F79] block">{p.speciality}</span>
                    </td>
                    <td className="p-2 text-[#202522]">{p.nationality}</td>
                    <td className="p-2">
                      <StatusBadge status={p.internationalStatus} />
                    </td>
                    <td className="p-2 text-right font-mono font-bold text-[#246B4B]">
                      {formatScore(p.pressureScore)}
                    </td>
                    <td className="p-2 text-right font-mono text-[#202522]">
                      ₹{p.auctionEstimatedMax ?? 2} Cr
                    </td>
                    <td className="p-2 text-right">
                      <button
                        onClick={() => handleRemove(p.id, p.name)}
                        className="p-1 rounded hover:bg-rose-100 text-[#777F79] hover:text-[#C44747] transition-colors cursor-pointer"
                        title="Remove from squad"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

