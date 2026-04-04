"""Tests for the FastAPI application factory and mode routing."""
import pytest
from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok():
    """GET /api/health must always return 200 regardless of mode."""
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mode_endpoint_returns_setup():
    """GET /api/mode returns the mode the app was created with."""
    from backend.main import create_app
    client = TestClient(create_app(mode="setup"))
    response = client.get("/api/mode")
    assert response.status_code == 200
    assert response.json() == {"mode": "setup"}


def test_mode_endpoint_returns_app():
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    response = client.get("/api/mode")
    assert response.json() == {"mode": "app"}


def test_setup_router_only_in_setup_mode():
    """Setup endpoints must not exist in app mode."""
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    response = client.get("/api/setup/status")
    assert response.status_code == 404


def test_app_router_only_in_app_mode():
    """App endpoints must not exist in setup mode."""
    from backend.main import create_app
    client = TestClient(create_app(mode="setup"))
    response = client.get("/api/app/status")
    assert response.status_code == 404


def test_config_get_always_available():
    """GET /api/config must be reachable in both modes."""
    from backend.main import create_app
    for mode in ("setup", "app"):
        client = TestClient(create_app(mode=mode))
        response = client.get("/api/config")
        assert response.status_code == 200, f"Failed in {mode} mode"


def test_config_put_removed_from_shared_router():
    """PUT /api/config no longer exists — it moved to /api/app/admin/config.

    FastAPI returns 405 (Method Not Allowed) rather than 404 because the path
    /api/config is still registered for GET; 405 confirms PUT is not available.
    """
    from backend.main import create_app
    # In app mode the endpoint exists under /api/app/admin/config, not /api/config
    client = TestClient(create_app(mode="app"))
    response = client.put("/api/config", json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en", "admin_username": "admin", "admin_password": ""})
    # 405 = method exists on path but PUT is not registered; PUT is not available
    assert response.status_code in (404, 405)


def test_api_routes_reachable_without_frontend_dist():
    """API routes work even when frontend/dist/ does not exist (dev mode)."""
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    response = client.get("/api/health")
    assert response.status_code == 200
