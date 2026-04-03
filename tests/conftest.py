"""
Shared pytest fixtures for the Trove test suite.

The config_dir fixture is used by all tests that exercise config
persistence — it redirects XDG_CONFIG_HOME to a temp directory so
tests never read or write to the real ~/.config/trove/.
"""
import pytest


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect XDG config to a temp directory for all config tests."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "trove"
    config_path.mkdir()
    return config_path
