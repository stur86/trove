#!/bin/bash
# Trove installer — downloads and installs Trove v__TROVE_VERSION__
# Usage: bash install.sh [--prefix /custom/path]
set -euo pipefail

VERSION="__TROVE_VERSION__"
REPO="https://github.com/stur86/trove"
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
