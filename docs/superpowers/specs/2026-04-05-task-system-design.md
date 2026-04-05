# Task System Design

**Date:** 2026-04-05

## Overview

A frozen, immutable `Task` data model with Jinja2 prompt templating, typed arguments, and SQLite persistence. No execution layer — tasks are data. APIs for task definition and usage come later.

## File Structure

```
backend/
├── db.py                # Shared SQLite init and connection manager
└── tasks/
    ├── __init__.py
    ├── models.py        # Task, StringArg, ChoiceArg, OutputMode, TaskOrigin
    ├── repository.py    # save_task(), load_task(), list_tasks()
    └── render.py        # render_prompt(task, values)
```

## Models (`tasks/models.py`)

```python
class StringArg(BaseModel, frozen=True):
    type: Literal["string"] = "string"
    name: str
    description: str = ""
    default: str = ""

class ChoiceArg(BaseModel, frozen=True):
    type: Literal["choice"] = "choice"
    name: str
    options: list[str]
    default: str = ""

TaskArg = Annotated[StringArg | ChoiceArg, Field(discriminator="type")]

class OutputMode(str, Enum):
    TEXT = "text"
    STRUCTURED = "structured"   # reserved

class TaskOrigin(str, Enum):
    INTERNAL = "internal"   # hardcoded in Python, system-invoked
    USER = "user"           # admin-defined, stored in DB

class Task(BaseModel, frozen=True):
    id: str                          # slug, e.g. "summarise-document"
    name: str
    description: str = ""
    origin: TaskOrigin
    template: str                    # Jinja2 source
    args: tuple[TaskArg, ...] = ()
    has_image: bool = False          # task accepts an image input (mock for now)
    has_audio: bool = False          # task accepts an audio input (mock for now)
    output_mode: OutputMode = OutputMode.TEXT
```

Image and audio are capability flags only — they are not named template variables and are not rendered by Jinja2. They will be passed as separate multimodal inputs at execution time.

## Persistence (`backend/db.py` + `tasks/repository.py`)

`backend/db.py` manages the SQLite file at `$XDG_DATA_HOME/trove/trove.db` (default `~/.local/share/trove/trove.db`). It is domain-agnostic — other domains will add their own tables here later.

```python
def get_db() -> Iterator[sqlite3.Connection]:
    """Context manager — yields an open connection, commits on exit."""
```

`tasks/repository.py` owns the `tasks` table:

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    origin      TEXT NOT NULL,
    template    TEXT NOT NULL,
    args        TEXT NOT NULL,       -- JSON array with "type" discriminator
    has_image   INTEGER NOT NULL DEFAULT 0,
    has_audio   INTEGER NOT NULL DEFAULT 0,
    output_mode TEXT NOT NULL DEFAULT 'text'
)
```

```python
def save_task(task: Task) -> None          # INSERT OR REPLACE
def load_task(task_id: str) -> Task        # raises KeyError if not found
def list_tasks(origin: TaskOrigin | None = None) -> list[Task]
```

## Prompt Rendering (`tasks/render.py`)

```python
def render_prompt(task: Task, values: dict[str, str]) -> str:
    """
    Fill the task's Jinja2 template with argument values.
    Merges arg defaults for missing keys before rendering.
    Raises ValueError if a required arg has no value and no default.
    Raises jinja2.TemplateError if the template is malformed.
    """
```

## Usage Pattern

Internal tasks (e.g. document summariser, schema suggester) are instantiated directly in Python and never stored in the DB unless needed. User-defined tasks are loaded from the DB before rendering.

## Out of Scope

- Task definition and usage REST APIs (later)
- Structured (JSON) output parsing (later)
- Real image/audio input handling (later)
- Auth gating on task APIs (later)
