"""
FastAPI router for the app domain.

Mounted only in app mode. Provides:
  - GET  /api/app/status         — public health check
  - GET  /api/app/network-url    — LAN URL for sharing with users
  - GET  /api/app/capabilities   — runtime capability flags (e.g. audio support)
  - POST /api/app/admin/login    — exchange HTTP Basic credentials for a cookie
  - GET  /api/app/admin/valid    — check whether the admin cookie is live
  - POST /api/app/admin/logout   — revoke the admin cookie
  - PUT  /api/app/admin/config   — save config (requires admin cookie)
  - POST /api/app/admin/build-model — rebuild trove_model SSE (requires admin cookie)
  - GET  /api/app/admin/logs     — log buffer snapshot (requires admin cookie)

Sub-routers for gems and documents are included at the bottom of this module.
The require_admin* dependencies are defined in backend.app.auth.
"""
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from backend.app.auth import ADMIN_LOGIN_ALLOWED_HOSTS, require_admin, require_admin_cookie
from backend.config.models import TroveConfig, TroveConfigUpdate
from backend.config.service import load_config, save_config
from backend.log_buffer import get_ollama_log_lines
from backend.network import get_lan_ip
from backend.ollama.service import OllamaService, get_ollama_service
from backend.session import admin_store
from backend.tasks.models import audio_supported

# Sub-routers — included at the bottom of this module after `router` is defined.
# They are imported here at the top so the dependency graph is visible at a glance.
# The include_router() calls must come after the APIRouter is instantiated, which
# is why they live at the bottom; the imports themselves have no such constraint.
from backend.tasks.router import router as gems_router          # noqa: E402
from backend.documents.router import router as documents_router  # noqa: E402
from backend.bundle.router import router as bundle_router        # noqa: E402

router = APIRouter(prefix="/api/app", tags=["app"])


@router.get("/status")
def app_status() -> dict:
    """Confirm app mode is active. Used by the frontend as a health check."""
    return {"mode": "app", "status": "ok"}


@router.get("/network-url")
def network_url() -> dict:
    """
    Return the URL other LAN devices can use to reach this Trove instance.

    Detects the machine's outbound LAN IP via a UDP connect trick (see backend.network).
    The port matches the default `trove start` port (7770).
    """
    ip = get_lan_ip()
    if ip:
        return {"url": f"http://{ip}:7770"}
    return {"url": None}

@router.post("/admin/login", dependencies=[Depends(require_admin)])
def admin_login(request: Request, response: Response) -> dict:
    """
    Exchange HTTP Basic credentials for a signed admin session cookie.

    Rejects requests not originating from the local machine (127.0.0.1 / ::1).
    ADMIN_LOGIN_ALLOWED_HOSTS is defined in backend.app.auth and may be extended
    if mDNS or a fixed hostname is added in future.
    """
    if request.client.host not in ADMIN_LOGIN_ALLOWED_HOSTS:
        raise HTTPException(
            status_code=403,
            detail="Admin login is only available from the server machine. "
                   "Open http://localhost:7770 in a browser on this machine.",
        )
    token = admin_store.create()
    response.set_cookie(
        key="admin_auth",
        value=token,
        httponly=True,
        # secure=True would prevent the cookie from being sent over HTTP, which is
        # Trove's current runtime (HTTPS is a future stretch goal). Set to False for now;
        # revisit when HTTPS/mDNS is added.
        secure=False,
        samesite="lax",
    )
    return {"message": "Admin login successful. Cookie set."}


@router.get("/admin/valid")
def check_admin_cookie(admin_auth: str = Cookie(None)) -> dict:
    """
    Return whether the current admin_auth cookie holds a live token.

    Returns {"valid": true} or {"valid": false} — never reflects the token value
    back to the caller so it cannot be exfiltrated via a response body.
    """
    valid = bool(admin_auth and admin_store.validate_and_refresh(admin_auth))
    return {"valid": valid}


@router.post("/admin/logout")
def admin_logout(request: Request, response: Response) -> dict:
    """
    Revoke the admin session cookie.

    Removes the token from the admin store so it cannot be replayed after logout.
    """
    token = request.cookies.get("admin_auth")
    if token:
        admin_store.revoke(token)
    response.delete_cookie(key="admin_auth")
    return {"message": "Admin logout successful. Cookie deleted."}

@router.put("/admin/config", dependencies=[Depends(require_admin_cookie)])
def update_config(update: TroveConfigUpdate) -> TroveConfigUpdate:
    """
    Update non-credential configuration fields and save to disk.

    Accepts only the public config fields (base_model, num_ctx, locale).
    Admin credentials are never in the request or response; use the dedicated
    save_admin_credentials endpoint in the setup router to change those.
    Requires admin cookie.
    """
    config = load_config()
    update_dict = update.model_dump(exclude_unset=True)
    config_dict = config.model_dump()
    config_dict.update(update_dict)
    save_config(TroveConfig(**config_dict))
    return update


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


@router.get("/admin/logs", dependencies=[Depends(require_admin_cookie)])
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


router.include_router(gems_router)
router.include_router(documents_router)
router.include_router(bundle_router)
