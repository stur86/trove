"""
Trove FastAPI application entry point.

Mounts all domain routers and serves the frontend as static files in production.
CORS is enabled for the Vite dev server (localhost:5173) during development.

In production (after `task build`), FastAPI serves the compiled React app from
frontend/dist/ so only one process needs to run on one port.
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env file if present; no-op if absent

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router
from backend.ollama.router import router as ollama_router
from backend.system.router import router as system_router

app = FastAPI(title="Trove", version="0.1.0")

# Allow the Vite dev server to call the backend during development.
# In production the frontend is served by FastAPI itself, so CORS is not needed,
# but it doesn't hurt to keep it here for hybrid dev/prod setups.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(i18n_router)
app.include_router(system_router)
app.include_router(ollama_router)


@app.get("/api/health")
def health() -> dict:
    """Health check endpoint. Returns ok if the server is running."""
    return {"status": "ok"}


# Serve the compiled React frontend in production.
# Only activated if frontend/dist/ exists (i.e. after `task build`).
# NOTE: Must come after all app.include_router() calls so /api/* routes
# are matched before the catch-all.
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    # Built JS/CSS bundles live under dist/assets/
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        """
        SPA fallback: serve static files if they exist, otherwise index.html.

        This lets React Router handle client-side routes like /setup and /admin
        while still serving favicon.svg, icons.svg, etc. directly.
        """
        file_path = _FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_FRONTEND_DIST / "index.html")
