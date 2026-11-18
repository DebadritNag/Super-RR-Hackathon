import React, { useMemo, useState } from 'react';
import type { RoleKind, WhyRow } from '@/types/submission';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Field, Note, PageHeader, TableWrap, Th, Td, inputCls } from '@/components/ui/ui';
import { Pager, RoleToggle } from '@/components/ui/extras';
import { useApp } from '@/context/AppContext';
import { fmt } from '@/lib/utils';

const LIMIT = 25;

const GROUP_LABEL: Record<string, string> = {
  SELECTED: 'Selected',
  NEAR_MISS: 'Near miss',
  RAW_STANDOUT: 'Strong raw statistic',
  EXCLUDED: 'Excluded',
};
const GROUP_ORDER = ['SELECTED', 'NEAR_MISS', 'RAW_STANDOUT', 'EXCLUDED'];

interface PlayerReasons {
  player_id: number;
  player_name: string;
  rank: number | null;
  groups: string[];
  reasons: { code: string; detail: string }[];
  deliveries?: number;
  matches?: number;
}

/** The API returns one row per reason; show one row per player with all their reasons. */
function groupByPlayer(rows: WhyRow[]): PlayerReasons[] {
  const byId = new Map<number, PlayerReasons>();
  for (const r of rows) {
    const id = Number(r.player_id);
    let p = byId.get(id);
    if (!p) {
      p = { player_id: id, player_name: r.player_name, rank: null, groups: [], reasons: [] };
      byId.set(id, p);
    }
    const rank = Number(r.rank);
    if (rank > 0 && (p.rank === null || rank < p.rank)) p.rank = rank;
    if (!p.groups.includes(r.kind)) p.groups.push(r.kind);
    if (!p.reasons.some((x) => x.code === r.reason_code && x.detail === r.detail)) {
      p.reasons.push({ code: r.reason_code, detail: r.detail });
    }
    if (r.deliveries != null) p.deliveries = Math.max(p.deliveries ?? 0, Number(r.deliveries));
    if (r.matches != null) p.matches = Math.max(p.matches ?? 0, Number(r.matches));
  }
  const groupPos = (p: PlayerReasons) => Math.min(...p.groups.map((g) => GROUP_ORDER.indexOf(g) + 1 || 99));
  return [...byId.values()].sort(
    (a, b) =>
      groupPos(a) - groupPos(b) ||
      (a.rank ?? 1e9) - (b.rank ?? 1e9) ||
      a.player_name.localeCompare(b.player_name),
  );
}

export const WhyPage: React.FC = () => {
  const [role, setRole] = useState<RoleKind>('batters');
  const [kind, setKind] = useState('');
  const [offset, setOffset] = useState(0);
  const s = useApi(() => submissionApi.whyAll(role, kind || undefined), [role, kind]);
  const players = useMemo(() => (s.data ? groupByPlayer(s.data.rows) : []), [s.data]);
  // The API does not always send delivery and match counts; hide those columns when it sends none.
  const hasCounts = players.some((p) => p.deliveries != null || p.matches != null);
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
        {() => (
          <>
            <TableWrap>
              <table className="min-w-[760px] w-full">
                <thead>
                  <tr>
                    <Th>Player</Th>
                    <Th>Group</Th>
                    <Th>Rank</Th>
                    <Th>Reasons</Th>
                    {hasCounts && <Th>Deliveries</Th>}
                    {hasCounts && <Th>Matches</Th>}
                  </tr>
                </thead>
                <tbody>
                  {players.slice(offset, offset + LIMIT).map((p) => (
                    <tr key={p.player_id} className="align-top">
                      <Td>
                        <button className="cursor-pointer text-[#1b533a] underline underline-offset-2 font-medium text-left" onClick={() => openPlayerEvidence(p.player_id, role)}>
                          {p.player_name}
                        </button>
                      </Td>
                      <Td className="whitespace-nowrap">{p.groups.map((g) => GROUP_LABEL[g] ?? g).join(', ')}</Td>
                      <Td>{p.rank ?? 'not ranked'}</Td>
                      <Td className="min-w-[320px]">
                        {p.reasons.some((x) => x.detail) ? (
                          <ul className="space-y-1">
                            {p.reasons
                              .filter((x) => x.detail)
                              .map((x) => (
                                <li key={`${x.code}-${x.detail}`}>{x.detail}</li>
                              ))}
                          </ul>
                        ) : (
                          <span className="text-[#4b524d]">On the submitted list. Open the player for the full evidence.</span>
                        )}
                      </Td>
                      {hasCounts && <Td>{fmt(p.deliveries, 0)}</Td>}
                      {hasCounts && <Td>{fmt(p.matches, 0)}</Td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
            <Pager total={players.length} limit={LIMIT} offset={offset} onChange={setOffset} />
            <div className="mt-2">
              <Note>Open a player for the full comparison of pressure level, baseline, sample size and rank stability.</Note>
            </div>
          </>
        )}
      </Async>
    </div>
  );
};
