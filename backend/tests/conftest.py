import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test gets its own throwaway state.json instead of touching
    backend/data/state.json on disk."""
    from app import storage

    monkeypatch.setattr(storage, "STATE_FILE", str(tmp_path / "state.json"))
    yield


@pytest.fixture
def client(monkeypatch):
    # The real scheduler spins up background threads and pushes to Telegram
    # on a timer — irrelevant noise for endpoint tests, so it's stubbed out.
    class _NullScheduler:
        def shutdown(self, wait=True):
            pass

    monkeypatch.setattr("app.main.start_scheduler", lambda: _NullScheduler())

    from app.main import app, settings

    # Tests must not depend on whatever BOTECONOMY_API_KEY happens to be set
    # in the developer's real backend/.env; tests that care about auth set
    # their own value explicitly.
    monkeypatch.setattr(settings, "api_key", "")

    with TestClient(app) as test_client:
        yield test_client
