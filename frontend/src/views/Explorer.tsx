import { useEffect, useState } from 'react';
import { api, type Filters } from '../api';
import type { IntervalRow } from '../types';
import { dtShort, fmt, signed } from '../format';
import { Panel } from '../components/ui';

export default function Explorer({ filters, days }: { filters: Filters; days: string[] }) {
  const [day, setDay] = useState(days[0] || '');
  const [rows, setRows] = useState<IntervalRow[]>([]);
  const [err, setErr] = useState('');
  useEffect(() => { if (!days.includes(day)) setDay(days[0] || ''); }, [days.join(',')]);
  useEffect(() => { if (day) api.intervals(filters, day).then(r => setRows(r.rows)).catch(e => setErr(e.message)); }, [day, filters.cutoff, filters.start, filters.end]);
  return <Panel title="Half-hourly forecast & outturn" sub="Pick a delivery day to inspect each settlement period"
    right={<select className="dayselect" value={day} onChange={e => setDay(e.target.value)}>{days.map(d => <option key={d}>{d}</option>)}</select>}>
    {err && <div className="empty">{err}</div>}
    <div className="tablewrap"><table><thead><tr><th>DELIVERY (UK)</th><th>ACTUAL</th><th>FORECAST AT CUT-OFF</th><th>ERROR</th><th>PUBLISHED</th><th>LEAD</th></tr></thead>
      <tbody>{rows.map(r => <tr key={r.startTime}><td>{dtShort(r.startTime)}</td><td>{fmt(r.actual)} MW</td>
        <td>{r.forecast == null ? <span className="muted">No eligible vintage</span> : `${fmt(r.forecast)} MW`}</td>
        <td className={r.error == null ? 'muted' : r.error > 0 ? 'positive' : 'negative'}>{signed(r.error)}</td>
        <td>{r.publishTime ? dtShort(r.publishTime) : '—'}</td><td>{r.leadHours == null ? '—' : `${fmt(r.leadHours, 1)} h`}</td></tr>)}</tbody></table>
      {!rows.length && !err && <div className="empty">No intervals for this day.</div>}</div></Panel>;
}
