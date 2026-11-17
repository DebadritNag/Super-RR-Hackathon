import { AuctionCombination } from '@/types';

export const MOCK_AUCTION_COMBINATIONS: AuctionCombination[] = [
  {
    id: 'combo-1',
    title: 'Clutch Core: Finisher + Death Specialist',
    description: 'Combines premier Indian finishing composure with elite death over yorker execution.',
    playerIds: ['p-103', 'p-202'], // Rinku Singh + Sandeep Sharma
    estimatedTotalMin: 19.0,
    estimatedTotalMax: 26.0,
    roleCoverage: 'Finisher (LHB) + Death Bowling Specialist (RH Seam)',
    nationalityComposition: '2 Indian (100%)',
    strengths: 'Addresses both primary historical choke points (close chases and death over defense) without consuming overseas quota.',
    risks: 'Competitive auction bidding for high-demand Indian clutch specialists.',
  },
  {
    id: 'combo-2',
    title: 'Dynamic Impact: Middle-Order Anchor + Extreme Pace',
    description: 'Combines spin-wrecking middle-order capability with raw 150+ km/h powerplay breakthrough pace.',
    playerIds: ['p-101', 'p-206'], // Riyan Parag + Mayank Yadav
    estimatedTotalMin: 22.0,
    estimatedTotalMax: 30.0,
    roleCoverage: 'Middle-Order Batter (RHB) + Express Strike Bowler (RH Fast)',
    nationalityComposition: '2 Indian (100%)',
    strengths: 'Young Indian core providing elite middle-overs batting stability and fearsome opening bowling threat.',
    risks: 'Fitness monitoring required for high-speed bowling workload.',
  },
  {
    id: 'combo-3',
    title: 'Uncapped Domestic Edge: Dual Finisher Package',
    description: 'High value-for-money combination securing two of the most explosive uncapped Indian finishers.',
    playerIds: ['p-105', 'p-106'], // Shashank Singh + Ashutosh Sharma
    estimatedTotalMin: 9.5,
    estimatedTotalMax: 15.5,
    roleCoverage: '2 Death Overs Finishers (RHB)',
    nationalityComposition: '2 Indian Uncapped (100%)',
    strengths: 'Substantial purse savings leaving budget for marquee international pace bowlers; fearlessness in tight chases.',
    risks: 'Slightly higher variance against world-class international spin bowlers.',
  },
  {
    id: 'combo-4',
    title: 'Overseas Powerhouse + Value Balance',
    description: 'World-class overseas middle-overs destructor paired with an efficient Indian uncapped left-arm seamer.',
    playerIds: ['p-102', 'p-208'], // Heinrich Klaasen + Yash Dayal
    estimatedTotalMin: 22.5,
    estimatedTotalMax: 30.0,
    roleCoverage: 'Middle-Order Spin Hitter (Overseas) + Left-Arm Seamer (Indian)',
    nationalityComposition: '1 Overseas, 1 Indian',
    strengths: 'Immediate transformation of spin scoring rate plus tactical left-arm bowling angle.',
    risks: 'Consumes 1 overseas slot and requires substantial purse allocation for marquee batter.',
  },
  {
    id: 'combo-5',
    title: 'Complete Balance: All-Rounder + Specialist Spinner',
    description: 'Solves long-tail syndrome and middle-overs wicket drought in a single strategic swoop.',
    playerIds: ['p-301', 'p-205'], // Axar Patel + Yuzvendra Chahal
    estimatedTotalMin: 26.0,
    estimatedTotalMax: 34.5,
    roleCoverage: 'Spin All-Rounder (LHB/SLA) + Wicket-Taking Leg Spinner (RH Legbreak)',
    nationalityComposition: '2 Indian (100%)',
    strengths: 'Guarantees 8 overs of top-tier spin control and batting depth down to number 8.',
    risks: 'High cumulative price point requiring strict budget discipline.',
  },
];

