import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api';
import type { Vintage } from '../types';
import { dtShort, fmt, signed } from '../format';
import { Panel, axis, tooltipStyle } from '../components/ui';

/** Forecast evolution for one delivery day: which publications existed at the cut-off, and how good was each. */
export default function Vintages({ cutoff, days }: { cutoff: string; days: string[] }) {
  const [day, setDay] = useState(days[0] || '');
  const [v, setV] = useState<Vintage[]>([]);
  const [err, setErr] = useState('');
  useEffect(() => { if (!days.includes(day)) setDay(days[0] || ''); }, [days.join(',')]);
  useEffect(() => { if (day) api.vintages(day, cutoff).then(r => setV(r.vintages)).catch(e => setErr(e.message)); }, [day, cutoff]);
  const chart = [...v].reverse().map(x => ({ t: dtShort(x.publishTime), mae: x.mae, eligible: x.eligible }));
  return <>
    <Panel title="Forecast evolution" sub="MAE of each publication for the selected delivery day · green = available at the cut-off"
      right={<select className="dayselect" value={day} onChange={e => setDay(e.target.value)}>{days.map(d => <option key={d}>{d}</option>)}</select>}>
      {err && <div className="empty">{err}</div>}
      <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart}>
        <CartesianGrid stroke="#263849" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="t" {...axis} interval="preserveStartEnd" /><YAxis {...axis} width={48} />
        <Tooltip contentStyle={tooltipStyle} formatter={(x: any) => `${fmt(x)} MW`} />
        <Bar dataKey="mae" name="MAE (MW)">{chart.map((c, i) => <Cell key={i} fill={c.eligible ? '#45d5ae' : '#4b5d70'} />)}</Bar></BarChart></ResponsiveContainer></div></Panel>
    <div style={{ height: 16 }} />
    <Panel title="Publications for this delivery day" sub="Newest first">
      <div className="tablewrap"><table><thead><tr><th>PUBLISHED (UK)</th><th>AT CUT-OFF</th><th>HRS BEFORE CUT-OFF</th><th>AVG FORECAST</th><th>MAE</th><th>BIAS</th></tr></thead>
        <tbody>{v.slice(0, 200).map(x => <tr key={x.publishTime}><td>{dtShort(x.publishTime)}</td><td>{x.eligible ? <span className="positive">available</span> : <span className="muted">too late</span>}</td>
          <td>{fmt(x.hoursBeforeCutoff, 1)}</td><td>{fmt(x.forecastAvg)} MW</td><td>{fmt(x.mae)} MW</td><td>{signed(x.bias)}</td></tr>)}</tbody></table>
        {!v.length && !err && <div className="empty">No publications found.</div>}</div></Panel></>;
}
