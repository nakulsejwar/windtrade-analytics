def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta(client):
    j = client.get("/api/meta").json()
    assert j["decisionMin"] == "2026-01-01" and j["dataSource"] == "sample"


def test_summary_shape(client):
    j = client.get("/api/summary?start=2026-01-05&end=2026-01-12&cutoff=09:20").json()
    assert j["period"]["deliveryStart"] == "2026-01-06"          # delivery = decision + 1
    assert j["metrics"]["coverage"] == 100 and j["metrics"]["mae"] > 0
    assert len(j["daily"]) == 8 and len(j["byHour"]) == 24 and j["byHorizon"]


def test_decision_and_vintages(client):
    d = client.get("/api/decision?date=2026-01-31&cutoff=15:30").json()
    assert d["deliveryDate"] == "2026-02-01" and d["summary"]["intervals"] == 48
    v = client.get("/api/vintages?date=2026-02-01&cutoff=15:30").json()
    assert v["vintages"]


def test_validation(client):
    assert client.get("/api/summary?start=2025-12-01&end=2026-01-05").status_code == 400
    assert client.get("/api/summary?start=2026-01-10&end=2026-01-05").status_code == 400
    assert client.get("/api/summary?cutoff=abc").status_code == 400


def test_csv_export(client):
    r = client.get("/api/export.csv?start=2026-01-02&end=2026-01-02")
    assert r.status_code == 200 and r.text.splitlines()[0].startswith("startTimeUTC") and len(r.text.splitlines()) == 49
