import { HistoricalSquadNeed, Player } from '@/types';
import { MOCK_HISTORICAL_NEEDS } from '@/data/mock/historicalNeeds';
import { MOCK_PLAYERS } from '@/data/mock/players';

export interface HistoricalNeedsResponse {
  season: string;
  needs: HistoricalSquadNeed[];
  recommendedPlayers: {
    player: Player;
    matchedNeed: HistoricalSquadNeed;
    squadFitScore: number;
    fitRationale: string;
  }[];
}

export const historicalNeedsService = {
  async getNeeds(season: string = 'Combined'): Promise<HistoricalNeedsResponse> {
    let filtered = [...MOCK_HISTORICAL_NEEDS];
    if (season !== 'Combined') {
      filtered = filtered.filter(n => n.season === season || n.season === 'Combined');
    }

    // Build recommended players with squad fit scores
    const recommendedMap = new Map<string, { player: Player; matchedNeed: HistoricalSquadNeed; squadFitScore: number; fitRationale: string }>();

    for (const need of filtered) {
      for (const pId of need.recommendedPlayerIds) {
        const player = MOCK_PLAYERS.find(p => p.id === pId);
        if (player) {
          if (!recommendedMap.has(pId)) {
            recommendedMap.set(pId, {
              player,
              matchedNeed: need,
              squadFitScore: player.squadFitScore ?? 85,
              fitRationale: player.squadFitReason ?? need.recruitmentImplication,
            });
          }
        }
      }
    }

    const recommendedList = Array.from(recommendedMap.values());
    recommendedList.sort((a, b) => b.squadFitScore - a.squadFitScore);

    return {
      season,
      needs: filtered,
      recommendedPlayers: recommendedList,
    };
  },
};

