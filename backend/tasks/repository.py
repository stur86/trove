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
