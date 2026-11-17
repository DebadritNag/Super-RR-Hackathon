import { Player, AuctionCombination } from '@/types';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { MOCK_AUCTION_COMBINATIONS } from '@/data/mock/auctionData';

export interface BudgetQueryResult {
  budgetCr: number;
  bestWithinBudget: Player[];
  bestValueForMoney: Player[];
  premiumTargets: { player: Player; surplusNeededCr: number }[];
  alternativeTargets: { original: Player; alternatives: Player[] }[];
  uncappedOpportunities: {
    indianUncapped: Player[];
    overseasUncapped: Player[];
  };
  recommendedCombinations: (AuctionCombination & { affordable: boolean; remainingPurseCr: number })[];
}

export const auctionService = {
  async getCombinations(): Promise<AuctionCombination[]> {
    return MOCK_AUCTION_COMBINATIONS;
  },

  async queryByBudget(budgetCr: number): Promise<BudgetQueryResult> {
    const validPlayers = MOCK_PLAYERS.filter(p => p.auctionEstimatedMax !== null);

    // 1. Within budget (estimated max <= budgetCr)
    const withinBudget = validPlayers.filter(p => (p.auctionEstimatedMax ?? 99) <= budgetCr);
    withinBudget.sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0));

    // 2. Best value for money (high value score + high pressure score relative to price)
    const valuePicks = [...validPlayers].filter(p => (p.auctionEstimatedMin ?? 0) <= budgetCr);
    valuePicks.sort((a, b) => (b.auctionValueScore ?? 0) - (a.auctionValueScore ?? 0));

    // 3. Premium targets (exceeds budget by up to 10 Cr)
    const premiumTargets = validPlayers
      .filter(p => (p.auctionEstimatedMin ?? 0) > budgetCr)
      .map(p => ({
        player: p,
        surplusNeededCr: Number(((p.auctionEstimatedMin ?? 0) - budgetCr).toFixed(1)),
      }))
      .sort((a, b) => a.surplusNeededCr - b.surplusNeededCr);

    // 4. Alternative targets: for top 3 premium players, find affordable counterparts with same role
    const alternativeTargets = premiumTargets.slice(0, 3).map(pt => {
      const alts = withinBudget.filter(
        p => p.id !== pt.player.id && (p.role === pt.player.role || p.speciality === pt.player.speciality)
      ).slice(0, 2);
      return {
        original: pt.player,
        alternatives: alts,
      };
    });

    // 5. Uncapped opportunities
    const indianUncapped = withinBudget.filter(p => p.nationality === 'Indian' && p.internationalStatus === 'Uncapped');
    const overseasUncapped = withinBudget.filter(p => p.nationality === 'Overseas' && p.internationalStatus === 'Uncapped');

    // 6. Combinations evaluated against current purse
    const combos = MOCK_AUCTION_COMBINATIONS.map(c => {
      const affordable = c.estimatedTotalMax <= budgetCr;
      const remainingPurseCr = Number(Math.max(0, budgetCr - c.estimatedTotalMax).toFixed(1));
      return {
        ...c,
        affordable,
        remainingPurseCr,
      };
    });

    return {
      budgetCr,
      bestWithinBudget: withinBudget,
      bestValueForMoney: valuePicks.slice(0, 6),
      premiumTargets: premiumTargets.slice(0, 5),
      alternativeTargets,
      uncappedOpportunities: {
        indianUncapped,
        overseasUncapped,
      },
      recommendedCombinations: combos,
    };
  },
};

