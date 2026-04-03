"""
Tests for the Ollama domain service layer.

Uses mocked subprocess calls throughout — no real Ollama installation
is required or touched by these tests.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from backend.config.models import TroveConfig
from backend.ollama.service import (
    is_ollama_installed,
    is_trove_model_built,
    generate_modelfile,
    get_ollama_status,
    stream_install,
    stream_pull,
    build_trove_model,
)


class FakeProcess:
    """
    Fake subprocess.Popen replacement for testing streaming functions.

    Yields a configurable list of output lines then exits with returncode.
    """
    def __init__(self, lines: list[str], returncode: int = 0):
        self.stdout = iter(lines)
        self.returncode = returncode

    def wait(self):
        pass


# --- Status checks ---

def test_is_ollama_installed_true():
    with patch("backend.ollama.service.shutil.which", return_value="/usr/bin/ollama"):
        assert is_ollama_installed() is True


def test_is_ollama_installed_false():
    with patch("backend.ollama.service.shutil.which", return_value=None):
        assert is_ollama_installed() is False


def test_is_trove_model_built_true():
    mock_result = MagicMock(returncode=0, stdout="NAME\ntrove_model:latest\n")
    with patch("backend.ollama.service.subprocess.run", return_value=mock_result):
        assert is_trove_model_built() is True


def test_is_trove_model_built_false():
    mock_result = MagicMock(returncode=0, stdout="NAME\nother_model:latest\n")
    with patch("backend.ollama.service.subprocess.run", return_value=mock_result):
        assert is_trove_model_built() is False


def test_get_ollama_status_not_installed():
    with patch("backend.ollama.service.shutil.which", return_value=None):
        status = get_ollama_status()
    assert status["installed"] is False
    assert status["running"] is False
    assert status["model_built"] is False


def test_get_ollama_status_installed_and_running():
    mock_list = MagicMock(returncode=0, stdout="NAME\ntrove_model:latest\n")
    with patch("backend.ollama.service.shutil.which", return_value="/usr/bin/ollama"):
        with patch("backend.ollama.service.subprocess.run", return_value=mock_list):
            with patch("backend.ollama.service.is_ollama_service_running", return_value=True):
                status = get_ollama_status()
    assert status["installed"] is True
    assert status["running"] is True
    assert status["model_built"] is True


# --- Modelfile generation ---

def test_generate_modelfile_contents(config_dir):
    config = TroveConfig(base_model="gemma4:e4b", num_ctx=8192, locale="en")
    path = generate_modelfile(config)
    assert path.read_text() == "FROM gemma4:e4b\nPARAMETER num_ctx 8192\n"


def test_generate_modelfile_path(config_dir):
    config = TroveConfig(base_model="gemma4:e4b", num_ctx=8192, locale="en")
    path = generate_modelfile(config)
    assert path.name == "Modelfile"


# --- SSE streaming (via injected FakeProcess) ---

def test_stream_install_yields_lines():
    fake = FakeProcess(["Installing Ollama...", "Done."], returncode=0)
    events = list(stream_install(runner=lambda *a, **kw: fake))
    # First event is the preamble, then lines, then DONE
    assert any("Installing" in e for e in events)
    assert any("[DONE]" in e for e in events)


def test_stream_install_yields_error_on_failure():
    fake = FakeProcess(["Something went wrong"], returncode=1)
    events = list(stream_install(runner=lambda *a, **kw: fake))
    assert any("[ERROR]" in e for e in events)


def test_stream_pull_yields_lines():
    fake = FakeProcess(["pulling manifest", "pulling layer"], returncode=0)
    events = list(stream_pull("gemma4:e4b", runner=lambda *a, **kw: fake))
    assert any("pulling" in e for e in events)
    assert any("[DONE]" in e for e in events)


def test_build_trove_model_yields_lines(config_dir):
    fake = FakeProcess(["creating model layer", "success"], returncode=0)
    events = list(build_trove_model(runner=lambda *a, **kw: fake))
    assert any("trove_model" in e for e in events)
    assert any("[DONE]" in e for e in events)
