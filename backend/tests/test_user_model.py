from models import User


def test_user_model_includes_preferred_city():
    user = User(
        username="testuser",
        hashed_password="hashed-password",
        preferred_city="Warsaw"
    )

    assert user.id is None
    assert user.username == "testuser"
    assert user.hashed_password == "hashed-password"
    assert user.is_active is True
    assert user.preferred_city == "Warsaw"
