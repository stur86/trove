"""
Shared pytest fixtures for the Trove test suite.

config_dir: redirects XDG_CONFIG_HOME to a temp directory so tests never
            touch the real ~/.config/trove/. All user-facing paths (config,
            db, documents) and, when TROVE_INSTALL_DIR is unset, Ollama
            runtime paths resolve under this directory.
"""
import pytest
from backend.ollama.service import get_ollama_service
from backend.session import admin_store, session_store
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


@pytest.fixture(autouse=True)
def disable_real_systems(monkeypatch):
    """Force tests to use mocks"""
    monkeypatch.setenv("TROVE_USE_GLOBAL_OLLAMA", "0")
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")



@pytest.fixture(autouse=True)
def clear_token_stores():
    """
    Clear session and admin token stores before and after each test.

    Prevents tokens created in one test from leaking into another.
    """
    session_store.clear()
    admin_store.clear()
    yield
    session_store.clear()
    admin_store.clear()


@pytest.fixture
def session_token() -> str:
    """A valid session token for attaching to API test requests."""
    return session_store.create()


@pytest.fixture
def admin_token() -> str:
    """A valid admin cookie token for use in admin-protected API test requests."""
    return admin_store.create()
