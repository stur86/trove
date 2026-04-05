# Gems — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Gems backend: locale relocation, Task→UserTask model split, Pydantic AI runner, and the full Gems REST API.

**Architecture:** `Task` becomes a pure template definition; `UserTask(Task)` adds identity/display fields. A reusable `runner.py` (Pydantic AI + OllamaModel) provides `stream_task` and `run_task` callable from anywhere. `tasks/router.py` is a thin wrapper mounted into the existing app router.

**Tech Stack:** Python, FastAPI, Pydantic v2, Pydantic AI, SQLite, pytest

---

### Task 1: Fix fixture conflict + extract auth + move locales

**Files:**
- Modify: `tests/conftest.py`
- Create: `backend/app/auth.py`
- Modify: `backend/app/router.py`
- Move: `backend/i18n/locales/` → `locales/` (project root)
- Modify: `backend/i18n/loader.py`

`config_dir` and `data_dir` fixtures both create `tmp_path / "trove"`, which conflicts when a test uses both. Fix by using `tmp_path / "config"` and `tmp_path / "data"` as their respective XDG bases. Also extract `require_admin` from `backend/app/router.py` into `backend/app/auth.py` so `backend/tasks/router.py` can import it without a circular dependency. Finally, move locale files to the project root.

- [ ] **Step 1: Fix conftest.py fixtures**

Replace the entire `tests/conftest.py` with:

```python
"""
Shared pytest fixtures for the Trove test suite.

config_dir: redirects XDG_CONFIG_HOME to tmp_path/config so tests never
            touch the real ~/.config/trove/.
data_dir:   redirects XDG_DATA_HOME  to tmp_path/data  so tests never
            touch the real ~/.local/share/trove/.

Using separate subdirectories means both fixtures can be used together
in the same test without conflicts.
"""
import pytest
from backend.ollama.service import get_ollama_service
from backend.system.service import get_system_service


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect XDG_CONFIG_HOME to a temp subdirectory for config tests."""
    xdg = tmp_path / "config"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    config_path = xdg / "trove"
    config_path.mkdir()
    return config_path


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect XDG_DATA_HOME to a temp subdirectory for DB tests."""
    xdg = tmp_path / "data"
    xdg.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    data_path = xdg / "trove"
    data_path.mkdir()
    return data_path


def _clear_lru_caches():
    """Clear LRU caches for service factories to avoid cross-test interference."""
    get_ollama_service.cache_clear()
    get_system_service.cache_clear()


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear LRU caches before each test to avoid cross-test interference."""
    _clear_lru_caches()
    yield
    _clear_lru_caches()
```

- [ ] **Step 2: Run existing tests to verify no regressions from fixture change**

```bash
uv run pytest -v 2>&1 | tail -20
```

Expected: all 116 tests PASS. (The config_dir fixture now sets XDG_CONFIG_HOME to `tmp_path/config` instead of `tmp_path` — `get_config_dir()` still returns `xdg/trove`, so all config tests remain valid.)

- [ ] **Step 3: Extract require_admin to backend/app/auth.py**

Create `backend/app/auth.py`:

```python
"""
Admin authentication dependency for Trove FastAPI routes.

Provides require_admin(), a FastAPI dependency that validates HTTP Basic
credentials against the stored admin_username / admin_password in TroveConfig.
Import this in any router that needs admin-gated endpoints.
"""
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.config.service import load_config

_security = HTTPBasic()


def require_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> None:
    """
    Verify admin credentials from HTTP Basic auth.

    Raises HTTP 401 if:
    - admin_password is empty (setup not complete)
    - username or password do not match config
    """
    config = load_config()
    if (
        not config.admin_password
        or credentials.username != config.admin_username
        or credentials.password != config.admin_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials or admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )
```

- [ ] **Step 4: Update backend/app/router.py to import require_admin from auth.py**

Replace the entire `backend/app/router.py` with:

```python
"""
FastAPI router for the app domain.

Mounted only in app mode. Provides:
  - GET /api/app/status — public health check
  - PUT /api/app/admin/config — save config (requires admin auth)
  - POST /api/app/admin/build-model — build trove_model SSE (requires admin auth)

The require_admin dependency is defined in backend.app.auth and shared
with other domain routers that need admin-gated endpoints.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.app.auth import require_admin
from backend.config.models import TroveConfig
from backend.config.service import load_config, save_config
from backend.ollama.service import OllamaService, get_ollama_service

router = APIRouter(prefix="/api/app", tags=["app"])


@router.get("/status")
def app_status() -> dict:
    """Confirm app mode is active. Used by the frontend as a health check."""
    return {"mode": "app", "status": "ok"}


@router.put("/admin/config", dependencies=[Depends(require_admin)])
def update_config(config: TroveConfig) -> TroveConfig:
    """
    Save updated configuration to disk.

    Requires admin credentials via HTTP Basic auth.
    """
    save_config(config)
    return config


@router.post("/admin/build-model", dependencies=[Depends(require_admin)])
def build_model(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> StreamingResponse:
    """
    Generate the Modelfile and build trove_model, streaming SSE progress.

    Requires admin credentials.
    """
    return StreamingResponse(
        service.build_trove_model(),
        media_type="text/event-stream",
    )
```

- [ ] **Step 5: Run tests to confirm auth refactor is clean**

```bash
uv run pytest tests/test_app_router.py -v 2>&1 | tail -15
```

Expected: all app router tests PASS.

- [ ] **Step 6: Move locale files to project root**

```bash
mkdir -p /home/simon/trove/locales
mv /home/simon/trove/backend/i18n/locales/en.json /home/simon/trove/locales/en.json
mv /home/simon/trove/backend/i18n/locales/it.json /home/simon/trove/locales/it.json
rmdir /home/simon/trove/backend/i18n/locales
```

- [ ] **Step 7: Update backend/i18n/loader.py LOCALES_DIR**

Replace `backend/i18n/loader.py` with:

```python
"""
i18n locale loader.

Reads JSON locale files from the shared locales/ directory at the project root.
Falls back to English if the requested locale doesn't exist.
"""
import json
from pathlib import Path

# Locale files live at the project root, shared between backend and frontend dev server.
# This file is at backend/i18n/loader.py — three parents up is the project root.
LOCALES_DIR = Path(__file__).parent.parent.parent / "locales"


def load_locale(locale: str) -> dict[str, str]:
    """
    Load a locale file by BCP-47 code (e.g. 'en', 'fr').

    Falls back to 'en' silently if the requested locale doesn't exist.
    Returns a flat dict of dot-separated keys to translated strings.
    """
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        path = LOCALES_DIR / "en.json"
    return json.loads(path.read_text())


def list_locales() -> list[str]:
    """Return the BCP-47 codes of all available locales (stems of .json files)."""
    return [p.stem for p in LOCALES_DIR.glob("*.json")]
```

- [ ] **Step 8: Run i18n tests to confirm locale move is clean**

```bash
uv run pytest tests/test_i18n.py -v 2>&1 | tail -10
```

Expected: all 6 tests PASS.

- [ ] **Step 9: Run full suite**

```bash
uv run pytest -v 2>&1 | tail -5
```

Expected: all tests PASS.

- [ ] **Step 10: Commit**

```bash
git add tests/conftest.py backend/app/auth.py backend/app/router.py \
        backend/i18n/loader.py locales/en.json locales/it.json
git rm backend/i18n/locales/en.json backend/i18n/locales/it.json 2>/dev/null || true
git commit -m "refactor: extract require_admin, move locales to project root, fix fixture conflict"
```

---

### Task 2: Refactor Task → Task + UserTask + GemHue

**Files:**
- Modify: `backend/tasks/models.py`
- Modify: `tests/test_task_models.py`
- Modify: `tests/test_task_render.py`

`Task` loses `id`, `name`, `description`. `UserTask(Task)` gains them plus `hue`. All tests that created `Task(id=..., name=...)` must switch to either plain `Task(template=...)` (for render tests) or `UserTask(id=..., name=..., template=...)` (for repository tests — done in Task 3).

- [ ] **Step 1: Update tests/test_task_models.py**

Replace the entire file:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_task_models.py -v 2>&1 | tail -5
```

Expected: collection error — `GemHue`, `UserTask` not yet defined.

- [ ] **Step 3: Replace backend/tasks/models.py**

```python
"""Task data models for Trove.

Task is a pure, immutable prompt definition (template + args + capabilities).
UserTask extends Task with the identity and display fields needed for user-facing
Gems stored in the database. Internal tasks use plain Task instances.
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


class GemHue(str, Enum):
    """
    16 preconfigured display colours for user-facing Gems.

    Named after Tailwind CSS colour palette entries. Used by GemIcon
    in the frontend to select facet colours.
    """

    RED = "red"
    ORANGE = "orange"
    AMBER = "amber"
    YELLOW = "yellow"
    LIME = "lime"
    GREEN = "green"
    EMERALD = "emerald"
    TEAL = "teal"
    CYAN = "cyan"
    SKY = "sky"
    BLUE = "blue"
    INDIGO = "indigo"
    VIOLET = "violet"
    PURPLE = "purple"
    FUCHSIA = "fuchsia"
    ROSE = "rose"


class Task(BaseModel, frozen=True):
    """
    Immutable, pure prompt definition.

    Contains only what is needed to render and execute a prompt:
    a Jinja2 template, typed arguments, multimodal capability flags,
    and the expected output mode. Has no identity or display fields.

    Use render_prompt() from backend.tasks.render to fill in argument
    values and produce a final prompt string.
    """

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


class UserTask(Task):
    """
    A user-defined Task with identity and display metadata.

    Stored in SQLite. Listed by the public Gems API. Rendered in the
    frontend as a Gem card with icon, name, description, and hue.
    """

    id: str
    """Unique slug identifier (e.g. 'summarise-text')."""
    name: str
    """Human-readable title displayed in the UI."""
    description: str = ""
    """Brief explanation of what this Gem does, shown in the card grid."""
    hue: GemHue = GemHue.INDIGO
    """Display colour for the GemIcon. Admin-chosen from 16 preset hues."""
```

- [ ] **Step 4: Run model tests**

```bash
uv run pytest tests/test_task_models.py -v 2>&1 | tail -20
```

Expected: all 14 tests PASS.

- [ ] **Step 5: Update tests/test_task_render.py**

`render_prompt` operates on `Task`. Strip `id`/`name` from all fixtures since plain `Task` no longer has those fields. Replace the entire file:

```python
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
```

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -v 2>&1 | tail -10
```

Expected: all tests PASS. (Repository and render tests use fixtures that still pass `id`/`name` to `Task` — those will fail until Task 3 updates the repository tests. If you see failures only in `test_task_repository.py`, that is expected — proceed.)

- [ ] **Step 7: Commit**

```bash
git add backend/tasks/models.py tests/test_task_models.py tests/test_task_render.py
git commit -m "feat: split Task into Task + UserTask, add GemHue enum"
```

---

### Task 3: Update repository for UserTask + hue + add delete_task

**Files:**
- Modify: `backend/tasks/repository.py`
- Modify: `tests/test_task_repository.py`

- [ ] **Step 1: Replace tests/test_task_repository.py**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_task_repository.py -v 2>&1 | tail -5
```

Expected: import errors or assertion errors — `UserTask`, `GemHue`, `delete_task` not found yet.

- [ ] **Step 3: Replace backend/tasks/repository.py**

```python
"""
SQLite repository for UserTask persistence.

Owns the 'tasks' table. Uses backend.db.get_db() for connections.
Args are stored as a JSON array with a 'type' discriminator field
for round-tripping via Pydantic's TypeAdapter.
"""
import json

from pydantic import TypeAdapter

from backend.db import get_db
from backend.tasks.models import TaskArg, UserTask

_arg_adapter: TypeAdapter[TaskArg] = TypeAdapter(TaskArg)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    hue         TEXT NOT NULL DEFAULT 'indigo',
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


def _row_to_user_task(row) -> UserTask:
    """Deserialise a sqlite3.Row into a UserTask, reconstructing the args union."""
    args = tuple(_arg_adapter.validate_python(a) for a in json.loads(row["args"]))
    return UserTask(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        hue=row["hue"],
        template=row["template"],
        args=args,
        has_image=bool(row["has_image"]),
        has_audio=bool(row["has_audio"]),
        output_mode=row["output_mode"],
    )


def save_task(task: UserTask) -> None:
    """
    Persist a UserTask to the database.

    Uses INSERT OR REPLACE, so calling save_task() with an existing id
    overwrites the previous record.
    """
    args_json = json.dumps([arg.model_dump() for arg in task.args])
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO tasks
               (id, name, description, hue, template, args, has_image, has_audio, output_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id,
                task.name,
                task.description,
                task.hue.value,
                task.template,
                args_json,
                int(task.has_image),
                int(task.has_audio),
                task.output_mode.value,
            ),
        )


def load_task(task_id: str) -> UserTask:
    """
    Load a UserTask by id.

    Raises:
        KeyError: if no task with the given id exists in the database.
    """
    with get_db() as conn:
        _ensure_table(conn)
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise KeyError(task_id)
    return _row_to_user_task(row)


def delete_task(task_id: str) -> None:
    """
    Delete a UserTask by id. No-op if the task does not exist.
    """
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def list_tasks() -> list[UserTask]:
    """Return all UserTasks stored in the database, ordered by id."""
    with get_db() as conn:
        _ensure_table(conn)
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [_row_to_user_task(row) for row in rows]
```

- [ ] **Step 4: Run repository tests**

```bash
uv run pytest tests/test_task_repository.py -v 2>&1 | tail -20
```

Expected: all 13 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest -v 2>&1 | tail -5
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/tasks/repository.py tests/test_task_repository.py
git commit -m "feat: update repository for UserTask + hue column + delete_task"
```

---

### Task 4: Add pydantic-ai dependency + implement runner

**Files:**
- Modify: `pyproject.toml`
- Create: `backend/tasks/runner.py`
- Create: `tests/test_task_runner.py`

The runner uses Pydantic AI with `OllamaModel("trove_model")`. A `_ThinkFilter` state machine strips `<think>…</think>` blocks from streamed output. Both `stream_task` and `run_task` accept an optional `_agent` parameter for testing without a real Ollama instance.

- [ ] **Step 1: Add pydantic-ai to pyproject.toml**

In `pyproject.toml`, add to the `dependencies` list:

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
    "pydantic-ai>=0.0.54",
]
```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync --group dev
```

Expected: pydantic-ai and its dependencies install without errors.

- [ ] **Step 3: Write failing tests**

Create `tests/test_task_runner.py`:

```python
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
    agent = Agent(TestModel(custom_result_text="Hello world"))
    chunks = []
    async for chunk in stream_task(task, {}, _agent=agent):
        chunks.append(chunk)
    assert "Hello world" in "".join(chunks)


@pytest.mark.asyncio
async def test_stream_task_filters_thinking_tokens():
    task = Task(template="Think")
    agent = Agent(TestModel(custom_result_text="<think>reasoning</think>Answer"))
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
    agent = Agent(TestModel(custom_result_text="The answer is 4"))
    result = await run_task(task, {}, _agent=agent)
    assert result == "The answer is 4"


@pytest.mark.asyncio
async def test_run_task_strips_thinking_tokens():
    task = Task(template="Think hard")
    agent = Agent(TestModel(custom_result_text="<think>working...</think>42"))
    result = await run_task(task, {}, _agent=agent)
    assert "thinking" not in result
    assert "42" in result


@pytest.mark.asyncio
async def test_run_task_renders_template_before_running():
    task = Task(
        template="Translate: {{ text }}",
        args=(),
    )
    agent = Agent(TestModel(custom_result_text="Bonjour"))
    # render_prompt is called internally; passing values works
    result = await run_task(task, {"text": "Hello"}, _agent=agent)
    assert result == "Bonjour"
```

- [ ] **Step 4: Run tests to confirm they fail**

```bash
uv run pytest tests/test_task_runner.py -v 2>&1 | tail -5
```

Expected: `ImportError` — `backend.tasks.runner` does not exist yet.

- [ ] **Step 5: Implement backend/tasks/runner.py**

```python
"""
Pydantic AI task runner for Trove.

Provides two execution functions:
  stream_task — streams text tokens, filtering <think>…</think> blocks
  run_task    — returns full response string (for structured output + internal use)

Both accept a plain Task (or UserTask subclass) and a values dict, making
them reusable from any context — HTTP handler, scheduled job, internal pipeline.
Neither function is aware of HTTP or SSE; formatting is the caller's concern.
"""
import re
from collections.abc import AsyncIterator

from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel

from backend.tasks.models import Task
from backend.tasks.render import render_prompt


def _default_agent() -> Agent:
    """Create a Pydantic AI Agent backed by the local trove_model Ollama model."""
    return Agent(OllamaModel("trove_model"))


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

        Keeps up to 7 trailing characters buffered when not in a think block
        (the length of '<think>') to guard against tags split across chunks.
        """
        self._buf += chunk
        out: list[str] = []

        while True:
            if self._in_think:
                idx = self._buf.find("</think>")
                if idx == -1:
                    # End tag not yet seen — discard all but a short tail
                    if len(self._buf) > 8:  # len("</think>") == 8
                        self._buf = self._buf[-8:]
                    return ""
                # End tag found — discard think content, resume normal output
                self._buf = self._buf[idx + 8:]
                self._in_think = False
            else:
                idx = self._buf.find("<think>")
                if idx == -1:
                    # No think tag — yield all but last 7 chars as partial-tag guard
                    safe = max(0, len(self._buf) - 7)
                    out.append(self._buf[:safe])
                    self._buf = self._buf[safe:]
                    return "".join(out)
                # Start tag found — yield content before it, enter think mode
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
    _agent: Agent | None = None,
) -> AsyncIterator[str]:
    """
    Stream text tokens for a task, filtering out thinking tokens.

    Args:
        task: The task to run (Task or UserTask).
        values: Argument values keyed by arg name.
        _agent: Optional Agent override for testing without a real Ollama instance.

    Yields:
        Filtered text chunks suitable for streaming to the client.
    """
    prompt = render_prompt(task, values)
    agent = _agent or _default_agent()
    filt = _ThinkFilter()

    async with agent.run_stream(prompt) as response:
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
        _agent: Optional Agent override for testing.

    Returns:
        The complete response with thinking tokens removed and whitespace stripped.
    """
    prompt = render_prompt(task, values)
    agent = _agent or _default_agent()
    result = await agent.run(prompt)
    text: str = result.data
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
```

- [ ] **Step 6: Run runner tests**

```bash
uv run pytest tests/test_task_runner.py -v 2>&1 | tail -20
```

Expected: all 10 tests PASS.

- [ ] **Step 7: Run full suite**

```bash
uv run pytest -v 2>&1 | tail -5
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock backend/tasks/runner.py tests/test_task_runner.py
git commit -m "feat: add Pydantic AI task runner (stream_task, run_task, ThinkFilter)"
```

---

### Task 5: Implement gems router + register in app router

**Files:**
- Create: `backend/tasks/router.py`
- Modify: `backend/app/router.py`
- Create: `tests/test_gems_router.py`

The gems router mounts 6 endpoints under the `/api/app` prefix (inherited from the parent). The run endpoint uses `stream_task`, which is monkeypatched in tests to avoid real Ollama calls.

- [ ] **Step 1: Write failing tests**

Create `tests/test_gems_router.py`:

```python
"""Tests for the Gems REST API endpoints."""
import base64
import pytest
from fastapi.testclient import TestClient

from backend.tasks.models import GemHue, StringArg, UserTask
from backend.tasks.repository import save_task


def _auth(username: str = "admin", password: str = "testpass") -> str:
    return f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"


@pytest.fixture
def client(config_dir, data_dir, monkeypatch):
    """App-mode TestClient with admin credentials and fake services."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.config.service import load_config, save_config
    cfg = load_config()
    cfg = cfg.model_copy(update={"admin_username": "admin", "admin_password": "testpass"})
    save_config(cfg)
    from backend.main import create_app_app
    return TestClient(create_app_app())


@pytest.fixture
def sample_gem(data_dir):
    task = UserTask(
        id="hello",
        name="Hello Gem",
        description="Says hello",
        template="Hello, {{ name }}!",
        args=(StringArg(name="name", default="World"),),
        hue=GemHue.EMERALD,
    )
    save_task(task)
    return task


# --- List ---

def test_list_gems_empty(client):
    res = client.get("/api/app/gems")
    assert res.status_code == 200
    assert res.json() == []


def test_list_gems_returns_saved(client, sample_gem):
    res = client.get("/api/app/gems")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "hello"
    assert data[0]["hue"] == "emerald"


# --- Get single ---

def test_get_gem_found(client, sample_gem):
    res = client.get("/api/app/gems/hello")
    assert res.status_code == 200
    assert res.json()["name"] == "Hello Gem"


def test_get_gem_not_found(client):
    res = client.get("/api/app/gems/missing")
    assert res.status_code == 404


# --- Create ---

def test_create_gem_requires_auth(client):
    payload = {"id": "new", "name": "New", "template": "Hi", "args": [], "has_image": False,
               "has_audio": False, "output_mode": "text", "description": "", "hue": "indigo"}
    res = client.post("/api/app/admin/gems", json=payload)
    assert res.status_code == 401


def test_create_gem_with_auth(client):
    payload = {"id": "new-gem", "name": "New Gem", "template": "Hi {{ name }}",
               "args": [{"type": "string", "name": "name", "description": "", "default": ""}],
               "has_image": False, "has_audio": False, "output_mode": "text",
               "description": "A new gem", "hue": "rose"}
    res = client.post("/api/app/admin/gems", json=payload,
                      headers={"Authorization": _auth()})
    assert res.status_code == 201
    assert res.json()["id"] == "new-gem"


# --- Update ---

def test_update_gem_requires_auth(client, sample_gem):
    payload = {"id": "hello", "name": "Updated", "template": "Hi",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "indigo"}
    res = client.put("/api/app/admin/gems/hello", json=payload)
    assert res.status_code == 401


def test_update_gem_not_found(client):
    payload = {"id": "ghost", "name": "Ghost", "template": "Boo",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "indigo"}
    res = client.put("/api/app/admin/gems/ghost", json=payload,
                     headers={"Authorization": _auth()})
    assert res.status_code == 404


def test_update_gem_success(client, sample_gem):
    payload = {"id": "hello", "name": "Updated Hello", "template": "Hi {{ name }}",
               "args": [], "has_image": False, "has_audio": False,
               "output_mode": "text", "description": "", "hue": "sky"}
    res = client.put("/api/app/admin/gems/hello", json=payload,
                     headers={"Authorization": _auth()})
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Hello"


# --- Delete ---

def test_delete_gem_requires_auth(client, sample_gem):
    res = client.delete("/api/app/admin/gems/hello")
    assert res.status_code == 401


def test_delete_gem_success(client, sample_gem):
    res = client.delete("/api/app/admin/gems/hello",
                        headers={"Authorization": _auth()})
    assert res.status_code == 204
    assert client.get("/api/app/gems/hello").status_code == 404


def test_delete_gem_not_found(client):
    res = client.delete("/api/app/admin/gems/ghost",
                        headers={"Authorization": _auth()})
    assert res.status_code == 404


# --- Run ---

def test_run_gem_streams_sse(client, sample_gem, monkeypatch):
    async def fake_stream(task, values, **kwargs):
        yield "Hello"
        yield " world"

    monkeypatch.setattr("backend.tasks.router.stream_task", fake_stream)
    res = client.post("/api/app/gems/hello/run", json={"values": {"name": "Alice"}})
    assert res.status_code == 200
    assert "Hello" in res.text
    assert "[DONE]" in res.text


def test_run_gem_not_found(client):
    res = client.post("/api/app/gems/missing/run", json={"values": {}})
    assert res.status_code == 404
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_gems_router.py -v 2>&1 | tail -5
```

Expected: `ImportError` — `backend.tasks.router` does not exist yet.

- [ ] **Step 3: Create backend/tasks/router.py**

```python
"""
FastAPI router for Gems (user-defined Tasks).

Provides public endpoints for listing and running Gems, and admin-gated
endpoints for creating, updating, and deleting them. This router has no
prefix of its own — it inherits /api/app from the parent app router.

All execution goes through backend.tasks.runner, keeping this file
as a thin HTTP wrapper.
"""
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.auth import require_admin
from backend.tasks.models import OutputMode, UserTask
from backend.tasks.repository import delete_task, list_tasks, load_task, save_task
from backend.tasks.runner import stream_task

router = APIRouter(tags=["gems"])


class RunRequest(BaseModel):
    """Request body for the run endpoint."""

    values: dict[str, str] = {}
    """Argument values keyed by arg name. Missing keys fall back to arg defaults."""


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


@router.post("/admin/gems", dependencies=[Depends(require_admin)], status_code=201)
def create_gem(gem: UserTask) -> UserTask:
    """
    Create a new Gem. Requires admin credentials.

    If a Gem with the same id already exists it is overwritten.
    """
    save_task(gem)
    return gem


@router.put("/admin/gems/{gem_id}", dependencies=[Depends(require_admin)])
def update_gem(gem_id: str, gem: UserTask) -> UserTask:
    """
    Update an existing Gem. Requires admin credentials.

    Raises 404 if the Gem does not exist (use POST to create).
    """
    try:
        load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")
    save_task(gem)
    return gem


@router.delete("/admin/gems/{gem_id}", dependencies=[Depends(require_admin)],
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
    Run a Gem with the provided argument values.

    For TEXT output mode: streams server-sent events (data: lines).
    Each token is a separate data line; streaming ends with data: [DONE].

    For STRUCTURED output mode: returns HTTP 501 (not yet implemented).
    """
    try:
        gem = load_task(gem_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Gem '{gem_id}' not found")

    if gem.output_mode == OutputMode.STRUCTURED:
        raise HTTPException(status_code=501, detail="Structured output not yet implemented")

    async def sse_generator() -> AsyncIterator[str]:
        """Wrap stream_task tokens as SSE data lines."""
        async for chunk in stream_task(gem, req.values):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
```

- [ ] **Step 4: Register gems router in backend/app/router.py**

Add the following import and `include_router` call at the bottom of `backend/app/router.py` (after the existing route definitions):

```python
# At the bottom of backend/app/router.py, after the build_model route:

from backend.tasks.router import router as gems_router
router.include_router(gems_router)
```

- [ ] **Step 5: Run gems router tests**

```bash
uv run pytest tests/test_gems_router.py -v 2>&1 | tail -25
```

Expected: all 16 tests PASS.

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -v 2>&1 | tail -5
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/tasks/router.py backend/app/router.py tests/test_gems_router.py
git commit -m "feat: add Gems REST API (CRUD + SSE run endpoint)"
```
