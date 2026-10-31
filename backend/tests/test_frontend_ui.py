from pathlib import Path


FRONTEND = Path(__file__).parents[2] / "frontend"


def test_frontend_supports_public_weather_and_account_ui():
    index = (FRONTEND / "index.html").read_text()
    script = (FRONTEND / "script.js").read_text()
    auth_script = (FRONTEND / "auth.js").read_text()

    assert 'id="account-button"' in index
    assert 'id="account-dropdown"' in index

    assert 'id="login-form"' in index
    assert 'id="register-form"' in index
    assert 'id="profile-form"' in index

    assert "Sign in to save your home city" in index

    assert 'id="weather-results"' in index
    assert 'id="weather-results" hidden' in index

    assert '<h1 id="city-name">--</h1>' in index
    assert '<span id="metar-station">' in index
    assert "EPWA" not in index

    assert "/api/weather" in script

    assert "/api/register" in auth_script
    assert "/api/token" in auth_script
    assert "/api/users/me" in auth_script

    assert "sessionStorage" in auth_script
    assert "preferred_city" in auth_script
    assert 'method: "PATCH"' in auth_script
