# WindTrade Analytics

Day-ahead wind forecast monitor for a GB energy buyer. Uses **only** national wind data from Elexon BMRS:
actuals (`FUELHH`, fuelType `WIND`) and forecasts (`WINDFOR`). React + TypeScript front end, FastAPI (Python) back end, Docker, deployed on Vercel.

**Live app:** https://windtrade-analytics.vercel.app

## What it answers
1. **What is the latest forecast I can use when I must buy?**  *Decision view*: pick a decision day D; see the forecast for D+1 exactly as it stood at the gate-closure cut-off (latest publication ≤ cut-off), the publication time used, and the later revisions that could not yet be seen.
2. **How wrong can it be?**  *Accuracy analysis*: MAE, RMSE, bias, WAPE, error quantiles, error histogram, error by time of day, by lead time and by day. The Decision view overlays a P10–P90 band built from those historical errors.

Also: *Interval explorer* (half-hourly table, CSV export) and *Forecast vintages* (how the forecast for one delivery day evolved across publications).

## Key assumptions (please review)
- **Decisions made in January 2026** → decision dates 1–31 Jan; each covers delivery on **D+1** (2 Jan – 1 Feb). Data outside that is ignored.
- **Cut-off** (UK local time, D-1): defaults to 09:20 (hourly auction) and 15:30 (half-hourly auction). These are *assumed* gate closures and can be changed in the UI. A forecast is eligible only if `publishTime ≤ cut-off`; the latest eligible one is used.
- **error = forecast − actual.** Positive = wind over-forecast = more thermal power needed.
- Only forecasts published 0–72 h before delivery are kept. Demand and thermal supply are out of scope, so no total procurement gap is computed.
- The P10–P90 band uses error quantiles over the *selected window* (in-sample), so it is a guide rather than a strict out-of-sample interval.

## Data findings (January 2026)
- **WINDFOR is hourly and published about 8 times a day** (02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC, plus an occasional ad-hoc update), while FUELHH is half-hourly. Each publication is filled onto the 30-minute grid by averaging its two neighbouring hourly values (never extrapolated), so accuracy figures on the in-between half-hours are slightly flattering.
- **The cut-off matters:** the 09:30 publication arrives after a 09:20 cut-off, so a 09:20 decision uses the 07:30 publication; a 15:30 cut-off can use the 15:30 one.
- **The forecast over-predicts wind.** The median error is about +1,478 MW; MAE is roughly 1,600 MW for 0–6 h lead time, rising to about 2,300 MW at 66–72 h. This was confirmed against the raw Elexon responses without any application code (`scripts/check_raw.py`). The cause is unknown: WINDFOR returns only `dataset`, `publishTime`, `startTime` and `generation`. A buyer using the raw forecast would systematically under-buy thermal power, which is why the app shows the quantified error band.

## Run it
### Docker (recommended)
```bash
docker compose up --build        # UI http://localhost:5173 , API docs http://localhost:8000/docs
```
### Without Docker
```bash
# from the repository root
python -m venv .venv
source .venv/bin/activate                # Windows: .venv\Scripts\activate
pip install -r backend/requirements-dev.txt
python -m uvicorn backend.app.main:app --reload --port 8000

# second terminal
cd frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api to :8000)
```
### Data: create the snapshot once (needs internet)
```bash
python scripts/ingest.py     # -> backend/data/wind_2026-01.json.gz  (already committed)
```
The API loads this snapshot if present (fast, deterministic, no Elexon calls at runtime, ideal for Vercel). If it is missing, it falls back to fetching live from Elexon (chunked, retried, cached for 15 minutes), which can be slow on serverless.
For offline UI work only: `python scripts/make_sample.py /tmp/s.json.gz`, then run the API with `SNAPSHOT_PATH=/tmp/s.json.gz` – **synthetic data; the UI shows a warning banner.**

### Tests and data checks
```bash
python -m pytest backend/tests -q        # 15 tests: analysis maths, cut-off logic, interpolation, API contract
python scripts/inspect_snapshot.py       # data quality: rows, vintages per target, publish times, cut-off coverage
```

## Deploy on Vercel
1. Run `scripts/ingest.py` and commit `backend/data/wind_2026-01.json.gz`.
2. Push to a public GitHub repo and import it in Vercel with the repository root as the project root. Preset: **Other**; no environment variables. Vercel may show a "possible configuration mismatch" warning because it detects FastAPI; ignore it, as `vercel.json` defines the build.
3. `vercel.json` builds the Vite app to `frontend/dist` and rewrites `/api/*` to the Python function `api/index.py` (FastAPI, routes already prefixed `/api`).
4. Check `/api/meta` shows `"dataSource":"snapshot"`.

## Repository layout
| Path | Purpose |
|---|---|
| `backend/app/config.py` | Analysis window, cut-off presets, constants |
| `backend/app/elexon.py` | Elexon client (chunked, concurrent, retries) |
| `backend/app/store.py` | Snapshot loader, live fallback, cache |
| `backend/app/analysis.py` | Pure functions: vintage selection, interpolation, metrics, quantiles, lead-time and time-of-day profiles, decision view |
| `backend/app/main.py` | FastAPI routes under `/api` |
| `backend/tests/` | pytest suite on a deterministic synthetic fixture |
| `backend/data/wind_2026-01.json.gz` | Snapshot of real FUELHH + WINDFOR data used by the app |
| `scripts/ingest.py` | Download Elexon data and build the snapshot |
| `scripts/inspect_snapshot.py` | Data-quality report on the snapshot |
| `scripts/check_raw.py` | Compares raw WINDFOR and FUELHH values with no application code |
| `scripts/make_sample.py` | Synthetic data for offline development only |
| `api/index.py`, `vercel.json` | Vercel entrypoint and routing |
| `frontend/src/` | `App.tsx` shell, `views/` (Decision, Accuracy, Explorer, Vintages), `components/`, `api.ts`, `types.ts` |
| `docker-compose.yml`, `*/Dockerfile`, `frontend/nginx.conf` | Containers (nginx serves the UI and proxies `/api`) |

## Known limitations / next steps
- Error bands are in-sample (computed on the selected window), not out-of-sample.
- The 09:20 and 15:30 cut-offs are assumptions; cut-offs use UK local time, but only January was tested.
- Half-hour forecast values are interpolated from hourly publications.
- The snapshot is static; a scheduled refresh would be needed beyond this pilot.
- Next: rolling out-of-sample error bands, an optional bias-corrected forecast, frontend tests.

## AI assistance
AI tools were used in building this project: Claude (Anthropic) for review, refactoring, new features, tests, debugging and this documentation, and an AI assistant for the initial scaffold. All code was run and checked against real Elexon data; it should still be reviewed before production use.
