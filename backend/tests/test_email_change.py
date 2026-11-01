from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app as app_module
from action_tokens import create_action_token
from app import app
from auth import create_access_token, hash_password
from database import create_db_and_tables, create_db_engine, get_session
from models import User


@pytest.fixture(autouse=True)
def configure_jwt_secret(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-email-change-secret-key-32-bytes-minimum",
    )


def build_client(tmp_path):
    database_path = tmp_path / "email-change.db"
    engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    return TestClient(app), engine


def create_user(
    session,
    *,
    username="yura",
    email="old@example.com",
    password="password123",
):
    user = User(
        username=username,
        email=email,
        email_verified=True,
        hashed_password=hash_password(password),
        preferred_city="Warsaw",
        auth_version=1,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def auth_headers(user):
    token = create_access_token(
        user.username,
        auth_version=user.auth_version,
    )

    return {
        "Authorization": f"Bearer {token}"
    }


def test_email_change_request_and_confirmation(
    tmp_path,
    monkeypatch,
):
    client, engine = build_client(tmp_path)
    sent = {}

    with Session(engine) as session:
        user = create_user(session)
        headers = auth_headers(user)

    def fake_send(email, token):
        sent["email"] = email
        sent["token"] = token

    monkeypatch.setattr(
        app_module,
        "send_email_change_verification",
        fake_send,
        raising=False,
    )

    try:
        request_response = client.post(
            "/api/users/me/email",
            headers=headers,
            json={
                "new_email": " NEW@Example.COM ",
                "current_password": "password123",
            },
        )

        assert request_response.status_code == 200
        assert request_response.json() == {
            "message": (
                "Check your new email to confirm the change"
            )
        }

        assert sent["email"] == "new@example.com"
        assert sent["token"]

        # The existing email must remain active until confirmation.
        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "yura"
                )
            ).one()

            assert user.email == "old@example.com"
            assert user.email_verified is True

        confirm_response = client.post(
            "/api/email/confirm-change",
            json={
                "token": sent["token"],
            },
        )

        assert confirm_response.status_code == 200
        assert confirm_response.json() == {
            "message": "Email changed successfully"
        }

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "yura"
                )
            ).one()

            assert user.email == "new@example.com"
            assert user.email_verified is True

    finally:
        app.dependency_overrides.clear()


def test_email_change_requires_current_password(
    tmp_path,
    monkeypatch,
):
    client, engine = build_client(tmp_path)
    sent = []

    with Session(engine) as session:
        user = create_user(session)
        headers = auth_headers(user)

    monkeypatch.setattr(
        app_module,
        "send_email_change_verification",
        lambda email, token: sent.append((email, token)),
        raising=False,
    )

    try:
        response = client.post(
            "/api/users/me/email",
            headers=headers,
            json={
                "new_email": "new@example.com",
                "current_password": "wrong-password",
            },
        )

        assert response.status_code == 400
        assert sent == []

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "yura"
                )
            ).one()

            assert user.email == "old@example.com"

    finally:
        app.dependency_overrides.clear()


def test_email_change_rejects_duplicate_email(
    tmp_path,
    monkeypatch,
):
    client, engine = build_client(tmp_path)
    sent = []

    with Session(engine) as session:
        user = create_user(session)

        create_user(
            session,
            username="other",
            email="taken@example.com",
        )

        headers = auth_headers(user)

    monkeypatch.setattr(
        app_module,
        "send_email_change_verification",
        lambda email, token: sent.append((email, token)),
        raising=False,
    )

    try:
        response = client.post(
            "/api/users/me/email",
            headers=headers,
            json={
                "new_email": " TAKEN@EXAMPLE.COM ",
                "current_password": "password123",
            },
        )

        assert response.status_code == 409
        assert sent == []

    finally:
        app.dependency_overrides.clear()


def test_email_change_requires_authentication(tmp_path):
    client, _ = build_client(tmp_path)

    try:
        response = client.post(
            "/api/users/me/email",
            json={
                "new_email": "new@example.com",
                "current_password": "password123",
            },
        )

        assert response.status_code == 401

    finally:
        app.dependency_overrides.clear()


def test_email_change_rejects_expired_confirmation_token(
    tmp_path,
):
    client, engine = build_client(tmp_path)

    with Session(engine) as session:
        user = create_user(session)

        token = create_action_token(
            session,
            user,
            purpose="change_email",
            expires_in=timedelta(seconds=-1),
            target_email="new@example.com",
        )

    try:
        response = client.post(
            "/api/email/confirm-change",
            json={"token": token},
        )

        assert response.status_code == 400

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "yura"
                )
            ).one()

            assert user.email == "old@example.com"

    finally:
        app.dependency_overrides.clear()


def test_email_change_confirmation_token_cannot_be_reused(
    tmp_path,
):
    client, engine = build_client(tmp_path)

    with Session(engine) as session:
        user = create_user(session)

        token = create_action_token(
            session,
            user,
            purpose="change_email",
            expires_in=timedelta(hours=1),
            target_email="new@example.com",
        )

    try:
        first = client.post(
            "/api/email/confirm-change",
            json={"token": token},
        )

        second = client.post(
            "/api/email/confirm-change",
            json={"token": token},
        )

        assert first.status_code == 200
        assert second.status_code == 400

    finally:
        app.dependency_overrides.clear()
