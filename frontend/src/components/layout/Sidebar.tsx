import React from 'react';
import { useApp, NavigationId } from '@/context/AppContext';
import {
  LayoutDashboard,
  Trophy,
  Target,
  Scale,
  HelpCircle,
  BookOpen,
  History,
  ChevronLeft,
  ChevronRight,
  Shield,
  FileSpreadsheet,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  id: NavigationId;
  label: string;
  icon: React.ReactNode;
  badge?: string;
  badgeColor?: string;
}

export const Sidebar: React.FC = () => {
  const {
    activeSection,
    setActiveSection,
    isSidebarCollapsed,
    toggleSidebar,
    isMobileDrawerOpen,
    setIsMobileDrawerOpen,
    comparisonPlayerIds,
    exportRankingsCSV,
  } = useApp();

  const navItems: NavItem[] = [
    { 
      id: 'overview', 
      label: 'Overview', 
      icon: <LayoutDashboard className="w-4 h-4" /> 
    },
    { 
      id: 'pressure-batters', 
      label: 'Pressure Batters', 
      icon: <Trophy className="w-4 h-4" />, 
      badge: 'Top 10',
      badgeColor: 'bg-[#246B4B]'
    },
    { 
      id: 'pressure-bowlers', 
      label: 'Pressure Bowlers', 
      icon: <Target className="w-4 h-4" />, 
      badge: 'Top 10',
      badgeColor: 'bg-[#246B4B]'
    },
    {
      id: 'player-comparison',
      label: 'Player Comparison',
      icon: <Scale className="w-4 h-4" />,
      badge: comparisonPlayerIds.length > 0 ? `${comparisonPlayerIds.length}` : undefined,
      badgeColor: 'bg-[#D97736]',
    },
    {
      id: 'selection-reasons',
      label: 'Why Selected / Not Selected',
      icon: <HelpCircle className="w-4 h-4" />,
      badge: 'Audit',
      badgeColor: 'bg-[#202522] border border-[#3b7e5f]'
    },
    { 
      id: 'methodology', 
      label: 'Data & Methodology', 
      icon: <BookOpen className="w-4 h-4" />,
      badge: '9-Step'
    },
    { 
      id: 'rr-analysis', 
      label: 'Rajasthan Royals Analysis', 
      icon: <History className="w-4 h-4" />,
      badge: '2025-26',
      badgeColor: 'bg-[#D97736]'
    },
  ];

  const handleNavClick = (id: NavigationId) => {
    setActiveSection(id);
    if (isMobileDrawerOpen) {
      setIsMobileDrawerOpen(false);
    }
  };

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#202522] text-white border-r border-[#2d3430] select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-[#2d3430]">
        {!isSidebarCollapsed ? (
          <div className="flex items-center space-x-3 overflow-hidden">
            <div className="w-8 h-8 rounded bg-[#246B4B] border border-[#3b7e5f] flex items-center justify-center text-white font-black text-sm tracking-tighter shrink-0 shadow-xs">
              RR
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-bold uppercase tracking-wider text-white truncate">
                SupeRR Selector
              </span>
              <span className="text-[10px] text-emerald-400/90 font-medium tracking-tight truncate">
                Season 2 • Intel Platform
              </span>
            </div>
          </div>
        ) : (
          <div className="mx-auto w-8 h-8 rounded bg-[#246B4B] border border-[#3b7e5f] flex items-center justify-center text-white font-black text-sm">
            RR
          </div>
        )}

        <button
          onClick={toggleSidebar}
          aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="hidden md:flex p-1.5 rounded text-[#777F79] hover:text-white hover:bg-[#2d3430] transition-colors cursor-pointer"
        >
          {isSidebarCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Primary Navigation List */}
      <div className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        <div className={cn(
          "px-2 pb-2 text-[10px] font-bold uppercase tracking-wider text-[#777F79]",
          isSidebarCollapsed && "sr-only"
        )}>
          Competition Submission
        </div>

        {navItems.map((item) => {
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              title={isSidebarCollapsed ? item.label : undefined}
              className={cn(
                "w-full flex items-center rounded-md text-xs font-medium transition-all duration-150 cursor-pointer relative",
                isSidebarCollapsed ? "justify-center p-2.5" : "px-3 py-2.5 space-x-3 text-left",
                isActive
                  ? "bg-[#246B4B] text-white shadow-xs font-semibold"
                  : "text-[#B5BCB7] hover:text-white hover:bg-[#282E2B]"
              )}
            >
              <span className={cn(
                "shrink-0",
                isActive ? "text-white" : "text-[#8F9791]"
              )}>
                {item.icon}
              </span>

              {!isSidebarCollapsed && (
                <div className="flex-1 flex items-center justify-between truncate">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={cn(
                        "ml-2 px-1.5 py-0.5 text-[9px] font-bold rounded uppercase tracking-wider leading-none",
                        item.badgeColor || "bg-[#2d3430] text-emerald-300"
                      )}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* CSV Quick Export Tool */}
      <div className="p-3 border-t border-[#2d3430]">
        {!isSidebarCollapsed ? (
          <div className="bg-[#181C1A] rounded p-2.5 border border-[#2d3430] space-y-2">
            <div className="flex items-center justify-between text-[11px] text-[#A2ABA5]">
              <span className="flex items-center space-x-1.5 font-medium">
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                <span>Export Submissions</span>
              </span>
            </div>
            <div className="grid grid-cols-2 gap-1.5 pt-1">
              <button
                onClick={() => exportRankingsCSV('batters')}
                className="px-2 py-1 bg-[#246B4B]/30 hover:bg-[#246B4B] text-[10px] text-white font-medium rounded transition-colors text-center border border-[#3b7e5f]/50 cursor-pointer"
              >
                Batters CSV
              </button>
              <button
                onClick={() => exportRankingsCSV('bowlers')}
                className="px-2 py-1 bg-[#246B4B]/30 hover:bg-[#246B4B] text-[10px] text-white font-medium rounded transition-colors text-center border border-[#3b7e5f]/50 cursor-pointer"
              >
                Bowlers CSV
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => exportRankingsCSV('all')}
            title="Export CSV"
            className="w-full flex justify-center p-2 text-[#777F79] hover:text-white hover:bg-[#2d3430] rounded cursor-pointer"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
          </button>
        )}
      </div>

      {/* Compliance / Status Footer */}
      <div className="p-3 border-t border-[#2d3430]">
        {!isSidebarCollapsed ? (
          <div className="space-y-1">
            <div className="flex items-center space-x-1.5 text-[10px] text-[#8F9791]">
              <Shield className="w-3 h-3 text-[#D97736]" />
              <span className="font-semibold text-amber-300">Phase 4 Disclosure</span>
            </div>
            <p className="text-[10px] text-[#777F79] leading-tight">
              Provisional 70:30 format. Test holdout previously accessed in Phase 4.
            </p>
          </div>
        ) : (
          <div className="flex justify-center" title="Phase 4 Disclosure: Provisional format">
            <Shield className="w-3.5 h-3.5 text-[#D97736]" />
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside
        className={cn(
          "hidden md:block transition-all duration-200 shrink-0",
          isSidebarCollapsed ? "w-16" : "w-64"
        )}
      >
        <div className="fixed top-0 bottom-0 left-0 z-30 transition-all duration-200" style={{ width: isSidebarCollapsed ? '4rem' : '16rem' }}>
          {sidebarContent}
        </div>
      </aside>

      {/* Mobile Backdrop & Drawer */}
      {isMobileDrawerOpen && (
        <div className="fixed inset-0 z-40 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={() => setIsMobileDrawerOpen(false)}
          />
          <div className="relative flex-1 flex flex-col max-w-xs w-full bg-[#202522] z-50">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
