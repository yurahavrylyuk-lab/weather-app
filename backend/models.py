from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str | None = Field(default=None, index=True, unique=True)
    email_verified: bool = False
    auth_version: int = 1
    hashed_password: str
    preferred_city: str
    is_active: bool = True


class AuthActionToken(SQLModel, table=True):
    __tablename__ = "auth_action_tokens"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    purpose: str = Field(index=True)
    target_email: str | None = None
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UserCreate(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    preferred_city: str = Field(min_length=1, max_length=100)


class UserPublic(SQLModel):
    id: int
    username: str
    email: str | None
    email_verified: bool
    preferred_city: str
    is_active: bool


class UserUpdate(SQLModel):
    preferred_city: str = Field(min_length=1, max_length=100)


class EmailTokenRequest(SQLModel):
    token: str = Field(min_length=1)


class EmailRequest(SQLModel):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetConfirm(SQLModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)



class EmailChangeRequest(SQLModel):
    new_email: str = Field(min_length=3, max_length=320)
    current_password: str = Field(min_length=1, max_length=128)



class PasswordChangeRequest(SQLModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    new_password_confirmation: str = Field(min_length=8, max_length=128)
