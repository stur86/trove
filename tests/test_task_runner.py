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
