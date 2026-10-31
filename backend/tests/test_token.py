import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import app
from auth import hash_password
from database import create_db_and_tables, create_db_engine, get_session
from models import User


def test_token_endpoint_returns_bearer_jwt(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-for-weather-app-at-least-32-bytes"
    )

    database_path = tmp_path / "token.db"
    test_engine = create_db_engine(
        f"sqlite:///{database_path}"
    )
    create_db_and_tables(test_engine)

    with Session(test_engine) as session:
        user = User(
            username="yura",
            hashed_password=hash_password("StrongPassword123")
        )
        session.add(user)
        session.commit()

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        response = client.post(
            "/api/token",
            data={
                "username": "yura",
                "password": "StrongPassword123"
            }
        )

        assert response.status_code == 200

        data = response.json()

        assert data["token_type"] == "bearer"
        assert data["access_token"]

        payload = jwt.decode(
            data["access_token"],
            "test-secret-key-for-weather-app-at-least-32-bytes",
            algorithms=["HS256"]
        )

        assert payload["sub"] == "yura"
        assert "exp" in payload

    finally:
        app.dependency_overrides.clear()
