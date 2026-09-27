#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail
BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
# Compatibility wrapper: all batch semantics live in batch_runtime.py.
exec python "$BASE/batch_runtime.py" "$@"
