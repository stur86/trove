"""Pydantic request/response models for the Ollama domain."""

from pydantic import BaseModel


class StartServiceResult(BaseModel):
    """
    Response for POST /api/ollama/start.

    Reports whether the Ollama server is now reachable.  When ``success``
    is False, ``reason`` explains why:

    - ``"not_installed"`` — the ``ollama`` binary is not on the PATH.
    - ``"timeout"`` — the process was spawned but did not become ready
      within the allowed window (10 s).
    - ``"not_running"`` — global-Ollama mode is active but the external
      service is not reachable.
    """

    success: bool
    reason: str | None = None
