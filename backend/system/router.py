"""FastAPI router for the system check domain. Exposes GET /api/system/check."""
from fastapi import APIRouter

from backend.system.service import check_system

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/check")
def system_check() -> dict:
    """
    Run system checks and return hardware info.

    Used by the Setup page to display RAM/disk/GPU and determine
    which Gemma 4 model variants are viable for this machine.
    """
    return check_system()
