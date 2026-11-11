"""Pure analysis functions (no I/O) so they are easy to unit test.

Conventions
- error = forecast - actual (MW). Positive error => wind over-forecast => buyer under-procures thermal.
- A forecast is "eligible" for a delivery interval if it was published at or before the decision cutoff
  on the day before delivery (D-1, UK local time). The latest eligible publication is used.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from math import sqrt
from typing import Iterable, Optional

from .config import LONDON


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_cutoff(value: str) -> time:
    try:
        hh, mm = value.split(":")
        return time(int(hh), int(mm))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("cutoff must be HH:MM") from exc


def cutoff_for_delivery_date(delivery: date, cutoff: time) -> datetime:
    """Cutoff instant (UTC) for a delivery date: D-1 at `cutoff` UK local time."""
    local = datetime.combine(delivery - timedelta(days=1), cutoff, tzinfo=LONDON)
    return local.astimezone(timezone.utc)


def delivery_date_of(start: datetime) -> date:
    """UK-local delivery date of an interval (settlement days are UK local)."""
    return start.astimezone(LONDON).date()


class ForecastIndex:
    """Forecast vintages per target interval, sorted by publish time."""

    def __init__(self, rows: Iterable[tuple[str, str, float]], interpolate: bool = True):
        """WINDFOR is published at hourly resolution (targets on the hour only). When `interpolate` is on,
        each publication is filled onto the 30-minute grid by averaging its two neighbouring hourly values,
        so every half-hour settlement period can be compared with FUELHH. Nothing is extrapolated."""
        by_pub: dict[datetime, dict[datetime, float]] = defaultdict(dict)
        for start, publish, mw in rows:
            by_pub[parse_dt(publish)][parse_dt(start)] = float(mw)
        half = timedelta(minutes=30)
        by_target: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        for pub, series in by_pub.items():
            for s_dt, mw in series.items():
                by_target[iso(s_dt)].append((pub, mw))
                if interpolate:
                    nxt = series.get(s_dt + 2 * half)
                    mid = s_dt + half
                    if nxt is not None and mid not in series:
                        by_target[iso(mid)].append((pub, (mw + nxt) / 2))
        self.by_target = {k: sorted(v) for k, v in by_target.items()}
        self._publish_cache = {k: [p for p, _ in v] for k, v in self.by_target.items()}

    def latest_at(self, start: str, cutoff: datetime) -> Optional[tuple[datetime, float]]:
        vs = self.by_target.get(start)
        if not vs:
            return None
        i = bisect_right(self._publish_cache[start], cutoff)
        return vs[i - 1] if i else None

    def latest(self, start: str) -> Optional[tuple[datetime, float]]:
        vs = self.by_target.get(start)
        return vs[-1] if vs else None

    def vintages(self, start: str) -> list[tuple[datetime, float]]:
        return self.by_target.get(start, [])


def build_rows(actuals: dict[str, float], idx: ForecastIndex, start: date, end: date, cutoff: time) -> list[dict]:
    """One row per actual interval whose UK delivery date is in [start, end]."""
    rows = []
    for t in sorted(actuals):
        sdt = parse_dt(t)
        d = delivery_date_of(sdt)
        if not (start <= d <= end):
            continue
        cut = cutoff_for_delivery_date(d, cutoff)
        hit = idx.latest_at(t, cut)
        f = hit[1] if hit else None
        rows.append({
            "startTime": t,
            "deliveryDate": d.isoformat(),
            "actual": actuals[t],
            "forecast": f,
            "error": (f - actuals[t]) if f is not None else None,
            "publishTime": iso(hit[0]) if hit else None,
            "leadHours": round((sdt - hit[0]).total_seconds() / 3600, 2) if hit else None,
        })
    return rows


def quantile(sorted_vals: list[float], q: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def metrics(errors_actuals: list[tuple[float, float]]) -> dict:
    """errors_actuals: list of (error, actual)."""
    n = len(errors_actuals)
    if not n:
        return {"n": 0, "mae": None, "rmse": None, "bias": None, "wape": None, "maxOver": None, "maxUnder": None}
    errs = [e for e, _ in errors_actuals]
    denom = sum(abs(a) for _, a in errors_actuals)
    return {
        "n": n,
        "mae": sum(abs(e) for e in errs) / n,
        "rmse": sqrt(sum(e * e for e in errs) / n),
        "bias": sum(errs) / n,
        "wape": (sum(abs(e) for e in errs) / denom * 100) if denom else None,
        "maxOver": max(errs),
        "maxUnder": min(errs),
    }


def error_quantiles(errors: list[float]) -> dict:
    s = sorted(errors)
    return {k: quantile(s, q) for k, q in
            (("p05", .05), ("p10", .10), ("p25", .25), ("p50", .50), ("p75", .75), ("p90", .90), ("p95", .95))}


def histogram(errors: list[float], bin_mw: float = 500, limit: float = 5000) -> list[dict]:
    if not errors:
        return []
    nb = int(2 * limit / bin_mw)
    counts = [0] * nb
    for e in errors:
        i = int((max(-limit, min(limit - 1e-9, e)) + limit) // bin_mw)
        counts[i] += 1
    return [{"from": -limit + i * bin_mw, "to": -limit + (i + 1) * bin_mw, "count": c} for i, c in enumerate(counts)]


def daily(rows: list[dict]) -> list[dict]:
    g: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        g[r["deliveryDate"]].append(r)
    out = []
    for d in sorted(g):
        rs = g[d]
        sc = [r for r in rs if r["forecast"] is not None]
        m = metrics([(r["error"], r["actual"]) for r in sc])
        out.append({
            "date": d,
            "intervals": len(rs),
            "scored": len(sc),
            "actualAvg": sum(r["actual"] for r in rs) / len(rs),
            "forecastAvg": (sum(r["forecast"] for r in sc) / len(sc)) if sc else None,
            "mae": m["mae"], "bias": m["bias"], "rmse": m["rmse"],
        })
    return out


def by_time_of_day(rows: list[dict]) -> list[dict]:
    """Error profile by UK-local hour of delivery."""
    g: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for r in rows:
        if r["forecast"] is None:
            continue
        h = parse_dt(r["startTime"]).astimezone(LONDON).hour
        g[h].append((r["error"], r["actual"]))
    return [{"hour": h, **metrics(g[h])} for h in sorted(g)]


def by_horizon(actuals: dict[str, float], idx: ForecastIndex, start: date, end: date, bucket_h: int = 6,
               max_h: int = 72) -> list[dict]:
    """Accuracy of every published vintage by lead time (independent of the decision cutoff)."""
    g: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for t, a in actuals.items():
        sdt = parse_dt(t)
        if not (start <= delivery_date_of(sdt) <= end):
            continue
        for pub, mw in idx.vintages(t):
            lead = (sdt - pub).total_seconds() / 3600
            if 0 <= lead < max_h:
                g[int(lead // bucket_h)].append((mw - a, a))
    return [{"fromHours": b * bucket_h, "toHours": (b + 1) * bucket_h, **metrics(g[b])} for b in sorted(g)]


def vintage_table(actuals: dict[str, float], idx: ForecastIndex, delivery: date, cutoff: time) -> list[dict]:
    """How the forecast for one delivery day evolved across publications."""
    cut = cutoff_for_delivery_date(delivery, cutoff)
    per_pub: dict[datetime, list[tuple[float, Optional[float]]]] = defaultdict(list)
    for t in actuals:
        sdt = parse_dt(t)
        if delivery_date_of(sdt) != delivery:
            continue
        for pub, mw in idx.vintages(t):
            per_pub[pub].append((mw, actuals[t]))
    out = []
    for pub in sorted(per_pub, reverse=True):
        items = per_pub[pub]
        m = metrics([(f - a, a) for f, a in items])
        out.append({
            "publishTime": iso(pub),
            "intervals": len(items),
            "forecastAvg": sum(f for f, _ in items) / len(items),
            "mae": m["mae"], "bias": m["bias"],
            "eligible": pub <= cut,
            "hoursBeforeCutoff": round((cut - pub).total_seconds() / 3600, 2),
        })
    return out


def decision_view(actuals: dict[str, float], idx: ForecastIndex, decision: date, cutoff: time, err_q: dict) -> dict:
    """What the buyer sees on `decision` day for delivery day decision+1."""
    delivery = decision + timedelta(days=1)
    cut = cutoff_for_delivery_date(delivery, cutoff)
    # Every half-hour of the delivery day, built from the union of known targets.
    starts = sorted(t for t in set(actuals) | set(idx.by_target) if delivery_date_of(parse_dt(t)) == delivery)
    pts = []
    for t in starts:
        hit = idx.latest_at(t, cut)
        final = idx.latest(t)
        a = actuals.get(t)
        f = hit[1] if hit else None
        lo = hi = None
        if f is not None and err_q.get("p10") is not None:
            # actual = forecast - error  =>  P10..P90 of actual from P90..P10 of error
            lo = max(0.0, f - err_q["p90"])
            hi = max(0.0, f - err_q["p10"])
        pts.append({
            "startTime": t, "forecast": f, "publishTime": iso(hit[0]) if hit else None,
            "latestForecast": final[1] if final else None, "actual": a, "low": lo, "high": hi,
        })
    fvals = [p["forecast"] for p in pts if p["forecast"] is not None]
    pubs = [p["publishTime"] for p in pts if p["publishTime"]]
    return {
        "decisionDate": decision.isoformat(), "deliveryDate": delivery.isoformat(),
        "cutoffUtc": iso(cut), "points": pts,
        "summary": {
            "intervals": len(pts), "withForecast": len(fvals),
            "avgMW": sum(fvals) / len(fvals) if fvals else None,
            "minMW": min(fvals) if fvals else None, "maxMW": max(fvals) if fvals else None,
            "energyMWh": sum(fvals) * 0.5 if fvals else None,
            "vintageFrom": min(pubs) if pubs else None, "vintageTo": max(pubs) if pubs else None,
        },
    }
