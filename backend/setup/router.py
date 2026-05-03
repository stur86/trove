"""
FastAPI router for the setup domain.

Mounted only in setup mode. Provides endpoints for
the setup wizard (language, status, admin credentials, service install)
and the management dashboard (LAN URL, Ollama version, restart, uninstall, logs).
"""
import shutil
import subprocess
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.app.auth import hash_password
from backend.config.service import load_config, save_config
from backend.log_buffer import get_ollama_log_lines
from backend.network import get_lan_ip
from backend.ollama.service import OllamaService, get_ollama_service
from backend.setup.models import (
    AdminCredentialsRequest,
    InstallServiceRequest,
    LanguageRequest,
    LanUrlResponse,
    OllamaVersionResponse,
    SetupStatus,
)
from backend.setup.service import ServiceInstaller, get_service_installer

# Default port the app mode listens on (used in the LAN URL response).
_APP_PORT = 7770

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status")
def get_status(
    installer: Annotated[ServiceInstaller, Depends(get_service_installer)],
    ollama: Annotated[OllamaService, Depends(get_ollama_service)],
) -> SetupStatus:
    """
    Return the completion state of each setup step.

    Used by SetupWizard to decide which steps are already done and
    by ManageDashboard to populate the status cards.
    """
    ollama_status = ollama.get_status()
    models_pulled = ollama.list_pulled_models()
    config = load_config()
    return SetupStatus(
        ollama_installed=ollama_status["installed"],
        models_pulled=models_pulled,
        admin_configured=bool(config.admin_password),
        service_installed=installer.is_installed(),
    )


@router.post("/language")
def set_language(body: LanguageRequest) -> dict:
    """
    Save the chosen locale to the persistent config.

    Called at Step 0 of the setup wizard so that all subsequent
    wizard text renders in the selected language.
    """
    config = load_config()
    config.locale = body.locale
    save_config(config)
    return {"saved": True, "locale": body.locale}


@router.post("/admin-credentials")
def save_admin_credentials(body: AdminCredentialsRequest) -> dict:
    """
    Save admin username and bcrypt-hashed password to config.

    The password is hashed with bcrypt before being written to disk.
    Plain-text passwords are never stored.
    """
    config = load_config()
    config.admin_username = body.username
    config.admin_password = hash_password(body.password)
    save_config(config)
    return {"saved": True}


@router.post("/install-service")
def install_service(
    body: InstallServiceRequest,
    installer: Annotated[ServiceInstaller, Depends(get_service_installer)],
) -> StreamingResponse:
    """Install and start the trove systemd service, streaming SSE progress."""
    return StreamingResponse(
        installer.install(app_port=body.app_port),
        media_type="text/event-stream",
    )


@router.post("/uninstall")
def uninstall(
    installer: Annotated[ServiceInstaller, Depends(get_service_installer)],
) -> StreamingResponse:
    """Stop, disable, and remove the trove systemd service."""
    return StreamingResponse(
        installer.uninstall(),
        media_type="text/event-stream",
    )


@router.post("/restart-service")
def restart_service(
    installer: Annotated[ServiceInstaller, Depends(get_service_installer)],
) -> StreamingResponse:
    """Restart the trove systemd service."""
    return StreamingResponse(
        installer.restart(),
        media_type="text/event-stream",
    )


@router.get("/lan-url")
def get_lan_url() -> LanUrlResponse:
    """
    Return the LAN URL where the app mode can be reached.

    Detects the machine's LAN IP and combines it with the default app port.
    """
    ip = get_lan_ip() or "127.0.0.1"
    return LanUrlResponse(ip=ip, port=_APP_PORT, url=f"http://{ip}:{_APP_PORT}")


@router.get("/ollama-version")
def get_ollama_version() -> OllamaVersionResponse:
    """Return the installed Ollama version string, or 'unknown' if not installed."""
    if not shutil.which("ollama"):
        return OllamaVersionResponse(version="unknown")
    result = subprocess.run(
        ["ollama", "--version"], capture_output=True, text=True
    )
    # Output format: "ollama version 0.6.2"
    version = result.stdout.strip().replace("ollama version ", "") or "unknown"
    return OllamaVersionResponse(version=version)


@router.get("/logs")
def get_logs() -> dict:
    """
    Return the last up to 1000 lines from the in-process log buffer.

    The buffer is populated from the Python root logger, so it captures
    output from FastAPI, uvicorn, and all Trove modules.
    """
    return {"lines": get_ollama_log_lines()}
