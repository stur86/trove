# Trove

Local LLM platform for non-technical users powered by Gemma 4, built for resource-constrained institutions (schools, care homes, prisons). Competition submission for the Ollama prize.

## Project vision

**The core unit is a Task** — a single prompt template with structured inputs, optional document access, and a defined output format. No iteration, no freeform chat. Designed for short context windows and non-technical users.

Key principles:
- **No-code**: admins define tasks via a form UI, not code. Jinja-style `{{ variable }}` for text fields, checkboxes for image/audio input
- **Multimodal**: all Gemma 4 models support image input; E2B and E4B also support audio
- **Document library**: documents uploaded → converted to markdown (Markitdown) → stored with AI-generated one-liner descriptions. Folder-based access control per task. Three access tiers: always-visible / on-request (fetched via tool call) / no-access. No vector store — the model reasons from metadata
- **Server-client on LAN**: one server, all devices connect via browser. Fixed IP, then just works
- **Translation**: locale JSON files only — no runtime translation by the local model. Cloud LLM translates locale files offline

## Tech stack (decided)

| Layer | Choice |
|---|---|
| Model runtime | Ollama (automated setup) |
| Backend | Python + FastAPI |
| Agentic workflows | Pydantic AI |
| Document conversion | Markitdown |
| Frontend | Bun + React + Vite (TypeScript) |
| Task runner | taskipy (in pyproject.toml) |
| Python deps | uv |

## Project structure

```
trove/
├── backend/
│   ├── main.py                  # FastAPI app, mounts all routers
│   ├── config/                  # Server configuration (model, context window, locale)
│   ├── i18n/                    # Locale file loading and API
│   ├── system/                  # Hardware checks (RAM, disk, GPU)
│   └── ollama/                  # Ollama install/pull/build SSE, status, Modelfile generation
├── frontend/                    # Bun/React/Vite app
│   ├── src/
│   │   ├── api/                 # Typed API clients (config, system, ollama)
│   │   ├── i18n/                # useTranslation hook, locale cache
│   │   └── pages/               # Setup.tsx, Admin.tsx
├── tests/                       # pytest tests, one file per domain
├── docs/
│   └── superpowers/
│       ├── specs/               # Design documents
│       └── plans/               # Implementation plans
├── pyproject.toml               # uv deps + taskipy tasks
└── uv.lock
```

**Runtime config** (not in repo): `~/.config/trove/config.json` and `~/.config/trove/Modelfile`

## Gemma 4 model catalogue

| Ollama tag | Effective params | Context max | Min RAM | Audio |
|---|---|---|---|---|
| `gemma4:e2b` | 2.3B | 128K | ~4 GB | ✓ |
| `gemma4:e4b` | 4.5B | 128K | ~6 GB | ✓ |
| `gemma4:26b` | 4B activated (MoE) | 256K | ~10 GB | ✗ |
| `gemma4:31b` | 31B dense | 256K | ~20 GB | ✗ |

The active model is always `trove_model` — a custom Ollama model derived from the chosen base via a generated Modelfile (`FROM <base> / PARAMETER num_ctx <n>`).

## Task runner (taskipy)

```bash
task dev-backend   # uvicorn backend.main:app --reload
task dev-frontend  # cd frontend && bun run dev
task build         # cd frontend && bun run build
task start         # build + uvicorn (production, serves frontend as static files)
task install-deps  # uv sync --extra dev && cd frontend && bun install
task test          # pytest -v
```

## Development conventions

- **TDD**: write failing tests first, implement, verify passing
- **Docstrings**: every Python module, class, and function. Every exported TypeScript function, interface, and hook (JSDoc)
- **Inline comments**: on any non-obvious logic
- **Feature-grouped**: each backend domain owns its `router.py`, `service.py`, and `models.py`
- **Protocol/Real/Fake pattern**: services use `@runtime_checkable Protocol` + `RealXxxService` + `FakeXxxService` + `get_xxx_service()` FastAPI dependency factory. Activated by env flags (`TROVE_FAKE_OLLAMA=1`, `TROVE_FAKE_SYSTEM=1`) in `.env` (gitignored)
- **XDG spec**: config lives at `$XDG_CONFIG_HOME/trove/` (default `~/.config/trove/`)
- **Frontend styling**: use Flowbite React components for all layout, forms, and UI elements. Avoid custom Tailwind classes except where Flowbite has no equivalent. The only truly custom visual element is the `GemIcon` SVG.

## What's built

- [x] Project scaffold (pyproject.toml, FastAPI skeleton, test infrastructure)
- [x] Config domain (`/api/config` GET+PUT, XDG persistence)
- [x] i18n domain (`/api/i18n/{locale}`, locale file loading with en fallback)
- [x] System check domain (`/api/system/check` — RAM, disk, GPU, viable models)
- [x] Ollama domain (install/pull/build via SSE, status, Modelfile generation; FakeOllamaService for dev)
- [x] Frontend scaffold (Bun/React/Vite, routing, API proxy)
- [x] Frontend API layer + i18n hook (`useTranslation`, locale cache)
- [x] Setup page (hardware table, phase-based install flow, SSE log streaming)
- [x] Admin page (model picker, num_ctx slider, language selector)
- [x] Production build (FastAPI serves `frontend/dist/` as static files; dev mode unaffected)
- [ ] Document library (upload, Markitdown conversion, folder structure, access tiers)
- [ ] Task definition system (Jinja templates, structured inputs, tool toggles)
- [ ] Auth (username/password, admin-created accounts)
- [ ] Pydantic AI agentic workflows
