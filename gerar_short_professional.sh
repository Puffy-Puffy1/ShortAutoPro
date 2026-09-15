#!/data/data/com.termux/files/usr/bin/bash
set -e
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
RUNTIME="$BASE/professional_pipeline_runtime.py"

if [ ! -f "$RUNTIME" ]; then
    echo "ERRO: professional_pipeline_runtime.py não encontrado."
    exit 1
fi

exec python "$RUNTIME"
