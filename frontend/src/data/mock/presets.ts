import { CustomConstraints } from '@/types';

export interface PresetConfig {
  id: string;
  name: string;
  description: string;
  constraints: CustomConstraints;
}

export const MOCK_PRESETS: PresetConfig[] = [
  {
    id: 'preset-1',
    name: 'Best Indian Uncapped XI',
    description: 'Selects the top performing Indian uncapped talents across batting, bowling and keeping.',
    constraints: {
      nationality: 'Indian only',
      internationalStatus: 'Uncapped only',
      role: 'Any role',
      selectionCount: 10,
      minIndian: 10,
      minUncapped: 10,
      isStrictMode: false,
    },
  },
  {
    id: 'preset-2',
    name: 'Top Indian Uncapped Batters',
    description: 'Ranks the highest rated Indian uncapped batters and finishers by pressure boundary conversion.',
    constraints: {
      nationality: 'Indian only',
      internationalStatus: 'Uncapped only',
      role: 'Batter',
      selectionCount: 10,
      minIndian: 10,
      minUncapped: 10,
      minBatters: 10,
      isStrictMode: false,
    },
  },
  {
    id: 'preset-3',
    name: 'Top Indian Uncapped Bowlers',
    description: 'Focuses on Indian uncapped pace and spin talent with superior economy and dot ball rates under pressure.',
    constraints: {
      nationality: 'Indian only',
      internationalStatus: 'Uncapped only',
      role: 'Bowler',
      selectionCount: 10,
      minIndian: 10,
      minUncapped: 10,
      minBowlers: 10,
      isStrictMode: false,
    },
  },
  {
    id: 'preset-4',
    name: 'Best Overseas Uncapped Players',
    description: 'Global emerging franchise talent who have not represented their senior national team in IT20.',
    constraints: {
      nationality: 'Overseas only',
      internationalStatus: 'Uncapped only',
      role: 'Any role',
      selectionCount: 10,
      minOverseas: 10,
      minUncapped: 10,
      isStrictMode: false,
    },
  },
  {
    id: 'preset-5',
    name: 'Emerging Domestic Talent',
    description: 'New IPL recruits and domestic standouts who meet basic sample thresholds.',
    constraints: {
      nationality: 'Indian only',
      internationalStatus: 'Uncapped only',
      role: 'Any role',
      selectionCount: 10,
      minUncapped: 8,
      isStrictMode: false,
    },
  },
  {
    id: 'preset-6',
    name: 'Mixed Capped and Uncapped XI',
    description: 'Balanced recruitment model pairing experienced mentors with explosive high-ceiling young prospects.',
    constraints: {
      nationality: 'Mixed',
      internationalStatus: 'Mixed',
      role: 'Any role',
      selectionCount: 10,
      minCapped: 5,
      minUncapped: 3,
      minIndian: 7,
      maxOverseas: 3,
      isStrictMode: true,
    },
  },
  {
    id: 'preset-7',
    name: 'Best Death-over Specialists',
    description: 'Targeted selection of players who excel in the critical overs 16-20 (bat or ball).',
    constraints: {
      nationality: 'No restriction',
      internationalStatus: 'No restriction',
      role: 'Any role',
      selectionCount: 10,
      isStrictMode: false,
    },
  },
  {
    id: 'preset-8',
    name: 'Best Middle-order Batters',
    description: 'Top-ranked middle-order stability anchors and spin disruptors in overs 7-15.',
    constraints: {
      nationality: 'No restriction',
      internationalStatus: 'No restriction',
      role: 'Batter',
      selectionCount: 10,
      minBatters: 10,
      isStrictMode: true,
    },
  },
  {
    id: 'preset-9',
    name: 'Best Pressure Bowlers',
    description: 'Elite bowlers with highest dot-ball percentage and lowest boundary concession under pressure.',
    constraints: {
      nationality: 'No restriction',
      internationalStatus: 'No restriction',
      role: 'Bowler',
      selectionCount: 10,
      minBowlers: 10,
      isStrictMode: true,
    },
  },
  {
    id: 'preset-10',
    name: 'Custom Selection',
    description: 'User-configured custom ranking matrix with full independent constraint flexibility.',
    constraints: {
      nationality: 'No restriction',
      internationalStatus: 'No restriction',
      role: 'Any role',
      selectionCount: 10,
      isStrictMode: false,
    },
  },
];

