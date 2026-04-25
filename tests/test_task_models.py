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


# ── MediaInput ────────────────────────────────────────────────────────────────

from backend.tasks.models import AUDIO_CAPABLE_MODELS, MediaInput, audio_supported  # noqa: E402


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


# ── audio_supported ───────────────────────────────────────────────────────────

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


# ── doc fields (Task 6) ───────────────────────────────────────────────────────

def test_user_task_defaults_to_empty_doc_fields():
    task = UserTask(id="t1", name="T1", template="Hello")
    assert task.doc_folder_ids == ()
    assert task.doc_ids == ()


def test_user_task_accepts_doc_fields():
    task = UserTask(
        id="t1", name="T1", template="Hello",
        doc_folder_ids=("hr", "finance"),
        doc_ids=("policy-doc",),
    )
    assert task.doc_folder_ids == ("hr", "finance")
    assert task.doc_ids == ("policy-doc",)


# ── ToolId and Task.tools (utility tools) ────────────────────────────────────

from backend.tasks.models import ToolId  # noqa: E402


def test_tool_id_values():
    assert ToolId.DATETIME.value == "datetime"
    assert ToolId.CALCULATOR.value == "calculator"


def test_tool_id_has_two_members():
    assert len(list(ToolId)) == 2


def test_task_defaults_to_empty_tools():
    task = Task(template="Hello")
    assert task.tools == frozenset()


def test_task_with_single_tool():
    task = Task(template="Hello", tools=frozenset({ToolId.DATETIME}))
    assert ToolId.DATETIME in task.tools
    assert ToolId.CALCULATOR not in task.tools


def test_task_with_multiple_tools():
    task = Task(template="Hello", tools=frozenset({ToolId.DATETIME, ToolId.CALCULATOR}))
    assert ToolId.DATETIME in task.tools
    assert ToolId.CALCULATOR in task.tools


def test_task_is_frozen_with_tools():
    task = Task(template="Hello", tools=frozenset({ToolId.DATETIME}))
    with pytest.raises(ValidationError):
        task.tools = frozenset()  # type: ignore[misc]


def test_user_task_inherits_tools_field():
    task = UserTask(
        id="t1", name="T", template="Hi",
        tools=frozenset({ToolId.CALCULATOR}),
    )
    assert ToolId.CALCULATOR in task.tools
