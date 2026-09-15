#!/data/data/com.termux/files/usr/bin/bash

set -u

BASE="$HOME/ShortAutoPro"
R="$BASE/roteiros"

cd "$BASE" || exit 1

echo
echo "======================================"
echo " TRUTH + SEMANTIC MASTER TEST 6.2"
echo " SEM GERAR VIDEO"
echo "======================================"
echo


# =====================================================
# 1. ARQUIVOS
# =====================================================

echo "--------------------------------------"
echo "1/6 - MODULOS"
echo "--------------------------------------"

FILES="
source_identity.py
scene_lossless_repair.py
post_script_truth_lock.py
semantic_integrity_gate.py
visual_intelligence_6.py
midia.py
"

for f in $FILES
do
    if [ ! -f "$BASE/$f" ]; then
        echo "ERRO: ausente $f"
        exit 1
    fi

    echo "OK $f"
done


# =====================================================
# 2. COMPILE
# =====================================================

echo
echo "--------------------------------------"
echo "2/6 - COMPILE"
echo "--------------------------------------"

python -m py_compile \
source_identity.py \
scene_lossless_repair.py \
post_script_truth_lock.py \
semantic_integrity_gate.py \
visual_intelligence_6.py \
midia.py

if [ "$?" -ne 0 ]; then
    echo "COMPILE: FAIL"
    exit 1
fi

bash -n gerar_short.sh

if [ "$?" -ne 0 ]; then
    echo "BASH: FAIL"
    exit 1
fi

echo "COMPILE: PASS"


# =====================================================
# 3. ULTIMO SEMANTIC BLOCK
# =====================================================

echo
echo "--------------------------------------"
echo "3/6 - LOCALIZANDO SHORT BLOQUEADO"
echo "--------------------------------------"

SEM="$(
ls -t "$R"/semantic_integrity_*.json \
2>/dev/null |
head -1
)"

if [ -z "${SEM:-}" ]; then
    echo "ERRO: nenhum relatório Semantic."
    exit 1
fi

SID="$(
basename "$SEM" |
sed -E 's/^semantic_integrity_//; s/\.json$//'
)"

echo "SHORT_ID=$SID"

export SHORT_ID="$SID"


# =====================================================
# 4. LOSSLESS
# =====================================================

echo
echo "--------------------------------------"
echo "4/6 - LOSSLESS COVERAGE REPAIR"
echo "--------------------------------------"

python scene_lossless_repair.py

CODE=$?

if [ "$CODE" -ne 0 ]; then
    echo
    echo "LOSSLESS: FAIL"
    exit "$CODE"
fi

echo
echo "LOSSLESS: PASS"


# =====================================================
# 5. TRUTH LOCK
# =====================================================

echo
echo "--------------------------------------"
echo "5/6 - POST-SCRIPT TRUTH LOCK"
echo "--------------------------------------"

python post_script_truth_lock.py

CODE=$?

if [ "$CODE" -ne 0 ]; then
    echo
    echo "TRUTH LOCK: BLOCK"
    exit "$CODE"
fi

echo
echo "TRUTH LOCK: PASS"


# =====================================================
# 6. SEMANTIC
# =====================================================

echo
echo "--------------------------------------"
echo "6/6 - SEMANTIC INTEGRITY"
echo "--------------------------------------"

python semantic_integrity_gate.py

CODE=$?

if [ "$CODE" -ne 0 ]; then
    echo
    echo "SEMANTIC: BLOCK"
    exit "$CODE"
fi


echo
echo "======================================"
echo " RESULTADO MASTER 6.2"
echo "======================================"
echo
echo "SHORT_ID: $SID"
echo "LOSSLESS: PASS"
echo "TRUTH LOCK: PASS"
echo "SEMANTIC: PASS"
echo
echo "NENHUM VIDEO FOI GERADO"
echo
echo "======================================"
