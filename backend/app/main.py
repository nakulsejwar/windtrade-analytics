"""WindTrade Analytics API. All routes live under /api so local, Docker and Vercel share one URL scheme."""
from __future__ import annotations

import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import analysis as an
from .config import CUTOFF_PRESETS, DECISION_MAX, DECISION_MIN, DEFAULT_CUTOFF
from .store import get_dataset

app = FastAPI(title="WindTrade Analytics API", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
api = APIRouter(prefix="/api")


def _check_range(start: date, end: date):
    if end < start:
        raise HTTPException(400, "end must be on or after start")
    if start < DECISION_MIN or end > DECISION_MAX:
        raise HTTPException(400, f"Decision dates must be within {DECISION_MIN} .. {DECISION_MAX}")


def _cutoff(value: str):
    try:
        return an.parse_cutoff(value)
    except ValueError as e:
        raise HTTPException(400, str(e))


async def _dataset():
    try:
        return await get_dataset()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Could not load Elexon data: {e}")


def _delivery_range(start: date, end: date):
    return start + timedelta(days=1), end + timedelta(days=1)


@api.get("/health")
async def health():
    return {"status": "ok"}


@api.get("/meta")
async def meta():
    ds = await _dataset()
    return {
        "decisionMin": DECISION_MIN.isoformat(), "decisionMax": DECISION_MAX.isoformat(),
        "cutoffPresets": [{"value": k, "label": v} for k, v in CUTOFF_PRESETS.items()],
        "defaultCutoff": DEFAULT_CUTOFF,
        "dataSource": ds.source, "dataGeneratedAt": ds.generated_at,
        "actualIntervals": len(ds.actuals), "forecastRecords": ds.forecast_rows,
    }


@api.get("/summary")
async def summary(start: date = Query(DECISION_MIN), end: date = Query(DECISION_MAX), cutoff: str = Query(DEFAULT_CUTOFF)):
    """Accuracy of the decision-eligible forecast for decisions made in [start, end] (delivery = decision + 1)."""
    _check_range(start, end)
    ds, cut = await _dataset(), _cutoff(cutoff)
    d0, d1 = _delivery_range(start, end)
    rows = an.build_rows(ds.actuals, ds.index, d0, d1, cut)
    scored = [r for r in rows if r["forecast"] is not None]
    errs = [r["error"] for r in scored]
    return {
        "period": {"decisionStart": start.isoformat(), "decisionEnd": end.isoformat(),
                   "deliveryStart": d0.isoformat(), "deliveryEnd": d1.isoformat(), "cutoff": cutoff},
        "metrics": {**an.metrics([(r["error"], r["actual"]) for r in scored]),
                    "actualIntervals": len(rows), "coverage": (len(scored) / len(rows) * 100) if rows else 0},
        "quantiles": an.error_quantiles(errs),
        "histogram": an.histogram(errs),
        "daily": an.daily(rows),
        "byHour": an.by_time_of_day(rows),
        "byHorizon": an.by_horizon(ds.actuals, ds.index, d0, d1),
        "dataSource": ds.source, "dataGeneratedAt": ds.generated_at,
    }


@api.get("/decision")
async def decision(date_: date = Query(..., alias="date"), start: date = Query(DECISION_MIN), end: date = Query(DECISION_MAX),
                   cutoff: str = Query(DEFAULT_CUTOFF)):
    """Forecast available on decision day `date` for delivery day date+1, with an empirical error band."""
    _check_range(date_, date_)
    _check_range(start, end)
    ds, cut = await _dataset(), _cutoff(cutoff)
    d0, d1 = _delivery_range(start, end)
    rows = an.build_rows(ds.actuals, ds.index, d0, d1, cut)
    q = an.error_quantiles([r["error"] for r in rows if r["error"] is not None])
    return {**an.decision_view(ds.actuals, ds.index, date_, cut, q), "errorQuantiles": q, "cutoff": cutoff}


@api.get("/vintages")
async def vintages(date_: date = Query(..., alias="date"), cutoff: str = Query(DEFAULT_CUTOFF)):
    """Forecast evolution for one DELIVERY day across all kept publications."""
    ds, cut = await _dataset(), _cutoff(cutoff)
    if not (DECISION_MIN + timedelta(days=1) <= date_ <= DECISION_MAX + timedelta(days=1)):
        raise HTTPException(400, "delivery date outside analysis window")
    return {"deliveryDate": date_.isoformat(), "cutoff": cutoff, "vintages": an.vintage_table(ds.actuals, ds.index, date_, cut)}


@api.get("/intervals")
async def intervals(start: date = Query(DECISION_MIN), end: date = Query(DECISION_MAX), cutoff: str = Query(DEFAULT_CUTOFF),
                    delivery: date | None = Query(None)):
    _check_range(start, end)
    ds, cut = await _dataset(), _cutoff(cutoff)
    d0, d1 = _delivery_range(start, end)
    if delivery:
        d0 = d1 = delivery
    return {"rows": an.build_rows(ds.actuals, ds.index, d0, d1, cut)}


@api.get("/export.csv")
async def export_csv(start: date = Query(DECISION_MIN), end: date = Query(DECISION_MAX), cutoff: str = Query(DEFAULT_CUTOFF)):
    _check_range(start, end)
    ds, cut = await _dataset(), _cutoff(cutoff)
    d0, d1 = _delivery_range(start, end)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["startTimeUTC", "deliveryDateUK", "actualMW", "forecastMW", "errorMW_forecast_minus_actual", "forecastPublishTimeUTC", "leadHours"])
    for r in an.build_rows(ds.actuals, ds.index, d0, d1, cut):
        w.writerow([r["startTime"], r["deliveryDate"], r["actual"], "" if r["forecast"] is None else r["forecast"],
                    "" if r["error"] is None else round(r["error"], 3), r["publishTime"] or "", r["leadHours"] if r["leadHours"] is not None else ""])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="windtrade-decisions-{start}_{end}-cutoff{cutoff.replace(":", "")}.csv"'})


app.include_router(api)
