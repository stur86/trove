"""
Ollama management service.

Defines the OllamaService Protocol and two implementations:
- RealOllamaService: uses the actual ollama binary and subprocess
- FakeOllamaService: simulates all operations for dev mode and testing

Which implementation is used is controlled by the TROVE_FAKE_OLLAMA
environment variable (set to 1 to use the fake). Load via python-dotenv.
"""
import os
import shutil
import subprocess
import time
from functools import lru_cache
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar, Protocol, runtime_checkable

from backend.config.models import TroveConfig
from backend.config.service import get_config_dir, load_config
from backend.system.service import is_ollama_service_running


# ---------------------------------------------------------------------------
# Shared utility (used by both implementations)
# ---------------------------------------------------------------------------

def generate_modelfile(config: TroveConfig) -> Path:
    """
    Write the Ollama Modelfile to ~/.config/trove/Modelfile and return its path.

    The Modelfile is minimal — just a FROM directive and num_ctx parameter:
        FROM gemma4:e4b
        PARAMETER num_ctx 8192

    Overwrites any existing Modelfile. Creates the config directory if absent.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "Modelfile"
    path.write_text(f"FROM {config.base_model}\nPARAMETER num_ctx {config.num_ctx}\n")
    return path


# ---------------------------------------------------------------------------
# Protocol (interface)
# ---------------------------------------------------------------------------

@runtime_checkable
class OllamaService(Protocol):
    """
    Interface for Ollama management operations.

    Implementations: RealOllamaService (production), FakeOllamaService (dev/test).
    """

    def get_status(self) -> dict:
        """Return installation status: installed, running, model_built."""
        ...

    def stream_install(self) -> Iterator[str]:
        """Install Ollama and yield SSE-formatted progress lines."""
        ...

    def start_service(self) -> Iterator[str]:
        """Start the Ollama service and yield SSE-formatted progress lines."""
        ...

    def stream_pull(self, model_tag: str) -> Iterator[str]:
        """Pull an Ollama model and yield SSE-formatted progress lines."""
        ...

    def build_trove_model(self) -> Iterator[str]:
        """Generate Modelfile and build trove_model, yielding SSE progress."""
        ...


# ---------------------------------------------------------------------------
# Real implementation
# ---------------------------------------------------------------------------

class RealOllamaService:
    """
    Production Ollama service that shells out to the real ollama binary.

    All subprocess calls use subprocess.Popen for streaming output.

    ``_serve_process`` is a class-level singleton holding the handle for any
    ``ollama serve`` process we spawned ourselves (non-systemd fallback). It
    persists across request instances so we can avoid double-spawning and can
    terminate it cleanly on application shutdown.
    """

    _serve_process: ClassVar[subprocess.Popen | None] = None

    def get_status(self) -> dict:
        """
        Return the current Ollama installation status.

        Keys:
          installed (bool): whether the ollama binary is on the PATH.
          running (bool): whether the ollama systemd service is active.
          model_pulled (bool): whether the configured base model has been pulled.
          model_built (bool): whether trove_model has been created.
        """
        installed = shutil.which("ollama") is not None
        running = is_ollama_service_running() if installed else False
        config = load_config()
        model_pulled = self._is_model_pulled(config.base_model) if installed else False
        model_built = self._is_trove_model_built() if installed else False
        return {
            "installed": installed,
            "running": running,
            "model_pulled": model_pulled,
            "model_built": model_built,
        }

    def _is_model_pulled(self, model_tag: str) -> bool:
        """Return True if model_tag appears in `ollama list` output."""
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        return model_tag in result.stdout

    def _is_trove_model_built(self) -> bool:
        """Return True if trove_model appears in `ollama list` output."""
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        return "trove_model" in result.stdout

    def stream_install(self) -> Iterator[str]:
        """
        Run the official Ollama Linux install script and yield SSE-formatted lines.

        Streams stdout+stderr line by line. Final event is [DONE] or [ERROR].
        """
        yield "data: Starting Ollama installation...\n\n"
        process = subprocess.Popen(
            ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout = process.stdout or []
        for line in stdout:
            yield f"data: {line.rstrip()}\n\n"
        process.wait()
        if process.returncode == 0:
            yield "data: [DONE] Ollama installed successfully.\n\n"
        else:
            yield f"data: [ERROR] Installation failed (exit {process.returncode}).\n\n"

    def start_service(self) -> Iterator[str]:
        """
        Start the Ollama service and yield SSE-formatted progress lines.

        Tries systemctl first (standard after the official install script).
        Falls back to running ``ollama serve`` as a detached background process.
        """
        yield "data: Starting Ollama service...\n\n"
        result = subprocess.run(
            ["systemctl", "start", "ollama"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and is_ollama_service_running():
            yield "data: [DONE] Ollama service started.\n\n"
            return

        # Fallback for non-systemd environments (WSL, containers, etc.)
        # Reuse an existing process if it is still alive.
        proc = RealOllamaService._serve_process
        if proc is not None and proc.poll() is None:
            yield "data: ollama serve already running (pid {proc.pid}).\n\n"
        else:
            yield "data: systemctl unavailable, starting ollama serve...\n\n"
            RealOllamaService._serve_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        # Give the server a moment to bind its port.
        time.sleep(2)
        if is_ollama_service_running():
            yield "data: [DONE] Ollama service started.\n\n"
        else:
            yield "data: [ERROR] Failed to start Ollama service.\n\n"

    def stream_pull(self, model_tag: str) -> Iterator[str]:
        """Pull an Ollama model and yield SSE-formatted progress lines."""
        yield f"data: Pulling {model_tag}...\n\n"
        process = subprocess.Popen(
            ["ollama", "pull", model_tag],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout = process.stdout or []
        for line in stdout:
            yield f"data: {line.rstrip()}\n\n"
        process.wait()
        if process.returncode == 0:
            yield "data: [DONE] Model pulled successfully.\n\n"
        else:
            yield f"data: [ERROR] Pull failed (exit {process.returncode}).\n\n"

    def build_trove_model(self) -> Iterator[str]:
        """
        Generate the Modelfile from current config and build trove_model.

        Reads config, writes ~/.config/trove/Modelfile, then runs ollama create.
        """
        config = load_config()
        modelfile_path = generate_modelfile(config)
        yield f"data: Building trove_model from {config.base_model}...\n\n"
        process = subprocess.Popen(
            ["ollama", "create", "trove_model", "-f", str(modelfile_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout = process.stdout or []
        for line in stdout:
            yield f"data: {line.rstrip()}\n\n"
        process.wait()
        if process.returncode == 0:
            yield "data: [DONE] trove_model built successfully.\n\n"
        else:
            yield f"data: [ERROR] Build failed (exit {process.returncode}).\n\n"


# ---------------------------------------------------------------------------
# Fake implementation (dev mode + testing)
# ---------------------------------------------------------------------------

class FakeOllamaService:
    """
    Simulated Ollama service for development and testing.

    Activated by setting TROVE_FAKE_OLLAMA=1 in the environment (or .env file).
    All operations succeed immediately with realistic-looking fake output.
    No real subprocess calls are made.
    """

    def get_status(self) -> dict:
        """Return a fully-installed status — as if Ollama is set up and running."""
        return {"installed": True, "running": True, "model_pulled": True, "model_built": True}

    def stream_install(self) -> Iterator[str]:
        """Yield fake install output that looks like the real Ollama installer."""
        lines = [
            ">>> Downloading ollama...",
            ">>> Installing ollama to /usr/local/bin",
            ">>> Creating ollama user",
            ">>> Adding ollama user to 'ollama' group",
            ">>> Adding current user to 'ollama' group",
            ">>> Creating ollama systemd service",
            ">>> Enabling and starting ollama service",
        ]
        yield "data: Starting Ollama installation (fake mode)...\n\n"
        for line in lines:
            yield f"data: {line}\n\n"
        yield "data: [DONE] Ollama installed successfully.\n\n"

    def start_service(self) -> Iterator[str]:
        """Yield fake service-start output."""
        yield "data: Starting Ollama service (fake mode)...\n\n"
        yield "data: [DONE] Ollama service started.\n\n"

    def stream_pull(self, model_tag: str) -> Iterator[str]:
        """Yield fake model pull output."""
        lines = [
            f"pulling manifest for {model_tag}",
            "pulling 819c2adf5ce6... 100% ▕████████████████▏ 4.3 GB",
            "pulling 38527fd45e30... 100% ▕████████████████▏  112 B",
            "pulling af0ddbdaaa26... 100% ▕████████████████▏   70 B",
            "pulling 35c9e4b3e265... 100% ▕████████████████▏  561 B",
            "verifying sha256 digest",
            "writing manifest",
        ]
        yield f"data: Pulling {model_tag} (fake mode)...\n\n"
        for line in lines:
            yield f"data: {line}\n\n"
        yield "data: [DONE] Model pulled successfully.\n\n"

    def build_trove_model(self) -> Iterator[str]:
        """Yield fake trove_model build output."""
        config = load_config()
        lines = [
            f"reading model metadata from {get_config_dir() / 'Modelfile'}",
            f"using existing layer sha256:abc123 (FROM {config.base_model})",
            "writing new layer sha256:def456 (PARAMETER num_ctx)",
            "writing manifest",
            "removing any unused layers",
            "success",
        ]
        generate_modelfile(config)  # still write the real Modelfile
        yield f"data: Building trove_model from {config.base_model} (fake mode)...\n\n"
        for line in lines:
            yield f"data: {line}\n\n"
        yield "data: [DONE] trove_model built successfully.\n\n"


# ---------------------------------------------------------------------------
# Service factory (used by FastAPI Depends)
# ---------------------------------------------------------------------------

@lru_cache
def get_ollama_service() -> OllamaService:
    """
    FastAPI dependency that returns the appropriate OllamaService implementation.

    Returns FakeOllamaService if TROVE_FAKE_OLLAMA=1, otherwise RealOllamaService.
    Set TROVE_FAKE_OLLAMA in .env for local dev without a real Ollama installation.
    """
    if os.environ.get("TROVE_FAKE_OLLAMA") == "1":
        return FakeOllamaService()
    return RealOllamaService()
