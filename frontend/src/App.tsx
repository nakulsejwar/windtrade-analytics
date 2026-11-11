import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CalendarDays, CheckCircle2, ChevronDown, Download, RefreshCw, Wind, Zap } from 'lucide-react';
import { api, type Filters } from './api';
import type { Meta, Summary } from './types';
import DecisionView from './views/Decision';
import Accuracy from './views/Accuracy';
import Explorer from './views/Explorer';
import Vintages from './views/Vintages';

const TABS = [['decision', 'Decision view', '◫'], ['accuracy', 'Accuracy analysis', '◷'], ['explorer', 'Interval explorer', '⌁'], ['vintages', 'Forecast vintages', '⟲']] as const;
type Tab = typeof TABS[number][0];

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [tab, setTab] = useState<Tab>('decision');
  const [draft, setDraft] = useState<Filters>({ start: '2026-01-01', end: '2026-01-31', cutoff: '09:20' });
  const [filters, setFilters] = useState<Filters>(draft);
  const [decisionDate, setDecisionDate] = useState('2026-01-15');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.meta().then(m => {
      setMeta(m);
      const f = { start: m.decisionMin, end: m.decisionMax, cutoff: m.defaultCutoff };
      setDraft(f); setFilters(f);
    }).catch(e => { setErr(e.message); setLoading(false); });
  }, []);

  const load = useCallback(async (f: Filters) => {
    setLoading(true); setErr('');
    try { setSummary(await api.summary(f)); } catch (e: any) { setErr(e.message || 'Unable to load data'); } finally { setLoading(false); }
  }, []);
  useEffect(() => { if (meta) load(filters); }, [meta, filters, load]);

  // keep the decision date inside the selected window
  useEffect(() => {
    if (decisionDate < filters.start) setDecisionDate(filters.start);
    else if (decisionDate > filters.end) setDecisionDate(filters.end);
  }, [filters.start, filters.end]);

  const deliveryDays = useMemo(() => summary?.daily.map(d => d.date) ?? [], [summary]);
  const invalid = draft.end < draft.start;
  const title = TABS.find(t => t[0] === tab)![1];

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brandmark"><Wind size={21} /></div><div><b>windtrade</b><small>ENERGY INTELLIGENCE</small></div></div>
      <div className="workspace"><span className="pulse" /> DAY-AHEAD WIND DESK</div>
      <div className="navlabel">WORKSPACE</div>
      {TABS.map(([id, label, ic]) => <button key={id} className={`nav ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}><span>{ic}</span>{label}</button>)}
      <div className="sidebottom">
        <div className="sourcebadge"><div className="sourceicon"><Zap size={16} /></div><div><b>Elexon BMRS</b><small>FUELHH · WINDFOR</small></div><CheckCircle2 size={15} color="#40c99a" /></div>
        <div className="profile"><div className="avatar">WT</div><div><b>Trading desk</b><small>Day-ahead GB</small></div><ChevronDown size={15} /></div>
      </div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="crumb">Analytics <span>/</span> <b>{title}</b></div>
        <div className="topright"><span className="status"><i /> {meta ? (meta.dataSource === 'sample' ? 'SAMPLE DATA' : 'DATA LOADED') : 'CONNECTING'}</span>
          <button className="iconbtn" onClick={() => load(filters)} title="Refresh"><RefreshCw size={16} className={loading ? 'spin' : ''} /></button></div></header>
      <div className="content">
        {meta?.dataSource === 'sample' && <div className="banner">⚠ Synthetic sample data in use (development only) — not real Elexon figures.</div>}
        <section className="heading"><div><div className="eyebrow">GB POWER MARKET <span>•</span> NATIONAL WIND</div><h1>{title}</h1>
          <p>Know the latest wind forecast available at gate closure, and how far to trust it, before buying day-ahead power.</p></div>
          <div className="headactions"><a className="secondary" href={api.csvUrl(filters)}><Download size={15} /> Export CSV</a></div></section>
        <section className="filterbar"><div className="filtertitle"><CalendarDays size={16} /> DECISION WINDOW</div>
          <label>From <input type="date" min={meta?.decisionMin} max={meta?.decisionMax} value={draft.start} onChange={e => setDraft({ ...draft, start: e.target.value })} /></label>
          <label>To <input type="date" min={meta?.decisionMin} max={meta?.decisionMax} value={draft.end} onChange={e => setDraft({ ...draft, end: e.target.value })} /></label>
          <label>Cut-off (UK) <select value={meta?.cutoffPresets.some(p => p.value === draft.cutoff) ? draft.cutoff : 'custom'} onChange={e => e.target.value !== 'custom' && setDraft({ ...draft, cutoff: e.target.value })}>
            {meta?.cutoffPresets.map(p => <option key={p.value} value={p.value}>{p.value} · {p.label}</option>)}<option value="custom">Custom…</option></select></label>
          <label>Time <input type="time" value={draft.cutoff} onChange={e => e.target.value && setDraft({ ...draft, cutoff: e.target.value })} /></label>
          <button className="apply" disabled={invalid} onClick={() => setFilters(draft)}>Apply</button>
          <span className="filterhint">Decision made on day D covers delivery on D+1 · times in UK local</span></section>
        {err && <div className="error"><AlertTriangle size={17} /><div><b>Could not load Elexon data</b><small>{err}</small></div><button onClick={() => load(filters)}>Retry</button></div>}
        {loading && !summary ? <div className="loading"><div className="loader" />Loading Elexon data…</div> : summary && <>
          {tab === 'decision' && <DecisionView filters={filters} decisionDate={decisionDate} setDecisionDate={setDecisionDate} min={filters.start} max={filters.end} />}
          {tab === 'accuracy' && <Accuracy data={summary} cutoff={filters.cutoff} />}
          {tab === 'explorer' && <Explorer filters={filters} days={deliveryDays} />}
          {tab === 'vintages' && <Vintages cutoff={filters.cutoff} days={deliveryDays} />}
          <div className="footnote"><div><span className="dotgreen" /> Source: <b>Elexon BMRS</b> · FUELHH (actual) · WINDFOR (forecast)</div>
            <div>Dataset {summary.dataSource}{summary.dataGeneratedAt ? ` · refreshed ${new Date(summary.dataGeneratedAt).toLocaleString('en-GB', { timeZone: 'Europe/London' })}` : ''}</div></div></>}
      </div></main></div>;
}
