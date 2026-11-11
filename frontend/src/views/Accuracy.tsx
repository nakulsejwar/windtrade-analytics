import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, ArrowDownRight, ArrowUpRight, Zap } from 'lucide-react';
import type { Summary } from '../types';
import { fmt, mw, signed } from '../format';
import { Kpi, Metric, Panel, axis, tooltipStyle } from '../components/ui';

/** Answers need #2: how accurate are the forecasts, quantitatively, and where do they go wrong? */
export default function Accuracy({ data, cutoff }: { data: Summary; cutoff: string }) {
  const m = data.metrics, q = data.quantiles;
  const hist = data.histogram.map(b => ({ label: `${fmt((b.from + b.to) / 2)}`, count: b.count, mid: (b.from + b.to) / 2 }));
  const horizon = data.byHorizon.map(h => ({ label: `${h.fromHours}–${h.toHours}h`, mae: h.mae, bias: h.bias }));
  const hours = data.byHour.map(h => ({ hour: `${String(h.hour).padStart(2, '0')}:00`, mae: h.mae, bias: h.bias }));
  return <>
    <div className="sectionline"><div><h2>Forecast error diagnostics</h2>
      <p>{m.n.toLocaleString()} half-hours scored · decisions {data.period.decisionStart} → {data.period.decisionEnd} · cut-off {cutoff} UK</p></div></div>
    <div className="kpis">
      <Kpi title="MAE" value={mw(m.mae)} sub="Average absolute error" icon={<Activity />} />
      <Kpi title="RMSE" value={mw(m.rmse)} sub="Penalises large misses" icon={<Zap />} />
      <Kpi title="WAPE" value={m.wape == null ? '—' : `${fmt(m.wape, 1)}%`} sub="Error as % of actual wind" icon={<ArrowUpRight />} />
      <Kpi title="Bias" value={signed(m.bias)} sub={m.bias == null ? '' : m.bias > 0 ? 'Over-forecasts wind on average' : 'Under-forecasts wind on average'} icon={<ArrowDownRight />} />
    </div>
    <div className="grid2">
      <Panel title="Error distribution" sub="Half-hours by error bucket · MW (forecast − actual)" foot={<><span>P05 {fmt(q.p05 as number)} · P50 {fmt(q.p50 as number)} · P95 {fmt(q.p95 as number)} MW</span><span>Worst: {signed(m.maxOver)} / {signed(m.maxUnder)}</span></>}>
        <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={hist}>
          <CartesianGrid stroke="#263849" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="label" {...axis} interval={1} /><YAxis {...axis} width={40} />
          <Tooltip contentStyle={tooltipStyle} labelFormatter={l => `≈ ${l} MW`} />
          <Bar dataKey="count" name="Half-hours" radius={[3, 3, 0, 0]}>{hist.map((h, i) => <Cell key={i} fill={h.mid > 0 ? '#d4a65a' : '#5795ff'} />)}</Bar>
          </BarChart></ResponsiveContainer></div></Panel>
      <Panel title="Accuracy vs lead time" sub="All published vintages · MAE by hours before delivery" foot={<><span>Shows why the cut-off matters</span><span>Independent of cut-off setting</span></>}>
        <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={horizon}>
          <CartesianGrid stroke="#263849" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="label" {...axis} /><YAxis {...axis} width={44} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => `${fmt(v)} MW`} /><Bar dataKey="mae" fill="#45d5ae" name="MAE (MW)" radius={[4, 4, 0, 0]} />
          </BarChart></ResponsiveContainer></div></Panel>
    </div>
    <div className="grid2 lower">
      <Panel title="Daily MAE" sub="By delivery day · MW"><div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.daily.map(d => ({ ...d, date: d.date.slice(5) }))}>
        <CartesianGrid stroke="#263849" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="date" {...axis} interval={2} /><YAxis {...axis} width={44} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => `${fmt(v)} MW`} /><Bar dataKey="mae" fill="#d4a65a" name="MAE" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div></Panel>
      <Panel title="Error by time of day" sub="UK hour of delivery · MAE and bias (MW)"><div className="chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={hours}>
        <CartesianGrid stroke="#263849" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="hour" {...axis} interval={3} /><YAxis {...axis} width={44} /><ReferenceLine y={0} stroke="#42566a" />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => `${fmt(v)} MW`} />
        <Line dataKey="mae" stroke="#5795ff" dot={false} strokeWidth={2} name="MAE" /><Line dataKey="bias" stroke="#45d5ae" dot={false} strokeWidth={2} name="Bias" /></LineChart></ResponsiveContainer></div></Panel>
    </div>
    <div className="grid2 lower"><Panel title="Error quantiles" sub="Use these to size a safety margin"><div className="metricrows">
      <Metric label="P05 / P95" value={`${fmt(q.p05 as number)} / ${fmt(q.p95 as number)} MW`} />
      <Metric label="P10 / P90" value={`${fmt(q.p10 as number)} / ${fmt(q.p90 as number)} MW`} />
      <Metric label="P25 / P75" value={`${fmt(q.p25 as number)} / ${fmt(q.p75 as number)} MW`} />
      <Metric label="Coverage (intervals with eligible forecast)" value={`${fmt(m.coverage, 1)}%`} /></div></Panel></div>
  </>;
}
