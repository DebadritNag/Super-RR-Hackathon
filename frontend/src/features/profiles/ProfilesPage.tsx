import React, { useMemo, useState } from 'react';
import type { DescriptiveProfile, RoleKind } from '@/types/submission';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Field, Note, PageHeader, TableWrap, Th, Td, inputCls, Btn } from '@/components/ui/ui';
import { Pager } from '@/components/ui/extras';
import { useApp } from '@/context/AppContext';
import { fmt } from '@/lib/utils';

const LIMIT = 25;
const FORMAT_ORDER: Record<string, number> = { IPL: 0, T20I: 1 };

/** The API returns one row per player per format; group them so each name appears once. */
function groupByPlayer(rows: DescriptiveProfile[]): { id: number; name: string; rows: DescriptiveProfile[] }[] {
  const byId = new Map<number, { id: number; name: string; rows: DescriptiveProfile[] }>();
  for (const r of rows) {
    const id = Number(r.player_id);
    const g = byId.get(id) ?? { id, name: String(r.player_name), rows: [] };
    g.rows.push(r);
    byId.set(id, g);
  }
  const out = [...byId.values()];
  out.forEach((g) => g.rows.sort((a, b) => (FORMAT_ORDER[String(a.format)] ?? 9) - (FORMAT_ORDER[String(b.format)] ?? 9)));
  return out.sort((a, b) => a.name.localeCompare(b.name) || a.id - b.id);
}

export const ProfilesPage: React.FC<{ role: RoleKind }> = ({ role }) => {
  const [format, setFormat] = useState('');
  const [q, setQ] = useState('');
  const [offset, setOffset] = useState(0);
  const s = useApi(() => submissionApi.profilesAll(role, { format: format || undefined, q: q || undefined }), [role, format, q]);
  const players = useMemo(() => (s.data ? groupByPlayer(s.data.rows) : []), [s.data]);
  // Some names belong to two different player ids; label them so they do not look duplicated.
  const sharedNames = useMemo(() => {
    const seen = new Map<string, number>();
    players.forEach((p) => seen.set(p.name, (seen.get(p.name) ?? 0) + 1));
    return new Set([...seen].filter(([, n]) => n > 1).map(([name]) => name));
  }, [players]);
  const { openPlayerEvidence, comparison, toggleComparison, goCompare } = useApp();
  const [msg, setMsg] = useState('');
  const bat = role === 'batters';
  const selected = comparison[role];
  return (
    <div>
      <PageHeader
        title={bat ? 'Batter profiles' : 'Bowler profiles'}
        subtitle="Descriptive career totals, 2022 to 2026, one block per player with IPL and T20I shown separately. No ranks, scores or eligibility are shown here."
      />
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <Field label="Search by name" htmlFor="profile-q">
          <input id="profile-q" className={inputCls} value={q} maxLength={60} onChange={(e) => { setQ(e.target.value); setOffset(0); }} />
        </Field>
        <Field label="Format" htmlFor="profile-format">
          <select id="profile-format" className={inputCls} value={format} onChange={(e) => { setFormat(e.target.value); setOffset(0); }}>
            <option value="">IPL and T20I</option>
            <option value="IPL">IPL</option>
            <option value="T20I">T20I</option>
          </select>
        </Field>
        <Btn disabled={selected.length < 2} onClick={() => goCompare(role, selected)}>
          Compare selected ({selected.length}/4)
        </Btn>
      </div>
      {msg && <p role="status" className="text-sm mb-2 text-[#8a4410]">{msg}</p>}
      <Async state={s}>
        {() => (
          <>
            <TableWrap>
              <table className="min-w-[900px] w-full">
                <thead>
                  <tr>
                    <Th>Compare</Th>
                    <Th>Player</Th>
                    <Th>Format</Th>
                    <Th>Matches</Th>
                    <Th>{bat ? 'Balls faced' : 'Balls bowled'}</Th>
                    <Th>{bat ? 'Runs' : 'Runs conceded'}</Th>
                    <Th>{bat ? 'Dismissals' : 'Wickets'}</Th>
                    <Th>{bat ? 'Strike rate (95% CI)' : 'Economy (95% CI)'}</Th>
                    <Th>Dot-ball share</Th>
                    <Th>Sample</Th>
                  </tr>
                </thead>
                {players.slice(offset, offset + LIMIT).map((p) => (
                  <tbody key={p.id} className="border-t border-[#d8dcd7]">
                    {p.rows.map((r, i) => {
                      const lo = bat ? r.strike_rate_ci_low : r.economy_ci_low;
                      const hi = bat ? r.strike_rate_ci_high : r.economy_ci_high;
                      return (
                        <tr key={`${p.id}-${r.format}`}>
                          {i === 0 && (
                            <>
                              <Td rowSpan={p.rows.length} className="align-top">
                                <input
                                  type="checkbox"
                                  aria-label={`Select ${p.name} for comparison`}
                                  className="w-4 h-4 cursor-pointer accent-[#246B4B]"
                                  checked={selected.includes(p.id)}
                                  onChange={() => setMsg(toggleComparison(role, p.id) ? '' : 'Comparison is limited to 4 players.')}
                                />
                              </Td>
                              <Td rowSpan={p.rows.length} className="align-top">
                                <button className="cursor-pointer text-[#1b533a] underline underline-offset-2 font-medium text-left" onClick={() => openPlayerEvidence(p.id, role)}>
                                  {p.name}
                                </button>
                                {sharedNames.has(p.name) && (
                                  <span className="block text-xs text-[#4b524d]">different player, id {p.id}</span>
                                )}
                              </Td>
                            </>
                          )}
                          <Td>{r.format}</Td>
                          <Td>{fmt(r.matches_played, 0)}</Td>
                          <Td>{fmt(bat ? r.balls_faced : r.legal_balls, 0)}</Td>
                          <Td>{fmt(bat ? r.runs : r.runs_conceded, 0)}</Td>
                          <Td>{fmt(bat ? r.dismissals : r.wickets, 0)}</Td>
                          <Td>
                            {fmt(bat ? r.strike_rate : r.economy, 2)}
                            <span className="block text-xs text-[#4b524d]">
                              {lo == null ? 'interval unavailable' : `${fmt(lo, 2)} to ${fmt(hi, 2)}`}
                            </span>
                          </Td>
                          <Td>{fmt(r.dot_ball_share)}</Td>
                          <Td>{String(r.sample_sufficiency ?? 'unavailable')}</Td>
                        </tr>
                      );
                    })}
                  </tbody>
                ))}
              </table>
            </TableWrap>
            <Pager total={players.length} limit={LIMIT} offset={offset} onChange={setOffset} />
            <div className="mt-2">
              <Note>Intervals are match-cluster bootstraps of the descriptive total. Players with too few observations show the interval as unavailable.</Note>
            </div>
          </>
        )}
      </Async>
    </div>
  );
};
