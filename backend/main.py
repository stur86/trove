"""
Trove FastAPI application entry point.

Exports create_app(mode) factory used by both the CLI and tests.
The module-level `app` instance uses TROVE_MODE env var (defaults to "app").

Mode routing:
  setup  — mounts setup_router (/api/setup/*), binds 127.0.0.1
  app    — mounts app_router (/api/app/*), binds 0.0.0.0
Shared routers (config GET, i18n, system, ollama) are always mounted.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # Must run before os.getenv calls below

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router
from backend.ollama.router import router as ollama_router
from backend.ollama.service import RealOllamaService
from backend.system.router import router as system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Terminate any ollama serve process we spawned on shutdown."""
    yield
    proc = RealOllamaService._serve_process
    if proc is not None and proc.poll() is None:
        proc.terminate()


def create_app(mode: str | None = None) -> FastAPI:
    """
    Create and configure the FastAPI application for the given mode.

    Args:
        mode: "setup" or "app". Reads TROVE_MODE env var if None,
              defaults to "app" if env var is also unset.
    """
    if mode is None:
        mode = os.getenv("TROVE_MODE", "app")

    application = FastAPI(title="Trove", version="0.1.0", lifespan=lifespan)

    # Allow the Vite dev server to call the backend during development.
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
        """Return the current operating mode (setup or app)."""
        return {"mode": mode}

    @application.get("/api/health")
    def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok"}

    # Mode-specific routers.
    # NOTE: These imports are deferred so that tests can call create_app(mode)
    # before those modules are fully implemented (they fail gracefully as 404s).
    if mode == "setup":
        try:
            from backend.setup.router import router as setup_router
            application.include_router(setup_router)
        except ImportError:
            pass  # setup domain not yet implemented
    elif mode == "app":
        try:
            from backend.app.router import router as app_router
            application.include_router(app_router)
        except ImportError:
            pass  # app domain not yet implemented

    # Serve the compiled React frontend in production.
    # NOTE: Must come after all include_router() calls — FastAPI matches
    # explicit routes first, but only if registered before the catch-all.
    _frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if _frontend_dist.exists():
        application.mount(
            "/assets",
            StaticFiles(directory=str(_frontend_dist / "assets")),
            name="assets",
        )

        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            """SPA fallback: serve static file if it exists, else index.html."""
            file_path = _frontend_dist / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(_frontend_dist / "index.html")

    return application


# Module-level instance for production (uvicorn backend.main:app).
app = create_app()
