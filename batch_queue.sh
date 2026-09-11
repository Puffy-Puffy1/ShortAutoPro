#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"

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


# ======================================
# QUANTIDADE
# ======================================

QTD="${1:-${SHORT_LOTE:-3}}"

if ! [[ "$QTD" =~ ^[0-9]+$ ]]; then
    echo "ERRO: quantidade inválida."
    echo "Exemplo:"
    echo "~/ShortAutoPro/batch_queue.sh 3"
    exit 1
fi

if [ "$QTD" -lt 1 ]; then
    QTD=1
fi

if [ "$QTD" -gt 10 ]; then
    QTD=10
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
# LOG DO LOTE
# ======================================

BATCH_ID="$(date +%F_%H%M%S)"

LOG_DIR="$BASE/logs/lotes"
mkdir -p "$LOG_DIR"

LOG="$LOG_DIR/lote_${BATCH_ID}.log"

exec > >(tee -a "$LOG") 2>&1


echo
echo "======================================"
echo " SHORTAUTO PRO - BATCH QUEUE 1.8"
echo "======================================"
echo
echo "Lote: $BATCH_ID"
echo "Quantidade: $QTD"
echo "Início: $(date)"
echo "Log: $LOG"
echo


# ======================================
# CONTADORES
# ======================================

SUCESSOS=0
FALHAS=0

declare -a IDS_OK
declare -a IDS_ERRO


# ======================================
# LOOP
# ======================================

for ((i=1; i<=QTD; i++)); do

    echo
    echo
    echo "######################################"
    echo " SHORT $i/$QTD"
    echo "######################################"
    echo


    # O gerar_short.sh cria o ID sozinho.
    # Garantimos que nenhum ID antigo
    # permaneça no ambiente.

    unset SHORT_ID


    INICIO=$(date +%s)


    if "$BASE/gerar_short.sh"; then

        FIM=$(date +%s)

        TEMPO=$((FIM - INICIO))

        SUCESSOS=$((SUCESSOS + 1))

        # Descobre o manifest mais recente
        # criado por esta geração.

        MANIFEST="$(
            ls -t \
            "$BASE"/manifests/*.json \
            2>/dev/null \
            | head -1
        )"

        if [ -n "$MANIFEST" ]; then

            ID_OK="$(
                basename "$MANIFEST" .json
            )"

        else

            ID_OK="desconhecido"

        fi


        IDS_OK+=(
            "$ID_OK"
        )


        echo
        echo "SHORT $i: OK"
        echo "ID: $ID_OK"
        echo "Tempo: ${TEMPO}s"


    else

        CODIGO=$?

        FIM=$(date +%s)

        TEMPO=$((FIM - INICIO))

        FALHAS=$((FALHAS + 1))

        ID_ERRO="$(
            date +%F_%H%M
        )"

        IDS_ERRO+=(
            "$ID_ERRO"
        )


        echo
        echo "SHORT $i: FALHOU"
        echo "Código: $CODIGO"
        echo "Tempo: ${TEMPO}s"
        echo
        echo "O lote continuará."


    fi


    # Pequena pausa para evitar IDs iguais
    # e aliviar APIs gratuitas.

    if [ "$i" -lt "$QTD" ]; then

        echo
        echo "Cooldown das APIs: ${COOLDOWN}s..."

        sleep "$COOLDOWN"

    fi

done


# ======================================
# RESUMO
# ======================================

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

    for ID in "${IDS_OK[@]}"; do
        echo "  OK  $ID"
    done

    echo

fi


if [ "${#IDS_ERRO[@]}" -gt 0 ]; then

    echo "FALHAS:"

    for ID in "${IDS_ERRO[@]}"; do
        echo "  ERRO  $ID"
    done

    echo

fi


echo "Log do lote:"
echo "$LOG"
echo

echo "Fim: $(date)"
echo "======================================"

# Não retorna erro se pelo menos
# um Short foi produzido.

if [ "$SUCESSOS" -gt 0 ]; then
    exit 0
fi

exit 1
