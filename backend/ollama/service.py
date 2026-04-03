"""
Ollama management service.

Handles Ollama installation detection, model pulling, Modelfile generation,
and building the custom trove_model. Long-running operations yield SSE-formatted
strings for streaming to the frontend.

All subprocess calls go through an injectable `runner` parameter (defaulting to
subprocess.Popen) so tests can inject a FakeProcess without touching the system.
"""
import shutil
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

from backend.config.models import TroveConfig
from backend.config.service import get_config_dir, load_config
from backend.system.service import is_ollama_service_running


def is_ollama_installed() -> bool:
    """Return True if the `ollama` binary is on the PATH."""
    return shutil.which("ollama") is not None


def is_trove_model_built() -> bool:
    """Return True if `trove_model` appears in `ollama list` output."""
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    return "trove_model" in result.stdout


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


def get_ollama_status() -> dict:
    """
    Return the current Ollama installation status.

    Keys:
      installed (bool): whether the ollama binary is on the PATH.
      running (bool): whether the ollama systemd service is active.
      model_built (bool): whether trove_model has been created.

    running and model_built are False when installed is False (no point checking).
    """
    installed = is_ollama_installed()
    running = is_ollama_service_running() if installed else False
    model_built = is_trove_model_built() if installed else False
    return {"installed": installed, "running": running, "model_built": model_built}


def stream_install(runner: Callable = subprocess.Popen) -> Iterator[str]:
    """
    Run the official Ollama Linux install script and yield SSE-formatted lines.

    Streams stdout+stderr line by line. Yields a [DONE] or [ERROR] sentinel
    as the final event so the frontend knows when the operation is complete.

    Args:
        runner: subprocess.Popen-compatible callable. Inject a FakeProcess in tests.
    """
    yield "data: Starting Ollama installation...\n\n"
    process = runner(
        ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in process.stdout:
        yield f"data: {line.rstrip()}\n\n"
    process.wait()
    if process.returncode == 0:
        yield "data: [DONE] Ollama installed successfully.\n\n"
    else:
        yield f"data: [ERROR] Installation failed (exit {process.returncode}).\n\n"


def stream_pull(model_tag: str, runner: Callable = subprocess.Popen) -> Iterator[str]:
    """
    Pull an Ollama model and yield SSE-formatted progress lines.

    Args:
        model_tag: Ollama model tag to pull, e.g. 'gemma4:e4b'.
        runner: subprocess.Popen-compatible callable. Inject a FakeProcess in tests.
    """
    yield f"data: Pulling {model_tag}...\n\n"
    process = runner(
        ["ollama", "pull", model_tag],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in process.stdout:
        yield f"data: {line.rstrip()}\n\n"
    process.wait()
    if process.returncode == 0:
        yield "data: [DONE] Model pulled successfully.\n\n"
    else:
        yield f"data: [ERROR] Pull failed (exit {process.returncode}).\n\n"


def build_trove_model(runner: Callable = subprocess.Popen) -> Iterator[str]:
    """
    Generate the Modelfile from current config and build the trove_model.

    Reads config from disk, writes the Modelfile, then runs
    `ollama create trove_model -f <Modelfile>`, streaming output as SSE.

    Args:
        runner: subprocess.Popen-compatible callable. Inject a FakeProcess in tests.
    """
    config = load_config()
    modelfile_path = generate_modelfile(config)
    yield f"data: Building trove_model from {config.base_model}...\n\n"
    process = runner(
        ["ollama", "create", "trove_model", "-f", str(modelfile_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in process.stdout:
        yield f"data: {line.rstrip()}\n\n"
    process.wait()
    if process.returncode == 0:
        yield "data: [DONE] trove_model built successfully.\n\n"
    else:
        yield f"data: [ERROR] Build failed (exit {process.returncode}).\n\n"
