"""
Service installation management for the setup domain.

Defines the ServiceInstaller Protocol and two implementations:
- RealServiceInstaller: manages the systemd trove.service unit
- FakeServiceInstaller: records calls and simulates operations for dev/testing

Activated by TROVE_FAKE_SERVICE=1 in the environment (.env file).

Also provides get_lan_ip() for detecting the machine's LAN address.
"""
import os
import shutil
import socket
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

# Path where the systemd unit file is installed (requires sudo).
UNIT_FILE_PATH = Path("/etc/systemd/system/trove.service")
SERVICE_NAME = "trove"


def get_lan_ip() -> str:
    """
    Detect the machine's LAN IP address.

    Opens a UDP socket toward a public address to determine which
    local interface would be used — without sending any packets.
    Falls back to 127.0.0.1 if detection fails.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _build_unit_file(app_port: int) -> str:
    """
    Generate the systemd unit file content for the trove service.

    Resolves the trove executable path via shutil.which() so the unit
    works regardless of install location.
    """
    import sys
    trove_bin = shutil.which("trove") or f"{sys.prefix}/bin/trove"
    working_dir = Path(__file__).parent.parent.parent  # repo root
    username = os.environ.get("USER", "trove")
    return (
        "[Unit]\n"
        "Description=Trove LLM Platform\n"
        "After=network.target\n\n"
        "[Service]\n"
        f"ExecStart={trove_bin} start --port {app_port}\n"
        "Restart=on-failure\n"
        f"User={username}\n"
        f"WorkingDirectory={working_dir}\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
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
    Manages the trove systemd service using subprocess calls.

    Requires sudo for writing to /etc/systemd/system/ and running
    systemctl commands that affect system-level services.
    """

    def install(self, app_port: int) -> Iterator[str]:
        """Write unit file via sudo tee and enable the service."""
        unit_content = _build_unit_file(app_port)
        yield "data: Writing systemd unit file...\n\n"

        result = subprocess.run(
            ["sudo", "tee", str(UNIT_FILE_PATH)],
            input=unit_content,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            yield f"data: [ERROR] Failed to write unit file: {result.stderr.strip()}\n\n"
            return

        yield "data: Reloading systemd daemon...\n\n"
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)

        yield "data: Enabling and starting trove service...\n\n"
        subprocess.run(
            ["sudo", "systemctl", "enable", "--now", SERVICE_NAME], check=True
        )
        yield "data: Service installed and started.\n\n"
        yield "data: [DONE]\n\n"

    def uninstall(self) -> Iterator[str]:
        """Stop, disable and remove the service unit file."""
        yield "data: Stopping trove service...\n\n"
        subprocess.run(
            ["sudo", "systemctl", "stop", SERVICE_NAME], capture_output=True
        )
        subprocess.run(
            ["sudo", "systemctl", "disable", SERVICE_NAME], capture_output=True
        )
        yield "data: Removing unit file...\n\n"
        subprocess.run(
            ["sudo", "rm", "-f", str(UNIT_FILE_PATH)], check=True
        )
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        yield "data: Trove uninstalled.\n\n"
        yield "data: [DONE]\n\n"

    def restart(self) -> Iterator[str]:
        """Restart the service."""
        yield "data: Restarting trove service...\n\n"
        result = subprocess.run(
            ["sudo", "systemctl", "restart", SERVICE_NAME],
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
        """Return True if systemctl reports the service as active."""
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
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
