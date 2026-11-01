import pytest

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import app
from auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from database import create_db_and_tables, create_db_engine, get_session
from models import User


@pytest.fixture(autouse=True)
def configure_jwt_secret(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-password-change-secret-key-at-least-32-bytes",
    )


def build_client(tmp_path):
    database_path = tmp_path / "password-change.db"
    engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    return TestClient(app), engine


def create_user(session):
    user = User(
        username="yura",
        email="yura@example.com",
        email_verified=True,
        hashed_password=hash_password("old-password-123"),
        preferred_city="Warsaw",
        auth_version=1,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def test_password_change_updates_password_and_issues_fresh_session(
    tmp_path,
):
    client, engine = build_client(tmp_path)

    with Session(engine) as session:
        user = create_user(session)

        old_access_token = create_access_token(
            user.username,
            auth_version=user.auth_version,
        )

        old_refresh_token = create_refresh_token(
            user.username,
            auth_version=user.auth_version,
        )

    headers = {
        "Authorization": f"Bearer {old_access_token}"
    }

    try:
        response = client.post(
            "/api/users/me/password",
            headers=headers,
            json={
                "current_password": "old-password-123",
                "new_password": "new-password-456",
                "new_password_confirmation": "new-password-456",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["token_type"] == "bearer"
        assert data["access_token"]

        assert "refresh_token=" in response.headers.get(
            "set-cookie",
            "",
        )

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "yura"
                )
            ).one()

            assert user.auth_version == 2

            assert verify_password(
                "new-password-456",
                user.hashed_password,
            )

            assert not verify_password(
                "old-password-123",
                user.hashed_password,
            )

        # The access token from before the password change is stale.
        stale_access_response = client.get(
            "/api/users/me",
            headers={
                "Authorization":
                    f"Bearer {old_access_token}"
            },
        )

        assert stale_access_response.status_code == 401

        # The freshly issued access token works.
        fresh_access_response = client.get(
            "/api/users/me",
            headers={
                "Authorization":
                    f'Bearer {data["access_token"]}'
            },
        )

        assert fresh_access_response.status_code == 200

        # The refresh token from before the password change is stale.
        stale_client = TestClient(app)
        stale_client.cookies.set(
            "refresh_token",
            old_refresh_token,
        )

        stale_refresh_response = stale_client.post(
            "/api/refresh"
        )

        assert stale_refresh_response.status_code == 401

    finally:
        app.dependency_overrides.clear()


def test_password_change_requires_correct_current_password(
    tmp_path,
):
    client, engine = build_client(tmp_path)

    with Session(engine) as session:
        user = create_user(session)

        access_token = create_access_token(
            user.username,
            auth_version=user.auth_version,
        )

    try:
        response = client.post(
            "/api/users/me/password",
            headers={
                "Authorization":
                    f"Bearer {access_token}"
            },
            json={
                "current_password": "wrong-password",
                "new_password": "new-password-456",
                "new_password_confirmation":
                    "new-password-456",
            },
        )

        assert response.status_code == 400

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "yura"
                )
            ).one()

            assert user.auth_version == 1

            assert verify_password(
                "old-password-123",
                user.hashed_password,
            )

    finally:
        app.dependency_overrides.clear()


def test_password_change_rejects_confirmation_mismatch(
    tmp_path,
):
    client, engine = build_client(tmp_path)

    with Session(engine) as session:
        user = create_user(session)

        access_token = create_access_token(
            user.username,
            auth_version=user.auth_version,
        )

    try:
        response = client.post(
            "/api/users/me/password",
            headers={
                "Authorization":
                    f"Bearer {access_token}"
            },
            json={
                "current_password": "old-password-123",
                "new_password": "new-password-456",
                "new_password_confirmation":
                    "different-password-789",
            },
        )

        assert response.status_code == 400

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "yura"
                )
            ).one()

            assert user.auth_version == 1

            assert verify_password(
                "old-password-123",
                user.hashed_password,
            )

    finally:
        app.dependency_overrides.clear()


def test_password_change_requires_authentication(tmp_path):
    client, _ = build_client(tmp_path)

    try:
        response = client.post(
            "/api/users/me/password",
            json={
                "current_password": "old-password-123",
                "new_password": "new-password-456",
                "new_password_confirmation":
                    "new-password-456",
            },
        )

        assert response.status_code == 401

    finally:
        app.dependency_overrides.clear()
