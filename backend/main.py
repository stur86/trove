"""
Trove FastAPI application entry point.

Mounts all domain routers and serves the frontend as static files in production.
CORS is enabled for the Vite dev server (localhost:5173) during development.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router
from backend.ollama.router import router as ollama_router
from backend.system.router import router as system_router

app = FastAPI(title="Trove", version="0.1.0")

# Allow the Vite dev server to call the backend during development.
# In production the frontend is served by FastAPI itself, so CORS is not needed.
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
