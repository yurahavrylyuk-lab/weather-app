import os

import resend


def _send_email(
    email: str,
    subject: str,
    html: str,
):
    api_key = os.getenv("RESEND_API_KEY")

    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    sender = os.getenv(
        "RESEND_FROM_EMAIL",
        "Weather App <onboarding@resend.dev>",
    )

    resend.api_key = api_key

    return resend.Emails.send(
        {
            "from": sender,
            "to": [email],
            "subject": subject,
            "html": html,
        }
    )


def _build_link(parameter: str, token: str) -> str:
    base_url = os.getenv("APP_BASE_URL")

    if not base_url:
        raise RuntimeError("APP_BASE_URL is not configured")

    base_url = base_url.rstrip("/")

    return f"{base_url}/?{parameter}={token}"


def send_verification_email(
    email: str,
    token: str,
):
    verification_link = _build_link(
        "verify_email_token",
        token,
    )

    return _send_email(
        email=email,
        subject="Verify your Weather App email",
        html=(
            "<p>Welcome to Weather App.</p>"
            "<p>Please verify your email address:</p>"
            f'<p><a href="{verification_link}">'
            "Verify email"
            "</a></p>"
        ),
    )


def send_password_reset_email(
    email: str,
    token: str,
):
    reset_link = _build_link(
        "reset_password_token",
        token,
    )

    return _send_email(
        email=email,
        subject="Reset your Weather App password",
        html=(
            "<p>A password reset was requested "
            "for your Weather App account.</p>"
            f'<p><a href="{reset_link}">'
            "Reset password"
            "</a></p>"
            "<p>If you did not request this, "
            "you can ignore this email.</p>"
        ),
    )


def send_email_change_verification(
    email: str,
    token: str,
):
    confirmation_link = _build_link(
        "change_email_token",
        token,
    )

    return _send_email(
        email=email,
        subject="Confirm your new Weather App email",
        html=(
            "<p>Please confirm this email address "
            "for your Weather App account:</p>"
            f'<p><a href="{confirmation_link}">'
            "Confirm new email"
            "</a></p>"
        ),
    )
