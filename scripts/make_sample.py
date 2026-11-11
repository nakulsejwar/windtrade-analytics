#!/usr/bin/env python3
"""Generate a SYNTHETIC snapshot for offline development / UI demos only (never real Elexon data).

    python scripts/make_sample.py /tmp/sample.json.gz
    SNAPSHOT_PATH=/tmp/sample.json.gz uvicorn backend.app.main:app --port 8000

The UI shows a 'sample data' banner whenever this file is in use.
"""
import gzip
import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.analysis import iso  # noqa: E402

random.seed(7)
out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/sample.json.gz")
t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
actuals, fc = [], []
wind = 6000.0
for i in range(33 * 48):
    s = t0 + timedelta(minutes=30 * i)
    wind = max(300.0, min(19000.0, wind + random.gauss(0, 220) + 40 * math.sin(i / 90)))
    actuals.append((iso(s), round(wind, 1)))
series = dict(actuals)
for s_iso, a in actuals:
    s = datetime.fromisoformat(s_iso.replace("Z", "+00:00"))
    for lead in range(1, 73):
        p = (s - timedelta(hours=lead)).replace(minute=0)
        if (s - p).total_seconds() / 3600 >= 73:
            continue
        sigma = 150 + 22 * lead
        f = max(0.0, a + random.gauss(40, sigma))
        fc.append((s_iso, iso(p), round(f, 1)))
with gzip.open(out, "wt") as fh:
    json.dump({"meta": {"source": "sample", "generatedAt": iso(datetime.now(timezone.utc))}, "actuals": actuals, "forecasts": sorted(set(fc))}, fh, separators=(",", ":"))
print("wrote", out, out.stat().st_size // 1024, "KB")
