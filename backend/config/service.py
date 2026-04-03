import os
from pathlib import Path

from backend.config.models import TroveConfig


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "trove"


def load_config() -> TroveConfig:
    path = get_config_dir() / "config.json"
    if not path.exists():
        return TroveConfig()
    return TroveConfig.model_validate_json(path.read_text())


def save_config(config: TroveConfig) -> None:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(config.model_dump_json(indent=2))
