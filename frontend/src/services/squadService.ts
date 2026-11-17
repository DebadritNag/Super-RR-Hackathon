import { Player, SquadSlotRule } from '@/types';
import { MOCK_PLAYERS } from '@/data/mock/players';
import { storageAdapter } from '@/lib/storage';

export interface SquadEvaluation {
  totalPlayers: number;
  indianCount: number;
  overseasCount: number;
  cappedCount: number;
  uncappedCount: number;
  unknownStatusCount: number;
  
  batterCount: number;
  bowlerCount: number;
  allRounderCount: number;
  keeperCount: number;

  totalEstimatedCostMin: number;
  totalEstimatedCostMax: number;
  remainingBudget: number;

  battingDepthScore: number;
  bowlingDepthScore: number;
  deathBowlingRating: number;
  powerplayRating: number;
  middleOverRating: number;
  finishingRating: number;
  overallBalanceScore: number;

  warnings: {
    id: string;
    level: 'error' | 'warning' | 'info';
    message: string;
  }[];
}

export const DEFAULT_SQUAD_RULES: SquadSlotRule = {
  maxSquadSize: 25,
  maxOverseas: 8,
  minIndian: 16,
  minBatters: 5,
  minBowlers: 6,
  minAllRounders: 3,
  minWicketkeepers: 2,
  totalPurseLimit: 120.0,
};

export const squadService = {
  async getSelectedSquad(): Promise<Player[]> {
    const ids = storageAdapter.getHypotheticalSquad();
    return MOCK_PLAYERS.filter(p => ids.includes(p.id));
  },

  async addPlayerToSquad(playerId: string): Promise<Player[]> {
    const currentIds = storageAdapter.getHypotheticalSquad();
    if (!currentIds.includes(playerId)) {
      const updated = [...currentIds, playerId];
      storageAdapter.saveHypotheticalSquad(updated);
      return MOCK_PLAYERS.filter(p => updated.includes(p.id));
    }
    return MOCK_PLAYERS.filter(p => currentIds.includes(p.id));
  },

  async removePlayerFromSquad(playerId: string): Promise<Player[]> {
    const currentIds = storageAdapter.getHypotheticalSquad();
    const updated = currentIds.filter(id => id !== playerId);
    storageAdapter.saveHypotheticalSquad(updated);
    return MOCK_PLAYERS.filter(p => updated.includes(p.id));
  },

  evaluateSquad(players: Player[], rules: SquadSlotRule = DEFAULT_SQUAD_RULES): SquadEvaluation {
    const totalPlayers = players.length;
    const indianCount = players.filter(p => p.nationality === 'Indian').length;
    const overseasCount = players.filter(p => p.nationality === 'Overseas').length;
    const cappedCount = players.filter(p => p.internationalStatus === 'Verified Capped' || p.internationalStatus === 'Derived Capped').length;
    const uncappedCount = players.filter(p => p.internationalStatus === 'Uncapped').length;
    const unknownStatusCount = players.filter(p => p.internationalStatus === 'Unknown').length;

    const batterCount = players.filter(p => p.role === 'Batter').length;
    const bowlerCount = players.filter(p => p.role === 'Bowler').length;
    const allRounderCount = players.filter(p => p.role === 'All-rounder').length;
    const keeperCount = players.filter(p => p.role === 'Wicketkeeper').length;

    let totalEstimatedCostMin = 0;
    let totalEstimatedCostMax = 0;
    for (const p of players) {
      totalEstimatedCostMin += p.auctionEstimatedMin ?? 1.0;
      totalEstimatedCostMax += p.auctionEstimatedMax ?? 2.0;
    }

    const remainingBudget = Number(Math.max(0, rules.totalPurseLimit - totalEstimatedCostMax).toFixed(1));

    // Tactical metrics
    const deathBowlers = players.filter(p => p.speciality === 'Death specialist' || (p.bowlerRadar && p.bowlerRadar.deathOverEffectiveness > 85));
    const finishers = players.filter(p => p.speciality === 'Finisher' || (p.batterRadar && p.batterRadar.deathOverPerformance > 85));
    const powerplayOptions = players.filter(p => p.speciality === 'Powerplay specialist' || (p.bowlerRadar && p.bowlerRadar.powerplayEffectiveness > 85));
    const spinOptions = players.filter(p => p.speciality === 'Spin bowler' || (p.bowlerRadar && p.bowlerRadar.middleOverEffectiveness > 85));

    const deathBowlingRating = Math.min(100, deathBowlers.length * 32);
    const finishingRating = Math.min(100, finishers.length * 30);
    const powerplayRating = Math.min(100, powerplayOptions.length * 28);
    const middleOverRating = Math.min(100, spinOptions.length * 30);
    const battingDepthScore = Math.min(100, (batterCount + allRounderCount + keeperCount) * 12);
    const bowlingDepthScore = Math.min(100, (bowlerCount + allRounderCount) * 12);

    const overallBalanceScore = Math.round(
      (battingDepthScore * 0.2) +
      (bowlingDepthScore * 0.2) +
      (deathBowlingRating * 0.25) +
      (finishingRating * 0.2) +
      (middleOverRating * 0.15)
    );

    const warnings: { id: string; level: 'error' | 'warning' | 'info'; message: string }[] = [];

    if (overseasCount > rules.maxOverseas) {
      warnings.push({
        id: 'w-overseas',
        level: 'error',
        message: `Overseas quota exceeded: ${overseasCount}/${rules.maxOverseas} players selected.`,
      });
    }

    if (totalEstimatedCostMax > rules.totalPurseLimit) {
      warnings.push({
        id: 'w-budget',
        level: 'error',
        message: `Hypothetical budget exceeded by ₹${(totalEstimatedCostMax - rules.totalPurseLimit).toFixed(1)} Cr.`,
      });
    }

    if (deathBowlers.length < 2) {
      warnings.push({
        id: 'w-death-bowl',
        level: 'warning',
        message: 'Critical vulnerability: Fewer than 2 frontline death bowling specialists in squad.',
      });
    }

    if (keeperCount < 1) {
      warnings.push({
        id: 'w-keeper',
        level: 'error',
        message: 'No designated wicketkeeper selected in the squad.',
      });
    } else if (keeperCount === 1) {
      warnings.push({
        id: 'w-keeper-backup',
        level: 'info',
        message: 'Only 1 wicketkeeper selected; a backup keeper is advised for injury cover.',
      });
    }

    if (finishers.length < 2) {
      warnings.push({
        id: 'w-finishers',
        level: 'warning',
        message: 'Limited death-overs finishing depth (<2 proven pressure finishers).',
      });
    }

    if (unknownStatusCount > 0) {
      warnings.push({
        id: 'w-unknown-status',
        level: 'info',
        message: `${unknownStatusCount} player(s) have 'Unknown' international capped status. Verification needed before auction registration.`,
      });
    }

    return {
      totalPlayers,
      indianCount,
      overseasCount,
      cappedCount,
      uncappedCount,
      unknownStatusCount,
      batterCount,
      bowlerCount,
      allRounderCount,
      keeperCount,
      totalEstimatedCostMin: Number(totalEstimatedCostMin.toFixed(1)),
      totalEstimatedCostMax: Number(totalEstimatedCostMax.toFixed(1)),
      remainingBudget,
      battingDepthScore,
      bowlingDepthScore,
      deathBowlingRating,
      powerplayRating,
      middleOverRating,
      finishingRating,
      overallBalanceScore,
      warnings,
    };
  },
};

