import type { Decision, IntervalRow, Meta, Summary, Vintage } from './types';

const BASE = (import.meta.env.VITE_API_URL as string | undefined) || '';

async function get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
  const q = new URLSearchParams(params).toString();
  const r = await fetch(`${BASE}/api${path}${q ? `?${q}` : ''}`);
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = j.detail || msg; } catch { /* non-JSON error body */ }
    throw new Error(msg);
  }
  return r.json();
}

export interface Filters { start: string; end: string; cutoff: string }
const f = (x: Filters) => ({ start: x.start, end: x.end, cutoff: x.cutoff });

export const api = {
  meta: () => get<Meta>('/meta'),
  summary: (x: Filters) => get<Summary>('/summary', f(x)),
  decision: (date: string, x: Filters) => get<Decision>('/decision', { date, ...f(x) }),
  vintages: (date: string, cutoff: string) => get<{ vintages: Vintage[] }>('/vintages', { date, cutoff }),
  intervals: (x: Filters, delivery?: string) => get<{ rows: IntervalRow[] }>('/intervals', { ...f(x), ...(delivery ? { delivery } : {}) }),
  csvUrl: (x: Filters) => `${BASE}/api/export.csv?${new URLSearchParams(f(x))}`,
};
