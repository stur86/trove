"""
Tests for the Ollama domain service layer.

Uses FakeOllamaService for streaming tests and patches RealOllamaService
methods for unit tests. No real Ollama installation is required or touched.
"""
import pytest
import httpx
from unittest.mock import MagicMock, patch

from backend.config.models import TroveConfig
from backend.ollama.service import (
    FakeOllamaService,
    RealOllamaService,
    generate_modelfile,
    get_ollama_service,
    OllamaProcess,
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

def test_real_get_status_not_installed(config_dir, monkeypatch):
    # Ensure we're not in global-ollama mode so _ollama_binary checks the file path.
    monkeypatch.delenv("TROVE_USE_GLOBAL_OLLAMA", raising=False)
    svc = RealOllamaService()
    # config_dir redirects XDG_CONFIG_HOME so no real binary exists at that path.
    with patch("backend.ollama.service._ollama_binary", return_value=None):
        status = svc.get_status()
    assert status["installed"] is False
    assert status["running"] is False
    assert status["model_pulled"] is False
    assert status["model_built"] is False


def test_real_get_status_installed_and_running(monkeypatch):
    monkeypatch.delenv("TROVE_USE_GLOBAL_OLLAMA", raising=False)
    svc = RealOllamaService()
    # `ollama list` output includes both the base model and trove_model.
    fake_list_output = "NAME\ngemma4:e4b:latest\ntrove_model:latest\n"
    mock_config = TroveConfig()  # defaults: base_model="gemma4:e4b"
    with patch("backend.ollama.service._ollama_binary", return_value="/fake/ollama"):
        with patch.object(OllamaProcess, "run", return_value=(fake_list_output, 0)):
            with patch("backend.ollama.service.is_ollama_service_running", return_value=True):
                with patch("backend.ollama.service.load_config", return_value=mock_config):
                    status = svc.get_status()
    assert status["installed"] is True
    assert status["running"] is True
    assert status["model_pulled"] is True
    assert status["model_built"] is True


# --- RealOllamaService streaming ---

def _mock_httpx_client(iter_bytes=None):
    """Return a mock httpx.Client context manager with an empty streaming response."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {"content-length": "0"}
    mock_response.iter_bytes = MagicMock(return_value=iter(iter_bytes or []))
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


def test_real_stream_install_yields_done(config_dir, monkeypatch):
    monkeypatch.delenv("TROVE_USE_GLOBAL_OLLAMA", raising=False)
    svc = RealOllamaService()
    with patch("backend.ollama.service.httpx.Client", return_value=_mock_httpx_client()):
        with patch("backend.ollama.service.sp.run", return_value=MagicMock(returncode=0)):
            with patch("backend.ollama.service.ensure_ollama_running"):
                with patch("backend.ollama.service.is_ollama_service_running", return_value=False):
                    events = list(svc.stream_install())
    assert any("[DONE]" in e for e in events)


def test_real_stream_install_yields_error_on_failure(config_dir, monkeypatch):
    # Successful download but failed tar extraction → [ERROR].
    monkeypatch.delenv("TROVE_USE_GLOBAL_OLLAMA", raising=False)
    svc = RealOllamaService()
    with patch("backend.ollama.service.httpx.Client", return_value=_mock_httpx_client()):
        with patch("backend.ollama.service.sp.run", return_value=MagicMock(returncode=1, stderr="bad archive")):
            events = list(svc.stream_install())
    assert any("[ERROR]" in e for e in events)


def test_real_start_service_not_installed(monkeypatch):
    """start_service returns not_installed when the binary is absent."""
    monkeypatch.delenv("TROVE_USE_GLOBAL_OLLAMA", raising=False)
    svc = RealOllamaService()
    with patch("backend.ollama.service._ollama_binary", return_value=None):
        result = svc.start_service()
    assert result.success is False
    assert result.reason == "not_installed"


def test_real_start_service_already_running(monkeypatch):
    """start_service returns success when Ollama is already up."""
    monkeypatch.delenv("TROVE_USE_GLOBAL_OLLAMA", raising=False)
    svc = RealOllamaService()
    with patch("backend.ollama.service._ollama_binary", return_value="/fake/ollama"):
        with patch("backend.ollama.service.is_ollama_service_running", return_value=True):
            result = svc.start_service()
    assert result.success is True


def test_real_start_service_spawns_and_stores_process():
    """start_service spawns ollama serve and stores the handle when not running."""
    RealOllamaService._serve_process = None
    svc = RealOllamaService()
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    # is_ollama_service_running: False on first call (so we spawn), True after
    side_effects = [False] + [True] * 20
    # Mock OllamaProcess to return a wrapper whose `.proc` is our subprocess mock
    wrapper = MagicMock()
    wrapper.proc = mock_proc
    wrapper.pipe_output_to_log = MagicMock()
    with patch("backend.ollama.service.shutil.which", return_value="/usr/bin/ollama"):
        with patch("backend.ollama.service.OllamaProcess", return_value=wrapper):
            with patch("backend.ollama.service.is_ollama_service_running", side_effect=side_effects):
                with patch("backend.ollama.service.time.sleep"):
                    result = svc.start_service()
    assert result.success is True
    assert RealOllamaService._serve_process.proc is mock_proc


def test_real_start_service_timeout():
    """start_service returns timeout when ollama serve never becomes ready."""
    RealOllamaService._serve_process = None
    svc = RealOllamaService()
    wrapper = MagicMock()
    wrapper.pipe_output_to_log = MagicMock()
    with patch("backend.ollama.service.shutil.which", return_value="/usr/bin/ollama"):
        with patch("backend.ollama.service.OllamaProcess", return_value=wrapper):
            with patch("backend.ollama.service.is_ollama_service_running", return_value=False):
                with patch("backend.ollama.service.time.sleep"):
                    result = svc.start_service()
    assert result.success is False
    assert result.reason == "timeout"


def test_real_stream_pull_yields_done():
    svc = RealOllamaService()
    mock_proc = MagicMock()
    mock_proc.stdout = iter(["pulling manifest\n"])
    mock_proc.returncode = 0
    mock_proc.wait = lambda: None
    # Mock OllamaProcess to return a wrapper whose `.proc` is our subprocess mock
    wrapper = MagicMock()
    wrapper.proc = mock_proc
    wrapper.wait = MagicMock(return_value=0)
    with patch("backend.ollama.service.OllamaProcess", return_value=wrapper):
        events = list(svc.stream_pull("gemma4:e4b"))
    assert any("[DONE]" in e for e in events)


def test_ollamaprocess_uses_sp_popen(monkeypatch):
    # Ensure OllamaProcess delegates to sp.Popen internally
    mock_sub = MagicMock()
    mock_sub.stdout = iter(["line1\n"])
    monkeypatch.setattr("backend.ollama.service.sp.Popen", lambda *args, **kwargs: mock_sub)
    proc = OllamaProcess(["pull", "gemma4:e4b"], port=11435)
    assert proc.proc is mock_sub


# --- RealOllamaService.list_pulled_models ---

def test_real_list_pulled_models_binary_absent():
    """Returns empty list when the Ollama binary is not installed."""
    svc = RealOllamaService()
    with patch("backend.ollama.service._ollama_binary", return_value=None):
        result = svc.list_pulled_models()
    assert result == []


def test_real_list_pulled_models_returns_parsed_tags():
    """Parses first-column tags from `ollama list` output."""
    svc = RealOllamaService()
    fake_output = (
        "NAME\tID\tSIZE\tMODIFIED\n"
        "gemma4:e4b:latest\tabc123\t4 GB\t2 minutes ago\n"
        "trove_model:latest\tdef456\t4 GB\t1 minute ago\n"
    )
    with patch("backend.ollama.service._ollama_binary", return_value="/bin/ollama"):
        with patch.object(OllamaProcess, "run", return_value=(fake_output, 0)):
            result = svc.list_pulled_models()
    assert result == ["gemma4:e4b:latest", "trove_model:latest"]


def test_real_list_pulled_models_command_failure():
    """Returns empty list when `ollama list` exits with a non-zero code."""
    svc = RealOllamaService()
    with patch("backend.ollama.service._ollama_binary", return_value="/bin/ollama"):
        with patch.object(OllamaProcess, "run", return_value=("", 1)):
            result = svc.list_pulled_models()
    assert result == []


# --- FakeOllamaService ---

def test_fake_get_status_returns_all_true():
    svc = FakeOllamaService()
    status = svc.get_status()
    assert status["installed"] is True
    assert status["running"] is True
    assert status["model_pulled"] is True
    assert status["model_built"] is True


def test_fake_list_pulled_models_returns_list():
    """Fake service returns a non-empty list of model tags."""
    svc = FakeOllamaService()
    result = svc.list_pulled_models()
    assert isinstance(result, list)
    assert len(result) > 0


def test_fake_stream_install_yields_done():
    svc = FakeOllamaService()
    events = list(svc.stream_install())
    assert any("[DONE]" in e for e in events)
    assert any("fake mode" in e for e in events)


def test_fake_start_service_returns_success():
    """Fake start_service always reports success."""
    svc = FakeOllamaService()
    result = svc.start_service()
    assert result.success is True


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
