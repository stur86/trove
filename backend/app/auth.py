"""
Admin authentication dependency for Trove FastAPI routes.

Provides require_admin(), a FastAPI dependency that validates HTTP Basic
credentials against the stored admin_username / admin_password in TroveConfig.
Import this in any router that needs admin-gated endpoints.
"""
import hmac
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.config.service import load_config

_security = HTTPBasic()


def require_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> None:
    """
    Verify admin credentials from HTTP Basic auth.

    Raises HTTP 401 if:
    - admin_password is empty (setup not complete)
    - username or password do not match config
    """
    config = load_config()
    # Use timing-safe comparison to prevent timing attacks on credential checks
    username_ok = hmac.compare_digest(credentials.username, config.admin_username)
    password_ok = hmac.compare_digest(credentials.password, config.admin_password)
    if not config.admin_password or not username_ok or not password_ok:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials or admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )

def require_admin_cookie(admin_auth: str = Cookie(None)) -> None:
    """
    Verify admin credentials from HTTP cookie.

    Raises HTTP 401 if:
    - admin_auth cookie is not set to "true"
    """
    if admin_auth != "true":
        raise HTTPException(
            status_code=401,
            detail="Admin authentication cookie missing or invalid. Please log in as admin.",
        )