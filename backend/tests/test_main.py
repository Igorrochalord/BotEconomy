from unittest.mock import patch

import pandas as pd


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_tickers_returns_defaults(client):
    resp = client.get("/api/tickers")
    assert resp.status_code == 200
    assert "JPM" in resp.json()["tickers"]


def test_create_and_delete_ticker(client):
    resp = client.post("/api/tickers", json={"ticker": "NVDA"})
    assert resp.status_code == 200
    assert "NVDA" in resp.json()["tickers"]

    resp = client.delete("/api/tickers/NVDA")
    assert resp.status_code == 200
    assert "NVDA" not in resp.json()["tickers"]


def test_delete_unknown_ticker_returns_404(client):
    resp = client.delete("/api/tickers/DOESNOTEXIST")
    assert resp.status_code == 404


def test_summary_returns_stock_data(client):
    fake_positive = pd.Series({"JPM": 1.234, "GS": 0.55})
    fake_negative = pd.Series({"C": -0.5})
    fake_top = pd.Series({"JPM": 1.234})
    with patch("app.main.stocks.get_stock_data", return_value=(fake_positive, fake_negative, fake_top)):
        resp = client.get("/api/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["top_positive"]["JPM"] == 1.23  # rounded to 2 decimals
    assert body["top_negative"]["C"] == -0.5


def test_summary_502_when_stocks_module_returns_nothing(client):
    with patch("app.main.stocks.get_stock_data", return_value=(None, None, None)):
        resp = client.get("/api/summary")
    assert resp.status_code == 502


def test_volume_skips_nan_entries(client):
    volume_df = pd.DataFrame({"JPM": [100, 200], "GS": [50, float("nan")]})
    with patch("app.main.stocks.get_volume_data", return_value=volume_df):
        resp = client.get("/api/volume")

    assert resp.status_code == 200
    assert resp.json()["volume"] == {"JPM": 200}


def test_create_and_list_alerts(client):
    resp = client.post("/api/alerts", json={"ticker": "aapl", "condition": "above", "price": 200})
    assert resp.status_code == 200
    alert_id = resp.json()["alert"]["id"]

    resp = client.get("/api/alerts")
    assert any(a["id"] == alert_id for a in resp.json()["alerts"])

    resp = client.delete(f"/api/alerts/{alert_id}")
    assert resp.status_code == 200


def test_alert_rejects_invalid_condition(client):
    resp = client.post("/api/alerts", json={"ticker": "AAPL", "condition": "sideways", "price": 1})
    assert resp.status_code == 400


def test_delete_unknown_alert_returns_404(client):
    resp = client.delete("/api/alerts/999999")
    assert resp.status_code == 404


def test_write_endpoints_require_api_key_when_configured(client, monkeypatch):
    monkeypatch.setattr("app.main.settings.api_key", "secret123")

    resp = client.post("/api/tickers", json={"ticker": "TSLA"})
    assert resp.status_code == 401

    resp = client.post("/api/tickers", json={"ticker": "TSLA"}, headers={"X-API-Key": "secret123"})
    assert resp.status_code == 200
