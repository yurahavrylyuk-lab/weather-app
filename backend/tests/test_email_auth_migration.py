from sqlalchemy import create_engine, inspect, text


def test_email_auth_migration_upgrades_existing_user_table(tmp_path):
    from alembic import command
    from alembic.config import Config

    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)

    # Simulate the production schema before the email-auth feature.
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE user (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR NOT NULL UNIQUE,
                    hashed_password VARCHAR NOT NULL,
                    preferred_city VARCHAR NOT NULL,
                    is_active BOOLEAN NOT NULL
                )
                """
            )
        )

    config = Config("backend/alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    inspector = inspect(engine)

    user_columns = {
        column["name"]
        for column in inspector.get_columns("user")
    }

    assert "email" in user_columns
    assert "email_verified" in user_columns
    assert "auth_version" in user_columns
    assert "auth_action_tokens" in inspector.get_table_names()
