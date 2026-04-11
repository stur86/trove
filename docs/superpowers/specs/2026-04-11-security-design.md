# Security Design

**Date:** 2026-04-11
**Scope:** Option B — per-session token, hardened admin cookie, bcrypt password hashing, localhost-only admin login, protected logs endpoint.

## Threat model

Trove runs on a LAN server. Realistic adversaries are:
- Another browser tab or website attempting cross-origin requests to the LAN address
- A LAN user calling the API directly without a browser session
- A curious user attempting to access the admin panel from a non-server device

Out of scope: XSS from compromised frontend dependencies, browser extensions with host permissions, physical access to the server.

---

## 1. Per-session token

### Purpose
Ensure API requests originate from a legitimate Trove frontend session, not a cross-origin page. Not cryptographically binding — a script running within the Trove origin could obtain a token — but closes all realistic cross-origin and direct-API attack vectors.

### `ExpirableTokenDict` (shared utility)

A new class in `backend/session.py`. Takes `ttl: timedelta` and `sweep_interval: timedelta` as constructor parameters. Starts its own daemon `threading.Thread` on init (no lifespan management required — threads die with the process). Uses a `threading.Lock` for thread safety.

**API:**
- `create() -> str` — generates `secrets.token_urlsafe(32)`, stores with expiry `now + ttl`, returns token
- `validate_and_refresh(token: str) -> bool` — checks presence and expiry; on hit, resets expiry to `now + ttl` and returns `True`; on miss or expired, returns `False`
- `revoke(token: str) -> None` — removes token (used on admin logout)

The sweep thread runs every `sweep_interval`, removing all entries where `now > expiry`.

### Token stores

Two module-level singletons in `backend/session.py`:

```python
session_store = ExpirableTokenDict(ttl=timedelta(hours=2),  sweep_interval=timedelta(minutes=5))
admin_store   = ExpirableTokenDict(ttl=timedelta(hours=8),  sweep_interval=timedelta(minutes=5))
```

`session_store` — one entry per connected client. Sliding 2-hour TTL reset on every valid API request.
`admin_store` — one entry per active admin login. Sliding 8-hour TTL reset on every admin-authenticated request.

### Session endpoint

`GET /api/session` — no auth required, mounted as a shared route in `main.py` (alongside `/api/health` and `/api/mode`) so it is available in both setup and app mode. Calls `session_store.create()` and returns `{"token": "..."}`.

### Middleware

A `SessionMiddleware` (Starlette `BaseHTTPMiddleware`) in `main.py` intercepts all requests. For any path beginning with `/api/`, it reads the `X-Trove-Session` header and calls `session_store.validate_and_refresh()`. Returns a 401 JSON response if the token is missing or invalid.

**Exempt paths** (no session token required):
- `GET /api/session`
- `GET /api/health`
- `GET /api/i18n/{locale}` (needed for localised error messages before session is established)

All other API paths are protected.

### Frontend changes

- `fetchSession()` is called once at app init, before any other API call, and stores the returned token in module-level JS memory (not `localStorage` or `sessionStorage`).
- All API clients in `src/api/` attach `X-Trove-Session: <token>` to every request.
- The central API layer catches 401 responses, calls `fetchSession()` once to refresh the token, and retries the original request. If the retry also fails with 401, the error is surfaced to the user.

---

## 2. Hardened admin cookie

### Problem
`require_admin_cookie` currently checks `admin_auth == "true"` — trivially forgeable by any client.

### Fix
On login, the server generates a `secrets.token_urlsafe(32)` value, stores it in `admin_store`, and sets it as the `admin_auth` cookie value (httpOnly, samesite=lax). `require_admin_cookie` checks the cookie value against `admin_store` via `validate_and_refresh()` instead of comparing to a literal string.

On logout, the token is removed from `admin_store` via `revoke()`.

On server restart, `admin_store` is cleared and the admin must log in again — acceptable given login is localhost-only and intentional.

---

## 3. Password hashing

`passlib[bcrypt]` is added as a dependency. The `admin_password` field in `TroveConfig` stores a bcrypt hash. `require_admin` calls `passlib`'s `CryptContext.verify()` instead of `hmac.compare_digest`.

No migration path. Existing configs with plaintext passwords will fail the `verify()` check; the admin re-runs setup to set a new password. This is intentional — reading and re-writing a plaintext password, even transiently, is itself an exposure.

During setup, the password is hashed before being written to `config.json` for the first time.

---

## 4. Localhost-only admin login

The `/api/app/admin/login` endpoint receives a `Request` parameter and checks `request.client.host` against a named constant:

```python
ADMIN_LOGIN_ALLOWED_HOSTS: list[str] = ["127.0.0.1", "::1"]
```

Defined at the top of `backend/app/auth.py` with a comment indicating it may be extended in future (e.g. for mDNS hostnames). If the check fails, a 403 is returned before credentials are validated.

**Note:** the admin must access the UI via `http://localhost:7770`, not the LAN IP, even from the server machine. Accessing via LAN IP causes the request source to appear as a LAN address and will be rejected.

**Note:** if Trove is ever placed behind a reverse proxy, `request.client.host` will always be `127.0.0.1` (the proxy), breaking this check. This is acceptable for the current direct-uvicorn deployment model.

On the frontend, if `window.location.hostname` is not `localhost` or `127.0.0.1`, the admin login UI is hidden and replaced with a localised note explaining that admin access is only available from the server machine.

---

## 5. Protected logs endpoint

`GET /api/app/admin/logs` gains `dependencies=[Depends(require_admin_cookie)]`.

---

## Files affected

| File | Change |
|---|---|
| `backend/session.py` | New — `ExpirableTokenDict`, `session_store`, `admin_store` |
| `backend/main.py` | Add `SessionMiddleware`; mount `GET /api/session` in both modes |
| `backend/app/auth.py` | `require_admin_cookie` checks `admin_store`; add `ADMIN_LOGIN_ALLOWED_HOSTS`; bcrypt verify in `require_admin` |
| `backend/app/router.py` | Localhost check on login; protect `/admin/logs`; revoke token on logout |
| `backend/config/models.py` | Update `admin_password` docstring to reflect hashed storage |
| `backend/setup/router.py` | Hash password before saving during setup |
| `pyproject.toml` | Add `passlib[bcrypt]` dependency |
| `frontend/src/api/` | Add `fetchSession()`; attach header in all clients; 401-retry logic |
| `frontend/src/` | Hide admin login UI when not on localhost |

---

## What this does not cover

- Rate limiting on the login endpoint (can be a follow-up)
- HTTPS / TLS (stretch goal, requires mDNS or fixed hostname)
- XSS / CSP headers
- Auth for regular (non-admin) users
