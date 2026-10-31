from models import User


def test_user_model_defaults():
    user = User(
        username="testuser",
        hashed_password="hashed-password"
    )

    assert user.id is None
    assert user.username == "testuser"
    assert user.hashed_password == "hashed-password"
    assert user.is_active is True
