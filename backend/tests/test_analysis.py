from datetime import date, time, datetime, timezone

import pytest

from backend.app import analysis as an


def test_cutoff_is_d_minus_1_uk_time():
    # January: UK == UTC
    assert an.cutoff_for_delivery_date(date(2026, 1, 10), time(9, 20)) == datetime(2026, 1, 9, 9, 20, tzinfo=timezone.utc)
    # BST: 09:20 UK == 08:20 UTC
    assert an.cutoff_for_delivery_date(date(2026, 7, 10), time(9, 20)) == datetime(2026, 7, 9, 8, 20, tzinfo=timezone.utc)


def test_latest_eligible_vintage_respects_cutoff(dataset):
    idx = dataset.index
    cut = an.cutoff_for_delivery_date(date(2026, 1, 10), time(9, 20))
    pub, _ = idx.latest_at("2026-01-10T12:00:00Z", cut)
    assert pub <= cut and (cut - pub).total_seconds() < 3600   # hourly publications -> within the last hour
    # interval so early that nothing was published before cutoff
    assert idx.latest_at("2026-01-09T10:00:00Z", cut) is None or idx.latest_at("2026-01-09T10:00:00Z", cut)[0] <= cut


def test_metrics_known_values():
    m = an.metrics([(10, 100), (-30, 100), (20, 100)])
    assert m["n"] == 3
    assert m["mae"] == pytest.approx(20)
    assert m["bias"] == pytest.approx(0)
    assert m["rmse"] == pytest.approx(((100 + 900 + 400) / 3) ** 0.5)
    assert m["wape"] == pytest.approx(20.0)
    assert an.metrics([])["mae"] is None


def test_quantile_interpolates():
    assert an.quantile([0, 10], 0.5) == 5
    assert an.quantile([], .5) is None


def test_build_rows_sign_convention(dataset):
    rows = an.build_rows(dataset.actuals, dataset.index, date(2026, 1, 10), date(2026, 1, 10), time(9, 20))
    assert len(rows) == 48
    r = rows[20]
    assert r["error"] == pytest.approx(r["forecast"] - r["actual"])
    assert r["error"] > 0                       # synthetic forecast always over-forecasts
    assert r["leadHours"] >= 0


def test_decision_view_band_and_no_lookahead(dataset):
    q = an.error_quantiles([100.0] * 10)
    v = an.decision_view(dataset.actuals, dataset.index, date(2026, 1, 9), time(9, 20), q)
    assert v["deliveryDate"] == "2026-01-10"
    p = v["points"][10]
    assert p["low"] == pytest.approx(p["forecast"] - 100) or p["low"] == 0
    assert datetime.fromisoformat(p["publishTime"].replace("Z", "+00:00")) <= datetime.fromisoformat(v["cutoffUtc"].replace("Z", "+00:00"))


def test_horizon_error_grows_with_lead(dataset):
    h = an.by_horizon(dataset.actuals, dataset.index, date(2026, 1, 5), date(2026, 1, 20))
    maes = [x["mae"] for x in h]
    assert maes == sorted(maes)


def test_vintage_table_flags_eligibility(dataset):
    t = an.vintage_table(dataset.actuals, dataset.index, date(2026, 1, 10), time(9, 20))
    assert any(x["eligible"] for x in t) and any(not x["eligible"] for x in t)
    assert all(x["eligible"] == (x["hoursBeforeCutoff"] >= 0) for x in t)
