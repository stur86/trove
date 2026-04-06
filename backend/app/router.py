"""
FastAPI router for the app domain.

Mounted only in app mode. Provides:
  - GET /api/app/status — public health check
  - PUT /api/app/admin/config — save config (requires admin auth)
  - POST /api/app/admin/build-model — build trove_model SSE (requires admin auth)

The require_admin dependency is defined in backend.app.auth and shared
with other domain routers that need admin-gated endpoints.
"""
import socket
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.responses import StreamingResponse

from backend.app.auth import require_admin, require_admin_cookie
from backend.config.models import TroveConfig
from backend.config.service import load_config, save_config
from backend.log_buffer import get_ollama_log_lines
from backend.ollama.service import OllamaService, get_ollama_service
from backend.tasks.models import audio_supported

router = APIRouter(prefix="/api/app", tags=["app"])


@router.get("/status")
def app_status() -> dict:
    """Confirm app mode is active. Used by the frontend as a health check."""
    return {"mode": "app", "status": "ok"}


def _lan_ip() -> str | None:
    """Return the machine's outbound LAN IP, or None if detection fails."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connecting to a public address reveals which local interface is used
            # for outbound traffic — no actual packet is sent.
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


@router.get("/network-url")
def network_url() -> dict:
    """
    Return the URL other LAN devices can use to reach this Trove instance.

    Detects the machine's outbound LAN IP via a UDP connect trick.
    The port matches the default `trove start` port (7770).
    """
    ip = _lan_ip()
    if ip:
        return {"url": f"http://{ip}:7770"}
    return {"url": None}

@router.post("/admin/login", dependencies=[Depends(require_admin)])
def admin_login(response: Response):
    response.set_cookie(
        key="admin_auth",
        value="true",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return {"message": "Admin login successful. Cookie set."}

@router.get("/admin/valid")
def check_admin_cookie(admin_auth: str = Cookie(None)):
    return {"admin_auth": admin_auth}

@router.post("/admin/logout")
def admin_logout(response: Response):
    response.delete_cookie(key="admin_auth")
    return {"message": "Admin logout successful. Cookie deleted."}

@router.put("/admin/config", dependencies=[Depends(require_admin_cookie)])
def update_config(config: TroveConfig) -> TroveConfig:
    """
    Save updated configuration to disk.

    Requires admin credentials via HTTP Basic auth.
    """
    save_config(config)
    return config


@router.post("/admin/build-model", dependencies=[Depends(require_admin_cookie)])
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


@router.get("/admin/logs")
def get_logs() -> dict:
    """
    Return the last up to 1000 lines from the in-process log buffer.

    Captures output from FastAPI, uvicorn, and all Trove modules.
    Requires admin cookie.
    """
    return {"lines": get_ollama_log_lines()}


@router.get("/capabilities")
def capabilities() -> dict:
    """
    Return runtime capability flags for the current model configuration.

    Currently exposes:
      audio (bool) — True when the active base model supports audio input.
                     Only gemma4:e2b and gemma4:e4b support audio.
    """
    config = load_config()
    return {"audio": audio_supported(config.base_model)}


from backend.tasks.router import router as gems_router  # noqa: E402
router.include_router(gems_router)
