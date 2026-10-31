import pytest
from fastapi.testclient import TestClient

import app as app_module


def test_weather_is_available_without_login(monkeypatch):
    def weather_provider_reached(*args, **kwargs):
        raise RuntimeError("weather provider reached")

    monkeypatch.setattr(
        app_module.httpx,
        "get",
        weather_provider_reached
    )

    client = TestClient(app_module.app)

    with pytest.raises(
        RuntimeError,
        match="weather provider reached"
    ):
        client.get(
            "/api/weather",
            params={"city": "Warsaw"}
        )
