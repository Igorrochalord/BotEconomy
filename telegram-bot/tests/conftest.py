import os

# bot.py reads this at import time; tests never talk to the real Telegram API.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

import pytest


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test gets its own throwaway state.json instead of touching
    telegram-bot/data/state.json on disk."""
    import storage

    monkeypatch.setattr(storage, "STATE_FILE", str(tmp_path / "state.json"))
    yield
