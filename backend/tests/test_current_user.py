from fastapi.testclient import TestClient

from app import app


def test_users_me_requires_bearer_token():
    client = TestClient(app)

    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_users_me_returns_authenticated_user(tmp_path, monkeypatch):
    from sqlmodel import Session

    from auth import create_access_token, hash_password
    from database import (
        create_db_and_tables,
        create_db_engine,
        get_session,
    )
    from models import User

    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-for-weather-app-at-least-32-bytes"
    )

    database_path = tmp_path / "current-user.db"
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
        access_token = create_access_token("yura")

        client = TestClient(app)

        response = client.get(
            "/api/users/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )

        assert response.status_code == 200

        data = response.json()

        assert data["username"] == "yura"
        assert data["is_active"] is True
        assert "hashed_password" not in data

    finally:
        app.dependency_overrides.clear()
