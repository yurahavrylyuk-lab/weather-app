from sqlalchemy import inspect

from database import create_db_and_tables, create_db_engine


def test_create_db_and_tables_creates_user_table(tmp_path):
    database_path = tmp_path / "test.db"
    database_url = f"sqlite:///{database_path}"

    engine = create_db_engine(database_url)
    create_db_and_tables(engine)

    table_names = inspect(engine).get_table_names()

    assert "user" in table_names


def test_get_session_yields_sqlmodel_session(tmp_path, monkeypatch):
    import database
    from sqlmodel import Session

    database_path = tmp_path / "session-test.db"
    test_engine = database.create_db_engine(
        f"sqlite:///{database_path}"
    )

    monkeypatch.setattr(database, "engine", test_engine)

    session_generator = database.get_session()
    session = next(session_generator)

    assert isinstance(session, Session)

    session_generator.close()
