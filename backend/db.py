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
