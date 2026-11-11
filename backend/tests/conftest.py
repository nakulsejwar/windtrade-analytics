import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from fastapi.testclient import TestClient

from backend.app.analysis import ForecastIndex, iso
from backend.app.main import app
from backend.app.store import Dataset, set_dataset_for_tests


def synthetic(days_from="2026-01-01", days=33):
    """Deterministic fake: actual = smooth wave; forecast published hourly = actual + known bias that shrinks with lead."""
    t0 = datetime.fromisoformat(days_from).replace(tzinfo=timezone.utc)
    actuals, fc = {}, []
    for i in range(days * 48):
        s = t0 + timedelta(minutes=30 * i)
        a = 5000 + 3000 * math.sin(i / 40)
        actuals[iso(s)] = a
        for lead in range(1, 49):          # hourly publications up to 48h ahead
            p = s - timedelta(hours=lead)
            fc.append((iso(s), iso(p), a + 10 * lead))   # error = +10 MW per lead hour
    return actuals, fc


@pytest.fixture(scope="session")
def dataset():
    a, f = synthetic()
    return Dataset(a, ForecastIndex(f), "sample", "2026-02-01T00:00:00Z", len(f))


@pytest.fixture()
def client(dataset):
    set_dataset_for_tests(dataset)
    yield TestClient(app)
    set_dataset_for_tests(None)
