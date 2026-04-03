"""
Trove FastAPI application entry point.

Mounts all domain routers and serves the frontend in production.
"""
from fastapi import FastAPI

from backend.config.router import router as config_router

app = FastAPI(title="Trove", version="0.1.0")

app.include_router(config_router)


@app.get("/api/health")
def health() -> dict:
    """Health check endpoint. Returns ok if the server is running."""
    return {"status": "ok"}
