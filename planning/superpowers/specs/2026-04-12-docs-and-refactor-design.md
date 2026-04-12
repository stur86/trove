# Documentation, Diagrams, and Code Readability Pass

**Date:** 2026-04-12
**Scope:** Full code review pass (backend + frontend) for readability and encapsulation, two architectural diagrams, and a MkDocs Material documentation site (user guide + admin guide in English and Italian, developer guide in English only).

---

## Execution order

1. Code review pass — backend Python, then frontend TypeScript
2. Architectural diagrams — standalone Mermaid files
3. Documentation site — MkDocs Material setup and page content

---

## 1. Code review pass

### Principles

- **No logic changes.** This is a readability and encapsulation pass only. If a change would alter behaviour or require touching tests, it is left with a clarifying comment instead.
- **Measure over completeness on encapsulation.** Where reducing global state would entangle existing request/lifespan logic, leave it as-is.

### Backend Python

Full pass over all `.py` files under `backend/`. Priorities in order:

**a) Docstrings and inline comments**
- Every module, class, and public function must have a docstring.
- Inline comments on any non-obvious logic — state machines, workarounds, ordering constraints.
- Fill gaps; fix vague or tautological docstrings.

**b) Encapsulation and global state**
- Identify module-level globals that routers or services depend on directly:
  - `session_store` and `admin_store` in `backend/session.py` — imported directly by routers
  - `RealOllamaService._serve_process` — class-level mutable state
  - The in-process log buffer (`backend/log_buffer.py`)
- Evaluate whether each can be passed via FastAPI's dependency injection instead. Apply where it genuinely makes the code clearer and more self-contained. Skip where it would complicate lifespan management or require structural changes to the app factories.

**c) Structural oddities**
- The deferred imports at the bottom of `backend/app/router.py` (lines 164–168) are unusual — move them to the top or explain clearly why they must remain at module tail.
- The try/except deferred imports in `backend/main.py` are intentional (allow partial domain implementations to fail gracefully as 404s during development). Make this intent explicit with a comment.

### Frontend TypeScript

Full pass over all `.ts` and `.tsx` files under `frontend/src/`. Priorities:

- JSDoc on every exported function, hook, interface, and type alias.
- Inline comments on non-obvious state transitions, API call sequencing, or SSE handling logic.
- No component restructuring — documentation pass only.

---

## 2. Architectural diagrams

Two standalone Mermaid files under `docs/diagrams/`. Both are standalone-renderable (GitHub, VS Code, any Mermaid viewer) and also included in the developer docs via `pymdownx.snippets`.

### Diagram A — Network topology (`docs/diagrams/network-topology.mmd`)

Shows the physical/network layout:
- The server machine running Trove
- Setup mode bound to `127.0.0.1:7071` (localhost only)
- App mode bound to `0.0.0.0:7770` (LAN-accessible)
- The LAN/router
- Client devices connecting via browser on the LAN
- The constraint that admin access requires a browser on the server machine

### Diagram B — Module/component map (`docs/diagrams/module-map.mmd`)

Shows the application boundary and its internals:

**Inside the application boundary:**
- FastAPI app (two modes: setup / app)
- Backend domains: `config`, `i18n`, `system`, `ollama`, `tasks`, `documents`, `app`, `setup`, `session`
- The React frontend (client-side, connected to the API)

**Outside the application boundary:**
- Ollama server process (separate OS process, connected via HTTP on `127.0.0.1:TROVE_OLLAMA_PORT`)
- SQLite database (file on disk, accessed via `backend/db.py`)
- Document storage (markdown files on disk under `~/.local/share/trove/documents/`)

Gem run data flow (C) and document upload pipeline (D) are represented as labelled edges on this diagram, not as separate sub-diagrams.

---

## 3. Documentation site

### Infrastructure

- **Tool:** MkDocs Material
- **Config:** `mkdocs.yml` at repo root
- **Source:** `docs/` directory (all contents are publishable)
- **Extensions:** `pymdownx.superfences` (Mermaid rendering), `pymdownx.snippets` (`.mmd` file inclusion)
- **i18n plugin:** `en` as default language, `it` as alternate. Developer docs (`dev/`) exist only in the English build.
- **Deployment target:** GitHub Pages (future; not wired up in this pass)

### Directory layout

```
docs/
├── en/
│   ├── user/
│   │   ├── index.md          # What is Trove, what are Gems
│   │   ├── running-a-gem.md  # Filling in a form, submitting, reading output
│   │   └── media-input.md    # Attaching images or audio
│   ├── admin/
│   │   ├── index.md          # Overview of the admin panel
│   │   ├── gems.md           # Creating and managing Gems
│   │   ├── documents.md      # Document library, folders, access control
│   │   └── settings.md       # Model selection, language, network address
│   └── dev/
│       ├── index.md          # Architecture overview, diagrams (via snippets)
│       ├── setup.md          # Dev environment, task runner, fake services
│       ├── backend.md        # Domain structure, Protocol/Real/Fake pattern, adding a domain
│       └── frontend.md       # Component structure, API layer, i18n hook
├── it/
│   ├── user/                 # Italian translations of en/user/
│   └── admin/                # Italian translations of en/admin/
│   # dev/ has no Italian equivalent
└── diagrams/
    ├── network-topology.mmd
    └── module-map.mmd
```

### What stays unchanged

- `README.md` — remains as the GitHub repository landing page (admin install instructions). Not part of the mkdocs site.
- `DEVELOPMENT.md` — remains as a quick-start reference for developers cloning the repo. Its content is expanded and formalized in `docs/en/dev/setup.md`, but the file itself is kept for discoverability.

### Diagram inclusion pattern

Diagrams are included in `docs/en/dev/index.md` using the snippets extension:

````markdown
```mermaid
--8<-- "docs/diagrams/network-topology.mmd"
```
````

---

## 4. Repository housekeeping

### Move planning artifacts

`docs/superpowers/` → `planning/superpowers/`

All existing specs and plans are moved. Future specs and plans go to `planning/superpowers/specs/` and `planning/superpowers/plans/` respectively. This keeps `docs/` clean — everything in it is part of the published site.

### Update CLAUDE.md

Add a note to `CLAUDE.md` clarifying:
- `docs/` — MkDocs source, everything here is published to the docs site
- `planning/` — internal planning artifacts (specs, implementation plans); not published

---

## Out of scope

- Wiring up GitHub Pages deployment (CI/CD)
- Adding more locales beyond `en` and `it`
- Any new Trove features or behaviour changes
- Changing test files
