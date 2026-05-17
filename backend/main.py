"""
Trove FastAPI application entry point.

Exports create_app_setup() and create_app_app() factories for the two modes of operation:
- setup mode: used for initial configuration
- app mode: used for regular operation after setup is complete

Mode routing:
  setup  — mounts setup_router (/api/setup/*), binds 127.0.0.1
  app    — mounts app_router (/api/app/*), binds 0.0.0.0
Shared routers (config GET, i18n, system, ollama) are always mounted.
"""
import logging
import os
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from backend.log_buffer import setup_ollama_log_buffer
from backend.paths import get_config_dir, get_install_dir, get_ollama_bin_dir, get_ollama_models_dir
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse as StarletteJSONResponse

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router
from backend.ollama.router import router as ollama_router
from backend.ollama.service import RealOllamaService
from backend.session import session_store
from backend.system.router import router as system_router
from backend.version import __version__

load_dotenv()  # Must run before os.getenv calls below
setup_ollama_log_buffer()

_log = logging.getLogger(__name__)
_log.info(
    "Trove paths — config: %s | install: %s | ollama bin: %s | models: %s",
    get_config_dir(), get_install_dir(), get_ollama_bin_dir(), get_ollama_models_dir(),
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Terminate any ollama serve process we spawned on shutdown."""
    yield
    proc = RealOllamaService._serve_process
    if proc is not None and proc.is_running:
        proc.proc.terminate()

class AppMode(str, Enum):
    SETUP = "setup"
    APP = "app"

# Paths that do not require a session token.
# /api/session — clients call this to obtain a token, so it cannot require one.
# /api/health  — health checks must always be reachable.
# /api/i18n/   — needed for displaying localised error messages before session is ready.
_SESSION_EXEMPT_PREFIXES: tuple[str, ...] = ("/api/session", "/api/health", "/api/i18n/")


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Enforce X-Trove-Session header on all /api/ requests.

    Clients obtain a token via GET /api/session and include it in every
    subsequent request. Protects against cross-origin and direct API calls
    from clients that never loaded the Trove frontend.
    """

    async def dispatch(self, request: StarletteRequest, call_next):
        """Check for a valid session token; pass through exempt paths unchanged."""
        path = request.url.path
        if path.startswith("/api/") and not any(
            path.startswith(prefix) for prefix in _SESSION_EXEMPT_PREFIXES
        ):
            token = request.headers.get("X-Trove-Session", "")
            if not session_store.validate_and_refresh(token):
                return StarletteJSONResponse(
                    {"detail": "Missing or invalid session token."},
                    status_code=401,
                )
        return await call_next(request)


def _find_frontend_dist() -> Path | None:
    """
    Locate the compiled React frontend.

    Resolution order:
    1. TROVE_FRONTEND_DIST env var (set by CLI --frontend-dist flag)
    2. backend/static/ next to this file (wheel install or local build)
    3. frontend/dist/ relative to repo root (legacy fallback)
    """
    import os
    override = os.environ.get("TROVE_FRONTEND_DIST")
    if override:
        return Path(override)
    static = Path(__file__).parent / "static"
    if static.is_dir():
        return static
    dev = Path(__file__).parent.parent / "frontend" / "dist"
    if dev.is_dir():
        return dev
    return None


def _create_app_with_mode(mode: AppMode) -> FastAPI:
    """
    Create and configure the FastAPI application for the given mode.

    Args:
        mode (AppMode): The operating mode of the application (setup or app).
    """
    # Pin the active Ollama port for this process before any subprocess is spawned.
    # Setup uses 11436 so it does not collide with a running app-mode instance (11435).
    from backend.system.service import (
        _OLLAMA_SETUP_PORT, TROVE_OLLAMA_PORT, set_active_ollama_port,
    )
    set_active_ollama_port(
        _OLLAMA_SETUP_PORT if mode == AppMode.SETUP else TROVE_OLLAMA_PORT
    )

    application = FastAPI(title="Trove", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    application.add_middleware(SessionMiddleware)

    @application.get("/api/session")
    def create_session() -> dict:
        """Issue a new session token for a connecting client. No auth required."""
        return {"token": session_store.create()}

    # Allow the Vite dev server to call the backend during development.
    # Not needed in production: the frontend is served as static files from the
    # same origin, so all requests are same-origin and require no CORS headers.
    if os.getenv("TROVE_DEV"):
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Shared routers — always available in both modes.
    application.include_router(config_router)   # GET /api/config
    application.include_router(i18n_router)     # GET /api/i18n/*
    application.include_router(system_router)   # GET /api/system/check
    application.include_router(ollama_router)   # GET/POST /api/ollama/*

    # Mode endpoint — tells the frontend which surface to render.
    @application.get("/api/mode")
    def get_mode() -> dict:
        """
        Return the current operating mode and whether setup has been completed.

        setup_complete is False when admin_password is empty (no credentials
        configured yet). The frontend uses this to block access to app-mode
        features and to gate setup wizard step advancement.
        """
        from backend.config.service import load_config
        config = load_config()
        return {"mode": mode.value, "setup_complete": bool(config.admin_password)}

    @application.get("/api/health")
    def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok"}

    # Mode-specific routers.
    # Imports are deferred inside try/except blocks intentionally: during early
    # development a domain module may not exist yet, and we'd rather return 404
    # for its routes than crash the whole application at startup. In a complete
    # installation both imports will always succeed; the except branch is never
    # reached in production.
    if mode == AppMode.SETUP:
        try:
            from backend.setup.router import router as setup_router
            application.include_router(setup_router)
        except ImportError:
            pass  # setup domain not yet implemented
    elif mode == AppMode.APP:
        try:
            from backend.app.router import router as app_router
            application.include_router(app_router)
        except ImportError:
            pass  # app domain not yet implemented
    else:
        raise ValueError(f"Invalid mode: {mode}")

    # Serve the compiled React frontend in production.
    # NOTE: Must come after all include_router() calls — FastAPI matches
    # explicit routes first, but only if registered before the catch-all.
    _frontend_dist = _find_frontend_dist()
    if _frontend_dist is not None:
        application.mount(
            "/assets",
            StaticFiles(directory=str(_frontend_dist / "assets")),
            name="assets",
        )

        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            """SPA fallback: serve static file if it exists, else index.html.

            API paths (/api/*) are intentionally excluded — if an API route is
            not registered, FastAPI must return 404, not the SPA shell.
            """
            # Let FastAPI's own 404 handler deal with unknown API paths.
            if full_path.startswith("api/"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            file_path = _frontend_dist / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(_frontend_dist / "index.html")
    else:
        _log.warning(
            "Frontend dist not found. Serving API without frontend assets. "
            "Make sure the frontend is compiled and bundled with the wheel or "
            "set TROVE_FRONTEND_DIST to the compiled frontend directory to fix this."
        )

    return application

# Factories
def create_app_setup() -> FastAPI:
    """Create the FastAPI application in setup mode."""
    return _create_app_with_mode(AppMode.SETUP)

def create_app_app() -> FastAPI:
    """Create the FastAPI application in app mode."""
    return _create_app_with_mode(AppMode.APP)