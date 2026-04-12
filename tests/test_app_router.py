"""Tests for the app domain router and admin authentication."""
import base64
import pytest
from fastapi.testclient import TestClient
from backend.app.auth import hash_password


@pytest.fixture
def app_client(config_dir, monkeypatch, session_token):
    """TestClient with the app running in app mode, fake services active."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.main import create_app_app
    return TestClient(create_app_app(), headers={"X-Trove-Session": session_token})


@pytest.fixture
def app_client_with_admin(config_dir, monkeypatch, session_token):
    """App-mode client with admin credentials pre-configured (hashed) in config."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.config.service import load_config, save_config
    from backend.app.auth import hash_password
    config = load_config()
    config.admin_username = "admin"
    config.admin_password = hash_password("testpass")
    save_config(config)
    from backend.main import create_app_app
    return TestClient(create_app_app(), headers={"X-Trove-Session": session_token})


def _basic_auth(username: str, password: str) -> str:
    """Return a valid Authorization: Basic header value."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"

def test_app_login_sets_cookie(app_client_with_admin):
    """POST /admin/login with valid credentials should set a random admin_auth cookie."""
    response = app_client_with_admin.post(
        "/api/app/admin/login",
        headers={"Authorization": _basic_auth("admin", "testpass")},
    )
    assert response.status_code == 200
    cookie_val = response.cookies.get("admin_auth")
    assert cookie_val is not None
    assert cookie_val != "true"  # Must be a random token, not a literal.
    assert len(cookie_val) > 10

def test_app_login_rejects_invalid_credentials(app_client_with_admin):
    """POST /admin/login with wrong credentials should return 401."""
    response = app_client_with_admin.post(
        "/api/app/admin/login",
        headers={"Authorization": _basic_auth("admin", "wrongpass")},
    )
    assert response.status_code == 401
    assert "admin_auth" not in response.cookies
    
def test_app_logout_clears_cookie(app_client_with_admin):
    """POST /admin/logout should delete the admin_auth cookie and revoke the token."""
    login_response = app_client_with_admin.post(
        "/api/app/admin/login",
        headers={"Authorization": _basic_auth("admin", "testpass")},
    )
    assert login_response.status_code == 200
    token = login_response.cookies.get("admin_auth")
    logout_response = app_client_with_admin.post("/api/app/admin/logout")
    assert logout_response.status_code == 200
    assert logout_response.cookies.get("admin_auth") is None
    # Token must be revoked — replaying it must now fail.
    from backend.session import admin_store
    assert not admin_store.validate_and_refresh(token)


def test_app_valid_checks_cookie(app_client_with_admin, admin_token):
    """GET /admin/valid returns {valid: true} for a live admin token."""
    app_client_with_admin.cookies.set("admin_auth", admin_token)
    response = app_client_with_admin.get("/api/app/admin/valid")
    assert response.status_code == 200
    assert response.json() == {"valid": True}
    # Token value must never be reflected in the response body.
    assert admin_token not in str(response.json())


def test_app_valid_rejects_invalid_cookie(app_client_with_admin):
    """GET /admin/valid returns {valid: false} for an unrecognised cookie."""
    app_client_with_admin.cookies.set("admin_auth", "not-a-valid-token")
    response = app_client_with_admin.get("/api/app/admin/valid")
    assert response.status_code == 200
    assert response.json() == {"valid": False}

def test_app_status_reachable(app_client):
    response = app_client.get("/api/app/status")
    assert response.status_code == 200
    assert response.json()["mode"] == "app"

def test_admin_config_accepts_correct_credentials(app_client_with_admin, config_dir, admin_token):
    app_client_with_admin.cookies.set("admin_auth", admin_token)
    response = app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "it",
              "admin_username": "admin", "admin_password": hash_password("testpass")},
    )
    assert response.status_code == 200
    assert response.json()["locale"] == "it"


def test_admin_config_persists_changes(app_client_with_admin, config_dir, admin_token):
    app_client_with_admin.cookies.set("admin_auth", admin_token)
    app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:26b", "num_ctx": 16384, "locale": "en",
              "admin_username": "admin", "admin_password": hash_password("testpass")},
    )
    from backend.config.service import load_config
    config = load_config()
    assert config.base_model == "gemma4:26b"
    assert config.num_ctx == 16384


def test_admin_blocked_when_false_cookie(app_client):
    """An unrecognised cookie value must result in 401."""
    app_client.cookies.set("admin_auth", "not-a-valid-token")
    response = app_client.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": ""},
    )
    assert response.status_code == 401

def test_admin_blocked_when_missing_cookie(app_client):
    """If the admin_auth cookie is missing, all admin routes return 401."""
    response = app_client.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": ""},
    )
    assert response.status_code == 401


def test_app_router_not_available_in_setup_mode(config_dir, session_token):
    from backend.main import create_app_setup
    client = TestClient(create_app_setup(), headers={"X-Trove-Session": session_token})
    assert client.get("/api/app/status").status_code == 404


def test_build_model_requires_auth(app_client_with_admin):
    response = app_client_with_admin.post("/api/app/admin/build-model")
    assert response.status_code == 401
