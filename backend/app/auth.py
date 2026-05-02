"""
Admin authentication dependency for Trove FastAPI routes.

Provides:
  hash_password(password)        — bcrypt hash for storage during setup
  verify_password(plain, hashed) — constant-time bcrypt check
  require_admin()                — FastAPI dependency: validates HTTP Basic credentials
  require_admin_cookie()         — FastAPI dependency: validates admin session cookie

  ADMIN_LOGIN_ALLOWED_HOSTS      — list of hosts permitted to access the login endpoint
                                   (extended in Task 5; defined here for central visibility)
"""
import hmac
from typing import Annotated

import bcrypt
from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.config.service import load_config
from backend.session import admin_store

_security = HTTPBasic()

# Hosts permitted to call the admin login endpoint.
# Extend this list if mDNS or a fixed hostname is added in future.
ADMIN_LOGIN_ALLOWED_HOSTS: list[str] = ["127.0.0.1", "::1"]


def hash_password(password: str) -> str:
    """
    Hash a plaintext password with bcrypt.

    Call this during setup when writing credentials to config.json.
    Never call it on already-hashed input.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Returns True if they match, False otherwise.
    """
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def require_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> None:
    """
    Verify admin credentials from HTTP Basic auth.

    Raises HTTP 401 if:
    - admin_password is empty (setup not complete)
    - username or password do not match config

    Both username and password checks always run to prevent timing attacks
    that would reveal whether a submitted username is recognised.
    """
    config = load_config()
    if not config.admin_password:
        raise HTTPException(
            status_code=401,
            detail="Admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )
    # hmac.compare_digest is timing-safe for the username string comparison.
    username_ok = hmac.compare_digest(credentials.username, config.admin_username)
    # Always call verify_password so response time does not reveal whether
    # the username was recognised (timing-safe constant-time behaviour).
    password_ok = verify_password(credentials.password, config.admin_password)
    if not username_ok or not password_ok:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials or admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )


def require_admin_cookie(admin_auth: str = Cookie(None)) -> None:
    """
    Verify the admin session cookie against the in-memory admin token store.

    Raises HTTP 401 if the cookie is absent or its value is not a live admin token.
    The cookie value is a cryptographically random string set by the login endpoint.
    """
    if not admin_auth or not admin_store.validate_and_refresh(admin_auth):
        raise HTTPException(
            status_code=401,
            detail="Admin authentication cookie missing or invalid. Please log in as admin.",
        )
