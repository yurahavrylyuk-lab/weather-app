import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlmodel import Session, select

from database import get_session
from models import User


password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/token"
)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password
    )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def authenticate_user(
    session: Session,
    identifier: str,
    password: str
) -> User | None:
    identifier = identifier.strip()
    normalized_email = normalize_email(identifier)

    user = session.exec(
        select(User).where(
            (User.username == identifier)
            | (User.email == normalized_email)
        )
    ).first()

    if user is None:
        return None

    if not verify_password(
        password,
        user.hashed_password
    ):
        return None

    if user.email is not None and not user.email_verified:
        return None

    return user


def create_access_token(
    username: str,
    auth_version: int = 1
) -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": username,
        "type": "access",
        "auth_version": auth_version,
        "exp": expires_at,
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    username: str,
    auth_version: int = 1
) -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": username,
        "type": "refresh",
        "auth_version": auth_version,
        "exp": expires_at,
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != "access":
            raise credentials_exception

        username = payload.get("sub")
        auth_version = payload.get("auth_version")

        if username is None:
            raise credentials_exception

        if type(auth_version) is not int:
            raise credentials_exception

    except jwt.InvalidTokenError:
        raise credentials_exception

    user = session.exec(
        select(User).where(User.username == username)
    ).first()

    if user is None:
        raise credentials_exception

    if user.auth_version != auth_version:
        raise credentials_exception

    return user
