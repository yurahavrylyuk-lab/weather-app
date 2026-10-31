from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import app
from database import create_db_and_tables, create_db_engine, get_session
from models import User
from auth import verify_password


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
                "password": "StrongPassword123",
                "preferred_city": "Warsaw"
            }
        )

        second_response = client.post(
            "/api/register",
            json={
                "username": "yura",
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
                "password": "short",
                "preferred_city": "Warsaw"
            }
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()
