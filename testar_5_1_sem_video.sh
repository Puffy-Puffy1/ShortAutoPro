#!/data/data/com.termux/files/usr/bin/bash

set +e

BASE="$HOME/ShortAutoPro"

cd "$BASE" || exit 1

echo
echo "======================================"
echo " SHORTAUTOPRO 5.1 - TESTE SEM VIDEO"
echo "======================================"
echo

# =====================================================
# LOCALIZAR ÚLTIMA PRODUÇÃO COMPLETA
# =====================================================

ULTIMO_VIDEO="$(
    ls -t \
    "$BASE"/videos/short_v6_*.mp4 \
    2>/dev/null \
    | head -1
)"

if [ -n "$ULTIMO_VIDEO" ]; then

    NOME="$(
        basename "$ULTIMO_VIDEO"
    )"

    SHORT_ID="${NOME#short_v6_}"

    SHORT_ID="${SHORT_ID%.mp4}"

else

    ULTIMO_MAPA="$(
        ls -t \
        "$BASE"/roteiros/scene_map_*.json \
        2>/dev/null \
        | head -1
    )"

    if [ -z "$ULTIMO_MAPA" ]; then
        echo "ERRO: nenhuma produção anterior encontrada."
        exit 1
    fi

    NOME="$(
        basename "$ULTIMO_MAPA"
    )"

    SHORT_ID="${NOME#scene_map_}"

    SHORT_ID="${SHORT_ID%.json}"

fi

export SHORT_ID

echo "Produção usada:"
echo "$SHORT_ID"
echo

PASS=0
FAIL=0
WARN=0


teste() {

    NOME="$1"
    shift

    echo
    echo "--------------------------------------"
    echo "$NOME"
    echo "--------------------------------------"
    echo

    "$@"

    CODIGO=$?

    echo

    if [ "$CODIGO" -eq 0 ]; then

        echo "[ PASS ] $NOME"

        PASS=$((PASS + 1))

    else

        echo "[ FAIL ] $NOME"
        echo "Código: $CODIGO"

        FAIL=$((FAIL + 1))

    fi

}


# =====================================================
# 1. ARQUIVOS ESSENCIAIS
# =====================================================

echo "======================================"
echo "1. ARQUIVOS DA PRODUCAO"
echo "======================================"
echo

ARQUIVOS=(
    "roteiros/short_${SHORT_ID}.txt"
    "roteiros/fonte_${SHORT_ID}.txt"
    "roteiros/scene_map_${SHORT_ID}.json"
    "roteiros/motion_plan_${SHORT_ID}.json"
)

for ARQ in "${ARQUIVOS[@]}"; do

    if [ -f "$BASE/$ARQ" ]; then
        echo "[ OK ] $ARQ"
    else
        echo "[ AUSENTE ] $ARQ"
        WARN=$((WARN + 1))
    fi

done


# =====================================================
# 2. PYTHON COMPILE
# =====================================================

teste \
"PYTHON COMPILE - MASTER QUALITY 5.1" \
python -m py_compile \
"$BASE/source_identity.py" \
"$BASE/semantic_integrity_gate.py" \
"$BASE/media_master_gate.py" \
"$BASE/production_supervisor.py" \
"$BASE/editorial_gate.py" \
"$BASE/publish_integrity_gate.py" \
"$BASE/source_ledger.py" \
"$BASE/production_manifest.py" \
"$BASE/final_quality.py" \
"$BASE/midia.py" \
"$BASE/motion_director.py" \
"$BASE/rhythm_director.py" \
"$BASE/video.py" \
"$BASE/v6.py"


# =====================================================
# 3. BASH
# =====================================================

teste \
"BASH SYNTAX - gerar_short.sh" \
bash -n \
"$BASE/gerar_short.sh"


teste \
"BASH SYNTAX - release_check.sh" \
bash -n \
"$BASE/release_check.sh"


teste \
"BASH SYNTAX - health_check.sh" \
bash -n \
"$BASE/health_check.sh"


# =====================================================
# 4. ORDEM DO PIPELINE
# =====================================================

echo
echo "======================================"
echo "4. ORDEM DO PIPELINE"
echo "======================================"
echo

grep -nE \
'semantic_integrity_gate|midia.py|media_master_gate|motion_director|rhythm_director|production_supervisor|editorial_gate|quality_check|publish_pack|source_ledger|publish_integrity_gate|production_manifest|final_quality|register_topic' \
"$BASE/gerar_short.sh"

echo


# =====================================================
# 5. RELEASE CHECK
# =====================================================

teste \
"RELEASE CHECK" \
"$BASE/release_check.sh"


# =====================================================
# 6. SEMANTIC INTEGRITY
# =====================================================

teste \
"SEMANTIC INTEGRITY GATE 5.1" \
python \
"$BASE/semantic_integrity_gate.py"


# =====================================================
# 7. MEDIA MASTER
# =====================================================

teste \
"MEDIA MASTER GATE 5.1" \
python \
"$BASE/media_master_gate.py"


# =====================================================
# 8. PRODUCTION SUPERVISOR
# =====================================================

teste \
"PRODUCTION SUPERVISOR 5.0" \
python \
"$BASE/production_supervisor.py"


# =====================================================
# 9. FINAL EDITORIAL GATE
# =====================================================

teste \
"FINAL EDITORIAL GATE 5.0" \
python \
"$BASE/editorial_gate.py"


# =====================================================
# 10. PUBLISH INTEGRITY
# =====================================================

PUBLISH="$BASE/roteiros/publish_${SHORT_ID}.txt"

if [ -f "$PUBLISH" ]; then

    teste \
    "PUBLISH INTEGRITY GATE 5.1" \
    python \
    "$BASE/publish_integrity_gate.py"

else

    echo
    echo "--------------------------------------"
    echo "PUBLISH INTEGRITY GATE 5.1"
    echo "--------------------------------------"
    echo
    echo "[ SKIP ] publish_${SHORT_ID}.txt ausente"
    echo

    WARN=$((WARN + 1))

fi


# =====================================================
# 11. QUALITY CHECK NO VIDEO EXISTENTE
# =====================================================

if [ -n "$ULTIMO_VIDEO" ] \
&& [ -f "$ULTIMO_VIDEO" ]; then

    teste \
    "QUALITY CHECK - VIDEO EXISTENTE" \
    python \
    "$BASE/quality_check.py"

else

    echo
    echo "[ SKIP ] Nenhum vídeo final existente."
    WARN=$((WARN + 1))

fi


# =====================================================
# RELATORIOS CRIADOS PELOS GATES
# =====================================================

echo
echo "======================================"
echo " RELATORIOS 5.1"
echo "======================================"
echo

for ARQ in \
"$BASE/roteiros/semantic_integrity_${SHORT_ID}.json" \
"$BASE/roteiros/media_quality_${SHORT_ID}.json" \
"$BASE/roteiros/supervisor_${SHORT_ID}.json" \
"$BASE/roteiros/publish_integrity_${SHORT_ID}.json"
do

    if [ -f "$ARQ" ]; then
        echo "[ OK ] $(basename "$ARQ")"
    else
        echo "[ -- ] $(basename "$ARQ")"
    fi

done


# =====================================================
# RESULTADO
# =====================================================

echo
echo "======================================"
echo " RESULTADO DO TESTE 5.1"
echo "======================================"
echo

echo "SHORT_ID: $SHORT_ID"
echo "PASS: $PASS"
echo "FAIL: $FAIL"
echo "WARN/SKIP: $WARN"
echo

if [ "$FAIL" -eq 0 ]; then

    echo "======================================"
    echo " MASTER QUALITY 5.1: TESTE APROVADO"
    echo " NENHUM VIDEO NOVO FOI GERADO"
    echo "======================================"

    exit 0

else

    echo "======================================"
    echo " MASTER QUALITY 5.1: AJUSTES NECESSARIOS"
    echo " NENHUM VIDEO NOVO FOI GERADO"
    echo "======================================"

    exit 1

fi
