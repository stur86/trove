# Setup/App Mode Split + Flowbite UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split Trove into a setup mode (127.0.0.1, wizard + management dashboard) and app mode (0.0.0.0, task shell + auth-gated admin panel), with a Typer CLI entry point and Flowbite/Tailwind frontend.

**Architecture:** A `create_app(mode)` factory in `backend/main.py` mounts different routers based on `TROVE_MODE`. A Typer CLI sets the mode and starts uvicorn. The frontend fetches `GET /api/mode` on load and renders the appropriate page tree. Two new backend domains: `backend/setup/` (setup-mode-only) and `backend/app/` (app-mode-only, admin routes behind HTTP Basic auth).

**Tech Stack:** FastAPI, Typer, uvicorn (programmatic), flowbite-react, Tailwind CSS v3, PostCSS, React Router v7, SSE streaming

---

## File Map

**Create:**
- `backend/cli.py` — Typer app: `trove setup` and `trove start` commands
- `backend/setup/__init__.py`
- `backend/setup/models.py` — Pydantic request/response types for setup endpoints
- `backend/setup/service.py` — `ServiceInstaller` Protocol + `RealServiceInstaller` + `FakeServiceInstaller`
- `backend/setup/router.py` — all `/api/setup/*` endpoints
- `backend/app/__init__.py`
- `backend/app/router.py` — `/api/app/*` endpoints + `require_admin` dependency
- `backend/i18n/locales/it.json` — Italian translations
- `frontend/tailwind.config.cjs` — Tailwind v3 config with Flowbite plugin
- `frontend/postcss.config.cjs` — PostCSS config (Tailwind + autoprefixer)
- `frontend/src/api/setup.ts` — typed API client for setup endpoints
- `frontend/src/api/app.ts` — typed API client for app/admin endpoints
- `frontend/src/pages/SetupWizard.tsx` — replaces Setup.tsx
- `frontend/src/pages/ManageDashboard.tsx` — management dashboard (return visits)
- `frontend/src/pages/TaskShell.tsx` — regular user landing page
- `tests/test_setup.py`
- `tests/test_app_router.py`
- `tests/test_cli.py`

**Modify:**
- `backend/config/models.py` — add `admin_username`, `admin_password` fields
- `backend/config/router.py` — remove `PUT /api/config` (moved to app router)
- `backend/main.py` — refactor to `create_app(mode)` factory, add `/api/mode` endpoint
- `backend/i18n/locales/en.json` — add new keys for setup/manage/admin/app flows
- `pyproject.toml` — add `typer`, `[project.scripts]`, update taskipy tasks
- `frontend/package.json` — add flowbite-react, tailwindcss@3, postcss, autoprefixer
- `frontend/src/index.css` — replace custom CSS with Tailwind directives
- `frontend/src/App.tsx` — mode-based routing
- `frontend/src/pages/Admin.tsx` — rename to `AdminPanel.tsx`, add tabs + login wall
- `tests/test_config.py` — add tests for new admin_username/admin_password fields

**Delete:**
- `frontend/src/App.css` — replaced by Tailwind utilities
- `frontend/src/pages/Setup.tsx` — replaced by SetupWizard.tsx

---

## Task 1: Config model extensions + Italian locale

**Files:**
- Modify: `backend/config/models.py`
- Modify: `backend/i18n/locales/en.json`
- Create: `backend/i18n/locales/it.json`
- Modify: `tests/test_config.py`
- Modify: `tests/test_i18n.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_config.py`:
```python
def test_config_has_admin_username_default(config_dir):
    config = load_config()
    assert config.admin_username == "admin"


def test_config_has_admin_password_default(config_dir):
    config = load_config()
    assert config.admin_password == ""


def test_save_and_load_admin_credentials(config_dir):
    config = TroveConfig(admin_username="sysadmin", admin_password="secret")
    save_config(config)
    loaded = load_config()
    assert loaded.admin_username == "sysadmin"
    assert loaded.admin_password == "secret"
```

Add to `tests/test_i18n.py`:
```python
def test_italian_locale_has_all_english_keys():
    """it.json must contain every key that en.json contains."""
    en = load_locale("en")
    it = load_locale("it")
    missing = set(en.keys()) - set(it.keys())
    assert missing == set(), f"it.json missing keys: {missing}"


def test_italian_locale_loads():
    it = load_locale("it")
    assert it["config.save"] == "Salva"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py::test_config_has_admin_username_default tests/test_i18n.py::test_italian_locale_has_all_english_keys -v
```
Expected: FAIL — `TroveConfig` has no `admin_username`, no `it.json` file.

- [ ] **Step 3: Add fields to TroveConfig**

Replace `backend/config/models.py`:
```python
"""Pydantic models for Trove server configuration."""
from pydantic import BaseModel, Field


class TroveConfig(BaseModel):
    """Persistent server configuration stored at $XDG_CONFIG_HOME/trove/config.json."""

    base_model: str = "gemma4:e4b"
    num_ctx: int = Field(default=8192, ge=512, le=262144)
    locale: str = "en"
    # Admin credentials — plaintext until full auth system is built.
    admin_username: str = "admin"
    admin_password: str = ""  # empty means setup not yet complete
```

- [ ] **Step 4: Add new i18n keys to en.json**

Replace `backend/i18n/locales/en.json` with the full file including all new keys:
```json
{
  "setup.title": "Trove Setup",
  "setup.system_check": "Checking your system...",
  "setup.step_install": "Install Ollama",
  "setup.step_start": "Start Ollama service",
  "setup.step_pull": "Download model",
  "setup.building": "Building model...",
  "setup.language.title": "Choose your language",
  "setup.language.select": "Select language",
  "setup.welcome.title": "Welcome to Trove",
  "setup.welcome.description": "This wizard will set up Trove on your computer. It will install Ollama, download an AI model, create your admin account, and configure Trove to start automatically.",
  "setup.welcome.begin": "Begin Setup",
  "setup.install.title": "Install Ollama",
  "setup.install.description": "Ollama is the AI runtime that powers Trove. This step downloads and installs it.",
  "setup.install.button": "Install Ollama",
  "setup.install.already_done": "Ollama is already installed",
  "setup.install.next": "Continue",
  "setup.models.title": "Choose AI Models",
  "setup.models.description": "Select one or more models to download. Only models that fit your computer's memory are shown.",
  "setup.models.pull_button": "Download selected",
  "setup.models.at_least_one": "Please select at least one model",
  "setup.models.next": "Continue",
  "setup.admin.title": "Create Admin Account",
  "setup.admin.description": "This account is used to access the Trove admin panel.",
  "setup.admin.username": "Username",
  "setup.admin.password": "Password",
  "setup.admin.button": "Save Account",
  "setup.admin.next": "Continue",
  "setup.service.title": "Install as Service",
  "setup.service.description": "This installs Trove so it starts automatically when the computer turns on.",
  "setup.service.button": "Install Service",
  "manage.title": "Trove Management",
  "manage.setup_complete": "Setup complete! Trove is now running on your network.",
  "manage.service_label": "Service",
  "manage.service_running": "Running",
  "manage.service_stopped": "Stopped",
  "manage.ollama_label": "Ollama",
  "manage.models_label": "Models",
  "manage.models_count": "{count} downloaded",
  "manage.access.title": "How to access Trove",
  "manage.access.description": "Give this address to anyone on your local network who needs to use Trove. They can type it directly into any web browser.",
  "manage.access.copy": "Copy",
  "manage.access.copied": "Copied!",
  "manage.restart": "Restart service",
  "manage.update_ollama": "Update Ollama",
  "manage.pull_model": "Download another model",
  "manage.uninstall": "Uninstall Trove",
  "admin.login.title": "Admin Login",
  "admin.login.username": "Username",
  "admin.login.password": "Password",
  "admin.login.button": "Sign in",
  "admin.login.error": "Invalid username or password",
  "admin.tab.settings": "Settings",
  "admin.tab.documents": "Documents",
  "admin.tab.tasks": "Tasks",
  "admin.documents.placeholder": "Document library coming soon",
  "admin.tasks.placeholder": "Task management coming soon",
  "app.tasks.placeholder": "Tasks will appear here",
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

- [ ] **Step 5: Create it.json**

Create `backend/i18n/locales/it.json`:
```json
{
  "setup.title": "Configurazione di Trove",
  "setup.system_check": "Controllo del sistema in corso...",
  "setup.step_install": "Installa Ollama",
  "setup.step_start": "Avvia il servizio Ollama",
  "setup.step_pull": "Scarica il modello",
  "setup.building": "Costruzione del modello...",
  "setup.language.title": "Scegli la lingua",
  "setup.language.select": "Seleziona lingua",
  "setup.welcome.title": "Benvenuto su Trove",
  "setup.welcome.description": "Questa procedura configurerà Trove sul tuo computer. Installerà Ollama, scaricherà un modello AI, creerà il tuo account amministratore e configurerà Trove per avviarsi automaticamente.",
  "setup.welcome.begin": "Inizia la configurazione",
  "setup.install.title": "Installa Ollama",
  "setup.install.description": "Ollama è il motore AI che alimenta Trove. Questo passaggio lo scarica e lo installa.",
  "setup.install.button": "Installa Ollama",
  "setup.install.already_done": "Ollama è già installato",
  "setup.install.next": "Continua",
  "setup.models.title": "Scegli i modelli AI",
  "setup.models.description": "Seleziona uno o più modelli da scaricare. Vengono mostrati solo i modelli compatibili con la memoria del tuo computer.",
  "setup.models.pull_button": "Scarica selezionati",
  "setup.models.at_least_one": "Seleziona almeno un modello",
  "setup.models.next": "Continua",
  "setup.admin.title": "Crea account amministratore",
  "setup.admin.description": "Questo account viene utilizzato per accedere al pannello di amministrazione di Trove.",
  "setup.admin.username": "Nome utente",
  "setup.admin.password": "Password",
  "setup.admin.button": "Salva account",
  "setup.admin.next": "Continua",
  "setup.service.title": "Installa come servizio",
  "setup.service.description": "Questo installa Trove in modo che si avvii automaticamente all'accensione del computer.",
  "setup.service.button": "Installa servizio",
  "manage.title": "Gestione Trove",
  "manage.setup_complete": "Configurazione completata! Trove è ora in esecuzione sulla tua rete.",
  "manage.service_label": "Servizio",
  "manage.service_running": "In esecuzione",
  "manage.service_stopped": "Fermo",
  "manage.ollama_label": "Ollama",
  "manage.models_label": "Modelli",
  "manage.models_count": "{count} scaricati",
  "manage.access.title": "Come accedere a Trove",
  "manage.access.description": "Dai questo indirizzo a chiunque sulla tua rete locale abbia bisogno di usare Trove. Possono digitarlo direttamente in qualsiasi browser web.",
  "manage.access.copy": "Copia",
  "manage.access.copied": "Copiato!",
  "manage.restart": "Riavvia servizio",
  "manage.update_ollama": "Aggiorna Ollama",
  "manage.pull_model": "Scarica un altro modello",
  "manage.uninstall": "Disinstalla Trove",
  "admin.login.title": "Accesso amministratore",
  "admin.login.username": "Nome utente",
  "admin.login.password": "Password",
  "admin.login.button": "Accedi",
  "admin.login.error": "Nome utente o password non validi",
  "admin.tab.settings": "Impostazioni",
  "admin.tab.documents": "Documenti",
  "admin.tab.tasks": "Attività",
  "admin.documents.placeholder": "Libreria documenti in arrivo",
  "admin.tasks.placeholder": "Gestione attività in arrivo",
  "app.tasks.placeholder": "Le attività appariranno qui",
  "config.title": "Configurazione",
  "config.base_model": "Modello base",
  "config.num_ctx": "Finestra di contesto",
  "config.locale": "Lingua",
  "config.save": "Salva",
  "config.saved": "Salvato",
  "model.gemma4_e2b": "Gemma 4 E2B (2,3B — più veloce)",
  "model.gemma4_e4b": "Gemma 4 E4B (4,5B — bilanciato)",
  "model.gemma4_26b": "Gemma 4 26B MoE (grande efficiente)",
  "model.gemma4_31b": "Gemma 4 31B (più capace)"
}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py tests/test_i18n.py -v
```
Expected: all pass including the 5 new tests.

- [ ] **Step 7: Commit**

```bash
git add backend/config/models.py backend/i18n/locales/en.json backend/i18n/locales/it.json tests/test_config.py tests/test_i18n.py
git commit -m "feat: add admin credentials to config model, add Italian locale"
```

---

## Task 2: main.py — create_app() factory + /api/mode endpoint

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/config/router.py` — remove PUT endpoint
- Modify: `tests/test_main.py`

- [ ] **Step 1: Write failing test for create_app factory and /api/mode**

Replace `tests/test_main.py`:
```python
"""Tests for the FastAPI application factory and mode routing."""
import pytest
from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok():
    """GET /api/health must always return 200 regardless of mode."""
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mode_endpoint_returns_setup():
    """GET /api/mode returns the mode the app was created with."""
    from backend.main import create_app
    client = TestClient(create_app(mode="setup"))
    response = client.get("/api/mode")
    assert response.status_code == 200
    assert response.json() == {"mode": "setup"}


def test_mode_endpoint_returns_app():
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    response = client.get("/api/mode")
    assert response.json() == {"mode": "app"}


def test_setup_router_only_in_setup_mode():
    """Setup endpoints must not exist in app mode."""
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    response = client.get("/api/setup/status")
    assert response.status_code == 404


def test_app_router_only_in_app_mode():
    """App endpoints must not exist in setup mode."""
    from backend.main import create_app
    client = TestClient(create_app(mode="setup"))
    response = client.get("/api/app/status")
    assert response.status_code == 404


def test_config_get_always_available():
    """GET /api/config must be reachable in both modes."""
    from backend.main import create_app
    for mode in ("setup", "app"):
        client = TestClient(create_app(mode=mode))
        response = client.get("/api/config")
        assert response.status_code == 200, f"Failed in {mode} mode"


def test_config_put_removed_from_shared_router():
    """PUT /api/config no longer exists — it moved to /api/app/admin/config."""
    from backend.main import create_app
    # In app mode the endpoint exists under /api/app/admin/config, not /api/config
    client = TestClient(create_app(mode="app"))
    response = client.put("/api/config", json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en", "admin_username": "admin", "admin_password": ""})
    assert response.status_code == 404


def test_api_routes_reachable_without_frontend_dist():
    """API routes work even when frontend/dist/ does not exist (dev mode)."""
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    response = client.get("/api/health")
    assert response.status_code == 200
```

- [ ] **Step 2: Run to verify failures**

```bash
uv run pytest tests/test_main.py -v
```
Expected: multiple failures — `create_app` not yet a function, setup/app routers not yet exist.

- [ ] **Step 3: Remove PUT from config router**

Replace `backend/config/router.py`:
```python
"""FastAPI router for the config domain. Exposes GET /api/config only.

PUT /api/config has moved to /api/app/admin/config (auth-gated, app mode only).
"""
from fastapi import APIRouter

from backend.config.models import TroveConfig
from backend.config.service import load_config

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config() -> TroveConfig:
    """Return the current server configuration."""
    return load_config()
```

- [ ] **Step 4: Refactor main.py to create_app() factory**

Replace `backend/main.py`:
```python
"""
Trove FastAPI application entry point.

Exports create_app(mode) factory used by both the CLI and tests.
The module-level `app` instance uses TROVE_MODE env var (defaults to "app").

Mode routing:
  setup  — mounts setup_router (/api/setup/*), binds 127.0.0.1
  app    — mounts app_router (/api/app/*), binds 0.0.0.0
Shared routers (config GET, i18n, system, ollama) are always mounted.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # Must run before os.getenv calls below

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config.router import router as config_router
from backend.i18n.router import router as i18n_router
from backend.ollama.router import router as ollama_router
from backend.ollama.service import RealOllamaService
from backend.system.router import router as system_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Terminate any ollama serve process we spawned on shutdown."""
    yield
    proc = RealOllamaService._serve_process
    if proc is not None and proc.poll() is None:
        proc.terminate()


def create_app(mode: str | None = None) -> FastAPI:
    """
    Create and configure the FastAPI application for the given mode.

    Args:
        mode: "setup" or "app". Reads TROVE_MODE env var if None,
              defaults to "app" if env var is also unset.
    """
    if mode is None:
        mode = os.getenv("TROVE_MODE", "app")

    application = FastAPI(title="Trove", version="0.1.0", lifespan=lifespan)

    # Allow the Vite dev server to call the backend during development.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Shared routers — always available in both modes.
    application.include_router(config_router)   # GET /api/config
    application.include_router(i18n_router)     # GET /api/i18n/*
    application.include_router(system_router)   # GET /api/system/check
    application.include_router(ollama_router)   # GET/POST /api/ollama/*

    # Mode endpoint — tells the frontend which surface to render.
    @application.get("/api/mode")
    def get_mode() -> dict:
        """Return the current operating mode (setup or app)."""
        return {"mode": mode}

    @application.get("/api/health")
    def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok"}

    # Mode-specific routers.
    # NOTE: These imports are deferred so that tests can call create_app(mode)
    # before those modules are fully implemented (they fail gracefully as 404s).
    if mode == "setup":
        try:
            from backend.setup.router import router as setup_router
            application.include_router(setup_router)
        except ImportError:
            pass  # setup domain not yet implemented
    elif mode == "app":
        try:
            from backend.app.router import router as app_router
            application.include_router(app_router)
        except ImportError:
            pass  # app domain not yet implemented

    # Serve the compiled React frontend in production.
    # NOTE: Must come after all include_router() calls — FastAPI matches
    # explicit routes first, but only if registered before the catch-all.
    _frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if _frontend_dist.exists():
        application.mount(
            "/assets",
            StaticFiles(directory=str(_frontend_dist / "assets")),
            name="assets",
        )

        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            """SPA fallback: serve static file if it exists, else index.html."""
            file_path = _frontend_dist / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(_frontend_dist / "index.html")

    return application


# Module-level instance for production (uvicorn backend.main:app).
app = create_app()
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_main.py -v
```
Expected: all 8 tests pass (setup/app router 404s because those modules don't exist yet, handled by the try/except ImportError).

- [ ] **Step 6: Run full suite to confirm no regressions**

```bash
uv run pytest -v
```
Expected: all 41 existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/config/router.py tests/test_main.py
git commit -m "refactor: create_app() factory with mode routing, remove PUT /api/config from shared router"
```

---

## Task 3: Setup domain — ServiceInstaller

**Files:**
- Create: `backend/setup/__init__.py`
- Create: `backend/setup/models.py`
- Create: `backend/setup/service.py`
- Create: `tests/test_setup.py` (service tests only — router tests added in Task 4)

- [ ] **Step 1: Write failing service tests**

Create `tests/test_setup.py`:
```python
"""Tests for the setup domain: ServiceInstaller and helper utilities."""
import os
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# ServiceInstaller tests
# ---------------------------------------------------------------------------

def test_fake_service_installer_records_install_call(monkeypatch):
    """FakeServiceInstaller.install() yields SSE lines and records the call."""
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    lines = list(installer.install(app_port=7770))
    assert any("[DONE]" in line for line in lines)
    assert installer.calls == ["install"]


def test_fake_service_installer_records_uninstall(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    lines = list(installer.uninstall())
    assert any("[DONE]" in line for line in lines)
    assert installer.calls == ["uninstall"]


def test_fake_service_installer_records_restart(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    list(installer.restart())
    assert installer.calls == ["restart"]


def test_fake_service_not_installed_by_default(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    assert installer.is_installed() is False


def test_fake_service_is_installed_after_install(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    list(installer.install(app_port=7770))
    assert installer.is_installed() is True


def test_fake_service_not_running_by_default(monkeypatch):
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    from backend.setup.service import get_service_installer
    installer = get_service_installer()
    assert installer.is_running() is False


def test_get_service_installer_returns_real_when_no_flag(monkeypatch):
    monkeypatch.delenv("TROVE_FAKE_SERVICE", raising=False)
    from backend.setup.service import get_service_installer, RealServiceInstaller
    installer = get_service_installer()
    assert isinstance(installer, RealServiceInstaller)


def test_get_lan_ip_returns_string():
    """get_lan_ip() should return a non-empty string (may be 127.0.0.1 in CI)."""
    from backend.setup.service import get_lan_ip
    ip = get_lan_ip()
    assert isinstance(ip, str)
    assert len(ip) > 0
    # Should look like an IP address
    parts = ip.split(".")
    assert len(parts) == 4
```

- [ ] **Step 2: Run to verify failures**

```bash
uv run pytest tests/test_setup.py -v
```
Expected: ImportError — `backend.setup.service` does not exist.

- [ ] **Step 3: Create backend/setup/__init__.py**

```python
"""Setup domain — setup-mode-only endpoints and service installation."""
```

- [ ] **Step 4: Create backend/setup/models.py**

```python
"""Pydantic request/response models for the setup domain."""
from pydantic import BaseModel


class LanguageRequest(BaseModel):
    """Request body for POST /api/setup/language."""
    locale: str


class AdminCredentialsRequest(BaseModel):
    """Request body for POST /api/setup/admin-credentials."""
    username: str
    password: str


class SetupStatus(BaseModel):
    """Response for GET /api/setup/status — which steps are complete."""
    ollama_installed: bool
    models_pulled: list[str]   # list of pulled model tags
    admin_configured: bool     # admin_password is non-empty
    service_installed: bool


class LanUrlResponse(BaseModel):
    """Response for GET /api/setup/lan-url."""
    ip: str
    port: int
    url: str


class OllamaVersionResponse(BaseModel):
    """Response for GET /api/setup/ollama-version."""
    version: str  # e.g. "0.6.2", or "unknown" if not installed
```

- [ ] **Step 5: Create backend/setup/service.py**

```python
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
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/test_setup.py -v
```
Expected: all 9 service tests pass.

- [ ] **Step 7: Run full suite**

```bash
uv run pytest -v
```
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/setup/ tests/test_setup.py
git commit -m "feat: add setup domain with ServiceInstaller (Protocol/Real/Fake)"
```

---

## Task 4: Setup domain — router

**Files:**
- Create: `backend/setup/router.py`
- Modify: `backend/ollama/router.py` — allow optional `model_tag` query param on pull
- Modify: `tests/test_setup.py` — add router tests

- [ ] **Step 1: Write failing router tests**

Append to `tests/test_setup.py`:
```python
# ---------------------------------------------------------------------------
# Router tests — require setup mode app
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_client(config_dir, monkeypatch):
    """TestClient with the app running in setup mode, fake services active."""
    monkeypatch.setenv("TROVE_FAKE_SERVICE", "1")
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.main import create_app
    return TestClient(create_app(mode="setup"))


def test_setup_status_returns_expected_fields(setup_client):
    response = setup_client.get("/api/setup/status")
    assert response.status_code == 200
    data = response.json()
    assert "ollama_installed" in data
    assert "models_pulled" in data
    assert "admin_configured" in data
    assert "service_installed" in data


def test_setup_status_admin_not_configured_by_default(setup_client):
    response = setup_client.get("/api/setup/status")
    assert response.json()["admin_configured"] is False


def test_setup_status_service_not_installed_by_default(setup_client):
    response = setup_client.get("/api/setup/status")
    assert response.json()["service_installed"] is False


def test_setup_language_saves_locale(setup_client, config_dir):
    response = setup_client.post("/api/setup/language", json={"locale": "it"})
    assert response.status_code == 200
    from backend.config.service import load_config
    assert load_config().locale == "it"


def test_setup_admin_credentials_saves_to_config(setup_client, config_dir):
    response = setup_client.post(
        "/api/setup/admin-credentials",
        json={"username": "teacher", "password": "blackboard"},
    )
    assert response.status_code == 200
    from backend.config.service import load_config
    config = load_config()
    assert config.admin_username == "teacher"
    assert config.admin_password == "blackboard"


def test_setup_status_admin_configured_after_save(setup_client, config_dir):
    setup_client.post(
        "/api/setup/admin-credentials",
        json={"username": "admin", "password": "pw"},
    )
    response = setup_client.get("/api/setup/status")
    assert response.json()["admin_configured"] is True


def test_setup_install_service_streams_done(setup_client):
    response = setup_client.post("/api/setup/install-service", json={"app_port": 7770})
    assert response.status_code == 200
    assert "[DONE]" in response.text


def test_setup_uninstall_streams_done(setup_client):
    response = setup_client.post("/api/setup/uninstall")
    assert response.status_code == 200
    assert "[DONE]" in response.text


def test_setup_restart_streams_done(setup_client):
    response = setup_client.post("/api/setup/restart-service")
    assert response.status_code == 200
    assert "[DONE]" in response.text


def test_setup_lan_url_returns_url(setup_client):
    response = setup_client.get("/api/setup/lan-url")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert ":" in data["url"]  # contains port
    assert data["port"] == 7770


def test_setup_ollama_version_returns_string(setup_client):
    response = setup_client.get("/api/setup/ollama-version")
    assert response.status_code == 200
    assert "version" in response.json()


def test_setup_not_available_in_app_mode(config_dir):
    from backend.main import create_app
    client = TestClient(create_app(mode="app"))
    assert client.get("/api/setup/status").status_code == 404
```

- [ ] **Step 2: Run to verify failures**

```bash
uv run pytest tests/test_setup.py -k "router or client or status or language or credentials or service or lan or version" -v
```
Expected: failures — `backend.setup.router` doesn't exist.

- [ ] **Step 3: Create backend/setup/router.py**

```python
"""
FastAPI router for the setup domain.

Mounted only in setup mode (TROVE_MODE=setup). Provides endpoints for
the setup wizard (language, status, admin credentials, service install)
and the management dashboard (LAN URL, Ollama version, restart, uninstall).
"""
import shutil
import subprocess
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.config.service import load_config, save_config
from backend.ollama.service import OllamaService, get_ollama_service
from backend.setup.models import (
    AdminCredentialsRequest,
    LanguageRequest,
    LanUrlResponse,
    OllamaVersionResponse,
    SetupStatus,
)
from backend.setup.service import ServiceInstaller, get_lan_ip, get_service_installer

# Default port the app mode listens on (used in the LAN URL response).
_APP_PORT = 7770

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status")
def get_status(
    installer: Annotated[ServiceInstaller, Depends(get_service_installer)],
    ollama: Annotated[OllamaService, Depends(get_ollama_service)],
) -> SetupStatus:
    """
    Return the completion state of each setup step.

    Used by SetupWizard to decide which steps are already done and
    by ManageDashboard to populate the status cards.
    """
    ollama_status = ollama.get_status()

    # List pulled models by running `ollama list` if Ollama is installed.
    models_pulled: list[str] = []
    if shutil.which("ollama"):
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True
        )
        if result.returncode == 0:
            # Output: "NAME\tID\tSIZE\tMODIFIED\n<tag>\t..."
            lines = result.stdout.strip().splitlines()[1:]  # skip header
            models_pulled = [line.split()[0] for line in lines if line.strip()]

    config = load_config()
    return SetupStatus(
        ollama_installed=ollama_status["installed"],
        models_pulled=models_pulled,
        admin_configured=bool(config.admin_password),
        service_installed=installer.is_installed(),
    )


@router.post("/language")
def set_language(body: LanguageRequest) -> dict:
    """
    Save the chosen locale to the persistent config.

    Called at Step 0 of the setup wizard so that all subsequent
    wizard text renders in the selected language.
    """
    config = load_config()
    config.locale = body.locale
    save_config(config)
    return {"saved": True, "locale": body.locale}


@router.post("/admin-credentials")
def save_admin_credentials(body: AdminCredentialsRequest) -> dict:
    """
    Save admin username and password to config.

    Stored as plaintext — this is a stub until the full auth system
    (JWT, password hashing) is implemented.
    """
    config = load_config()
    config.admin_username = body.username
    config.admin_password = body.password
    save_config(config)
    return {"saved": True}


@router.post("/install-service")
def install_service(
    body: InstallServiceRequest,
    installer: Annotated[ServiceInstaller, Depends(get_service_installer)],
) -> StreamingResponse:
    """Install and start the trove systemd service, streaming SSE progress."""
    return StreamingResponse(
        installer.install(app_port=body.app_port),
        media_type="text/event-stream",
    )


@router.post("/uninstall")
def uninstall(
    installer: Annotated[ServiceInstaller, Depends(get_service_installer)],
) -> StreamingResponse:
    """Stop, disable, and remove the trove systemd service."""
    return StreamingResponse(
        installer.uninstall(),
        media_type="text/event-stream",
    )


@router.post("/restart-service")
def restart_service(
    installer: Annotated[ServiceInstaller, Depends(get_service_installer)],
) -> StreamingResponse:
    """Restart the trove systemd service."""
    return StreamingResponse(
        installer.restart(),
        media_type="text/event-stream",
    )


@router.get("/lan-url")
def get_lan_url() -> LanUrlResponse:
    """
    Return the LAN URL where the app mode can be reached.

    Detects the machine's LAN IP and combines it with the default app port.
    """
    ip = get_lan_ip()
    return LanUrlResponse(ip=ip, port=_APP_PORT, url=f"http://{ip}:{_APP_PORT}")


@router.get("/ollama-version")
def get_ollama_version() -> OllamaVersionResponse:
    """Return the installed Ollama version string, or 'unknown' if not installed."""
    if not shutil.which("ollama"):
        return OllamaVersionResponse(version="unknown")
    result = subprocess.run(
        ["ollama", "--version"], capture_output=True, text=True
    )
    # Output format: "ollama version 0.6.2"
    version = result.stdout.strip().replace("ollama version ", "") or "unknown"
    return OllamaVersionResponse(version=version)
```

- [ ] **Step 4: Update backend/ollama/router.py to accept an optional model_tag**

The SetupWizard pulls multiple specific models (user-chosen tags, not just the config default).
Update `POST /api/ollama/pull` to accept an optional `model_tag` query parameter:

Replace the `pull_model` function in `backend/ollama/router.py`:
```python
@router.post("/pull")
def pull_model(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
    model_tag: str | None = None,
) -> StreamingResponse:
    """
    Pull a model and stream progress as SSE.

    Uses the provided model_tag query parameter if given, otherwise falls back
    to the base_model from current config. This allows the setup wizard to pull
    specific models by tag without changing the persisted config.
    """
    tag = model_tag or load_config().base_model
    return StreamingResponse(service.stream_pull(tag), media_type="text/event-stream")
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_setup.py -v
```
Expected: all setup tests pass.

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -v
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/setup/router.py backend/setup/models.py tests/test_setup.py
git commit -m "feat: add setup router with wizard and management endpoints"
```

---

## Task 5: App domain — router + Basic auth

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/router.py`
- Create: `tests/test_app_router.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_app_router.py`:
```python
"""Tests for the app domain router and admin authentication."""
import base64
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(config_dir, monkeypatch):
    """TestClient with the app running in app mode, fake services active."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.main import create_app
    return TestClient(create_app(mode="app"))


@pytest.fixture
def app_client_with_admin(config_dir, monkeypatch):
    """App-mode client with admin credentials pre-configured in config."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.config.service import load_config, save_config
    config = load_config()
    config.admin_username = "admin"
    config.admin_password = "testpass"
    save_config(config)
    from backend.main import create_app
    return TestClient(create_app(mode="app"))


def _basic_auth(username: str, password: str) -> str:
    """Return a valid Authorization: Basic header value."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def test_app_status_reachable(app_client):
    response = app_client.get("/api/app/status")
    assert response.status_code == 200
    assert response.json()["mode"] == "app"


def test_admin_config_requires_auth(app_client_with_admin):
    """PUT /api/app/admin/config without credentials returns 401."""
    response = app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": "testpass"},
    )
    assert response.status_code == 401


def test_admin_config_rejects_wrong_password(app_client_with_admin):
    response = app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": "testpass"},
        headers={"Authorization": _basic_auth("admin", "wrongpassword")},
    )
    assert response.status_code == 401


def test_admin_config_accepts_correct_credentials(app_client_with_admin, config_dir):
    response = app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "it",
              "admin_username": "admin", "admin_password": "testpass"},
        headers={"Authorization": _basic_auth("admin", "testpass")},
    )
    assert response.status_code == 200
    assert response.json()["locale"] == "it"


def test_admin_config_persists_changes(app_client_with_admin, config_dir):
    app_client_with_admin.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:26b", "num_ctx": 16384, "locale": "en",
              "admin_username": "admin", "admin_password": "testpass"},
        headers={"Authorization": _basic_auth("admin", "testpass")},
    )
    from backend.config.service import load_config
    config = load_config()
    assert config.base_model == "gemma4:26b"
    assert config.num_ctx == 16384


def test_admin_blocked_when_password_empty(app_client):
    """If admin_password is empty (setup not done), all admin routes return 401."""
    response = app_client.put(
        "/api/app/admin/config",
        json={"base_model": "gemma4:e2b", "num_ctx": 4096, "locale": "en",
              "admin_username": "admin", "admin_password": ""},
        headers={"Authorization": _basic_auth("admin", "")},
    )
    assert response.status_code == 401


def test_app_router_not_available_in_setup_mode(config_dir):
    from backend.main import create_app
    client = TestClient(create_app(mode="setup"))
    assert client.get("/api/app/status").status_code == 404


def test_build_model_requires_auth(app_client_with_admin):
    response = app_client_with_admin.post("/api/app/admin/build-model")
    assert response.status_code == 401
```

- [ ] **Step 2: Run to verify failures**

```bash
uv run pytest tests/test_app_router.py -v
```
Expected: failures — `backend.app.router` doesn't exist.

- [ ] **Step 3: Create backend/app/__init__.py**

```python
"""App domain — app-mode-only endpoints including the auth-gated admin panel."""
```

- [ ] **Step 4: Create backend/app/router.py**

```python
"""
FastAPI router for the app domain.

Mounted only in app mode (TROVE_MODE=app). Provides:
  - GET /api/app/status — public health check
  - PUT /api/app/admin/config — save config (requires admin auth)
  - POST /api/app/admin/build-model — build trove_model SSE (requires admin auth)

The require_admin dependency uses HTTP Basic auth checked against
the admin_username / admin_password stored in TroveConfig. Returns 401
if credentials are wrong or if admin_password is empty (setup not done).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.config.models import TroveConfig
from backend.config.service import load_config, save_config
from backend.ollama.service import OllamaService, get_ollama_service

router = APIRouter(prefix="/api/app", tags=["app"])
_security = HTTPBasic()


def require_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> None:
    """
    Verify admin credentials from HTTP Basic auth.

    Raises HTTP 401 if:
    - admin_password is empty (setup not complete)
    - username or password do not match config
    """
    config = load_config()
    if (
        not config.admin_password  # setup not done
        or credentials.username != config.admin_username
        or credentials.password != config.admin_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials or admin account not configured. Run trove setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/status")
def app_status() -> dict:
    """Confirm app mode is active. Used by the frontend as a health check."""
    return {"mode": "app", "status": "ok"}


@router.put("/admin/config", dependencies=[Depends(require_admin)])
def update_config(config: TroveConfig) -> TroveConfig:
    """
    Save updated configuration to disk.

    Requires admin credentials via HTTP Basic auth. This is the moved
    version of PUT /api/config, now auth-gated.
    """
    save_config(config)
    return config


@router.post("/admin/build-model", dependencies=[Depends(require_admin)])
def build_model(
    service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> StreamingResponse:
    """
    Generate the Modelfile and build trove_model, streaming SSE progress.

    Requires admin credentials. Moved from the shared ollama router.
    """
    return StreamingResponse(
        service.build_trove_model(),
        media_type="text/event-stream",
    )
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_app_router.py -v
```
Expected: all 9 tests pass.

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -v
```
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/ tests/test_app_router.py
git commit -m "feat: add app domain router with HTTP Basic auth for admin endpoints"
```

---

## Task 6: Typer CLI + pyproject.toml

**Files:**
- Create: `backend/cli.py`
- Modify: `pyproject.toml`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:
```python
"""Tests for the Typer CLI entry point."""
import os
import pytest
from typer.testing import CliRunner

from backend.cli import cli


runner = CliRunner()


def test_setup_command_sets_mode_and_correct_host(monkeypatch):
    """trove setup must configure TROVE_MODE=setup and bind 127.0.0.1."""
    captured = {}

    def fake_run(app_str, **kwargs):
        captured["app_str"] = app_str
        captured.update(kwargs)

    monkeypatch.setattr("backend.cli.uvicorn.run", fake_run)
    runner.invoke(cli, ["setup"])
    assert os.environ.get("TROVE_MODE") == "setup"
    assert captured.get("host") == "127.0.0.1"
    assert captured.get("port") == 7071


def test_setup_command_custom_port(monkeypatch):
    captured = {}
    monkeypatch.setattr("backend.cli.uvicorn.run", lambda a, **kw: captured.update(kw))
    runner.invoke(cli, ["setup", "--port", "9000"])
    assert captured.get("port") == 9000


def test_start_command_sets_mode_and_correct_host(monkeypatch):
    """trove start must configure TROVE_MODE=app and bind 0.0.0.0."""
    captured = {}
    monkeypatch.setattr("backend.cli.uvicorn.run", lambda a, **kw: captured.update(kw))
    runner.invoke(cli, ["start"])
    assert os.environ.get("TROVE_MODE") == "app"
    assert captured.get("host") == "0.0.0.0"
    assert captured.get("port") == 7770


def test_start_command_custom_host(monkeypatch):
    captured = {}
    monkeypatch.setattr("backend.cli.uvicorn.run", lambda a, **kw: captured.update(kw))
    runner.invoke(cli, ["start", "--host", "192.168.1.10"])
    assert captured.get("host") == "192.168.1.10"
```

- [ ] **Step 2: Run to verify failures**

```bash
uv run pytest tests/test_cli.py -v
```
Expected: ImportError — `backend.cli` doesn't exist.

- [ ] **Step 3: Add typer to dependencies**

In `pyproject.toml`, add `"typer>=0.12"` to the `dependencies` list:
```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2.10",
    "psutil>=6.1",
    "sse-starlette>=2.2",
    "python-dotenv>=1.0",
    "typer>=0.12",
]
```

Run `uv sync` to install:
```bash
uv sync --extra dev
```

- [ ] **Step 4: Create backend/cli.py**

```python
"""
Trove CLI entry point.

Provides two commands launched via the `trove` script defined in
[project.scripts] in pyproject.toml:

    trove setup   — setup mode, binds to 127.0.0.1 (local machine only)
    trove start   — app mode, binds to 0.0.0.0 (LAN accessible)

Each command sets TROVE_MODE before starting uvicorn so that create_app()
mounts the correct routers.
"""
import os

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
    os.environ["TROVE_MODE"] = "setup"
    uvicorn.run("backend.main:app", host=host, port=port)


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
    os.environ["TROVE_MODE"] = "app"
    uvicorn.run("backend.main:app", host=host, port=port)
```

- [ ] **Step 5: Add [project.scripts] and update taskipy tasks in pyproject.toml**

```toml
[project.scripts]
trove = "backend.cli:cli"

[tool.taskipy.tasks]
# Development: run both servers together (recommended)
dev          = "bash scripts/dev.sh"
# Development: run servers individually
dev-backend  = "uvicorn backend.main:app --reload --port 8001"
dev-frontend = "cd frontend && bun run dev"
# Setup and production modes via CLI
setup        = "trove setup"
start        = "trove start"
# Build frontend static files
build        = "cd frontend && bun run build"
install-deps = "uv sync --extra dev && cd frontend && bun install"
test         = "pytest -v"
```

Run `uv sync` again to register the new script:
```bash
uv sync --extra dev
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/test_cli.py -v
```
Expected: all 4 tests pass.

- [ ] **Step 7: Smoke test the CLI entry point**

```bash
trove --help
```
Expected: shows `setup` and `start` commands with descriptions.

- [ ] **Step 8: Run full suite**

```bash
uv run pytest -v
```
Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add backend/cli.py pyproject.toml uv.lock tests/test_cli.py
git commit -m "feat: add Typer CLI with trove setup and trove start commands"
```

---

## Task 7: Frontend — Flowbite + Tailwind CSS setup

**Files:**
- Modify: `frontend/package.json` (via bun add)
- Create: `frontend/tailwind.config.cjs`
- Create: `frontend/postcss.config.cjs`
- Modify: `frontend/src/index.css`
- Delete: `frontend/src/App.css` (inline styles removed from App.tsx and other files)
- Modify: `frontend/src/App.tsx` — remove App.css import
- Modify: `frontend/src/pages/Admin.tsx` — remove any App.css-dependent styles

- [ ] **Step 1: Install Flowbite and Tailwind v3**

```bash
cd frontend && bun add -d tailwindcss@3 postcss autoprefixer flowbite flowbite-react
```

Expected: packages added to `devDependencies` in `package.json`.

- [ ] **Step 2: Create tailwind.config.cjs**

Create `frontend/tailwind.config.cjs`:
```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    // Include flowbite-react component definitions so Tailwind doesn't purge their classes
    "./node_modules/flowbite-react/lib/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("flowbite/plugin"),
  ],
}
```

- [ ] **Step 3: Create postcss.config.cjs**

Create `frontend/postcss.config.cjs`:
```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 4: Replace index.css with Tailwind directives**

Replace `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: Remove App.css**

Delete `frontend/src/App.css`. Remove the `import './App.css'` line from `frontend/src/App.tsx` (and any other files that import it).

Check for imports:
```bash
grep -r "App.css" frontend/src/
```

Remove any found import lines.

- [ ] **Step 6: Verify the build works**

```bash
cd frontend && bun run build
```
Expected: build succeeds. There may be Tailwind class warnings but no TypeScript errors.

If the build fails with a PostCSS error about `tailwindcss` config, verify that `tailwind.config.cjs` is in the `frontend/` directory (not the repo root) and that `postcss.config.cjs` is also in `frontend/`.

- [ ] **Step 7: Verify dev server starts**

```bash
cd frontend && bun run dev
```
Expected: dev server starts on port 5173. Visit http://localhost:5173 — the app should render (possibly with different or no styling since custom CSS was replaced with Tailwind). Ctrl+C to stop.

- [ ] **Step 8: Commit**

```bash
cd .. && git add frontend/tailwind.config.cjs frontend/postcss.config.cjs frontend/src/index.css frontend/package.json frontend/bun.lock
git rm frontend/src/App.css
git add frontend/src/App.tsx
git commit -m "feat: add Flowbite + Tailwind CSS v3 to frontend"
```

---

## Task 8: Frontend — API clients + App.tsx mode routing

**Files:**
- Modify: `frontend/src/api/client.ts` — add optional headers support
- Create: `frontend/src/api/setup.ts` — typed setup API client
- Create: `frontend/src/api/app.ts` — typed app/admin API client
- Modify: `frontend/src/App.tsx` — fetch mode, conditional route trees

- [ ] **Step 1: Update ollamaApi.pull to accept an optional model tag**

The SetupWizard pulls user-chosen models by tag. Update the `pull` entry in `frontend/src/api/ollama.ts`:

```typescript
  /**
   * Pull a model; returns a streaming Response.
   * @param modelTag Specific tag to pull (e.g. "gemma4:26b").
   *   If omitted, backend uses the base_model from config.
   */
  pull: (modelTag?: string) =>
    post(modelTag
      ? `/ollama/pull?model_tag=${encodeURIComponent(modelTag)}`
      : '/ollama/pull'),
```

Replace the existing `pull: () => post('/ollama/pull'),` line with the above.

- [ ] **Step 2: Add headers support to api/client.ts**

Replace `frontend/src/api/client.ts`:
```typescript
/**
 * Base HTTP client for the Trove API.
 *
 * All requests go to /api (proxied to FastAPI in dev, served directly in prod).
 * Throws an Error with a descriptive message on non-2xx responses.
 */

const BASE = '/api'

/**
 * Make a GET request and return the parsed JSON response.
 * @template T Expected response type
 * @param path API path (e.g. "/config")
 * @param headers Optional additional request headers
 */
export async function get<T>(path: string, headers?: HeadersInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

/**
 * Make a PUT request with a JSON body and return the parsed JSON response.
 * @template T Expected response type
 * @param path API path
 * @param body Request body (serialised to JSON)
 * @param headers Optional additional request headers
 */
export async function put<T>(path: string, body: unknown, headers?: HeadersInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...(headers as Record<string, string> ?? {}) },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  return res.json()
}

/**
 * Make a POST request with an optional JSON body. Returns the raw Response for SSE streaming.
 * Throws if the response is non-2xx.
 * @param path API path
 * @param body Optional request body
 * @param headers Optional additional request headers
 */
export async function post(path: string, body?: unknown, headers?: HeadersInit): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(headers as Record<string, string> ?? {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res
}

/** Encode credentials for HTTP Basic Authorization header. */
export function basicAuth(username: string, password: string): string {
  return `Basic ${btoa(`${username}:${password}`)}`
}
```

- [ ] **Step 3: Create frontend/src/api/setup.ts**

```typescript
/**
 * Typed API client for setup-mode endpoints (/api/setup/*).
 *
 * These endpoints are only available when Trove is running in setup mode
 * (trove setup). Calling them in app mode returns 404.
 */
import { get, post } from './client'

/** Completion state returned by GET /api/setup/status. */
export interface SetupStatus {
  ollama_installed: boolean
  models_pulled: string[]
  admin_configured: boolean
  service_installed: boolean
}

/** LAN URL info returned by GET /api/setup/lan-url. */
export interface LanUrl {
  ip: string
  port: number
  url: string
}

export const setupApi = {
  /** Return which setup steps are complete. */
  status: (): Promise<SetupStatus> => get('/setup/status'),

  /** Save the chosen locale to config. */
  setLanguage: (locale: string): Promise<{ saved: boolean; locale: string }> =>
    post('/setup/language', { locale }),

  /** Save admin username and password to config. */
  saveAdminCredentials: (username: string, password: string): Promise<{ saved: boolean }> =>
    post('/setup/admin-credentials', { username, password }),

  /** Install the systemd service. Returns a raw Response for SSE streaming. */
  installService: (appPort = 7770): Promise<Response> =>
    post('/setup/install-service', { app_port: appPort }),

  /** Uninstall the systemd service. Returns a raw Response for SSE streaming. */
  uninstall: (): Promise<Response> => post('/setup/uninstall'),

  /** Restart the systemd service. Returns a raw Response for SSE streaming. */
  restart: (): Promise<Response> => post('/setup/restart-service'),

  /** Get the LAN URL for the app mode. */
  lanUrl: (): Promise<LanUrl> => get('/setup/lan-url'),

  /** Get the installed Ollama version string. */
  ollamaVersion: (): Promise<{ version: string }> => get('/setup/ollama-version'),
}
```

- [ ] **Step 4: Create frontend/src/api/app.ts**

```typescript
/**
 * Typed API client for app-mode admin endpoints (/api/app/admin/*).
 *
 * All admin endpoints require HTTP Basic auth. Pass credentials via
 * basicAuth(username, password) from ./client.
 */
import { type TroveConfig } from './config'
import { basicAuth, post, put } from './client'

export const appApi = {
  /**
   * Save updated configuration. Requires admin credentials.
   * @param config Updated configuration object
   * @param username Admin username
   * @param password Admin password
   */
  saveConfig: (
    config: TroveConfig,
    username: string,
    password: string,
  ): Promise<TroveConfig> =>
    put('/app/admin/config', config, { Authorization: basicAuth(username, password) }),

  /**
   * Build trove_model from the current config. Requires admin credentials.
   * Returns a raw Response for SSE streaming.
   */
  buildModel: (username: string, password: string): Promise<Response> =>
    post('/app/admin/build-model', undefined, {
      Authorization: basicAuth(username, password),
    }),
}
```

- [ ] **Step 5: Rewrite App.tsx with mode-based routing**

Replace `frontend/src/App.tsx`:
```typescript
import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { get } from './api/client'
import AdminPanel from './pages/AdminPanel'
import ManageDashboard from './pages/ManageDashboard'
import SetupWizard from './pages/SetupWizard'
import TaskShell from './pages/TaskShell'

/**
 * Root application component.
 *
 * Fetches GET /api/mode on load to determine which surface to render.
 * Setup mode exposes the setup wizard and management dashboard.
 * App mode exposes the task runner shell and the admin panel.
 *
 * Shows a loading screen while the mode is being fetched.
 */
export default function App() {
  const [mode, setMode] = useState<'setup' | 'app' | null>(null)

  useEffect(() => {
    get<{ mode: string }>('/mode')
      .then(({ mode: m }) => setMode(m as 'setup' | 'app'))
      .catch(() => setMode('app')) // default to app on error
  }, [])

  if (mode === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <p className="text-gray-400">Loading...</p>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        {mode === 'setup' ? (
          <>
            <Route path="/" element={<SetupWizard />} />
            <Route path="/manage" element={<ManageDashboard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </>
        ) : (
          <>
            <Route path="/" element={<TaskShell />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}
```

Note: `AdminPanel`, `ManageDashboard`, `SetupWizard`, `TaskShell` are imported but don't exist yet. The build will fail until Tasks 9–12 are complete. That is expected — proceed to Task 9.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/ollama.ts frontend/src/api/setup.ts frontend/src/api/app.ts frontend/src/App.tsx
git commit -m "feat: add setup/app API clients, update ollamaApi.pull, and mode-based routing in App.tsx"
```

---

## Task 9: SetupWizard.tsx + new i18n keys

**Files:**
- Create: `frontend/src/pages/SetupWizard.tsx`
- Delete: `frontend/src/pages/Setup.tsx`

Note: The old `Setup.tsx` page is replaced entirely. The SetupWizard uses Flowbite components and the new `/api/setup/*` endpoints.

- [ ] **Step 1: Create frontend/src/pages/SetupWizard.tsx**

```typescript
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { configApi } from '../api/config'
import { ollamaApi, streamLines } from '../api/ollama'
import { setupApi, type SetupStatus } from '../api/setup'
import { systemApi, type ModelInfo } from '../api/system'
import { useTranslation } from '../i18n'

/**
 * SetupWizard — six-step guided setup flow.
 *
 * Steps:
 *   0. Language   — pick locale, saved to config immediately
 *   1. Welcome    — system info table, begin button
 *   2. Ollama     — install Ollama (skipped if already installed)
 *   3. Models     — multi-select viable models, pull each in sequence
 *   4. Admin      — set admin username + password
 *   5. Service    — install systemd service, then redirect to /manage
 *
 * The step indicator at the top shows completed steps as ticked.
 * A step can only proceed once its action succeeds.
 */
export default function SetupWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [locale, setLocale] = useState('en')
  const { t, ready } = useTranslation(locale)
  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [system, setSystem] = useState<Awaited<ReturnType<typeof systemApi.check>> | null>(null)
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set())
  const [log, setLog] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [adminUser, setAdminUser] = useState('')
  const [adminPass, setAdminPass] = useState('')
  const logEndRef = useRef<HTMLDivElement>(null)

  // Load initial state on mount
  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    setupApi.status().then(setStatus)
    systemApi.check().then(setSystem)
  }, [])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [log])

  function appendLog(line: string) {
    if (line.startsWith('[DONE]')) return
    setLog(prev => [
      ...prev,
      line.startsWith('[ERROR]') ? `ERROR: ${line.replace('[ERROR] ', '')}` : line,
    ])
  }

  // Step 0 — Language picker
  async function handleLanguageSelect(newLocale: string) {
    setLocale(newLocale)
    await setupApi.setLanguage(newLocale)
  }

  // Step 2 — Install Ollama (stream)
  async function handleInstallOllama() {
    setBusy(true)
    setLog([])
    const res = await ollamaApi.install()
    await streamLines(res, appendLog, () => {
      setBusy(false)
      setupApi.status().then(setStatus)
    })
  }

  // Step 3 — Pull selected models in sequence
  async function handlePullModels() {
    if (selectedModels.size === 0) return
    setBusy(true)
    setLog([])
    for (const tag of selectedModels) {
      appendLog(`--- Downloading ${tag} ---`)
      const res = await ollamaApi.pull(tag)
      await new Promise<void>(resolve =>
        streamLines(res, appendLog, resolve)
      )
    }
    setBusy(false)
    setupApi.status().then(setStatus)
  }

  // Step 4 — Save admin credentials
  async function handleSaveAdmin() {
    if (!adminUser || !adminPass) return
    setBusy(true)
    await setupApi.saveAdminCredentials(adminUser, adminPass)
    setBusy(false)
    setupApi.status().then(setStatus)
  }

  // Step 5 — Install service and redirect to management dashboard
  async function handleInstallService() {
    setBusy(true)
    setLog([])
    const res = await setupApi.installService()
    await streamLines(res, appendLog, () => {
      setBusy(false)
      navigate('/manage', { state: { justInstalled: true } })
    })
  }

  if (!ready || !status || !system) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <p className="text-gray-400">{t('setup.system_check')}</p>
      </div>
    )
  }

  const steps = [
    t('setup.language.title'),
    t('setup.welcome.title'),
    t('setup.install.title'),
    t('setup.models.title'),
    t('setup.admin.title'),
    t('setup.service.title'),
  ]

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Step indicator */}
      <div className="border-b border-gray-700 bg-gray-800 px-6 py-4">
        <ol className="flex items-center gap-2 text-sm overflow-x-auto">
          {steps.map((label, i) => (
            <li key={i} className="flex items-center gap-2 whitespace-nowrap">
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  i < step
                    ? 'bg-green-600 text-white'
                    : i === step
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-600 text-gray-400'
                }`}
              >
                {i < step ? '✓' : i + 1}
              </span>
              <span className={i === step ? 'text-white font-medium' : 'text-gray-400'}>
                {label}
              </span>
              {i < steps.length - 1 && <span className="text-gray-600">›</span>}
            </li>
          ))}
        </ol>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-10">

        {/* Step 0: Language */}
        {step === 0 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.language.title')}</h1>
            <select
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
              value={locale}
              onChange={e => handleLanguageSelect(e.target.value)}
            >
              <option value="en">English</option>
              <option value="it">Italiano</option>
            </select>
            <button
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium"
              onClick={() => setStep(1)}
            >
              {t('setup.welcome.begin')}
            </button>
          </div>
        )}

        {/* Step 1: Welcome */}
        {step === 1 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.welcome.title')}</h1>
            <p className="text-gray-300">{t('setup.welcome.description')}</p>
            <table className="w-full text-sm border border-gray-700 rounded-lg overflow-hidden">
              <tbody>
                <tr className="border-b border-gray-700">
                  <td className="px-4 py-2 text-gray-400 bg-gray-800">RAM</td>
                  <td className="px-4 py-2">{system.ram_gb.toFixed(1)} GB</td>
                </tr>
                <tr className="border-b border-gray-700">
                  <td className="px-4 py-2 text-gray-400 bg-gray-800">Disk</td>
                  <td className="px-4 py-2">{system.disk_free_gb.toFixed(1)} GB free</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 text-gray-400 bg-gray-800">GPU</td>
                  <td className="px-4 py-2">
                    {system.gpu_info
                      ? `${system.gpu_info.name} (${system.gpu_info.vram_gb.toFixed(1)} GB VRAM)`
                      : 'None detected'}
                  </td>
                </tr>
              </tbody>
            </table>
            <button
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium"
              onClick={() => setStep(2)}
            >
              {t('setup.welcome.begin')}
            </button>
          </div>
        )}

        {/* Step 2: Install Ollama */}
        {step === 2 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.install.title')}</h1>
            <p className="text-gray-300">{t('setup.install.description')}</p>

            {status.ollama_installed ? (
              <div className="flex items-center gap-2 text-green-400">
                <span>✓</span>
                <span>{t('setup.install.already_done')}</span>
              </div>
            ) : (
              <button
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
                disabled={busy}
                onClick={handleInstallOllama}
              >
                {busy ? '...' : t('setup.install.button')}
              </button>
            )}

            {log.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
                {log.map((l, i) => <div key={i}>{l}</div>)}
                <div ref={logEndRef} />
              </div>
            )}

            <button
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium disabled:opacity-50"
              disabled={!status.ollama_installed || busy}
              onClick={() => setStep(3)}
            >
              {t('setup.install.next')}
            </button>
          </div>
        )}

        {/* Step 3: Choose models */}
        {step === 3 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.models.title')}</h1>
            <p className="text-gray-300">{t('setup.models.description')}</p>

            <div className="space-y-3">
              {system.viable_models.map((m: ModelInfo) => (
                <label
                  key={m.tag}
                  className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedModels.has(m.tag)
                      ? 'border-blue-500 bg-blue-950'
                      : 'border-gray-700 bg-gray-800 hover:border-gray-500'
                  }`}
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selectedModels.has(m.tag)}
                    onChange={e => {
                      const next = new Set(selectedModels)
                      if (e.target.checked) next.add(m.tag)
                      else next.delete(m.tag)
                      setSelectedModels(next)
                    }}
                  />
                  <div>
                    <div className="font-medium">{m.tag}</div>
                    <div className="text-sm text-gray-400">
                      Min {m.min_ram_gb} GB RAM · Max {(m.max_ctx / 1024).toFixed(0)}K context
                      {m.audio && ' · Audio'}
                      {status.models_pulled.includes(m.tag) && (
                        <span className="ml-2 text-green-400">✓ downloaded</span>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>

            {log.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
                {log.map((l, i) => <div key={i}>{l}</div>)}
                <div ref={logEndRef} />
              </div>
            )}

            <div className="flex gap-3">
              <button
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
                disabled={selectedModels.size === 0 || busy}
                onClick={handlePullModels}
              >
                {busy ? '...' : t('setup.models.pull_button')}
              </button>
              <button
                className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium disabled:opacity-50"
                disabled={status.models_pulled.length === 0 || busy}
                onClick={() => setStep(4)}
              >
                {t('setup.models.next')}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Admin account */}
        {step === 4 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.admin.title')}</h1>
            <p className="text-gray-300">{t('setup.admin.description')}</p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('setup.admin.username')}</label>
                <input
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  value={adminUser}
                  onChange={e => setAdminUser(e.target.value)}
                  autoComplete="username"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('setup.admin.password')}</label>
                <input
                  type="password"
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  value={adminPass}
                  onChange={e => setAdminPass(e.target.value)}
                  autoComplete="new-password"
                />
              </div>
            </div>

            {status.admin_configured && (
              <p className="text-green-400 text-sm">✓ Admin account saved</p>
            )}

            <div className="flex gap-3">
              <button
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
                disabled={!adminUser || !adminPass || busy}
                onClick={handleSaveAdmin}
              >
                {busy ? '...' : t('setup.admin.button')}
              </button>
              <button
                className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium disabled:opacity-50"
                disabled={!status.admin_configured || busy}
                onClick={() => setStep(5)}
              >
                {t('setup.admin.next')}
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Install service */}
        {step === 5 && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">{t('setup.service.title')}</h1>
            <p className="text-gray-300">{t('setup.service.description')}</p>

            <button
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
              disabled={busy}
              onClick={handleInstallService}
            >
              {busy ? '...' : t('setup.service.button')}
            </button>

            {log.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
                {log.map((l, i) => <div key={i}>{l}</div>)}
                <div ref={logEndRef} />
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
```

- [ ] **Step 2: Remove old Setup.tsx**

```bash
git rm frontend/src/pages/Setup.tsx
```

If any other file imports `Setup`, update the import to `SetupWizard`. Check:
```bash
grep -r "from.*Setup'" frontend/src/
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && bun run build
```
Expected: build succeeds (App.tsx imports SetupWizard which now exists).

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/src/pages/SetupWizard.tsx frontend/src/
git commit -m "feat: add SetupWizard with six-step flow and Flowbite styling"
```

---

## Task 10: ManageDashboard.tsx

**Files:**
- Create: `frontend/src/pages/ManageDashboard.tsx`

- [ ] **Step 1: Create frontend/src/pages/ManageDashboard.tsx**

```typescript
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { configApi } from '../api/config'
import { ollamaApi, streamLines } from '../api/ollama'
import { setupApi, type LanUrl, type SetupStatus } from '../api/setup'
import { useTranslation } from '../i18n'

/**
 * ManageDashboard — shown after setup completes and on return visits to setup mode.
 *
 * Displays:
 * - Optional success banner (when arriving from SetupWizard via /manage?justInstalled)
 * - Status cards: service, Ollama version, models count
 * - Prominent LAN URL box with copy button
 * - Management action buttons: restart, update Ollama, pull model, uninstall
 */
export default function ManageDashboard() {
  const location = useLocation()
  const justInstalled = (location.state as { justInstalled?: boolean } | null)?.justInstalled ?? false

  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)
  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [lanUrl, setLanUrl] = useState<LanUrl | null>(null)
  const [ollamaVersion, setOllamaVersion] = useState<string>('')
  const [copied, setCopied] = useState(false)
  const [log, setLog] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [activeAction, setActiveAction] = useState<string | null>(null)

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
    setupApi.status().then(setStatus)
    setupApi.lanUrl().then(setLanUrl)
    setupApi.ollamaVersion().then(v => setOllamaVersion(v.version))
  }, [])

  function appendLog(line: string) {
    if (line.startsWith('[DONE]')) return
    setLog(prev => [
      ...prev,
      line.startsWith('[ERROR]') ? `ERROR: ${line.replace('[ERROR] ', '')}` : line,
    ])
  }

  async function runAction(label: string, action: () => Promise<Response>) {
    setBusy(true)
    setActiveAction(label)
    setLog([])
    const res = await action()
    await streamLines(res, appendLog, () => {
      setBusy(false)
      setActiveAction(null)
      setupApi.status().then(setStatus)
    })
  }

  function copyUrl() {
    if (!lanUrl) return
    navigator.clipboard.writeText(lanUrl.url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-2xl mx-auto px-6 py-10 space-y-6">

        {/* Success banner — only shown right after setup completes */}
        {justInstalled && (
          <div className="p-4 rounded-lg bg-green-900 border border-green-700 text-green-300">
            ✓ {t('manage.setup_complete')}
          </div>
        )}

        <h1 className="text-2xl font-bold">{t('manage.title')}</h1>

        {/* Status cards */}
        {status && (
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase mb-1">{t('manage.service_label')}</p>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${status.service_installed ? 'bg-green-400' : 'bg-red-400'}`} />
                <span className="font-medium text-sm">
                  {status.service_installed ? t('manage.service_running') : t('manage.service_stopped')}
                </span>
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase mb-1">{t('manage.ollama_label')}</p>
              <p className="font-medium text-sm">{ollamaVersion || '—'}</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase mb-1">{t('manage.models_label')}</p>
              <p className="font-medium text-sm">
                {t('manage.models_count').replace('{count}', String(status.models_pulled.length))}
              </p>
            </div>
          </div>
        )}

        {/* LAN URL — prominent access instructions */}
        {lanUrl && (
          <div className="bg-gray-800 rounded-lg p-5 border border-blue-600">
            <h2 className="font-semibold mb-1">{t('manage.access.title')}</h2>
            <p className="text-sm text-gray-400 mb-3">{t('manage.access.description')}</p>
            <div className="flex gap-3 items-center">
              <code className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-2 text-base font-mono">
                {lanUrl.url}
              </code>
              <button
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium whitespace-nowrap"
                onClick={copyUrl}
              >
                {copied ? t('manage.access.copied') : t('manage.access.copy')}
              </button>
            </div>
          </div>
        )}

        {/* Management actions */}
        <div>
          <p className="text-xs text-gray-400 uppercase mb-3">Management</p>
          <div className="flex gap-3 flex-wrap">
            <button
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => runAction('restart', setupApi.restart)}
            >
              {activeAction === 'restart' ? '...' : t('manage.restart')}
            </button>
            <button
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => runAction('update', () => ollamaApi.install())}
            >
              {activeAction === 'update' ? '...' : t('manage.update_ollama')}
            </button>
            <button
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => {
                const tag = prompt('Model tag to download (e.g. gemma4:26b):')
                if (tag) runAction('pull', () => ollamaApi.pull(tag))
              }}
            >
              {activeAction === 'pull' ? '...' : t('manage.pull_model')}
            </button>
            <button
              className="px-4 py-2 bg-red-900 hover:bg-red-800 border border-red-700 text-red-300 rounded-lg text-sm disabled:opacity-50"
              disabled={busy}
              onClick={() => {
                if (confirm('Are you sure you want to uninstall Trove?')) {
                  runAction('uninstall', setupApi.uninstall)
                }
              }}
            >
              {activeAction === 'uninstall' ? '...' : t('manage.uninstall')}
            </button>
          </div>
        </div>

        {/* SSE log for ongoing actions */}
        {log.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-48 overflow-y-auto">
            {log.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}

      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && bun run build
```
Expected: no TypeScript errors from ManageDashboard.

- [ ] **Step 3: Commit**

```bash
cd .. && git add frontend/src/pages/ManageDashboard.tsx
git commit -m "feat: add ManageDashboard with status cards, LAN URL, and management actions"
```

---

## Task 11: AdminPanel.tsx (replaces Admin.tsx)

**Files:**
- Create: `frontend/src/pages/AdminPanel.tsx`
- Delete: `frontend/src/pages/Admin.tsx`

- [ ] **Step 1: Create frontend/src/pages/AdminPanel.tsx**

```typescript
import { useEffect, useState } from 'react'
import { appApi } from '../api/app'
import { type TroveConfig, configApi } from '../api/config'
import { streamLines } from '../api/ollama'
import { systemApi, type ModelInfo } from '../api/system'
import { useTranslation } from '../i18n'

type SaveState = 'idle' | 'saving' | 'building' | 'done' | 'error'

/**
 * AdminPanel — tabbed admin interface for app mode (/admin).
 *
 * Requires admin login (HTTP Basic). On first render shows a login form.
 * Credentials are stored in component state only (cleared on page refresh).
 *
 * Tabs:
 *   Settings  — model picker, num_ctx slider, language selector, save + build
 *   Documents — placeholder
 *   Tasks     — placeholder
 */
export default function AdminPanel() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authed, setAuthed] = useState(false)
  const [loginError, setLoginError] = useState(false)
  const [activeTab, setActiveTab] = useState<'settings' | 'documents' | 'tasks'>('settings')

  const [config, setConfig] = useState<TroveConfig | null>(null)
  const [viableModels, setViableModels] = useState<ModelInfo[]>([])
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [buildLog, setBuildLog] = useState<string[]>([])
  const { t } = useTranslation(config?.locale ?? 'en')

  // Load config and viable models after successful login
  useEffect(() => {
    if (!authed) return
    Promise.all([configApi.get(), systemApi.check()]).then(([c, sys]) => {
      setConfig(c)
      setViableModels(sys.viable_models)
    })
  }, [authed])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoginError(false)
    try {
      // Attempt a GET /api/app/status (no auth needed) then try a config put to
      // verify credentials without making a destructive call.
      // Actually: fetch config first then try a no-op PUT to verify credentials.
      const c = await configApi.get()
      await appApi.saveConfig(c, username, password)
      setAuthed(true)
    } catch {
      setLoginError(true)
    }
  }

  async function handleSave() {
    if (!config) return
    setSaveState('saving')
    try {
      await appApi.saveConfig(config, username, password)
      setSaveState('building')
      setBuildLog([])
      const res = await appApi.buildModel(username, password)
      await streamLines(
        res,
        line => {
          if (!line.startsWith('[DONE]')) {
            setBuildLog(prev => [...prev, line])
          }
        },
        () => setSaveState('done'),
      )
    } catch {
      setSaveState('error')
    }
  }

  // ---- Login wall ----
  if (!authed) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="w-full max-w-sm bg-gray-800 border border-gray-700 rounded-xl p-8">
          <h1 className="text-xl font-bold mb-6">{t('admin.login.title')}</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">{t('admin.login.username')}</label>
              <input
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">{t('admin.login.password')}</label>
              <input
                type="password"
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {loginError && (
              <p className="text-red-400 text-sm">{t('admin.login.error')}</p>
            )}
            <button
              type="submit"
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium"
            >
              {t('admin.login.button')}
            </button>
          </form>
        </div>
      </div>
    )
  }

  // ---- Admin panel (authenticated) ----
  if (!config) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-gray-400">Loading...</p>
      </div>
    )
  }

  const MODEL_LABELS: Record<string, string> = {
    'gemma4:e2b': t('model.gemma4_e2b'),
    'gemma4:e4b': t('model.gemma4_e4b'),
    'gemma4:26b': t('model.gemma4_26b'),
    'gemma4:31b': t('model.gemma4_31b'),
  }

  const selectedModel = viableModels.find(m => m.tag === config.base_model)
  const maxCtx = selectedModel?.max_ctx ?? 131072

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold mb-6">Trove Admin</h1>

        {/* Tabs */}
        <div className="flex border-b border-gray-700 mb-6">
          {(['settings', 'documents', 'tasks'] as const).map(tab => (
            <button
              key={tab}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'border-b-2 border-blue-500 text-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
              onClick={() => setActiveTab(tab)}
            >
              {t(`admin.tab.${tab}`)}
            </button>
          ))}
        </div>

        {/* Settings tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm text-gray-400 mb-2">{t('config.base_model')}</label>
              <select
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
                value={config.base_model}
                onChange={e => setConfig({ ...config, base_model: e.target.value, num_ctx: 8192 })}
              >
                {viableModels.map(m => (
                  <option key={m.tag} value={m.tag}>
                    {MODEL_LABELS[m.tag] ?? m.tag}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                {t('config.num_ctx')}: {config.num_ctx.toLocaleString()}
              </label>
              <input
                type="range"
                className="w-full"
                min={512}
                max={maxCtx}
                step={512}
                value={config.num_ctx}
                onChange={e => setConfig({ ...config, num_ctx: Number(e.target.value) })}
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>512</span>
                <span>{(maxCtx / 1024).toFixed(0)}K</span>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">{t('config.locale')}</label>
              <select
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
                value={config.locale}
                onChange={e => setConfig({ ...config, locale: e.target.value })}
              >
                <option value="en">English</option>
                <option value="it">Italiano</option>
              </select>
            </div>

            <button
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
              disabled={saveState === 'saving' || saveState === 'building'}
              onClick={handleSave}
            >
              {saveState === 'saving' ? 'Saving...'
                : saveState === 'building' ? t('setup.building')
                : saveState === 'done' ? t('config.saved')
                : t('config.save')}
            </button>

            {buildLog.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-4 font-mono text-xs text-gray-300 max-h-40 overflow-y-auto">
                {buildLog.map((l, i) => <div key={i}>{l}</div>)}
              </div>
            )}
          </div>
        )}

        {/* Documents tab — placeholder */}
        {activeTab === 'documents' && (
          <p className="text-gray-400">{t('admin.documents.placeholder')}</p>
        )}

        {/* Tasks tab — placeholder */}
        {activeTab === 'tasks' && (
          <p className="text-gray-400">{t('admin.tasks.placeholder')}</p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Remove old Admin.tsx**

```bash
git rm frontend/src/pages/Admin.tsx
```

Check for any remaining imports of `Admin`:
```bash
grep -r "from.*Admin'" frontend/src/
```
Any found should already reference `AdminPanel` from App.tsx (Task 8 already uses `AdminPanel`).

- [ ] **Step 3: Verify build**

```bash
cd frontend && bun run build
```
Expected: clean build, no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/src/pages/AdminPanel.tsx frontend/src/
git commit -m "feat: add AdminPanel with login wall, tabs, and Settings migrated from Admin.tsx"
```

---

## Task 12: TaskShell.tsx

**Files:**
- Create: `frontend/src/pages/TaskShell.tsx`

- [ ] **Step 1: Create frontend/src/pages/TaskShell.tsx**

```typescript
import { useEffect, useState } from 'react'
import { configApi } from '../api/config'
import { useTranslation } from '../i18n'

/**
 * TaskShell — landing page for regular users in app mode.
 *
 * No login required. Shows the Trove wordmark and a placeholder area
 * where the task runner will live once the task system is implemented.
 */
export default function TaskShell() {
  const [locale, setLocale] = useState('en')
  const { t } = useTranslation(locale)

  useEffect(() => {
    configApi.get().then(c => setLocale(c.locale))
  }, [])

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Navigation bar */}
      <nav className="border-b border-gray-700 bg-gray-800 px-6 py-4 flex items-center justify-between">
        <span className="text-lg font-bold tracking-tight">Trove</span>
        <a
          href="/admin"
          className="text-sm text-gray-400 hover:text-white transition-colors"
        >
          Admin →
        </a>
      </nav>

      {/* Placeholder content */}
      <div className="flex items-center justify-center min-h-[calc(100vh-65px)]">
        <p className="text-gray-500 text-sm">{t('app.tasks.placeholder')}</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify full build**

```bash
cd frontend && bun run build
```
Expected: clean build, all pages compile.

- [ ] **Step 3: Run full backend test suite**

```bash
cd .. && uv run pytest -v
```
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/TaskShell.tsx
git commit -m "feat: add TaskShell placeholder for regular user app mode"
```

---

## Final check

After all 12 tasks, run the complete test suite one more time:

```bash
uv run pytest -v && cd frontend && bun run build
```

Expected:
- All backend tests pass
- Frontend build succeeds with no TypeScript errors

Then update `.env` to set `TROVE_FAKE_SERVICE=1` alongside the existing fake flags for development:
```
TROVE_FAKE_OLLAMA=1
TROVE_FAKE_SYSTEM=1
TROVE_FAKE_SERVICE=1
```

Smoke test the full dev flow:
```bash
task dev-backend  # in one terminal — starts on :8001 in app mode (TROVE_MODE unset → default app)
task dev-frontend # in another terminal — starts on :5173
```
Visit http://localhost:5173 — should show TaskShell (app mode). To test setup mode, run:
```bash
TROVE_MODE=setup uvicorn backend.main:app --reload --port 8001
```
Visit http://localhost:5173 — should show SetupWizard.
