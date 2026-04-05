"""Tests for the Gems REST API endpoints."""
import base64
import pytest
from fastapi.testclient import TestClient

from backend.tasks.models import GemHue, StringArg, UserTask
from backend.tasks.repository import save_task


def _auth(username: str = "admin", password: str = "testpass") -> str:
    return f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"


@pytest.fixture
def client(config_dir, data_dir, monkeypatch):
    """App-mode TestClient with admin credentials and fake services."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.config.service import load_config, save_config
    cfg = load_config()
    cfg = cfg.model_copy(update={"admin_username": "admin", "admin_password": "testpass"})
    save_config(cfg)
    from backend.main import create_app_app
    return TestClient(create_app_app())


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


def test_create_gem_with_auth(client):
    payload = {"id": "new-gem", "name": "New Gem", "template": "Hi {{ name }}",
               "args": [{"type": "string", "name": "name", "description": "", "default": ""}],
               "has_image": False, "has_audio": False, "output_mode": "text",
               "description": "A new gem", "hue": "rose"}
    res = client.post("/api/app/admin/gems", json=payload,
                      headers={"Authorization": _auth()})
    assert res.status_code == 201
    assert res.json()["id"] == "new-gem"


# --- Update ---

def test_update_gem_requires_auth(client, sample_gem):
    payload = {"id": "hello", "name": "Updated", "template": "Hi",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "indigo"}
    res = client.put("/api/app/admin/gems/hello", json=payload)
    assert res.status_code == 401


def test_update_gem_not_found(client):
    payload = {"id": "ghost", "name": "Ghost", "template": "Boo",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "indigo"}
    res = client.put("/api/app/admin/gems/ghost", json=payload,
                     headers={"Authorization": _auth()})
    assert res.status_code == 404


def test_update_gem_id_mismatch(client, sample_gem):
    payload = {"id": "different-id", "name": "Updated", "template": "Hi",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "indigo"}
    res = client.put("/api/app/admin/gems/hello", json=payload,
                     headers={"Authorization": _auth()})
    assert res.status_code == 422


def test_update_gem_success(client, sample_gem):
    payload = {"id": "hello", "name": "Updated Hello", "template": "Hi {{ name }}",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "sky"}
    res = client.put("/api/app/admin/gems/hello", json=payload,
                     headers={"Authorization": _auth()})
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Hello"


# --- Delete ---

def test_delete_gem_requires_auth(client, sample_gem):
    res = client.delete("/api/app/admin/gems/hello")
    assert res.status_code == 401


def test_delete_gem_success(client, sample_gem):
    res = client.delete("/api/app/admin/gems/hello",
                        headers={"Authorization": _auth()})
    assert res.status_code == 204
    assert client.get("/api/app/gems/hello").status_code == 404


def test_delete_gem_not_found(client):
    res = client.delete("/api/app/admin/gems/ghost",
                        headers={"Authorization": _auth()})
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
