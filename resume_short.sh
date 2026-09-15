#!/data/data/com.termux/files/usr/bin/bash

set -e
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
RUNTIME="$BASE/resume_short_runtime.py"

# Exporta também variáveis definidas em config.sh sem alterar o arquivo.
if [ -f "$BASE/config.sh" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$BASE/config.sh"
    set +a
fi

export SAP_PRO_EDIT="${SAP_PRO_EDIT:-1}"

if [ ! -f "$RUNTIME" ]; then
    echo "ERRO: runtime unificado de retomada não encontrado: $RUNTIME"
    exit 1
fi

exec python "$RUNTIME" "$@"
