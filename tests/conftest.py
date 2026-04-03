import pytest
from pathlib import Path


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect XDG config to a temp directory for all config tests."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "trove"
    config_path.mkdir()
    return config_path
