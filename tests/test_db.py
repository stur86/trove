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
