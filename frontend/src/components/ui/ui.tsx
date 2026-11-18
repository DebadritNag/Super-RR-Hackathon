import React from 'react';
import { Info, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ApiState } from '@/hooks/useApi';

export const PageHeader: React.FC<{ title: string; subtitle?: string; children?: React.ReactNode }> = ({
  title,
  subtitle,
  children,
}) => (
  <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
    <div className="min-w-0">
      <h1 className="text-xl sm:text-2xl font-bold text-[#202522]">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-[#4b524d] max-w-3xl">{subtitle}</p>}
    </div>
    {children}
  </div>
);

export const Card: React.FC<{ title?: string; children: React.ReactNode; className?: string }> = ({
  title,
  children,
  className,
}) => (
  <section className={cn('bg-white border border-[#d9ddd7] rounded-lg p-4', className)}>
    {title && <h2 className="text-sm font-semibold uppercase tracking-wide text-[#246B4B] mb-3">{title}</h2>}
    {children}
  </section>
);

const STATUS_STYLE: Record<string, string> = {
  VALIDATED: 'bg-[#246B4B] text-white',
  PROVISIONAL: 'bg-[#FDF3EB] text-[#8a4410] border border-[#D97736]',
  EXPLORATORY: 'bg-[#FDF3EB] text-[#8a4410] border border-[#D97736]',
  INSUFFICIENT_EVIDENCE: 'bg-[#e9ebe7] text-[#3a403c] border border-[#9aa19c]',
  DESCRIPTIVE_ONLY: 'bg-[#e9ebe7] text-[#3a403c] border border-[#9aa19c]',
  EXPERIMENTAL_NOT_VALIDATED: 'bg-[#FDF3EB] text-[#8a4410] border border-[#D97736]',
};

export const StatusPill: React.FC<{ status?: string | null }> = ({ status }) => (
  <span
    className={cn(
      'inline-block rounded px-2 py-0.5 text-xs font-semibold font-mono whitespace-nowrap',
      STATUS_STYLE[status ?? ''] ?? 'bg-[#e9ebe7] text-[#3a403c]',
    )}
  >
    {status ?? 'unavailable'}
  </span>
);

/** Plain-language meaning of each status label, shown on one line. */
const STATUS_SUMMARY: Record<string, string> = {
  VALIDATED: 'Validated ranking.',
  PROVISIONAL: 'Provisional ranking: supported, but not yet validated.',
  EXPLORATORY: 'Best-supported ordering of the data, not a statistically validated ranking.',
  INSUFFICIENT_EVIDENCE: 'Not enough evidence to rank these players.',
};

/**
 * Compact status line. The label, explanation and caveats come from the API response;
 * the explanation and caveats sit behind a "Details" toggle to keep pages clean.
 */
export const StatusBanner: React.FC<{ status: string; text?: string | null; caveats?: string[] }> = ({
  status,
  text,
  caveats,
}) => {
  const validated = status === 'VALIDATED';
  const hasDetails = Boolean(text) || (caveats?.length ?? 0) > 0;
  const summary = STATUS_SUMMARY[status] ?? '';
  return (
    <div
      role="note"
      className={cn(
        'mb-4 rounded-md border px-3 py-2 text-sm text-[#202522]',
        validated ? 'border-[#cfe3d7] bg-[#f3f8f5]' : 'border-[#f0d9c6] bg-[#fdf8f3]',
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill status={status} />
        {summary && <span className="text-[#3a403c]">{summary}</span>}
      </div>
      {hasDetails && (
        <details className="mt-1 group">
          <summary className="cursor-pointer select-none text-xs font-medium text-[#246B4B] hover:underline focus-visible:outline-2 focus-visible:outline-[#246B4B] rounded">
            Details
          </summary>
          <div className="mt-2 space-y-1 text-xs text-[#3a403c]">
            {text && <p>{text}</p>}
            {caveats && caveats.length > 0 && (
              <ul className="list-disc pl-5 space-y-0.5">
                {caveats.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            )}
          </div>
        </details>
      )}
    </div>
  );
};

export const Loading: React.FC = () => (
  <div className="flex items-center gap-2 p-6 text-sm text-[#4b524d]" role="status">
    <Loader2 className="w-4 h-4 animate-spin motion-reduce:animate-none" aria-hidden="true" /> Loading from the API...
  </div>
);

export const ErrorBox: React.FC<{ message: string }> = ({ message }) => (
  <div role="alert" className="rounded-lg border border-[#C44747] bg-[#fbeeee] p-4 text-sm text-[#7a2222]">
    {message}
  </div>
);

export function Async<T>({ state, children }: { state: ApiState<T>; children: (d: T) => React.ReactNode }) {
  if (state.loading) return <Loading />;
  if (state.error || !state.data) return <ErrorBox message={state.error ?? 'No data returned.'} />;
  return <>{children(state.data)}</>;
}

export const Note: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="flex items-start gap-2 text-xs text-[#4b524d]">
    <Info className="w-4 h-4 shrink-0 text-[#246B4B]" aria-hidden="true" />
    <span>{children}</span>
  </p>
);

export const TableWrap: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="overflow-x-auto border border-[#d9ddd7] rounded-lg bg-white">{children}</div>
);

export const Th: React.FC<{ children?: React.ReactNode; className?: string }> = ({ children, className }) => (
  <th scope="col" className={cn('px-3 py-2 text-left text-xs font-semibold text-[#3a403c] bg-[#eef0ec] whitespace-nowrap', className)}>
    {children}
  </th>
);
export const Td: React.FC<{ children?: React.ReactNode; className?: string }> = ({ children, className }) => (
  <td className={cn('px-3 py-2 text-sm border-t border-[#e5e8e3] align-top', className)}>{children}</td>
);

export const Btn: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: 'primary' | 'ghost' }> = ({
  tone = 'ghost',
  className,
  ...p
}) => (
  <button
    {...p}
    className={cn(
      'inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition-colors duration-200 disabled:opacity-50',
      tone === 'primary'
        ? 'bg-[#246B4B] text-white hover:bg-[#1b533a]'
        : 'border border-[#b9bfb9] text-[#202522] bg-white hover:bg-[#eef0ec]',
      className,
    )}
  />
);

/** Horizontal interval bar: point estimate and its interval on a shared axis. */
export const IntervalBar: React.FC<{ low: number; high: number; point: number; min: number; max: number; label: string }> = ({
  low,
  high,
  point,
  min,
  max,
  label,
}) => {
  const span = max - min || 1;
  const p = (v: number) => `${Math.min(100, Math.max(0, ((v - min) / span) * 100))}%`;
  return (
    <div
      className="relative h-3 w-full min-w-[80px] bg-[#eef0ec] rounded"
      role="img"
      aria-label={label}
      title={label}
    >
      <div className="absolute top-1 h-1 bg-[#8fb9a3] rounded" style={{ left: p(low), width: `calc(${p(high)} - ${p(low)})` }} />
      <div className="absolute top-0 h-3 w-1 bg-[#246B4B]" style={{ left: p(point) }} />
    </div>
  );
};

export const Field: React.FC<{ label: string; children: React.ReactNode; htmlFor: string }> = ({ label, children, htmlFor }) => (
  <div className="flex flex-col gap-1">
    <label htmlFor={htmlFor} className="text-xs font-semibold text-[#3a403c]">
      {label}
    </label>
    {children}
  </div>
);

export const inputCls =
  'rounded border border-[#8d958f] bg-white px-2 py-1.5 text-sm text-[#202522] transition-colors duration-200 focus:border-[#246B4B]';
