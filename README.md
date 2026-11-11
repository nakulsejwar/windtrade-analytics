# WindTrade Analytics

Day-ahead wind forecast monitor for a GB energy buyer. Uses **only** national wind data from Elexon BMRS:
actuals (`FUELHH`, fuelType `WIND`) and forecasts (`WINDFOR`). React + TypeScript front end, FastAPI back end, Docker, Vercel.

**Live app:** `<paste Vercel URL here>`  ·  **Demo video:** `<paste unlisted YouTube URL here>`

## What it answers
1. **What is the latest forecast I can use when I must buy?**  *Decision view*: pick a decision day D; see the forecast for D+1 exactly as it stood at the gate-closure cut-off (latest publication ≤ cut-off), the publication times used, and the later revisions you could not yet see.
2. **How wrong can it be?**  *Accuracy analysis*: MAE, RMSE, bias, WAPE, error quantiles, error histogram, error by time of day, by lead time and by day. The Decision view overlays a P10–P90 band built from those historical errors.

Also: *Interval explorer* (half-hourly table, CSV export) and *Forecast vintages* (how the forecast for one day evolved across publications).

## Key assumptions (please review)
- **Decisions made in January 2026** → decision dates 1–31 Jan; each covers delivery on **D+1** (2 Jan – 1 Feb). Actuals/forecasts outside that are ignored.
- **Cut-off** (UK local time, D-1): defaults to 09:20 (hourly auction) and 15:30 (half-hourly auction); both are *assumed* gate closures and can be changed in the UI. A forecast is eligible only if `publishTime ≤ cut-off`; the latest eligible one is used.
- **error = forecast − actual.** Positive = wind over-forecast = more thermal power needed.
- Only forecasts published 0–72 h before delivery are kept. Demand and thermal supply are out of scope, so no total procurement gap is computed.
- The P10–P90 band uses error quantiles over the *selected window* (in-sample, so it is a guide rather than a strict out-of-sample interval).

## Run it
### Docker (recommended)
```bash
docker compose up --build        # UI http://localhost:5173 , API docs http://localhost:8000/docs
```
### Without Docker
```bash
pip install -r backend/requirements-dev.txt
uvicorn backend.app.main:app --reload --port 8000     # from repo root
cd frontend && npm install && npm run dev              # http://localhost:5173 (proxies /api to :8000)
```
### Data: create the snapshot once (needs internet)
```bash
python scripts/ingest.py     # -> backend/data/wind_2026-01.json.gz  (commit this file)
```
The API loads that snapshot if present (fast, deterministic, no Elexon calls at runtime, ideal for Vercel). If it is missing it falls back to fetching live from Elexon (chunked, retried, cached 15 min), which can be slow on serverless.
For offline UI work only: `python scripts/make_sample.py /tmp/s.json.gz` then `SNAPSHOT_PATH=/tmp/s.json.gz uvicorn …` – **synthetic data; the UI shows a warning banner.**

### Tests
```bash
pytest backend/tests -q      # analysis maths, cut-off logic, API contract
```

## Deploy on Vercel
1. Run `scripts/ingest.py` and commit `backend/data/wind_2026-01.json.gz`.
2. Push to a public GitHub repo (anonymous name), import it in Vercel with the repo root as project root.
3. `vercel.json` builds the Vite app to `frontend/dist` and rewrites `/api/*` to the Python function `api/index.py` (FastAPI, routes already prefixed `/api`).
4. Open the URL in an incognito window and check `/api/meta` shows `"dataSource":"snapshot"`.

## Layout
| Path | Purpose |
|---|---|
| `backend/app/config.py` | Window, cut-off presets, constants |
| `backend/app/elexon.py` | Elexon client (chunked, concurrent, retries) |
| `backend/app/store.py` | Snapshot loader + live fallback + cache |
| `backend/app/analysis.py` | Pure functions: vintage selection, metrics, quantiles, horizon/hour profiles, decision view |
| `backend/app/main.py` | FastAPI routes under `/api` |
| `backend/tests/` | pytest suite on a deterministic synthetic fixture |
| `scripts/ingest.py` / `make_sample.py` | Build real snapshot / synthetic dev data |
| `api/index.py`, `vercel.json` | Vercel entrypoint and routing |
| `frontend/src/` | `App.tsx` shell, `views/` (Decision, Accuracy, Explorer, Vintages), `api.ts`, `types.ts` |
| `docker-compose.yml`, `*/Dockerfile`, `frontend/nginx.conf` | Containers (nginx serves UI and proxies `/api`) |

## Known limitations / next steps
Elexon field names and query parameters follow the public API docs but were not exercised against the live API in the authoring environment (no network access) – run `scripts/ingest.py` first and check the counts it prints. Next: out-of-sample (rolling) error bands, DST-aware cut-offs beyond January, scheduled snapshot refresh, frontend tests.

## AI assistance
AI tools (ChatGPT for initial scaffolding; Claude for review, refactor, tests and README) were used. All code should be reviewed before production use.
