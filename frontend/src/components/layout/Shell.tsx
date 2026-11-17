import React from 'react';
import { useApp } from '@/context/AppContext';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { DemoBanner } from '../shared/DemoBanner';
import { ToastContainer } from '../shared/Toast';
import { PlayerProfileModal } from '@/features/player-profile/PlayerProfileModal';

// The 7 Competition-Submission Features
import { OverviewDashboard } from '@/features/overview/OverviewDashboard';
import { PressureBattersPage } from '@/features/pressure-batters/PressureBattersPage';
import { PressureBowlersPage } from '@/features/pressure-bowlers/PressureBowlersPage';
import { PlayerComparison } from '@/features/player-comparison/PlayerComparison';
import { WhySelectedPage } from '@/features/selection-reasons/WhySelectedPage';
import { DataMethodologyPage } from '@/features/methodology/DataMethodologyPage';
import { RRAnalysisPage } from '@/features/rr-analysis/RRAnalysisPage';

export const Shell: React.FC = () => {
  const { activeSection } = useApp();

  const renderActiveView = () => {
    switch (activeSection) {
      case 'overview':
        return <OverviewDashboard />;
      case 'pressure-batters':
        return <PressureBattersPage />;
      case 'pressure-bowlers':
        return <PressureBowlersPage />;
      case 'player-comparison':
        return <PlayerComparison />;
      case 'selection-reasons':
        return <WhySelectedPage />;
      case 'methodology':
        return <DataMethodologyPage />;
      case 'rr-analysis':
        return <RRAnalysisPage />;
      default:
        return <OverviewDashboard />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F7F6F2] text-[#202522]">
      {/* Global Demonstration / Gating Status Banner */}
      <DemoBanner />

      <div className="flex-1 flex">
        {/* Persistent 7-Section Sidebar Navigation */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar />

          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
            {renderActiveView()}
          </main>
        </div>
      </div>

      {/* Global Player Profile Modal/Drawer */}
      <PlayerProfileModal />

      {/* Global Toast Notifications */}
      <ToastContainer />
    </div>
  );
};
