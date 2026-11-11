"""Data access: prefer a committed snapshot (fast, deterministic); fall back to live Elexon fetch (cached)."""
from __future__ import annotations

import asyncio
import gzip
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .analysis import ForecastIndex
from .config import DECISION_MAX, DECISION_MIN
from .elexon import fetch_actuals, fetch_forecasts, snapshot_window

SNAPSHOT_PATH = Path(os.getenv("SNAPSHOT_PATH", Path(__file__).resolve().parents[1] / "data" / "wind_2026-01.json.gz"))
LIVE_TTL_SECONDS = 15 * 60


@dataclass
class Dataset:
    actuals: dict[str, float]
    index: ForecastIndex
    source: str            # "snapshot" | "live" | "sample"
    generated_at: str | None
    forecast_rows: int


_cache: Dataset | None = None
_cache_time = 0.0
_lock = asyncio.Lock()


def load_snapshot(path: Path = SNAPSHOT_PATH) -> Dataset | None:
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        blob = json.load(fh)
    rows = [tuple(r) for r in blob["forecasts"]]
    return Dataset({k: float(v) for k, v in blob["actuals"]}, ForecastIndex(rows),
                   blob.get("meta", {}).get("source", "snapshot"), blob.get("meta", {}).get("generatedAt"), len(rows))


async def load_live() -> Dataset:
    from datetime import datetime, timezone
    d_start, d_end, pub_from, pub_to = snapshot_window(DECISION_MIN, DECISION_MAX)
    actuals, forecasts = await asyncio.gather(fetch_actuals(d_start, d_end), fetch_forecasts(pub_from, pub_to))
    return Dataset(actuals, ForecastIndex(forecasts), "live",
                   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), len(forecasts))


async def get_dataset() -> Dataset:
    global _cache, _cache_time
    async with _lock:
        if _cache and (_cache.source != "live" or time.time() - _cache_time < LIVE_TTL_SECONDS):
            return _cache
        snap = load_snapshot()
        _cache = snap if snap else await load_live()
        _cache_time = time.time()
        return _cache


def set_dataset_for_tests(ds: Dataset | None):
    global _cache, _cache_time
    _cache, _cache_time = ds, time.time()
