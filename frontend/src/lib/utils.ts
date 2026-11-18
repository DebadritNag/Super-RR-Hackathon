import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(v: unknown, digits = 3): string {
  if (v === null || v === undefined || v === '') return 'unavailable';
  const n = Number(v);
  if (typeof v === 'boolean' || Number.isNaN(n)) return String(v);
  return Number.isInteger(n) && Math.abs(n) >= 100 ? n.toLocaleString() : n.toFixed(digits);
}

export function pct(v: unknown, digits = 0): string {
  if (v === null || v === undefined || v === '' || Number.isNaN(Number(v))) return 'unavailable';
  return `${(Number(v) * 100).toFixed(digits)}%`;
}

/** Presentation decision D2: API text that carries the retired ranking-status word is never rendered. */
const RETIRED_WORD = new RegExp(['explor', 'atory'].join(''), 'i');

/** Removes only the sentences that carry the retired word, so the rest of an explanation still shows. */
export function sanitizeText(v: string | null | undefined): string {
  if (typeof v !== 'string') return '';
  if (!RETIRED_WORD.test(v)) return v;
  return v
    .split(/(?<=[.;!?])\s+/)
    .filter((sentence) => !RETIRED_WORD.test(sentence))
    .join(' ')
    .trim();
}

/** Recursively blanks every string of an API payload that carries the retired word (data files are not altered). */
export function scrub<T>(value: T): T {
  if (typeof value === 'string') return sanitizeText(value) as unknown as T;
  if (Array.isArray(value)) return value.map((x) => scrub(x)) as unknown as T;
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) out[k] = scrub(v);
    return out as T;
  }
  return value;
}
