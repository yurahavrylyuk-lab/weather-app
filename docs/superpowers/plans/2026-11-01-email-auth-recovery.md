# Email Authentication & Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add mandatory verified-email registration, username-or-email login, password recovery by email, and profile email/password changes while preserving the existing JWT session model and public weather access.

**Architecture:** Extend the existing `User` model and JWT helpers, add hashed single-use action tokens, introduce Alembic for production schema migrations, isolate Resend behind an email-service module, and extend the existing auth dialog/UI. Existing username-only accounts remain usable and can add/verify email later.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, Alembic, pwdlib, PyJWT, Resend Python SDK, Neon PostgreSQL, vanilla HTML/CSS/JS, Vercel.

**Spec:** `docs/superpowers/specs/2026-11-01-email-auth-recovery-design.md`

## Global Constraints

- New registrations require a unique normalized email and cannot log in before verification.
- Existing accounts with `email = null` retain username/password login.
- Website/reset/verification links use the existing Vercel app URL.
- Resend remains test-mode infrastructure until a custom sender domain is introduced.
- Access JWT lifetime remains 30 minutes; refresh JWT lifetime remains rolling 30 days.
- Action tokens are random, hashed in storage, expiring, and single-use.
- Password change/reset invalidates old JWTs through `auth_version`.
- Public weather search remains guest-accessible.

## Review Focus

- Case-insensitive duplicate emails must be rejected.
- Forgot-password must not disclose whether an account exists.
- Expired/used/wrong-purpose action tokens must fail safely.
- Password change/reset must invalidate previously issued refresh JWTs.
- Legacy users without email must still be able to log in by username.

---

### Task 1: Database migration foundation

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/<revision>_add_email_auth_fields.py`
- Modify: `backend/models.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_email_auth_models.py`

**Interfaces:**
- Produces `User.email`, `User.email_verified`, `User.auth_version`, and `AuthActionToken`.

- [ ] Write failing model tests for nullable legacy email, normalized/unique email support at application level, default `email_verified=False`, default `auth_version=1`, and action-token fields.
- [ ] Run the focused test and verify RED.
- [ ] Add model fields/classes and Alembic dependency/configuration.
- [ ] Create migration that preserves existing users and adds the token table/indexes.
- [ ] Run focused tests and migration smoke test; verify GREEN.
- [ ] Commit: `feat: add email auth database schema`

### Task 2: Email normalization and username-or-email authentication

**Files:**
- Modify: `backend/auth.py`
- Modify: `backend/app.py`
- Modify: `backend/models.py`
- Test: `backend/tests/test_email_login.py`
- Test: `backend/tests/test_registration.py`

**Interfaces:**
- Produces `normalize_email(email: str) -> str`.
- `authenticate_user(session, identifier, password)` accepts username or email.

- [ ] Add RED tests for email normalization, duplicate normalized email rejection, username login, email login, wrong-password rejection, legacy username-only login, and unverified new-user login rejection.
- [ ] Implement normalization and identifier lookup.
- [ ] Extend registration payload with required email for new users.
- [ ] Block login for users with a non-null, unverified email.
- [ ] Run focused tests and existing auth tests; verify GREEN.
- [ ] Commit: `feat: add email identity and login`

### Task 3: JWT auth-version invalidation

**Files:**
- Modify: `backend/auth.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_auth_version.py`

**Interfaces:**
- Access/refresh JWTs carry `auth_version`.
- Protected access and refresh compare token version with the current user row.

- [ ] Add RED tests proving stale access and refresh tokens fail after version increment.
- [ ] Add `auth_version` to token creation and validation.
- [ ] Run focused and refresh-session tests; verify GREEN.
- [ ] Commit: `feat: invalidate stale auth sessions`

### Task 4: Action-token service

**Files:**
- Create: `backend/action_tokens.py`
- Test: `backend/tests/test_action_tokens.py`

**Interfaces:**
- `create_action_token(session, user, purpose, expires_in, target_email=None) -> str`
- `consume_action_token(session, raw_token, purpose) -> AuthActionToken | None`

- [ ] Add RED tests for SHA-256 storage, single use, expiry, wrong purpose, and target email preservation.
- [ ] Implement token generation/hash/consume helpers.
- [ ] Run focused tests; verify GREEN.
- [ ] Commit: `feat: add secure auth action tokens`

### Task 5: Email delivery abstraction

**Files:**
- Create: `backend/email_service.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_email_service.py`

**Interfaces:**
- `send_verification_email(email, token)`
- `send_password_reset_email(email, token)`
- `send_email_change_verification(email, token)`

- [ ] Add RED tests using a mocked Resend client; no real email in automated tests.
- [ ] Implement provider wrapper using `RESEND_API_KEY`, `APP_BASE_URL`, and configurable sender.
- [ ] Ensure raw token is used only in email URL and never logged.
- [ ] Run focused tests; verify GREEN.
- [ ] Commit: `feat: add transactional auth emails`

### Task 6: Mandatory email verification

**Files:**
- Modify: `backend/app.py`
- Modify: `frontend/index.html`
- Modify: `frontend/auth.js`
- Modify: `frontend/style.css`
- Test: `backend/tests/test_email_verification.py`
- Test: `backend/tests/test_frontend_ui.py`

**Interfaces:**
- `POST /api/email/verify`
- `POST /api/email/resend-verification`

- [ ] Add RED backend tests for verification, expiry, reuse, duplicate target, and resend behavior.
- [ ] Add RED frontend contract tests for registration email field, verification state, and query-token handling.
- [ ] Implement registration email dispatch and verification endpoints.
- [ ] Add frontend verification UI and resend action.
- [ ] Strip token query parameters after processing with `history.replaceState`.
- [ ] Run focused tests; verify GREEN.
- [ ] Commit: `feat: require verified email registration`

### Task 7: Forgot/reset password flow

**Files:**
- Modify: `backend/app.py`
- Modify: `frontend/index.html`
- Modify: `frontend/auth.js`
- Modify: `frontend/style.css`
- Test: `backend/tests/test_password_reset.py`
- Test: `backend/tests/test_frontend_ui.py`

**Interfaces:**
- `POST /api/password-reset/request`
- `POST /api/password-reset/confirm`

- [ ] Add RED tests for generic request responses, verified-account email dispatch, unverified/unknown email privacy, token expiry/reuse, password replacement, and `auth_version` increment.
- [ ] Implement request/confirm endpoints.
- [ ] Add Forgot Password and Reset Password panels opened from reset-token query parameter.
- [ ] Run focused tests and JWT invalidation tests; verify GREEN.
- [ ] Commit: `feat: add password recovery flow`

### Task 8: Profile email change

**Files:**
- Modify: `backend/app.py`
- Modify: `frontend/index.html`
- Modify: `frontend/auth.js`
- Modify: `frontend/style.css`
- Test: `backend/tests/test_email_change.py`

**Interfaces:**
- `POST /api/users/me/email`
- `POST /api/email/confirm-change`

- [ ] Add RED tests for current-password requirement, duplicate email rejection, keeping old email active until confirmation, token expiry/reuse, and successful replacement.
- [ ] Implement request/confirm endpoints.
- [ ] Add profile email display/change UI.
- [ ] Run focused tests; verify GREEN.
- [ ] Commit: `feat: add profile email change`

### Task 9: Profile password change

**Files:**
- Modify: `backend/app.py`
- Modify: `frontend/index.html`
- Modify: `frontend/auth.js`
- Modify: `frontend/style.css`
- Test: `backend/tests/test_password_change.py`

**Interfaces:**
- `POST /api/users/me/password`
- Returns a fresh authenticated session after successful password change.

- [ ] Add RED tests for wrong current password, password confirmation mismatch, new hash, auth-version increment, stale-token rejection, and fresh-session issuance.
- [ ] Implement endpoint and refresh-cookie replacement.
- [ ] Add profile password-change UI.
- [ ] Run focused tests; verify GREEN.
- [ ] Commit: `feat: add profile password change`

### Task 10: Full regression and deployment validation

**Files:**
- Modify tests/documentation only as needed.

- [ ] Run complete backend test suite.
- [ ] Run `node --check frontend/auth.js` and `node --check frontend/script.js`.
- [ ] Run `git diff --check` and confirm clean status.
- [ ] Validate legacy username-only login locally.
- [ ] Validate new registration → verification → login locally with Resend test delivery.
- [ ] Validate forgot/reset password locally.
- [ ] Validate profile email/password changes locally.
- [ ] Push feature branch and deploy Vercel Preview.
- [ ] Apply Alembic migration to Preview/Neon target before exercising new columns.
- [ ] Validate secure-cookie browser-restart session behavior on Preview.
- [ ] Create PR and inspect checks/mergeability.
- [ ] After explicit merge approval, merge to `main`, verify production migration/deployment, and repeat critical E2E flows.
