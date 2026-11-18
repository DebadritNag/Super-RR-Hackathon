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

/** Plain notice used where text must stay visible (experimental model output). */
export const Notice: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div role="note" className="mb-4 rounded-md border border-[#d9ddd7] bg-[#f6f7f4] px-3 py-2 text-sm text-[#3a403c]">
    {children}
  </div>
);

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
export const Td: React.FC<{ children?: React.ReactNode; className?: string; rowSpan?: number }> = ({
  children,
  className,
  rowSpan,
}) => (
  <td rowSpan={rowSpan} className={cn('px-3 py-2 text-sm border-t border-[#e5e8e3] align-top', className)}>
    {children}
  </td>
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
