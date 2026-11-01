from datetime import datetime

from models import AuthActionToken, User


def test_legacy_user_email_is_optional():
    user = User(
        username="legacy-user",
        hashed_password="hashed",
        preferred_city="Warsaw",
    )

    assert user.email is None


def test_new_user_defaults_to_unverified_email():
    user = User(
        username="test-user",
        email="user@example.com",
        hashed_password="hashed",
        preferred_city="Warsaw",
    )

    assert user.email_verified is False


def test_user_auth_version_defaults_to_one():
    user = User(
        username="test-user",
        email="user@example.com",
        hashed_password="hashed",
        preferred_city="Warsaw",
    )

    assert user.auth_version == 1


def test_auth_action_token_has_required_fields():
    token = AuthActionToken(
        user_id=1,
        token_hash="hashed-token",
        purpose="verify_email",
        expires_at=datetime(2030, 1, 1),
    )

    assert token.user_id == 1
    assert token.token_hash == "hashed-token"
    assert token.purpose == "verify_email"
    assert token.target_email is None
    assert token.used_at is None


def test_user_email_column_is_unique():
    email_column = User.__table__.c.email

    assert email_column.unique is True
