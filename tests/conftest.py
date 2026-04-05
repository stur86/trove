"""
Shared pytest fixtures for the Trove test suite.

The config_dir fixture redirects XDG_CONFIG_HOME to a temp directory so
tests never read or write to the real ~/.config/trove/.

The data_dir fixture redirects XDG_DATA_HOME to a temp directory so
tests never read or write to the real ~/.local/share/trove/.
"""
import pytest
from backend.ollama.service import get_ollama_service
from backend.system.service import get_system_service

@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect XDG config to a temp directory for all config tests."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "trove"
    config_path.mkdir()
    return config_path

@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect XDG_DATA_HOME to a temp directory for DB tests."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    data_path = tmp_path / "trove"
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