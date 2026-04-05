"""
Shared pytest fixtures for the Trove test suite.

config_dir: redirects XDG_CONFIG_HOME to tmp_path/config so tests never
            touch the real ~/.config/trove/.
data_dir:   redirects XDG_DATA_HOME  to tmp_path/data  so tests never
            touch the real ~/.local/share/trove/.

Using separate subdirectories means both fixtures can be used together
in the same test without conflicts.
"""
import pytest
from backend.ollama.service import get_ollama_service
from backend.system.service import get_system_service


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect XDG_CONFIG_HOME to a temp subdirectory for config tests."""
    xdg = tmp_path / "config"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    config_path = xdg / "trove"
    config_path.mkdir()
    return config_path


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect XDG_DATA_HOME to a temp subdirectory for DB tests."""
    xdg = tmp_path / "data"
    xdg.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    data_path = xdg / "trove"
    data_path.mkdir()
    return data_path


def _clear_lru_caches():
    """Clear LRU caches for service factories to avoid cross-test interference."""
    get_ollama_service.cache_clear()
    get_system_service.cache_clear()


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear LRU caches before each test to avoid cross-test interference."""
    _clear_lru_caches()
    yield
    _clear_lru_caches()
