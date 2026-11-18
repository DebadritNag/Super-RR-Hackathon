import React, { useState } from 'react';
import type { RoleKind } from '@/types/submission';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Field, Note, PageHeader, TableWrap, Th, Td, inputCls } from '@/components/ui/ui';
import { Pager, RoleToggle } from '@/components/ui/extras';
import { useApp } from '@/context/AppContext';
import { fmt } from '@/lib/utils';

const LIMIT = 25;

export const WhyPage: React.FC = () => {
  const [role, setRole] = useState<RoleKind>('batters');
  const [kind, setKind] = useState('');
  const [offset, setOffset] = useState(0);
  const s = useApi(() => submissionApi.why(role, kind || undefined, LIMIT, offset), [role, kind, offset]);
  const { openPlayerEvidence } = useApp();
  return (
    <div>
      <PageHeader
        title="Why selected / why not selected"
        subtitle="Data-based reasons for each listed player, near misses and players with strong raw statistics who are not listed. A missing place is never a statement that a player is poor."
      />
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <RoleToggle role={role} onChange={(r) => { setRole(r); setOffset(0); }} />
        <Field label="Group" htmlFor="why-kind">
          <select id="why-kind" className={inputCls} value={kind} onChange={(e) => { setKind(e.target.value); setOffset(0); }}>
            <option value="">All</option>
            <option value="SELECTED">Selected</option>
            <option value="NEAR_MISS">Near miss</option>
            <option value="RAW_STANDOUT">Strong raw statistic, not selected</option>
          </select>
        </Field>
      </div>
      <Async state={s}>
        {(d) => (
          <>
            <TableWrap>
              <table className="min-w-[760px] w-full">
                <thead>
                  <tr>
                    <Th>Player</Th>
                    <Th>Group</Th>
                    <Th>Rank</Th>
                    <Th>Reason code</Th>
                    <Th>Detail</Th>
                    <Th>Deliveries</Th>
                    <Th>Matches</Th>
                  </tr>
                </thead>
                <tbody>
                  {d.rows.map((r, i) => (
                    <tr key={`${r.player_id}-${r.reason_code}-${i}`}>
                      <Td>
                        <button className="text-[#1b533a] underline underline-offset-2 font-medium text-left" onClick={() => openPlayerEvidence(r.player_id, role)}>
                          {r.player_name}
                        </button>
                      </Td>
                      <Td>{r.kind}</Td>
                      <Td>{r.rank ? r.rank : 'not ranked'}</Td>
                      <Td className="font-mono text-xs">{r.reason_code}</Td>
                      <Td className="min-w-[260px]">{r.detail}</Td>
                      <Td>{fmt(r.deliveries, 0)}</Td>
                      <Td>{fmt(r.matches, 0)}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
            <Pager total={d.page.total} limit={LIMIT} offset={offset} onChange={setOffset} />
            <div className="mt-2">
              <Note>Open a player for the full comparison of pressure level, baseline, sample size and rank stability.</Note>
            </div>
          </>
        )}
      </Async>
    </div>
  );
};
