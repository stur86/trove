"""Tests for backend.paths — the central runtime path module."""
from pathlib import Path
import pytest
from backend.paths import get_config_dir, get_install_dir, get_ollama_bin_dir, get_ollama_models_dir


def test_get_config_dir_default(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert get_config_dir() == tmp_path / ".config" / "trove"


def test_get_config_dir_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert get_config_dir() == tmp_path / "trove"


def test_get_install_dir_falls_back_to_config_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("TROVE_INSTALL_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert get_install_dir() == get_config_dir()


def test_get_install_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TROVE_INSTALL_DIR", str(tmp_path))
    assert get_install_dir() == tmp_path


def test_get_ollama_bin_dir_under_install_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TROVE_INSTALL_DIR", str(tmp_path))
    assert get_ollama_bin_dir() == tmp_path / "bin"


def test_get_ollama_models_dir_under_install_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TROVE_INSTALL_DIR", str(tmp_path))
    assert get_ollama_models_dir() == tmp_path / "models"
