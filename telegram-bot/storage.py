"""Tiny JSON-file persistence for tickers and price alerts.

The bot is single-tenant (one Telegram channel), so a JSON file is enough
and keeps it dependency-free of a database.
"""
import json
import os
import threading

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

DEFAULT_TICKERS = [
    "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "BK",
    "STT", "COF", "AXP", "DFS", "ALLY", "KEY", "FITB", "HBAN", "RF", "CMA",
]

_lock = threading.Lock()


def _default_state() -> dict:
    return {"tickers": list(DEFAULT_TICKERS), "alerts": []}


def _load() -> dict:
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
            state.setdefault("tickers", list(DEFAULT_TICKERS))
            state.setdefault("alerts", [])
            return state
    except (json.JSONDecodeError, OSError):
        return _default_state()


def _save(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_tickers() -> list[str]:
    with _lock:
        return list(_load()["tickers"])


def add_ticker(ticker: str) -> tuple[bool, str]:
    ticker = ticker.strip().upper()
    if ticker.isalpha() and len(ticker) == 5 and not ticker.endswith(".SA"):
        ticker += ".SA"
    with _lock:
        state = _load()
        if ticker in state["tickers"]:
            return False, f"Ticker {ticker} já está na lista."
        state["tickers"].append(ticker)
        _save(state)
        return True, f"Ticker {ticker} adicionado com sucesso!"


def remove_ticker(ticker: str) -> tuple[bool, str]:
    ticker = ticker.strip().upper()
    with _lock:
        state = _load()
        if ticker not in state["tickers"]:
            return False, f"Ticker {ticker} não encontrado na lista."
        state["tickers"].remove(ticker)
        _save(state)
        return True, f"Ticker {ticker} removido com sucesso!"


def get_alerts() -> list[dict]:
    with _lock:
        return list(_load()["alerts"])


def add_alert(ticker: str, condition: str, price: float) -> dict:
    with _lock:
        state = _load()
        next_id = max((a["id"] for a in state["alerts"]), default=0) + 1
        alert = {
            "id": next_id,
            "ticker": ticker.strip().upper(),
            "condition": condition,
            "price": price,
            "triggered": False,
        }
        state["alerts"].append(alert)
        _save(state)
        return alert


def remove_alert(alert_id: int) -> bool:
    with _lock:
        state = _load()
        before = len(state["alerts"])
        state["alerts"] = [a for a in state["alerts"] if a["id"] != alert_id]
        _save(state)
        return len(state["alerts"]) < before


def mark_alert_triggered(alert_id: int, triggered: bool = True) -> None:
    with _lock:
        state = _load()
        for alert in state["alerts"]:
            if alert["id"] == alert_id:
                alert["triggered"] = triggered
        _save(state)
