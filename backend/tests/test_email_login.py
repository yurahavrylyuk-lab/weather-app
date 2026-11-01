from sqlmodel import Session, SQLModel, create_engine

from auth import authenticate_user, hash_password, normalize_email
from models import User


def build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_normalize_email_lowercases_and_strips_whitespace():
    assert normalize_email("  USER@Example.COM  ") == "user@example.com"


def test_authenticate_user_accepts_username():
    session = build_session()
    user = User(
        username="yura",
        email="yura@example.com",
        email_verified=True,
        hashed_password=hash_password("password123"),
        preferred_city="Warsaw",
    )
    session.add(user)
    session.commit()

    result = authenticate_user(
        session,
        "yura",
        "password123",
    )

    assert result is not None
    assert result.username == "yura"


def test_authenticate_user_accepts_email():
    session = build_session()
    user = User(
        username="yura",
        email="yura@example.com",
        email_verified=True,
        hashed_password=hash_password("password123"),
        preferred_city="Warsaw",
    )
    session.add(user)
    session.commit()

    result = authenticate_user(
        session,
        "YURA@EXAMPLE.COM",
        "password123",
    )

    assert result is not None
    assert result.username == "yura"


def test_authenticate_user_rejects_wrong_password():
    session = build_session()
    user = User(
        username="yura",
        email="yura@example.com",
        email_verified=True,
        hashed_password=hash_password("password123"),
        preferred_city="Warsaw",
    )
    session.add(user)
    session.commit()

    result = authenticate_user(
        session,
        "yura@example.com",
        "wrong-password",
    )

    assert result is None


def test_legacy_user_without_email_can_still_login_by_username():
    session = build_session()
    user = User(
        username="legacy-user",
        hashed_password=hash_password("password123"),
        preferred_city="Warsaw",
    )
    session.add(user)
    session.commit()

    result = authenticate_user(
        session,
        "legacy-user",
        "password123",
    )

    assert result is not None


def test_unverified_email_user_cannot_login():
    session = build_session()
    user = User(
        username="new-user",
        email="new@example.com",
        email_verified=False,
        hashed_password=hash_password("password123"),
        preferred_city="Warsaw",
    )
    session.add(user)
    session.commit()

    result = authenticate_user(
        session,
        "new@example.com",
        "password123",
    )

    assert result is None
