# Image & Audio Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make image and audio inputs functional end-to-end — file pick or device capture in the browser, base64 transport, Pydantic AI multimodal messages, Ollama execution.

**Architecture:** `MediaInput` carries optional image/audio bytes through the stack. The run endpoint decodes base64 fields into a `MediaInput` and passes it to `stream_task`, which builds a Pydantic AI multipart message `[BinaryContent(...), prompt]`. A `/capabilities` endpoint exposes audio support based on the active model so the frontend can hide unsupported controls.

**Tech Stack:** Python/FastAPI (backend), pydantic-ai 1.x `BinaryContent`, React/TypeScript/Flowbite (frontend), MediaRecorder API (in-browser audio capture), `FileReader` API (base64 encoding).

---

## File Map

**Create:** none

**Modify:**
- `backend/tasks/models.py` — add `MediaInput`, `AUDIO_CAPABLE_MODELS`, `audio_supported()`
- `backend/tasks/runner.py` — add `_build_parts()`, extend `stream_task`/`run_task` with `media` param
- `backend/tasks/router.py` — extend `RunRequest` with base64 fields, decode to `MediaInput`
- `backend/app/router.py` — add `GET /capabilities` endpoint
- `tests/test_task_models.py` — `MediaInput` and `audio_supported` tests
- `tests/test_task_runner.py` — `_build_parts` unit tests, runner tests with `MediaInput`
- `tests/test_gems_router.py` — base64 decode tests, capabilities endpoint tests
- `frontend/src/api/tasks.ts` — extend `run()` with optional image/audio blobs
- `frontend/src/api/app.ts` — add `capabilities()` method
- `frontend/src/api/mock/tasks.ts` — update mock `run()` signature
- `frontend/src/api/mock/app.ts` — add mock `capabilities()`
- `locales/en.json` — add media UI strings
- `locales/it.json` — add Italian equivalents
- `frontend/src/pages/TaskShell.tsx` — fetch capabilities, filter audio gems
- `frontend/src/pages/GemForm.tsx` — fetch capabilities, disable audio checkbox
- `frontend/src/pages/AdminPanel.tsx` — warn on non-audio model with audio gems
- `frontend/src/pages/GemRunner.tsx` — image modal, audio modal, inline recorder

---

## Task 1: MediaInput model and audio_supported helper

**Files:**
- Modify: `backend/tasks/models.py`
- Test: `tests/test_task_models.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_task_models.py`:

```python
from backend.tasks.models import (
    AUDIO_CAPABLE_MODELS, MediaInput, audio_supported,
)


# --- MediaInput ---

def test_media_input_defaults_to_no_media():
    m = MediaInput()
    assert m.image is None
    assert m.audio is None
    assert m.image_mime == "image/jpeg"
    assert m.audio_mime == "audio/webm"


def test_media_input_has_image_false_when_none():
    assert MediaInput().has_image is False


def test_media_input_has_audio_false_when_none():
    assert MediaInput().has_audio is False


def test_media_input_has_image_true_when_set():
    m = MediaInput(image=b"\xff\xd8\xff", image_mime="image/jpeg")
    assert m.has_image is True


def test_media_input_has_audio_true_when_set():
    m = MediaInput(audio=b"\x1a\x45\xdf\xa3", audio_mime="audio/webm")
    assert m.has_audio is True


def test_media_input_is_frozen():
    m = MediaInput(image=b"\xff")
    with pytest.raises(Exception):
        m.image = b"\xfe"


# --- audio_supported ---

def test_audio_supported_e2b():
    assert audio_supported("gemma4:e2b") is True


def test_audio_supported_e4b():
    assert audio_supported("gemma4:e4b") is True


def test_audio_supported_26b():
    assert audio_supported("gemma4:26b") is False


def test_audio_supported_31b():
    assert audio_supported("gemma4:31b") is False


def test_audio_supported_unknown_model():
    assert audio_supported("llama3:8b") is False
```

Also add `import pytest` if not already present at the top (check the file first — it imports pytest for other tests).

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_task_models.py -v -k "media_input or audio_supported"
```

Expected: `ImportError` or `AttributeError` — `MediaInput`, `AUDIO_CAPABLE_MODELS`, `audio_supported` not yet defined.

- [ ] **Step 3: Implement MediaInput and audio_supported in models.py**

Add the following to `backend/tasks/models.py` — insert after the `TaskArg` union and before `OutputMode`:

```python
AUDIO_CAPABLE_MODELS: frozenset[str] = frozenset({"gemma4:e2b", "gemma4:e4b"})
"""Ollama model tags that support audio input. Only the E2B and E4B Gemma 4 variants."""


def audio_supported(base_model: str) -> bool:
    """Return True if the given Ollama base model tag supports audio input.

    Args:
        base_model: The Ollama tag string (e.g. 'gemma4:e4b').

    Returns:
        True for gemma4:e2b and gemma4:e4b; False for all other tags.
    """
    return base_model in AUDIO_CAPABLE_MODELS
```

Then add the following after the `UserTask` class at the bottom of the file:

```python
class MediaInput(BaseModel, frozen=True):
    """
    Runtime multimodal data attached to a single gem run request.

    Carries optional raw bytes for image and/or audio inputs alongside the
    rendered text prompt. The has_image / has_audio properties let callers
    check presence without inspecting bytes directly.

    image_mime and audio_mime default to the most common browser formats;
    callers should always supply the actual MIME type when the bytes are set.
    """

    image: bytes | None = None
    """Raw image bytes in any browser-supported format (JPEG, PNG, WebP, …)."""
    image_mime: str = "image/jpeg"
    """MIME type of the image bytes (e.g. 'image/jpeg', 'image/png')."""
    audio: bytes | None = None
    """Raw audio bytes — typically audio/webm from the browser MediaRecorder API."""
    audio_mime: str = "audio/webm"
    """MIME type of the audio bytes (e.g. 'audio/webm', 'audio/mp4')."""

    @property
    def has_image(self) -> bool:
        """True when image bytes are present."""
        return self.image is not None

    @property
    def has_audio(self) -> bool:
        """True when audio bytes are present."""
        return self.audio is not None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_task_models.py -v -k "media_input or audio_supported"
```

Expected: all 11 new tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/tasks/models.py tests/test_task_models.py
git commit -m "feat: add MediaInput model and audio_supported helper"
```

---

## Task 2: _build_parts helper and runner multimodal support

**Files:**
- Modify: `backend/tasks/runner.py`
- Test: `tests/test_task_runner.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_task_runner.py`:

```python
from pydantic_ai import BinaryContent
from backend.tasks.models import MediaInput


# --- _build_parts ---

def test_build_parts_text_only_returns_string():
    from backend.tasks.runner import _build_parts
    result = _build_parts("Hello", None)
    assert result == "Hello"


def test_build_parts_with_image_returns_list():
    from backend.tasks.runner import _build_parts
    media = MediaInput(image=b"\xff\xd8\xff", image_mime="image/jpeg")
    result = _build_parts("Describe this", media)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], BinaryContent)
    assert result[0].data == b"\xff\xd8\xff"
    assert result[0].media_type == "image/jpeg"
    assert result[1] == "Describe this"


def test_build_parts_with_audio_returns_list():
    from backend.tasks.runner import _build_parts
    media = MediaInput(audio=b"\x1a\x45\xdf\xa3", audio_mime="audio/webm")
    result = _build_parts("Transcribe", media)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], BinaryContent)
    assert result[0].media_type == "audio/webm"
    assert result[1] == "Transcribe"


def test_build_parts_with_image_and_audio_returns_list_of_three():
    from backend.tasks.runner import _build_parts
    media = MediaInput(
        image=b"\xff\xd8\xff", image_mime="image/jpeg",
        audio=b"\x1a\x45", audio_mime="audio/webm",
    )
    result = _build_parts("Describe", media)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0].media_type == "image/jpeg"
    assert result[1].media_type == "audio/webm"
    assert result[2] == "Describe"


def test_build_parts_empty_media_object_returns_string():
    """MediaInput with no bytes set should still return a plain string."""
    from backend.tasks.runner import _build_parts
    media = MediaInput()  # both image and audio are None
    result = _build_parts("Hello", media)
    assert result == "Hello"


# --- stream_task and run_task with MediaInput ---

@pytest.mark.asyncio
async def test_stream_task_with_image_media_yields_content():
    task = Task(template="Describe this image", has_image=True)
    agent = Agent(TestModel(custom_output_text="A red apple"))
    media = MediaInput(image=b"\xff\xd8\xff", image_mime="image/jpeg")
    chunks = []
    async for chunk in stream_task(task, {}, media=media, _agent=agent):
        chunks.append(chunk)
    assert "A red apple" in "".join(chunks)


@pytest.mark.asyncio
async def test_run_task_with_audio_media_returns_response():
    task = Task(template="Transcribe this audio", has_audio=True)
    agent = Agent(TestModel(custom_output_text="Hello world"))
    media = MediaInput(audio=b"\x1a\x45\xdf\xa3", audio_mime="audio/webm")
    result = await run_task(task, {}, media=media, _agent=agent)
    assert result == "Hello world"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_task_runner.py -v -k "build_parts or with_image_media or with_audio_media"
```

Expected: `ImportError` — `_build_parts` not yet defined; `TypeError` on `stream_task`/`run_task` not accepting `media` kwarg.

- [ ] **Step 3: Implement _build_parts and update runner.py**

Replace the contents of `backend/tasks/runner.py` with:

```python
"""
Pydantic AI task runner for Trove.

Provides two execution functions:
  stream_task — streams text tokens, filtering <think>…</think> blocks
  run_task    — returns full response string (for structured output + internal use)

Both accept a plain Task (or UserTask subclass), a values dict, and an optional
MediaInput for image/audio data. Neither function is aware of HTTP or SSE.
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
        # image is guaranteed non-None here; type: ignore for mypy narrowing
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
                    if len(self._buf) > 7:
                        self._buf = self._buf[-7:]
                    return ""
                self._buf = self._buf[idx + 8:]
                self._in_think = False
            else:
                idx = self._buf.find("<think>")
                if idx == -1:
                    safe = max(0, len(self._buf) - 6)
                    out.append(self._buf[:safe])
                    self._buf = self._buf[safe:]
                    return "".join(out)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_task_runner.py -v
```

Expected: all tests pass (including all pre-existing tests).

- [ ] **Step 5: Run the full suite**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/tasks/runner.py tests/test_task_runner.py
git commit -m "feat: add _build_parts and multimodal support to task runner"
```

---

## Task 3: RunRequest extension and /capabilities endpoint

**Files:**
- Modify: `backend/tasks/router.py`
- Modify: `backend/app/router.py`
- Test: `tests/test_gems_router.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_gems_router.py`:

```python
import base64


# --- /capabilities ---

def test_capabilities_returns_audio_true_for_e4b(client):
    """Default config uses gemma4:e4b which supports audio."""
    res = client.get("/api/app/capabilities")
    assert res.status_code == 200
    assert res.json() == {"audio": True}


def test_capabilities_returns_audio_false_for_26b(client):
    from backend.config.service import load_config, save_config
    cfg = load_config()
    cfg = cfg.model_copy(update={"base_model": "gemma4:26b"})
    save_config(cfg)
    res = client.get("/api/app/capabilities")
    assert res.status_code == 200
    assert res.json() == {"audio": False}


# --- Run with base64 media ---

def test_run_gem_passes_image_media_to_runner(authed_client, sample_gem, monkeypatch):
    """Base64 image in request is decoded and passed as MediaInput to stream_task."""
    from backend.tasks.models import MediaInput
    captured: list[MediaInput | None] = []

    async def fake_stream(task, values, *, media=None, _agent=None):
        captured.append(media)
        yield "ok"

    monkeypatch.setattr("backend.tasks.router.stream_task", fake_stream)

    img_bytes = b"\xff\xd8\xff\xe0"  # minimal JPEG header
    img_b64 = base64.b64encode(img_bytes).decode()

    res = authed_client.post(
        f"/api/app/gems/{sample_gem.id}/run",
        json={"values": {"name": "World"}, "image": img_b64, "image_mime": "image/jpeg"},
    )
    assert res.status_code == 200
    assert len(captured) == 1
    assert captured[0] is not None
    assert captured[0].has_image
    assert captured[0].image == img_bytes
    assert captured[0].image_mime == "image/jpeg"


def test_run_gem_malformed_base64_returns_422(client, sample_gem):
    """Malformed base64 in the image field returns HTTP 422."""
    res = client.post(
        f"/api/app/gems/{sample_gem.id}/run",
        json={"values": {}, "image": "not-valid-base64!!!"},
    )
    assert res.status_code == 422


def test_run_gem_no_media_passes_none_to_runner(authed_client, sample_gem, monkeypatch):
    """When no image or audio field is sent, media=None is passed to stream_task."""
    captured: list = []

    async def fake_stream(task, values, *, media=None, _agent=None):
        captured.append(media)
        yield "ok"

    monkeypatch.setattr("backend.tasks.router.stream_task", fake_stream)

    res = authed_client.post(
        f"/api/app/gems/{sample_gem.id}/run",
        json={"values": {"name": "World"}},
    )
    assert res.status_code == 200
    assert captured[0] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_gems_router.py -v -k "capabilities or base64 or malformed or no_media"
```

Expected: FAIL — `/capabilities` not found (404), `RunRequest` doesn't have `image` field.

- [ ] **Step 3: Update RunRequest and run_gem in router.py**

Replace `backend/tasks/router.py` with:

```python
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
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.auth import require_admin_cookie
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
async def run_gem(gem_id: str, req: RunRequest) -> StreamingResponse:
    """
    Run a Gem with the provided argument values and optional media.

    For TEXT output mode: streams server-sent events (data: lines).
    Each token is a separate data line; streaming ends with data: [DONE].

    For STRUCTURED output mode: returns HTTP 501 (not yet implemented).

    Media fields (image, audio) must be base64-encoded. Include the
    corresponding MIME type field (image_mime, audio_mime) for correct
    handling by the model.
    """
    try:
        gem = load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")

    if gem.output_mode == OutputMode.STRUCTURED:
        raise HTTPException(status_code=501, detail="Structured output not yet implemented")

    media = _decode_media(req)

    async def sse_generator() -> AsyncIterator[str]:
        """Wrap stream_task tokens as SSE data lines."""
        try:
            async for chunk in stream_task(gem, req.values, media=media):
                yield f"data: {chunk}\n\n"
        except ValueError as exc:
            yield f"event: error\ndata: {exc}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 4: Add /capabilities endpoint to app/router.py**

Add these two imports near the top of `backend/app/router.py` (after the existing imports):

```python
from backend.config.service import load_config, save_config
from backend.tasks.models import audio_supported
```

Note: `save_config` is already imported; only add `load_config` if not already present. Check the file — currently only `save_config` is imported from `config.service`. Add `load_config` to that import line.

Then add this endpoint anywhere before the `from backend.tasks.router import router as gems_router` line at the bottom:

```python
@router.get("/capabilities")
def capabilities() -> dict:
    """
    Return runtime capability flags for the current model configuration.

    Currently exposes:
      audio (bool) — True when the active base model supports audio input.
                     Only gemma4:e2b and gemma4:e4b support audio.
    """
    config = load_config()
    return {"audio": audio_supported(config.base_model)}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_gems_router.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Run the full suite**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/tasks/router.py backend/app/router.py tests/test_gems_router.py
git commit -m "feat: extend RunRequest with base64 media and add /capabilities endpoint"
```

---

## Task 4: Frontend API layer and locale strings

**Files:**
- Modify: `frontend/src/api/tasks.ts`
- Modify: `frontend/src/api/app.ts`
- Modify: `frontend/src/api/mock/tasks.ts`
- Modify: `frontend/src/api/mock/app.ts`
- Modify: `locales/en.json`
- Modify: `locales/it.json`

No automated frontend tests — verify manually with `task dev-mock` after each sub-step.

- [ ] **Step 1: Update tasks.ts — extend run() with optional media blobs**

Replace the `_realGemsApi` object's `run` property and add the `blobToBase64` helper in `frontend/src/api/tasks.ts`.

Add the helper function after the `readSSEStream` export at the bottom of the file (or above `_realGemsApi` — your choice, but before it is used):

```typescript
/**
 * Convert a Blob to a base64-encoded string (without the data URL prefix).
 * Uses FileReader so it works in all browsers without Buffer.
 */
async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}
```

Update the `run` property in `_realGemsApi`:

```typescript
  /**
   * Run a gem. Returns a raw Response whose body is an SSE stream.
   * Parse with readSSEStream() below.
   *
   * @param id        Gem slug id.
   * @param values    Argument values keyed by arg name.
   * @param image     Optional image to send. Pass { blob, mime } from a file input or canvas.
   * @param audio     Optional audio to send. Pass { blob, mime } from a file input or MediaRecorder.
   */
  run: async (
    id: string,
    values: Record<string, string>,
    image?: { blob: Blob; mime: string },
    audio?: { blob: Blob; mime: string },
  ): Promise<Response> => {
    const body: Record<string, unknown> = { values }
    if (image) {
      body.image = await blobToBase64(image.blob)
      body.image_mime = image.mime
    }
    if (audio) {
      body.audio = await blobToBase64(audio.blob)
      body.audio_mime = audio.mime
    }
    return post(`/app/gems/${id}/run`, body)
  },
```

- [ ] **Step 2: Update mock/tasks.ts — match new run() signature**

In `frontend/src/api/mock/tasks.ts`, update the `run` property to accept (and ignore) the new optional params:

```typescript
  run: (
    _id: string,
    _values: Record<string, string>,
    _image?: { blob: Blob; mime: string },
    _audio?: { blob: Blob; mime: string },
  ): Promise<Response> => {
    // image and audio are ignored in mock mode — streaming response is always canned
    console.log(`Mock run gem with id ${_id} and values`, _values)
    const words = CANNED_RESPONSE.split(' ')
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        await delay(400)
        for (const word of words) {
          controller.enqueue(encoder.encode(`data: ${word} \n\n`))
          await delay(80)
        }
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      },
    })
    return Promise.resolve(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    )
  },
```

- [ ] **Step 3: Add capabilities() to app.ts**

In `frontend/src/api/app.ts`, add the `capabilities` method to `_realAppApi`:

```typescript
  /**
   * Return runtime capability flags for the current model configuration.
   * Currently: { audio: boolean } — True when the active model supports audio input.
   */
  capabilities: (): Promise<{ audio: boolean }> =>
    get('/app/capabilities'),
```

- [ ] **Step 4: Add capabilities() to mock/app.ts**

In `frontend/src/api/mock/app.ts`, add the `capabilities` method to `appApi`:

```typescript
  capabilities: async (): Promise<{ audio: boolean }> => {
    await new Promise(r => setTimeout(r, 50))
    return { audio: true }  // mock default: gemma4:e4b supports audio
  },
```

- [ ] **Step 5: Add new locale strings to en.json**

In `locales/en.json`, replace the two existing "coming soon" tooltip keys and add the new media UI strings. Remove:

```json
  "gem.upload_image_soon": "Image upload coming soon",
  "gem.upload_audio_soon": "Audio upload coming soon",
```

Add (alongside the existing `gem.upload_image` and `gem.upload_audio` keys):

```json
  "gem.add_image": "Add image",
  "gem.add_audio": "Add audio",
  "gem.image_source.title": "Add an image",
  "gem.image_source.file": "Choose from files",
  "gem.image_source.capture": "Take a photo",
  "gem.audio_source.title": "Add audio",
  "gem.audio_source.file": "Choose from files",
  "gem.audio_source.record": "Record now",
  "gem.stop_recording": "Stop",
  "gem.remove": "Remove",
  "admin.gem.audio_not_supported": "Requires gemma4:e2b or gemma4:e4b — current model does not support audio",
  "admin.settings.audio_warning": "The selected model does not support audio input. Gems that use audio will be hidden from users."
```

- [ ] **Step 6: Add Italian translations to it.json**

Open `locales/it.json`. Remove the same two "coming soon" keys, then add:

```json
  "gem.add_image": "Aggiungi immagine",
  "gem.add_audio": "Aggiungi audio",
  "gem.image_source.title": "Aggiungi un'immagine",
  "gem.image_source.file": "Scegli dai file",
  "gem.image_source.capture": "Scatta una foto",
  "gem.audio_source.title": "Aggiungi audio",
  "gem.audio_source.file": "Scegli dai file",
  "gem.audio_source.record": "Registra ora",
  "gem.stop_recording": "Ferma",
  "gem.remove": "Rimuovi",
  "admin.gem.audio_not_supported": "Richiede gemma4:e2b o gemma4:e4b — il modello attuale non supporta l'audio",
  "admin.settings.audio_warning": "Il modello selezionato non supporta l'input audio. I gem che usano l'audio saranno nascosti agli utenti."
```

- [ ] **Step 7: Verify TypeScript compiles**

```bash
cd frontend && bun run build 2>&1 | tail -20
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/tasks.ts frontend/src/api/app.ts \
        frontend/src/api/mock/tasks.ts frontend/src/api/mock/app.ts \
        locales/en.json locales/it.json
git commit -m "feat: extend frontend API layer with capabilities and media upload support"
```

---

## Task 5: TaskShell — filter audio gems by capability

**Files:**
- Modify: `frontend/src/pages/TaskShell.tsx`

- [ ] **Step 1: Add capabilities state and fetch**

In `TaskShell.tsx`, add `appApi` to the imports if not already present (it is — check the file). Add `capabilities` state after the existing state declarations:

```typescript
const [capabilities, setCapabilities] = useState<{ audio: boolean }>({ audio: false })
```

In the existing `useEffect`, add the capabilities fetch. The useEffect currently calls `configApi.get()`, `gemsApi.list()`, and `appApi.networkUrl()`. Add `appApi.capabilities()`:

```typescript
  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    gemsApi.list()
      .then(list => { setGems(list); setLoading(false) })
      .catch(() => setLoading(false))
    appApi.networkUrl().then(r => setNetworkUrl(r.url))
    appApi.capabilities()
      .then(caps => setCapabilities(caps))
      .catch(() => {})  // default { audio: false } is safe
  }, [])
```

- [ ] **Step 2: Filter gems before rendering**

In the JSX, replace `gems.map(...)` with a filtered version. Find the `gems.map(gem => (` line inside the grid div and change it so the map operates on a filtered list:

```typescript
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {gems
              .filter(gem => !gem.has_audio || capabilities.audio)
              .map(gem => (
                <Card
                  key={gem.id}
                  ...
```

Also update the empty-state check — a gem list that has entries but all are filtered out should still show "no gems":

```typescript
        {loading ? (
          <div className="flex justify-center py-20">
            <Spinner size="lg" />
          </div>
        ) : gems.filter(gem => !gem.has_audio || capabilities.audio).length === 0 ? (
          <p className="text-center text-gray-400 py-20">
            {t('app.tasks.placeholder', 'No gems yet. Ask an admin to create some.')}
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {gems
              .filter(gem => !gem.has_audio || capabilities.audio)
              .map(gem => (
```

To avoid repeating the filter expression, extract it:

```typescript
        const visibleGems = gems.filter(gem => !gem.has_audio || capabilities.audio)
```

Put this just before the `return` statement of `TaskShell`, then use `visibleGems` in both the empty check and the map.

- [ ] **Step 3: Build and visually verify**

```bash
cd frontend && bun run build 2>&1 | tail -5
```

Expected: build succeeds. In mock mode (`task dev-mock`), all gems appear (mock capabilities returns `{ audio: true }`). To verify filtering, temporarily set the mock to `{ audio: false }` — any gems with `has_audio: true` should disappear from the grid.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/TaskShell.tsx
git commit -m "feat: hide audio gems in TaskShell when model does not support audio"
```

---

## Task 6: GemForm — disable audio checkbox when model lacks audio support

**Files:**
- Modify: `frontend/src/pages/GemForm.tsx`

- [ ] **Step 1: Add capabilities state and fetch**

In `GemForm.tsx`, add to the existing state declarations:

```typescript
const [capabilities, setCapabilities] = useState<{ audio: boolean }>({ audio: false })
```

Add a `useEffect` after the existing two `useEffect` calls:

```typescript
  useEffect(() => {
    appApi.capabilities()
      .then(caps => setCapabilities(caps))
      .catch(() => {})  // safe default: treat audio as unsupported if fetch fails
  }, [])
```

Also add `appApi` to the imports at the top:

```typescript
import { appApi } from '../api/app'
```

- [ ] **Step 2: Disable the audio checkbox when not supported**

Find the audio capability checkbox section (currently around line 289). Replace it with:

```tsx
          <div className="flex items-start gap-2">
            <Checkbox
              id="has-audio"
              checked={gem.has_audio}
              disabled={!capabilities.audio}
              onChange={e => setGem(g => ({ ...g, has_audio: e.target.checked }))}
              className={!capabilities.audio ? 'opacity-50' : ''}
            />
            <div>
              <Label
                htmlFor="has-audio"
                className={!capabilities.audio ? 'text-gray-400' : ''}
              >
                Accepts audio input
              </Label>
              {!capabilities.audio && (
                <p className="text-xs text-gray-400 mt-0.5">
                  {t('admin.gem.audio_not_supported')}
                </p>
              )}
            </div>
          </div>
```

- [ ] **Step 3: Build to verify**

```bash
cd frontend && bun run build 2>&1 | tail -5
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/GemForm.tsx
git commit -m "feat: disable audio checkbox in GemForm when model does not support audio"
```

---

## Task 7: AdminPanel — warn when switching to a non-audio model with audio gems

**Files:**
- Modify: `frontend/src/pages/AdminPanel.tsx`

- [ ] **Step 1: Add the derived warning flag**

In `AdminPanel.tsx`, add a derived boolean just before the `return` statement (after the `selectedModel` and `maxCtx` derivations):

```typescript
  // True when the currently selected model lacks audio AND at least one saved gem uses audio.
  // Shown as a warning in the Settings tab so the admin knows those gems will be hidden.
  const audioGemsExist = gems.some(g => g.has_audio)
  const selectedModelSupportsAudio = !config?.base_model || ["gemma4:e2b", "gemma4:e4b"].includes(config.base_model)
  const showAudioWarning = audioGemsExist && !selectedModelSupportsAudio
```

- [ ] **Step 2: Render the warning Alert in the Settings tab**

Inside the Settings `<TabItem>`, add the Alert immediately after the model `<Select>` block (after the closing `</div>` of the `base-model` section, before the `num_ctx` section):

```tsx
                {showAudioWarning && (
                  <Alert color="warning">
                    {t('admin.settings.audio_warning')}
                  </Alert>
                )}
```

- [ ] **Step 3: Build to verify**

```bash
cd frontend && bun run build 2>&1 | tail -5
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AdminPanel.tsx
git commit -m "feat: warn in AdminPanel settings when non-audio model is selected with audio gems"
```

---

## Task 8: GemRunner — image modal and capture flow

**Files:**
- Modify: `frontend/src/pages/GemRunner.tsx`

This task adds image picking. Task 9 will add audio recording on top of this.

- [ ] **Step 1: Add imports and state**

In `GemRunner.tsx`, update the imports block:

```typescript
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Label, Modal, Select, Spinner, TextInput, Tooltip } from 'flowbite-react'
import { gemsApi, readSSEStream, type UserTask } from '../api/tasks'
import { appApi } from '../api/app'
import GemIcon from '../components/GemIcon'
import { useLocale, useTranslation } from '../i18n'
```

(Add `Modal` to the Flowbite imports, add `appApi` import.)

Add the following state and refs inside the component, after the existing state declarations:

```typescript
  // Capabilities
  const [capabilities, setCapabilities] = useState<{ audio: boolean }>({ audio: false })

  // Image state
  const [imageBlob, setImageBlob] = useState<Blob | null>(null)
  const [imageMime, setImageMime] = useState<string>('image/jpeg')
  const [showImageModal, setShowImageModal] = useState(false)
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null)

  // Refs for hidden file inputs
  const imageFileRef = useRef<HTMLInputElement>(null)
  const imageCapRef = useRef<HTMLInputElement>(null)
```

- [ ] **Step 2: Add capabilities fetch and image preview URL effect**

After the existing `useEffect` that loads the gem, add:

```typescript
  // Fetch capabilities (needed to show/hide audio controls)
  useEffect(() => {
    if (!id) return
    appApi.capabilities()
      .then(caps => setCapabilities(caps))
      .catch(() => {})
  }, [id])

  // Manage image preview URL — revoke on change to avoid memory leaks
  useEffect(() => {
    if (!imageBlob) { setImagePreviewUrl(null); return }
    const url = URL.createObjectURL(imageBlob)
    setImagePreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [imageBlob])
```

- [ ] **Step 3: Update handleRun to pass image**

Replace the existing `handleRun` function with:

```typescript
  async function handleRun() {
    if (!gem || !id) return
    setOutput('')
    setPhase('running')
    try {
      const imgArg = imageBlob ? { blob: imageBlob, mime: imageMime } : undefined
      const res = await gemsApi.run(id, values, imgArg)
      let firstToken = true
      for await (const token of readSSEStream(res)) {
        if (firstToken) {
          firstToken = false
          setPhase('done')
        }
        setOutput(prev => prev + token)
      }
      setPhase('done')
    } catch {
      setOutput(t('gem.error.run'))
      setPhase('done')
    }
  }
```

(Audio will be added in Task 9.)

- [ ] **Step 4: Add hidden file inputs for image**

In the JSX, just before the closing `</div>` of the outer `max-w-2xl` container (or anywhere outside the conditional phases), add the hidden inputs:

```tsx
        {/* Hidden file inputs for image picking */}
        {gem.has_image && (
          <>
            <input
              type="file"
              accept="image/*"
              className="hidden"
              ref={imageFileRef}
              onChange={e => {
                const f = e.target.files?.[0]
                if (f) { setImageBlob(f); setImageMime(f.type || 'image/jpeg') }
                setShowImageModal(false)
                // Reset so the same file can be re-selected
                if (imageFileRef.current) imageFileRef.current.value = ''
              }}
            />
            <input
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              ref={imageCapRef}
              onChange={e => {
                const f = e.target.files?.[0]
                if (f) { setImageBlob(f); setImageMime(f.type || 'image/jpeg') }
                setShowImageModal(false)
                if (imageCapRef.current) imageCapRef.current.value = ''
              }}
            />
          </>
        )}
```

- [ ] **Step 5: Replace the disabled image button with functional controls**

In the Phase 1 form section, find the existing disabled image button block:

```tsx
            {gem.has_image && (
              <Tooltip content={t('gem.upload_image_soon')}>
                <Button color="light" disabled>{t('gem.upload_image')}</Button>
              </Tooltip>
            )}
```

Replace it with:

```tsx
            {gem.has_image && (
              <div className="flex flex-col gap-2">
                {imagePreviewUrl ? (
                  <div className="flex items-center gap-3">
                    <img
                      src={imagePreviewUrl}
                      alt="Selected image"
                      className="h-16 w-16 object-cover rounded border border-gray-200"
                    />
                    <Button
                      color="light"
                      size="xs"
                      onClick={() => setImageBlob(null)}
                    >
                      {t('gem.remove')}
                    </Button>
                  </div>
                ) : (
                  <Button color="light" onClick={() => setShowImageModal(true)}>
                    {t('gem.add_image')}
                  </Button>
                )}
              </div>
            )}
```

- [ ] **Step 6: Add the image picker Modal**

Add the Modal JSX after the Phase 1 form closing tag (or anywhere at the same level as the other conditional sections — outside the `phase === 'form'` block so it can render over the page):

```tsx
        {/* Image source picker modal */}
        <Modal show={showImageModal} onClose={() => setShowImageModal(false)} size="sm">
          <Modal.Header>{t('gem.image_source.title')}</Modal.Header>
          <Modal.Body>
            <div className="flex flex-col gap-3">
              <Button
                color="light"
                className="w-full"
                onClick={() => imageFileRef.current?.click()}
              >
                {t('gem.image_source.file')}
              </Button>
              <Button
                color="light"
                className="w-full"
                onClick={() => imageCapRef.current?.click()}
              >
                {t('gem.image_source.capture')}
              </Button>
            </div>
          </Modal.Body>
        </Modal>
```

- [ ] **Step 7: Update the collapsed summary bar to show image attachment**

Replace the `argSummary` derivation:

```typescript
  const argSummary = gem.args
    .filter(a => values[a.name])
    .map(a => `${a.name}: ${values[a.name]}`)
    .join(' · ')
```

With:

```typescript
  const argSummary = [
    ...gem.args.filter(a => values[a.name]).map(a => `${a.name}: ${values[a.name]}`),
    ...(imageBlob ? ['image attached'] : []),
  ].join(' · ')
```

- [ ] **Step 8: Remove the now-unused Tooltip import**

The `Tooltip` import from flowbite-react was only used for the disabled stub buttons. Remove `Tooltip` from the Flowbite import line.

- [ ] **Step 9: Build to verify**

```bash
cd frontend && bun run build 2>&1 | tail -10
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages/GemRunner.tsx
git commit -m "feat: add image picker modal and capture support to GemRunner"
```

---

## Task 9: GemRunner — audio modal and inline recording

**Files:**
- Modify: `frontend/src/pages/GemRunner.tsx` (building on Task 8)

- [ ] **Step 1: Add audio state and refs**

Inside the component, after the image state declarations from Task 8, add:

```typescript
  // Audio state
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioMime, setAudioMime] = useState<string>('audio/webm')
  const [showAudioModal, setShowAudioModal] = useState(false)
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null)
  const [recording, setRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)

  // Refs for audio recording
  const audioFileRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
```

- [ ] **Step 2: Add audio preview URL effect and recorder cleanup**

After the image preview URL effect, add:

```typescript
  // Manage audio preview URL
  useEffect(() => {
    if (!audioBlob) { setAudioPreviewUrl(null); return }
    const url = URL.createObjectURL(audioBlob)
    setAudioPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [audioBlob])

  // Stop recording and clear timer on unmount (e.g. user navigates away mid-recording)
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
    }
  }, [])
```

- [ ] **Step 3: Add startRecording and stopRecording functions**

Add these functions inside the component, after `handleRun`:

```typescript
  /**
   * Start recording audio from the default microphone.
   * Closes the audio modal, starts MediaRecorder, and begins counting elapsed seconds.
   * On stop, stores the resulting Blob as audioBlob.
   */
  async function startRecording() {
    setShowAudioModal(false)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const mime = recorder.mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type: mime })
        setAudioBlob(blob)
        setAudioMime(mime)
        // Release microphone
        stream.getTracks().forEach(t => t.stop())
        if (timerRef.current) {
          clearInterval(timerRef.current)
          timerRef.current = null
        }
      }
      recorder.start()
      mediaRecorderRef.current = recorder
      setRecordingSeconds(0)
      setRecording(true)
      timerRef.current = setInterval(
        () => setRecordingSeconds(s => s + 1),
        1000,
      )
    } catch {
      // Microphone permission denied or unavailable — fail silently.
      // The audio button remains visible; user can try again or choose a file.
    }
  }

  /** Stop an in-progress recording. The onstop handler stores the resulting Blob. */
  function stopRecording() {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }
```

- [ ] **Step 4: Update handleRun to pass both image and audio**

Replace the `handleRun` function written in Task 8 with the final version that includes audio:

```typescript
  async function handleRun() {
    if (!gem || !id) return
    setOutput('')
    setPhase('running')
    try {
      const imgArg = imageBlob ? { blob: imageBlob, mime: imageMime } : undefined
      const audArg = audioBlob ? { blob: audioBlob, mime: audioMime } : undefined
      const res = await gemsApi.run(id, values, imgArg, audArg)
      let firstToken = true
      for await (const token of readSSEStream(res)) {
        if (firstToken) {
          firstToken = false
          setPhase('done')
        }
        setOutput(prev => prev + token)
      }
      setPhase('done')
    } catch {
      setOutput(t('gem.error.run'))
      setPhase('done')
    }
  }
```

- [ ] **Step 5: Add hidden audio file input**

In the hidden-inputs section (alongside the image inputs from Task 8), add:

```tsx
        {/* Hidden file input for audio picking */}
        {gem.has_audio && capabilities.audio && (
          <input
            type="file"
            accept="audio/*"
            className="hidden"
            ref={audioFileRef}
            onChange={e => {
              const f = e.target.files?.[0]
              if (f) { setAudioBlob(f); setAudioMime(f.type || 'audio/webm') }
              setShowAudioModal(false)
              if (audioFileRef.current) audioFileRef.current.value = ''
            }}
          />
        )}
```

- [ ] **Step 6: Replace the disabled audio button with functional controls**

Find the existing disabled audio button block:

```tsx
            {gem.has_audio && (
              <Tooltip content={t('gem.upload_audio_soon')}>
                <Button color="light" disabled>{t('gem.upload_audio')}</Button>
              </Tooltip>
            )}
```

Replace it with:

```tsx
            {gem.has_audio && capabilities.audio && (
              <div className="flex flex-col gap-2">
                {recording ? (
                  // Inline recorder — shown while MediaRecorder is active
                  <div className="flex items-center gap-3 py-1">
                    <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shrink-0" />
                    <span className="text-sm text-gray-600 tabular-nums">
                      {recordingSeconds}s
                    </span>
                    <Button color="failure" size="sm" onClick={stopRecording}>
                      {t('gem.stop_recording')}
                    </Button>
                  </div>
                ) : audioPreviewUrl ? (
                  // Preview + remove — shown after recording or file pick
                  <div className="flex items-center gap-3">
                    <audio controls src={audioPreviewUrl} className="h-9 flex-1 min-w-0" />
                    <Button
                      color="light"
                      size="xs"
                      className="shrink-0"
                      onClick={() => setAudioBlob(null)}
                    >
                      {t('gem.remove')}
                    </Button>
                  </div>
                ) : (
                  <Button color="light" onClick={() => setShowAudioModal(true)}>
                    {t('gem.add_audio')}
                  </Button>
                )}
              </div>
            )}
```

- [ ] **Step 7: Add the audio source picker Modal**

After the image Modal from Task 8, add:

```tsx
        {/* Audio source picker modal */}
        <Modal show={showAudioModal} onClose={() => setShowAudioModal(false)} size="sm">
          <Modal.Header>{t('gem.audio_source.title')}</Modal.Header>
          <Modal.Body>
            <div className="flex flex-col gap-3">
              <Button
                color="light"
                className="w-full"
                onClick={() => audioFileRef.current?.click()}
              >
                {t('gem.audio_source.file')}
              </Button>
              <Button
                color="light"
                className="w-full"
                onClick={startRecording}
              >
                {t('gem.audio_source.record')}
              </Button>
            </div>
          </Modal.Body>
        </Modal>
```

- [ ] **Step 8: Update the collapsed summary bar to include audio attachment**

Replace the `argSummary` derivation from Task 8:

```typescript
  const argSummary = [
    ...gem.args.filter(a => values[a.name]).map(a => `${a.name}: ${values[a.name]}`),
    ...(imageBlob ? ['image attached'] : []),
    ...(audioBlob ? ['audio attached'] : []),
  ].join(' · ')
```

- [ ] **Step 9: Build to verify**

```bash
cd frontend && bun run build 2>&1 | tail -10
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 10: Run the full test suite one final time**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/pages/GemRunner.tsx
git commit -m "feat: add audio modal and inline MediaRecorder to GemRunner"
```

---

## Self-Review Checklist

- **Spec coverage:**
  - ✅ MediaInput with has_image/has_audio properties — Task 1
  - ✅ Base64 transport via extended RunRequest — Task 3
  - ✅ _build_parts for Pydantic AI multimodal messages — Task 2
  - ✅ /capabilities endpoint — Task 3
  - ✅ Frontend API layer (run with blobs, capabilities) — Task 4
  - ✅ TaskShell hides audio gems when unsupported — Task 5
  - ✅ GemForm audio checkbox disabled with explanation — Task 6
  - ✅ AdminPanel warning on non-audio model with audio gems — Task 7
  - ✅ Image modal with file picker + camera capture — Task 8
  - ✅ Audio modal with file picker + in-browser MediaRecorder — Task 9
  - ✅ Locale strings for all new UI — Task 4

- **Type consistency:** `MediaInput` defined in Task 1 is imported in Tasks 2 and 3. `audio_supported` defined in Task 1 is imported in Task 3. `appApi.capabilities()` added in Task 4 is used in Tasks 5, 6, and 8. `gemsApi.run()` signature extended in Task 4 is called with the new params in Task 9. All consistent.

- **No placeholders:** All steps contain complete code.
