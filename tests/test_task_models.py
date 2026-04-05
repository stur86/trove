"""Tests for Task, UserTask, and GemHue data models."""
import pytest
from pydantic import ValidationError
from backend.tasks.models import (
    ChoiceArg,
    GemHue,
    OutputMode,
    StringArg,
    Task,
    UserTask,
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
    task = Task(template="Hello")
    with pytest.raises(ValidationError):
        task.template = "Other"


def test_task_defaults():
    task = Task(template="Hello {{ name }}")
    assert task.args == ()
    assert task.has_image is False
    assert task.has_audio is False
    assert task.output_mode == OutputMode.TEXT


def test_task_with_args():
    args = (
        StringArg(name="topic"),
        ChoiceArg(name="lang", options=["en", "fr"], default="en"),
    )
    task = Task(template="{{ topic }} in {{ lang }}", args=args)
    assert len(task.args) == 2
    assert task.args[0].name == "topic"
    assert task.args[1].name == "lang"


def test_task_with_capabilities():
    task = Task(template="Describe the image.", has_image=True)
    assert task.has_image is True
    assert task.has_audio is False


def test_output_mode_enum():
    assert OutputMode.TEXT.value == "text"
    assert OutputMode.STRUCTURED.value == "structured"


def test_gem_hue_has_sixteen_values():
    assert len(list(GemHue)) == 16


def test_gem_hue_values():
    assert GemHue.INDIGO.value == "indigo"
    assert GemHue.RED.value == "red"
    assert GemHue.EMERALD.value == "emerald"


def test_user_task_defaults():
    task = UserTask(id="t1", name="Test", template="Hello")
    assert task.description == ""
    assert task.hue == GemHue.INDIGO


def test_user_task_inherits_task_fields():
    task = UserTask(id="t1", name="Test", template="Hello", has_image=True)
    assert task.has_image is True
    assert task.output_mode == OutputMode.TEXT


def test_user_task_is_frozen():
    task = UserTask(id="t1", name="Test", template="Hello")
    with pytest.raises(ValidationError):
        task.name = "Other"


def test_user_task_custom_hue():
    task = UserTask(id="t1", name="Test", template="Hi", hue=GemHue.EMERALD)
    assert task.hue == GemHue.EMERALD
