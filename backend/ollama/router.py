"""
FastAPI router for the Ollama domain.

Exposes status check and SSE-streaming endpoints for install, pull, and build.
All long-running operations stream progress as Server-Sent Events so the
admin Setup page can display live output.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.config.service import load_config
from backend.ollama.service import (
    build_trove_model,
    get_ollama_status,
    stream_install,
    stream_pull,
)

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/status")
def ollama_status() -> dict:
    """Return current Ollama installation status (installed, running, model_built)."""
    return get_ollama_status()


@router.post("/install")
def install_ollama() -> StreamingResponse:
    """
    Run the Ollama install script and stream progress as SSE.

    The client reads the stream and displays each line in the setup log.
    The final event is either [DONE] or [ERROR].
    """
    return StreamingResponse(stream_install(), media_type="text/event-stream")


@router.post("/pull")
def pull_model() -> StreamingResponse:
    """
    Pull the configured base model and stream progress as SSE.

    Uses the base_model from current config (~/.config/trove/config.json).
    """
    config = load_config()
    return StreamingResponse(stream_pull(config.base_model), media_type="text/event-stream")


@router.post("/build")
def build_model() -> StreamingResponse:
    """
    Generate the Modelfile and build trove_model, streaming progress as SSE.

    Reads config, writes ~/.config/trove/Modelfile, then runs ollama create.
    """
    return StreamingResponse(build_trove_model(), media_type="text/event-stream")
