# Task System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the core Task data model, SQLite persistence layer, and Jinja2 prompt rendering — no REST API yet, just the domain layer.

**Architecture:** Frozen Pydantic models for `Task` and its argument types; a shared `backend/db.py` for SQLite connection management (XDG data dir); a `backend/tasks/` domain with a repository for persistence and a `render_prompt()` helper.

**Tech Stack:** Python, Pydantic v2, `sqlite3` (stdlib), Jinja2

---

### Task 1: Add Jinja2 dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add jinja2 to dependencies**

In `pyproject.toml`, add `"jinja2>=3.1"` to the `dependencies` list:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2.10",
    "psutil>=6.1",
    "sse-starlette>=2.2",
    "python-dotenv>=1.0",
    "typer>=0.12",
    "jinja2>=3.1",
]
```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync --group dev
```

Expected: resolves and installs jinja2 without errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add jinja2 dependency"
```

---

### Task 2: Task models

**Files:**
- Create: `backend/tasks/__init__.py`
- Create: `backend/tasks/models.py`
- Create: `tests/test_task_models.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_task_models.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_models.py -v
```

Expected: `ImportError` — `backend.tasks.models` does not exist yet.

- [ ] **Step 3: Create the package init**

Create `backend/tasks/__init__.py` (empty):

```python
```

- [ ] **Step 4: Implement `backend/tasks/models.py`**

```python
"""Task data models for Trove.

A Task is an immutable prompt definition: a Jinja2 template, typed arguments,
capability flags, and output mode. Internal tasks are hardcoded in Python;
user-defined tasks are stored in SQLite.
"""
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class StringArg(BaseModel, frozen=True):
    """A free-text input argument for a task template."""

    type: Literal["string"] = "string"
    name: str
    """Variable name used in the Jinja2 template (e.g. 'topic')."""
    description: str = ""
    """Human-readable hint shown to the user in the UI."""
    default: str = ""
    """Value used when the caller does not supply this argument."""


class ChoiceArg(BaseModel, frozen=True):
    """A fixed-list selection argument for a task template."""

    type: Literal["choice"] = "choice"
    name: str
    """Variable name used in the Jinja2 template."""
    options: list[str]
    """Exhaustive list of allowed values."""
    description: str = ""
    default: str = ""
    """Must be one of options, or empty string for no default."""


TaskArg = Annotated[StringArg | ChoiceArg, Field(discriminator="type")]
"""Discriminated union of all argument types."""


class OutputMode(str, Enum):
    """Expected output format of a task."""

    TEXT = "text"
    STRUCTURED = "structured"  # JSON output — reserved for later


class Task(BaseModel, frozen=True):
    """
    Immutable task definition.

    A task pairs a Jinja2 prompt template with typed arguments. It cannot be
    modified after creation. Use render_prompt() from backend.tasks.render to
    fill in argument values and produce a final prompt string.
    """

    id: str
    """Unique slug identifier (e.g. 'summarise-document')."""
    name: str
    """Human-readable display name."""
    description: str = ""
    """Brief explanation of what this task does."""
    template: str
    """Jinja2 template source. Named args map to {{ variable }} placeholders."""
    args: tuple[TaskArg, ...] = ()
    """Ordered argument definitions. Only StringArg and ChoiceArg appear in templates."""
    has_image: bool = False
    """Task accepts an image input passed alongside the prompt (mock for now)."""
    has_audio: bool = False
    """Task accepts an audio input passed alongside the prompt (mock for now)."""
    output_mode: OutputMode = OutputMode.TEXT
    """Expected output format. STRUCTURED is reserved and not yet implemented."""
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_task_models.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/tasks/__init__.py backend/tasks/models.py tests/test_task_models.py
git commit -m "feat: add Task models (StringArg, ChoiceArg, Task, OutputMode)"
```

---

### Task 3: Shared DB layer

**Files:**
- Create: `backend/db.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_db.py`:

```python
"""Tests for the shared SQLite database layer."""
from pathlib import Path
import pytest
from backend.db import get_data_dir, get_db_path, get_db


def test_get_data_dir_default(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = get_data_dir()
    assert result == tmp_path / ".local" / "share" / "trove"


def test_get_data_dir_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    result = get_data_dir()
    assert result == tmp_path / "trove"


def test_get_db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert get_db_path() == tmp_path / "trove" / "trove.db"


def test_get_db_creates_file(data_dir):
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
    assert (data_dir / "trove.db").exists()


def test_get_db_commits_on_exit(data_dir):
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT, v TEXT)")
        conn.execute("INSERT INTO kv VALUES (?, ?)", ("hello", "world"))
    # New connection should see the committed row
    with get_db() as conn:
        row = conn.execute("SELECT v FROM kv WHERE k = 'hello'").fetchone()
    assert row[0] == "world"
```

- [ ] **Step 2: Add `data_dir` fixture to conftest**

Add this fixture to `tests/conftest.py` (below the existing `config_dir` fixture):

```python
@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect XDG_DATA_HOME to a temp directory for DB tests."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    data_path = tmp_path / "trove"
    data_path.mkdir()
    return data_path
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: `ImportError` — `backend.db` does not exist yet.

- [ ] **Step 4: Implement `backend/db.py`**

```python
"""
Shared SQLite database connection for Trove.

Manages the database file at $XDG_DATA_HOME/trove/trove.db
(default ~/.local/share/trove/trove.db). Domain-specific repositories
import get_db() from here and own their own table creation.
"""
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def get_data_dir() -> Path:
    """
    Return the Trove data directory, respecting the XDG Base Directory spec.

    Uses $XDG_DATA_HOME if set, otherwise defaults to ~/.local/share.
    The returned path is $XDG_DATA_HOME/trove (or ~/.local/share/trove).
    The directory is not guaranteed to exist — callers must create it if needed.
    """
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "trove"


def get_db_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    return get_data_dir() / "trove.db"


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """
    Context manager that yields an open SQLite connection.

    Creates the data directory if it does not exist. Commits on clean exit
    and closes the connection in all cases.

    Usage::

        with get_db() as conn:
            conn.execute("INSERT INTO ...")
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/db.py tests/test_db.py tests/conftest.py
git commit -m "feat: add shared SQLite DB layer (XDG data dir, get_db context manager)"
```

---

### Task 4: Task repository

**Files:**
- Create: `backend/tasks/repository.py`
- Create: `tests/test_task_repository.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_task_repository.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_repository.py -v
```

Expected: `ImportError` — `backend.tasks.repository` does not exist yet.

- [ ] **Step 3: Implement `backend/tasks/repository.py`**

```python
"""
SQLite repository for Task persistence.

Owns the 'tasks' table. Uses backend.db.get_db() for connections.
Args are stored as a JSON array; each element carries a 'type' discriminator
field for clean round-tripping via Pydantic's TypeAdapter.
"""
import json

from pydantic import TypeAdapter

from backend.db import get_db
from backend.tasks.models import Task, TaskArg

_arg_adapter: TypeAdapter[TaskArg] = TypeAdapter(TaskArg)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    template    TEXT NOT NULL,
    args        TEXT NOT NULL,
    has_image   INTEGER NOT NULL DEFAULT 0,
    has_audio   INTEGER NOT NULL DEFAULT 0,
    output_mode TEXT NOT NULL DEFAULT 'text'
)
"""


def _ensure_table(conn) -> None:
    """Create the tasks table if it does not exist."""
    conn.execute(_CREATE_TABLE)


def _row_to_task(row) -> Task:
    """Deserialise a sqlite3.Row into a Task, reconstructing the args union."""
    args = tuple(_arg_adapter.validate_python(a) for a in json.loads(row["args"]))
    return Task(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        template=row["template"],
        args=args,
        has_image=bool(row["has_image"]),
        has_audio=bool(row["has_audio"]),
        output_mode=row["output_mode"],
    )


def save_task(task: Task) -> None:
    """
    Persist a task to the database.

    Uses INSERT OR REPLACE, so calling save_task() with an existing id
    overwrites the previous record.
    """
    args_json = json.dumps([arg.model_dump() for arg in task.args])
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO tasks
               (id, name, description, template, args, has_image, has_audio, output_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id,
                task.name,
                task.description,
                task.template,
                args_json,
                int(task.has_image),
                int(task.has_audio),
                task.output_mode.value,
            ),
        )


def load_task(task_id: str) -> Task:
    """
    Load a task by id.

    Raises:
        KeyError: if no task with the given id exists in the database.
    """
    with get_db() as conn:
        _ensure_table(conn)
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise KeyError(task_id)
    return _row_to_task(row)


def list_tasks() -> list[Task]:
    """Return all tasks stored in the database, ordered by id."""
    with get_db() as conn:
        _ensure_table(conn)
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [_row_to_task(row) for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_task_repository.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/repository.py tests/test_task_repository.py
git commit -m "feat: add task repository (save, load, list via SQLite)"
```

---

### Task 5: Prompt rendering

**Files:**
- Create: `backend/tasks/render.py`
- Create: `tests/test_task_render.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_task_render.py`:

```python
"""Tests for Jinja2 prompt rendering."""
import pytest
import jinja2
from backend.tasks.models import ChoiceArg, StringArg, Task
from backend.tasks.render import render_prompt


@pytest.fixture
def greeting_task():
    return Task(
        id="greet",
        name="Greeting",
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
        id="translate",
        name="Translate",
        template="Translate '{{ text }}' to {{ language }}.",
        args=(
            StringArg(name="text"),
            ChoiceArg(name="language", options=["French", "Spanish"], default="French"),
        ),
    )
    result = render_prompt(task, {"text": "Hello"})
    assert result == "Translate 'Hello' to French."


def test_render_no_args():
    task = Task(id="static", name="Static", template="This is a static prompt.")
    result = render_prompt(task, {})
    assert result == "This is a static prompt."


def test_render_raises_template_error_for_malformed_template():
    task = Task(id="bad", name="Bad", template="{{ unclosed")
    with pytest.raises(jinja2.TemplateSyntaxError):
        render_prompt(task, {})


def test_render_unknown_variable_raises_undefined_error():
    # Template references a variable not in task.args — Jinja2 should raise
    task = Task(
        id="mystery",
        name="Mystery",
        template="Hello {{ ghost }}.",
        args=(),
    )
    with pytest.raises(jinja2.UndefinedError):
        render_prompt(task, {})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_render.py -v
```

Expected: `ImportError` — `backend.tasks.render` does not exist yet.

- [ ] **Step 3: Implement `backend/tasks/render.py`**

```python
"""
Jinja2 prompt rendering for Tasks.

Provides render_prompt(), which fills a Task's Jinja2 template with
caller-supplied argument values, merging arg defaults for missing keys.
"""
import jinja2

from backend.tasks.models import Task

_env = jinja2.Environment(undefined=jinja2.StrictUndefined)


def render_prompt(task: Task, values: dict[str, str]) -> str:
    """
    Fill the task's Jinja2 template with argument values.

    Builds a merged dict of {arg.name: arg.default} for all args, then
    overlays the caller-supplied values. Checks that every arg with an
    empty default has a supplied value — raises ValueError if not.

    Args:
        task: The task whose template will be rendered.
        values: Caller-supplied argument values keyed by arg name.

    Returns:
        The rendered prompt string.

    Raises:
        ValueError: If a required arg (empty default, no supplied value) is missing.
        jinja2.TemplateSyntaxError: If the template source is malformed.
        jinja2.UndefinedError: If the template references a variable not in task.args.
    """
    # Check required args before rendering to give a clear error message.
    missing = [
        arg.name
        for arg in task.args
        if arg.default == "" and arg.name not in values
    ]
    if missing:
        raise ValueError(f"Missing required argument(s): {', '.join(missing)}")

    # Merge defaults with supplied values (supplied values take precedence).
    merged = {arg.name: arg.default for arg in task.args}
    merged.update(values)

    template = _env.from_string(task.template)
    return template.render(**merged)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_task_render.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all existing tests plus new task tests PASS — no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/tasks/render.py tests/test_task_render.py
git commit -m "feat: add render_prompt() for Jinja2 task prompt rendering"
```
