from datetime import datetime, timedelta, timezone

import jwt

import auth


TEST_SECRET = "test-secret-key-for-persistent-login"


def test_access_token_is_typed_as_access(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    token = auth.create_access_token("yura")
    payload = jwt.decode(token, TEST_SECRET, algorithms=[auth.ALGORITHM])

    assert payload["sub"] == "yura"
    assert payload["type"] == "access"


def test_refresh_token_is_typed_and_expires_in_30_days(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    assert hasattr(auth, "create_refresh_token")

    token = auth.create_refresh_token("yura")
    payload = jwt.decode(token, TEST_SECRET, algorithms=[auth.ALGORITHM])

    assert payload["sub"] == "yura"
    assert payload["type"] == "refresh"

    expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)
    expected = datetime.now(timezone.utc) + timedelta(days=30)

    assert abs((expires_at - expected).total_seconds()) < 5


def test_refresh_token_cannot_be_used_as_access_token(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app import app
    from database import create_db_and_tables, create_db_engine, get_session
    from models import User

    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    database_path = tmp_path / "refresh-as-access.db"
    test_engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(test_engine)

    with Session(test_engine) as session:
        session.add(
            User(
                username="yura",
                hashed_password=auth.hash_password("StrongPassword123"),
                preferred_city="Warsaw",
            )
        )
        session.commit()

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)
        refresh_token = auth.create_refresh_token("yura")

        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_untyped_jwt_cannot_be_used_as_access_token(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app import app
    from database import create_db_and_tables, create_db_engine, get_session
    from models import User

    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    database_path = tmp_path / "untyped-token.db"
    test_engine = create_db_engine(f"sqlite:///{database_path}")
    create_db_and_tables(test_engine)

    with Session(test_engine) as session:
        session.add(
            User(
                username="yura",
                hashed_password=auth.hash_password("StrongPassword123"),
                preferred_city="Warsaw",
            )
        )
        session.commit()

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        client = TestClient(app)

        token = jwt.encode(
            {
                "sub": "yura",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            },
            TEST_SECRET,
            algorithm=auth.ALGORITHM,
        )

        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
