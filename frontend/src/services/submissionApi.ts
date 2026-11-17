import type {
  OverviewData,
  Top10Data,
  WhyData,
  RadarData,
  ProfilesData,
  MethodologyData,
  ValidationData,
  ExperimentalAiData,
  PlayerEvidenceData,
  CompareData,
  RoleKind,
} from '@/types/submission';

const ORIGIN = import.meta.env.VITE_API_ORIGIN || 'http://localhost:8000';
const BASE = `${ORIGIN}/api/v1`;

export class ApiFailure extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function get<T>(path: string, headers: Record<string, string> = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { headers: { Accept: 'application/json', ...headers } });
  } catch {
    throw new ApiFailure('The backend could not be reached. Start the API and reload.', 0);
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      msg = body?.error?.message || msg;
    } catch {
      /* keep default message */
    }
    throw new ApiFailure(msg, res.status);
  }
  return (await res.json()) as T;
}

const qs = (o: Record<string, string | number | undefined | null>) => {
  const p = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : '';
};

export const submissionApi = {
  overview: () => get<OverviewData>('/submission/overview'),
  top10: (role: RoleKind) => get<Top10Data>(`/submission/top10/${role}`),
  player: (role: RoleKind, id: number) => get<PlayerEvidenceData>(`/submission/players/${role}/${id}`),
  why: (role: RoleKind, kind?: string, limit = 50, offset = 0) =>
    get<WhyData>(`/submission/why/${role}${qs({ kind, limit, offset })}`),
  methodology: () => get<MethodologyData>('/submission/methodology'),
  validation: () => get<ValidationData>('/submission/validation'),
  profiles: (role: RoleKind, o: { format?: string; q?: string; limit?: number; offset?: number } = {}) =>
    get<ProfilesData>(`/submission/profiles/${role}${qs({ limit: 50, ...o })}`),
  compare: (role: RoleKind, ids: number[], format?: string) =>
    get<CompareData>(`/submission/compare/${role}${qs({ player_ids: ids.join(','), format })}`),
  radar: (role: RoleKind, id: number, format: string) =>
    get<RadarData>(`/submission/radar/${role}/${id}${qs({ format })}`),
  // The token is typed by the user at runtime and is never stored or bundled.
  experimentalAi: (role: RoleKind, token: string) =>
    get<ExperimentalAiData>(`/internal/experimental-ai/${role}`, { 'X-Admin-Token': token }),
};
