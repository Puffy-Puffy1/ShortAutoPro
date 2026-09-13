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

BATCH_ID="$(date +%F_%H%M%S)"
LOG_DIR="$BASE/logs/lotes"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/lote_${BATCH_ID}.log"
exec > >(tee -a "$LOG") 2>&1

echo
echo "======================================"
echo " SHORTAUTO PRO - BATCH QUEUE 1.9"
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
ULTIMO_MINUTO=""

manifest_mais_recente() {
    find "$BASE/manifests" -maxdepth 1 -type f -name '*.json' ! -name '*_quality.json' -print0 2>/dev/null \
        | xargs -0 -r ls -1t 2>/dev/null \
        | head -1
}

manifest_id_valido() {
    local arquivo="$1"
    [ -n "$arquivo" ] || return 1
    [ -f "$arquivo" ] || return 1
    python - "$arquivo" <<'PY'
import json
import sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)
if not isinstance(data, dict):
    raise SystemExit(1)
short_id = str(data.get("short_id", "")).strip()
status = str(data.get("status", "")).strip()
if not short_id or status != "QUALITY_PASS":
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

    if [ -n "$ULTIMO_MINUTO" ]; then
        while [ "$(date +%Y%m%d%H%M)" = "$ULTIMO_MINUTO" ]; do
            sleep 1
        done
    fi

    unset SHORT_ID
    ULTIMO_MINUTO="$(date +%Y%m%d%H%M)"
    MANIFEST_ANTES="$(manifest_mais_recente)"
    INICIO=$(date +%s)

    if "$BASE/gerar_short.sh"; then
        FIM=$(date +%s)
        TEMPO=$((FIM - INICIO))
        MANIFEST_DEPOIS="$(manifest_mais_recente)"

        if [ -z "$MANIFEST_DEPOIS" ] || [ "$MANIFEST_DEPOIS" = "$MANIFEST_ANTES" ]; then
            FALHAS=$((FALHAS + 1))
            IDS_ERRO+=("manifest_ausente")
            echo
            echo "SHORT $i: FALHOU"
            echo "Motivo: nenhum novo manifest QUALITY_PASS foi produzido."
            echo "Tempo: ${TEMPO}s"
        else
            ID_OK="$(manifest_id_valido "$MANIFEST_DEPOIS" 2>/dev/null || true)"
            if [ -z "$ID_OK" ]; then
                FALHAS=$((FALHAS + 1))
                IDS_ERRO+=("manifest_invalido")
                echo
                echo "SHORT $i: FALHOU"
                echo "Motivo: manifest final inválido ou sem QUALITY_PASS."
                echo "Tempo: ${TEMPO}s"
            else
                SUCESSOS=$((SUCESSOS + 1))
                IDS_OK+=("$ID_OK")
                echo
                echo "SHORT $i: OK"
                echo "ID: $ID_OK"
                echo "Tempo: ${TEMPO}s"
            fi
        fi
    else
        CODIGO=$?
        FIM=$(date +%s)
        TEMPO=$((FIM - INICIO))
        FALHAS=$((FALHAS + 1))
        ID_ERRO="$(date +%F_%H%M%S)"
        IDS_ERRO+=("$ID_ERRO")
        echo
        echo "SHORT $i: FALHOU"
        echo "Código: $CODIGO"
        echo "Tempo: ${TEMPO}s"
        echo
        echo "O lote continuará."
    fi

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
echo
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
echo
echo "Fim: $(date)"
echo "======================================"

if [ "$SUCESSOS" -gt 0 ]; then exit 0; fi
exit 1
