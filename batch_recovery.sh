#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail
BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
exec python "$BASE/batch_runtime.py" "$@"
