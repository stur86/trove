"""
System information service.

Checks available hardware resources (RAM, disk, GPU) and determines
which Gemma 4 model variants are viable on this machine.
Also checks whether the Ollama systemd service is running.
"""
import shutil
import subprocess

import psutil

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


def get_ram_gb() -> float:
    """Return total system RAM in gigabytes."""
    return psutil.virtual_memory().total / 1024**3


def get_disk_free_gb() -> float:
    """Return free disk space on the root filesystem in gigabytes."""
    return psutil.disk_usage("/").free / 1024**3


def get_gpu_info() -> dict:
    """
    Detect NVIDIA GPU presence and VRAM via nvidia-smi.

    Returns a dict with:
      available (bool): True if nvidia-smi is present and reports a GPU.
      vram_gb (float | None): Total VRAM in GB, or None if unavailable.

    Gracefully returns available=False if nvidia-smi is absent or fails.
    AMD/ROCm GPUs are not detected in this version.
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


def get_viable_models(ram_gb: float, gpu_info: dict) -> list[dict]:
    """
    Return the subset of MODELS that can run on this machine.

    Currently filters by RAM only. gpu_info is accepted for future use
    (e.g. GPU-accelerated inference with lower RAM requirements).
    """
    # TODO: Consider VRAM as contributing to model viability in future,
    # model can be split between RAM and VRAM for GPU inference. 
    return [m for m in MODELS if ram_gb >= m["min_ram_gb"]]


def is_ollama_service_running() -> bool:
    """
    Check whether the Ollama systemd service is active.

    Uses `systemctl is-active ollama`. Returns False on any error,
    including systems without systemd.
    """
    result = subprocess.run(
        ["systemctl", "is-active", "ollama"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "active"


def check_system() -> dict:
    """
    Run all system checks and return a combined status dict.

    Used by the admin Setup page to display hardware info and guide
    model selection. Keys:
      ram_gb (float): Total RAM rounded to 1 decimal.
      disk_free_gb (float): Free disk space rounded to 1 decimal.
      gpu (dict): GPU info from get_gpu_info().
      ollama_running (bool): Whether the Ollama service is active.
      viable_models (list[dict]): Models from MODELS that fit in RAM.
    """
    ram_gb = get_ram_gb()
    gpu_info = get_gpu_info()
    return {
        "ram_gb": round(ram_gb, 1),
        "disk_free_gb": round(get_disk_free_gb(), 1),
        "gpu": gpu_info,
        "ollama_running": is_ollama_service_running(),
        "viable_models": get_viable_models(ram_gb, gpu_info),
    }
