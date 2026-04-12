# Release & Install System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an end-to-end release pipeline: GitHub Action builds a Python wheel (with bundled frontend), publishes a GitHub Release, and provides a `install.sh` script that self-installs Trove on any Linux machine without system-level dependencies.

**Architecture:** The GitHub Action (workflow_dispatch) reads the version from `pyproject.toml`, builds the React frontend into `backend/static/`, packages the wheel (which includes `backend/static/` as package data), then creates a GitHub Release with the wheel and a version-substituted `install.sh` as assets. The install script downloads and installs a local copy of uv, creates a venv, installs the wheel, and writes a wrapper script at `~/.local/bin/trove` (or `/usr/local/bin/trove` for root) that uses the local uv binary to run Trove in the correct environment. `backend/cli.py` gains a `--frontend-dist` flag that sets `TROVE_FRONTEND_DIST`; `backend/main.py` resolves the frontend dist path from that env var, then `backend/static/` (installed wheel), then `frontend/dist/` (dev fallback).

**Tech Stack:** Python/uv, setuptools, GitHub Actions, Bash, React/Bun, `gh` CLI

---

## Files

| File | Action | Purpose |
|------|--------|---------|
| `install.sh` | Create | Install script with `__TROVE_VERSION__` placeholder |
| `.github/workflows/release.yml` | Create | GitHub Action: build → package → release |
| `pyproject.toml` | Modify | Add `backend/static/` package data |
| `.gitignore` | Modify | Ignore `backend/static/` (build output) |
| `backend/cli.py` | Modify | Add `--frontend-dist` option to both commands |
| `backend/main.py` | Modify | Replace hardcoded dist path with `_find_frontend_dist()` |

---

## Task 1: Add `backend/static/` package data and gitignore entry

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

- [ ] **Step 1: Add package-data to `pyproject.toml`**

Add this section after `[tool.setuptools.packages.find]`:

```toml
[tool.setuptools.package-data]
backend = ["static/**/*"]
```

- [ ] **Step 2: Add `backend/static/` to `.gitignore`**

Append to the `# Frontend` section:

```
backend/static/
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "build: add backend/static/ package data for bundled frontend"
```

---

## Task 2: Add `--frontend-dist` flag to CLI and refactor path resolution in `main.py`

**Files:**
- Modify: `backend/cli.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Refactor `_find_frontend_dist()` in `backend/main.py`**

Replace the existing `_frontend_dist = Path(...) / "frontend" / "dist"` block (lines 101–123) with a call to a new helper. Add the helper just before `_create_app_with_mode`:

```python
def _find_frontend_dist() -> Path | None:
    """
    Locate the compiled React frontend.

    Resolution order:
    1. TROVE_FRONTEND_DIST env var (set by CLI --frontend-dist flag)
    2. backend/static/ next to this file (installed wheel)
    3. frontend/dist/ relative to repo root (dev mode)
    """
    import os
    override = os.environ.get("TROVE_FRONTEND_DIST")
    if override:
        return Path(override)
    static = Path(__file__).parent / "static"
    if static.is_dir():
        return static
    dev = Path(__file__).parent.parent / "frontend" / "dist"
    if dev.is_dir():
        return dev
    return None
```

Then update `_create_app_with_mode` to use it — replace the old block starting at `_frontend_dist = Path(...)`:

```python
    # Serve the compiled React frontend in production.
    # NOTE: Must come after all include_router() calls — FastAPI matches
    # explicit routes first, but only if registered before the catch-all.
    _frontend_dist = _find_frontend_dist()
    if _frontend_dist is not None:
        application.mount(
            "/assets",
            StaticFiles(directory=str(_frontend_dist / "assets")),
            name="assets",
        )

        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            """SPA fallback: serve static file if it exists, else index.html.

            API paths (/api/*) are intentionally excluded — if an API route is
            not registered, FastAPI must return 404, not the SPA shell.
            """
            if full_path.startswith("api/"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            file_path = _frontend_dist / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(_frontend_dist / "index.html")
```

- [ ] **Step 2: Add `--frontend-dist` option to both CLI commands in `backend/cli.py`**

Add `Optional` to the import line and a `frontend_dist` parameter to both `setup` and `start`:

```python
from typing import Optional
```

Update the `setup` command signature and body:

```python
@cli.command()
def setup(
    host: str = typer.Option("127.0.0.1", help="Host to bind (default: localhost only)"),
    port: int = typer.Option(7071, help="Port to listen on"),
    frontend_dist: Optional[str] = typer.Option(
        None, "--frontend-dist",
        help="Path to compiled frontend dist directory (overrides auto-detection)",
    ),
) -> None:
    """
    Run Trove in setup mode.

    Setup mode binds to 127.0.0.1 — accessible only from this machine.
    No login required. Use this to install Ollama, pull models, configure
    the admin account, and install Trove as a system service.
    """
    if frontend_dist:
        os.environ["TROVE_FRONTEND_DIST"] = frontend_dist
    _set_ollama_host()
    uvicorn.run("backend.main:create_app_setup", host=host, port=port, factory=True)
```

Update the `start` command signature and body:

```python
@cli.command()
def start(
    host: str = typer.Option("0.0.0.0", help="Host to bind (default: all interfaces)"),
    port: int = typer.Option(7770, help="Port to listen on"),
    frontend_dist: Optional[str] = typer.Option(
        None, "--frontend-dist",
        help="Path to compiled frontend dist directory (overrides auto-detection)",
    ),
) -> None:
    """
    Run Trove in app mode.

    App mode binds to 0.0.0.0 — accessible from the local network.
    Regular users reach the task runner without login; admins access
    /admin with the credentials set during setup.

    Automatically starts Trove's private Ollama instance (port 11435) if
    the ollama binary is installed but the server is not yet running.
    Set TROVE_USE_GLOBAL_OLLAMA=1 in .env to use the system-wide Ollama
    instance (port 11434) instead and share already-pulled models.
    """
    if frontend_dist:
        os.environ["TROVE_FRONTEND_DIST"] = frontend_dist
    _set_ollama_host()
    if shutil.which("ollama"):
        from backend.ollama.service import ensure_ollama_running
        ensure_ollama_running()
    uvicorn.run("backend.main:create_app_app", host=host, port=port, factory=True)
```

- [ ] **Step 3: Verify existing tests still pass**

```bash
task test
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py backend/cli.py
git commit -m "feat: add --frontend-dist flag and auto-detect backend/static/ for installed wheel"
```

---

## Task 3: Write `install.sh`

**Files:**
- Create: `install.sh`

- [ ] **Step 1: Create `install.sh`**

```bash
#!/bin/bash
# Trove installer — downloads and installs Trove v__TROVE_VERSION__
# Usage: bash install.sh [--prefix /custom/path]
set -euo pipefail

VERSION="__TROVE_VERSION__"
REPO="https://github.com/stur86/trove"  # update to actual repo URL
WHEEL_URL="${REPO}/releases/download/v${VERSION}/trove-${VERSION}-py3-none-any.whl"

# ── Parse arguments ──────────────────────────────────────────────────────────
PREFIX=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix) PREFIX="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# ── Determine install directories ────────────────────────────────────────────
if [[ -n "$PREFIX" ]]; then
  INSTALL_DIR="$PREFIX"
  BIN_DIR="$PREFIX/bin"
elif [[ "$(id -u)" -eq 0 ]]; then
  INSTALL_DIR="/opt/trove"
  BIN_DIR="/usr/local/bin"
else
  INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/trove"
  BIN_DIR="$HOME/.local/bin"
fi

echo "Installing Trove ${VERSION} to ${INSTALL_DIR}"
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# ── Install uv locally ───────────────────────────────────────────────────────
UV_DIR="$INSTALL_DIR/uv"
mkdir -p "$UV_DIR"
echo "Installing uv to ${UV_DIR}..."
UV_INSTALL_DIR="$UV_DIR" curl -LsSf https://astral.sh/uv/install.sh | sh
UV="$UV_DIR/uv"

# ── Download wheel ───────────────────────────────────────────────────────────
WHEEL_PATH="$INSTALL_DIR/trove-${VERSION}.whl"
echo "Downloading Trove wheel..."
curl -LsSf "$WHEEL_URL" -o "$WHEEL_PATH"

# ── Create venv and install wheel ────────────────────────────────────────────
echo "Creating virtual environment..."
"$UV" venv "$INSTALL_DIR/.venv" --python 3.11

echo "Installing Trove..."
"$UV" pip install --python "$INSTALL_DIR/.venv/bin/python" "$WHEEL_PATH"

rm "$WHEEL_PATH"

# ── Write wrapper script ─────────────────────────────────────────────────────
cat > "$BIN_DIR/trove" <<WRAPPER
#!/bin/bash
# Trove wrapper — runs Trove using the local uv and venv.
VIRTUAL_ENV="${INSTALL_DIR}/.venv" exec "${UV}" run python -m backend.cli "\$@"
WRAPPER
chmod +x "$BIN_DIR/trove"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Trove ${VERSION} installed successfully."
echo ""
echo "Run setup:  ${BIN_DIR}/trove setup"
echo "Run app:    ${BIN_DIR}/trove start"
if [[ "$BIN_DIR" == "$HOME/.local/bin" ]]; then
  if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo ""
    echo "Note: Add ~/.local/bin to your PATH if 'trove' is not found:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
  fi
fi
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x install.sh
```

- [ ] **Step 3: Commit**

```bash
git add install.sh
git commit -m "feat: add install.sh with local uv, venv, and wrapper script"
```

---

## Task 4: Write GitHub Actions release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create the `.github/workflows/` directory and `release.yml`**

```bash
mkdir -p .github/workflows
```

Then create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  workflow_dispatch:

jobs:
  release:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/astral-sh/uv:python3.11-bookworm
    permissions:
      contents: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Read version from pyproject.toml
        id: version
        run: |
          VERSION=$(uv run python -c "import tomllib; f=open('pyproject.toml','rb'); d=tomllib.load(f); print(d['project']['version'])")
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"
          echo "Releasing version: $VERSION"

      - name: Fail if tag already exists
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          if git ls-remote --tags origin "refs/tags/v${VERSION}" | grep -q .; then
            echo "Error: tag v${VERSION} already exists. Bump the version in pyproject.toml first." >&2
            exit 1
          fi

      - name: Install Bun
        uses: oven-sh/setup-bun@v2
        with:
          bun-version: latest

      - name: Install frontend dependencies
        working-directory: frontend
        run: bun install

      - name: Build frontend
        working-directory: frontend
        run: bun run build

      - name: Copy frontend dist into backend/static/
        run: |
          rm -rf backend/static
          cp -r frontend/dist backend/static

      - name: Install Python dependencies
        run: uv sync

      - name: Build wheel
        run: uv build --wheel

      - name: Prepare install.sh with version substituted
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          sed "s/__TROVE_VERSION__/${VERSION}/g" install.sh > dist/install.sh
          chmod +x dist/install.sh

      - name: Create GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          VERSION="${{ steps.version.outputs.version }}"
          WHEEL="dist/trove-${VERSION}-py3-none-any.whl"
          gh release create "v${VERSION}" \
            --title "Trove v${VERSION}" \
            --generate-notes \
            "$WHEEL" \
            "dist/install.sh"
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add workflow_dispatch release action (build wheel + install.sh)"
```

---

## Self-Review Notes

- `backend/static/**/*` package-data glob covers all asset subdirectories (css, js, etc.) — correct.
- `_find_frontend_dist()` is called once per `_create_app_with_mode` call, which only happens once per process — no performance concern.
- The wrapper bakes `VIRTUAL_ENV` and the absolute uv path; no PATH lookup at runtime.
- `uv run` with `VIRTUAL_ENV` set uses that venv without requiring a `pyproject.toml` in the directory.
- `tomllib` is stdlib in Python 3.11+ — no extra dependency needed in the Action.
- The Action uses `uv build --wheel` (not `uv build` alone) to avoid also building a sdist, keeping the release assets clean.
- `gh release create` needs `permissions: contents: write` — included.
- `oven-sh/setup-bun@v2` is the official Bun action for GitHub Actions.
- `git ls-remote --tags origin` checks the remote, not local tags — correct guard for the CI environment.
