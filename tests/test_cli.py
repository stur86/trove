"""Tests for the Typer CLI entry point."""
import os
import pytest
from typer.testing import CliRunner

from backend.cli import cli


runner = CliRunner()


def test_setup_command_sets_mode_and_correct_host(monkeypatch):
    """trove setup must call the setup factory and bind 127.0.0.1."""
    captured = {}

    def fake_run(app_str, **kwargs):
        captured["app_str"] = app_str
        captured.update(kwargs)

    monkeypatch.setattr("backend.cli.uvicorn.run", fake_run)
    runner.invoke(cli, ["setup"])
    assert captured.get("app_str") == "backend.main:create_app_setup"
    assert captured.get("factory") is True
    assert captured.get("host") == "127.0.0.1"
    assert captured.get("port") == 7071


def test_setup_command_custom_port(monkeypatch):
    captured = {}
    monkeypatch.setattr("backend.cli.uvicorn.run", lambda a, **kw: captured.update({"app_str": a, **kw}))
    runner.invoke(cli, ["setup", "--port", "9000"])
    assert captured.get("port") == 9000


def test_start_command_sets_mode_and_correct_host(monkeypatch):
    """trove start must call the app factory and bind 0.0.0.0."""
    captured = {}
    monkeypatch.setattr("backend.cli.uvicorn.run", lambda a, **kw: captured.update(kw))
    runner.invoke(cli, ["start"])
    assert captured.get("host") == "0.0.0.0"
    assert captured.get("port") == 7770
    # ensure correct factory string was passed
    # the lambda above didn't capture the app string, re-run with explicit capture
    captured = {}
    monkeypatch.setattr("backend.cli.uvicorn.run", lambda a, **kw: captured.update({"app_str": a, **kw}))
    runner.invoke(cli, ["start"])
    assert captured.get("app_str") == "backend.main:create_app_app"
    assert captured.get("factory") is True
def test_start_command_custom_host(monkeypatch):
    captured = {}
    monkeypatch.setattr("backend.cli.uvicorn.run", lambda a, **kw: captured.update({"app_str": a, **kw}))
    runner.invoke(cli, ["start", "--host", "192.168.1.10"])
    assert captured.get("host") == "192.168.1.10"
