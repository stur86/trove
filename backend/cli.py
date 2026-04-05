"""
Trove CLI entry point.

Provides two commands launched via the `trove` script defined in
[project.scripts] in pyproject.toml:

    trove setup   — setup mode, binds to 127.0.0.1 (local machine only)
    trove start   — app mode, binds to 0.0.0.0 (LAN accessible)

Each command uses the appropriate factory function to create the FastAPI application.
"""
import typer
import uvicorn

cli = typer.Typer(
    name="trove",
    help="Trove LLM Platform — local AI for non-technical users.",
    no_args_is_help=True,
)


@cli.command()
def setup(
    host: str = typer.Option("127.0.0.1", help="Host to bind (default: localhost only)"),
    port: int = typer.Option(7071, help="Port to listen on"),
) -> None:
    """
    Run Trove in setup mode.

    Setup mode binds to 127.0.0.1 — accessible only from this machine.
    No login required. Use this to install Ollama, pull models, configure
    the admin account, and install Trove as a system service.
    """
    uvicorn.run("backend.main:create_app_setup", host=host, port=port, factory=True)


@cli.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Host to bind (default: all interfaces)"),
    port: int = typer.Option(7770, help="Port to listen on"),
) -> None:
    """
    Run Trove in app mode.

    App mode binds to 0.0.0.0 — accessible from the local network.
    Regular users reach the task runner without login; admins access
    /admin with the credentials set during setup.
    """
    uvicorn.run("backend.main:create_app_app", host=host, port=port, factory=True)
