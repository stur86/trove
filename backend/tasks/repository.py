"""
SQLite repository for UserTask persistence.

Owns the 'tasks' table. Uses backend.db.get_db() for connections.
Args are stored as a JSON array with a 'type' discriminator field
for round-tripping via Pydantic's TypeAdapter.
"""
import json

from pydantic import TypeAdapter

from backend.db import get_db
from backend.tasks.models import TaskArg, ToolId, UserTask

_arg_adapter: TypeAdapter[TaskArg] = TypeAdapter(TaskArg)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    hue             TEXT NOT NULL DEFAULT 'indigo',
    template        TEXT NOT NULL,
    args            TEXT NOT NULL,
    has_image       INTEGER NOT NULL DEFAULT 0,
    has_audio       INTEGER NOT NULL DEFAULT 0,
    output_mode     TEXT NOT NULL DEFAULT 'text',
    doc_folder_ids  TEXT NOT NULL DEFAULT '[]',
    doc_ids         TEXT NOT NULL DEFAULT '[]',
    tools           TEXT NOT NULL DEFAULT '[]'
)
"""

# ADD COLUMN statements are no-ops on databases that already have the columns.
# SQLite does not support IF NOT EXISTS on ALTER TABLE, so we swallow the error.
_ADD_DOC_COLUMNS = [
    "ALTER TABLE tasks ADD COLUMN doc_folder_ids TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE tasks ADD COLUMN doc_ids TEXT NOT NULL DEFAULT '[]'",
]


def _ensure_table(conn) -> None:
    """Create the tasks table if it does not exist, then add doc columns if missing."""
    conn.execute(_CREATE_TABLE)
    for stmt in _ADD_DOC_COLUMNS:
        try:
            conn.execute(stmt)
        except Exception:
            pass  # Column already exists — safe to ignore


def _row_to_user_task(row) -> UserTask:
    """Deserialise a sqlite3.Row into a UserTask, reconstructing the args union."""
    args = tuple(_arg_adapter.validate_python(a) for a in json.loads(row["args"]))
    doc_folder_ids = tuple(json.loads(row["doc_folder_ids"] or "[]"))
    doc_ids = tuple(json.loads(row["doc_ids"] or "[]"))
    tools = frozenset(ToolId(t) for t in json.loads(row["tools"] or "[]"))
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
        doc_folder_ids=doc_folder_ids,
        doc_ids=doc_ids,
        tools=tools,
    )


def save_task(task: UserTask) -> None:
    """
    Persist a UserTask to the database.

    Uses INSERT OR REPLACE, so calling save_task() with an existing id
    overwrites the previous record.
    """
    args_json = json.dumps([arg.model_dump() for arg in task.args])
    doc_folder_ids_json = json.dumps(list(task.doc_folder_ids))
    doc_ids_json = json.dumps(list(task.doc_ids))
    tools_json = json.dumps([tid.value for tid in task.tools])
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO tasks
               (id, name, description, hue, template, args,
                has_image, has_audio, output_mode, doc_folder_ids, doc_ids, tools)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                doc_folder_ids_json,
                doc_ids_json,
                tools_json,
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


def task_id_exists(task_id: str) -> bool:
    """Return True if a task with the given id already exists in the database."""
    with get_db() as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT 1 FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return row is not None
