"""
Service installation management for the setup domain.

Defines the ServiceInstaller Protocol and two implementations:
- RealServiceInstaller: manages a per-user systemd service (no sudo required)
- FakeServiceInstaller: records calls and simulates operations for dev/testing

Uses systemd user services (~/.config/systemd/user/trove.service) so that no
root privileges are needed. The service runs under the current user account,
which is appropriate for a single-user LAN appliance.

Activated by TROVE_FAKE_SERVICE=1 in the environment (.env file).
"""
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from backend.paths import get_config_dir, get_install_dir

# User-level systemd unit file path — no sudo required.
UNIT_FILE_PATH = Path.home() / ".config" / "systemd" / "user" / "trove.service"
SERVICE_NAME = "trove"


def _build_unit_file(app_port: int) -> str:
    """
    Generate the systemd user unit file content for the trove service.

    Uses the user session unit target so no root privileges are required.
    Resolves the trove executable path via shutil.which() so the unit works
    regardless of install location (venv, pipx, uv tool, etc.).
    """
    import sys
    trove_bin = shutil.which("trove") or f"{sys.prefix}/bin/trove"
    install_dir = get_install_dir()
    env_lines = f"Environment=TROVE_INSTALL_DIR={install_dir}\n"
    if os.getenv("TROVE_USE_GLOBAL_OLLAMA") == "1":
        env_lines += "Environment=TROVE_USE_GLOBAL_OLLAMA=1\n"
    return (
        "[Unit]\n"
        "Description=Trove LLM Platform\n"
        "After=network.target\n\n"
        "[Service]\n"
        f"{env_lines}"
        f"ExecStart={trove_bin} start --port {app_port}\n"
        "Restart=on-failure\n"
        f"WorkingDirectory={get_config_dir()}\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ServiceInstaller(Protocol):
    """Interface for systemd service management operations."""

    def install(self, app_port: int) -> Iterator[str]:
        """Install and start the systemd service, yielding SSE progress lines."""
        ...

    def uninstall(self) -> Iterator[str]:
        """Stop, disable, and remove the service, yielding SSE progress lines."""
        ...

    def restart(self) -> Iterator[str]:
        """Restart the service, yielding SSE progress lines."""
        ...

    def is_installed(self) -> bool:
        """Return True if the systemd unit file exists on disk."""
        ...

    def is_running(self) -> bool:
        """Return True if the service is currently active (running)."""
        ...


# ---------------------------------------------------------------------------
# Real implementation
# ---------------------------------------------------------------------------

class RealServiceInstaller:
    """
    Manages a per-user systemd service — no sudo required.

    Writes the unit file directly to ~/.config/systemd/user/trove.service
    and manages it with `systemctl --user`. The service runs under the current
    user account, so it starts only when the user is logged in.

    To have the service survive logout (e.g. on a headless server), the admin
    can run `loginctl enable-linger <username>` once manually — this is not
    done automatically as it requires root.
    """

    def install(self, app_port: int) -> Iterator[str]:
        """Write unit file directly and enable the user service."""
        unit_content = _build_unit_file(app_port)
        yield "data: Writing systemd unit file...\n\n"

        try:
            UNIT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            UNIT_FILE_PATH.write_text(unit_content)
        except OSError as exc:
            yield f"data: [ERROR] Failed to write unit file: {exc}\n\n"
            return

        yield "data: Reloading systemd daemon...\n\n"
        result = subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            yield f"data: [ERROR] daemon-reload failed: {result.stderr.strip()}\n\n"
            return

        yield "data: Enabling and starting trove service...\n\n"
        result = subprocess.run(
            ["systemctl", "--user", "enable", "--now", SERVICE_NAME],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            yield f"data: [ERROR] Failed to enable service: {result.stderr.strip()}\n\n"
            return

        yield "data: Service installed and started.\n\n"
        yield "data: [DONE]\n\n"

    def uninstall(self) -> Iterator[str]:
        """Stop, disable and remove the user service unit file."""
        yield "data: Stopping trove service...\n\n"
        subprocess.run(
            ["systemctl", "--user", "stop", SERVICE_NAME], capture_output=True
        )
        subprocess.run(
            ["systemctl", "--user", "disable", SERVICE_NAME], capture_output=True
        )
        yield "data: Removing unit file...\n\n"
        UNIT_FILE_PATH.unlink(missing_ok=True)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"], capture_output=True
        )
        yield "data: Trove uninstalled.\n\n"
        yield "data: [DONE]\n\n"

    def restart(self) -> Iterator[str]:
        """Restart the user service."""
        yield "data: Restarting trove service...\n\n"
        result = subprocess.run(
            ["systemctl", "--user", "restart", SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            yield f"data: [ERROR] {result.stderr.strip()}\n\n"
        else:
            yield "data: Service restarted.\n\n"
            yield "data: [DONE]\n\n"

    def is_installed(self) -> bool:
        """Return True if the unit file exists at the expected path."""
        return UNIT_FILE_PATH.exists()

    def is_running(self) -> bool:
        """Return True if systemctl reports the user service as active."""
        result = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "active"


# ---------------------------------------------------------------------------
# Fake implementation (dev / testing)
# ---------------------------------------------------------------------------

class FakeServiceInstaller:
    """
    Simulates service installation without touching the real system.

    Records all method calls in `self.calls` for test assertions.
    Tracks internal installed/running state for is_installed()/is_running().
    Activated by TROVE_FAKE_SERVICE=1.
    """

    def __init__(self) -> None:
        """Initialise with empty call log and not-installed state."""
        self.calls: list[str] = []
        self._installed: bool = False
        self._running: bool = False

    def install(self, app_port: int) -> Iterator[str]:
        """Simulate install: record call, update state, yield fake progress."""
        self.calls.append("install")
        yield "data: [FAKE] Writing unit file...\n\n"
        yield "data: [FAKE] Enabling service...\n\n"
        self._installed = True
        self._running = True
        yield "data: [DONE]\n\n"

    def uninstall(self) -> Iterator[str]:
        """Simulate uninstall: record call, update state."""
        self.calls.append("uninstall")
        yield "data: [FAKE] Removing unit file...\n\n"
        self._installed = False
        self._running = False
        yield "data: [DONE]\n\n"

    def restart(self) -> Iterator[str]:
        """Simulate restart: record call."""
        self.calls.append("restart")
        yield "data: [FAKE] Restarting...\n\n"
        yield "data: [DONE]\n\n"

    def is_installed(self) -> bool:
        """Return simulated installation state."""
        return self._installed

    def is_running(self) -> bool:
        """Return simulated running state."""
        return self._running


# ---------------------------------------------------------------------------
# Dependency factory
# ---------------------------------------------------------------------------

def get_service_installer() -> ServiceInstaller:
    """
    FastAPI dependency factory.

    Returns FakeServiceInstaller when TROVE_FAKE_SERVICE=1 (dev/testing),
    RealServiceInstaller otherwise.
    """
    if os.getenv("TROVE_FAKE_SERVICE") == "1":
        return FakeServiceInstaller()
    return RealServiceInstaller()
