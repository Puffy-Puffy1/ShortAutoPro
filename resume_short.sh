#!/data/data/com.termux/files/usr/bin/bash

set -e
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
RUNTIME="$BASE/resume_short_runtime.py"

if [ ! -f "$RUNTIME" ]; then
    echo "ERRO: resume_short_runtime.py não encontrado."
    exit 1
fi

# Exporta também variáveis definidas em config.sh sem alterar o arquivo.
if [ -f "$BASE/config.sh" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$BASE/config.sh"
    set +a
fi

exec python "$RUNTIME" "$@"
