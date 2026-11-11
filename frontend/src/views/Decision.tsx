import { useEffect, useState } from 'react';
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, Clock3, Gauge, Wind } from 'lucide-react';
import { api, type Filters } from '../api';
import type { Decision } from '../types';
import { dayLabel, dtShort, fmt, mw, timeOnly } from '../format';
import { Kpi, Panel, axis, tooltipStyle } from '../components/ui';

/** Answers need #1: what is the latest forecast available when I must decide, and how wrong can it be? */
export default function DecisionView({ filters, decisionDate, setDecisionDate, min, max }: {
  filters: Filters; decisionDate: string; setDecisionDate: (d: string) => void; min: string; max: string;
}) {
  const [d, setD] = useState<Decision | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    setErr('');
    api.decision(decisionDate, filters).then(setD).catch(e => setErr(e.message));
  }, [decisionDate, filters.start, filters.end, filters.cutoff]);

  const shift = (n: number) => {
    const t = new Date(decisionDate + 'T12:00:00Z'); t.setUTCDate(t.getUTCDate() + n);
    const s = t.toISOString().slice(0, 10);
    if (s >= min && s <= max) setDecisionDate(s);
  };
  if (err) return <div className="error"><div><b>Could not load decision view</b><small>{err}</small></div></div>;
  if (!d) return <div className="loading"><div className="loader" />Loading decision view…</div>;

  const s = d.summary;
  const q = d.errorQuantiles;
  const chart = d.points.map(p => ({
    t: timeOnly(p.startTime), forecast: p.forecast, actual: p.actual, latest: p.latestForecast,
    band: p.low != null && p.high != null ? [p.low, p.high] : null,
  }));
  const hasActual = d.points.some(p => p.actual != null);

  return <>
    <div className="sectionline"><div>
      <h2>Buy on {dayLabel(d.decisionDate)} → deliver {dayLabel(d.deliveryDate)}</h2>
      <p>Forecast as it stood at the {filters.cutoff} UK cut-off, i.e. the latest vintage you could actually have used.</p></div>
      <div className="daynav"><button onClick={() => shift(-1)} disabled={decisionDate <= min}>‹ Prev</button>
        <input type="date" min={min} max={max} value={decisionDate} onChange={e => e.target.value && setDecisionDate(e.target.value)} />
        <button onClick={() => shift(1)} disabled={decisionDate >= max}>Next ›</button></div></div>
    <div className="kpis">
      <Kpi title="Average forecast wind" value={mw(s.avgMW)} sub={`${fmt(s.energyMWh)} MWh over the day`} icon={<Wind />} />
      <Kpi title="Range (min – max)" value={s.minMW == null ? '—' : `${fmt(s.minMW)} – ${fmt(s.maxMW)}`} sub="MW across 48 half-hours" icon={<Activity />} />
      <Kpi title="Forecast published" value={s.vintageTo ? dtShort(s.vintageTo) : '—'} sub={s.vintageFrom && s.vintageFrom !== s.vintageTo ? `earliest vintage used ${dtShort(s.vintageFrom)}` : 'single vintage used'} icon={<Clock3 />} />
      <Kpi title="Typical error (P10–P90)" value={q.p10 == null ? '—' : `${fmt(q.p10 as number)} to ${fmt(q.p90 as number)}`} sub="MW, forecast − actual, window history" icon={<Gauge />} />
    </div>
    <Panel title="Forecast with historical error band" sub="MW · half-hourly · UK time"
      right={<span className="legend"><i className="mint" /> Forecast at cut-off <i className="band" /> P10–P90 band {hasActual && <><i className="blue" /> Actual</>}</span>}
      foot={<><span>Band = forecast adjusted by the P10/P90 of historical error ({fmt(q.p10 as number)} / {fmt(q.p90 as number)} MW) — a guide, not a guarantee.</span><span>{s.withForecast}/{s.intervals} intervals with eligible forecast</span></>}>
      <div className="chart tall"><ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chart}>
          <CartesianGrid stroke="#263849" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="t" {...axis} interval={5} /><YAxis {...axis} width={52} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => Array.isArray(v) ? `${fmt(v[0])} – ${fmt(v[1])} MW` : `${fmt(v)} MW`} />
          <Area dataKey="band" stroke="none" fill="#45d5ae" fillOpacity={0.16} name="P10–P90 band" isAnimationActive={false} />
          <Line dataKey="forecast" stroke="#45d5ae" strokeWidth={2.2} dot={false} name="Forecast at cut-off" isAnimationActive={false} />
          <Line dataKey="latest" stroke="#d4a65a" strokeWidth={1.4} strokeDasharray="4 4" dot={false} name="Latest update (after cut-off)" isAnimationActive={false} />
          {hasActual && <Line dataKey="actual" stroke="#5795ff" strokeWidth={2} dot={false} name="Actual" isAnimationActive={false} />}
          <Legend wrapperStyle={{ fontSize: 11, color: '#8394a6' }} />
        </ComposedChart></ResponsiveContainer></div>
    </Panel>
    <div className="grid2 lower">
      <Panel title="How to use this" sub="Reading the chart for procurement">
        <div className="metricrows">
          <div className="metric"><span>Planning value</span><b>Use the green line as expected wind</b></div>
          <div className="metric"><span>Downside case (P10)</span><b>{mw(d.points.length ? Math.min(...d.points.filter(p => p.low != null).map(p => p.low as number)) : null)} min low</b></div>
          <div className="metric"><span>Dashed amber line</span><b>Revisions you could not yet see</b></div>
        </div></Panel>
      <div className="panel insight"><div className="insighticon"><Gauge size={19} /></div><div><span className="eyebrow">TRADING CONTEXT</span>
        <h3>Wind shortfall risk is one-sided for a buyer</h3>
        <p>Positive error = wind over-forecast = more thermal power needed. Plan for the P10 wind case if you want to avoid buying short. This tool covers wind only; demand and other supply are outside this pilot's scope.</p></div></div>
    </div>
  </>;
}
