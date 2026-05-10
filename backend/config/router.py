"""FastAPI router for the config domain. Exposes GET /api/config only.

PUT /api/config has moved to /api/app/admin/config (auth-gated, app mode only).
"""
from fastapi import APIRouter

from backend.config.models import TroveConfigUpdate
from backend.config.service import load_config

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config() -> TroveConfigUpdate:
    """Return the current server configuration, excluding admin credentials."""
    return load_config()
