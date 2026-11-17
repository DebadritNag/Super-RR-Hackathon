import { ShortlistItem } from '@/types';

export const INITIAL_SHORTLISTS: ShortlistItem[] = [
  {
    id: 'sl-1',
    type: 'player',
    title: 'Rinku Singh',
    targetId: 'p-103',
    notes: 'Primary target for Indian pressure finisher role. Elite boundary conversion in final 3 overs.',
    createdAt: '2026-11-12T14:30:00Z',
    updatedAt: '2026-11-12T14:30:00Z',
  },
  {
    id: 'sl-2',
    type: 'player',
    title: 'Jasprit Bumrah',
    targetId: 'p-201',
    notes: 'World-class death bowler. Would completely solve historical death-overs economy leakage.',
    createdAt: '2026-11-13T09:15:00Z',
    updatedAt: '2026-11-13T09:15:00Z',
  },
  {
    id: 'sl-3',
    type: 'auction-target',
    title: 'High-Priority Purse Combination #1',
    targetId: 'combo-1',
    playerIds: ['p-103', 'p-202'],
    notes: 'Rinku + Sandeep Sharma combo. Solves both finishing and death bowling within ~₹22 Cr budget.',
    createdAt: '2026-11-14T11:45:00Z',
    updatedAt: '2026-11-14T11:45:00Z',
  },
  {
    id: 'sl-4',
    type: 'custom-ranking',
    title: 'Emerging Indian Finishers 2026',
    targetId: 'preset-2',
    playerIds: ['p-105', 'p-106', 'p-109'],
    notes: 'Ranked list of uncapped domestic finishers to watch during auction second round.',
    createdAt: '2026-11-14T16:20:00Z',
    updatedAt: '2026-11-14T16:20:00Z',
  },
];

