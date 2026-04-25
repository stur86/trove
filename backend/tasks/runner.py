"""
Pydantic AI task runner for Trove.

Provides two execution functions:
  stream_task — streams text tokens, filtering <think>…</think> blocks
  run_task    — returns full response string (for structured output + internal use)

Both accept a plain Task (or UserTask subclass), a values dict, and an optional
MediaInput for image/audio data. Neither function is aware of HTTP or SSE;
formatting is the caller's concern.
"""
from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from backend.system.service import TROVE_OLLAMA_PORT
from backend.tasks.models import MediaInput, Task, ToolId
from backend.tasks.render import render_prompt
from backend.tasks.tools import build_tool_functions

if TYPE_CHECKING:
    from backend.documents.models import Document

# Ollama's OpenAI-compatible endpoint on Trove's private port.
# AsyncOpenAI appends /chat/completions to this base URL.
_OLLAMA_BASE_URL = f"http://127.0.0.1:{TROVE_OLLAMA_PORT}/v1"


_DOC_SYSTEM_PROMPT = (
    "You have access to a document library. "
    "Call get_table_of_contents() to see what is available, "
    "then get_document(id) to read a specific document."
)


def _build_document_tools(documents: list[Document]) -> list:
    """Create the two document-access tool functions for a gem run.

    Returns a list of two plain callables:
      [0] get_table_of_contents() → str
      [1] get_document(doc_id: str) → str

    Both close over the permitted document list so they can enforce
    access control and read from the correct filesystem paths.

    Args:
        documents: The full list of documents accessible to this run.
    """
    from backend.db import get_data_dir

    doc_map = {doc.id: doc for doc in documents}
    data_dir = get_data_dir()

    def get_table_of_contents() -> str:
        """Return a list of all accessible documents with their one-line descriptions."""
        lines = [
            f"[{doc.id}] {doc.name} — {doc.description}"
            for doc in documents
        ]
        return "\n".join(lines)

    def get_document(doc_id: str) -> str:
        """Return the full markdown content of a document by its ID."""
        if doc_id not in doc_map:
            return (
                f"Error: document '{doc_id}' is not in the permitted document set. "
                f"Call get_table_of_contents() to see available documents."
            )
        doc = doc_map[doc_id]
        path = data_dir / "documents" / doc.folder_id / f"{doc.id}.md"
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            return f"Error: could not read document '{doc_id}': {exc}"

    return [get_table_of_contents, get_document]


def _make_agent(
    documents: list[Document] | None = None,
    tool_ids: frozenset[ToolId] | None = None,
) -> Agent:
    """Create a Pydantic AI Agent backed by the local trove_model Ollama model.

    When documents are provided, document-access tools and a guiding system
    prompt are added. When tool_ids are provided, utility tool callables are
    added — Pydantic AI derives their descriptions from docstrings and type
    hints automatically.

    Args:
        documents: Documents in scope for this run. None or empty → no document tools.
        tool_ids: Utility tool IDs to inject. None or empty → no utility tools.
    """
    model = OpenAIChatModel(
        "trove_model",
        provider=OllamaProvider(base_url=_OLLAMA_BASE_URL),
    )
    tools: list = []
    system_prompt: str | None = None

    if documents:
        tools.extend(_build_document_tools(documents))
        system_prompt = _DOC_SYSTEM_PROMPT

    if tool_ids:
        tools.extend(build_tool_functions(tool_ids))

    if not tools:
        return Agent(model)

    # Only pass system_prompt to Agent if it's non-None
    if system_prompt:
        return Agent(model, tools=tools, system_prompt=system_prompt)
    return Agent(model, tools=tools)


def _build_parts(prompt: str, media: MediaInput | None) -> str | list:
    """Build the user content for a Pydantic AI agent run.

    Returns the prompt string directly when there is no media, preserving
    the existing text-only behaviour. Returns a list of BinaryContent parts
    followed by the prompt string when media is present.

    Ordering: image first, then audio, then the text prompt. An empty
    MediaInput (no bytes set) is treated the same as None.

    Args:
        prompt: The rendered Jinja2 prompt string.
        media: Optional MediaInput carrying raw image and/or audio bytes.

    Returns:
        str when no media bytes are present, list[BinaryContent | str] otherwise.
    """
    if media is None or (not media.has_image and not media.has_audio):
        return prompt
    parts: list = []
    if media.has_image:
        # image is guaranteed non-None when has_image is True
        parts.append(BinaryContent(data=media.image, media_type=media.image_mime))  # type: ignore[arg-type]
    if media.has_audio:
        parts.append(BinaryContent(data=media.audio, media_type=media.audio_mime))  # type: ignore[arg-type]
    parts.append(prompt)
    return parts


class _ThinkFilter:
    """
    State machine that strips <think>…</think> blocks from streaming output.

    Gemma 4 and similar models can emit reasoning tokens wrapped in <think>
    tags. These should never reach the user. This filter processes chunks
    incrementally, buffering the minimum needed to detect tag boundaries.
    """

    def __init__(self) -> None:
        self._buf = ""
        self._in_think = False

    def feed(self, chunk: str) -> str:
        """
        Absorb a streaming chunk and return the portion safe to yield.

        Keeps up to 6 trailing characters buffered when not in a think block
        (len('<think>') - 1 = 6) to guard against tags split across chunks.
        """
        self._buf += chunk
        out: list[str] = []

        while True:
            if self._in_think:
                idx = self._buf.find("</think>")
                if idx == -1:
                    # End tag not yet seen — discard all but a short tail guard.
                    # Keep 7 chars (len("</think>") - 1) to detect partial end tags.
                    if len(self._buf) > 7:
                        self._buf = self._buf[-7:]
                    return ""
                # End tag found — discard think content, resume normal output
                self._buf = self._buf[idx + 8:]
                self._in_think = False
            else:
                idx = self._buf.find("<think>")
                if idx == -1:
                    # No think tag — yield all but last 6 chars as partial-tag guard.
                    # We need to retain len('<think>') - 1 = 6 chars so a tag split
                    # across a chunk boundary is not prematurely emitted.
                    safe = max(0, len(self._buf) - 6)
                    out.append(self._buf[:safe])
                    self._buf = self._buf[safe:]
                    return "".join(out)
                # Start tag found — yield content before it, enter think mode
                out.append(self._buf[:idx])
                self._buf = self._buf[idx + 7:]
                self._in_think = True

    def flush(self) -> str:
        """
        Return any remaining buffered text after streaming ends.

        Returns empty string if still inside an unclosed think block.
        """
        if self._in_think:
            return ""
        result = self._buf
        self._buf = ""
        return result


async def stream_task(
    task: Task,
    values: dict[str, str],
    *,
    media: MediaInput | None = None,
    documents: list[Document] | None = None,
    _agent: Agent | None = None,
) -> AsyncIterator[str]:
    """
    Stream text tokens for a task, filtering out thinking tokens.

    Args:
        task: The task to run (Task or UserTask).
        values: Argument values keyed by arg name.
        media: Optional image and/or audio bytes to include in the message.
        documents: Documents accessible to this run. When non-empty, two tool
                   functions are injected into the agent.
        _agent: Optional Agent override for testing without a real Ollama instance.

    Yields:
        Filtered text chunks suitable for streaming to the client.
    """
    prompt = render_prompt(task, values)
    parts = _build_parts(prompt, media)
    agent = _agent or _make_agent(documents, task.tools)
    filt = _ThinkFilter()

    async with agent.run_stream(parts) as response:
        async for chunk in response.stream_text(delta=True):
            filtered = filt.feed(chunk)
            if filtered:
                yield filtered

    tail = filt.flush()
    if tail:
        yield tail


async def run_task(
    task: Task,
    values: dict[str, str],
    *,
    media: MediaInput | None = None,
    documents: list[Document] | None = None,
    _agent: Agent | None = None,
) -> str:
    """
    Run a task and return the complete response string.

    Strips thinking tokens from the final response using a regex (safe because
    the full string is available). Used for structured output and internal tasks
    where partial streaming is not appropriate.

    Args:
        task: The task to run (Task or UserTask).
        values: Argument values keyed by arg name.
        media: Optional image and/or audio bytes to include in the message.
        documents: Documents accessible to this run. When non-empty, two tool
                   functions are injected into the agent.
        _agent: Optional Agent override for testing.

    Returns:
        The complete response with thinking tokens removed and whitespace stripped.
    """
    prompt = render_prompt(task, values)
    parts = _build_parts(prompt, media)
    agent = _agent or _make_agent(documents, task.tools)
    result = await agent.run(parts)
    text: str = result.output
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
