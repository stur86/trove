"""Tests for the Pydantic AI task runner."""
import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from backend.tasks.models import Task
from backend.tasks.runner import _ThinkFilter, run_task, stream_task


# --- _ThinkFilter unit tests ---

def test_think_filter_passes_plain_text():
    f = _ThinkFilter()
    assert f.feed("Hello world") == "Hello"  # last 6 chars held as guard
    assert f.flush() == " world"


def test_think_filter_strips_think_block():
    f = _ThinkFilter()
    result = f.feed("<think>internal</think>Answer")
    assert "<think>" not in result
    assert "internal" not in result
    tail = f.flush()
    assert "Answer" in result + tail


def test_think_filter_strips_think_block_across_chunks():
    f = _ThinkFilter()
    r1 = f.feed("<thi")
    r2 = f.feed("nk>some </thi")
    r3 = f.feed("nk>Output")
    tail = f.flush()
    combined = r1 + r2 + r3 + tail
    assert "some" not in combined
    assert "Output" in combined


def test_think_filter_flush_returns_remaining():
    f = _ThinkFilter()
    f.feed("Hello ")
    assert f.flush() == "Hello "


def test_think_filter_discards_unclosed_think():
    f = _ThinkFilter()
    f.feed("<think>never closed")
    assert f.flush() == ""


# --- stream_task tests ---

@pytest.mark.asyncio
async def test_stream_task_yields_content():
    task = Task(template="Say hello")
    agent = Agent(TestModel(custom_output_text="Hello world"))
    chunks = []
    async for chunk in stream_task(task, {}, _agent=agent):
        chunks.append(chunk)
    assert "Hello world" in "".join(chunks)


@pytest.mark.asyncio
async def test_stream_task_filters_thinking_tokens():
    task = Task(template="Think")
    agent = Agent(TestModel(custom_output_text="<think>reasoning</think>Answer"))
    chunks = []
    async for chunk in stream_task(task, {}, _agent=agent):
        chunks.append(chunk)
    combined = "".join(chunks)
    assert "reasoning" not in combined
    assert "Answer" in combined


# --- run_task tests ---

@pytest.mark.asyncio
async def test_run_task_returns_full_response():
    task = Task(template="What is 2+2?")
    agent = Agent(TestModel(custom_output_text="The answer is 4"))
    result = await run_task(task, {}, _agent=agent)
    assert result == "The answer is 4"


@pytest.mark.asyncio
async def test_run_task_strips_thinking_tokens():
    task = Task(template="Think hard")
    agent = Agent(TestModel(custom_output_text="<think>working...</think>42"))
    result = await run_task(task, {}, _agent=agent)
    assert "thinking" not in result
    assert "42" in result


@pytest.mark.asyncio
async def test_run_task_renders_template_before_running():
    task = Task(
        template="Translate: {{ text }}",
        args=(),
    )
    agent = Agent(TestModel(custom_output_text="Bonjour"))
    # render_prompt is called internally; passing values works
    result = await run_task(task, {"text": "Hello"}, _agent=agent)
    assert result == "Bonjour"


# ── _build_parts ──────────────────────────────────────────────────────────────

from pydantic_ai import BinaryContent  # noqa: E402
from backend.tasks.models import MediaInput  # noqa: E402
from backend.tasks.runner import _build_parts  # noqa: E402


def test_build_parts_text_only_returns_string():
    result = _build_parts("Hello", None)
    assert result == "Hello"


def test_build_parts_empty_media_returns_string():
    """MediaInput with no bytes set behaves the same as None."""
    result = _build_parts("Hello", MediaInput())
    assert result == "Hello"


def test_build_parts_with_image_returns_list():
    media = MediaInput(image=b"\xff\xd8\xff", image_mime="image/jpeg")
    result = _build_parts("Describe this", media)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], BinaryContent)
    assert result[0].data == b"\xff\xd8\xff"
    assert result[0].media_type == "image/jpeg"
    assert result[1] == "Describe this"


def test_build_parts_with_audio_returns_list():
    media = MediaInput(audio=b"\x1a\x45\xdf\xa3", audio_mime="audio/webm")
    result = _build_parts("Transcribe", media)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], BinaryContent)
    assert result[0].media_type == "audio/webm"
    assert result[1] == "Transcribe"


def test_build_parts_with_image_and_audio_returns_three_parts():
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


# ── stream_task / run_task with MediaInput ────────────────────────────────────

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


# ── Document tool injection (Task 7) ─────────────────────────────────────────

from datetime import datetime, timezone  # noqa: E402
from backend.documents.models import Document  # noqa: E402
from backend.tasks.runner import _build_document_tools  # noqa: E402


def _make_doc(doc_id: str, folder_id: str = "f1", description: str = "A doc") -> Document:
    return Document(
        id=doc_id, folder_id=folder_id, name=f"{doc_id}.txt",
        description=description, mime_type="text/plain",
        created_at=datetime.now(timezone.utc),
    )


def test_build_document_tools_returns_two_callables():
    tools = _build_document_tools([_make_doc("d1")])
    assert len(tools) == 2
    assert callable(tools[0])
    assert callable(tools[1])


def test_get_table_of_contents_lists_all_docs():
    docs = [
        _make_doc("d1", description="First document."),
        _make_doc("d2", description="Second document."),
    ]
    toc_fn, _ = _build_document_tools(docs)
    result = toc_fn()
    assert "[d1]" in result
    assert "First document." in result
    assert "[d2]" in result
    assert "Second document." in result


def test_get_document_returns_file_content(data_dir):
    doc_dir = data_dir / "documents" / "f1"
    doc_dir.mkdir(parents=True)
    (doc_dir / "d1.md").write_text("# Hello\nThis is the content.")

    _, get_fn = _build_document_tools([_make_doc("d1")])
    result = get_fn("d1")
    assert "This is the content." in result


def test_get_document_out_of_scope_returns_error_string(data_dir):
    _, get_fn = _build_document_tools([_make_doc("d1")])
    result = get_fn("not-in-scope")
    assert "not" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_stream_task_with_documents_runs_without_error(data_dir):
    """Documents param accepted — agent runs normally (tool calls not asserted here)."""
    doc = _make_doc("d1")
    task = Task(template="Answer the question")
    agent = Agent(TestModel(custom_output_text="The answer"))
    chunks = []
    async for chunk in stream_task(task, {}, documents=[doc], _agent=agent):
        chunks.append(chunk)
    assert "The answer" in "".join(chunks)


@pytest.mark.asyncio
async def test_run_task_with_documents_runs_without_error(data_dir):
    doc = _make_doc("d1")
    task = Task(template="Answer")
    agent = Agent(TestModel(custom_output_text="42"))
    result = await run_task(task, {}, documents=[doc], _agent=agent)
    assert result == "42"


# ── Utility tool injection ────────────────────────────────────────────────────

from backend.tasks.models import ToolId  # noqa: E402


@pytest.mark.asyncio
async def test_stream_task_with_datetime_tool_runs():
    """Tools field on task is threaded through — agent runs without error."""
    task = Task(template="What time is it?", tools=frozenset({ToolId.DATETIME}))
    agent = Agent(TestModel(custom_output_text="It is noon."))
    chunks = []
    async for chunk in stream_task(task, {}, _agent=agent):
        chunks.append(chunk)
    assert "It is noon." in "".join(chunks)


@pytest.mark.asyncio
async def test_run_task_with_calculator_tool_returns_response():
    task = Task(template="Calculate 2+2", tools=frozenset({ToolId.CALCULATOR}))
    agent = Agent(TestModel(custom_output_text="4"))
    result = await run_task(task, {}, _agent=agent)
    assert result == "4"


@pytest.mark.asyncio
async def test_stream_task_with_both_tools_runs():
    task = Task(template="Help", tools=frozenset({ToolId.DATETIME, ToolId.CALCULATOR}))
    agent = Agent(TestModel(custom_output_text="Done."))
    chunks = []
    async for chunk in stream_task(task, {}, _agent=agent):
        chunks.append(chunk)
    assert "Done." in "".join(chunks)


from backend.tasks.runner import _make_agent  # noqa: E402


def test_make_agent_with_no_args_returns_agent():
    from pydantic_ai import Agent as PAAgent
    agent = _make_agent()
    assert isinstance(agent, PAAgent)


def test_make_agent_with_tool_ids_registers_utility_tools():
    from pydantic_ai import Agent as PAAgent
    agent = _make_agent(tool_ids=frozenset({ToolId.DATETIME, ToolId.CALCULATOR}))
    assert isinstance(agent, PAAgent)
    tool_names = set(agent._function_toolset.tools)
    assert "get_current_datetime" in tool_names
    assert "calculate" in tool_names
