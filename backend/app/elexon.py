"""Elexon BMRS client: chunked, concurrent, with retries."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

import httpx

from .config import ELEXON_BASE, MAX_HORIZON_HOURS
from .analysis import parse_dt, iso

HEADERS = {"Accept": "application/json", "User-Agent": "WindTradeAnalytics/1.1"}


async def _get(client: httpx.AsyncClient, path: str, params: dict, retries: int = 3) -> list[dict]:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = await client.get(f"{ELEXON_BASE}{path}", params=params)
            r.raise_for_status()
            payload = r.json()
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                return payload.get("data") or payload.get("dataRows") or []
            return []
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
            await asyncio.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"Elexon request failed for {path}: {last}")


async def fetch_actuals(start: date, end: date) -> dict[str, float]:
    """FUELHH WIND outturn keyed by startTime (UTC ISO). `start`/`end` are settlement dates, inclusive."""
    chunks = []
    d = start
    while d <= end:
        e = min(d + timedelta(days=6), end)
        chunks.append((d, e))
        d = e + timedelta(days=1)
    out: dict[str, tuple[str, float]] = {}
    async with httpx.AsyncClient(timeout=60, headers=HEADERS) as client:
        res = await asyncio.gather(*[
            _get(client, "/datasets/FUELHH/stream",
                 {"settlementDateFrom": a.isoformat(), "settlementDateTo": b.isoformat(), "fuelType": "WIND"})
            for a, b in chunks])
    for rows in res:
        for x in rows:
            if x.get("fuelType") not in (None, "WIND") or x.get("generation") is None or not x.get("startTime"):
                continue
            key = iso(parse_dt(x["startTime"]))
            pub = x.get("publishTime") or ""
            if key not in out or pub >= out[key][0]:  # keep latest publication of a restated value
                out[key] = (pub, float(x["generation"]))
    return {k: v[1] for k, v in out.items()}


async def fetch_forecasts(pub_from: datetime, pub_to: datetime, concurrency: int = 6) -> list[tuple[str, str, float]]:
    """WINDFOR vintages published in [pub_from, pub_to), fetched in 1-day publication windows.

    Only rows with 0 <= lead < MAX_HORIZON_HOURS are kept (what a D-1 decision can use)."""
    windows = []
    t = pub_from
    while t < pub_to:
        windows.append((t, min(t + timedelta(days=1), pub_to)))
        t += timedelta(days=1)
    sem = asyncio.Semaphore(concurrency)
    kept: dict[tuple[str, str], float] = {}

    async with httpx.AsyncClient(timeout=90, headers=HEADERS) as client:
        async def one(a: datetime, b: datetime):
            async with sem:
                return await _get(client, "/datasets/WINDFOR/stream", {
                    "publishDateTimeFrom": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "publishDateTimeTo": b.strftime("%Y-%m-%dT%H:%M:%SZ")})
        res = await asyncio.gather(*[one(a, b) for a, b in windows])
    for rows in res:
        for x in rows:
            if x.get("generation") is None or not x.get("startTime") or not x.get("publishTime"):
                continue
            s, p = parse_dt(x["startTime"]), parse_dt(x["publishTime"])
            lead = (s - p).total_seconds() / 3600
            if 0 <= lead < MAX_HORIZON_HOURS:
                kept[(iso(s), iso(p))] = float(x["generation"])
    return [(s, p, v) for (s, p), v in kept.items()]


def snapshot_window(decision_start: date, decision_end: date):
    """Delivery days are decision+1; forecasts may have been published up to MAX_HORIZON before delivery."""
    delivery_start, delivery_end = decision_start + timedelta(days=1), decision_end + timedelta(days=1)
    pub_from = datetime.combine(delivery_start, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=MAX_HORIZON_HOURS)
    pub_to = datetime.combine(delivery_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    return delivery_start, delivery_end, pub_from, pub_to
