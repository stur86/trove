#!/bin/bash
# Trove installer — fetches the latest release from GitHub and installs it.
# Usage: bash install.sh [--prefix /custom/path]
set -euo pipefail

REPO="stur86/trove"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

# Fetch the latest release metadata and extract the wheel download URL.
# Uses only curl and sed — no jq required.
echo "Fetching latest Trove release..."
RELEASE_JSON=$(curl -sf "$API_URL") || {
  echo "Error: could not reach GitHub API at ${API_URL}" >&2; exit 1
}

WHEEL_URL=$(printf '%s' "$RELEASE_JSON" \
  | grep '"browser_download_url"' \
  | grep '\.whl"' \
  | sed 's/.*"browser_download_url": "\(.*\)"/\1/')

if [[ -z "$WHEEL_URL" ]]; then
  echo "Error: no .whl asset found in the latest release." >&2; exit 1
fi

# Derive the version from the wheel filename (trove-X.Y.Z-py3-none-any.whl).
VERSION=$(printf '%s' "$WHEEL_URL" | sed 's|.*/trove-\([^-]*\)-.*|\1|')

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
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$UV_DIR" sh
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
