# Video outline (≤10 min)
**Part 1 – Client pitch (≤5 min)**
1. 0:00 Problem: buy day-ahead before knowing wind; forecast error = cost.
2. 0:30 Decision view: pick 15 Jan, show forecast at 09:20 cut-off, publication time, P10–P90 band, amber "revisions you couldn't see".
3. 1:45 Accuracy: MAE/RMSE/WAPE/bias, error histogram, error rises with lead time → why cut-off matters.
4. 3:15 Time-of-day / daily view, vintage evolution, CSV export.
5. 4:15 Takeaway: plan on P10 wind, quantified margin; next steps.

**Part 2 – Tech review (≤5 min)**
1. Architecture: React → `/api` → FastAPI → snapshot (or live Elexon).
2. `analysis.py`: cut-off logic (D-1 UK time), `ForecastIndex` bisect for latest eligible vintage, sign convention.
3. Data: ingest script, 72 h horizon filter, snapshot vs live fallback, Vercel routing.
4. Tests (`pytest`), Docker/nginx, assumptions & limitations, AI-use disclosure.
