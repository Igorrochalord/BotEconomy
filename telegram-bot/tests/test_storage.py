import storage


def test_add_ticker_success():
    ok, message = storage.add_ticker("nvda")
    assert ok is True
    assert "NVDA" in storage.get_tickers()
    assert "NVDA" in message


def test_add_ticker_appends_sa_suffix_for_five_letter_alpha_codes():
    # Mirrors B3 (Bovespa) ticker convention: 5-letter alpha codes get .SA.
    ok, _ = storage.add_ticker("abcde")
    assert ok is True
    assert "ABCDE.SA" in storage.get_tickers()


def test_add_ticker_rejects_duplicates():
    storage.add_ticker("NVDA")
    ok, message = storage.add_ticker("nvda")
    assert ok is False
    assert "já está na lista" in message


def test_remove_ticker_success():
    storage.add_ticker("NVDA")
    ok, _ = storage.remove_ticker("nvda")
    assert ok is True
    assert "NVDA" not in storage.get_tickers()


def test_remove_ticker_not_found():
    ok, message = storage.remove_ticker("ZZZZ")
    assert ok is False
    assert "não encontrado" in message


def test_alert_lifecycle():
    alert = storage.add_alert("aapl", "above", 200.0)
    assert alert["ticker"] == "AAPL"
    assert alert["triggered"] is False
    assert alert in storage.get_alerts()

    storage.mark_alert_triggered(alert["id"])
    updated = next(a for a in storage.get_alerts() if a["id"] == alert["id"])
    assert updated["triggered"] is True

    assert storage.remove_alert(alert["id"]) is True
    assert storage.remove_alert(alert["id"]) is False
