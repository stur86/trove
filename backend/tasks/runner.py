"""
Pydantic AI task runner for Trove.

Provides two execution functions:
  stream_task — streams text tokens, filtering <think>…</think> blocks
  run_task    — returns full response string (for structured output + internal use)

Both accept a plain Task (or UserTask subclass), a values dict, and an optional
MediaInput for image/audio data. Neither function is aware of HTTP or SSE;
formatting is the caller's concern.
"""
import re
from collections.abc import AsyncIterator

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from backend.system.service import TROVE_OLLAMA_PORT
from backend.tasks.models import MediaInput, Task
from backend.tasks.render import render_prompt

# Ollama's OpenAI-compatible endpoint on Trove's private port.
# AsyncOpenAI appends /chat/completions to this base URL.
_OLLAMA_BASE_URL = f"http://127.0.0.1:{TROVE_OLLAMA_PORT}/v1"


def _default_agent() -> Agent:
    """Create a Pydantic AI Agent backed by the local trove_model Ollama model."""
    model = OpenAIChatModel(
        "trove_model",
        provider=OllamaProvider(base_url=_OLLAMA_BASE_URL),
    )
    return Agent(model)


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
    _agent: Agent | None = None,
) -> AsyncIterator[str]:
    """
    Stream text tokens for a task, filtering out thinking tokens.

    Args:
        task: The task to run (Task or UserTask).
        values: Argument values keyed by arg name.
        media: Optional image and/or audio bytes to include in the message.
        _agent: Optional Agent override for testing without a real Ollama instance.

    Yields:
        Filtered text chunks suitable for streaming to the client.
    """
    prompt = render_prompt(task, values)
    parts = _build_parts(prompt, media)
    agent = _agent or _default_agent()
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
        _agent: Optional Agent override for testing.

    Returns:
        The complete response with thinking tokens removed and whitespace stripped.
    """
    prompt = render_prompt(task, values)
    parts = _build_parts(prompt, media)
    agent = _agent or _default_agent()
    result = await agent.run(parts)
    text: str = result.output
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
