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

export SHORT_ID
cd "$BASE"

LOCK_ROOT="$BASE/.locks"
mkdir -p "$LOCK_ROOT"
exec 8>"$LOCK_ROOT/finalize_short.lock"
if command -v flock >/dev/null 2>&1; then
    if ! flock -n 8; then
        echo "ERRO: outra finalização já está em andamento."
        exit 75
    fi
fi

if [ -f "$BASE/config.sh" ]; then
    # shellcheck disable=SC1091
    source "$BASE/config.sh"
else
    echo "ERRO: config.sh não encontrado."
    exit 1
fi

FINAL="$BASE/videos/short_v6_${SHORT_ID}.mp4"
if [ ! -s "$FINAL" ]; then
    echo "ERRO: vídeo final ausente ou vazio: $FINAL"
    exit 1
fi

run_py() {
    local label="$1"
    local file="$2"
    shift 2
    echo
    echo "--------------------------------------"
    echo "$label"
    echo "--------------------------------------"
    python "$BASE/$file" "$@"
}

echo
echo "======================================"
echo " SHORTAUTOPRO - FINALIZAÇÃO SEGURA"
echo "======================================"
echo "ID: $SHORT_ID"
echo "Vídeo: $FINAL"

run_py "REPARANDO/VALIDANDO HOOK" "hook_runtime.py" --repair-only
run_py "QUALITY GATE" "quality_check.py"
run_py "PUBLISH PACK" "publish_pack.py"
run_py "SOURCE & ATTRIBUTION LEDGER" "source_ledger.py"
run_py "PUBLISH INTEGRITY GATE" "publish_integrity_gate.py"
run_py "PRODUCTION MANIFEST" "production_manifest.py"
run_py "FINAL QUALITY GATE" "final_quality.py"
run_py "REGISTRANDO ASSUNTO" "register_topic.py"

DOWNLOADS="$HOME/storage/shared/Download"
DESTINO="$FINAL"
if [ -d "$DOWNLOADS" ]; then
    CANDIDATO="$DOWNLOADS/ShortAutoPro_${SHORT_ID}.mp4"
    if cp "$FINAL" "$CANDIDATO" && [ -s "$CANDIDATO" ]; then
        DESTINO="$CANDIDATO"
    else
        echo "AVISO: falha ao copiar para Downloads; vídeo preservado em $FINAL"
    fi
fi

echo
echo "======================================"
echo " FINALIZAÇÃO CONCLUÍDA"
echo "======================================"
echo "ID: $SHORT_ID"
echo "STATUS: QUALITY PASS"
echo "VÍDEO: $DESTINO"
