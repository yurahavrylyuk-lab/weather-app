from auth import hash_password, verify_password


def test_hash_password_does_not_store_plain_password():
    password = "StrongPassword123"

    hashed_password = hash_password(password)

    assert hashed_password != password


def test_verify_password_accepts_correct_password():
    password = "StrongPassword123"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True


def test_verify_password_rejects_wrong_password():
    hashed_password = hash_password("StrongPassword123")

    assert verify_password(
        "WrongPassword123",
        hashed_password
    ) is False


def test_authenticate_user_accepts_correct_credentials(tmp_path):
    from sqlmodel import Session

    from auth import authenticate_user, hash_password
    from database import create_db_and_tables, create_db_engine
    from models import User

    database_path = tmp_path / "authenticate.db"
    test_engine = create_db_engine(
        f"sqlite:///{database_path}"
    )
    create_db_and_tables(test_engine)

    with Session(test_engine) as session:
        user = User(
            username="yura",
            hashed_password=hash_password("StrongPassword123"),
            preferred_city="Warsaw"
        )
        session.add(user)
        session.commit()

        authenticated_user = authenticate_user(
            session,
            "yura",
            "StrongPassword123"
        )

        assert authenticated_user is not None
        assert authenticated_user.username == "yura"
