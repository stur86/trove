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
