"""Tests for the FastAPI application factory and mode routing."""
import pytest
from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok():
    """GET /api/health must always return 200 — it is exempt from session auth."""
    from backend.main import create_app_app
    client = TestClient(create_app_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mode_endpoint_returns_setup(session_token):
    """GET /api/mode returns the mode the app was created with."""
    from backend.main import create_app_setup
    client = TestClient(create_app_setup(), headers={"X-Trove-Session": session_token})
    response = client.get("/api/mode")
    assert response.status_code == 200
    assert response.json() == {"mode": "setup"}


def test_mode_endpoint_returns_app(session_token):
    """GET /api/mode returns 'app' when the app is created in app mode."""
    from backend.main import create_app_app
    client = TestClient(create_app_app(), headers={"X-Trove-Session": session_token})
    assert client.get("/api/mode").json() == {"mode": "app"}


def test_setup_router_only_in_setup_mode(session_token):
    """Setup endpoints must not exist in app mode."""
    from backend.main import create_app_app
    client = TestClient(create_app_app(), headers={"X-Trove-Session": session_token})
    response = client.get("/api/setup/status")
    assert response.status_code == 404


def test_app_router_only_in_app_mode(session_token):
    """App endpoints must not exist in setup mode."""
    from backend.main import create_app_setup
    client = TestClient(create_app_setup(), headers={"X-Trove-Session": session_token})
    response = client.get("/api/app/status")
    assert response.status_code == 404


def test_config_get_always_available(session_token):
    """GET /api/config must be reachable in both modes."""
    from backend.main import create_app_setup, create_app_app
    for mode in ("setup", "app"):
        client = TestClient(
            create_app_setup() if mode == "setup" else create_app_app(),
            headers={"X-Trove-Session": session_token},
        )
        assert client.get("/api/config").status_code == 200, f"Failed in {mode} mode"


def test_config_put_removed_from_shared_router(session_token):
    """PUT /api/config no longer exists — moved to /api/app/admin/config."""
    from backend.main import create_app_app
    client = TestClient(create_app_app(), headers={"X-Trove-Session": session_token})
    response = client.put(
        "/api/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": ""},
    )
    assert response.status_code in (404, 405)


def test_api_routes_reachable_without_frontend_dist():
    """GET /api/health works with no frontend build — it is exempt from session auth."""
    from backend.main import create_app_app
    client = TestClient(create_app_app())
    assert client.get("/api/health").status_code == 200


# ── New session-specific tests ────────────────────────────────────────────────

def test_session_endpoint_returns_token():
    """/api/session must return a non-empty token string without any auth."""
    from backend.main import create_app_app
    client = TestClient(create_app_app())
    response = client.get("/api/session")
    assert response.status_code == 200
    assert "token" in response.json()
    assert len(response.json()["token"]) > 0


def test_api_blocked_without_session_token():
    """Any non-exempt /api/ path must return 401 without X-Trove-Session."""
    from backend.main import create_app_app
    client = TestClient(create_app_app())
    assert client.get("/api/mode").status_code == 401


def test_api_allowed_with_valid_session_token():
    """A valid X-Trove-Session token must allow access to protected /api/ paths."""
    from backend.main import create_app_app
    from backend.session import session_store
    token = session_store.create()
    client = TestClient(create_app_app(), headers={"X-Trove-Session": token})
    assert client.get("/api/mode").status_code == 200


def test_exempt_health_needs_no_session_token():
    """/api/health must be reachable without any session token."""
    from backend.main import create_app_app
    assert TestClient(create_app_app()).get("/api/health").status_code == 200


def test_exempt_i18n_needs_no_session_token():
    """/api/i18n/<locale> must be reachable without any session token."""
    from backend.main import create_app_app
    assert TestClient(create_app_app()).get("/api/i18n/en").status_code == 200


def test_invalid_session_token_returns_401():
    """A made-up X-Trove-Session value must be rejected with 401."""
    from backend.main import create_app_app
    client = TestClient(create_app_app(), headers={"X-Trove-Session": "not-a-real-token"})
    assert client.get("/api/mode").status_code == 401
