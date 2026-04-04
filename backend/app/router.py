"""
FastAPI router for the app domain.

Mounted only in app mode (TROVE_MODE=app). Provides:
  - GET /api/app/status — public health check
  - PUT /api/app/admin/config — save config (requires admin auth)
  - POST /api/app/admin/build-model — build trove_model SSE (requires admin auth)

The require_admin dependency uses HTTP Basic auth checked against
the admin_username / admin_password stored in TroveConfig. Returns 401
if credentials are wrong or if admin_password is empty (setup not done).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.config.models import TroveConfig
from backend.config.service import load_config, save_config
from backend.ollama.service import OllamaService, get_ollama_service

router = APIRouter(prefix="/api/app", tags=["app"])
_security = HTTPBasic()


def require_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> None:
    """
    Verify admin credentials from HTTP Basic auth.

    Raises HTTP 401 if:
    - admin_password is empty (setup not complete)
    - username or password do not match config
    """
    config = load_config()
    if (
        not config.admin_password  # setup not done
        or credentials.username != config.admin_username
        or credentials.password != config.admin_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials or admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/status")
def app_status() -> dict:
    """Confirm app mode is active. Used by the frontend as a health check."""
    return {"mode": "app", "status": "ok"}


@router.put("/admin/config", dependencies=[Depends(require_admin)])
def update_config(config: TroveConfig) -> TroveConfig:
    """
    Save updated configuration to disk.

    Requires admin credentials via HTTP Basic auth. This is the moved
    version of PUT /api/config, now auth-gated.
    """
    save_config(config)
    return config


@router.post("/admin/build-model", dependencies=[Depends(require_admin)])
def build_model(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> StreamingResponse:
    """
    Generate the Modelfile and build trove_model, streaming SSE progress.

    Requires admin credentials. Moved from the shared ollama router.
    """
    return StreamingResponse(
        service.build_trove_model(),
        media_type="text/event-stream",
    )
