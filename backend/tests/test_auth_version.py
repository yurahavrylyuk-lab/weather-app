import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app import app
from auth import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
)
from database import create_db_and_tables, create_db_engine, get_session
from models import User


TEST_SECRET = "test-secret-key-for-weather-app-at-least-32-bytes"


def build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_access_token_contains_auth_version(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    token = create_access_token(
        "yura",
        auth_version=3,
    )

    payload = jwt.decode(
        token,
        TEST_SECRET,
        algorithms=[ALGORITHM],
    )

    assert payload["auth_version"] == 3


def test_refresh_token_contains_auth_version(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    token = create_refresh_token(
        "yura",
        auth_version=4,
    )

    payload = jwt.decode(
        token,
        TEST_SECRET,
        algorithms=[ALGORITHM],
    )

    assert payload["auth_version"] == 4


def test_current_user_rejects_stale_auth_version(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    session = build_session()

    user = User(
        username="yura",
        hashed_password=hash_password("password123"),
        preferred_city="Warsaw",
        auth_version=2,
    )
    session.add(user)
    session.commit()

    token = create_access_token(
        "yura",
        auth_version=1,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            token=token,
            session=session,
        )

    assert exc_info.value.status_code == 401


def test_current_user_accepts_matching_auth_version(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    session = build_session()

    user = User(
        username="yura",
        hashed_password=hash_password("password123"),
        preferred_city="Warsaw",
        auth_version=2,
    )
    session.add(user)
    session.commit()

    token = create_access_token(
        "yura",
        auth_version=2,
    )

    current_user = get_current_user(
        token=token,
        session=session,
    )

    assert current_user.username == "yura"


def test_refresh_rejects_stale_auth_version(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.delenv("VERCEL_ENV", raising=False)

    database_path = tmp_path / "stale-refresh.db"
    test_engine = create_db_engine(
        f"sqlite:///{database_path}"
    )
    create_db_and_tables(test_engine)

    with Session(test_engine) as session:
        session.add(
            User(
                username="yura",
                hashed_password=hash_password("password123"),
                preferred_city="Warsaw",
                auth_version=2,
            )
        )
        session.commit()

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        stale_refresh_token = create_refresh_token(
            "yura",
            auth_version=1,
        )

        client.cookies.set(
            "refresh_token",
            stale_refresh_token,
        )

        response = client.post("/api/refresh")

        assert response.status_code == 401

    finally:
        app.dependency_overrides.clear()
