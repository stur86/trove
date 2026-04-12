# Developer overview

Trove is a local AI platform for non-technical users. It wraps Ollama (specifically Gemma 4 models) in a no-code task runner with a browser-based UI.

## High-level architecture

```
Browser (React SPA)  ←→  FastAPI backend  ←→  Ollama server
                               ↕
                     SQLite (tasks + documents)
                     Filesystem (~/.local/share/trove/)
                     Config (~/.config/trove/)
```

The backend runs in one of two exclusive modes:

- **Setup mode** (`trove setup`, port 7071, localhost only) — a step-by-step wizard for first-time configuration.
- **App mode** (`trove start`, port 7770, all interfaces) — the daily-use task runner.

See the [architectural diagrams](../diagrams/module-map.mmd) for a full module map.

## Technology choices

| Layer | Choice | Why |
|---|---|---|
| Model runtime | Ollama | Automated install, pull, and hot-reload; manages model lifecycle |
| Backend | FastAPI + Python | Async, typed, easy SSE support |
| Agentic workflows | Pydantic AI | Typed tool calls, streaming, minimal abstraction |
| Document conversion | Markitdown | Converts PDF/DOCX/etc. to Markdown; no external services |
| Frontend | React + Vite + Bun | Fast build, TypeScript, modern tooling |
| UI components | Flowbite React | Consistent, accessible Tailwind-based components |

## Key conventions

- **Protocol / Real / Fake pattern** — every external service (Ollama, system checks, service installer) has a `@runtime_checkable Protocol`, a `RealXxxService`, and a `FakeXxxService`. The factory function `get_xxx_service()` chooses which to return based on `TROVE_FAKE_*` environment variables, making the full stack testable without Ollama or root access.
- **TDD** — tests are written before implementation. Run with `task test`.
- **XDG Base Directory Specification** — config at `$XDG_CONFIG_HOME/trove/` (default `~/.config/trove/`), data at `$XDG_DATA_HOME/trove/` (default `~/.local/share/trove/`).
- **Session tokens** — every browser client receives a short-lived `X-Trove-Session` token on first load. All API calls must include it. Admin operations additionally require an admin cookie obtained by logging in.

## Next steps

- [Setup & installation](setup.md)
- [Backend reference](backend.md)
- [Frontend reference](frontend.md)
