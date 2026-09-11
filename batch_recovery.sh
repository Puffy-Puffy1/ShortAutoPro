#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"

# Pausa entre produções para aliviar APIs gratuitas.
COOLDOWN="${SHORT_BATCH_COOLDOWN:-20}"

if ! [[ "$COOLDOWN" =~ ^[0-9]+$ ]]; then
    COOLDOWN=20
fi

COOLDOWN=$((COOLDOWN))

if [ "$COOLDOWN" -lt 10 ]; then
    COOLDOWN=10
fi

if [ "$COOLDOWN" -gt 120 ]; then
    COOLDOWN=120
fi


STATE_DIR="$BASE/queue"
mkdir -p "$STATE_DIR"

STATE_FILE="$STATE_DIR/batch_state.json"

# ======================================
# HELPERS
# ======================================

salvar_estado() {

    local batch_id="$1"
    local total="$2"
    local atual="$3"
    local sucessos="$4"
    local falhas="$5"
    local status="$6"

    python - <<PY
import json
from datetime import datetime

data = {
    "batch_id": "$batch_id",
    "total": int("$total"),
    "current": int("$atual"),
    "successes": int("$sucessos"),
    "failures": int("$falhas"),
    "status": "$status",
    "updated_at": datetime.now().isoformat()
}

with open(
    "$STATE_FILE",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        data,
        f,
        ensure_ascii=False,
        indent=2
    )
PY
}


ler_campo() {

    local campo="$1"

    python - <<PY
import json
from pathlib import Path

p = Path("$STATE_FILE")

if not p.exists():
    print("")
else:
    try:
        d = json.loads(
            p.read_text(
                encoding="utf-8"
            )
        )

        print(
            d.get(
                "$campo",
                ""
            )
        )

    except Exception:
        print("")
PY
}


# ======================================
# MODO
# ======================================

MODO="${1:-}"

if [ "$MODO" = "--status" ]; then

    if [ ! -f "$STATE_FILE" ]; then
        echo "Nenhum lote salvo."
        exit 0
    fi

    echo
    echo "======================================"
    echo " BATCH RECOVERY - STATUS"
    echo "======================================"
    echo

    cat "$STATE_FILE"

    echo

    exit 0
fi


if [ "$MODO" = "--reset" ]; then

    rm -f "$STATE_FILE"

    echo "Estado do lote apagado."

    exit 0
fi


# ======================================
# RETOMAR
# ======================================

if [ "$MODO" = "--resume" ]; then

    if [ ! -f "$STATE_FILE" ]; then
        echo "ERRO: nenhum lote salvo."
        exit 1
    fi

    BATCH_ID="$(ler_campo batch_id)"
    TOTAL="$(ler_campo total)"
    ATUAL="$(ler_campo current)"
    SUCESSOS="$(ler_campo successes)"
    FALHAS="$(ler_campo failures)"
    STATUS="$(ler_campo status)"

    if [ -z "$TOTAL" ] || [ -z "$ATUAL" ]; then
        echo "ERRO: estado inválido."
        exit 1
    fi

    if [ "$STATUS" = "completed" ]; then
        echo "Este lote já foi concluído."
        exit 0
    fi

    INICIO=$((ATUAL + 1))

    echo
    echo "Retomando lote:"
    echo "$BATCH_ID"
    echo
    echo "Próximo Short:"
    echo "$INICIO/$TOTAL"
    echo

else

    # ======================================
    # NOVO LOTE
    # ======================================

    TOTAL="${1:-${SHORT_LOTE:-3}}"

    if ! [[ "$TOTAL" =~ ^[0-9]+$ ]]; then
        echo "ERRO: quantidade inválida."
        exit 1
    fi

    TOTAL=$((TOTAL))

    if [ "$TOTAL" -lt 1 ]; then
        TOTAL=1
    fi

    if [ "$TOTAL" -gt 10 ]; then
        TOTAL=10
    fi

    BATCH_ID="$(date +%F_%H%M%S)"

    INICIO=1
    SUCESSOS=0
    FALHAS=0

    salvar_estado \
        "$BATCH_ID" \
        "$TOTAL" \
        "0" \
        "$SUCESSOS" \
        "$FALHAS" \
        "running"

fi


# ======================================
# CONFIG
# ======================================

if [ -f "$BASE/config.sh" ]; then
    source "$BASE/config.sh"
else
    echo "ERRO: config.sh não encontrado."
    exit 1
fi


# ======================================
# LOG
# ======================================

LOG_DIR="$BASE/logs/lotes"
mkdir -p "$LOG_DIR"

LOG="$LOG_DIR/lote_${BATCH_ID}.log"

exec > >(tee -a "$LOG") 2>&1


echo
echo "======================================"
echo " SHORTAUTO PRO - BATCH RECOVERY 1.9"
echo "======================================"
echo
echo "Lote: $BATCH_ID"
echo "Total: $TOTAL"
echo "Início em: $INICIO"
echo "Sucessos anteriores: $SUCESSOS"
echo "Falhas anteriores: $FALHAS"
echo


# ======================================
# LOOP
# ======================================

for ((i=INICIO; i<=TOTAL; i++)); do

    echo
    echo "######################################"
    echo " SHORT $i/$TOTAL"
    echo "######################################"
    echo

    unset SHORT_ID

    salvar_estado \
        "$BATCH_ID" \
        "$TOTAL" \
        "$((i - 1))" \
        "$SUCESSOS" \
        "$FALHAS" \
        "running"


    INICIO_SHORT=$(date +%s)


    if "$BASE/gerar_short.sh"; then

        SUCESSOS=$((SUCESSOS + 1))

        STATUS_SHORT="OK"

    else

        CODIGO=$?

        FALHAS=$((FALHAS + 1))

        STATUS_SHORT="ERRO $CODIGO"

    fi


    FIM_SHORT=$(date +%s)

    TEMPO=$((FIM_SHORT - INICIO_SHORT))


    salvar_estado \
        "$BATCH_ID" \
        "$TOTAL" \
        "$i" \
        "$SUCESSOS" \
        "$FALHAS" \
        "running"


    echo
    echo "SHORT $i: $STATUS_SHORT"
    echo "Tempo: ${TEMPO}s"
    echo "Sucessos: $SUCESSOS"
    echo "Falhas: $FALHAS"


    if [ "$i" -lt "$TOTAL" ]; then

        echo
        echo "Cooldown das APIs: ${COOLDOWN}s..."
        echo

        sleep "$COOLDOWN"

    fi

done


# ======================================
# FINAL
# ======================================

salvar_estado \
    "$BATCH_ID" \
    "$TOTAL" \
    "$TOTAL" \
    "$SUCESSOS" \
    "$FALHAS" \
    "completed"


echo
echo "======================================"
echo " LOTE FINALIZADO"
echo "======================================"
echo
echo "Total: $TOTAL"
echo "Sucessos: $SUCESSOS"
echo "Falhas: $FALHAS"
echo
echo "Estado:"
echo "$STATE_FILE"
echo
echo "Log:"
echo "$LOG"
echo
