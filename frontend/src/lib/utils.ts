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
