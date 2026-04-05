"""Tests for Task SQLite persistence."""
import pytest
from backend.tasks.models import ChoiceArg, OutputMode, StringArg, Task
from backend.tasks.repository import load_task, save_task, list_tasks


@pytest.fixture
def sample_task():
    return Task(
        id="greet",
        name="Greeting",
        description="Greet someone",
        template="Hello, {{ name }}!",
        args=(StringArg(name="name", default="World"),),
    )


@pytest.fixture
def choice_task():
    return Task(
        id="translate",
        name="Translate",
        template="Translate '{{ text }}' to {{ language }}.",
        args=(
            StringArg(name="text"),
            ChoiceArg(name="language", options=["French", "Spanish"], default="French"),
        ),
    )


def test_save_and_load_task(data_dir, sample_task):
    save_task(sample_task)
    loaded = load_task("greet")
    assert loaded.id == "greet"
    assert loaded.name == "Greeting"
    assert loaded.template == "Hello, {{ name }}!"
    assert loaded.description == "Greet someone"


def test_load_task_raises_key_error_when_missing(data_dir):
    with pytest.raises(KeyError):
        load_task("nonexistent")


def test_save_task_overwrites_existing(data_dir, sample_task):
    save_task(sample_task)
    updated = Task(
        id="greet",
        name="Greeting v2",
        template="Hi, {{ name }}!",
    )
    save_task(updated)
    loaded = load_task("greet")
    assert loaded.name == "Greeting v2"
    assert loaded.template == "Hi, {{ name }}!"


def test_args_round_trip_string(data_dir, sample_task):
    save_task(sample_task)
    loaded = load_task("greet")
    assert len(loaded.args) == 1
    arg = loaded.args[0]
    assert arg.type == "string"
    assert arg.name == "name"
    assert arg.default == "World"


def test_args_round_trip_choice(data_dir, choice_task):
    save_task(choice_task)
    loaded = load_task("translate")
    assert len(loaded.args) == 2
    lang_arg = loaded.args[1]
    assert lang_arg.type == "choice"
    assert lang_arg.name == "language"
    assert lang_arg.options == ["French", "Spanish"]
    assert lang_arg.default == "French"


def test_task_flags_round_trip(data_dir):
    task = Task(
        id="vision",
        name="Vision Task",
        template="Describe this.",
        has_image=True,
        has_audio=False,
    )
    save_task(task)
    loaded = load_task("vision")
    assert loaded.has_image is True
    assert loaded.has_audio is False


def test_output_mode_round_trip(data_dir):
    task = Task(
        id="structured",
        name="Structured",
        template="Output JSON.",
        output_mode=OutputMode.STRUCTURED,
    )
    save_task(task)
    loaded = load_task("structured")
    assert loaded.output_mode == OutputMode.STRUCTURED


def test_list_tasks_empty(data_dir):
    assert list_tasks() == []


def test_list_tasks_returns_all(data_dir, sample_task, choice_task):
    save_task(sample_task)
    save_task(choice_task)
    tasks = list_tasks()
    assert len(tasks) == 2
    ids = {t.id for t in tasks}
    assert ids == {"greet", "translate"}
