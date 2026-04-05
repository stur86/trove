"""Tests for Task data models."""
import pytest
from pydantic import ValidationError
from backend.tasks.models import (
    StringArg,
    ChoiceArg,
    Task,
    OutputMode,
)


def test_string_arg_defaults():
    arg = StringArg(name="topic")
    assert arg.type == "string"
    assert arg.description == ""
    assert arg.default == ""


def test_choice_arg_defaults():
    arg = ChoiceArg(name="language", options=["English", "French"])
    assert arg.type == "choice"
    assert arg.default == ""
    assert arg.options == ["English", "French"]


def test_task_is_frozen():
    task = Task(id="t1", name="Test", template="Hello")
    with pytest.raises(ValidationError):
        task.name = "Other"


def test_task_defaults():
    task = Task(id="t1", name="Test", template="Hello {{ name }}")
    assert task.description == ""
    assert task.args == ()
    assert task.has_image is False
    assert task.has_audio is False
    assert task.output_mode == OutputMode.TEXT


def test_task_with_args():
    args = (
        StringArg(name="topic"),
        ChoiceArg(name="lang", options=["en", "fr"], default="en"),
    )
    task = Task(id="t2", name="Multi", template="{{ topic }} in {{ lang }}", args=args)
    assert len(task.args) == 2
    assert task.args[0].name == "topic"
    assert task.args[1].name == "lang"


def test_task_with_capabilities():
    task = Task(id="t3", name="Vision", template="Describe the image.", has_image=True)
    assert task.has_image is True
    assert task.has_audio is False


def test_output_mode_enum():
    assert OutputMode.TEXT.value == "text"
    assert OutputMode.STRUCTURED.value == "structured"
