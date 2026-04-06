"""Tests for the Gems REST API endpoints."""
import pytest
from fastapi.testclient import TestClient

from backend.tasks.models import GemHue, StringArg, UserTask
from backend.tasks.repository import save_task


@pytest.fixture
def client(config_dir, data_dir, monkeypatch):
    """App-mode TestClient without admin cookie (for testing unauthenticated access)."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.config.service import load_config, save_config
    cfg = load_config()
    cfg = cfg.model_copy(update={"admin_username": "admin", "admin_password": "testpass"})
    save_config(cfg)
    from backend.main import create_app_app
    return TestClient(create_app_app())


@pytest.fixture
def authed_client(client):
    """TestClient with the admin_auth cookie pre-set (for testing authenticated access)."""
    client.cookies.set("admin_auth", "true")
    return client


@pytest.fixture
def sample_gem(data_dir):
    task = UserTask(
        id="hello",
        name="Hello Gem",
        description="Says hello",
        template="Hello, {{ name }}!",
        args=(StringArg(name="name", default="World"),),
        hue=GemHue.EMERALD,
    )
    save_task(task)
    return task


# --- List ---

def test_list_gems_empty(client):
    res = client.get("/api/app/gems")
    assert res.status_code == 200
    assert res.json() == []


def test_list_gems_returns_saved(client, sample_gem):
    res = client.get("/api/app/gems")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "hello"
    assert data[0]["hue"] == "emerald"


# --- Get single ---

def test_get_gem_found(client, sample_gem):
    res = client.get("/api/app/gems/hello")
    assert res.status_code == 200
    assert res.json()["name"] == "Hello Gem"


def test_get_gem_not_found(client):
    res = client.get("/api/app/gems/missing")
    assert res.status_code == 404


# --- Create ---

def test_create_gem_requires_auth(client):
    payload = {"id": "new", "name": "New", "template": "Hi", "args": [], "has_image": False,
               "has_audio": False, "output_mode": "text", "description": "", "hue": "indigo"}
    res = client.post("/api/app/admin/gems", json=payload)
    assert res.status_code == 401


def test_create_gem_with_auth(authed_client):
    payload = {"id": "new-gem", "name": "New Gem", "template": "Hi {{ name }}",
               "args": [{"type": "string", "name": "name", "description": "", "default": ""}],
               "has_image": False, "has_audio": False, "output_mode": "text",
               "description": "A new gem", "hue": "rose"}
    res = authed_client.post("/api/app/admin/gems", json=payload)
    assert res.status_code == 201
    assert res.json()["id"] == "new-gem"


# --- Update ---

def test_update_gem_requires_auth(client, sample_gem):
    payload = {"id": "hello", "name": "Updated", "template": "Hi",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "indigo"}
    res = client.put("/api/app/admin/gems/hello", json=payload)
    assert res.status_code == 401


def test_update_gem_not_found(authed_client):
    payload = {"id": "ghost", "name": "Ghost", "template": "Boo",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "indigo"}
    res = authed_client.put("/api/app/admin/gems/ghost", json=payload)
    assert res.status_code == 404


def test_update_gem_id_mismatch(authed_client, sample_gem):
    payload = {"id": "different-id", "name": "Updated", "template": "Hi",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "indigo"}
    res = authed_client.put("/api/app/admin/gems/hello", json=payload)
    assert res.status_code == 422


def test_update_gem_success(authed_client, sample_gem):
    payload = {"id": "hello", "name": "Updated Hello", "template": "Hi {{ name }}",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "sky"}
    res = authed_client.put("/api/app/admin/gems/hello", json=payload)
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Hello"


# --- Delete ---

def test_delete_gem_requires_auth(client, sample_gem):
    res = client.delete("/api/app/admin/gems/hello")
    assert res.status_code == 401


def test_delete_gem_success(authed_client, sample_gem):
    res = authed_client.delete("/api/app/admin/gems/hello")
    assert res.status_code == 204
    assert authed_client.get("/api/app/gems/hello").status_code == 404


def test_delete_gem_not_found(authed_client):
    res = authed_client.delete("/api/app/admin/gems/ghost")
    assert res.status_code == 404


# --- Run ---

def test_run_gem_streams_sse(client, sample_gem, monkeypatch):
    async def fake_stream(task, values, **kwargs):
        yield "Hello"
        yield " world"

    monkeypatch.setattr("backend.tasks.router.stream_task", fake_stream)
    res = client.post("/api/app/gems/hello/run", json={"values": {"name": "Alice"}})
    assert res.status_code == 200
    assert "Hello" in res.text
    assert "[DONE]" in res.text


def test_run_gem_not_found(client):
    res = client.post("/api/app/gems/missing/run", json={"values": {}})
    assert res.status_code == 404


# --- /capabilities ---

def test_capabilities_returns_audio_true_for_e4b(client):
    """Default config uses gemma4:e4b which supports audio."""
    res = client.get("/api/app/capabilities")
    assert res.status_code == 200
    assert res.json() == {"audio": True}


def test_capabilities_returns_audio_false_for_26b(client):
    from backend.config.service import load_config, save_config
    cfg = load_config()
    cfg = cfg.model_copy(update={"base_model": "gemma4:26b"})
    save_config(cfg)
    res = client.get("/api/app/capabilities")
    assert res.status_code == 200
    assert res.json() == {"audio": False}


# --- Run with base64 media ---

import base64  # noqa: E402


def test_run_gem_passes_image_media_to_runner(client, sample_gem, monkeypatch):
    """Base64 image in request is decoded and passed as MediaInput to stream_task."""
    from backend.tasks.models import MediaInput
    captured: list = []

    async def fake_stream(task, values, *, media=None, _agent=None):
        captured.append(media)
        yield "ok"

    monkeypatch.setattr("backend.tasks.router.stream_task", fake_stream)

    img_bytes = b"\xff\xd8\xff\xe0"
    img_b64 = base64.b64encode(img_bytes).decode()

    res = client.post(
        f"/api/app/gems/{sample_gem.id}/run",
        json={"values": {"name": "World"}, "image": img_b64, "image_mime": "image/jpeg"},
    )
    assert res.status_code == 200
    assert len(captured) == 1
    assert captured[0] is not None
    assert captured[0].has_image
    assert captured[0].image == img_bytes
    assert captured[0].image_mime == "image/jpeg"


def test_run_gem_malformed_base64_returns_422(client, sample_gem):
    """Malformed base64 in the image field returns HTTP 422."""
    res = client.post(
        f"/api/app/gems/{sample_gem.id}/run",
        json={"values": {}, "image": "not-valid-base64!!!"},
    )
    assert res.status_code == 422


def test_run_gem_no_media_passes_none_to_runner(client, sample_gem, monkeypatch):
    """When no image or audio field is sent, media=None is passed to stream_task."""
    captured: list = []

    async def fake_stream(task, values, *, media=None, _agent=None):
        captured.append(media)
        yield "ok"

    monkeypatch.setattr("backend.tasks.router.stream_task", fake_stream)

    res = client.post(
        f"/api/app/gems/{sample_gem.id}/run",
        json={"values": {"name": "World"}},
    )
    assert res.status_code == 200
    assert captured[0] is None
