#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"
IMAGENS="$BASE/imagens"
TEMP="$BASE/temp"

EXECUTAR=0
MANTER="${SHORT_STORAGE_MANTER:-2}"

if [ "${1:-}" = "--execute" ]; then
    EXECUTAR=1
fi

if ! [[ "$MANTER" =~ ^[0-9]+$ ]]; then
    MANTER=2
fi

if [ "$MANTER" -lt 1 ]; then
    MANTER=1
fi

if [ "$MANTER" -gt 10 ]; then
    MANTER=10
fi


tamanho_bytes() {

    local caminho="$1"

    if [ ! -e "$caminho" ]; then
        echo 0
        return
    fi

    local kb

    kb="$(
        du -sk "$caminho" 2>/dev/null \
        | awk '{print $1}'
    )"

    kb="${kb:-0}"

    echo $((kb * 1024))
}


humanizar() {

    local bytes="${1:-0}"

    awk -v b="$bytes" '
    BEGIN {
        if (b >= 1073741824)
            printf "%.2f GB", b/1073741824
        else if (b >= 1048576)
            printf "%.1f MB", b/1048576
        else if (b >= 1024)
            printf "%.1f KB", b/1024
        else
            printf "%d B", b
    }'
}


listar_pastas() {

    local base="$1"
    local padrao="$2"

    if [ ! -d "$base" ]; then
        return
    fi

    find "$base" \
        -mindepth 1 \
        -maxdepth 1 \
        -type d \
        -name "$padrao" \
        -printf '%T@ %p\n' \
        2>/dev/null \
        | sort -nr \
        | cut -d' ' -f2-
}


echo
echo "======================================"
echo " SHORTAUTO PRO - STORAGE GUARD 2.3.9"
echo "======================================"
echo

if [ "$EXECUTAR" -eq 1 ]; then
    echo "MODO: LIMPEZA REAL"
else
    echo "MODO: SIMULAÇÃO"
fi

echo
echo "Projetos recentes preservados: $MANTER"
echo

ANTES_BYTES="$(tamanho_bytes "$BASE")"

echo "Espaço atual do ShortAutoPro:"
du -sh "$BASE" 2>/dev/null || true
echo

TOTAL_LIBERAR=0


# =====================================================
# IMAGENS
# =====================================================

echo "======================================"
echo " MÍDIA BRUTA"
echo "======================================"
echo

mapfile -t PASTAS_IMG < <(
    listar_pastas "$IMAGENS" "short_*"
)

TOTAL_IMG="${#PASTAS_IMG[@]}"

echo "Pastas encontradas: $TOTAL_IMG"
echo

echo "PRESERVADAS:"

LIMITE="$MANTER"

if [ "$TOTAL_IMG" -lt "$MANTER" ]; then
    LIMITE="$TOTAL_IMG"
fi

for ((i=0; i<LIMITE; i++)); do

    DIR="${PASTAS_IMG[$i]}"

    TAM_H="$(
        du -sh "$DIR" 2>/dev/null \
        | awk '{print $1}'
    )"

    echo "  ${TAM_H:-?}  $DIR"

done

if [ "$TOTAL_IMG" -eq 0 ]; then
    echo "  Nenhuma."
fi


echo
echo "REMOVIDAS:"

if [ "$TOTAL_IMG" -gt "$MANTER" ]; then

    for ((i=MANTER; i<TOTAL_IMG; i++)); do

        DIR="${PASTAS_IMG[$i]}"

        TAM_H="$(
            du -sh "$DIR" 2>/dev/null \
            | awk '{print $1}'
        )"

        TAM_B="$(tamanho_bytes "$DIR")"
        TAM_B="${TAM_B:-0}"

        TOTAL_LIBERAR=$((TOTAL_LIBERAR + TAM_B))

        echo "  ${TAM_H:-?}  $DIR"

        if [ "$EXECUTAR" -eq 1 ]; then
            rm -rf -- "$DIR"
        fi

    done

else

    echo "  Nada para remover."

fi


# =====================================================
# TEMP
# =====================================================

echo
echo "======================================"
echo " TEMPORÁRIOS"
echo "======================================"
echo

mapfile -t PASTAS_TEMP < <(
    listar_pastas "$TEMP" "2026-*"
)

TOTAL_TEMP="${#PASTAS_TEMP[@]}"

echo "Pastas encontradas: $TOTAL_TEMP"
echo

echo "PRESERVADAS:"

LIMITE="$MANTER"

if [ "$TOTAL_TEMP" -lt "$MANTER" ]; then
    LIMITE="$TOTAL_TEMP"
fi

for ((i=0; i<LIMITE; i++)); do

    DIR="${PASTAS_TEMP[$i]}"

    TAM_H="$(
        du -sh "$DIR" 2>/dev/null \
        | awk '{print $1}'
    )"

    echo "  ${TAM_H:-?}  $DIR"

done

if [ "$TOTAL_TEMP" -eq 0 ]; then
    echo "  Nenhuma."
fi


echo
echo "REMOVIDAS:"

if [ "$TOTAL_TEMP" -gt "$MANTER" ]; then

    for ((i=MANTER; i<TOTAL_TEMP; i++)); do

        DIR="${PASTAS_TEMP[$i]}"

        TAM_H="$(
            du -sh "$DIR" 2>/dev/null \
            | awk '{print $1}'
        )"

        TAM_B="$(tamanho_bytes "$DIR")"
        TAM_B="${TAM_B:-0}"

        TOTAL_LIBERAR=$((TOTAL_LIBERAR + TAM_B))

        echo "  ${TAM_H:-?}  $DIR"

        if [ "$EXECUTAR" -eq 1 ]; then
            rm -rf -- "$DIR"
        fi

    done

else

    echo "  Nada para remover."

fi


# =====================================================
# PYTHON CACHE
# =====================================================

echo
echo "======================================"
echo " CACHE PYTHON"
echo "======================================"
echo

CACHE_TOTAL=0
CACHE_ENCONTRADO=0

while IFS= read -r DIR; do

    [ -z "$DIR" ] && continue

    CACHE_ENCONTRADO=1

    TAM_H="$(
        du -sh "$DIR" 2>/dev/null \
        | awk '{print $1}'
    )"

    TAM_B="$(tamanho_bytes "$DIR")"
    TAM_B="${TAM_B:-0}"

    CACHE_TOTAL=$((CACHE_TOTAL + TAM_B))

    echo "  ${TAM_H:-?}  $DIR"

    if [ "$EXECUTAR" -eq 1 ]; then
        rm -rf -- "$DIR"
    fi

done < <(
    find "$BASE" \
        -type d \
        -name "__pycache__" \
        -not -path "$BASE/backups/*" \
        2>/dev/null
)

if [ "$CACHE_ENCONTRADO" -eq 0 ]; then
    echo "Nenhum cache Python."
fi

TOTAL_LIBERAR=$((TOTAL_LIBERAR + CACHE_TOTAL))


# =====================================================
# RESULTADO
# =====================================================

TOTAL_MB=$((TOTAL_LIBERAR / 1024 / 1024))

TOTAL_GB="$(
    awk \
    -v b="$TOTAL_LIBERAR" \
    'BEGIN {printf "%.2f", b/1073741824}'
)"

echo
echo "======================================"
echo " RESULTADO"
echo "======================================"
echo

echo "Espaço estimado para liberar:"
humanizar "$TOTAL_LIBERAR"
echo
echo "${TOTAL_MB} MB (~${TOTAL_GB} GB)"
echo


if [ "$EXECUTAR" -eq 0 ]; then

    echo "SIMULAÇÃO FINALIZADA."
    echo "Nenhum arquivo foi apagado."
    echo
    echo "Para executar:"
    echo "~/ShortAutoPro/limpar_storage.sh --execute"
    echo

    exit 0

fi


DEPOIS_BYTES="$(tamanho_bytes "$BASE")"

if [[ "$ANTES_BYTES" =~ ^[0-9]+$ ]] &&    [[ "$DEPOIS_BYTES" =~ ^[0-9]+$ ]] &&    [ "$ANTES_BYTES" -ge "$DEPOIS_BYTES" ]; then

    REAL_LIBERADO=$((ANTES_BYTES - DEPOIS_BYTES))

else

    REAL_LIBERADO=0

fi


echo "LIMPEZA FINALIZADA."
echo
echo "Espaço realmente liberado:"
humanizar "$REAL_LIBERADO"
echo
echo "Espaço atual:"
du -sh "$BASE" 2>/dev/null || true
echo
echo "======================================"
echo
