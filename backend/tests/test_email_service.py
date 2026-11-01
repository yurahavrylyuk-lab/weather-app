from email_service import (
    send_email_change_verification,
    send_password_reset_email,
    send_verification_email,
)


def configure(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv(
        "APP_BASE_URL",
        "https://weather-app-taupe-one-89.vercel.app",
    )
    monkeypatch.setenv(
        "RESEND_FROM_EMAIL",
        "Weather App <onboarding@resend.dev>",
    )


def test_send_verification_email_builds_correct_link(monkeypatch):
    configure(monkeypatch)

    sent = {}

    def fake_send(params):
        sent.update(params)
        return {"id": "email-1"}

    monkeypatch.setattr(
        "resend.Emails.send",
        fake_send,
    )

    send_verification_email(
        "user@example.com",
        "raw-secret-token",
    )

    assert sent["to"] == ["user@example.com"]
    assert sent["subject"] == "Verify your Weather App email"
    assert (
        "https://weather-app-taupe-one-89.vercel.app/"
        "?verify_email_token=raw-secret-token"
        in sent["html"]
    )


def test_send_password_reset_email_builds_correct_link(monkeypatch):
    configure(monkeypatch)

    sent = {}

    def fake_send(params):
        sent.update(params)
        return {"id": "email-2"}

    monkeypatch.setattr(
        "resend.Emails.send",
        fake_send,
    )

    send_password_reset_email(
        "user@example.com",
        "reset-secret-token",
    )

    assert sent["to"] == ["user@example.com"]
    assert sent["subject"] == "Reset your Weather App password"
    assert (
        "https://weather-app-taupe-one-89.vercel.app/"
        "?reset_password_token=reset-secret-token"
        in sent["html"]
    )


def test_send_email_change_verification_builds_correct_link(monkeypatch):
    configure(monkeypatch)

    sent = {}

    def fake_send(params):
        sent.update(params)
        return {"id": "email-3"}

    monkeypatch.setattr(
        "resend.Emails.send",
        fake_send,
    )

    send_email_change_verification(
        "new@example.com",
        "change-secret-token",
    )

    assert sent["to"] == ["new@example.com"]
    assert sent["subject"] == "Confirm your new Weather App email"
    assert (
        "https://weather-app-taupe-one-89.vercel.app/"
        "?change_email_token=change-secret-token"
        in sent["html"]
    )


def test_email_sender_uses_configured_from_address(monkeypatch):
    configure(monkeypatch)

    sent = {}

    def fake_send(params):
        sent.update(params)
        return {"id": "email-4"}

    monkeypatch.setattr(
        "resend.Emails.send",
        fake_send,
    )

    send_verification_email(
        "user@example.com",
        "token",
    )

    assert sent["from"] == "Weather App <onboarding@resend.dev>"
