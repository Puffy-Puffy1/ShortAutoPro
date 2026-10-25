#!/data/data/com.termux/files/usr/bin/bash

# Compatibility entry point. Keep all installation logic in one place.
set -euo pipefail

PROJECT_DIR="${SAP_PROJECT_DIR:-$HOME/ShortAutoPro}"
export SAP_PROJECT_DIR="$PROJECT_DIR"
export SAP_BRIDGE_BRANCH="${SAP_BRIDGE_BRANCH:-termux-stable}"

INSTALLER="$PROJECT_DIR/automation/install_termux_bridge.sh"
if [ ! -f "$INSTALLER" ]; then
    printf 'ERRO: instalador canonico nao encontrado: %s\n' "$INSTALLER" >&2
    exit 10
fi

exec bash "$INSTALLER"
