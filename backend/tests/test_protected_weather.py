from fastapi.testclient import TestClient

import app as app_module


def test_weather_requires_bearer_token(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError(
            "Weather provider should not be called "
            "for an unauthenticated request"
        )

    monkeypatch.setattr(
        app_module.httpx,
        "get",
        fail_if_called
    )

    client = TestClient(app_module.app)

    response = client.get(
        "/api/weather",
        params={"city": "Warsaw"}
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
