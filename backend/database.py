import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from models import User


DEFAULT_DATABASE_PATH = Path(__file__).with_name("weather.db")
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"


def create_db_engine(database_url: str | None = None):
    url = database_url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    connect_args = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        url,
        connect_args=connect_args
    )


engine = create_db_engine()


def create_db_and_tables(engine_to_use=engine):
    SQLModel.metadata.create_all(engine_to_use)


def get_session():
    with Session(engine) as session:
        yield session
