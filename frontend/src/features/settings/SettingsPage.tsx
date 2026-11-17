import React from 'react';
import { useApp } from '@/context/AppContext';
import {
  Settings,
  RotateCcw,
  Sparkles,
  Database,
  Layers,
  Shield,
  Sliders,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { storageAdapter } from '@/lib/storage';

export const SettingsPage: React.FC = () => {
  const {
    selectedSeason,
    setSelectedSeason,
    hypotheticalPurseCr,
    setHypotheticalPurseCr,
    lastYearSuggestionActive,
    setLastYearSuggestionActive,
    refreshShortlistCount,
    refreshSquadCount,
    addToast,
  } = useApp();

  const handleResetData = () => {
    localStorage.clear();
    setHypotheticalPurseCr(15.0);
    setLastYearSuggestionActive(false);
    setSelectedSeason('IPL 2026');
    refreshShortlistCount();
    refreshSquadCount();
    addToast('Demonstration state and shortlists reset to factory defaults', 'success');
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs">
        <div className="flex items-center space-x-2">
          <Settings className="w-4 h-4 text-[#246B4B]" />
          <h2 className="text-lg font-bold text-[#202522] tracking-tight">Terminal Configuration & Demonstration Settings</h2>
        </div>
        <p className="text-xs text-[#777F79] mt-0.5">
          Configure active tournament season, scouting purse parameters, and local persistence adapter.
        </p>
      </div>

      {/* Settings Sections */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-5">
        <h3 className="text-xs font-bold text-[#202522] uppercase tracking-wider pb-2 border-b border-[#E5E8E3]">
          Scouting & Tournament Parameters
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
              Active Evaluation Season
            </label>
            <select
              value={selectedSeason}
              onChange={e => {
                setSelectedSeason(e.target.value);
                addToast(`Switched active season to ${e.target.value}`, 'info');
              }}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-lg px-3 py-2 text-xs font-semibold text-[#202522] outline-none focus:border-[#246B4B]"
            >
              <option value="IPL 2026">IPL 2026 (Current Season)</option>
              <option value="IPL 2025">IPL 2025</option>
              <option value="IPL 2024">IPL 2024</option>
              <option value="IPL 2023">IPL 2023</option>
            </select>
            <span className="text-[10px] text-[#777F79] mt-1 block">Controls active squad pool and tournament context.</span>
          </div>

          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">
              Default Hypothetical Purse (₹ Cr)
            </label>
            <input
              type="number"
              min="0"
              max="35"
              step="0.5"
              value={hypotheticalPurseCr}
              onChange={e => setHypotheticalPurseCr(parseFloat(e.target.value) || 0)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-lg px-3 py-2 text-xs font-semibold text-[#202522] font-mono outline-none focus:border-[#246B4B]"
            />
            <span className="text-[10px] text-[#777F79] mt-1 block">Baseline purse budget used across Auction Intelligence modules.</span>
          </div>
        </div>

        {/* Future Backend Integration Readiness */}
        <div className="pt-4 border-t border-[#E5E8E3] space-y-2">
          <h4 className="text-xs font-bold text-[#202522] uppercase tracking-wider flex items-center space-x-1.5">
            <Database className="w-4 h-4 text-[#246B4B]" />
            <span>Future Backend Integration Interface</span>
          </h4>
          <p className="text-xs text-[#777F79] leading-relaxed">
            All UI components communicate exclusively via typed frontend services (<code>playerService</code>, <code>rankingService</code>, <code>comparisonService</code>, <code>historicalNeedsService</code>, <code>auctionService</code>, <code>squadService</code>, <code>shortlistService</code>).
            When the backend API is deployed, mock implementations can be swapped without restructuring any page components.
          </p>

          <div className="p-3 bg-[#F7F6F2] rounded-lg border border-[#E5E8E3] text-xs font-mono text-[#777F79]">
            Current Service Adapter: <span className="text-[#246B4B] font-bold">MOCK_DATA_LAYER_V1 (Client-side)</span>
          </div>
        </div>

        {/* Reset State */}
        <div className="pt-4 border-t border-[#E5E8E3] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h4 className="text-xs font-bold text-[#202522]">Reset Demonstration State</h4>
            <p className="text-xs text-[#777F79]">Clears locally persisted shortlists, custom rankings and restored factory data.</p>
          </div>

          <button
            onClick={handleResetData}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-rose-50 hover:bg-rose-100 text-[#C44747] border border-rose-200 text-xs font-bold transition-colors cursor-pointer self-start sm:self-auto"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Demo State</span>
          </button>
        </div>
      </div>
    </div>
  );
};

