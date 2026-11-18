import React from 'react';
import { LayoutDashboard, Trophy, Target, Users, ShieldCheck, GitCompare, HelpCircle, BookOpen, Database, Cpu } from 'lucide-react';
import type { NavigationId } from '@/context/AppContext';

export const NAV_ITEMS: { id: NavigationId; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'top10-batters', label: 'Top 10 Batters', icon: <Trophy className="w-4 h-4" /> },
  { id: 'top10-bowlers', label: 'Top 10 Bowlers', icon: <Target className="w-4 h-4" /> },
  { id: 'batter-profiles', label: 'Batter Profiles', icon: <Users className="w-4 h-4" /> },
  { id: 'bowler-profiles', label: 'Bowler Profiles', icon: <ShieldCheck className="w-4 h-4" /> },
  { id: 'player-comparison', label: 'Player Comparison', icon: <GitCompare className="w-4 h-4" /> },
  { id: 'selection-analysis', label: 'Why Selected / Why Not Selected', icon: <HelpCircle className="w-4 h-4" /> },
  { id: 'methodology', label: 'Pressure Methodology', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'data-validation', label: 'Data & Validation', icon: <Database className="w-4 h-4" /> },
  { id: 'ai-predictions', label: 'Experimental AI Predictions', icon: <Cpu className="w-4 h-4" /> },
];
