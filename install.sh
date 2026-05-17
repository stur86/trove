#!/bin/bash
# Trove installer — fetches the latest release from GitHub and installs it.
# Usage: bash install.sh [--prefix /custom/path] [--local /path/to/trove-*.whl] [--global-ollama]
set -euo pipefail

REPO="stur86/trove"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

# ── Parse arguments ──────────────────────────────────────────────────────────
PREFIX=""
LOCAL_WHEEL=""
# Pre-seed from env var so that TROVE_USE_GLOBAL_OLLAMA=1 bash install.sh also works.
GLOBAL_OLLAMA="${TROVE_USE_GLOBAL_OLLAMA:-0}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)        PREFIX=$(realpath "$2"); shift 2 ;;
    --local)         LOCAL_WHEEL="$2"; shift 2 ;;
    --global-ollama) GLOBAL_OLLAMA=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# ── Resolve wheel source ─────────────────────────────────────────────────────
if [[ -n "$LOCAL_WHEEL" ]]; then
  # Local path provided — validate and derive version from filename.
  if [[ ! -f "$LOCAL_WHEEL" ]]; then
    echo "Error: local wheel not found: ${LOCAL_WHEEL}" >&2; exit 1
  fi
  WHEEL_FILENAME=$(basename "$LOCAL_WHEEL")
  VERSION=$(printf '%s' "$WHEEL_FILENAME" | sed 's/trove-\([^-]*\)-.*/\1/')
  if [[ -z "$VERSION" || "$VERSION" == "$WHEEL_FILENAME" ]]; then
    echo "Error: could not derive version from filename: ${WHEEL_FILENAME}" >&2; exit 1
  fi
  echo "Using local wheel: ${LOCAL_WHEEL} (version ${VERSION})"
else
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
  WHEEL_FILENAME=$(basename "$WHEEL_URL")
fi

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
curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="$UV_DIR" sh
UV="$UV_DIR/uv"

# ── Obtain wheel ─────────────────────────────────────────────────────────────
WHEEL_PATH="$INSTALL_DIR/$WHEEL_FILENAME"
if [[ -n "$LOCAL_WHEEL" ]]; then
  cp "$LOCAL_WHEEL" "$WHEEL_PATH"
else
  echo "Downloading Trove wheel..."
  curl -LsSf "$WHEEL_URL" -o "$WHEEL_PATH"
fi

# ── Create venv and install wheel ────────────────────────────────────────────
echo "Creating virtual environment..."
"$UV" venv "$INSTALL_DIR/.venv" --python 3.11

echo "Installing Trove..."
"$UV" pip install --python "$INSTALL_DIR/.venv/bin/python" "$WHEEL_PATH"

rm "$WHEEL_PATH"

# ── Write wrapper script ─────────────────────────────────────────────────────
GLOBAL_OLLAMA_EXPORT=""
if [[ "$GLOBAL_OLLAMA" == "1" ]]; then
  GLOBAL_OLLAMA_EXPORT="export TROVE_USE_GLOBAL_OLLAMA=1"
fi

cat > "$BIN_DIR/trove" <<WRAPPER
#!/bin/bash
# Trove wrapper — runs Trove using the local uv and venv.
export TROVE_INSTALL_DIR="${INSTALL_DIR}"
${GLOBAL_OLLAMA_EXPORT}
VIRTUAL_ENV="${INSTALL_DIR}/.venv" exec "${UV}" run trove "\$@"
WRAPPER
chmod +x "$BIN_DIR/trove"

# ── Write uninstall script ───────────────────────────────────────────────────
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/trove"
UNIT_FILE="$HOME/.config/systemd/user/trove.service"

cat > "$BIN_DIR/trove-uninstall" <<UNINSTALLER
#!/bin/bash
# Trove uninstaller — reverses all changes made by install.sh.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR}"
BIN_DIR="${BIN_DIR}"
UNIT_FILE="${UNIT_FILE}"
CONFIG_DIR="${CONFIG_DIR}"

echo ""
echo "WARNING: This will permanently remove Trove from your system."
echo ""
echo "The following will be deleted:"
echo "  * Install directory:  \${INSTALL_DIR}"
echo "  * Wrapper scripts:    \${BIN_DIR}/trove  and  \${BIN_DIR}/trove-uninstall"
if [[ -f "\${UNIT_FILE}" ]]; then
  echo "  * Systemd service:    \${UNIT_FILE}"
fi
echo ""
echo "Your Trove data and configuration at \${CONFIG_DIR} will NOT be removed."
echo "Delete that folder manually for a complete removal."
echo ""
read -r -p "Continue with uninstall? [y/N] " confirm
if [[ ! "\$confirm" =~ ^[Yy]\$ ]]; then
  echo "Uninstall cancelled."
  exit 0
fi

# ── Remove systemd service if present ───────────────────────────────────────
if [[ -f "\${UNIT_FILE}" ]]; then
  echo ""
  echo "Stopping and disabling Trove service..."
  systemctl --user stop trove 2>/dev/null || true
  systemctl --user disable trove 2>/dev/null || true
  rm -f "\${UNIT_FILE}"
  systemctl --user daemon-reload 2>/dev/null || true
  echo "Service removed."
fi

# ── Remove install directory ─────────────────────────────────────────────────
if [[ -d "\${INSTALL_DIR}" ]]; then
  echo ""
  echo "Removing install directory \${INSTALL_DIR}..."
  rm -rf "\${INSTALL_DIR}"
fi

# ── Remove wrapper scripts (self-deletes last) ───────────────────────────────
echo ""
echo "Removing wrapper scripts from \${BIN_DIR}..."
rm -f "\${BIN_DIR}/trove"
rm -f "\${BIN_DIR}/trove-uninstall"

echo ""
echo "Trove has been uninstalled."
echo ""
echo "Your configuration and data at \${CONFIG_DIR} were not removed."
echo "To delete them completely, run:"
echo "  rm -rf \"\${CONFIG_DIR}\""
UNINSTALLER
chmod +x "$BIN_DIR/trove-uninstall"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Trove ${VERSION} installed successfully."
echo ""
echo "Run setup:    ${BIN_DIR}/trove setup"
echo "Run app:      ${BIN_DIR}/trove start"
echo "Uninstall:    ${BIN_DIR}/trove-uninstall"
if [[ "$BIN_DIR" == "$HOME/.local/bin" ]]; then
  if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo ""
    echo "Note: Add ~/.local/bin to your PATH if 'trove' is not found:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
  fi
fi
