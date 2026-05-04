"""Tests for the shared SQLite database layer."""
from pathlib import Path
import pytest
from backend.db import get_db_path, get_db


def test_get_db_path(config_dir):
    assert get_db_path() == config_dir / "trove.db"


def test_get_db_creates_file(config_dir):
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
    assert (config_dir / "trove.db").exists()


def test_get_db_commits_on_exit(config_dir):
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT, v TEXT)")
        conn.execute("INSERT INTO kv VALUES (?, ?)", ("hello", "world"))
    # New connection should see the committed row
    with get_db() as conn:
        row = conn.execute("SELECT v FROM kv WHERE k = 'hello'").fetchone()
    assert row[0] == "world"
