"""
FastAPI router for the Ollama domain.

All endpoints use dependency injection (Depends) to receive an OllamaService
instance — either RealOllamaService or FakeOllamaService depending on env.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.config.service import load_config
from backend.ollama.service import OllamaService, get_ollama_service

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/status")
def ollama_status(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> dict:
    """Return current Ollama installation status (installed, running, model_built)."""
    return service.get_status()


@router.post("/install")
def install_ollama(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> StreamingResponse:
    """
    Run the Ollama install script and stream progress as SSE.

    The client reads the stream and displays each line in the setup log.
    Final event is [DONE] or [ERROR].
    """
    return StreamingResponse(service.stream_install(), media_type="text/event-stream")


@router.post("/start")
def start_ollama(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> StreamingResponse:
    """
    Start the Ollama service and stream progress as SSE.

    Tries systemctl first, falls back to ollama serve for non-systemd environments.
    """
    return StreamingResponse(service.start_service(), media_type="text/event-stream")


@router.post("/pull")
def pull_model(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> StreamingResponse:
    """
    Pull the configured base model and stream progress as SSE.

    Uses the base_model from current config (~/.config/trove/config.json).
    """
    config = load_config()
    return StreamingResponse(service.stream_pull(config.base_model), media_type="text/event-stream")


@router.post("/build")
def build_model(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> StreamingResponse:
    """
    Generate the Modelfile and build trove_model, streaming progress as SSE.

    Reads config, writes ~/.config/trove/Modelfile, then runs ollama create.
    """
    return StreamingResponse(service.build_trove_model(), media_type="text/event-stream")
