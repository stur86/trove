"""Tests for the config domain: XDG path resolution, load/save persistence."""
import json
import pytest
from pathlib import Path
from backend.config.models import TroveConfig
from backend.config.service import get_config_dir, load_config, save_config


def test_get_config_dir_default(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = get_config_dir()
    assert result == tmp_path / ".config" / "trove"


def test_get_config_dir_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    result = get_config_dir()
    assert result == tmp_path / "trove"


def test_load_config_returns_defaults_when_no_file(config_dir):
    config = load_config()
    assert config.base_model == "gemma4:e4b"
    assert config.num_ctx == 8192
    assert config.locale == "en"


def test_load_config_reads_existing_file(config_dir):
    (config_dir / "config.json").write_text(
        '{"base_model": "gemma4:31b", "num_ctx": 32768, "locale": "fr"}'
    )
    config = load_config()
    assert config.base_model == "gemma4:31b"
    assert config.num_ctx == 32768
    assert config.locale == "fr"


def test_save_config_writes_file(config_dir):
    config = TroveConfig(base_model="gemma4:e2b", num_ctx=4096, locale="es")
    save_config(config)
    data = json.loads((config_dir / "config.json").read_text())
    assert data["base_model"] == "gemma4:e2b"
    assert data["num_ctx"] == 4096
    assert data["locale"] == "es"
    assert "admin_username" in data
    assert "admin_password" in data


def test_save_config_creates_dir_if_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # directory does not exist yet — only tmp_path exists, not tmp_path/trove
    config = TroveConfig(base_model="gemma4:e4b", num_ctx=8192, locale="en")
    save_config(config)
    assert (tmp_path / "trove" / "config.json").exists()


def test_config_has_admin_username_default(config_dir):
    config = load_config()
    assert config.admin_username == "admin"


def test_config_has_admin_password_default(config_dir):
    config = load_config()
    assert config.admin_password == ""


def test_save_and_load_admin_credentials(config_dir):
    config = TroveConfig(admin_username="sysadmin", admin_password="secret")
    save_config(config)
    loaded = load_config()
    assert loaded.admin_username == "sysadmin"
    assert loaded.admin_password == "secret"
