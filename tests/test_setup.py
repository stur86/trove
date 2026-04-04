"""Tests for the setup domain: ServiceInstaller and helper utilities."""
import os
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


def test_get_lan_ip_returns_string():
    """get_lan_ip() should return a non-empty string (may be 127.0.0.1 in CI)."""
    from backend.setup.service import get_lan_ip
    ip = get_lan_ip()
    assert isinstance(ip, str)
    assert len(ip) > 0
    # Should look like an IP address
    parts = ip.split(".")
    assert len(parts) == 4
