"""
Tests for the Ollama domain service layer.

Uses FakeOllamaService for streaming tests and patches RealOllamaService
methods for unit tests. No real Ollama installation is required or touched.
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.config.models import TroveConfig
from backend.ollama.service import (
    FakeOllamaService,
    RealOllamaService,
    generate_modelfile,
    get_ollama_service,
)


# --- generate_modelfile (shared utility) ---

def test_generate_modelfile_contents(config_dir):
    config = TroveConfig(base_model="gemma4:e4b", num_ctx=8192, locale="en")
    path = generate_modelfile(config)
    assert path.read_text() == "FROM gemma4:e4b\nPARAMETER num_ctx 8192\n"


def test_generate_modelfile_path(config_dir):
    config = TroveConfig(base_model="gemma4:e4b", num_ctx=8192, locale="en")
    path = generate_modelfile(config)
    assert path.name == "Modelfile"


# --- RealOllamaService.get_status ---

def test_real_get_status_not_installed():
    svc = RealOllamaService()
    with patch("backend.ollama.service.shutil.which", return_value=None):
        status = svc.get_status()
    assert status["installed"] is False
    assert status["running"] is False
    assert status["model_pulled"] is False
    assert status["model_built"] is False


def test_real_get_status_installed_and_running():
    svc = RealOllamaService()
    # stdout includes both the base model and trove_model; config is patched to
    # avoid reading the real ~/.config/trove/config.json during the test.
    mock_list = MagicMock(returncode=0, stdout="NAME\ngemma4:e4b:latest\ntrove_model:latest\n")
    mock_config = TroveConfig()  # defaults: base_model="gemma4:e4b"
    with patch("backend.ollama.service.shutil.which", return_value="/usr/bin/ollama"):
        with patch("backend.ollama.service.subprocess.run", return_value=mock_list):
            with patch("backend.ollama.service.is_ollama_service_running", return_value=True):
                with patch("backend.ollama.service.load_config", return_value=mock_config):
                    status = svc.get_status()
    assert status["installed"] is True
    assert status["running"] is True
    assert status["model_pulled"] is True
    assert status["model_built"] is True


# --- RealOllamaService streaming ---

def test_real_stream_install_yields_done():
    svc = RealOllamaService()
    mock_proc = MagicMock()
    mock_proc.stdout = iter(["Installing...\n"])
    mock_proc.returncode = 0
    mock_proc.wait = lambda: None
    with patch("backend.ollama.service.subprocess.Popen", return_value=mock_proc):
        events = list(svc.stream_install())
    assert any("[DONE]" in e for e in events)


def test_real_stream_install_yields_error_on_failure():
    svc = RealOllamaService()
    mock_proc = MagicMock()
    mock_proc.stdout = iter([])
    mock_proc.returncode = 1
    mock_proc.wait = lambda: None
    with patch("backend.ollama.service.subprocess.Popen", return_value=mock_proc):
        events = list(svc.stream_install())
    assert any("[ERROR]" in e for e in events)


def test_real_start_service_systemctl_success():
    """start_service yields [DONE] when systemctl succeeds and service is running."""
    svc = RealOllamaService()
    mock_result = MagicMock(returncode=0)
    with patch("backend.ollama.service.subprocess.run", return_value=mock_result):
        with patch("backend.ollama.service.is_ollama_service_running", return_value=True):
            events = list(svc.start_service())
    assert any("[DONE]" in e for e in events)


def test_real_start_service_fallback_stores_process():
    """start_service stores the Popen handle on RealOllamaService when using fallback."""
    RealOllamaService._serve_process = None  # reset class-level state
    svc = RealOllamaService()
    mock_run = MagicMock(returncode=1)
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # process appears alive
    with patch("backend.ollama.service.subprocess.run", return_value=mock_run):
        with patch("backend.ollama.service.subprocess.Popen", return_value=mock_proc):
            with patch("backend.ollama.service.is_ollama_service_running", return_value=True):
                with patch("backend.ollama.service.time.sleep"):
                    events = list(svc.start_service())
    assert any("[DONE]" in e for e in events)
    assert RealOllamaService._serve_process is mock_proc


def test_real_start_service_fallback_failure():
    """start_service yields [ERROR] when both systemctl and ollama serve fail."""
    RealOllamaService._serve_process = None
    svc = RealOllamaService()
    mock_result = MagicMock(returncode=1)
    with patch("backend.ollama.service.subprocess.run", return_value=mock_result):
        with patch("backend.ollama.service.subprocess.Popen"):
            with patch("backend.ollama.service.is_ollama_service_running", return_value=False):
                with patch("backend.ollama.service.time.sleep"):
                    events = list(svc.start_service())
    assert any("[ERROR]" in e for e in events)


def test_real_stream_pull_yields_done():
    svc = RealOllamaService()
    mock_proc = MagicMock()
    mock_proc.stdout = iter(["pulling manifest\n"])
    mock_proc.returncode = 0
    mock_proc.wait = lambda: None
    with patch("backend.ollama.service.subprocess.Popen", return_value=mock_proc):
        events = list(svc.stream_pull("gemma4:e4b"))
    assert any("[DONE]" in e for e in events)


# --- FakeOllamaService ---

def test_fake_get_status_returns_all_true():
    svc = FakeOllamaService()
    status = svc.get_status()
    assert status["installed"] is True
    assert status["running"] is True
    assert status["model_pulled"] is True
    assert status["model_built"] is True


def test_fake_stream_install_yields_done():
    svc = FakeOllamaService()
    events = list(svc.stream_install())
    assert any("[DONE]" in e for e in events)
    assert any("fake mode" in e for e in events)


def test_fake_start_service_yields_done():
    svc = FakeOllamaService()
    events = list(svc.start_service())
    assert any("[DONE]" in e for e in events)


def test_fake_stream_pull_yields_done():
    svc = FakeOllamaService()
    events = list(svc.stream_pull("gemma4:e4b"))
    assert any("[DONE]" in e for e in events)


def test_fake_build_yields_done(config_dir):
    svc = FakeOllamaService()
    events = list(svc.build_trove_model())
    assert any("[DONE]" in e for e in events)


# --- get_ollama_service factory ---

def test_get_ollama_service_returns_real_by_default(monkeypatch):
    monkeypatch.delenv("TROVE_FAKE_OLLAMA", raising=False)
    svc = get_ollama_service()
    assert isinstance(svc, RealOllamaService)


def test_get_ollama_service_returns_fake_when_env_set(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    svc = get_ollama_service()
    assert isinstance(svc, FakeOllamaService)
