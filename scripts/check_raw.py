import json, urllib.request
d = json.load(open("windfor_day.json"))
print("fields:", list(d[0].keys()))
pub = "2026-01-10T22:30:00Z"
f = {x["startTime"]: x["generation"] for x in d if x["publishTime"] == pub}
url = ("https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream"
       "?settlementDateFrom=2026-01-11&settlementDateTo=2026-01-11&fuelType=WIND")
a = {x["startTime"]: x["generation"] for x in json.load(urllib.request.urlopen(url))}
diffs = []
for t in sorted(f):
    if t in a:
        diffs.append(f[t] - a[t])
        print(t, "forecast", f[t], "actual", a[t], "diff", f[t] - a[t])
print("mean diff:", sum(diffs) / len(diffs), "n:", len(diffs))