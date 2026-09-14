#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"
COOLDOWN="${SHORT_BATCH_COOLDOWN:-20}"

if ! [[ "$COOLDOWN" =~ ^[0-9]+$ ]]; then COOLDOWN=20; fi
COOLDOWN=$((COOLDOWN))
if [ "$COOLDOWN" -lt 10 ]; then COOLDOWN=10; fi
if [ "$COOLDOWN" -gt 120 ]; then COOLDOWN=120; fi

QTD="${1:-${SHORT_LOTE:-3}}"
if ! [[ "$QTD" =~ ^[0-9]+$ ]]; then
    echo "ERRO: quantidade inválida."
    echo "Exemplo: ~/ShortAutoPro/batch_queue.sh 3"
    exit 1
fi
QTD=$((QTD))
if [ "$QTD" -lt 1 ]; then QTD=1; fi
if [ "$QTD" -gt 10 ]; then QTD=10; fi

if [ -f "$BASE/config.sh" ]; then
    # shellcheck disable=SC1091
    source "$BASE/config.sh"
else
    echo "ERRO: config.sh não encontrado."
    exit 1
fi

BATCH_ID="$(date +%F_%H%M%S)_$$"
LOG_DIR="$BASE/logs/lotes"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/lote_${BATCH_ID}.log"
exec > >(tee -a "$LOG") 2>&1

echo
echo "======================================"
echo " SHORTAUTO PRO - BATCH QUEUE 2.0"
echo "======================================"
echo
echo "Lote: $BATCH_ID"
echo "Quantidade: $QTD"
echo "Início: $(date)"
echo "Log: $LOG"
echo

SUCESSOS=0
FALHAS=0
declare -a IDS_OK=()
declare -a IDS_ERRO=()

manifest_id_valido() {
    local arquivo="$1"
    local esperado="$2"
    [ -f "$arquivo" ] || return 1

    python - "$arquivo" "$esperado" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
esperado = sys.argv[2]
try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)

if not isinstance(data, dict):
    raise SystemExit(1)

short_id = str(data.get("short_id", "")).strip()
status = str(data.get("status", "")).strip()

if short_id != esperado or status != "QUALITY_PASS":
    raise SystemExit(1)

print(short_id)
PY
}

for ((i=1; i<=QTD; i++)); do
    echo
echo
    echo "######################################"
    echo " SHORT $i/$QTD"
    echo "######################################"
    echo

    # O ID é definido pelo lote e preservado por gerar_short.sh.
    # Assim não dependemos de relógio por minuto nem de descobrir o
    # manifest "mais recente" entre arquivos de outras execuções.
    SHORT_ID="${BATCH_ID}_$(printf '%02d' "$i")"
    export SHORT_ID
    MANIFEST_ESPERADO="$BASE/manifests/${SHORT_ID}.json"

    INICIO="$(date +%s)"

    if "$BASE/gerar_short.sh"; then
        FIM="$(date +%s)"
        TEMPO="$((FIM - INICIO))"
        ID_OK="$(manifest_id_valido "$MANIFEST_ESPERADO" "$SHORT_ID" 2>/dev/null || true)"

        if [ -z "$ID_OK" ]; then
            FALHAS=$((FALHAS + 1))
            IDS_ERRO+=("$SHORT_ID:manifest_invalido")
            echo
            echo "SHORT $i: FALHOU"
            echo "Motivo: manifest esperado ausente, inválido ou sem QUALITY_PASS."
            echo "Manifest: $MANIFEST_ESPERADO"
            echo "Tempo: ${TEMPO}s"
        else
            SUCESSOS=$((SUCESSOS + 1))
            IDS_OK+=("$ID_OK")
            echo
            echo "SHORT $i: OK"
            echo "ID: $ID_OK"
            echo "Tempo: ${TEMPO}s"
        fi
    else
        CODIGO=$?
        FIM="$(date +%s)"
        TEMPO="$((FIM - INICIO))"
        FALHAS=$((FALHAS + 1))
        IDS_ERRO+=("$SHORT_ID:exit_$CODIGO")
        echo
        echo "SHORT $i: FALHOU"
        echo "ID: $SHORT_ID"
        echo "Código: $CODIGO"
        echo "Tempo: ${TEMPO}s"
        echo "O lote continuará para registrar todas as falhas."
    fi

    unset SHORT_ID

    if [ "$i" -lt "$QTD" ]; then
        echo
        echo "Cooldown das APIs: ${COOLDOWN}s..."
        sleep "$COOLDOWN"
    fi
done

echo
echo
echo "======================================"
echo " BATCH QUEUE FINALIZADA"
echo "======================================"
echo "Quantidade solicitada: $QTD"
echo "Sucessos: $SUCESSOS"
echo "Falhas: $FALHAS"
echo

if [ "${#IDS_OK[@]}" -gt 0 ]; then
    echo "SHORTS CRIADOS:"
    for ID in "${IDS_OK[@]}"; do echo "  OK  $ID"; done
    echo
fi

if [ "${#IDS_ERRO[@]}" -gt 0 ]; then
    echo "FALHAS:"
    for ID in "${IDS_ERRO[@]}"; do echo "  ERRO  $ID"; done
    echo
fi

echo "Log do lote:"
echo "$LOG"
echo "Fim: $(date)"
echo "======================================"

# Um lote parcial não é sucesso completo. Os Shorts produzidos continuam
# preservados, mas o chamador recebe falha para não mascarar problemas.
if [ "$FALHAS" -eq 0 ] && [ "$SUCESSOS" -eq "$QTD" ]; then
    exit 0
fi

exit 1
