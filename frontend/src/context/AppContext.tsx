import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { RoleKind } from '@/types/submission';

export type NavigationId =
  | 'overview'
  | 'top10-batters'
  | 'top10-bowlers'
  | 'batter-profiles'
  | 'bowler-profiles'
  | 'player-comparison'
  | 'selection-analysis'
  | 'methodology'
  | 'data-validation'
  | 'ai-predictions';

export interface PlayerRef {
  id: number;
  role: RoleKind;
}

interface AppContextType {
  activeSection: NavigationId;
  setActiveSection: (s: NavigationId) => void;
  isMobileDrawerOpen: boolean;
  setIsMobileDrawerOpen: (o: boolean) => void;
  openPlayer: PlayerRef | null;
  openPlayerEvidence: (id: number, role: RoleKind) => void;
  closePlayerEvidence: () => void;
  comparison: Record<RoleKind, number[]>;
  toggleComparison: (role: RoleKind, id: number) => boolean;
  setComparison: (role: RoleKind, ids: number[]) => void;
  goCompare: (role: RoleKind, ids: number[]) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [activeSection, setActiveSection] = useState<NavigationId>('overview');
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);
  const [openPlayer, setOpenPlayer] = useState<PlayerRef | null>(null);
  const [comparison, setComparisonState] = useState<Record<RoleKind, number[]>>({ batters: [], bowlers: [] });

  const openPlayerEvidence = useCallback((id: number, role: RoleKind) => setOpenPlayer({ id, role }), []);
  const closePlayerEvidence = useCallback(() => setOpenPlayer(null), []);
  const setComparison = useCallback(
    (role: RoleKind, ids: number[]) => setComparisonState((p) => ({ ...p, [role]: ids.slice(0, 4) })),
    [],
  );
  // Returns false when the 4-player limit blocks an addition.
  const toggleComparison = useCallback(
    (role: RoleKind, id: number) => {
      const cur = comparison[role];
      if (cur.includes(id)) {
        setComparison(role, cur.filter((x) => x !== id));
        return true;
      }
      if (cur.length >= 4) return false;
      setComparison(role, [...cur, id]);
      return true;
    },
    [comparison, setComparison],
  );
  const goCompare = useCallback(
    (role: RoleKind, ids: number[]) => {
      setComparison(role, ids);
      setActiveSection('player-comparison');
    },
    [setComparison],
  );

  return (
    <AppContext.Provider
      value={{
        activeSection,
        setActiveSection,
        isMobileDrawerOpen,
        setIsMobileDrawerOpen,
        openPlayer,
        openPlayerEvidence,
        closePlayerEvidence,
        comparison,
        toggleComparison,
        setComparison,
        goCompare,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const c = useContext(AppContext);
  if (!c) throw new Error('useApp must be used within an AppProvider');
  return c;
};
