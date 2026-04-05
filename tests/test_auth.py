"""Tests on authentication for app domain admin endpoints."""
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
import pytest
from pathlib import Path
from backend.app.auth import require_admin, require_admin_cookie
from backend.config.models import TroveConfig

# Fixture to have all tests use the same admin credentials in config
@pytest.fixture(autouse=True)
def set_admin_credentials(config_dir: Path):
    config_file_path = config_dir / "config.json" 
    config = TroveConfig(admin_username="admin", admin_password="password")
    config_file_path.write_text(config.model_dump_json(indent=2))

def test_require_admin_valid_credentials():
    """require_admin() should pass with correct credentials."""
    require_admin(credentials=HTTPBasicCredentials(username="admin", password="password"))
    
def test_require_admin_invalid_credentials():
    """require_admin() should raise HTTPException with wrong credentials."""
    with pytest.raises(HTTPException) as exc_info:
        require_admin(credentials=HTTPBasicCredentials(username="admin", password="wrong"))
    assert exc_info.value.status_code == 401
    
def test_require_admin_cookie_valid():
    """require_admin_cookie() should pass with correct cookie."""
    require_admin_cookie(admin_auth="true")
    
def test_require_admin_cookie_invalid():
    """require_admin_cookie() should raise HTTPException with wrong cookie."""
    with pytest.raises(HTTPException) as exc_info:
        require_admin_cookie(admin_auth="false")
    assert exc_info.value.status_code == 401
