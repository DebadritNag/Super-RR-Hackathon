import { Player, Nationality, InternationalStatus, PressureSituation } from '@/types';
import { MOCK_PLAYERS } from '@/data/mock/players';

export interface RankingFilterParams {
  category: 'Batters' | 'Bowlers';
  nationality?: Nationality | 'All';
  internationalStatus?: InternationalStatus | 'All';
  pressureDefinition?: 'Standard Leverage Index' | 'Death Overs Closeness' | 'Chasing High RRR' | 'Early Wicket Collapse';
  matchSituation?: PressureSituation | 'All';
  inningsPhase?: 'All' | 'Powerplay' | 'Middle Overs' | 'Death Overs';
  minSample?: number;
  eligibilityOnly?: boolean;
}

export interface RankedPlayerItem {
  rank: number;
  player: Player;
  pressureScore: number;
  baselineScore: number;
  adjustedPerformance: number;
  opportunities: number; // sample size
  matches: number;
  reliability: string;
  uncertainty: string;
}

export interface ExcludedPlayerItem {
  player: Player;
  reason: string;
}

export interface RankingResponse {
  rankedPlayers: RankedPlayerItem[];
  excludedPlayers: ExcludedPlayerItem[];
  matchingCount: number;
  eligibleCount: number;
  isExperimental: boolean;
  filterSummary: string;
}

export const rankingService = {
  async getRankings(params: RankingFilterParams): Promise<RankingResponse> {
    const isBatter = params.category === 'Batters';
    
    // Initial role separation
    const pool = MOCK_PLAYERS.filter(p => {
      if (isBatter) {
        return p.role === 'Batter' || p.role === 'Wicketkeeper' || (p.role === 'All-rounder' && p.batterRadar);
      } else {
        return p.role === 'Bowler' || (p.role === 'All-rounder' && p.bowlerRadar);
      }
    });

    const ranked: RankedPlayerItem[] = [];
    const excluded: ExcludedPlayerItem[] = [];

    const minSample = params.minSample ?? 100;

    for (const player of pool) {
      // Check filters
      if (params.nationality && params.nationality !== 'All' && player.nationality !== params.nationality) {
        excluded.push({ player, reason: `Nationality mismatch (Requires ${params.nationality})` });
        continue;
      }

      if (params.internationalStatus && params.internationalStatus !== 'All' && player.internationalStatus !== params.internationalStatus) {
        excluded.push({ player, reason: `Status mismatch (Requires ${params.internationalStatus})` });
        continue;
      }

      if (params.matchSituation && params.matchSituation !== 'All' && !player.excelsInSituations.includes(params.matchSituation)) {
        excluded.push({ player, reason: `Does not meet criteria for ${params.matchSituation}` });
        continue;
      }

      if (player.sampleSize < minSample) {
        excluded.push({ player, reason: `Sample size (${player.sampleSize}) below required minimum (${minSample} balls)` });
        continue;
      }

      if (player.eligibility !== 'Eligible') {
        excluded.push({ player, reason: `Data eligibility status: ${player.eligibility}` });
        continue;
      }

      if (player.pressureScore === null) {
        excluded.push({ player, reason: 'Pressure performance score not computable (insufficient data)' });
        continue;
      }

      // Dynamic weighting adjustments depending on pressure definition
      let calculatedScore = player.pressureScore;
      if (params.pressureDefinition === 'Death Overs Closeness') {
        if (isBatter && player.batterRadar) {
          calculatedScore = (calculatedScore * 0.6) + (player.batterRadar.deathOverPerformance * 0.4);
        } else if (!isBatter && player.bowlerRadar) {
          calculatedScore = (calculatedScore * 0.6) + (player.bowlerRadar.deathOverEffectiveness * 0.4);
        }
      } else if (params.pressureDefinition === 'Chasing High RRR') {
        if (isBatter && player.batterRadar) {
          calculatedScore = (calculatedScore * 0.5) + (player.batterRadar.chasePerformance * 0.5);
        }
      }

      ranked.push({
        rank: 0, // Will be set after sort
        player,
        pressureScore: Number(calculatedScore.toFixed(1)),
        baselineScore: player.baselineScore ?? 75.0,
        adjustedPerformance: player.adjustedPerformance ?? 0.0,
        opportunities: player.sampleSize,
        matches: player.matches,
        reliability: player.reliability,
        uncertainty: player.uncertaintyInterval ? `±${((player.uncertaintyInterval[1] - player.uncertaintyInterval[0]) / 2).toFixed(1)}` : 'N/A',
      });
    }

    // Sort by calculated pressure score descending
    ranked.sort((a, b) => b.pressureScore - a.pressureScore);

    // Assign true consecutive ranks (1, 2, 3...)
    ranked.forEach((item, index) => {
      item.rank = index + 1;
    });

    return {
      rankedPlayers: ranked,
      excludedPlayers: excluded,
      matchingCount: pool.length,
      eligibleCount: ranked.length,
      isExperimental: true,
      filterSummary: `${params.category} | ${params.nationality ?? 'All Nationalities'} | ${params.internationalStatus ?? 'All Statuses'}`,
    };
  },
};

