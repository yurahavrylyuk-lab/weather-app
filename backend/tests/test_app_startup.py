import app as app_module

from fastapi.testclient import TestClient


def test_app_startup_initializes_database(monkeypatch):
    calls = []

    monkeypatch.setattr(
        app_module,
        "create_db_and_tables",
        lambda: calls.append(True),
        raising=False
    )

    with TestClient(app_module.app):
        pass

    assert calls == [True]
