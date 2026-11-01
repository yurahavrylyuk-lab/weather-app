# Email Authentication, Verification & Recovery Design

## Intent
Extend the existing FastAPI + JWT authentication system without replacing it. Add email as a required identity for new registrations, allow username-or-email login, require email verification before new accounts can log in, add forgot/reset password, and add profile flows for changing email and password.

## Constraints
- Keep the existing Vercel `*.vercel.app` deployment as the website and link domain.
- Use Resend in test mode for now; do not require a custom sender domain yet.
- Preserve the current 30-minute access JWT + rolling 30-day refresh JWT architecture.
- Keep public weather search available to guests.
- Preserve existing database rows and existing username/password accounts during migration.
- Never store plaintext passwords or plaintext action tokens.

## User model
Add nullable `email`, `email_verified`, and `auth_version` fields to `User`.

Existing users are treated as legacy accounts: they may continue username/password login even when `email` is null, but they cannot use email login or email recovery until they add and verify an email. New registrations must include an email and cannot log in until it is verified.

## Action tokens
Use one `AuthActionToken` table for verification/recovery operations:
- `id`
- `user_id`
- `token_hash`
- `purpose`: `verify_email`, `reset_password`, or `change_email`
- `target_email` when needed
- `expires_at`
- `used_at`
- `created_at`

Generate raw tokens with `secrets.token_urlsafe(32)`. Store only a SHA-256 hash. Tokens are single-use.

Expiry targets:
- email verification: 24 hours
- password reset: 30 minutes
- email change: 60 minutes

## Registration and verification
Registration requires username, email, password, and preferred city. Email is normalized to lowercase and must be unique. The user is created with `email_verified = false`; no authenticated session is issued. A verification email is sent.

The email link uses the Vercel application URL and query parameters, for example `/?verify_email_token=...`. The frontend detects the token, opens the verification UI, calls the verification endpoint, then removes the token from the browser address bar with `history.replaceState`.

Unverified new users cannot log in. The login UI offers resend verification.

## Login
Keep the existing `/api/token` endpoint and OAuth form structure. The existing `username` field becomes a generic identifier. Authentication accepts either exact username or normalized email plus password.

## Forgot/reset password
`POST /api/password-reset/request` accepts an email and always returns a generic success response so account existence is not disclosed. If a verified account exists, create a 30-minute reset token and send the reset link.

The reset link uses `/?reset_password_token=...`. The website opens a reset-password form for new password + confirmation. `POST /api/password-reset/confirm` validates the token, updates the password hash, marks the token used, increments `auth_version`, and invalidates all previously issued JWTs.

## Session invalidation
Add `auth_version` to both access and refresh JWT payloads. Protected access and refresh paths compare the JWT version with the current user row. Password change/reset increments the user's version so all old access/refresh tokens become invalid.

## Profile email change
A signed-in user supplies a new email and current password. The existing verified email remains active until the new email is verified. A `change_email` token stores the new target email. Successful verification atomically replaces the email and leaves the session active.

## Profile password change
A signed-in user supplies current password, new password, and confirmation. The backend verifies the current password, stores the new hash, increments `auth_version`, and issues a fresh access/refresh session for the current browser.

## Email delivery
Add an email service module that wraps Resend. `RESEND_API_KEY` is server-only. Links derive from `APP_BASE_URL` when set, otherwise Vercel's runtime URL, otherwise localhost for local development.

For the no-custom-domain phase, Resend is integration/test infrastructure only. The implementation must be provider-isolated so switching the sender/domain later requires configuration, not auth rewrites.

## Database migrations
Introduce Alembic. The migration must preserve existing rows, add nullable email safely, add `email_verified` and `auth_version`, and create the action-token table and indexes. `SQLModel.metadata.create_all()` may remain useful for local scratch databases/tests but production schema evolution is owned by Alembic.

## Frontend
Extend the current account dialog rather than create a second auth application. Add:
- Email field to registration
- `Username or email` login label
- `Forgot password?`
- verification state + resend action
- reset-password form opened from the reset token query parameter
- profile email change form
- profile password change form

## Security requirements
- Generic forgot-password response
- Unique normalized email
- Hashed, expiring, single-use action tokens
- Current-password confirmation for email/password changes
- Mandatory verification for new accounts
- No token values in logs
- JWT version invalidation after password change/reset
- Existing public weather access remains unchanged
