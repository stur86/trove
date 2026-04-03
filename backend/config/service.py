"""
Config persistence service.

Reads and writes TroveConfig to ~/.config/trove/config.json,
following the XDG Base Directory Specification.
"""
import os
from pathlib import Path

from backend.config.models import TroveConfig


def get_config_dir() -> Path:
    """
    Return the Trove config directory, respecting the XDG Base Directory spec.

    Uses $XDG_CONFIG_HOME if set, otherwise defaults to ~/.config.
    The returned path is ~/.config/trove (or $XDG_CONFIG_HOME/trove).
    The directory is not guaranteed to exist — callers must create it if needed.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "trove"


def load_config() -> TroveConfig:
    """
    Load config from disk, returning defaults if the file doesn't exist yet.

    Reads from get_config_dir()/config.json. On a fresh install before any
    admin configuration, this returns TroveConfig() with all defaults.
    """
    path = get_config_dir() / "config.json"
    if not path.exists():
        return TroveConfig()
    return TroveConfig.model_validate_json(path.read_text())


def save_config(config: TroveConfig) -> None:
    """
    Persist config to disk, creating the config directory if it doesn't exist.

    Writes to get_config_dir()/config.json as pretty-printed JSON.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(config.model_dump_json(indent=2))
