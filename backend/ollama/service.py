"""
Ollama management service.

Defines the OllamaService Protocol and two implementations:
- RealOllamaService: uses the actual ollama binary and subprocess
- FakeOllamaService: simulates all operations for dev mode and testing

Which implementation is used is controlled by the TROVE_FAKE_OLLAMA
environment variable (set to 1 to use the fake). Load via python-dotenv.
"""

import logging
import os
import platform
import shutil
import subprocess as sp
import tempfile
import threading
import time
from functools import lru_cache
from collections.abc import Iterator

import httpx
from pathlib import Path
from typing import ClassVar, Protocol, runtime_checkable

from backend.config.models import TroveConfig
from backend.config.service import get_config_dir, get_ollama_bin_dir, get_ollama_models_dir, load_config
from backend.ollama.models import StartServiceResult
from backend.system.service import TROVE_OLLAMA_PORT, is_ollama_service_running
from backend.log_buffer import OLLAMA_LOGGER_NAME

_ollama_logger = logging.getLogger(OLLAMA_LOGGER_NAME)


def _ollama_binary() -> str | None:
    """
    Return the path to the ollama binary, or None if it is not available.

    When TROVE_USE_GLOBAL_OLLAMA=1, delegates to the system PATH.
    Otherwise, resolves to Trove's private installation directory.
    """
    if os.getenv("TROVE_USE_GLOBAL_OLLAMA") == "1":
        return shutil.which("ollama")
    candidate = get_ollama_bin_dir() / "ollama"
    return str(candidate) if candidate.exists() else None


class OllamaProcess:
    """
    Thin wrapper around a running ``ollama`` subprocess.

    Spawns the process with OLLAMA_HOST set to the given port, merges
    stdout and stderr into a single stream, and exposes helpers to pipe
    that output to a logger, check liveness, and wait for completion.
    """

    def __init__(self, command: list[str], port: int = TROVE_OLLAMA_PORT):
        binary = _ollama_binary()
        if binary is None:
            raise FileNotFoundError("Ollama binary not found; run setup first")
        proc_env = os.environ.copy()
        proc_env["OLLAMA_HOST"] = f"localhost:{port}"
        if os.getenv("TROVE_USE_GLOBAL_OLLAMA") != "1":
            proc_env["OLLAMA_MODELS"] = str(get_ollama_models_dir())
        self.proc = sp.Popen(
            [binary] + command,
            stdout=sp.PIPE,
            stderr=sp.STDOUT,
            text=True,
            env=proc_env,
        )

    @classmethod
    def run(cls, command: list[str], port: int = TROVE_OLLAMA_PORT) -> tuple[str, int]:
        """Run an ollama command synchronously, returning (output, returncode)."""
        proc = cls(command, port=port)
        output = proc.proc.stdout.read() if proc.proc.stdout else ""
        return output, proc.wait()

    def pipe_output_to_log(self, logger: logging.Logger) -> None:
        """
        Start a daemon thread that reads proc.stdout line by line and emits each
        line via the provided logger.

        Args:
            logger: The logging.Logger instance to emit lines to.
        """

        def _reader() -> None:
            while self.proc.poll() is None:  # while process is still running
                line = self.proc.stdout.readline()  # type: ignore[union-attr]
                logger.info(line.rstrip())

        threading.Thread(target=_reader, daemon=True).start()

    @property
    def is_running(self) -> bool:
        """Return True if the process is still running."""
        return self.proc.poll() is None

    @property
    def pid(self) -> int:
        """Return the process ID."""
        return self.proc.pid

    def wait(self) -> int:
        """Wait for the process to finish and return the exit code."""
        self.proc.wait()
        return self.proc.returncode


# ---------------------------------------------------------------------------
# Ollama lifecycle helpers
# ---------------------------------------------------------------------------


def ensure_ollama_running() -> None:
    """
    Start Trove's private Ollama instance if it is not already running.

    Spawns ``ollama serve`` as a background subprocess. The process inherits
    the current environment, which must have ``OLLAMA_HOST`` set to the private
    port (done by cli.py before uvicorn starts). The handle is stored on
    RealOllamaService._serve_process so the lifespan hook can terminate it
    on shutdown.

    Silently does nothing if:
    - TROVE_USE_GLOBAL_OLLAMA=1 (defer to the system-wide service)
    - the ollama binary is not installed (setup not yet complete)
    - a live process handle already exists
    - the server responds within 2 s (already running)

    Logs a warning if the process is spawned but doesn't become ready within
    10 seconds (e.g. blocked by a slow disk).
    """
    if os.getenv("TROVE_USE_GLOBAL_OLLAMA") == "1":
        return  # global service mode — never spawn our own process
    if not _ollama_binary():
        return  # not installed yet — setup will handle it
    if is_ollama_service_running():
        return  # already accepting requests on our port
    proc = RealOllamaService._serve_process
    if proc is not None and proc.is_running:
        return  # our process is still alive

    _ollama_logger.info("Starting Ollama on port %d…", TROVE_OLLAMA_PORT)
    RealOllamaService._serve_process = OllamaProcess(["serve"], port=TROVE_OLLAMA_PORT)
    RealOllamaService._serve_process.pipe_output_to_log(_ollama_logger)
    # Wait up to 10 s for the server to become ready
    for _ in range(20):
        time.sleep(0.5)
        if is_ollama_service_running():
            _ollama_logger.info("Ollama ready on port %d.", TROVE_OLLAMA_PORT)
            return
    _ollama_logger.warning(
        "Ollama did not become ready on port %d within 10 s.", TROVE_OLLAMA_PORT
    )


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

    def list_pulled_models(self) -> list[str]:
        """Return the list of Ollama model tags available locally."""
        ...

    def stream_install(self) -> Iterator[str]:
        """Install Ollama and yield SSE-formatted progress lines."""
        ...

    def start_service(self) -> StartServiceResult:
        """
        Start the Ollama service and report whether it is now reachable.

        Returns a ``StartServiceResult`` with ``success=True`` when the
        server is accepting requests, or ``success=False`` with a
        ``reason`` string on failure.
        """
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

    ``_serve_process`` is intentionally a *class-level* attribute, not an
    instance attribute. Because FastAPI creates a new service instance on every
    request (via ``get_ollama_service``), an instance attribute would be lost
    between requests and we would lose the handle to the process we spawned.
    Class-level storage keeps the handle alive for the lifetime of the process,
    regardless of how many service instances are created. The lifespan hook in
    ``backend.main`` reads this attribute to terminate the process on shutdown.
    """

    _serve_process: ClassVar[OllamaProcess | None] = None

    def get_status(self) -> dict:
        """
        Return the current Ollama installation status.

        Runs ``ollama list`` once and checks the output for both the configured
        base model and the derived ``trove_model``, avoiding two subprocess calls.

        Keys:
          installed (bool): whether the ollama binary is available.
          running (bool): whether the Ollama server is accepting requests.
          model_pulled (bool): whether the configured base model has been pulled.
          model_built (bool): whether trove_model has been created.
        """
        installed = _ollama_binary() is not None
        running = is_ollama_service_running() if installed else False
        config = load_config()
        model_pulled = False
        model_built = False
        if installed:
            # A single `ollama list` call is enough to check both models.
            list_output, _ = OllamaProcess.run(["list"])
            model_pulled = config.base_model in list_output
            model_built = "trove_model" in list_output
        return {
            "installed": installed,
            "running": running,
            "model_pulled": model_pulled,
            "model_built": model_built,
        }

    def list_pulled_models(self) -> list[str]:
        """
        Return model tags currently available locally by running ``ollama list``.

        Returns an empty list if the binary is absent or the command fails.
        """
        if _ollama_binary() is None:
            return []
        try:
            list_output, rc = OllamaProcess.run(["list"])
        except FileNotFoundError:
            return []
        if rc != 0:
            return []
        # Output: "NAME\tID\tSIZE\tMODIFIED\n<tag>\t..."
        lines = list_output.strip().splitlines()[1:]  # skip header row
        return [line.split()[0] for line in lines if line.strip()]

    def stream_install(self) -> Iterator[str]:
        """
        Download and extract the Ollama binary into Trove's private bin directory.

        Uses the official Ollama tar.zst package rather than the install script,
        so no sudo, systemd, or system-wide changes are made. The binary and its
        companion libraries land in ~/.config/trove/ (bin/ and lib/).

        Streams stdout+stderr line by line. Final event is [DONE] or [ERROR].
        """
        if os.getenv("TROVE_USE_GLOBAL_OLLAMA") == "1":
            yield "data: [ERROR] TROVE_USE_GLOBAL_OLLAMA is set; Ollama must be managed externally.\n\n"
            return

        machine = platform.machine()
        arch = "arm64" if machine == "aarch64" else "amd64"
        url = f"https://ollama.com/download/ollama-linux-{arch}.tar.zst"
        install_dir = get_config_dir()
        install_dir.mkdir(parents=True, exist_ok=True)

        yield f"data: Downloading Ollama for {arch}...\n\n"

        # Download to a temp file with streaming progress, then extract separately.
        # This gives the user feedback during the large download rather than
        # silently blocking on a piped curl | tar command.
        tmp_fd, tmp_name = tempfile.mkstemp(suffix=".tar.zst", dir=install_dir)
        tmp_path = Path(tmp_name)
        try:
            with httpx.Client(follow_redirects=True, timeout=None) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    last_pct = -1
                    last_mb = -1
                    with os.fdopen(tmp_fd, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                pct = downloaded * 100 // total
                                if pct >= last_pct + 5:
                                    last_pct = pct
                                    yield (
                                        f"data: Downloading... "
                                        f"{downloaded // (1024 * 1024)} MB"
                                        f" / {total // (1024 * 1024)} MB"
                                        f" ({pct}%)\n\n"
                                    )
                            else:
                                mb = downloaded // (1024 * 1024)
                                if mb > last_mb:
                                    last_mb = mb
                                    yield f"data: Downloading... {mb} MB\n\n"

            yield "data: Download complete. Extracting...\n\n"
            result = sp.run(
                [
                    "tar", "x", "--zstd", "--no-same-owner",
                    "-C", str(install_dir),
                    "-f", str(tmp_path),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                yield f"data: [ERROR] Extraction failed: {result.stderr.strip()}\n\n"
                return
        except httpx.HTTPError as exc:
            yield f"data: [ERROR] Download failed: {exc}\n\n"
            return
        finally:
            tmp_path.unlink(missing_ok=True)

        yield "data: [DONE] Ollama installed successfully.\n\n"
        # Immediately start the service so the next setup step (model pull)
        # can proceed without a separate "Start" click.
        yield "data: Starting Ollama service...\n\n"
        ensure_ollama_running()
        if is_ollama_service_running():
            yield f"data: Ollama is running on port {TROVE_OLLAMA_PORT}.\n\n"

    def start_service(self) -> StartServiceResult:
        """
        Start Trove's Ollama instance and return whether it is reachable.

        Returns immediately with ``reason="not_installed"`` when the
        ``ollama`` binary is absent, so callers can offer installation.

        When ``TROVE_USE_GLOBAL_OLLAMA=1``, checks that the external
        service is reachable without spawning a private process.

        Otherwise, spawns ``ollama serve`` as a managed subprocess on
        Trove's private port (11435) and waits up to 10 s for readiness.
        """
        if not _ollama_binary():
            return StartServiceResult(success=False, reason="not_installed")

        if os.getenv("TROVE_USE_GLOBAL_OLLAMA") == "1":
            if is_ollama_service_running():
                return StartServiceResult(success=True)
            return StartServiceResult(success=False, reason="not_running")

        # Already responding on our port — nothing to do.
        if is_ollama_service_running():
            return StartServiceResult(success=True)

        # We already spawned a process that is still alive.
        proc = RealOllamaService._serve_process
        if proc is not None and proc.is_running:
            return StartServiceResult(success=True)

        # Spawn a new ``ollama serve`` process on the private port.
        _ollama_logger.info("Starting Ollama on port %d…", TROVE_OLLAMA_PORT)
        RealOllamaService._serve_process = OllamaProcess(
            ["serve"], port=TROVE_OLLAMA_PORT
        )
        RealOllamaService._serve_process.pipe_output_to_log(_ollama_logger)

        # Wait up to 10 s for the server to become ready.
        for _ in range(20):
            time.sleep(0.5)
            if is_ollama_service_running():
                _ollama_logger.info("Ollama ready on port %d.", TROVE_OLLAMA_PORT)
                return StartServiceResult(success=True)

        _ollama_logger.warning(
            "Ollama did not become ready on port %d within 10 s.",
            TROVE_OLLAMA_PORT,
        )
        return StartServiceResult(success=False, reason="timeout")

    def stream_pull(self, model_tag: str) -> Iterator[str]:
        """Pull an Ollama model and yield SSE-formatted progress lines."""
        yield f"data: Pulling {model_tag}...\n\n"
        pull_proc = OllamaProcess(["pull", model_tag], port=TROVE_OLLAMA_PORT)
        stdout = pull_proc.proc.stdout or []
        for line in stdout:
            yield f"data: {line.rstrip()}\n\n"
        ret = pull_proc.wait()
        if ret == 0:
            yield "data: [DONE] Model pulled successfully.\n\n"
        else:
            yield f"data: [ERROR] Pull failed (exit {ret}).\n\n"

    def build_trove_model(self) -> Iterator[str]:
        """
        Generate the Modelfile from current config and build trove_model.

        Reads config, writes ~/.config/trove/Modelfile, then runs ollama create.
        """
        config = load_config()
        modelfile_path = generate_modelfile(config)
        yield f"data: Building trove_model from {config.base_model}...\n\n"
        create_process = OllamaProcess(
            ["create", "trove_model", "-f", str(modelfile_path)], port=TROVE_OLLAMA_PORT
        )
        stdout = create_process.proc.stdout or []
        for line in stdout:
            yield f"data: {line.rstrip()}\n\n"
        ret = create_process.wait()
        if ret == 0:
            yield "data: [DONE] trove_model built successfully.\n\n"
        else:
            yield f"data: [ERROR] Build failed (exit {ret}).\n\n"


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
        return {
            "installed": True,
            "running": True,
            "model_pulled": True,
            "model_built": True,
        }

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

    def start_service(self) -> StartServiceResult:
        """Return a successful start result (fake mode — always succeeds)."""
        return StartServiceResult(success=True)

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

    def list_pulled_models(self) -> list[str]:
        """Return a fixed list of fake pulled model tags for dev/test mode."""
        return ["gemma4:e4b"]

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
