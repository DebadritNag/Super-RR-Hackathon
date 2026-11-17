import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Player } from '@/types';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { shortlistService } from '@/services/shortlistService';
import { squadService } from '@/services/squadService';

export type NavigationId = 
  | 'overview'
  | 'pressure-batters'
  | 'pressure-bowlers'
  | 'player-comparison'
  | 'selection-reasons'
  | 'methodology'
  | 'rr-analysis'
  | 'player-explorer'
  | 'pressure-rankings'
  | 'custom-top10'
  | 'squad-builder'
  | 'historical-needs'
  | 'auction-intelligence'
  | 'purse-explorer'
  | 'saved-shortlists'
  | 'settings';

export interface ToastMessage {
  id: string;
  type: 'success' | 'warning' | 'info' | 'error';
  title?: string;
  message: string;
}

interface AppContextType {
  activeSection: NavigationId;
  setActiveSection: (section: NavigationId) => void;
  selectedSeason: string;
  setSelectedSeason: (season: string) => void;
  
  // Profile modal / drawer
  selectedPlayerForProfile: Player | null;
  openPlayerProfile: (player: Player) => void;
  closePlayerProfile: () => void;

  // Comparison queue (2 to 4 compatible players)
  comparisonPlayerIds: string[];
  addToComparison: (playerId: string) => void;
  removeFromComparison: (playerId: string) => void;
  setComparisonPlayers: (playerIds: string[]) => void;
  clearComparison: () => void;

  // Overview Radar Selected Players
  overviewSelectedBatterId: string;
  setOverviewSelectedBatterId: (id: string) => void;
  overviewSelectedBowlerId: string;
  setOverviewSelectedBowlerId: (id: string) => void;

  // Global search
  globalSearch: string;
  setGlobalSearch: (q: string) => void;

  // Navigation toggles
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  isMobileDrawerOpen: boolean;
  setIsMobileDrawerOpen: (open: boolean) => void;

  // Toast notifications
  toasts: ToastMessage[];
  addToast: (message: string, type?: ToastMessage['type'], title?: string) => void;
  removeToast: (id: string) => void;

  // CSV Export utility
  exportRankingsCSV: (category?: 'batters' | 'bowlers' | 'all') => void;

  // Legacy helper properties (retained for backward compatibility)
  hypotheticalPurseCr: number;
  setHypotheticalPurseCr: (purse: number) => void;
  lastYearSuggestionActive: boolean;
  setLastYearSuggestionActive: (active: boolean) => void;
  shortlistCount: number;
  refreshShortlistCount: () => Promise<void>;
  addPlayerToShortlist: (player: Player, note?: string) => Promise<void>;
  squadCount: number;
  refreshSquadCount: () => Promise<void>;
  addPlayerToSquad: (player: Player) => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [activeSection, setActiveSection] = useState<NavigationId>('overview');
  const [selectedSeason, setSelectedSeason] = useState<string>('IPL 2024-2026 Evaluation Window');
  const [selectedPlayerForProfile, setSelectedPlayerForProfile] = useState<Player | null>(null);
  const [comparisonPlayerIds, setComparisonPlayerIds] = useState<string[]>(['p-101', 'p-102']);
  const [overviewSelectedBatterId, setOverviewSelectedBatterId] = useState<string>('p-101');
  const [overviewSelectedBowlerId, setOverviewSelectedBowlerId] = useState<string>('p-201');
  const [globalSearch, setGlobalSearch] = useState<string>('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState<boolean>(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [hypotheticalPurseCr, setHypotheticalPurseCr] = useState<number>(15.0);
  const [lastYearSuggestionActive, setLastYearSuggestionActive] = useState<boolean>(false);
  const [shortlistCount, setShortlistCount] = useState<number>(4);
  const [squadCount, setSquadCount] = useState<number>(5);

  const refreshShortlistCount = async () => {
    const list = await shortlistService.getShortlists();
    setShortlistCount(list.length);
  };

  const refreshSquadCount = async () => {
    const list = await squadService.getSelectedSquad();
    setSquadCount(list.length);
  };

  const addPlayerToShortlist = async (player: Player, note?: string) => {
    await shortlistService.addPlayer(player.id, player.name, note);
    await refreshShortlistCount();
    addToast(`${player.name} added to shortlist`, 'success');
  };

  const addPlayerToSquad = async (player: Player) => {
    await squadService.addPlayerToSquad(player.id);
    await refreshSquadCount();
    addToast(`${player.name} added to squad`, 'success');
  };

  const addToast = (message: string, type: ToastMessage['type'] = 'info', title?: string) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    setToasts(prev => [...prev, { id, message, type, title }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4500);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  const openPlayerProfile = (player: Player) => {
    setSelectedPlayerForProfile(player);
  };

  const closePlayerProfile = () => {
    setSelectedPlayerForProfile(null);
  };

  const addToComparison = (playerId: string) => {
    if (comparisonPlayerIds.includes(playerId)) {
      addToast('Player is already in comparison table', 'info');
      return;
    }
    if (comparisonPlayerIds.length >= 4) {
      addToast('Maximum 4 players can be compared simultaneously', 'warning');
      return;
    }
    const newPlayer = MOCK_PLAYERS.find(p => p.id === playerId);
    if (!newPlayer) return;

    if (comparisonPlayerIds.length > 0) {
      const existingFirst = MOCK_PLAYERS.find(p => p.id === comparisonPlayerIds[0]);
      if (existingFirst) {
        const isFirstBatter = existingFirst.role === 'Batter' || existingFirst.role === 'Wicketkeeper';
        const isNewBatter = newPlayer.role === 'Batter' || newPlayer.role === 'Wicketkeeper';
        if (isFirstBatter !== isNewBatter) {
          addToast(`Cannot compare incompatible player types: ${existingFirst.role} with ${newPlayer.role}`, 'error', 'Incompatible Roles');
          return;
        }
      }
    }

    setComparisonPlayerIds(prev => [...prev, playerId]);
    addToast(`${newPlayer.name} added to comparison`, 'success');
  };

  const removeFromComparison = (playerId: string) => {
    setComparisonPlayerIds(prev => prev.filter(id => id !== playerId));
  };

  const setComparisonPlayers = (playerIds: string[]) => {
    setComparisonPlayerIds(playerIds);
  };

  const clearComparison = () => {
    setComparisonPlayerIds([]);
    addToast('Comparison cleared', 'info');
  };

  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => !prev);
  };

  const exportRankingsCSV = (category: 'batters' | 'bowlers' | 'all' = 'all') => {
    let rows: string[][] = [
      ['Category', 'Rank', 'Player Name', 'Player ID', 'Team', 'Role', 'Nationality', 'International Status', 'Pressure Score', 'Baseline Score', 'Residual Uplift %', 'Pressure Balls Faced/Bowled', 'Distinct Matches', 'Reliability', 'Credible Interval', 'Selection Rationale']
    ];

    const batters = MOCK_PLAYERS.filter(p => p.isSelectedTop10 && (p.role === 'Batter' || p.role === 'Wicketkeeper'))
      .sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0));
    
    const bowlers = MOCK_PLAYERS.filter(p => p.isSelectedTop10 && (p.role === 'Bowler' || (p.role === 'All-rounder' && p.bowlerRadar)))
      .sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0));

    if (category === 'batters' || category === 'all') {
      batters.forEach((p, idx) => {
        rows.push([
          'Pressure Batter',
          String(idx + 1),
          p.name,
          p.id,
          p.team,
          p.role,
          p.nationality,
          p.internationalStatus,
          String(p.pressureScore ?? 'N/A'),
          String(p.baselineScore ?? 'N/A'),
          String(p.adjustedPerformance ?? 'N/A'),
          String(p.sampleSize),
          String(p.matches),
          p.reliability,
          p.uncertaintyInterval ? `[${p.uncertaintyInterval[0]} - ${p.uncertaintyInterval[1]}]` : 'N/A',
          `"${p.rankingRationale.replace(/"/g, '""')}"`
        ]);
      });
    }

    if (category === 'bowlers' || category === 'all') {
      bowlers.forEach((p, idx) => {
        rows.push([
          'Pressure Bowler',
          String(idx + 1),
          p.name,
          p.id,
          p.team,
          p.role,
          p.nationality,
          p.internationalStatus,
          String(p.pressureScore ?? 'N/A'),
          String(p.baselineEconomy ?? 'N/A'),
          String(p.adjustedPerformance ?? 'N/A'),
          String(p.sampleSize),
          String(p.matches),
          p.reliability,
          p.uncertaintyInterval ? `[${p.uncertaintyInterval[0]} - ${p.uncertaintyInterval[1]}]` : 'N/A',
          `"${p.rankingRationale.replace(/"/g, '""')}"`
        ]);
      });
    }

    const csvContent = 'data:text/csv;charset=utf-8,' + rows.map(e => e.join(',')).join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `superr_selector_s2_${category}_rankings.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    addToast(`Exported ${category.toUpperCase()} rankings to CSV successfully`, 'success');
  };

  return (
    <AppContext.Provider
      value={{
        activeSection,
        setActiveSection,
        selectedSeason,
        setSelectedSeason,
        selectedPlayerForProfile,
        openPlayerProfile,
        closePlayerProfile,
        comparisonPlayerIds,
        addToComparison,
        removeFromComparison,
        setComparisonPlayers,
        clearComparison,
        overviewSelectedBatterId,
        setOverviewSelectedBatterId,
        overviewSelectedBowlerId,
        setOverviewSelectedBowlerId,
        globalSearch,
        setGlobalSearch,
        isSidebarCollapsed,
        toggleSidebar,
        isMobileDrawerOpen,
        setIsMobileDrawerOpen,
        toasts,
        addToast,
        removeToast,
        exportRankingsCSV,
        hypotheticalPurseCr,
        setHypotheticalPurseCr,
        lastYearSuggestionActive,
        setLastYearSuggestionActive,
        shortlistCount,
        refreshShortlistCount,
        addPlayerToShortlist,
        squadCount,
        refreshSquadCount,
        addPlayerToSquad,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
