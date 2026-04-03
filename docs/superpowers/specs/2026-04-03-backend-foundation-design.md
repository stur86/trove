# Trove — Backend Foundation Design

**Date:** 2026-04-03
**Scope:** Backend skeleton, Ollama integration, configuration system, i18n, frontend scaffold, build system

---

## 1. Project Structure

Monorepo with two top-level packages: `backend/` (Python/FastAPI) and `frontend/` (Bun/React). Feature-grouped backend domains, each owning its router, service logic, and Pydantic models.

```
trove/
├── backend/
│   ├── main.py                  # FastAPI app, mounts all routers
│   ├── ollama/
│   │   ├── router.py            # /api/ollama/* endpoints
│   │   └── service.py           # install, model pull, Modelfile generation
│   ├── config/
│   │   ├── router.py            # /api/config/* endpoints
│   │   ├── service.py           # read/write settings, trigger model rebuild
│   │   └── models.py            # Pydantic config schema
│   ├── system/
│   │   ├── router.py            # /api/system/* endpoints
│   │   └── service.py           # RAM/disk/GPU checks
│   └── i18n/
│       ├── loader.py            # loads locale JSON files
│       └── locales/
│           ├── en.json
│           └── ...
├── frontend/
│   ├── package.json
│   ├── bunfig.toml
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── api/                 # typed fetch wrappers per backend domain
│       ├── i18n/                # locale loading + useTranslation hook
│       ├── pages/
│       │   ├── Setup.tsx        # Ollama install button, system check
│       │   └── Admin.tsx        # config panel (model picker, num_ctx)
│       └── components/
├── pyproject.toml               # taskipy tasks + uv dependencies
└── docs/
```

**Persistent config:** `~/.config/trove/` (XDG-compliant, resolved via `$XDG_CONFIG_HOME`):
```
~/.config/trove/
├── config.json      # persisted admin settings
└── Modelfile        # generated from config, used by ollama create
```

---

## 2. Ollama Integration

### Model options

| Ollama tag | Effective params | Context window max | Min RAM | Audio input |
|---|---|---|---|---|
| `gemma4:e2b` | 2.3B | 128K | ~4GB | Yes |
| `gemma4:e4b` | 4.5B | 128K | ~6GB | Yes |
| `gemma4:26b` | 4B activated (MoE) | 256K | ~10GB | No |
| `gemma4:31b` | 31B dense | 256K | ~20GB | No |

All models support image input. Audio is supported on E2B and E4B only. No video support.

The admin panel greys out models the system's RAM cannot support. The `num_ctx` slider is capped at the selected model's maximum.

### API endpoints

- `GET /api/ollama/status` — is Ollama installed, is the service running, does `trove_model` exist
- `POST /api/ollama/install` — runs the official Linux install script, streams progress via SSE
- `POST /api/ollama/pull` — pulls the configured base model, streamed via SSE
- `POST /api/ollama/build` — writes Modelfile and runs `ollama create trove_model`

### Modelfile

Generated from config and written to `~/.config/trove/Modelfile`:

```
FROM <base_model>
PARAMETER num_ctx <num_ctx>
```

Rebuilt automatically whenever `base_model` or `num_ctx` changes in config.

### Install script

Uses the official Ollama install script:
```
curl -fsSL https://ollama.com/install.sh | sh
```

Output is streamed back to the frontend via Server-Sent Events so the admin sees live progress rather than a spinner.

---

## 3. System Check

`GET /api/system/check` returns:

- Available RAM and which Gemma 4 model tiers are viable
- Free disk space
- GPU presence and VRAM (via `nvidia-smi` or ROCm; gracefully absent if neither)
- Whether Ollama service is active

Used by the admin panel to guide model selection and surface hardware limitations early.

---

## 4. Configuration

### Schema (`~/.config/trove/config.json`)

```json
{
  "base_model": "gemma4:e4b",
  "num_ctx": 8192,
  "locale": "en"
}
```

### API endpoints

- `GET /api/config` — read current config
- `PUT /api/config` — update config; triggers Modelfile regeneration and `ollama create trove_model` if model settings changed

Config is loaded at startup; defaults are applied if the file doesn't exist yet.

---

## 5. i18n

Locale files are JSON key-value pairs in `backend/i18n/locales/`. Example:

```json
{
  "setup.install_button": "Install Ollama",
  "setup.checking_system": "Checking your system...",
  "config.base_model": "Base model"
}
```

- `GET /api/i18n/{locale}` — returns the full locale file
- Frontend fetches once on load, caches for the session
- Fallback is always `en`
- Adding a new locale = dropping a new JSON file, no code changes

Locale is a server-wide setting (one institution, one language). Per-user locale is a future extension.

Locale file translation is done offline with a cloud LLM — not at runtime by the local model.

---

## 6. Frontend Scaffold

Bun + React + TypeScript, built with Vite. In production, built to static files and served by FastAPI via `StaticFiles` — single process, single port on the LAN.

Initial pages:
- **Setup** — system check results, "Install Ollama" button, model pull progress
- **Admin** — model picker (with RAM-based availability), `num_ctx` slider, locale selector

---

## 7. Build System (taskipy)

Defined in `pyproject.toml`:

```toml
[tool.taskipy.tasks]
dev-backend  = "uvicorn backend.main:app --reload"
dev-frontend = "cd frontend && bun run dev"
dev          = "task dev-backend & task dev-frontend"
build        = "cd frontend && bun run build"
start        = "task build && uvicorn backend.main:app"
install-deps = "uv sync && cd frontend && bun install"
```

- `task dev` — runs backend and frontend in parallel during development
- `task start` — production: builds frontend, launches single FastAPI server
- `task install-deps` — one-time setup after cloning

---

## Out of scope for this iteration

- Auth / user accounts
- Document library
- Task definition system
- Any Pydantic AI agentic workflows
