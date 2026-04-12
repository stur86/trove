# Setup / App Mode Split + Flowbite UI

**Date:** 2026-04-04
**Scope:** Two-mode architecture (setup vs app), Typer CLI entry point, Flowbite/Tailwind frontend, Italian locale

---

## Overview

Trove is split into two distinct operating modes launched by a single Typer CLI entry point:

- **Setup mode** (`trove setup`) — binds to `127.0.0.1`, accessible only from the local machine, no login. Used for first-time installation (Ollama, model pull, admin credentials, systemd service) and ongoing management (restart, update, pull models, uninstall).
- **App mode** (`trove start`) — binds to `0.0.0.0`, accessible from the LAN. Regular users reach the task runner with no login; admins reach `/admin` with a username/password check.

Both modes run the same FastAPI application, with routers conditionally mounted based on a `TROVE_MODE` environment variable set by the CLI.

---

## CLI Entry Point (`backend/cli.py`)

A Typer application with two commands:

```
trove setup   [--host 127.0.0.1] [--port 7071]
trove start   [--host 0.0.0.0]   [--port 7770]
```

Each command:
1. Sets `TROVE_MODE` (`"setup"` or `"app"`) as an environment variable
2. Starts uvicorn programmatically with the given host/port
3. On shutdown, signals cleanup to the lifespan context (existing Ollama process termination)

Registered in `pyproject.toml` as:
```toml
[project.scripts]
trove = "backend.cli:app"
```

Taskipy tasks become thin wrappers:
```toml
setup   = "trove setup"
start   = "trove start"
dev     = "bash scripts/dev.sh"   # unchanged — still runs both dev servers
```

---

## Backend Changes

### Conditional router mounting (`backend/main.py`)

Reads `TROVE_MODE` at startup (defaults to `"app"` if unset, so existing dev workflows keep working):

```python
mode = os.getenv("TROVE_MODE", "app")

# Always mounted (read-only / shared)
app.include_router(config_router)       # GET /api/config
app.include_router(i18n_router)         # GET /api/i18n/*
app.include_router(system_router)       # GET /api/system/check
app.include_router(ollama_router)       # GET/POST /api/ollama/*

# Mode-specific
if mode == "setup":
    app.include_router(setup_router)    # /api/setup/*
elif mode == "app":
    app.include_router(app_router)      # /api/app/* (includes /api/app/admin/*)
```

A `GET /api/mode` endpoint (always available) returns `{"mode": "setup"|"app"}` so the frontend can route accordingly.

### New domain: `backend/setup/`

**`router.py`** — all endpoints under `/api/setup/`:

| Endpoint | Method | Description |
|---|---|---|
| `/api/setup/status` | GET | Returns completion state of each setup step: `ollama_installed`, `models_pulled` (list of pulled tags), `admin_configured`, `service_installed` |
| `/api/setup/language` | POST | Saves `locale` to `TroveConfig` immediately (so rest of setup renders in chosen language) |
| `/api/setup/admin-credentials` | POST | Saves `admin_username` + `admin_password` to config (plaintext — replaced when full auth is built) |
| `/api/setup/install-service` | POST | Generates systemd unit file, installs it to `/etc/systemd/system/trove.service`, calls `systemctl enable --now trove` — streams SSE progress |
| `/api/setup/uninstall` | POST | Stops service, calls `systemctl disable trove`, removes unit file — streams SSE progress |
| `/api/setup/restart-service` | POST | Calls `systemctl restart trove` — streams SSE progress |
| `/api/setup/lan-url` | GET | Detects LAN IP via `socket.getfqdn()` / `socket.gethostbyname()`, returns full app URL (e.g. `http://192.168.1.42:7770`) |
| `/api/setup/ollama-version` | GET | Returns Ollama version string by running `ollama --version` |

**`service.py`** — `ServiceInstaller` Protocol + `RealServiceInstaller` + `FakeServiceInstaller` (activated by `TROVE_FAKE_SERVICE=1`). The systemd unit file content:

```ini
[Unit]
Description=Trove LLM Platform
After=network.target

[Service]
ExecStart=/path/to/trove start
Restart=on-failure
User=<current user>

[Install]
WantedBy=multi-user.target
```

The executable path is resolved at install time via `sys.executable` + the `trove` script location.

**`models.py`** — request/response Pydantic models for the setup endpoints.

### New domain: `backend/app/`

**`router.py`** — all endpoints under `/api/app/`:

- `GET /api/app/status` — confirms app mode is active (used by frontend health check)
- Admin-gated sub-router at `/api/app/admin/` — all existing mutating config endpoints move here:
  - `PUT /api/app/admin/config` — save model, num_ctx, locale (moved from `PUT /api/config`)
  - `POST /api/app/admin/build-model` — build trove_model SSE stream (moved from ollama router)
  - Future: `/api/app/admin/documents/`, `/api/app/admin/tasks/`

Auth dependency (`require_admin`) — for now, checks `Authorization: Basic` header against `admin_username`/`admin_password` from config. Returns 401 if credentials missing or wrong.

`GET /api/config` and all read-only ollama/system endpoints remain shared and unauthenticated.

### Config model additions (`backend/config/models.py`)

```python
class TroveConfig(BaseModel):
    base_model: str = "gemma4:e4b"
    num_ctx: int = Field(default=8192, ge=512, le=262144)
    locale: str = "en"
    admin_username: str = "admin"
    admin_password: str = ""  # empty = not yet configured
```

### Italian locale (`backend/i18n/locales/it.json`)

New locale file — added alongside `en.json`. Full translation of all existing keys:

```json
{
  "setup.title": "Configurazione di Trove",
  "setup.system_check": "Controllo del sistema in corso...",
  "setup.step_install": "Installa Ollama",
  "setup.step_start": "Avvia il servizio Ollama",
  "setup.step_pull": "Scarica il modello",
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

New locale keys needed across setup and manage flows will be added to both `en.json` and `it.json` as part of implementation.

---

## Frontend Changes

### Flowbite + Tailwind

Install via bun:
```bash
bun add -d tailwindcss@3 postcss autoprefixer flowbite flowbite-react
```

Use Tailwind v3 (not v4) — Flowbite's React components are tested against v3 and its `tailwind.config.js` plugin API.

`tailwind.config.js` (new) — content paths include `./src/**/*.{ts,tsx}` and `node_modules/flowbite-react/lib/**/*.js`; add `flowbite` as a plugin.
`postcss.config.js` (new) — standard Tailwind PostCSS setup.
`src/index.css` — replace custom CSS with Tailwind directives (`@tailwind base/components/utilities`).
`src/App.css` — removed entirely; per-component styling via Tailwind utilities and Flowbite React components.

### Routing by mode

`App.tsx` fetches `GET /api/mode` on load. Based on response:

- **Setup mode routes:**
  - `/` → `SetupWizard.tsx`
  - `/manage` → `ManageDashboard.tsx`
  - `*` → redirect `/`

- **App mode routes:**
  - `/` → `TaskShell.tsx`
  - `/admin` → `AdminPanel.tsx` (prompts login if not authenticated)
  - `*` → redirect `/`

### New pages

**`SetupWizard.tsx`** — replaces `Setup.tsx`. Step-based flow with a persistent step indicator at the top:

0. **Language** — dropdown of available locales (fetched from `/api/i18n/locales`); on select, calls `POST /api/setup/language` and re-fetches translations; whole page re-renders in chosen language
1. **Welcome** — system info table (RAM, disk, GPU from `/api/system/check`); plain-English description of what setup will do
2. **Install Ollama** — install button + streaming log; auto-marked complete with ✓ if already installed
3. **Choose models** — multi-select cards of viable models (filtered by RAM); "Pull selected" button pulls each in sequence with SSE progress log; at least one must be pulled to proceed
4. **Admin account** — username + password fields; calls `POST /api/setup/admin-credentials`
5. **Install service** — "Install Trove as a service" button; SSE progress; on completion redirects to `/manage`

**`ManageDashboard.tsx`** — shown after setup completes and on all return visits to setup mode:
- Optional "Setup complete!" success banner (shown only when arriving from wizard)
- Three status cards: Service (running/stopped), Ollama version, Models pulled count
- Prominent "How to access Trove" box: plain-English label + LAN URL with Copy button (from `/api/setup/lan-url`)
- Action buttons: Restart service, Update Ollama (SSE), Pull another model (opens inline model picker), Uninstall Trove

**`AdminPanel.tsx`** — replaces `Admin.tsx`. Shown at `/admin` in app mode:
- Login wall: if not authenticated, shows username/password form; on submit stores credentials in React component state (in-memory only — cleared on page refresh; full session management deferred)
- Tabbed interface (Flowbite Tabs component):
  - **Settings** — existing model picker, num_ctx slider, language selector, save + build model flow (migrated from `Admin.tsx`, endpoints updated to `/api/app/admin/*`)
  - **Documents** — placeholder tab ("Document library coming soon")
  - **Tasks** — placeholder tab ("Task management coming soon")

**`TaskShell.tsx`** — landing page for regular users in app mode:
- Trove wordmark + nav bar
- Placeholder content area ("Tasks will appear here")
- No login required

### i18n

The `useTranslation` hook and locale cache are unchanged. The language step in `SetupWizard.tsx` calls `POST /api/setup/language` with the selected locale, then calls `fetchLocale(newLocale)` and forces a re-render — all subsequent wizard text appears in the chosen language.

---

## Testing

### `tests/test_setup.py`
- Language save writes to config
- Status endpoint correctly detects each step's completion
- Admin credentials save and are retrievable
- LAN URL returns a plausible IP + port string
- Service install/uninstall call `FakeServiceInstaller` and record correct systemctl commands
- SSE streams from install/uninstall/restart yield progress lines and a `[DONE]` sentinel

### `tests/test_app.py`
- Unauthenticated request to `/api/app/admin/config` returns 401
- Authenticated request (correct Basic credentials) returns 200
- Wrong credentials return 401
- Config PUT via admin route saves and is reflected in GET

### `tests/test_cli.py`
- `trove setup` sets `TROVE_MODE=setup` and would start on 127.0.0.1:7071 (uvicorn call inspected, not actually started)
- `trove start` sets `TROVE_MODE=app` and would start on 0.0.0.0:7770

### `FakeServiceInstaller`
Same Protocol/Real/Fake pattern as `FakeOllamaService`. Activated by `TROVE_FAKE_SERVICE=1` in `.env`. Records all `systemctl` calls made during a test run; asserts can verify correct command sequence.

---

## Ports

| Mode | Default host | Default port | Configurable |
|---|---|---|---|
| Setup | 127.0.0.1 | 7071 | `--port` flag |
| App | 0.0.0.0 | 7770 | `--port` flag |

---

## Out of scope

- Full auth system (JWT, sessions, password hashing) — deferred
- Document library — deferred
- Task definition system — deferred
- Ollama version detection from install script contents — deferred (Update Ollama button exists but version comparison is not implemented yet)
