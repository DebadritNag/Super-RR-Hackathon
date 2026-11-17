import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import {
  Menu,
  Search,
  Sparkles,
  Trophy,
  Target,
  AlertTriangle,
  X,
  FileSpreadsheet,
} from 'lucide-react';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { Player } from '@/types';

export const Topbar: React.FC = () => {
  const {
    activeSection,
    globalSearch,
    setGlobalSearch,
    openPlayerProfile,
    setIsMobileDrawerOpen,
    exportRankingsCSV,
  } = useApp();

  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const searchResults = globalSearch.trim().length > 1
    ? MOCK_PLAYERS.filter(p =>
        p.name.toLowerCase().includes(globalSearch.toLowerCase()) ||
        p.team.toLowerCase().includes(globalSearch.toLowerCase()) ||
        p.role.toLowerCase().includes(globalSearch.toLowerCase()) ||
        p.id.toLowerCase().includes(globalSearch.toLowerCase())
      ).slice(0, 6)
    : [];

  const handleSelectSearchResult = (p: Player) => {
    openPlayerProfile(p);
    setGlobalSearch('');
    setIsSearchOpen(false);
  };

  const getPageTitle = () => {
    switch (activeSection) {
      case 'overview':
        return { 
          title: 'Pressure Performance Intelligence', 
          subtitle: 'Identifying players who perform when the match situation demands the most' 
        };
      case 'pressure-batters':
        return { 
          title: 'Top 10 Pressure Batters', 
          subtitle: 'Context-adjusted run scoring, strike rate uplift & boundary conversion' 
        };
      case 'pressure-bowlers':
        return { 
          title: 'Top 10 Pressure Bowlers', 
          subtitle: 'Negated residual run suppression, death-overs containment & clutch wickets' 
        };
      case 'player-comparison':
        return { 
          title: 'Head-to-Head Player Comparison', 
          subtitle: 'Multi-dimensional overlaid spider charts and differential advantage analysis' 
        };
      case 'selection-reasons':
        return { 
          title: 'Why Selected / Why Not Selected', 
          subtitle: 'Transparent competition audit: mathematical qualifications vs explicit gate failures' 
        };
      case 'methodology':
        return { 
          title: 'Data Sources & 9-Step Methodology', 
          subtitle: 'Ball-by-ball leverage indexing, Bayesian shrinkage & Phase 4 test disclosure' 
        };
      case 'rr-analysis':
        return { 
          title: 'Rajasthan Royals Historical Analysis', 
          subtitle: '2025 & 2026 tactical debrief, middle-overs spin vulnerability & recruitment blueprint' 
        };
      default:
        return { 
          title: 'Pressure Performance Intelligence', 
          subtitle: 'Rajasthan Royals Player Intelligence & Selection Platform' 
        };
    }
  };

  const { title, subtitle } = getPageTitle();

  return (
    <header className="h-16 bg-white border-b border-[#E5E8E3] px-4 sm:px-6 lg:px-8 flex items-center justify-between sticky top-0 z-20 shadow-xs">
      {/* Left: Mobile hamburger & Page Header */}
      <div className="flex items-center space-x-3 min-w-0">
        <button
          onClick={() => setIsMobileDrawerOpen(true)}
          className="md:hidden p-2 rounded-md text-[#777F79] hover:text-[#202522] hover:bg-[#F7F6F2] cursor-pointer"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex flex-col min-w-0">
          <div className="flex items-center space-x-2">
            <h1 className="text-sm sm:text-base font-bold text-[#202522] tracking-tight truncate">
              {title}
            </h1>
            <span className="hidden sm:inline-flex px-1.5 py-0.5 text-[10px] font-bold bg-[#F7F6F2] text-[#246B4B] border border-[#E5E8E3] rounded uppercase tracking-wider">
              Season 2
            </span>
          </div>
          <p className="text-[11px] text-[#777F79] truncate hidden sm:block">
            {subtitle}
          </p>
        </div>
      </div>

      {/* Right: Search, Data Period, Status Indicator & Actions */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Global Player Search */}
        <div ref={searchRef} className="relative">
          <div className="relative">
            <input
              type="text"
              placeholder="Search player or ID..."
              value={globalSearch}
              onChange={(e) => {
                setGlobalSearch(e.target.value);
                setIsSearchOpen(true);
              }}
              onFocus={() => setIsSearchOpen(true)}
              className="w-36 sm:w-56 md:w-64 pl-8 pr-7 py-1.5 text-xs bg-[#F7F6F2] border border-[#E5E8E3] rounded-md focus:outline-none focus:border-[#246B4B] focus:bg-white text-[#202522] transition-colors"
            />
            <Search className="w-3.5 h-3.5 text-[#777F79] absolute left-2.5 top-2.5" />
            {globalSearch && (
              <button
                onClick={() => setGlobalSearch('')}
                className="absolute right-2 top-2 text-[#777F79] hover:text-[#202522] cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Search Dropdown Results */}
          {isSearchOpen && searchResults.length > 0 && (
            <div className="absolute right-0 mt-1 w-72 sm:w-80 bg-white border border-[#E5E8E3] rounded-md shadow-lg py-1 z-50">
              <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[#777F79] border-b border-[#E5E8E3] flex justify-between items-center">
                <span>Player Registry Matches</span>
                <span>{searchResults.length} found</span>
              </div>
              {searchResults.map((player) => (
                <button
                  key={player.id}
                  onClick={() => handleSelectSearchResult(player)}
                  className="w-full px-3 py-2 text-left hover:bg-[#F7F6F2] flex items-center justify-between transition-colors cursor-pointer border-b border-[#F7F6F2] last:border-0"
                >
                  <div className="flex items-center space-x-2 min-w-0">
                    <div className="w-6 h-6 rounded bg-[#246B4B]/10 text-[#246B4B] flex items-center justify-center font-bold text-[10px] shrink-0">
                      {player.role === 'Bowler' ? (
                        <Target className="w-3.5 h-3.5" />
                      ) : (
                        <Trophy className="w-3.5 h-3.5" />
                      )}
                    </div>
                    <div className="truncate">
                      <div className="text-xs font-semibold text-[#202522] truncate flex items-center space-x-1">
                        <span>{player.name}</span>
                        {player.isSelectedTop10 && (
                          <span className="text-[9px] bg-emerald-100 text-[#246B4B] px-1 rounded font-bold">Top 10</span>
                        )}
                      </div>
                      <div className="text-[10px] text-[#777F79] truncate">
                        {player.team} • {player.speciality}
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-2">
                    <span className="text-xs font-bold text-[#246B4B]">
                      {player.pressureScore ?? 'N/A'}
                    </span>
                    <div className="text-[9px] text-[#777F79]">{player.nationality}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Current Season / Data Period */}
        <div className="hidden lg:flex items-center px-2.5 py-1 bg-[#F7F6F2] border border-[#E5E8E3] rounded text-[11px] text-[#202522] font-medium space-x-1.5">
          <span className="text-[#777F79]">Data Window:</span>
          <span className="font-semibold text-[#202522]">IPL 2024–2026</span>
          <span className="text-[10px] text-[#777F79]">(Cutoff: 2025-12-31)</span>
        </div>

        {/* Data Status Indicator */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 bg-amber-50 border border-amber-200 text-[#D97736] rounded text-[11px] font-semibold" title="Strict methodology gating: Publication status is INTERNAL_EXPERIMENTAL_ONLY. Test set accessed in Phase 4.">
          <AlertTriangle className="w-3.5 h-3.5 text-[#D97736] shrink-0" />
          <span className="hidden sm:inline">EXPERIMENTAL (UNVALIDATED)</span>
          <span className="sm:hidden">EXP</span>
        </div>

        {/* Quick CSV Export */}
        <button
          onClick={() => exportRankingsCSV('all')}
          title="Export Top 10 Batters & Bowlers to CSV"
          className="hidden sm:flex items-center space-x-1 px-2.5 py-1 text-xs font-semibold bg-[#246B4B] text-white rounded hover:bg-[#1b5239] transition-colors cursor-pointer shadow-xs"
        >
          <FileSpreadsheet className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Export CSV</span>
        </button>
      </div>
    </header>
  );
};
