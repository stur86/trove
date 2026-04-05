"""
FastAPI router for Gems (user-defined Tasks).

Provides public endpoints for listing and running Gems, and admin-gated
endpoints for creating, updating, and deleting them. This router has no
prefix of its own — it inherits /api/app from the parent app router.

All execution goes through backend.tasks.runner, keeping this file
as a thin HTTP wrapper.
"""
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.auth import require_admin
from backend.tasks.models import OutputMode, UserTask
from backend.tasks.repository import delete_task, list_tasks, load_task, save_task
from backend.tasks.runner import stream_task

router = APIRouter(tags=["gems"])


class RunRequest(BaseModel):
    """Request body for the run endpoint."""

    values: dict[str, str] = {}
    """Argument values keyed by arg name. Missing keys fall back to arg defaults."""


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


@router.post("/admin/gems", dependencies=[Depends(require_admin)], status_code=201)
def create_gem(gem: UserTask) -> UserTask:
    """
    Create a new Gem. Requires admin credentials.

    If a Gem with the same id already exists it is overwritten.
    """
    save_task(gem)
    return gem


@router.put("/admin/gems/{gem_id}", dependencies=[Depends(require_admin)])
def update_gem(gem_id: str, gem: UserTask) -> UserTask:
    """
    Update an existing Gem. Requires admin credentials.

    Raises 404 if the Gem does not exist (use POST to create).
    """
    try:
        load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")
    save_task(gem)
    return gem


@router.delete("/admin/gems/{gem_id}", dependencies=[Depends(require_admin)],
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
async def run_gem(gem_id: str, req: RunRequest) -> StreamingResponse:
    """
    Run a Gem with the provided argument values.

    For TEXT output mode: streams server-sent events (data: lines).
    Each token is a separate data line; streaming ends with data: [DONE].

    For STRUCTURED output mode: returns HTTP 501 (not yet implemented).
    """
    try:
        gem = load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")

    if gem.output_mode == OutputMode.STRUCTURED:
        raise HTTPException(status_code=501, detail="Structured output not yet implemented")

    async def sse_generator() -> AsyncIterator[str]:
        """Wrap stream_task tokens as SSE data lines."""
        async for chunk in stream_task(gem, req.values):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
