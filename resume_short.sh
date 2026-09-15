#!/data/data/com.termux/files/usr/bin/bash

set -e
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
STANDARD_RUNTIME="$BASE/resume_short_runtime.py"
PRO_RUNTIME="$BASE/resume_short_professional_runtime.py"

# Exporta também variáveis definidas em config.sh sem alterar o arquivo.
if [ -f "$BASE/config.sh" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$BASE/config.sh"
    set +a
fi

export SAP_PRO_EDIT="${SAP_PRO_EDIT:-1}"

if [ "$SAP_PRO_EDIT" = "1" ]; then
    RUNTIME="$PRO_RUNTIME"
else
    RUNTIME="$STANDARD_RUNTIME"
fi

if [ ! -f "$RUNTIME" ]; then
    echo "ERRO: runtime de retomada não encontrado: $RUNTIME"
    exit 1
fi

exec python "$RUNTIME" "$@"
