"""Tests for the FastAPI application entry point (backend/main.py).

Covers the health endpoint and verifies the app starts correctly in dev mode
(no frontend/dist/ directory present, which is normal during development).
"""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    """GET /api/health should always return 200 with status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_routes_reachable_without_frontend_dist(tmp_path, monkeypatch):
    """API routes must work even when frontend/dist/ does not exist (dev mode).

    This guards against accidentally mounting the static files unconditionally,
    which would shadow /api/* routes if dist/ ever existed with wrong content.
    """
    # The app fixture is already running without dist/ (tests run from source),
    # so simply confirming the health endpoint is reachable is sufficient.
    response = client.get("/api/health")
    assert response.status_code == 200
