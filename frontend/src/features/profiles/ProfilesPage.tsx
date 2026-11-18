import React, { useState } from 'react';
import type { RoleKind } from '@/types/submission';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Field, Note, PageHeader, TableWrap, Th, Td, inputCls, Btn } from '@/components/ui/ui';
import { Pager } from '@/components/ui/extras';
import { useApp } from '@/context/AppContext';
import { fmt } from '@/lib/utils';

const LIMIT = 25;

export const ProfilesPage: React.FC<{ role: RoleKind }> = ({ role }) => {
  const [format, setFormat] = useState('');
  const [q, setQ] = useState('');
  const [offset, setOffset] = useState(0);
  const s = useApi(() => submissionApi.profiles(role, { format: format || undefined, q: q || undefined, limit: LIMIT, offset }), [role, format, q, offset]);
  const { openPlayerEvidence, comparison, toggleComparison, goCompare } = useApp();
  const [msg, setMsg] = useState('');
  const bat = role === 'batters';
  const selected = comparison[role];
  return (
    <div>
      <PageHeader
        title={bat ? 'Batter profiles' : 'Bowler profiles'}
        subtitle="Descriptive career totals (2022 to 2025, TEST-period matches never read). No ranks, scores or eligibility are shown here."
      />
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <Field label="Search by name" htmlFor="profile-q">
          <input id="profile-q" className={inputCls} value={q} maxLength={60} onChange={(e) => { setQ(e.target.value); setOffset(0); }} />
        </Field>
        <Field label="Format" htmlFor="profile-format">
          <select id="profile-format" className={inputCls} value={format} onChange={(e) => { setFormat(e.target.value); setOffset(0); }}>
            <option value="">Both (shown separately)</option>
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
        {(d) => (
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
                <tbody>
                  {d.rows.map((r) => {
                    const lo = bat ? r.strike_rate_ci_low : r.economy_ci_low;
                    const hi = bat ? r.strike_rate_ci_high : r.economy_ci_high;
                    return (
                      <tr key={`${r.player_id}-${r.format}`}>
                        <Td>
                          <input
                            type="checkbox"
                            aria-label={`Select ${r.player_name} for comparison`}
                            className="w-4 h-4 accent-[#246B4B]"
                            checked={selected.includes(r.player_id)}
                            onChange={() => setMsg(toggleComparison(role, r.player_id) ? '' : 'Comparison is limited to 4 players.')}
                          />
                        </Td>
                        <Td>
                          <button className="text-[#1b533a] underline underline-offset-2 font-medium text-left" onClick={() => openPlayerEvidence(r.player_id, role)}>
                            {r.player_name}
                          </button>
                        </Td>
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
              </table>
            </TableWrap>
            <Pager total={d.page.total} limit={LIMIT} offset={offset} onChange={setOffset} />
            <div className="mt-2">
              <Note>Intervals are match-cluster bootstraps of the descriptive total. Players with too few observations show the interval as unavailable.</Note>
            </div>
          </>
        )}
      </Async>
    </div>
  );
};
