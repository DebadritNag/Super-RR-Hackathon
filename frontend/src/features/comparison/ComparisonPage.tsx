import React, { useState } from 'react';
import type { RoleKind } from '@/types/submission';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Btn, Card, Field, Note, PageHeader, StatusBanner, TableWrap, Th, Td, inputCls } from '@/components/ui/ui';
import { RoleToggle } from '@/components/ui/extras';
import { PressureRadar } from '@/components/charts/PressureRadar';
import { useApp } from '@/context/AppContext';
import { fmt, pct } from '@/lib/utils';

const BAT: [string, string, string][] = [
  ['matches_played', 'Matches', 'matches_played'],
  ['balls_faced', 'Balls faced', 'balls_faced'],
  ['runs', 'Runs', 'balls_faced'],
  ['dismissals', 'Dismissals', 'balls_faced'],
  ['strike_rate', 'Strike rate', 'balls_faced'],
  ['balls_per_dismissal', 'Balls per dismissal', 'dismissals'],
  ['boundary_ball_share', 'Boundary ball share', 'balls_faced'],
  ['dot_ball_share', 'Dot ball share', 'balls_faced'],
  ['pp_strike_rate', 'Powerplay strike rate (balls: pp_balls)', 'pp_balls'],
  ['mid_strike_rate', 'Middle-overs strike rate (balls: mid_balls)', 'mid_balls'],
  ['death_strike_rate', 'Death-overs strike rate (balls: death_balls)', 'death_balls'],
];
const BOWL: [string, string, string][] = [
  ['matches_played', 'Matches', 'matches_played'],
  ['legal_balls', 'Balls bowled', 'legal_balls'],
  ['runs_conceded', 'Runs conceded', 'legal_balls'],
  ['wickets', 'Wickets', 'legal_balls'],
  ['economy', 'Economy', 'legal_balls'],
  ['balls_per_wicket', 'Balls per wicket', 'wickets'],
  ['boundary_conceded_share', 'Boundary conceded share', 'legal_balls'],
  ['dot_ball_share', 'Dot ball share', 'legal_balls'],
  ['pp_economy', 'Powerplay economy (balls: pp_balls)', 'pp_balls'],
  ['mid_economy', 'Middle-overs economy (balls: mid_balls)', 'mid_balls'],
  ['death_economy', 'Death-overs economy (balls: death_balls)', 'death_balls'],
];

export const ComparisonPage: React.FC = () => {
  const { comparison, setComparison, toggleComparison } = useApp();
  const [role, setRole] = useState<RoleKind>('batters');
  const [format, setFormat] = useState('IPL');
  const [q, setQ] = useState('');
  const [msg, setMsg] = useState('');
  const ids = comparison[role];
  const search = useApi(
    () => (q.trim().length >= 2 ? submissionApi.profiles(role, { q, format, limit: 8 }) : Promise.resolve(null)),
    [role, q, format],
  );
  const cmp = useApi(
    () => (ids.length >= 2 ? submissionApi.compare(role, ids, format) : Promise.resolve(null)),
    [role, format, ids.join(',')],
  );
  const radars = useApi(
    () => (ids.length >= 2 ? Promise.all(ids.map((id) => submissionApi.radar(role, id, format))) : Promise.resolve(null)),
    [role, format, ids.join(',')],
  );
  const metrics = role === 'batters' ? BAT : BOWL;

  return (
    <div>
      <PageHeader title="Player comparison" subtitle="Two to four players of the same role, one format at a time. Raw values are shown beside their denominators." />
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <RoleToggle role={role} onChange={(r) => { setRole(r); setMsg(''); }} />
        <Field label="Format" htmlFor="cmp-format">
          <select id="cmp-format" className={inputCls} value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="IPL">IPL</option>
            <option value="T20I">T20I</option>
          </select>
        </Field>
        <Field label="Find a player to add" htmlFor="cmp-q">
          <input id="cmp-q" className={inputCls} value={q} maxLength={60} onChange={(e) => setQ(e.target.value)} placeholder="Type at least 2 letters" />
        </Field>
        <Btn disabled={ids.length === 0} onClick={() => setComparison(role, [])}>Clear selection</Btn>
      </div>
      {msg && <p role="status" className="text-sm mb-2 text-[#8a4410]">{msg}</p>}
      {search.data && (
        <ul className="mb-4 flex flex-wrap gap-2" aria-label="Search results">
          {search.data.rows.map((r) => (
            <li key={`${r.player_id}-${r.format}`}>
              <Btn onClick={() => setMsg(toggleComparison(role, r.player_id) ? '' : 'Comparison is limited to 4 players.')}>
                {ids.includes(r.player_id) ? 'Remove' : 'Add'} {r.player_name}
              </Btn>
            </li>
          ))}
          {search.data.rows.length === 0 && <li className="text-sm">No player matches that name in {format}.</li>}
        </ul>
      )}
      {ids.length < 2 ? (
        <Card>
          <p className="text-sm">Select at least two {role} (currently {ids.length}). Players can also be added from the profile and Top 10 pages.</p>
        </Card>
      ) : (
        <Async state={cmp}>
          {(d) =>
            d && (
              <>
                <StatusBanner status={d.status_label} caveats={d.caveats} />
                <Card className="mb-4">
                  <p className="text-sm font-medium">{d.superiority_note}</p>
                  <p className="text-xs text-[#4b524d] mt-1">Claim status from API: {d.superiority_claim}</p>
                </Card>
                <TableWrap>
                  <table className="min-w-[600px] w-full">
                    <thead>
                      <tr>
                        <Th>Metric</Th>
                        {d.players.map((p) => (
                          <Th key={p.player_id}>{p.profiles[0]?.player_name ?? `id ${p.player_id}`}</Th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.map(([key, label, den]) => (
                        <tr key={key}>
                          <Td className="font-medium">{label}</Td>
                          {d.players.map((p) => {
                            const prof = p.profiles.find((x) => x.format === format) ?? p.profiles[0];
                            const v = prof?.[key];
                            const n = prof?.[den];
                            return (
                              <Td key={p.player_id}>
                                {fmt(v, 2)}
                                {key !== den && <span className="block text-xs text-[#4b524d]">denominator {fmt(n, 0)}</span>}
                              </Td>
                            );
                          })}
                        </tr>
                      ))}
                      <tr>
                        <Td className="font-medium">Submitted-list pressure score (95% interval)</Td>
                        {d.players.map((p) => (
                          <Td key={p.player_id}>
                            {p.submitted_list_evidence ? (
                              <>
                                {fmt(p.submitted_list_evidence.pressure_score)}
                                <span className="block text-xs text-[#4b524d]">
                                  {fmt(p.submitted_list_evidence.interval_low)} to {fmt(p.submitted_list_evidence.interval_high)}; rank{' '}
                                  {p.submitted_list_evidence.rank}; top-10 prob. {pct(p.submitted_list_evidence.top10_inclusion_probability)}
                                </span>
                              </>
                            ) : (
                              'not on the submitted list'
                            )}
                          </Td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </TableWrap>
                <Card title="Descriptive radar" className="mt-4">
                  <Async state={radars}>
                    {(rs) =>
                      rs && <PressureRadar series={rs.map((r) => ({ name: r.player_name, radar: r }))} />
                    }
                  </Async>
                </Card>
                <div className="mt-3">
                  <Note>Overlapping intervals mean the data does not separate the players on pressure performance.</Note>
                </div>
              </>
            )
          }
        </Async>
      )}
    </div>
  );
};
