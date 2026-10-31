from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    preferred_city: str
    is_active: bool = True


class UserCreate(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    preferred_city: str = Field(min_length=1, max_length=100)


class UserPublic(SQLModel):
    id: int
    username: str
    preferred_city: str
    is_active: bool


class UserUpdate(SQLModel):
    preferred_city: str = Field(min_length=1, max_length=100)
