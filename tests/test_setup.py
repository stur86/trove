"""Tests for the setup domain: ServiceInstaller, router endpoints, and helpers."""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# ServiceInstaller tests
# ---------------------------------------------------------------------------

def test_fake_service_installer_records_install_call(monkeypatch):
    """FakeServiceInstaller.install() yields SSE lines and records the call."""
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    lines = list(installer.install(app_port=7770))
    assert any("[DONE]" in line for line in lines)
    assert installer.calls == ["install"]


def test_fake_service_installer_records_uninstall(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    lines = list(installer.uninstall())
    assert any("[DONE]" in line for line in lines)
    assert installer.calls == ["uninstall"]


def test_fake_service_installer_records_restart(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    list(installer.restart())
    assert installer.calls == ["restart"]


def test_fake_service_not_installed_by_default(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    assert installer.is_installed() is False


def test_fake_service_is_installed_after_install(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    list(installer.install(app_port=7770))
    assert installer.is_installed() is True


def test_fake_service_not_running_by_default(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    assert installer.is_running() is False


def test_get_service_installer_returns_real_when_no_flag(monkeypatch):
    monkeypatch.delenv("TROVE_FAKE_SERVICE", raising=False)
    from backend.setup.service import get_service_installer, RealServiceInstaller
    installer = get_service_installer()
    assert isinstance(installer, RealServiceInstaller)


# ---------------------------------------------------------------------------
# LAN IP helper
# ---------------------------------------------------------------------------

def test_get_lan_ip_returns_string():
    """_get_lan_ip() (via router import) should return a non-empty IP string."""
    from backend.setup.router import _get_lan_ip
    ip = _get_lan_ip()
    assert isinstance(ip, str)
    assert len(ip) > 0
    parts = ip.split(".")
    assert len(parts) == 4


# ---------------------------------------------------------------------------
# Router tests — require setup mode app
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_client(config_dir, monkeypatch):
    """TestClient with the app running in setup mode, fake services active."""
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.main import create_app_setup
    return TestClient(create_app_setup())


def test_setup_status_returns_expected_fields(setup_client):
    response = setup_client.get("/api/setup/status")
    assert response.status_code == 200
    data = response.json()
    assert "ollama_installed" in data
    assert "models_pulled" in data
    assert "admin_configured" in data
    assert "service_installed" in data


def test_setup_status_service_not_installed_by_default(setup_client):
    response = setup_client.get("/api/setup/status")
    assert response.json()["service_installed"] is False


def test_setup_status_admin_not_configured_by_default(setup_client):
    response = setup_client.get("/api/setup/status")
    assert response.json()["admin_configured"] is False


def test_setup_language_saves_locale(setup_client, config_dir):
    response = setup_client.post("/api/setup/language", json={"locale": "it"})
    assert response.status_code == 200
    from backend.config.service import load_config
    assert load_config().locale == "it"


def test_setup_admin_credentials_saves_to_config(setup_client, config_dir):
    response = setup_client.post(
        "/api/setup/admin-credentials",
        json={"username": "teacher", "password": "blackboard"},
    )
    assert response.status_code == 200
    from backend.config.service import load_config
    config = load_config()
    assert config.admin_username == "teacher"
    assert config.admin_password == "blackboard"


def test_setup_status_admin_configured_after_save(setup_client, config_dir):
    setup_client.post(
        "/api/setup/admin-credentials",
        json={"username": "admin", "password": "pw"},
    )
    response = setup_client.get("/api/setup/status")
    assert response.json()["admin_configured"] is True


def test_setup_install_service_streams_done(setup_client):
    response = setup_client.post("/api/setup/install-service", json={"app_port": 7770})
    assert response.status_code == 200
    assert "[DONE]" in response.text


def test_setup_uninstall_streams_done(setup_client):
    response = setup_client.post("/api/setup/uninstall")
    assert response.status_code == 200
    assert "[DONE]" in response.text


def test_setup_restart_streams_done(setup_client):
    response = setup_client.post("/api/setup/restart-service")
    assert response.status_code == 200
    assert "[DONE]" in response.text


def test_setup_lan_url_returns_url(setup_client):
    response = setup_client.get("/api/setup/lan-url")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert ":" in data["url"]  # contains port
    assert data["port"] == 7770


def test_setup_ollama_version_returns_string(setup_client):
    response = setup_client.get("/api/setup/ollama-version")
    assert response.status_code == 200
    assert "version" in response.json()


def test_setup_logs_returns_lines(setup_client):
    response = setup_client.get("/api/setup/logs")
    assert response.status_code == 200
    data = response.json()
    assert "lines" in data
    assert isinstance(data["lines"], list)


def test_setup_not_available_in_app_mode(config_dir):
    from backend.main import create_app_app
    client = TestClient(create_app_app())
    assert client.get("/api/setup/status").status_code == 404
