"""
Shared SQLite database connection for Trove.

Manages the database file at ~/.config/trove/trove.db.
Path resolution is centralised in backend.paths.
Domain-specific repositories import get_db() from here and own their own
table creation.
"""
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from backend.paths import get_config_dir


def get_db_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    return get_config_dir() / "trove.db"


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """
    Context manager that yields an open SQLite connection.

    Creates the config directory if it does not exist. Commits on clean exit
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
