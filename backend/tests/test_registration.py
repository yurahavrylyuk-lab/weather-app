import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app as app_module
from app import app
from database import create_db_and_tables, create_db_engine, get_session
from models import User
from auth import verify_password


@pytest.fixture(autouse=True)
def stub_verification_email(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "send_verification_email",
        lambda email, token: None,
    )


def test_register_creates_user_with_hashed_password(tmp_path):
    database_path = tmp_path / "registration.db"
    test_engine = create_db_engine(
        f"sqlite:///{database_path}"
    )
    create_db_and_tables(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        response = client.post(
            "/api/register",
            json={
                "username": "yura",
                "email": "yura@example.com",
                "password": "StrongPassword123",
                "preferred_city": "Warsaw"
            }
        )

        assert response.status_code == 201

        data = response.json()

        assert data["username"] == "yura"
        assert data["is_active"] is True
        assert data["preferred_city"] == "Warsaw"
        assert "password" not in data
        assert "hashed_password" not in data

        with Session(test_engine) as session:
            user = session.exec(
                select(User).where(User.username == "yura")
            ).one()

            assert user.preferred_city == "Warsaw"
            assert user.hashed_password != "StrongPassword123"
            assert verify_password(
                "StrongPassword123",
                user.hashed_password
            ) is True

    finally:
        app.dependency_overrides.clear()


def test_register_rejects_duplicate_username(tmp_path):
    database_path = tmp_path / "duplicate-registration.db"
    test_engine = create_db_engine(
        f"sqlite:///{database_path}"
    )
    create_db_and_tables(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        first_response = client.post(
            "/api/register",
            json={
                "username": "yura",
                "email": "first@example.com",
                "password": "StrongPassword123",
                "preferred_city": "Warsaw"
            }
        )

        second_response = client.post(
            "/api/register",
            json={
                "username": "yura",
                "email": "second@example.com",
                "password": "AnotherPassword456",
                "preferred_city": "Krakow"
            }
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json() == {
            "detail": "Username already registered"
        }

    finally:
        app.dependency_overrides.clear()


def test_register_rejects_short_username(tmp_path):
    database_path = tmp_path / "short-username.db"
    test_engine = create_db_engine(
        f"sqlite:///{database_path}"
    )
    create_db_and_tables(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        response = client.post(
            "/api/register",
            json={
                "username": "yu",
                "email": "short-username@example.com",
                "password": "StrongPassword123",
                "preferred_city": "Warsaw"
            }
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


def test_register_rejects_short_password(tmp_path):
    database_path = tmp_path / "short-password.db"
    test_engine = create_db_engine(
        f"sqlite:///{database_path}"
    )
    create_db_and_tables(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        response = client.post(
            "/api/register",
            json={
                "username": "yura",
                "email": "short-password@example.com",
                "password": "short",
                "preferred_city": "Warsaw"
            }
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()



def test_registration_requires_email(tmp_path):
    database_path = tmp_path / "requires-email.db"
    test_engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        response = client.post(
            "/api/register",
            json={
                "username": "new-user",
                "password": "password123",
                "preferred_city": "Warsaw",
            },
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


def test_registration_normalizes_email(tmp_path):
    database_path = tmp_path / "normalizes-email.db"
    test_engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        response = client.post(
            "/api/register",
            json={
                "username": "email-user",
                "email": "  USER@Example.COM  ",
                "password": "password123",
                "preferred_city": "Warsaw",
            },
        )

        assert response.status_code == 201
        assert response.json()["email"] == "user@example.com"
        assert response.json()["email_verified"] is False

    finally:
        app.dependency_overrides.clear()


def test_registration_rejects_duplicate_email_case_insensitively(tmp_path):
    database_path = tmp_path / "duplicate-email.db"
    test_engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        first_response = client.post(
            "/api/register",
            json={
                "username": "first-user",
                "email": "user@example.com",
                "password": "password123",
                "preferred_city": "Warsaw",
            },
        )

        assert first_response.status_code == 201

        second_response = client.post(
            "/api/register",
            json={
                "username": "second-user",
                "email": "USER@EXAMPLE.COM",
                "password": "password123",
                "preferred_city": "Krakow",
            },
        )

        assert second_response.status_code == 409
        assert second_response.json()["detail"] == "Email already registered"

    finally:
        app.dependency_overrides.clear()
