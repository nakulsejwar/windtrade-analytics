import gzip, json, sys
from collections import Counter
from datetime import datetime
sys.path.insert(0, ".")
from backend.app.analysis import ForecastIndex, build_rows, parse_cutoff
from datetime import date

blob = json.load(gzip.open("backend/data/wind_2026-01.json.gz", "rt"))
fc = blob["forecasts"]
print("forecast rows:", len(fc), " actual rows:", len(blob["actuals"]))

per_target = Counter(r[0] for r in fc)
print("targets with any forecast:", len(per_target), "of", len(blob["actuals"]))
print("vintages per target: min", min(per_target.values()), "max", max(per_target.values()))

pub_hours = Counter(r[1][11:16] for r in fc)
print("publish times of day (top 12):", pub_hours.most_common(12))

leads = Counter(int((datetime.fromisoformat(r[0].replace("Z","+00:00")) -
                     datetime.fromisoformat(r[1].replace("Z","+00:00"))).total_seconds() // 3600 // 6 * 6) for r in fc)
print("lead-time buckets (h):", sorted(leads.items()))

idx = ForecastIndex([tuple(r) for r in fc])
actuals = {k: v for k, v in blob["actuals"]}
for c in ("09:20", "15:30"):
    rows = build_rows(actuals, idx, date(2026, 1, 2), date(2026, 2, 1), parse_cutoff(c))
    ok = sum(r["forecast"] is not None for r in rows)
    print(f"cutoff {c}: coverage {ok}/{len(rows)} = {ok/len(rows):.1%}")