"""FastAPI router for the config domain. Exposes GET and PUT /api/config."""
from fastapi import APIRouter

from backend.config.models import TroveConfig
from backend.config.service import load_config, save_config

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config() -> TroveConfig:
    """Return the current server configuration."""
    return load_config()


@router.put("")
def update_config(config: TroveConfig) -> TroveConfig:
    """Persist updated configuration to disk and return it."""
    save_config(config)
    return config
