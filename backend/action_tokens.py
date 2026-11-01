import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from models import AuthActionToken, User


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()


def create_action_token(
    session: Session,
    user: User,
    purpose: str,
    expires_in: timedelta,
    target_email: str | None = None,
) -> str:
    if user.id is None:
        raise ValueError("User must be persisted before creating a token")

    raw_token = secrets.token_urlsafe(32)

    token = AuthActionToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        purpose=purpose,
        target_email=target_email,
        expires_at=datetime.now(timezone.utc) + expires_in,
    )

    session.add(token)
    session.commit()

    return raw_token


def consume_action_token(
    session: Session,
    raw_token: str,
    purpose: str,
) -> AuthActionToken | None:
    token_hash = _hash_token(raw_token)

    token = session.exec(
        select(AuthActionToken).where(
            AuthActionToken.token_hash == token_hash,
            AuthActionToken.purpose == purpose,
            AuthActionToken.used_at.is_(None),
        )
    ).first()

    if token is None:
        return None

    expires_at = token.expires_at

    # SQLite may return stored datetimes without timezone information.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    if expires_at <= now:
        return None

    token.used_at = now

    session.add(token)
    session.commit()
    session.refresh(token)

    return token
