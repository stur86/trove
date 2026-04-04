# trove

![](banner.png)

A powerful, simple, user-friendly local agentic framework to help communities draw the best out of the power of local AI and overcome the digital gap.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Bun](https://bun.sh/) — JavaScript runtime (for building the frontend)

## Installation

```bash
git clone <repo>
cd trove
uv sync --group dev
cd frontend && bun install && cd ..
```

## First-time setup

Run the setup wizard. It opens on localhost only — nobody else on the network can reach it.

```bash
uv run trove setup
```

Then open **http://127.0.0.1:7071** in a browser. The wizard walks you through six steps:

1. **Language** — choose the UI language (saved as the default for the main app too)
2. **Welcome** — confirms your hardware and what Trove will install
3. **Install Ollama** — downloads and installs the AI runtime (skipped if already present)
4. **Choose models** — pick one or more Gemma 4 models to download; only models your machine can run are shown
5. **Admin account** — set a username and password for the admin panel
6. **Install service** — registers Trove as a systemd user service so it starts automatically on login

After step 6 you land on the **management dashboard**, which shows the LAN address to hand to your users.

## Starting Trove manually

If you skipped the service install step, or want to run Trove without it:

```bash
uv run trove start
```

This binds to `0.0.0.0:7770` — reachable from any device on the local network. Users open that address in any browser; no app to install.

## Returning to the management dashboard

Run setup mode again at any time:

```bash
uv run trove setup
```

Steps that are already complete are skipped automatically. From the dashboard you can restart the service, update Ollama, download more models, or uninstall.

## Service management

If you installed the systemd service during setup, use standard user-level systemctl commands:

```bash
systemctl --user status trove
systemctl --user restart trove
systemctl --user stop trove
```

The service runs under your user account. To keep it running after you log out (useful on a headless server):

```bash
loginctl enable-linger $USER   # one-time; requires sudo
```

## Development

Run the backend and frontend dev servers separately:

```bash
# Terminal 1 — backend
uv run uvicorn backend.main:app --reload --port 8001

# Terminal 2 — frontend (proxies /api to the backend automatically)
cd frontend && bun run dev
```

The frontend is at http://localhost:5173.

To run in a specific mode during development, set `TROVE_MODE`:

```bash
TROVE_MODE=setup uv run uvicorn backend.main:app --reload --port 8001
TROVE_MODE=app   uv run uvicorn backend.main:app --reload --port 8001
```

To skip real Ollama and system calls entirely (useful for UI work):

```bash
TROVE_FAKE_OLLAMA=1 TROVE_FAKE_SYSTEM=1 TROVE_FAKE_SERVICE=1 \
  uv run uvicorn backend.main:app --reload
```

## Tests

```bash
uv run pytest -v
```

## Production build

Build the frontend into `frontend/dist/`, then start — the backend serves the compiled assets directly:

```bash
cd frontend && bun run build && cd ..
uv run trove start
```