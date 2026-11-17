import React from 'react';
import { useApp } from '@/context/AppContext';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { PlayerEvidenceModal } from '@/features/player-evidence/PlayerEvidenceModal';
import { OverviewPage } from '@/features/overview/OverviewPage';
import { Top10Page } from '@/features/top10/Top10Page';
import { ProfilesPage } from '@/features/profiles/ProfilesPage';
import { ComparisonPage } from '@/features/comparison/ComparisonPage';
import { WhyPage } from '@/features/why/WhyPage';
import { MethodologyPage } from '@/features/methodology/MethodologyPage';
import { ValidationPage } from '@/features/validation/ValidationPage';
import { AiPredictionsPage } from '@/features/experimental/AiPredictionsPage';

export const Shell: React.FC = () => {
  const { activeSection } = useApp();
  const view = (() => {
    switch (activeSection) {
      case 'top10-batters':
        return <Top10Page role="batters" />;
      case 'top10-bowlers':
        return <Top10Page role="bowlers" />;
      case 'batter-profiles':
        return <ProfilesPage role="batters" />;
      case 'bowler-profiles':
        return <ProfilesPage role="bowlers" />;
      case 'player-comparison':
        return <ComparisonPage />;
      case 'selection-analysis':
        return <WhyPage />;
      case 'methodology':
        return <MethodologyPage />;
      case 'data-validation':
        return <ValidationPage />;
      case 'ai-predictions':
        return <AiPredictionsPage />;
      default:
        return <OverviewPage />;
    }
  })();
  return (
    <div className="min-h-screen flex bg-[#F7F6F2] text-[#202522]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto min-w-0">{view}</main>
      </div>
      <PlayerEvidenceModal />
    </div>
  );
};
