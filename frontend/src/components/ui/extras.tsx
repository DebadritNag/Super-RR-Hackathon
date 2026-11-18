import React from 'react';
import type { RoleKind } from '@/types/submission';
import { Btn, TableWrap, Th, Td } from './ui';
import { cn } from '@/lib/utils';
import { fmt, scrub } from '@/lib/utils';

export const RoleToggle: React.FC<{ role: RoleKind; onChange: (r: RoleKind) => void }> = ({ role, onChange }) => (
  <div role="group" aria-label="Role" className="inline-flex rounded border border-[#8d958f] overflow-hidden">
    {(['batters', 'bowlers'] as RoleKind[]).map((r) => (
      <button
        key={r}
        aria-pressed={role === r}
        onClick={() => onChange(r)}
        className={cn(
          'px-3 py-1.5 text-sm font-medium transition-colors duration-200',
          role === r ? 'bg-[#246B4B] text-white' : 'bg-white text-[#202522] hover:bg-[#eef0ec]',
        )}
      >
        {r === 'batters' ? 'Batters' : 'Bowlers'}
      </button>
    ))}
  </div>
);

export const Pager: React.FC<{ total: number; limit: number; offset: number; onChange: (o: number) => void }> = ({
  total,
  limit,
  offset,
  onChange,
}) => (
  <div className="flex items-center justify-between gap-2 mt-3 text-sm">
    <span>
      {total === 0 ? 'No rows' : `Rows ${offset + 1} to ${Math.min(offset + limit, total)} of ${total}`}
    </span>
    <div className="flex gap-2">
      <Btn disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
        Previous
      </Btn>
      <Btn disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
        Next
      </Btn>
    </div>
  </div>
);

/** Renders API rows as a table without naming any value in the source. */
export const GenericTable: React.FC<{ rows: Record<string, any>[]; columns?: string[]; max?: number }> = ({
  rows,
  columns,
  max = 60,
}) => {
  rows = scrub(rows);
  if (!rows || rows.length === 0) return <p className="text-sm text-[#4b524d]">No rows returned.</p>;
  const cols = columns ?? Object.keys(rows[0]).slice(0, 14);
  return (
    <TableWrap>
      <table className="min-w-full">
        <thead>
          <tr>
            {cols.map((c) => (
              <Th key={c}>{c.replace(/_/g, ' ')}</Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, max).map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <Td key={c}>
                  {typeof r[c] === 'object' && r[c] !== null ? JSON.stringify(r[c]) : typeof r[c] === 'number' ? fmt(r[c]) : (r[c] ?? 'unavailable').toString() || 'unavailable'}
                </Td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > max && <p className="p-2 text-xs text-[#4b524d]">Showing {max} of {rows.length} rows.</p>}
    </TableWrap>
  );
};
