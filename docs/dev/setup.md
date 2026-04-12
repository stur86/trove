# Setup & installation

## Prerequisites

- Linux (Ubuntu 22.04+ recommended)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- [Bun](https://bun.sh/) (JavaScript runtime and bundler)
- Ollama installed and running (or `TROVE_FAKE_OLLAMA=1` for dev without a GPU)

## Clone and install

```bash
git clone https://github.com/simone-sturniolo/trove.git
cd trove
task install-deps   # uv sync --group dev && cd frontend && bun install
```

## Development

Run the backend and frontend concurrently:

```bash
task dev            # starts both servers via scripts/dev.sh
```

Or start them separately:

```bash
task dev-backend    # uvicorn on port 8001, auto-reload
task dev-frontend   # Vite on port 5173, proxies /api/ to port 8001
```

For frontend-only work with no backend:

```bash
task dev-mock       # Vite with VITE_MOCK_API=1; all API calls use mock data
```

## Environment variables

Create a `.env` file in the repo root (gitignored) to control behaviour:

| Variable | Default | Effect |
|---|---|---|
| `TROVE_FAKE_OLLAMA` | — | `1` → use FakeOllamaService (no real Ollama needed) |
| `TROVE_FAKE_SYSTEM` | — | `1` → use FakeSystemService (skip hardware checks) |
| `TROVE_FAKE_SERVICE` | — | `1` → use FakeServiceInstaller (skip systemd operations) |
| `TROVE_CONFIG_DIR` | `~/.config/trove` | Override config directory |
| `TROVE_DATA_DIR` | `~/.local/share/trove` | Override data directory |

## Running tests

```bash
task test           # pytest -v
```

All tests use fake services and an in-memory/temp-directory config, so no Ollama installation is needed to run the suite.

## Production build

```bash
task build          # compiles frontend into frontend/dist/
trove start         # serves frontend/dist/ as static files + FastAPI on port 7770
```

## First-time setup wizard

```bash
trove setup         # starts the setup wizard on localhost:7071
```

Walk through the six steps: language, hardware check, Ollama install, model download, admin credentials, service installation. After the final step, Trove installs itself as a systemd service and starts automatically on boot.

## Uninstalling

```bash
trove setup         # re-run setup
# click Uninstall on the management dashboard
```

Or manually: `systemctl --user stop trove && systemctl --user disable trove`
