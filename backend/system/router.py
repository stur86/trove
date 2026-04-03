"""FastAPI router for the system check domain. Exposes GET /api/system/check."""
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.system.service import SystemService, get_system_service

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/check")
def system_check(
    service: Annotated[SystemService, Depends(get_system_service)],
) -> dict:
    """
    Run system checks and return hardware info.

    Used by the Setup page to display RAM/disk/GPU and determine
    which Gemma 4 model variants are viable for this machine.
    """
    return service.check()
