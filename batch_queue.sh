#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
QTD="${1:-${SHORT_LOTE:-3}}"
exec python "$BASE/batch_runtime.py" run "$QTD"
