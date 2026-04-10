"""Tests for UserTask SQLite persistence."""
import pytest
from backend.tasks.models import ChoiceArg, GemHue, OutputMode, StringArg, UserTask
from backend.tasks.repository import delete_task, list_tasks, load_task, save_task


@pytest.fixture
def sample_task():
    return UserTask(
        id="greet",
        name="Greeting",
        description="Greet someone",
        template="Hello, {{ name }}!",
        args=(StringArg(name="name", default="World"),),
    )


@pytest.fixture
def choice_task():
    return UserTask(
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
    updated = UserTask(id="greet", name="Greeting v2", template="Hi, {{ name }}!")
    save_task(updated)
    loaded = load_task("greet")
    assert loaded.name == "Greeting v2"


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
    lang_arg = loaded.args[1]
    assert lang_arg.type == "choice"
    assert lang_arg.name == "language"
    assert lang_arg.options == ["French", "Spanish"]
    assert lang_arg.default == "French"


def test_task_flags_round_trip(data_dir):
    task = UserTask(id="vision", name="Vision", template="Describe.", has_image=True)
    save_task(task)
    loaded = load_task("vision")
    assert loaded.has_image is True
    assert loaded.has_audio is False


def test_output_mode_round_trip(data_dir):
    task = UserTask(id="structured", name="Structured", template="JSON.", output_mode=OutputMode.STRUCTURED)
    save_task(task)
    loaded = load_task("structured")
    assert loaded.output_mode == OutputMode.STRUCTURED


def test_hue_round_trip(data_dir):
    task = UserTask(id="emerald-gem", name="Emerald", template="Hi", hue=GemHue.EMERALD)
    save_task(task)
    loaded = load_task("emerald-gem")
    assert loaded.hue == GemHue.EMERALD


def test_default_hue_is_indigo(data_dir):
    task = UserTask(id="default-gem", name="Default", template="Hi")
    save_task(task)
    loaded = load_task("default-gem")
    assert loaded.hue == GemHue.INDIGO


def test_list_tasks_empty(data_dir):
    assert list_tasks() == []


def test_list_tasks_returns_all(data_dir, sample_task, choice_task):
    save_task(sample_task)
    save_task(choice_task)
    tasks = list_tasks()
    assert len(tasks) == 2
    assert {t.id for t in tasks} == {"greet", "translate"}


def test_delete_task(data_dir, sample_task):
    save_task(sample_task)
    delete_task("greet")
    with pytest.raises(KeyError):
        load_task("greet")


def test_delete_task_nonexistent_is_noop(data_dir):
    delete_task("does-not-exist")  # should not raise


# ── doc fields round-trip (Task 6) ───────────────────────────────────────────

def test_save_and_load_task_with_doc_fields(data_dir):
    task = UserTask(
        id="t1",
        name="T1",
        template="Hello",
        doc_folder_ids=("hr", "finance"),
        doc_ids=("policy-doc",),
    )
    save_task(task)
    loaded = load_task("t1")
    assert loaded.doc_folder_ids == ("hr", "finance")
    assert loaded.doc_ids == ("policy-doc",)


def test_existing_task_without_doc_fields_loads_with_defaults(data_dir):
    """Tasks saved before doc columns existed default to empty tuples."""
    import sqlite3
    from backend.db import get_db_path
    from backend.tasks.repository import _ensure_table

    # Simulate old-style task without doc columns by inserting directly
    with sqlite3.connect(str(get_db_path())) as conn:
        conn.row_factory = sqlite3.Row
        # Ensure table exists first
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO tasks (id, name, description, hue, template, args, has_image, has_audio, output_mode)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("legacy", "Legacy", "", "indigo", "Hi", "[]", 0, 0, "text"),
        )
        conn.commit()

    loaded = load_task("legacy")
    assert loaded.doc_folder_ids == ()
    assert loaded.doc_ids == ()
