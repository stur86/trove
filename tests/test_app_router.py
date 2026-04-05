"""Tests for the app domain router and admin authentication."""
import base64
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(config_dir, monkeypatch):
    """TestClient with the app running in app mode, fake services active."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.main import create_app_app
    return TestClient(create_app_app())


@pytest.fixture
def app_client_with_admin(config_dir, monkeypatch):
    """App-mode client with admin credentials pre-configured in config."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.config.service import load_config, save_config
    config = load_config()
    config.admin_username = "admin"
    config.admin_password = "testpass"
    save_config(config)
    from backend.main import create_app_app
    return TestClient(create_app_app())


def _basic_auth(username: str, password: str) -> str:
    """Return a valid Authorization: Basic header value."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def test_app_status_reachable(app_client):
    response = app_client.get("/api/app/status")
    assert response.status_code == 200
    assert response.json()["mode"] == "app"


def test_admin_config_requires_auth(app_client_with_admin):
    """PUT /api/app/admin/config without credentials returns 401."""
    response = app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": "testpass"},
    )
    assert response.status_code == 401


def test_admin_config_rejects_wrong_password(app_client_with_admin):
    response = app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": "testpass"},
        headers={"Authorization": _basic_auth("admin", "wrongpassword")},
    )
    assert response.status_code == 401


def test_admin_config_accepts_correct_credentials(app_client_with_admin, config_dir):
    response = app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "it",
              "admin_username": "admin", "admin_password": "testpass"},
        headers={"Authorization": _basic_auth("admin", "testpass")},
    )
    assert response.status_code == 200
    assert response.json()["locale"] == "it"


def test_admin_config_persists_changes(app_client_with_admin, config_dir):
    app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:26b", "num_ctx": 16384, "locale": "en",
              "admin_username": "admin", "admin_password": "testpass"},
        headers={"Authorization": _basic_auth("admin", "testpass")},
    )
    from backend.config.service import load_config
    config = load_config()
    assert config.base_model == "gemma4:26b"
    assert config.num_ctx == 16384


def test_admin_blocked_when_password_empty(app_client):
    """If admin_password is empty (setup not done), all admin routes return 401."""
    response = app_client.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": ""},
        headers={"Authorization": _basic_auth("admin", "")},
    )
    assert response.status_code == 401


def test_app_router_not_available_in_setup_mode(config_dir):
    from backend.main import create_app_setup
    client = TestClient(create_app_setup())
    assert client.get("/api/app/status").status_code == 404


def test_build_model_requires_auth(app_client_with_admin):
    response = app_client_with_admin.post("/api/app/admin/build-model")
    assert response.status_code == 401
