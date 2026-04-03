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


# Serve the compiled React frontend as static files.
# Only mounted if frontend/dist/ exists (i.e. after `task build`).
# html=True makes FastAPI serve index.html for unknown paths (SPA routing).
# NOTE: This mount must come after all app.include_router() calls. FastAPI
# matches explicit routes first, but only when they were registered before
# the catch-all "/" mount. Moving this block above the routers would shadow
# all /api/* endpoints in production.
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
