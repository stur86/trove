"""
FastAPI router for Gems (user-defined Tasks).

Provides public endpoints for listing and running Gems, and admin-gated
endpoints for creating, updating, and deleting them. This router has no
prefix of its own — it inherits /api/app from the parent app router.

All execution goes through backend.tasks.runner, keeping this file
as a thin HTTP wrapper.
"""
import base64
import binascii
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.auth import require_admin_cookie
from backend.documents.repository import resolve_documents
from backend.ollama.service import OllamaService, get_ollama_service
from backend.tasks.models import MediaInput, OutputMode, UserTask
from backend.tasks.repository import delete_task, list_tasks, load_task, save_task
from backend.tasks.runner import stream_task

router = APIRouter(tags=["gems"])


class RunRequest(BaseModel):
    """Request body for the run endpoint."""

    values: dict[str, str] = {}
    """Argument values keyed by arg name. Missing keys fall back to arg defaults."""
    image: str | None = None
    """Base64-encoded image bytes. Include image_mime when set."""
    image_mime: str | None = None
    """MIME type of the image (e.g. 'image/jpeg', 'image/png'). Defaults to image/jpeg."""
    audio: str | None = None
    """Base64-encoded audio bytes. Include audio_mime when set."""
    audio_mime: str | None = None
    """MIME type of the audio (e.g. 'audio/webm', 'audio/mp4'). Defaults to audio/webm."""


def _decode_media(req: RunRequest) -> MediaInput | None:
    """Decode base64 media fields from a RunRequest into a MediaInput.

    Returns None when neither image nor audio is present.
    Raises HTTPException 422 when a base64 field is malformed.
    """
    if not req.image and not req.audio:
        return None
    try:
        image_bytes = base64.b64decode(req.image) if req.image else None
        audio_bytes = base64.b64decode(req.audio) if req.audio else None
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid base64 media data: {exc}")
    return MediaInput(
        image=image_bytes,
        image_mime=req.image_mime or "image/jpeg",
        audio=audio_bytes,
        audio_mime=req.audio_mime or "audio/webm",
    )


@router.get("/gems")
def get_gems() -> list[UserTask]:
    """Return all user-defined Gems, ordered by id. No authentication required."""
    return list_tasks()


@router.get("/gems/{gem_id}")
def get_gem(gem_id: str) -> UserTask:
    """
    Return a single Gem by id.

    Raises 404 if no Gem with that id exists.
    """
    try:
        return load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")


@router.post("/admin/gems", dependencies=[Depends(require_admin_cookie)], status_code=201)
def create_gem(gem: UserTask) -> UserTask:
    """
    Create a new Gem. Requires admin credentials.

    If a Gem with the same id already exists it is overwritten.
    """
    save_task(gem)
    return gem


@router.put("/admin/gems/{gem_id}", dependencies=[Depends(require_admin_cookie)])
def update_gem(gem_id: str, gem: UserTask) -> UserTask:
    """
    Update an existing Gem. Requires admin credentials.

    Raises 404 if the Gem does not exist (use POST to create).
    Raises 422 if the body id does not match the URL gem_id.
    """
    try:
        load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")
    if gem.id != gem_id:
        raise HTTPException(
            status_code=422,
            detail=f"Body id '{gem.id}' does not match URL gem_id '{gem_id}'",
        )
    save_task(gem)
    return gem


@router.delete("/admin/gems/{gem_id}", dependencies=[Depends(require_admin_cookie)],
               status_code=204)
def delete_gem(gem_id: str) -> None:
    """
    Delete a Gem. Requires admin credentials.

    Raises 404 if the Gem does not exist.
    """
    try:
        load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")
    delete_task(gem_id)


@router.post("/gems/{gem_id}/run")
async def run_gem(
    gem_id: str,
    req: RunRequest,
    ollama: OllamaService = Depends(get_ollama_service),
) -> StreamingResponse:
    """
    Run a Gem with the provided argument values and optional media.

    For TEXT output mode: streams server-sent events (data: lines).
    Each token is a separate data line; streaming ends with data: [DONE].

    For STRUCTURED output mode: returns HTTP 501 (not yet implemented).

    Media fields (image, audio) must be base64-encoded. Include the
    corresponding MIME type field (image_mime, audio_mime) for correct
    handling by the model.

    Raises 503 if the Ollama model has not been built yet, which can happen
    when a bundle produced on another machine is imported without running setup.
    """
    try:
        gem = load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")

    if not ollama.get_status().get("model_built"):
        raise HTTPException(
            status_code=503,
            detail="The AI model is not ready. Complete setup before running a gem.",
        )

    if gem.output_mode == OutputMode.STRUCTURED:
        raise HTTPException(status_code=501, detail="Structured output not yet implemented")

    media = _decode_media(req)

    # Resolve document access for this gem
    documents = resolve_documents(
        list(gem.doc_folder_ids),
        list(gem.doc_ids),
    ) if (gem.doc_folder_ids or gem.doc_ids) else None

    async def sse_generator() -> AsyncIterator[str]:
        """Wrap stream_task tokens as SSE data lines."""
        try:
            async for chunk in stream_task(gem, req.values, media=media, documents=documents):
                # JSON-encode so newlines inside chunks become \n literals and
                # never break the SSE framing (a bare newline would split the
                # data: line and the continuation would be silently dropped).
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as exc:
            logging.getLogger(__name__).error("Gem run failed", exc_info=True)
            yield f"event: error\ndata: {exc}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
