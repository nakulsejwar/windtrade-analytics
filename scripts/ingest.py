#!/usr/bin/env python3
"""Download January-2026 decision data from Elexon and write a compact snapshot.

    python scripts/ingest.py            # writes backend/data/wind_2026-01.json.gz

Run this once with internet access, commit the file, then the app (incl. Vercel) needs no live calls.
"""
import asyncio
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import DECISION_MAX, DECISION_MIN  # noqa: E402
from backend.app.elexon import fetch_actuals, fetch_forecasts, snapshot_window  # noqa: E402

OUT = ROOT / "backend" / "data" / "wind_2026-01.json.gz"


async def main():
    d0, d1, p0, p1 = snapshot_window(DECISION_MIN, DECISION_MAX)
    print(f"Actuals {d0}..{d1}; forecasts published {p0:%Y-%m-%d %H:%M} .. {p1:%Y-%m-%d %H:%M} UTC")
    actuals, forecasts = await asyncio.gather(fetch_actuals(d0, d1), fetch_forecasts(p0, p1))
    print(f"{len(actuals)} actual intervals, {len(forecasts)} forecast vintages")
    if not actuals or not forecasts:
        sys.exit("No data returned - check connectivity / API parameters.")
    blob = {"meta": {"source": "snapshot", "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "datasets": ["FUELHH", "WINDFOR"]},
            "actuals": sorted(actuals.items()), "forecasts": sorted(forecasts)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(blob, fh, separators=(",", ":"))
    print(f"Wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
