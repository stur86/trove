"""
Central source of truth for all Trove runtime paths.

Environment variable overrides exported by the trove wrapper script take
precedence over procedurally-derived defaults, keeping install.sh and the
Python backend in sync without a shared config file. Each override name
mirrors its install.sh counterpart (e.g. INSTALL_DIR → TROVE_INSTALL_DIR).

Two root directories:

  config_dir   (~/.config/trove/)   — user-facing files: settings, database,
                                       uploaded documents. Small; preserved on
                                       uninstall.

  install_dir  (INSTALL_DIR)        — installer-managed runtime: Python venv,
                                       private uv, Ollama binary and libraries,
                                       model weights. Large; deleted on uninstall.
                                       Falls back to config_dir when TROVE_INSTALL_DIR
                                       is not set (development / editable installs).
"""
import os
from pathlib import Path


def get_config_dir() -> Path:
    """
    Return the Trove user directory (~/.config/trove/).

    Holds all user-facing files: config.json, Modelfile, trove.db, and
    uploaded documents. Respects XDG_CONFIG_HOME if set.
    The directory is not guaranteed to exist — callers must create it if needed.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "trove"


def get_install_dir() -> Path:
    """
    Return the Trove installation directory.

    Holds all installer-managed runtime files: Python venv, private uv,
    Ollama binary (bin/), Ollama libraries (lib/), and model weights (models/).

    Reads TROVE_INSTALL_DIR if set — exported by the trove wrapper script,
    pointing at the directory created by install.sh. Falls back to
    get_config_dir() when running without the wrapper (dev, tests, editable
    install).
    """
    override = os.environ.get("TROVE_INSTALL_DIR")
    if override:
        return Path(override)
    return get_config_dir()


def get_ollama_bin_dir() -> Path:
    """
    Return the directory containing Trove's private Ollama binary.

    Resolves to <install_dir>/bin/. Isolated from any system-wide Ollama
    installation. Not guaranteed to exist — stream_install creates it.
    """
    return get_install_dir() / "bin"


def get_ollama_models_dir() -> Path:
    """
    Return the directory for Trove's private Ollama model storage.

    Resolves to <install_dir>/models/. Passed as OLLAMA_MODELS to every
    Ollama subprocess. Not guaranteed to exist — Ollama creates it on first use.
    """
    return get_install_dir() / "models"
