#!/data/data/com.termux/files/usr/bin/bash

set -euo pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
SHORT_ID="${1:-${SHORT_ID:-}}"

if [ -z "$SHORT_ID" ]; then
    echo "Uso: finalize_short.sh <SHORT_ID>"
    exit 2
fi

if ! [[ "$SHORT_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "ERRO: SHORT_ID inválido."
    exit 2
fi

if [ ! -f "$BASE/main.py" ]; then
    echo "ERRO: main.py ausente em $BASE"
    exit 1
fi

export SHORTAUTOPRO_BASE="$BASE"
export SHORT_ID
cd "$BASE"

echo
echo "======================================"
echo " SHORTAUTOPRO - FINALIZAÇÃO 3.0"
echo "======================================"
echo "ID: $SHORT_ID"
echo "Entrada canônica: main.py resume"
echo

# A finalização não mantém um segundo pipeline. O runtime de resume identifica
# o último checkpoint válido e executa Audio Finalizer, Visual QA, Quality,
# Integrity, Manifest e Release Gate conforme necessário.
exec python "$BASE/main.py" resume --short-id "$SHORT_ID"
