"""Tests on authentication for app domain admin endpoints."""
import pytest
from pathlib import Path
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from backend.app.auth import hash_password, require_admin, require_admin_cookie, verify_password
from backend.config.models import TroveConfig


@pytest.fixture(autouse=True)
def set_admin_credentials(config_dir: Path):
    """Pre-configure admin credentials (hashed) for every test in this file."""
    config_file_path = config_dir / "config.json"
    config = TroveConfig(
        admin_username="admin",
        admin_password=hash_password("password"),
    )
    config_file_path.write_text(config.model_dump_json(indent=2))


def test_hash_password_returns_bcrypt_string():
    """hash_password() must return a bcrypt hash starting with $2b$."""
    h = hash_password("secret")
    assert h.startswith("$2b$")


def test_verify_password_correct():
    """verify_password() returns True for matching plaintext/hash pair."""
    h = hash_password("correct")
    assert verify_password("correct", h) is True


def test_verify_password_wrong():
    """verify_password() returns False for a wrong plaintext."""
    h = hash_password("correct")
    assert verify_password("wrong", h) is False


def test_require_admin_valid_credentials():
    """require_admin() should pass with correct credentials."""
    require_admin(credentials=HTTPBasicCredentials(username="admin", password="password"))


def test_require_admin_invalid_credentials():
    """require_admin() should raise HTTPException with wrong credentials."""
    with pytest.raises(HTTPException) as exc_info:
        require_admin(credentials=HTTPBasicCredentials(username="admin", password="wrong"))
    assert exc_info.value.status_code == 401


def test_require_admin_cookie_valid():
    """require_admin_cookie() passes when the cookie value is 'true' (pre-Task 4 stub)."""
    require_admin_cookie(admin_auth="true")


def test_require_admin_cookie_invalid():
    """require_admin_cookie() raises HTTPException with wrong cookie."""
    with pytest.raises(HTTPException) as exc_info:
        require_admin_cookie(admin_auth="false")
    assert exc_info.value.status_code == 401
