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

from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext

from backend.config.service import load_config

_security = HTTPBasic()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hosts permitted to call the admin login endpoint.
# Extend this list if mDNS or a fixed hostname is added in future.
ADMIN_LOGIN_ALLOWED_HOSTS: list[str] = ["127.0.0.1", "::1"]


def hash_password(password: str) -> str:
    """
    Hash a plaintext password with bcrypt.

    Call this during setup when writing credentials to config.json.
    Never call it on already-hashed input.
    """
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Returns True if they match, False otherwise.
    """
    return _pwd_context.verify(plain, hashed)


def require_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> None:
    """
    Verify admin credentials from HTTP Basic auth.

    Raises HTTP 401 if:
    - admin_password is empty (setup not complete)
    - username does not match config
    - password does not match the stored bcrypt hash
    """
    config = load_config()
    # Reject immediately if setup is incomplete or username is wrong.
    # Username comparison is timing-safe; bcrypt verify is inherently slow.
    username_ok = hmac.compare_digest(credentials.username, config.admin_username)
    if not config.admin_password or not username_ok:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials or admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not verify_password(credentials.password, config.admin_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials or admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )


def require_admin_cookie(admin_auth: str = Cookie(None)) -> None:
    """
    Verify admin credentials from HTTP cookie.

    Raises HTTP 401 if the admin_auth cookie is absent or not equal to 'true'.
    Note: this check is replaced with a token-store lookup in Task 4.
    """
    if admin_auth != "true":
        raise HTTPException(
            status_code=401,
            detail="Admin authentication cookie missing or invalid. Please log in as admin.",
        )
