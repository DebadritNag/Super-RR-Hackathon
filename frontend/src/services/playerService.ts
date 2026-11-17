import { Player, Nationality, InternationalStatus, PlayerRole, IPLExperience, Speciality, PressureSituation, DataEligibility } from '@/types';
import { MOCK_PLAYERS } from '@/data/mock/players';

export interface PlayerFilterParams {
  search?: string;
  nationality?: Nationality | 'All';
  internationalStatus?: InternationalStatus | 'All';
  role?: PlayerRole | 'All';
  iplExperience?: IPLExperience | 'All';
  speciality?: Speciality | 'All';
  pressureSituation?: PressureSituation | 'All';
  eligibility?: DataEligibility | 'All';
  sortBy?: keyof Player;
  sortOrder?: 'asc' | 'desc';
}

export interface PlayerListResponse {
  players: Player[];
  totalCount: number;
  matchingCount: number;
  eligibleCount: number;
}

export const playerService = {
  async getPlayers(params: PlayerFilterParams = {}): Promise<PlayerListResponse> {
    // Simulate brief asynchronous turnaround
    let filtered = [...MOCK_PLAYERS];

    if (params.search) {
      const q = params.search.toLowerCase().trim();
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(q) ||
        p.team.toLowerCase().includes(q) ||
        p.role.toLowerCase().includes(q) ||
        p.speciality.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q)
      );
    }

    if (params.nationality && params.nationality !== 'All') {
      filtered = filtered.filter(p => p.nationality === params.nationality);
    }

    if (params.internationalStatus && params.internationalStatus !== 'All') {
      filtered = filtered.filter(p => p.internationalStatus === params.internationalStatus);
    }

    if (params.role && params.role !== 'All') {
      filtered = filtered.filter(p => p.role === params.role);
    }

    if (params.iplExperience && params.iplExperience !== 'All') {
      filtered = filtered.filter(p => p.iplExperience === params.iplExperience);
    }

    if (params.speciality && params.speciality !== 'All') {
      filtered = filtered.filter(p => p.speciality === params.speciality);
    }

    if (params.pressureSituation && params.pressureSituation !== 'All') {
      filtered = filtered.filter(p => p.excelsInSituations.includes(params.pressureSituation as PressureSituation));
    }

    if (params.eligibility && params.eligibility !== 'All') {
      filtered = filtered.filter(p => p.eligibility === params.eligibility);
    }

    // Sort
    if (params.sortBy) {
      const field = params.sortBy;
      const order = params.sortOrder === 'desc' ? -1 : 1;
      filtered.sort((a, b) => {
        const valA = a[field] ?? -9999;
        const valB = b[field] ?? -9999;
        if (valA < valB) return -1 * order;
        if (valA > valB) return 1 * order;
        return 0;
      });
    }

    return {
      players: filtered,
      totalCount: MOCK_PLAYERS.length,
      matchingCount: filtered.length,
      eligibleCount: filtered.filter(p => p.eligibility === 'Eligible').length,
    };
  },

  async getPlayerById(id: string): Promise<Player | null> {
    const found = MOCK_PLAYERS.find(p => p.id === id);
    return found || null;
  },

  async getMultiplePlayers(ids: string[]): Promise<Player[]> {
    return MOCK_PLAYERS.filter(p => ids.includes(p.id));
  },
};

