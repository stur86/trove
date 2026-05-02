"""
Trove CLI entry point.

Provides two commands launched via the `trove` script defined in
[project.scripts] in pyproject.toml:

    trove setup   — setup mode, binds to 127.0.0.1 (local machine only)
    trove start   — app mode, binds to 0.0.0.0 (LAN accessible)

Each command uses the appropriate factory function to create the FastAPI application.
"""
import os
from typing import Optional

import typer
import uvicorn
from dotenv import load_dotenv

# Load .env before any backend imports so env-var-driven constants (e.g.
# TROVE_USE_GLOBAL_OLLAMA, TROVE_OLLAMA_PORT) are resolved from the file.
load_dotenv()

cli = typer.Typer(
    name="trove",
    help="Trove LLM Platform — local AI for non-technical users.",
    no_args_is_help=True,
)


def _set_ollama_host() -> None:
    """
    Point all ollama CLI commands at Trove's private Ollama port.

    Setting OLLAMA_HOST before spawning uvicorn ensures the env var is
    inherited by every subprocess (model pulls, builds, serve) that the
    OllamaService starts during the session.
    """
    from backend.system.service import TROVE_OLLAMA_PORT
    os.environ["OLLAMA_HOST"] = f"127.0.0.1:{TROVE_OLLAMA_PORT}"



@cli.command()
def setup(
    host: str = typer.Option("127.0.0.1", help="Host to bind (default: localhost only)"),
    port: int = typer.Option(7071, help="Port to listen on"),
    frontend_dist: Optional[str] = typer.Option(
        None, "--frontend-dist",
        help="Path to compiled frontend dist directory (overrides auto-detection)",
    ),
) -> None:
    """
    Run Trove in setup mode.

    Setup mode binds to 127.0.0.1 — accessible only from this machine.
    No login required. Use this to install Ollama, pull models, configure
    the admin account, and install Trove as a system service.
    """
    if frontend_dist:
        os.environ["TROVE_FRONTEND_DIST"] = frontend_dist
    _set_ollama_host()
    uvicorn.run("backend.main:create_app_setup", host=host, port=port, factory=True)


@cli.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Host to bind (default: all interfaces)"),
    port: int = typer.Option(7770, help="Port to listen on"),
    frontend_dist: Optional[str] = typer.Option(
        None, "--frontend-dist",
        help="Path to compiled frontend dist directory (overrides auto-detection)",
    ),
) -> None:
    """
    Run Trove in app mode.

    App mode binds to 0.0.0.0 — accessible from the local network.
    Regular users reach the task runner without login; admins access
    /admin with the credentials set during setup.

    Automatically starts Trove's private Ollama instance (port 11435) if
    the ollama binary is installed but the server is not yet running.
    Set TROVE_USE_GLOBAL_OLLAMA=1 in .env to use the system-wide Ollama
    instance (port 11434) instead and share already-pulled models.
    """
    if frontend_dist:
        os.environ["TROVE_FRONTEND_DIST"] = frontend_dist
    _set_ollama_host()
    from backend.ollama.service import ensure_ollama_running
    ensure_ollama_running()
    uvicorn.run("backend.main:create_app_app", host=host, port=port, factory=True)

if __name__ == "__main__":
    # Running the CLI via `python -m backend.cli` is supported
    cli()