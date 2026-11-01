import hashlib
from datetime import timedelta

from sqlmodel import Session, SQLModel, create_engine, select

from action_tokens import create_action_token, consume_action_token
from auth import hash_password
from models import AuthActionToken, User


def build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def create_user(session):
    user = User(
        username="yura",
        hashed_password=hash_password("password123"),
        preferred_city="Warsaw",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_action_token_stores_sha256_hash_not_raw_token():
    session = build_session()
    user = create_user(session)

    raw_token = create_action_token(
        session,
        user,
        purpose="verify_email",
        expires_in=timedelta(hours=24),
    )

    stored = session.exec(
        select(AuthActionToken)
    ).one()

    expected_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    assert stored.token_hash == expected_hash
    assert stored.token_hash != raw_token


def test_action_token_can_only_be_consumed_once():
    session = build_session()
    user = create_user(session)

    raw_token = create_action_token(
        session,
        user,
        purpose="reset_password",
        expires_in=timedelta(minutes=30),
    )

    first = consume_action_token(
        session,
        raw_token,
        purpose="reset_password",
    )

    second = consume_action_token(
        session,
        raw_token,
        purpose="reset_password",
    )

    assert first is not None
    assert first.used_at is not None
    assert second is None


def test_expired_action_token_cannot_be_consumed():
    session = build_session()
    user = create_user(session)

    raw_token = create_action_token(
        session,
        user,
        purpose="reset_password",
        expires_in=timedelta(seconds=-1),
    )

    consumed = consume_action_token(
        session,
        raw_token,
        purpose="reset_password",
    )

    assert consumed is None


def test_wrong_purpose_does_not_consume_token():
    session = build_session()
    user = create_user(session)

    raw_token = create_action_token(
        session,
        user,
        purpose="verify_email",
        expires_in=timedelta(hours=24),
    )

    wrong_purpose = consume_action_token(
        session,
        raw_token,
        purpose="reset_password",
    )

    correct_purpose = consume_action_token(
        session,
        raw_token,
        purpose="verify_email",
    )

    assert wrong_purpose is None
    assert correct_purpose is not None


def test_action_token_preserves_target_email():
    session = build_session()
    user = create_user(session)

    raw_token = create_action_token(
        session,
        user,
        purpose="change_email",
        expires_in=timedelta(hours=1),
        target_email="new@example.com",
    )

    consumed = consume_action_token(
        session,
        raw_token,
        purpose="change_email",
    )

    assert consumed is not None
    assert consumed.target_email == "new@example.com"
