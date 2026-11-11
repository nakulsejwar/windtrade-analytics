import type { ReactNode } from 'react';

export function Kpi({ title, value, sub, icon }: { title: string; value: string; sub: string; icon: ReactNode }) {
  return <div className="kpi"><div className="kpitop"><span>{title}</span><div className="kpiicon">{icon}</div></div><strong>{value}</strong><small>{sub}</small></div>;
}
export function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><b>{value}</b></div>;
}
export function Panel({ title, sub, right, children, foot }: { title: string; sub?: string; right?: ReactNode; children: ReactNode; foot?: ReactNode }) {
  return <div className="panel"><div className="panelhead"><div><h3>{title}</h3>{sub && <p>{sub}</p>}</div>{right}</div>{children}{foot && <div className="chartfoot">{foot}</div>}</div>;
}
export const axis = { tick: { fill: '#8394a6', fontSize: 10 }, tickLine: false, axisLine: false } as const;
export const tooltipStyle = { background: '#102333', border: '1px solid #294154', borderRadius: 10, color: '#eaf2f9' };
