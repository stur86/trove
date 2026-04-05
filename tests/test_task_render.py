"""Tests for Jinja2 prompt rendering."""
import pytest
import jinja2
from backend.tasks.models import ChoiceArg, StringArg, Task
from backend.tasks.render import render_prompt


@pytest.fixture
def greeting_task():
    return Task(
        template="Hello, {{ name }}! You are learning {{ topic }}.",
        args=(
            StringArg(name="name"),
            StringArg(name="topic", default="Python"),
        ),
    )


def test_render_all_values_supplied(greeting_task):
    result = render_prompt(greeting_task, {"name": "Alice", "topic": "Maths"})
    assert result == "Hello, Alice! You are learning Maths."


def test_render_uses_default_when_value_missing(greeting_task):
    result = render_prompt(greeting_task, {"name": "Bob"})
    assert result == "Hello, Bob! You are learning Python."


def test_render_raises_value_error_for_missing_required_arg(greeting_task):
    # 'name' has no default — omitting it should raise ValueError
    with pytest.raises(ValueError, match="name"):
        render_prompt(greeting_task, {})


def test_render_choice_arg():
    task = Task(
        template="Translate '{{ text }}' to {{ language }}.",
        args=(
            StringArg(name="text"),
            ChoiceArg(name="language", options=["French", "Spanish"], default="French"),
        ),
    )
    result = render_prompt(task, {"text": "Hello"})
    assert result == "Translate 'Hello' to French."


def test_render_no_args():
    task = Task(template="This is a static prompt.")
    result = render_prompt(task, {})
    assert result == "This is a static prompt."


def test_render_raises_template_error_for_malformed_template():
    task = Task(template="{{ unclosed")
    with pytest.raises(jinja2.TemplateSyntaxError):
        render_prompt(task, {})


def test_render_unknown_variable_raises_undefined_error():
    task = Task(template="Hello {{ ghost }}.", args=())
    with pytest.raises(jinja2.UndefinedError):
        render_prompt(task, {})
