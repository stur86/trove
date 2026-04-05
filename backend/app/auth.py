"""
Admin authentication dependency for Trove FastAPI routes.

Provides require_admin(), a FastAPI dependency that validates HTTP Basic
credentials against the stored admin_username / admin_password in TroveConfig.
Import this in any router that needs admin-gated endpoints.
"""
from typing import Annotated

from fastapi import Depends, HTTPException
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
    if (
        not config.admin_password
        or credentials.username != config.admin_username
        or credentials.password != config.admin_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials or admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )
