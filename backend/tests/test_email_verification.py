from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from action_tokens import create_action_token
from app import app
from auth import hash_password
from database import create_db_and_tables, create_db_engine, get_session
from models import User


def build_client(tmp_path):
    database_path = tmp_path / "email-verification.db"
    engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    return TestClient(app), engine


def test_verify_email_marks_user_verified(tmp_path):
    client, engine = build_client(tmp_path)

    try:
        with Session(engine) as session:
            user = User(
                username="yura",
                email="yura@example.com",
                email_verified=False,
                hashed_password=hash_password("password123"),
                preferred_city="Warsaw",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            token = create_action_token(
                session,
                user,
                purpose="verify_email",
                expires_in=timedelta(hours=24),
            )

        response = client.post(
            "/api/email/verify",
            json={"token": token},
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": "Email verified"
        }

        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.username == "yura")
            ).one()

            assert user.email_verified is True

    finally:
        app.dependency_overrides.clear()


def test_verify_email_rejects_invalid_token(tmp_path):
    client, _ = build_client(tmp_path)

    try:
        response = client.post(
            "/api/email/verify",
            json={"token": "invalid-token"},
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_verify_email_rejects_reused_token(tmp_path):
    client, engine = build_client(tmp_path)

    try:
        with Session(engine) as session:
            user = User(
                username="yura",
                email="yura@example.com",
                email_verified=False,
                hashed_password=hash_password("password123"),
                preferred_city="Warsaw",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            token = create_action_token(
                session,
                user,
                purpose="verify_email",
                expires_in=timedelta(hours=24),
            )

        first = client.post(
            "/api/email/verify",
            json={"token": token},
        )
        second = client.post(
            "/api/email/verify",
            json={"token": token},
        )

        assert first.status_code == 200
        assert second.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_verify_email_rejects_expired_token(tmp_path):
    client, engine = build_client(tmp_path)

    try:
        with Session(engine) as session:
            user = User(
                username="yura",
                email="yura@example.com",
                email_verified=False,
                hashed_password=hash_password("password123"),
                preferred_city="Warsaw",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            token = create_action_token(
                session,
                user,
                purpose="verify_email",
                expires_in=timedelta(seconds=-1),
            )

        response = client.post(
            "/api/email/verify",
            json={"token": token},
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_registration_sends_verification_email(
    tmp_path,
    monkeypatch,
):
    import app as app_module

    client, engine = build_client(tmp_path)
    sent = {}

    def fake_send(email, token):
        sent["email"] = email
        sent["token"] = token

    monkeypatch.setattr(
        app_module,
        "send_verification_email",
        fake_send,
        raising=False,
    )

    try:
        response = client.post(
            "/api/register",
            json={
                "username": "new-user",
                "email": "new@example.com",
                "password": "password123",
                "preferred_city": "Warsaw",
            },
        )

        assert response.status_code == 201
        assert sent["email"] == "new@example.com"
        assert sent["token"]

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    User.username == "new-user"
                )
            ).one()

            assert user.email_verified is False

    finally:
        app.dependency_overrides.clear()


def test_resend_verification_sends_for_unverified_user(
    tmp_path,
    monkeypatch,
):
    import app as app_module

    client, engine = build_client(tmp_path)
    sent = {}

    with Session(engine) as session:
        session.add(
            User(
                username="yura",
                email="yura@example.com",
                email_verified=False,
                hashed_password=hash_password("password123"),
                preferred_city="Warsaw",
            )
        )
        session.commit()

    def fake_send(email, token):
        sent["email"] = email
        sent["token"] = token

    monkeypatch.setattr(
        app_module,
        "send_verification_email",
        fake_send,
        raising=False,
    )

    try:
        response = client.post(
            "/api/email/resend-verification",
            json={"email": " YURA@EXAMPLE.COM "},
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": (
                "If an unverified account exists, "
                "a verification email has been sent"
            )
        }

        assert sent["email"] == "yura@example.com"
        assert sent["token"]

    finally:
        app.dependency_overrides.clear()


def test_resend_verification_does_not_reveal_unknown_email(
    tmp_path,
    monkeypatch,
):
    import app as app_module

    client, _ = build_client(tmp_path)
    sent = []

    def fake_send(email, token):
        sent.append((email, token))

    monkeypatch.setattr(
        app_module,
        "send_verification_email",
        fake_send,
        raising=False,
    )

    try:
        response = client.post(
            "/api/email/resend-verification",
            json={"email": "missing@example.com"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": (
                "If an unverified account exists, "
                "a verification email has been sent"
            )
        }

        assert sent == []

    finally:
        app.dependency_overrides.clear()


def test_resend_verification_does_not_send_for_verified_user(
    tmp_path,
    monkeypatch,
):
    import app as app_module

    client, engine = build_client(tmp_path)
    sent = []

    with Session(engine) as session:
        session.add(
            User(
                username="yura",
                email="yura@example.com",
                email_verified=True,
                hashed_password=hash_password("password123"),
                preferred_city="Warsaw",
            )
        )
        session.commit()

    def fake_send(email, token):
        sent.append((email, token))

    monkeypatch.setattr(
        app_module,
        "send_verification_email",
        fake_send,
        raising=False,
    )

    try:
        response = client.post(
            "/api/email/resend-verification",
            json={"email": "yura@example.com"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": (
                "If an unverified account exists, "
                "a verification email has been sent"
            )
        }

        assert sent == []

    finally:
        app.dependency_overrides.clear()
