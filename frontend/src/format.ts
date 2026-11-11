export const fmt = (n: number | null | undefined, d = 0) =>
  n == null ? '—' : n.toLocaleString('en-GB', { maximumFractionDigits: d, minimumFractionDigits: d });
export const mw = (n: number | null | undefined, d = 0) => (n == null ? '—' : `${fmt(n, d)} MW`);
export const signed = (n: number | null | undefined, d = 0) => (n == null ? '—' : `${n > 0 ? '+' : ''}${fmt(n, d)} MW`);
const LON = 'Europe/London';
export const dtShort = (s: string) => new Date(s).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: LON });
export const timeOnly = (s: string) => new Date(s).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: LON });
export const dayLabel = (iso: string) => new Date(iso + 'T12:00:00Z').toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
