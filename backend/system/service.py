"""
System information service.

Defines the SystemService Protocol and two implementations:
- RealSystemService: reads actual hardware via psutil and nvidia-smi
- FakeSystemService: returns configurable values for dev mode and testing

Controlled via environment variables (set in .env):
  TROVE_FAKE_SYSTEM=1          — enable fake mode
  TROVE_FAKE_SYSTEM_RAM_GB     — total RAM to report (default: 8.0)
  TROVE_FAKE_SYSTEM_DISK_GB    — free disk to report (default: 50.0)
  TROVE_FAKE_SYSTEM_GPU        — 1 if GPU present, 0 if not (default: 0)
  TROVE_FAKE_SYSTEM_GPU_VRAM   — VRAM in GB when GPU present (default: 8.0)
  TROVE_FAKE_SYSTEM_OLLAMA_RUNNING — 1 if service active (default: 1)
"""
import os
import shutil
import subprocess
import urllib.request
from functools import lru_cache
from typing import Protocol, runtime_checkable

import psutil

# Port Trove uses for its own private Ollama instance.
# Using a non-default port keeps Trove isolated from any system-level Ollama.
TROVE_OLLAMA_PORT = 11435

# Gemma 4 model catalogue with hardware requirements.
# min_ram_gb is a conservative estimate for CPU-only inference.
# max_ctx is the model's maximum supported context window in tokens.
# audio indicates whether the model supports audio input natively.
MODELS = [
    {"tag": "gemma4:e2b", "min_ram_gb": 4.0,  "max_ctx": 131072, "audio": True},
    {"tag": "gemma4:e4b", "min_ram_gb": 6.0,  "max_ctx": 131072, "audio": True},
    {"tag": "gemma4:26b", "min_ram_gb": 10.0, "max_ctx": 262144, "audio": False},
    {"tag": "gemma4:31b", "min_ram_gb": 20.0, "max_ctx": 262144, "audio": False},
]


# ---------------------------------------------------------------------------
# Protocol (interface)
# ---------------------------------------------------------------------------

@runtime_checkable
class SystemService(Protocol):
    """
    Interface for system hardware checks.

    Implementations: RealSystemService (production), FakeSystemService (dev/test).
    """

    def check(self) -> dict:
        """
        Return a hardware snapshot used by the Setup page.

        Keys: ram_gb, disk_free_gb, gpu, ollama_running, viable_models.
        """
        ...


# ---------------------------------------------------------------------------
# Real implementation
# ---------------------------------------------------------------------------

class RealSystemService:
    """Production system service that reads real hardware via psutil and nvidia-smi."""

    def check(self) -> dict:
        """
        Run all system checks and return a combined status dict.

        Keys:
          ram_gb (float): Total RAM rounded to 1 decimal.
          disk_free_gb (float): Free disk space rounded to 1 decimal.
          gpu (dict): GPU info with 'available' and 'vram_gb'.
          ollama_running (bool): Whether the Ollama systemd service is active.
          viable_models (list[dict]): Models from MODELS that fit in RAM.
        """
        ram_gb = self._get_ram_gb()
        gpu_info = self._get_gpu_info()
        return {
            "ram_gb": round(ram_gb, 1),
            "disk_free_gb": round(self._get_disk_free_gb(), 1),
            "gpu": gpu_info,
            "ollama_running": self._is_ollama_service_running(),
            "viable_models": _get_viable_models(ram_gb, gpu_info),
        }

    def _get_ram_gb(self) -> float:
        """Return total system RAM in gigabytes."""
        return psutil.virtual_memory().total / 1024**3

    def _get_disk_free_gb(self) -> float:
        """Return free disk space on the root filesystem in gigabytes."""
        return psutil.disk_usage("/").free / 1024**3

    def _get_gpu_info(self) -> dict:
        """
        Detect NVIDIA GPU presence and VRAM via nvidia-smi.

        Returns dict with 'available' (bool) and 'vram_gb' (float|None).
        Gracefully returns available=False if nvidia-smi is absent or fails.
        """
        if shutil.which("nvidia-smi") is None:
            return {"available": False, "vram_gb": None}
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {"available": False, "vram_gb": None}
        try:
            # nvidia-smi reports VRAM in MiB; convert to GB
            vram_mb = float(result.stdout.strip().splitlines()[0])
            return {"available": True, "vram_gb": round(vram_mb / 1024, 1)}
        except (ValueError, IndexError):
            return {"available": False, "vram_gb": None}

    def _is_ollama_service_running(self) -> bool:
        """
        Check whether the Ollama systemd service is active.

        Returns False on any error, including systems without systemd.
        """
        return is_ollama_service_running()

# ---------------------------------------------------------------------------
# Fake implementation (dev mode + testing)
# ---------------------------------------------------------------------------

class FakeSystemService:
    """
    Configurable fake system service for development and testing.

    Values are read from environment variables at instantiation time,
    allowing different test scenarios without changing code:

        TROVE_FAKE_SYSTEM_RAM_GB=3.0  # simulate low-RAM machine
        TROVE_FAKE_SYSTEM_OLLAMA_RUNNING=0  # simulate Ollama not started

    Defaults simulate a mid-range machine with no GPU and Ollama running.
    """

    def check(self) -> dict:
        """Return hardware snapshot from environment variable configuration."""
        ram_gb = float(os.environ.get("TROVE_FAKE_SYSTEM_RAM_GB", "8.0"))
        disk_gb = float(os.environ.get("TROVE_FAKE_SYSTEM_DISK_GB", "50.0"))
        gpu_present = os.environ.get("TROVE_FAKE_SYSTEM_GPU", "0") == "1"
        gpu_vram = float(os.environ.get("TROVE_FAKE_SYSTEM_GPU_VRAM", "8.0")) if gpu_present else None
        ollama_running = os.environ.get("TROVE_FAKE_SYSTEM_OLLAMA_RUNNING", "1") == "1"

        gpu_info = {"available": gpu_present, "vram_gb": gpu_vram}
        return {
            "ram_gb": round(ram_gb, 1),
            "disk_free_gb": round(disk_gb, 1),
            "gpu": gpu_info,
            "ollama_running": ollama_running,
            "viable_models": _get_viable_models(ram_gb, gpu_info),
        }


# ---------------------------------------------------------------------------
# Shared utility
# ---------------------------------------------------------------------------

def _get_viable_models(ram_gb: float, gpu_info: dict) -> list[dict]:
    """
    Return the subset of MODELS that can run on a machine with the given RAM.

    gpu_info is accepted for future use (GPU-accelerated inference with lower
    RAM requirements may be supported in a later version).
    """
    # TODO: Consider VRAM as contributing to model viability in future,
    # model can be split between RAM and VRAM for GPU inference. 
    return [m for m in MODELS if ram_gb >= m["min_ram_gb"]]


# ---------------------------------------------------------------------------
# Keep module-level is_ollama_service_running for import by ollama domain
# ---------------------------------------------------------------------------

def is_ollama_service_running() -> bool:
    """
    Check whether Trove's private Ollama instance is accepting requests.

    Does a lightweight HTTP GET to the Ollama root endpoint on TROVE_OLLAMA_PORT
    rather than shelling out — faster and doesn't depend on the PATH.
    Returns False on any error (connection refused, timeout, etc.).
    """
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{TROVE_OLLAMA_PORT}", timeout=2
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Service factory (used by FastAPI Depends)
# ---------------------------------------------------------------------------

@lru_cache
def get_system_service() -> SystemService:
    """
    FastAPI dependency that returns the appropriate SystemService implementation.

    Returns FakeSystemService if TROVE_FAKE_SYSTEM=1, otherwise RealSystemService.
    Configure fake hardware via TROVE_FAKE_SYSTEM_* variables in .env.
    """
    if os.environ.get("TROVE_FAKE_SYSTEM") == "1":
        return FakeSystemService()
    return RealSystemService()
