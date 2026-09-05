# Authentication

RecoveryPilot Phase 11A adds a JWT SaaS shell around the existing merchant ops UI. Diagnosis, policy, planner, executor, orchestrator, simulator, and webhook **domain logic are unchanged**. Existing dashboard HTTP routes stay public so current tests and internal tools keep working; the React app gates those screens.

## JWT flow

1. **Signup** `POST /api/v1/auth/signup`  
   Creates a `merchant_users` row. Password is hashed with **passlib + bcrypt** (72-byte limit). No merchant tenant yet. Returns an access JWT and a refresh JWT.

2. **Login** `POST /api/v1/auth/login`  
   Verifies bcrypt, writes `last_login_at`, inserts an `auth_sessions` row with `sha256(refresh_token)`, returns a new token pair.

3. **Access token**  
   HS256 JWT, default **15 minutes**. Claims: `sub` (user id), `email`, `merchant_id` (nullable), `sid` (session id), `typ=access`. Sent as `Authorization: Bearer`.

4. **Refresh** `POST /api/v1/auth/refresh`  
   Body `{ "refresh_token": "..." }`. The previous session is revoked and a new pair is issued (rotation). Reusing a rotated token returns `401 unauthorized`.

5. **Me** `GET /api/v1/auth/me`  
   Requires a valid access token. Returns the operator plus onboarding fields.

6. **Logout** `POST /api/v1/auth/logout`  
   Body `{ "refresh_token": "..." }`. Sets `auth_sessions.revoked_at`. Idempotent if the token is already dead.

The SPA stores both tokens in `localStorage` (`rp_access_token`, `rp_refresh_token`). On a 401 the client tries refresh once, then clears storage and sends the user to `/login`.

### Environment

```
JWT_SECRET=local-dev-jwt-secret-change-me-32b!!
JWT_ALGORITHM=HS256
JWT_ACCESS_MINUTES=15
JWT_REFRESH_DAYS=7
```

Startup fails in staging/production if `JWT_SECRET` is missing or still the local default.

## Data model

| Table | Role |
| --- | --- |
| `merchant_users` | Operator identity: email (unique, lowercase), `password_hash`, `full_name`, `merchant_id` (null until onboarding) |
| `auth_sessions` | Hashed refresh tokens, expiry, user agent, IP, `revoked_at` |
| `merchant_settings` | Onboarding step, workspace kind, Razorpay/Gemini keys, notification toggles |

Secrets in `merchant_settings` are **never** returned in full. Settings APIs return a redacted preview (`rzp_…abcd`) and booleans.

Tables are created with `checkfirst` on API startup when Postgres is reachable (same pattern as `scheduler_jobs`). Alembic revision `20260905_0001` also creates `merchant_users`, `auth_sessions`, and `merchant_settings`.

## Onboarding (four steps)

All routes require a bearer token.

| Step | Endpoint | Writes |
| --- | --- | --- |
| 1 Merchant info | `POST /api/v1/onboarding/merchant` | `merchants` + zeroed `merchant_metrics` + `merchant_settings` |
| 2 Business type | `POST /api/v1/onboarding/business` | `merchants.business_category` |
| 3 Razorpay Sandbox | `POST /api/v1/onboarding/razorpay` | key id/secret/webhook on `merchant_settings` (never logged) |
| 4 Workspace | `POST /api/v1/onboarding/workspace` | `workspace_kind=demo\|empty`, `onboarding_completed=true` |

`GET /api/v1/onboarding` returns the current user projection. `GET /api/v1/onboarding/business-types` lists allowed categories.

**Demo** keeps the existing FitLife snapshot in the ops UI. **Empty** selects the new merchant id (live APIs return zeros until traffic exists). Step 4 does **not** call `simulator.seed_database` (that path truncates domain tables).

## Frontend guards

- `/` public landing
- `/login`, `/signup` (`GuestOnly` — signed-in users skip them)
- `/onboarding` (`RequireAuth` + unfinished onboarding)
- `/dashboard`, `/recovery-queue`, `/analytics`, `/audit`, `/simulator`, `/operations`, `/settings` (`RequireAuth` + `RequireOnboarding`)

Unauthenticated visits to a protected path redirect to `/login?next=…`.

## Settings

`GET/PATCH /api/v1/account/settings/*` and `POST /api/v1/account/settings/password`. Tabs: Profile, Razorpay, Gemini, Notifications, Security (password + session list + revoke-all).

Recovery engines **still read process environment** for Razorpay and Gemini. Keys saved here are the merchant UI source of truth for Phase 11A; they are not injected into the executor in this phase.

## Errors

Auth failures use the standard envelope (`message` mirrors `error` for the SPA):

```json
{
  "success": false,
  "error": "Invalid email or password",
  "message": "Invalid email or password",
  "code": "unauthorized|invalid_credentials|email_taken|validation_error|database_unavailable|auth_schema_missing"
}
```

PostgreSQL down or missing `merchant_users` / `auth_sessions` returns **503**, not a generic 500. Unhandled failures say "Something went wrong. Please try again in a moment."

These are `ApplicationException` subclasses, so Sentry `before_send` drops them as expected business errors.
