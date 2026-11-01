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


def test_frontend_supports_persistent_login():
    auth_script = (FRONTEND / "auth.js").read_text()

    assert "/api/refresh" in auth_script
    assert "/api/logout" in auth_script

    # Refresh/login/logout requests must carry the secure cookie.
    assert 'credentials: "include"' in auth_script

    # Expired access JWT should trigger silent renewal.
    assert "response.status === 401" in auth_script

    # Short-lived access JWT remains session-only.
    assert "sessionStorage" in auth_script


def test_frontend_supports_email_registration_and_verification_ui():
    index = (FRONTEND / "index.html").read_text()
    auth_script = (FRONTEND / "auth.js").read_text()

    assert 'id="register-email"' in index
    assert 'type="email"' in index

    assert 'id="verification-panel"' in index
    assert 'id="verification-email"' in index
    assert 'id="resend-verification-button"' in index
    assert 'id="verification-message"' in index

    assert "Username or email" in index

    assert "register-email" in auth_script
    assert "email," in auth_script

    # New users must verify before they can log in.
    assert "Check your email" in auth_script
    assert "showVerificationPanel" in auth_script


def test_frontend_handles_verification_links_and_resend():
    auth_script = (FRONTEND / "auth.js").read_text()

    assert "verify_email_token" in auth_script
    assert "/api/email/verify" in auth_script
    assert "/api/email/resend-verification" in auth_script

    assert "URLSearchParams" in auth_script
    assert "history.replaceState" in auth_script

    assert "resend-verification-button" in auth_script


def test_frontend_supports_forgot_password_ui():
    index = (FRONTEND / "index.html").read_text()
    auth_script = (FRONTEND / "auth.js").read_text()

    assert 'id="forgot-password-button"' in index
    assert 'id="forgot-password-panel"' in index
    assert 'id="forgot-password-form"' in index
    assert 'id="forgot-password-email"' in index
    assert 'id="forgot-password-message"' in index

    assert "/api/password-reset/request" in auth_script
    assert "forgot-password-form" in auth_script


def test_frontend_supports_password_reset_link():
    index = (FRONTEND / "index.html").read_text()
    auth_script = (FRONTEND / "auth.js").read_text()

    assert 'id="reset-password-panel"' in index
    assert 'id="reset-password-form"' in index
    assert 'id="reset-password-new"' in index
    assert 'id="reset-password-confirm"' in index
    assert 'id="reset-password-message"' in index

    assert "reset_password_token" in auth_script
    assert "/api/password-reset/confirm" in auth_script
    assert "history.replaceState" in auth_script


def test_frontend_supports_email_change_in_profile():
    index = (FRONTEND / "index.html").read_text()
    auth_script = (FRONTEND / "auth.js").read_text()

    assert 'id="profile-email"' in index
    assert 'id="change-email-form"' in index
    assert 'id="change-email-new"' in index
    assert 'id="change-email-password"' in index
    assert 'id="change-email-message"' in index

    assert "/api/users/me/email" in auth_script
    assert "change-email-form" in auth_script
    assert "profile-email" in auth_script


def test_frontend_handles_email_change_confirmation_link():
    auth_script = (FRONTEND / "auth.js").read_text()

    assert "change_email_token" in auth_script
    assert "/api/email/confirm-change" in auth_script
    assert "history.replaceState" in auth_script
