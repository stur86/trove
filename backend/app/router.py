"""
FastAPI router for the app domain.

Mounted only in app mode. Provides:
  - GET /api/app/status — public health check
  - PUT /api/app/admin/config — save config (requires admin auth)
  - POST /api/app/admin/build-model — build trove_model SSE (requires admin auth)

The require_admin dependency is defined in backend.app.auth and shared
with other domain routers that need admin-gated endpoints.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.app.auth import require_admin
from backend.config.models import TroveConfig
from backend.config.service import load_config, save_config
from backend.ollama.service import OllamaService, get_ollama_service

router = APIRouter(prefix="/api/app", tags=["app"])


@router.get("/status")
def app_status() -> dict:
    """Confirm app mode is active. Used by the frontend as a health check."""
    return {"mode": "app", "status": "ok"}


@router.put("/admin/config", dependencies=[Depends(require_admin)])
def update_config(config: TroveConfig) -> TroveConfig:
    """
    Save updated configuration to disk.

    Requires admin credentials via HTTP Basic auth.
    """
    save_config(config)
    return config


@router.post("/admin/build-model", dependencies=[Depends(require_admin)])
def build_model(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> StreamingResponse:
    """
    Generate the Modelfile and build trove_model, streaming SSE progress.

    Requires admin credentials.
    """
    return StreamingResponse(
        service.build_trove_model(),
        media_type="text/event-stream",
    )
