import React from 'react';
import type { RoleKind } from '@/types/submission';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Card, IntervalBar, Note, PageHeader, TableWrap, Th, Td, Btn } from '@/components/ui/ui';
import { useApp } from '@/context/AppContext';
import { fmt, pct } from '@/lib/utils';

export const Top10Page: React.FC<{ role: RoleKind }> = ({ role }) => {
  const s = useApi(() => submissionApi.top10(role), [role]);
  const { openPlayerEvidence, goCompare } = useApp();
  const title = role === 'batters' ? 'Top 10 batters under pressure' : 'Top 10 bowlers under pressure';
  return (
    <div>
      <PageHeader title={title} subtitle="Ordered list as submitted. Click a player name for the full evidence." />
      <Async state={s}>
        {(d) => {
          const lo = Math.min(...d.rows.map((r) => r.interval_low));
          const hi = Math.max(...d.rows.map((r) => r.interval_high));
          return (
            <>
              {d.list_status.shortfall && <p className="mb-3 text-sm">Shortfall: {d.list_status.shortfall}</p>}
              <TableWrap>
                <table className="min-w-[960px] w-full">
                  <thead>
                    <tr>
                      <Th>Rank</Th>
                      <Th>Player</Th>
                      <Th>Pressure score ({d.rows[0]?.score_unit ?? 'unit'})</Th>
                      <Th>95% interval</Th>
                      <Th>Pressure vs baseline</Th>
                      <Th>Pressure matches</Th>
                      <Th>Pressure deliveries</Th>
                      <Th>IPL / T20I matches</Th>
                      <Th>Top-10 inclusion prob.</Th>
                      <Th>Rank interval</Th>
                      <Th>Evidence class</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.rows.map((r) => (
                      <tr key={r.player_id} className="hover:bg-[#f3f5f1] transition-colors duration-200">
                        <Td className="font-bold">{r.rank}</Td>
                        <Td>
                          <button
                            className="text-[#1b533a] underline underline-offset-2 font-medium text-left hover:text-[#0f3b27]"
                            onClick={() => openPlayerEvidence(r.player_id, role)}
                          >
                            {r.player_name}
                          </button>
                        </Td>
                        <Td>{fmt(r.pressure_score)}</Td>
                        <Td>
                          <div className="min-w-[110px]">
                            <IntervalBar
                              low={r.interval_low}
                              high={r.interval_high}
                              point={r.pressure_score}
                              min={lo}
                              max={hi}
                              label={`${fmt(r.interval_low)} to ${fmt(r.interval_high)}`}
                            />
                            <span className="text-xs text-[#4b524d]">
                              {fmt(r.interval_low)} to {fmt(r.interval_high)} ({r.interval_flag})
                            </span>
                          </div>
                        </Td>
                        <Td className="text-xs">
                          baseline {fmt(r.normal_baseline)}
                          <br />
                          pressure {fmt(r.pressure_performance_unshrunk)}
                          <br />
                          difference {fmt(r.pressure_delta)}
                        </Td>
                        <Td>{fmt(r.pressure_matches, 0)}</Td>
                        <Td>{fmt(r.pressure_deliveries, 0)}</Td>
                        <Td>
                          {fmt(r.ipl_matches, 0)} / {fmt(r.t20i_matches, 0)}
                        </Td>
                        <Td>{pct(r.top10_inclusion_probability)}</Td>
                        <Td>
                          {fmt(r.rank_interval_low, 0)} to {fmt(r.rank_interval_high, 0)}
                        </Td>
                        <Td>{String(r.evidence_class ?? 'unavailable')}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
              <div className="mt-3 flex flex-wrap gap-2">
                <Btn onClick={() => goCompare(role, d.rows.slice(0, 4).map((r) => r.player_id))}>Compare the first four listed</Btn>
              </div>
              <div className="grid gap-4 md:grid-cols-2 mt-5">
                <Card title="How to read the uncertainty">
                  <Note>
                    The interval is a match-cluster bootstrap of the score. Rank interval and inclusion probability come from the same resampling.
                    Where rank intervals are wide, neighbouring places are not separated by the data.
                  </Note>
                </Card>
                <Card title="Basis">
                  <dl className="text-sm grid grid-cols-[150px_1fr] gap-1">
                    <dt className="text-[#4b524d]">Approach</dt>
                    <dd>{d.list_status.approach}</dd>
                    <dt className="text-[#4b524d]">Rank basis</dt>
                    <dd className="break-words">{d.list_status.rank_basis ?? 'unavailable'}</dd>
                    <dt className="text-[#4b524d]">Eligible</dt>
                    <dd>{d.list_status.n_eligible ?? 'unavailable'}</dd>
                  </dl>
                </Card>
              </div>
            </>
          );
        }}
      </Async>
    </div>
  );
};
