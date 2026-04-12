# Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the Trove monorepo with a working FastAPI backend, Ollama integration (install/pull/build via SSE), configuration persistence, i18n, system checks, and a Bun/React frontend served as static files.

**Architecture:** Feature-grouped FastAPI backend with one domain per folder (ollama, config, system, i18n), each owning its router and service. Frontend is a Bun/React/Vite app built to static files and served by FastAPI in production. Config persists to `~/.config/trove/config.json` (XDG spec). SSE streams progress for long-running Ollama operations.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn[standard], pydantic, psutil, sse-starlette, pytest, httpx, taskipy, uv; TypeScript, React 19, Vite, Bun, react-router-dom

---

## File Map

**Created (backend):**
- `backend/__init__.py`
- `backend/main.py`
- `backend/config/__init__.py`, `models.py`, `service.py`, `router.py`
- `backend/i18n/__init__.py`, `loader.py`, `router.py`, `locales/en.json`
- `backend/system/__init__.py`, `service.py`, `router.py`
- `backend/ollama/__init__.py`, `service.py`, `router.py`
- `tests/__init__.py`, `conftest.py`
- `tests/test_config.py`, `test_i18n.py`, `test_system.py`, `test_ollama_service.py`

**Created (frontend):**
- `frontend/` (Vite scaffold)
- `frontend/src/api/client.ts`, `config.ts`, `system.ts`, `ollama.ts`
- `frontend/src/i18n/index.ts`
- `frontend/src/pages/Setup.tsx`, `Admin.tsx`
- `frontend/src/App.tsx`

**Modified:**
- `pyproject.toml` — dependencies, taskipy tasks, pytest config
- `.gitignore` — frontend dist, Python cache
- `backend/main.py` — grows incrementally across tasks

**Runtime (not in repo):**
- `~/.config/trove/config.json`
- `~/.config/trove/Modelfile`

---

### Task 1: Project scaffold

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `backend/__init__.py`
- Create: `backend/main.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Update pyproject.toml**

Replace the full contents of `pyproject.toml`:

```toml
[project]
name = "trove"
version = "0.1.0"
description = "Local LLM platform for non-technical users"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2.10",
    "psutil>=6.1",
    "sse-starlette>=2.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "httpx>=0.28",
    "taskipy>=1.14",
]

[tool.taskipy.tasks]
dev-backend  = "uvicorn backend.main:app --reload"
dev-frontend = "cd frontend && bun run dev"
build        = "cd frontend && bun run build"
start        = "task build && uvicorn backend.main:app"
install-deps = "uv sync --extra dev && cd frontend && bun install"
test         = "pytest -v"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Update .gitignore**

Add to `.gitignore`:
```
# Python
__pycache__/
*.pyc
.venv/

# Frontend
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 3: Create backend package and skeleton**

Create `backend/__init__.py` (empty file).

Create `backend/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Trove", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Create test infrastructure**

Create `tests/__init__.py` (empty file).

Create `tests/conftest.py`:
```python
import pytest
from pathlib import Path


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect XDG config to a temp directory for all config tests."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "trove"
    config_path.mkdir()
    return config_path
```

- [ ] **Step 5: Install Python dependencies**

```bash
uv sync --extra dev
```

Expected: all packages install without errors.

- [ ] **Step 6: Verify server starts**

```bash
uvicorn backend.main:app --reload
```

In another terminal:
```bash
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok"}`. Stop server with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore backend/__init__.py backend/main.py tests/__init__.py tests/conftest.py
git commit -m "feat: scaffold project with FastAPI skeleton and test infrastructure"
```

---

### Task 2: Config domain

**Files:**
- Create: `backend/config/__init__.py`
- Create: `backend/config/models.py`
- Create: `backend/config/service.py`
- Create: `backend/config/router.py`
- Create: `tests/test_config.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:
```python
import json
import pytest
from pathlib import Path
from backend.config.models import TroveConfig
from backend.config.service import get_config_dir, load_config, save_config


def test_get_config_dir_default(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = get_config_dir()
    assert result == tmp_path / ".config" / "trove"


def test_get_config_dir_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    result = get_config_dir()
    assert result == tmp_path / "trove"


def test_load_config_returns_defaults_when_no_file(config_dir):
    config = load_config()
    assert config.base_model == "gemma4:e4b"
    assert config.num_ctx == 8192
    assert config.locale == "en"


def test_load_config_reads_existing_file(config_dir):
    (config_dir / "config.json").write_text(
        '{"base_model": "gemma4:31b", "num_ctx": 32768, "locale": "fr"}'
    )
    config = load_config()
    assert config.base_model == "gemma4:31b"
    assert config.num_ctx == 32768
    assert config.locale == "fr"


def test_save_config_writes_file(config_dir):
    config = TroveConfig(base_model="gemma4:e2b", num_ctx=4096, locale="es")
    save_config(config)
    data = json.loads((config_dir / "config.json").read_text())
    assert data["base_model"] == "gemma4:e2b"
    assert data["num_ctx"] == 4096
    assert data["locale"] == "es"


def test_save_config_creates_dir_if_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # directory does not exist yet — only tmp_path exists, not tmp_path/trove
    config = TroveConfig(base_model="gemma4:e4b", num_ctx=8192, locale="en")
    save_config(config)
    assert (tmp_path / "trove" / "config.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError` — config module doesn't exist yet.

- [ ] **Step 3: Create config models**

Create `backend/config/__init__.py` (empty file).

Create `backend/config/models.py`:
```python
from pydantic import BaseModel, Field


class TroveConfig(BaseModel):
    base_model: str = "gemma4:e4b"
    num_ctx: int = Field(default=8192, ge=512, le=262144)
    locale: str = "en"
```

- [ ] **Step 4: Create config service**

Create `backend/config/service.py`:
```python
import os
from pathlib import Path

from backend.config.models import TroveConfig


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "trove"


def load_config() -> TroveConfig:
    path = get_config_dir() / "config.json"
    if not path.exists():
        return TroveConfig()
    return TroveConfig.model_validate_json(path.read_text())


def save_config(config: TroveConfig) -> None:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(config.model_dump_json(indent=2))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 6: Create config router**

Create `backend/config/router.py`:
```python
from fastapi import APIRouter

from backend.config.models import TroveConfig
from backend.config.service import load_config, save_config

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config() -> TroveConfig:
    return load_config()


@router.put("")
def update_config(config: TroveConfig) -> TroveConfig:
    save_config(config)
    return config
```

- [ ] **Step 7: Mount router in main.py**

Replace `backend/main.py`:
```python
from fastapi import FastAPI

from backend.config.router import router as config_router

app = FastAPI(title="Trove", version="0.1.0")

app.include_router(config_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 8: Smoke test the endpoint**

```bash
uvicorn backend.main:app --reload
```

```bash
curl http://localhost:8000/api/config
```

Expected: `{"base_model":"gemma4:e4b","num_ctx":8192,"locale":"en"}`

- [ ] **Step 9: Commit**

```bash
git add backend/config/ tests/test_config.py backend/main.py
git commit -m "feat: add config domain with XDG-compliant persistence"
```

---

### Task 3: i18n domain

**Files:**
- Create: `backend/i18n/__init__.py`
- Create: `backend/i18n/loader.py`
- Create: `backend/i18n/router.py`
- Create: `backend/i18n/locales/en.json`
- Create: `tests/test_i18n.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create locale file**

Create `backend/i18n/locales/en.json`:
```json
{
  "setup.title": "Trove Setup",
  "setup.install_button": "Install Ollama",
  "setup.installing": "Installing Ollama...",
  "setup.pull_model": "Download model",
  "setup.pulling": "Downloading model...",
  "setup.system_check": "Checking your system...",
  "setup.ram": "RAM",
  "setup.disk": "Free disk",
  "setup.gpu": "GPU",
  "setup.ollama_status": "Ollama",
  "setup.model_built": "Model ready",
  "setup.not_installed": "Not installed",
  "setup.running": "Running",
  "setup.not_running": "Not running",
  "config.title": "Configuration",
  "config.base_model": "Base model",
  "config.num_ctx": "Context window",
  "config.locale": "Language",
  "config.save": "Save",
  "config.saved": "Saved",
  "model.gemma4_e2b": "Gemma 4 E2B (2.3B — fastest)",
  "model.gemma4_e4b": "Gemma 4 E4B (4.5B — balanced)",
  "model.gemma4_26b": "Gemma 4 26B MoE (efficient large)",
  "model.gemma4_31b": "Gemma 4 31B (most capable)"
}
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_i18n.py`:
```python
from backend.i18n.loader import load_locale, list_locales


def test_load_locale_en_contains_required_keys():
    strings = load_locale("en")
    assert strings["setup.install_button"] == "Install Ollama"
    assert "config.base_model" in strings


def test_load_locale_falls_back_to_en_for_unknown():
    strings = load_locale("nonexistent_locale")
    assert "setup.install_button" in strings


def test_list_locales_includes_en():
    locales = list_locales()
    assert "en" in locales


def test_list_locales_returns_list_of_strings():
    locales = list_locales()
    assert all(isinstance(loc, str) for loc in locales)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_i18n.py -v
```

Expected: `ModuleNotFoundError` — i18n module doesn't exist yet.

- [ ] **Step 4: Create i18n loader**

Create `backend/i18n/__init__.py` (empty file).

Create `backend/i18n/loader.py`:
```python
import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"


def load_locale(locale: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        path = LOCALES_DIR / "en.json"
    return json.loads(path.read_text())


def list_locales() -> list[str]:
    return [p.stem for p in LOCALES_DIR.glob("*.json")]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_i18n.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Create i18n router**

Create `backend/i18n/router.py`:
```python
from fastapi import APIRouter

from backend.i18n.loader import list_locales, load_locale

router = APIRouter(prefix="/api/i18n", tags=["i18n"])


@router.get("/locales")
def get_locales() -> list[str]:
    return list_locales()


@router.get("/{locale}")
def get_locale(locale: str) -> dict[str, str]:
    return load_locale(locale)
```

- [ ] **Step 7: Mount router in main.py**

Replace `backend/main.py`:
```python
from fastapi import FastAPI

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router

app = FastAPI(title="Trove", version="0.1.0")

app.include_router(config_router)
app.include_router(i18n_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 8: Commit**

```bash
git add backend/i18n/ tests/test_i18n.py backend/main.py
git commit -m "feat: add i18n domain with locale file loading and fallback"
```

---

### Task 4: System check domain

**Files:**
- Create: `backend/system/__init__.py`
- Create: `backend/system/service.py`
- Create: `backend/system/router.py`
- Create: `tests/test_system.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_system.py`:
```python
import pytest
from unittest.mock import MagicMock, patch

from backend.system.service import (
    MODELS,
    get_disk_free_gb,
    get_gpu_info,
    get_ram_gb,
    get_viable_models,
)


def test_get_ram_gb_returns_positive_float():
    result = get_ram_gb()
    assert isinstance(result, float)
    assert result > 0


def test_get_disk_free_gb_returns_non_negative_float():
    result = get_disk_free_gb()
    assert isinstance(result, float)
    assert result >= 0


def test_get_gpu_info_no_nvidia():
    with patch("backend.system.service.shutil.which", return_value=None):
        result = get_gpu_info()
    assert result["available"] is False
    assert result["vram_gb"] is None


def test_get_gpu_info_nvidia_present():
    mock_result = MagicMock(returncode=0, stdout="8192\n")
    with patch("backend.system.service.shutil.which", return_value="/usr/bin/nvidia-smi"):
        with patch("backend.system.service.subprocess.run", return_value=mock_result):
            result = get_gpu_info()
    assert result["available"] is True
    assert result["vram_gb"] == pytest.approx(8.0, abs=0.1)


def test_get_viable_models_3gb_ram():
    result = get_viable_models(ram_gb=3.0, gpu_info={"available": False, "vram_gb": None})
    assert result == []


def test_get_viable_models_6gb_ram():
    result = get_viable_models(ram_gb=6.0, gpu_info={"available": False, "vram_gb": None})
    tags = [m["tag"] for m in result]
    assert "gemma4:e2b" in tags
    assert "gemma4:e4b" in tags
    assert "gemma4:31b" not in tags


def test_get_viable_models_24gb_ram():
    result = get_viable_models(ram_gb=24.0, gpu_info={"available": False, "vram_gb": None})
    tags = [m["tag"] for m in result]
    assert "gemma4:e2b" in tags
    assert "gemma4:31b" in tags


def test_models_constant_has_required_fields():
    for model in MODELS:
        assert "tag" in model
        assert "min_ram_gb" in model
        assert "max_ctx" in model
        assert "audio" in model
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_system.py -v
```

Expected: `ModuleNotFoundError` — system module doesn't exist yet.

- [ ] **Step 3: Create system service**

Create `backend/system/__init__.py` (empty file).

Create `backend/system/service.py`:
```python
import shutil
import subprocess

import psutil

MODELS = [
    {"tag": "gemma4:e2b", "min_ram_gb": 4.0,  "max_ctx": 131072, "audio": True},
    {"tag": "gemma4:e4b", "min_ram_gb": 6.0,  "max_ctx": 131072, "audio": True},
    {"tag": "gemma4:26b", "min_ram_gb": 10.0, "max_ctx": 262144, "audio": False},
    {"tag": "gemma4:31b", "min_ram_gb": 20.0, "max_ctx": 262144, "audio": False},
]


def get_ram_gb() -> float:
    return psutil.virtual_memory().total / 1024**3


def get_disk_free_gb() -> float:
    return psutil.disk_usage("/").free / 1024**3


def get_gpu_info() -> dict:
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
        vram_mb = float(result.stdout.strip().splitlines()[0])
        return {"available": True, "vram_gb": round(vram_mb / 1024, 1)}
    except (ValueError, IndexError):
        return {"available": False, "vram_gb": None}


def get_viable_models(ram_gb: float, gpu_info: dict) -> list[dict]:
    return [m for m in MODELS if ram_gb >= m["min_ram_gb"]]


def is_ollama_service_running() -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", "ollama"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "active"


def check_system() -> dict:
    ram_gb = get_ram_gb()
    gpu_info = get_gpu_info()
    return {
        "ram_gb": round(ram_gb, 1),
        "disk_free_gb": round(get_disk_free_gb(), 1),
        "gpu": gpu_info,
        "ollama_running": is_ollama_service_running(),
        "viable_models": get_viable_models(ram_gb, gpu_info),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_system.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Create system router**

Create `backend/system/router.py`:
```python
from fastapi import APIRouter

from backend.system.service import check_system

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/check")
def system_check() -> dict:
    return check_system()
```

- [ ] **Step 6: Mount router in main.py**

Replace `backend/main.py`:
```python
from fastapi import FastAPI

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router
from backend.system.router import router as system_router

app = FastAPI(title="Trove", version="0.1.0")

app.include_router(config_router)
app.include_router(i18n_router)
app.include_router(system_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 7: Commit**

```bash
git add backend/system/ tests/test_system.py backend/main.py
git commit -m "feat: add system check domain with RAM/disk/GPU detection"
```

---

### Task 5: Ollama domain

**Files:**
- Create: `backend/ollama/__init__.py`
- Create: `backend/ollama/service.py`
- Create: `backend/ollama/router.py`
- Create: `tests/test_ollama_service.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ollama_service.py`:
```python
import pytest
from unittest.mock import MagicMock, patch

from backend.config.models import TroveConfig
from backend.ollama.service import (
    generate_modelfile,
    get_ollama_status,
    is_ollama_installed,
    is_trove_model_built,
)


def test_is_ollama_installed_true():
    with patch("backend.ollama.service.shutil.which", return_value="/usr/bin/ollama"):
        assert is_ollama_installed() is True


def test_is_ollama_installed_false():
    with patch("backend.ollama.service.shutil.which", return_value=None):
        assert is_ollama_installed() is False


def test_is_trove_model_built_true():
    mock_result = MagicMock(returncode=0, stdout="NAME\ntrove_model:latest\n")
    with patch("backend.ollama.service.subprocess.run", return_value=mock_result):
        assert is_trove_model_built() is True


def test_is_trove_model_built_false():
    mock_result = MagicMock(returncode=0, stdout="NAME\nother_model:latest\n")
    with patch("backend.ollama.service.subprocess.run", return_value=mock_result):
        assert is_trove_model_built() is False


def test_generate_modelfile_contents(config_dir):
    config = TroveConfig(base_model="gemma4:e4b", num_ctx=8192, locale="en")
    path = generate_modelfile(config)
    assert path.read_text() == "FROM gemma4:e4b\nPARAMETER num_ctx 8192\n"


def test_generate_modelfile_path(config_dir):
    config = TroveConfig(base_model="gemma4:e4b", num_ctx=8192, locale="en")
    path = generate_modelfile(config)
    assert path.name == "Modelfile"


def test_get_ollama_status_not_installed():
    with patch("backend.ollama.service.shutil.which", return_value=None):
        status = get_ollama_status()
    assert status["installed"] is False
    assert status["running"] is False
    assert status["model_built"] is False


def test_get_ollama_status_installed_and_running():
    mock_list = MagicMock(returncode=0, stdout="NAME\ntrove_model:latest\n")
    with patch("backend.ollama.service.shutil.which", return_value="/usr/bin/ollama"):
        with patch("backend.ollama.service.subprocess.run", return_value=mock_list):
            with patch("backend.ollama.service.is_ollama_service_running", return_value=True):
                status = get_ollama_status()
    assert status["installed"] is True
    assert status["running"] is True
    assert status["model_built"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ollama_service.py -v
```

Expected: `ModuleNotFoundError` — ollama module doesn't exist yet.

- [ ] **Step 3: Create ollama service**

Create `backend/ollama/__init__.py` (empty file).

Create `backend/ollama/service.py`:
```python
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

from backend.config.models import TroveConfig
from backend.config.service import get_config_dir, load_config
from backend.system.service import is_ollama_service_running


def is_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def is_trove_model_built() -> bool:
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    return "trove_model" in result.stdout


def generate_modelfile(config: TroveConfig) -> Path:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "Modelfile"
    path.write_text(f"FROM {config.base_model}\nPARAMETER num_ctx {config.num_ctx}\n")
    return path


def get_ollama_status() -> dict:
    installed = is_ollama_installed()
    running = is_ollama_service_running() if installed else False
    model_built = is_trove_model_built() if installed else False
    return {"installed": installed, "running": running, "model_built": model_built}


def stream_install() -> Iterator[str]:
    yield "data: Starting Ollama installation...\n\n"
    process = subprocess.Popen(
        ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in process.stdout:
        yield f"data: {line.rstrip()}\n\n"
    process.wait()
    if process.returncode == 0:
        yield "data: [DONE] Ollama installed successfully.\n\n"
    else:
        yield f"data: [ERROR] Installation failed (exit {process.returncode}).\n\n"


def stream_pull(model_tag: str) -> Iterator[str]:
    yield f"data: Pulling {model_tag}...\n\n"
    process = subprocess.Popen(
        ["ollama", "pull", model_tag],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in process.stdout:
        yield f"data: {line.rstrip()}\n\n"
    process.wait()
    if process.returncode == 0:
        yield "data: [DONE] Model pulled successfully.\n\n"
    else:
        yield f"data: [ERROR] Pull failed (exit {process.returncode}).\n\n"


def build_trove_model() -> Iterator[str]:
    config = load_config()
    modelfile_path = generate_modelfile(config)
    yield f"data: Building trove_model from {config.base_model}...\n\n"
    process = subprocess.Popen(
        ["ollama", "create", "trove_model", "-f", str(modelfile_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in process.stdout:
        yield f"data: {line.rstrip()}\n\n"
    process.wait()
    if process.returncode == 0:
        yield "data: [DONE] trove_model built successfully.\n\n"
    else:
        yield f"data: [ERROR] Build failed (exit {process.returncode}).\n\n"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ollama_service.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Create ollama router with SSE**

Create `backend/ollama/router.py`:
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.config.service import load_config
from backend.ollama.service import (
    build_trove_model,
    get_ollama_status,
    stream_install,
    stream_pull,
)

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/status")
def ollama_status() -> dict:
    return get_ollama_status()


@router.post("/install")
def install_ollama() -> StreamingResponse:
    return StreamingResponse(stream_install(), media_type="text/event-stream")


@router.post("/pull")
def pull_model() -> StreamingResponse:
    config = load_config()
    return StreamingResponse(stream_pull(config.base_model), media_type="text/event-stream")


@router.post("/build")
def build_model() -> StreamingResponse:
    return StreamingResponse(build_trove_model(), media_type="text/event-stream")
```

- [ ] **Step 6: Mount router and add CORS in main.py**

Replace `backend/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router
from backend.ollama.router import router as ollama_router
from backend.system.router import router as system_router

app = FastAPI(title="Trove", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(i18n_router)
app.include_router(system_router)
app.include_router(ollama_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 7: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/ollama/ tests/test_ollama_service.py backend/main.py
git commit -m "feat: add Ollama domain with install/pull/build SSE streaming"
```

---

### Task 6: Frontend scaffold

**Files:**
- Create: `frontend/` (Vite scaffold)
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/pages/Setup.tsx`
- Create: `frontend/src/pages/Admin.tsx`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Scaffold Vite React TypeScript project**

```bash
cd frontend && bun create vite . --template react-ts
```

If prompted about non-empty directory, select "Ignore files and continue".

- [ ] **Step 2: Install frontend dependencies**

```bash
cd frontend && bun install && bun add react-router-dom
```

- [ ] **Step 3: Configure Vite proxy**

Replace `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

- [ ] **Step 4: Create App.tsx with routing**

Replace `frontend/src/App.tsx`:
```typescript
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Admin from './pages/Admin'
import Setup from './pages/Setup'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/setup" element={<Setup />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 5: Create placeholder pages**

Create `frontend/src/pages/Setup.tsx`:
```typescript
export default function Setup() {
  return <div>Setup page</div>
}
```

Create `frontend/src/pages/Admin.tsx`:
```typescript
export default function Admin() {
  return <div>Admin page</div>
}
```

- [ ] **Step 6: Update main.tsx**

Replace `frontend/src/main.tsx`:
```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 7: Verify dev server starts**

```bash
cd frontend && bun run dev
```

Expected: Vite starts at `http://localhost:5173`. Browser shows "Setup page" at `/setup`. Stop with Ctrl+C.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Bun/React/Vite frontend with routing"
```

---

### Task 7: Frontend API layer and i18n hook

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/config.ts`
- Create: `frontend/src/api/system.ts`
- Create: `frontend/src/api/ollama.ts`
- Create: `frontend/src/i18n/index.ts`

- [ ] **Step 1: Create base API client**

Create `frontend/src/api/client.ts`:
```typescript
const BASE = '/api'

export async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

export async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  return res.json()
}

export async function post(path: string): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res
}
```

- [ ] **Step 2: Create config API module**

Create `frontend/src/api/config.ts`:
```typescript
import { get, put } from './client'

export interface TroveConfig {
  base_model: string
  num_ctx: number
  locale: string
}

export const configApi = {
  get: () => get<TroveConfig>('/config'),
  update: (config: TroveConfig) => put<TroveConfig>('/config', config),
}
```

- [ ] **Step 3: Create system API module**

Create `frontend/src/api/system.ts`:
```typescript
import { get } from './client'

export interface GpuInfo {
  available: boolean
  vram_gb: number | null
}

export interface ModelInfo {
  tag: string
  min_ram_gb: number
  max_ctx: number
  audio: boolean
}

export interface SystemCheck {
  ram_gb: number
  disk_free_gb: number
  gpu: GpuInfo
  ollama_running: boolean
  viable_models: ModelInfo[]
}

export const systemApi = {
  check: () => get<SystemCheck>('/system/check'),
}
```

- [ ] **Step 4: Create ollama API module**

Create `frontend/src/api/ollama.ts`:
```typescript
import { get, post } from './client'

export interface OllamaStatus {
  installed: boolean
  running: boolean
  model_built: boolean
}

export function streamLines(
  response: Response,
  onLine: (line: string) => void,
  onDone: () => void,
): void {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  function read() {
    reader.read().then(({ done, value }) => {
      if (done) { onDone(); return }
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() ?? ''
      for (const chunk of chunks) {
        const line = chunk.replace(/^data: /, '').trim()
        if (line) onLine(line)
      }
      read()
    })
  }
  read()
}

export const ollamaApi = {
  status: () => get<OllamaStatus>('/ollama/status'),
  install: () => post('/ollama/install'),
  pull: () => post('/ollama/pull'),
  build: () => post('/ollama/build'),
}
```

- [ ] **Step 5: Create i18n hook**

Create `frontend/src/i18n/index.ts`:
```typescript
import { useEffect, useState } from 'react'
import { get } from '../api/client'

type Strings = Record<string, string>

const cache: Record<string, Strings> = {}

async function fetchLocale(locale: string): Promise<Strings> {
  if (cache[locale]) return cache[locale]
  const strings = await get<Strings>(`/i18n/${locale}`)
  cache[locale] = strings
  return strings
}

export function useTranslation(locale: string = 'en') {
  const [strings, setStrings] = useState<Strings>(cache[locale] ?? {})

  useEffect(() => {
    fetchLocale(locale).then(setStrings)
  }, [locale])

  function t(key: string, fallback?: string): string {
    return strings[key] ?? fallback ?? key
  }

  return { t, ready: Object.keys(strings).length > 0 }
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/ frontend/src/i18n/
git commit -m "feat: add frontend API layer and i18n hook"
```

---

### Task 8: Setup page

**Files:**
- Modify: `frontend/src/pages/Setup.tsx`

- [ ] **Step 1: Implement Setup page**

Replace `frontend/src/pages/Setup.tsx`:
```typescript
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OllamaStatus, ollamaApi, streamLines } from '../api/ollama'
import { SystemCheck, systemApi } from '../api/system'
import { configApi } from '../api/config'
import { useTranslation } from '../i18n'

type Phase = 'checking' | 'ready' | 'installing' | 'pulling' | 'building' | 'done'

export default function Setup() {
  const navigate = useNavigate()
  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)
  const [status, setStatus] = useState<OllamaStatus | null>(null)
  const [system, setSystem] = useState<SystemCheck | null>(null)
  const [phase, setPhase] = useState<Phase>('checking')
  const [log, setLog] = useState<string[]>([])

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    Promise.all([ollamaApi.status(), systemApi.check()]).then(([s, sys]) => {
      setStatus(s)
      setSystem(sys)
      if (s.installed && s.running && s.model_built) {
        navigate('/admin')
      } else {
        setPhase('ready')
      }
    })
  }, [])

  function appendLog(line: string) {
    if (line.startsWith('[ERROR]')) {
      setLog(prev => [...prev, `ERROR: ${line.replace('[ERROR] ', '')}`])
    } else if (!line.startsWith('[DONE]')) {
      setLog(prev => [...prev, line])
    }
  }

  async function runSetup() {
    setLog([])

    if (!status?.installed) {
      setPhase('installing')
      const res = await ollamaApi.install()
      await new Promise<void>(resolve => streamLines(res, appendLog, resolve))
    }

    setPhase('pulling')
    const pullRes = await ollamaApi.pull()
    await new Promise<void>(resolve => streamLines(pullRes, appendLog, resolve))

    setPhase('building')
    const buildRes = await ollamaApi.build()
    await new Promise<void>(resolve => streamLines(buildRes, appendLog, resolve))

    setPhase('done')
    setTimeout(() => navigate('/admin'), 1500)
  }

  const buttonLabel =
    phase === 'ready' ? t('setup.install_button') :
    phase === 'installing' ? t('setup.installing') :
    phase === 'pulling' ? t('setup.pulling') :
    phase === 'building' ? 'Building model...' :
    'Done'

  if (phase === 'checking') {
    return <div style={{ padding: '2rem' }}>{t('setup.system_check')}</div>
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '640px', margin: '0 auto' }}>
      <h1>{t('setup.title')}</h1>

      {system && (
        <table style={{ marginBottom: '1.5rem', borderCollapse: 'collapse', width: '100%' }}>
          <tbody>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.ram')}</td>
              <td>{system.ram_gb} GB</td>
            </tr>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.disk')}</td>
              <td>{system.disk_free_gb} GB free</td>
            </tr>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.gpu')}</td>
              <td>{system.gpu.available ? `${system.gpu.vram_gb} GB VRAM` : 'None'}</td>
            </tr>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.ollama_status')}</td>
              <td>
                {status?.installed
                  ? status.running ? t('setup.running') : t('setup.not_running')
                  : t('setup.not_installed')}
              </td>
            </tr>
            <tr>
              <td style={{ padding: '4px 8px', fontWeight: 'bold' }}>{t('setup.model_built')}</td>
              <td>{status?.model_built ? '✓' : '✗'}</td>
            </tr>
          </tbody>
        </table>
      )}

      {phase === 'done' ? (
        <p>Setup complete. Redirecting...</p>
      ) : (
        <button
          onClick={runSetup}
          disabled={phase !== 'ready'}
          style={{ padding: '0.75rem 2rem', fontSize: '1.1rem', cursor: 'pointer' }}
        >
          {buttonLabel}
        </button>
      )}

      {log.length > 0 && (
        <pre style={{
          marginTop: '1rem',
          background: '#111',
          color: '#cfc',
          padding: '1rem',
          borderRadius: '4px',
          maxHeight: '300px',
          overflowY: 'auto',
          fontSize: '0.8rem',
        }}>
          {log.join('\n')}
        </pre>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Smoke test with both servers running**

```bash
# Terminal 1
uvicorn backend.main:app --reload

# Terminal 2
cd frontend && bun run dev
```

Open `http://localhost:5173/setup`. Expected:
- System check table populates with real values
- "Install Ollama" button is visible if Ollama is not installed
- If already fully set up, redirects to `/admin`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Setup.tsx
git commit -m "feat: implement Setup page with system check and Ollama install flow"
```

---

### Task 9: Admin page

**Files:**
- Modify: `frontend/src/pages/Admin.tsx`

- [ ] **Step 1: Implement Admin page**

Replace `frontend/src/pages/Admin.tsx`:
```typescript
import { useEffect, useState } from 'react'
import { TroveConfig, configApi } from '../api/config'
import { ModelInfo, systemApi } from '../api/system'
import { useTranslation } from '../i18n'

const MODEL_LABELS: Record<string, string> = {
  'gemma4:e2b': 'Gemma 4 E2B — 2.3B effective (fastest, audio)',
  'gemma4:e4b': 'Gemma 4 E4B — 4.5B effective (balanced, audio)',
  'gemma4:26b': 'Gemma 4 26B MoE — 4B activated (efficient large)',
  'gemma4:31b': 'Gemma 4 31B — dense (most capable)',
}

export default function Admin() {
  const [config, setConfig] = useState<TroveConfig | null>(null)
  const [viableModels, setViableModels] = useState<ModelInfo[]>([])
  const [saved, setSaved] = useState(false)
  const { t } = useTranslation(config?.locale ?? 'en')

  useEffect(() => {
    Promise.all([configApi.get(), systemApi.check()]).then(([c, sys]) => {
      setConfig(c)
      setViableModels(sys.viable_models)
    })
  }, [])

  async function handleSave() {
    if (!config) return
    await configApi.update(config)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (!config) return <div style={{ padding: '2rem' }}>Loading...</div>

  const selectedModel = viableModels.find(m => m.tag === config.base_model)
  const maxCtx = selectedModel?.max_ctx ?? 131072

  return (
    <div style={{ padding: '2rem', maxWidth: '480px', margin: '0 auto' }}>
      <h1>{t('config.title')}</h1>

      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.4rem' }}>
          {t('config.base_model')}
        </label>
        <select
          value={config.base_model}
          onChange={e => setConfig({
            ...config,
            base_model: e.target.value,
            num_ctx: Math.min(config.num_ctx, maxCtx),
          })}
          style={{ width: '100%', padding: '0.5rem' }}
        >
          {viableModels.length > 0
            ? viableModels.map(m => (
                <option key={m.tag} value={m.tag}>
                  {MODEL_LABELS[m.tag] ?? m.tag}
                </option>
              ))
            : <option value={config.base_model}>{MODEL_LABELS[config.base_model] ?? config.base_model}</option>
          }
        </select>
      </div>

      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.4rem' }}>
          {t('config.num_ctx')}: {config.num_ctx.toLocaleString()}
        </label>
        <input
          type="range"
          min={512}
          max={maxCtx}
          step={512}
          value={config.num_ctx}
          onChange={e => setConfig({ ...config, num_ctx: parseInt(e.target.value) })}
          style={{ width: '100%' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#888' }}>
          <span>512</span>
          <span>{Math.round(maxCtx / 1000)}K</span>
        </div>
      </div>

      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.4rem' }}>
          {t('config.locale')}
        </label>
        <select
          value={config.locale}
          onChange={e => setConfig({ ...config, locale: e.target.value })}
          style={{ width: '100%', padding: '0.5rem' }}
        >
          <option value="en">English</option>
        </select>
      </div>

      <button
        onClick={handleSave}
        style={{ padding: '0.75rem 2rem', fontSize: '1rem', cursor: 'pointer' }}
      >
        {saved ? t('config.saved') : t('config.save')}
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Smoke test Admin page**

With both servers running, open `http://localhost:5173/admin`. Expected:
- Config loads with current values
- Model dropdown shows only models viable for the system's RAM
- Context window slider is bounded by the selected model's max context
- Saving persists config to `~/.config/trove/config.json`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Admin.tsx
git commit -m "feat: implement Admin config page with model picker and context window slider"
```

---

### Task 10: Production build and frontend serving

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Mount static files in FastAPI**

Replace `backend/main.py`:
```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router
from backend.ollama.router import router as ollama_router
from backend.system.router import router as system_router

app = FastAPI(title="Trove", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server only
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(i18n_router)
app.include_router(system_router)
app.include_router(ollama_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
```

- [ ] **Step 2: Run production build**

```bash
task build
```

Expected: `frontend/dist/` is created with `index.html` and assets.

- [ ] **Step 3: Verify production mode**

```bash
task start
```

Expected:
- FastAPI starts on port 8000
- `http://localhost:8000/setup` shows the Setup page (served as static file)
- `http://localhost:8000/api/health` returns `{"status":"ok"}`

- [ ] **Step 4: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat: serve frontend static files from FastAPI in production"
```

---

## Self-Review

**Spec coverage:**
- ✅ Feature-grouped backend: `ollama/`, `config/`, `system/`, `i18n/`
- ✅ XDG-compliant config at `~/.config/trove/config.json`
- ✅ Modelfile at `~/.config/trove/Modelfile`
- ✅ `GET /api/ollama/status`, `POST /api/ollama/install`, `POST /api/ollama/pull`, `POST /api/ollama/build`
- ✅ SSE streaming for install/pull/build via `StreamingResponse`
- ✅ `GET /api/system/check` with ram_gb, disk_free_gb, gpu, ollama_running, viable_models
- ✅ RAM-based model viability (only viable models shown in dropdown)
- ✅ `GET /api/config`, `PUT /api/config`
- ✅ `GET /api/i18n/{locale}`, `GET /api/i18n/locales`, fallback to `en`
- ✅ Locale files as JSON in `backend/i18n/locales/`
- ✅ Bun/React/Vite frontend with react-router-dom
- ✅ Setup page: system check table, install button, SSE progress log
- ✅ Admin page: model picker (RAM-aware), num_ctx slider (capped by model max), locale selector
- ✅ Frontend served from FastAPI in production via StaticFiles
- ✅ taskipy tasks: dev-backend, dev-frontend, build, start, install-deps, test
- ✅ uv for Python deps, bun for frontend deps
- ✅ Gemma 4 models (e2b, e4b, 26b, 31b) with correct RAM thresholds, context windows, audio flags
- ✅ TDD: failing test → implementation → passing test for all backend domains

**No placeholders found.**

**Type consistency:**
- `TroveConfig` defined in `backend/config/models.py`, used identically in service, router, and frontend `api/config.ts`
- `is_ollama_service_running` defined in `backend/system/service.py`, imported in `backend/ollama/service.py` ✅
- `get_config_dir` defined in `backend/config/service.py`, imported in `backend/ollama/service.py` ✅
- `ModelInfo.tag` used in `Admin.tsx` `viableModels.find(m => m.tag === ...)` matches `system.ts` interface ✅
- `streamLines(response, onLine, onDone)` defined in `ollama.ts`, called with same signature in `Setup.tsx` ✅
