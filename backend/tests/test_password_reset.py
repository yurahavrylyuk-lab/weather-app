from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app as app_module
from action_tokens import create_action_token
from app import app
from auth import authenticate_user, hash_password
from database import create_db_and_tables, create_db_engine, get_session
from models import User


GENERIC_MESSAGE = {
    "message": (
        "If a verified account exists for that email, "
        "password reset instructions have been sent"
    )
}


def build_client(tmp_path):
    database_path = tmp_path / "password-reset.db"
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
    email="yura@example.com",
    email_verified=True,
):
    user = User(
        username="yura",
        email=email,
        email_verified=email_verified,
        hashed_password=hash_password("old-password"),
        preferred_city="Warsaw",
        auth_version=1,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def test_password_reset_request_sends_email_for_verified_user(
    tmp_path,
    monkeypatch,
):
    client, engine = build_client(tmp_path)
    sent = {}

    with Session(engine) as session:
        create_user(session)

    def fake_send(email, token):
        sent["email"] = email
        sent["token"] = token

    monkeypatch.setattr(
        app_module,
        "send_password_reset_email",
        fake_send,
        raising=False,
    )

    try:
        response = client.post(
            "/api/password-reset/request",
            json={"email": " YURA@EXAMPLE.COM "},
        )

        assert response.status_code == 200
        assert response.json() == GENERIC_MESSAGE

        assert sent["email"] == "yura@example.com"
        assert sent["token"]

    finally:
        app.dependency_overrides.clear()


def test_password_reset_request_does_not_reveal_unknown_email(
    tmp_path,
    monkeypatch,
):
    client, _ = build_client(tmp_path)
    sent = []

    monkeypatch.setattr(
        app_module,
        "send_password_reset_email",
        lambda email, token: sent.append((email, token)),
        raising=False,
    )

    try:
        response = client.post(
            "/api/password-reset/request",
            json={"email": "missing@example.com"},
        )

        assert response.status_code == 200
        assert response.json() == GENERIC_MESSAGE
        assert sent == []

    finally:
        app.dependency_overrides.clear()


def test_password_reset_request_does_not_send_for_unverified_user(
    tmp_path,
    monkeypatch,
):
    client, engine = build_client(tmp_path)
    sent = []

    with Session(engine) as session:
        create_user(
            session,
            email_verified=False,
        )

    monkeypatch.setattr(
        app_module,
        "send_password_reset_email",
        lambda email, token: sent.append((email, token)),
        raising=False,
    )

    try:
        response = client.post(
            "/api/password-reset/request",
            json={"email": "yura@example.com"},
        )

        assert response.status_code == 200
        assert response.json() == GENERIC_MESSAGE
        assert sent == []

    finally:
        app.dependency_overrides.clear()


def test_password_reset_confirm_changes_password_and_auth_version(
    tmp_path,
):
    client, engine = build_client(tmp_path)

    with Session(engine) as session:
        user = create_user(session)

        token = create_action_token(
            session,
            user,
            purpose="reset_password",
            expires_in=timedelta(minutes=30),
        )

    try:
        response = client.post(
            "/api/password-reset/confirm",
            json={
                "token": token,
                "new_password": "new-password-123",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": "Password reset successful"
        }

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "yura"
                )
            ).one()

            assert user.auth_version == 2

            assert authenticate_user(
                session,
                "yura",
                "old-password",
            ) is None

            assert authenticate_user(
                session,
                "yura",
                "new-password-123",
            ) is not None

    finally:
        app.dependency_overrides.clear()


def test_password_reset_confirm_rejects_invalid_token(tmp_path):
    client, _ = build_client(tmp_path)

    try:
        response = client.post(
            "/api/password-reset/confirm",
            json={
                "token": "invalid-token",
                "new_password": "new-password-123",
            },
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_password_reset_confirm_rejects_expired_token(tmp_path):
    client, engine = build_client(tmp_path)

    with Session(engine) as session:
        user = create_user(session)

        token = create_action_token(
            session,
            user,
            purpose="reset_password",
            expires_in=timedelta(seconds=-1),
        )

    try:
        response = client.post(
            "/api/password-reset/confirm",
            json={
                "token": token,
                "new_password": "new-password-123",
            },
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_password_reset_token_cannot_be_reused(tmp_path):
    client, engine = build_client(tmp_path)

    with Session(engine) as session:
        user = create_user(session)

        token = create_action_token(
            session,
            user,
            purpose="reset_password",
            expires_in=timedelta(minutes=30),
        )

    try:
        first = client.post(
            "/api/password-reset/confirm",
            json={
                "token": token,
                "new_password": "new-password-123",
            },
        )

        second = client.post(
            "/api/password-reset/confirm",
            json={
                "token": token,
                "new_password": "another-password-123",
            },
        )

        assert first.status_code == 200
        assert second.status_code == 400

    finally:
        app.dependency_overrides.clear()
