This document contains more developer-oriented instructions.

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Bun](https://bun.sh/) — JavaScript runtime (for the frontend)

### Setup from source

```bash
git clone <repo>
cd trove
uv sync --group dev
cd frontend && bun install && cd ..
```

### Running in development

```bash
# Terminal 1 — backend
uv run uvicorn backend.main:create_app_setup --reload --port 8001 --factory
# or for app mode:
uv run uvicorn backend.main:create_app_app --reload --port 8001 --factory

# Terminal 2 — frontend (proxies /api to the backend automatically)
cd frontend && bun run dev
```

The frontend is at http://localhost:5173.

To skip real Ollama and system calls (useful for UI work):

```bash
TROVE_FAKE_OLLAMA=1 TROVE_FAKE_SYSTEM=1 uv run uvicorn backend.main:create_app_app --reload --factory
```

### Tests

```bash
uv run pytest -v
```

### Production build

```bash
cd frontend && bun run build && cd ..
uv run trove start
```
