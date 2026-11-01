import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import app
from auth import hash_password
from database import create_db_and_tables, create_db_engine, get_session
from models import User


TEST_SECRET = "test-secret-key-for-weather-app-at-least-32-bytes"


def create_client(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.delenv("VERCEL_ENV", raising=False)

    database_path = tmp_path / "refresh-session.db"
    test_engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(test_engine)

    with Session(test_engine) as session:
        session.add(
            User(
                username="yura",
                hashed_password=hash_password("StrongPassword123"),
                preferred_city="Warsaw",
            )
        )
        session.commit()

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    return TestClient(app)


def login(client):
    return client.post(
        "/api/token",
        data={
            "username": "yura",
            "password": "StrongPassword123",
        },
    )


def test_login_sets_30_day_refresh_cookie(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)

    try:
        response = login(client)

        assert response.status_code == 200

        cookie = response.headers.get("set-cookie", "").lower()

        assert "refresh_token=" in cookie
        assert "httponly" in cookie
        assert "samesite=lax" in cookie
        assert "max-age=2592000" in cookie
    finally:
        app.dependency_overrides.clear()


def test_refresh_returns_new_access_token(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)

    try:
        login_response = login(client)
        assert login_response.status_code == 200

        response = client.post("/api/refresh")

        assert response.status_code == 200

        data = response.json()
        assert data["token_type"] == "bearer"
        assert data["access_token"]

        payload = jwt.decode(
            data["access_token"],
            TEST_SECRET,
            algorithms=["HS256"],
        )

        assert payload["sub"] == "yura"
        assert payload["type"] == "access"

        cookie = response.headers.get("set-cookie", "").lower()
        assert "refresh_token=" in cookie
        assert "max-age=2592000" in cookie

    finally:
        app.dependency_overrides.clear()


def test_refresh_requires_refresh_cookie(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)

    try:
        response = client.post("/api/refresh")

        assert response.status_code == 401

    finally:
        app.dependency_overrides.clear()


def test_logout_clears_refresh_cookie(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)

    try:
        login_response = login(client)
        assert login_response.status_code == 200
        assert client.cookies.get("refresh_token")

        response = client.post("/api/logout")

        assert response.status_code == 200
        assert response.json() == {"message": "Logged out"}

        cookie = response.headers.get("set-cookie", "").lower()

        assert "refresh_token=" in cookie
        assert "max-age=0" in cookie
        assert client.cookies.get("refresh_token") is None

    finally:
        app.dependency_overrides.clear()
