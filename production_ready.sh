#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"

ERROS=0
AVISOS=0

ok() {
    printf "OK      %s\n" "$1"
}

aviso() {
    printf "AVISO   %s\n" "$1"
    AVISOS=$((AVISOS + 1))
}

erro() {
    printf "ERRO    %s\n" "$1"
    ERROS=$((ERROS + 1))
}

echo
echo "======================================"
echo " SHORTAUTO PRO - READINESS GATE 2.4.0"
echo "======================================"
echo


# ======================================
# 1. RELEASE CHECK
# ======================================

if "$BASE/release_check.sh" >/dev/null 2>&1; then
    ok "Release Check"
else
    erro "Release Check"
fi


# ======================================
# 2. FERRAMENTAS
# ======================================

for cmd in python ffmpeg ffprobe; do

    if command -v "$cmd" >/dev/null 2>&1; then
        ok "$cmd"
    else
        erro "$cmd ausente"
    fi

done


# ======================================
# 3. CONFIG
# ======================================

if [ -f "$BASE/config.sh" ]; then

    # shellcheck disable=SC1090
    source "$BASE/config.sh"

    ok "Config carregada"

else

    erro "config.sh ausente"

fi


# ======================================
# 4. CHAVES
# ======================================

if [ -n "${GEMINI_API_KEY:-}" ]; then
    ok "Gemini"
else
    erro "GEMINI_API_KEY"
fi

if [ -n "${PEXELS_API_KEY:-}" ]; then
    ok "Pexels"
else
    aviso "PEXELS_API_KEY ausente"
fi

if [ -n "${PIXABAY_API_KEY:-}" ]; then
    ok "Pixabay"
else
    aviso "PIXABAY_API_KEY ausente"
fi

if [ -n "${COVERR_API_KEY:-}" ]; then
    ok "Coverr"
else
    aviso "COVERR_API_KEY ausente"
fi


# ======================================
# 5. PIPER
# ======================================

PIPER_OK=0

if command -v piper >/dev/null 2>&1; then
    PIPER_OK=1
fi

if [ -x "$BASE/piper/piper" ]; then
    PIPER_OK=1
fi

if [ "$PIPER_OK" -eq 1 ]; then
    ok "Piper"
else
    aviso "Piper não localizado pelo Readiness Gate"
fi


# ======================================
# 6. HISTÓRICO
# ======================================

HIST="$BASE/historico_assuntos.json"

if [ ! -f "$HIST" ]; then

    aviso "Histórico ainda não existe"

else

    if python - "$HIST" <<'PY' >/dev/null 2>&1
import json
import sys

with open(
    sys.argv[1],
    "r",
    encoding="utf-8"
) as f:
    data = json.load(f)

if not isinstance(data, list):
    raise SystemExit(1)
PY
    then
        ok "Histórico JSON"
    else
        erro "historico_assuntos.json inválido"
    fi

fi


# ======================================
# 7. STORAGE
# ======================================

LIVRE_KB="$(
    df -Pk "$HOME" 2>/dev/null |
    awk 'NR==2 {print $4}'
)"

if [[ "${LIVRE_KB:-}" =~ ^[0-9]+$ ]]; then

    LIVRE_MB=$((LIVRE_KB / 1024))

    if [ "$LIVRE_MB" -ge 3000 ]; then

        ok "Storage ${LIVRE_MB} MB livres"

    elif [ "$LIVRE_MB" -ge 1500 ]; then

        aviso "Storage ${LIVRE_MB} MB livres"

    else

        erro "Storage insuficiente: ${LIVRE_MB} MB"

    fi

else

    erro "Não consegui verificar storage"

fi


# ======================================
# 8. DIRETÓRIOS DE PRODUÇÃO
# ======================================

DIRS=(
    roteiros
    imagens
    audios
    videos
    temp
    logs
    manifests
)

for dir in "${DIRS[@]}"; do

    if [ -d "$BASE/$dir" ] &&
       [ -w "$BASE/$dir" ]; then

        ok "$dir gravável"

    else

        erro "$dir não está gravável"

    fi

done


# ======================================
# 9. ARQUIVOS PRINCIPAIS
# ======================================

CRITICOS=(
    gerar_short.sh
    topic_engine.py
    roteiro.py
    hook_engine.py
    scene_director.py
    midia.py
    audio.py
    legenda_dinamica.py
    v6.py
    quality_check.py
    publish_pack.py
    production_manifest.py
    final_quality.py
)

for arq in "${CRITICOS[@]}"; do

    if [ -s "$BASE/$arq" ]; then
        ok "$arq"
    else
        erro "$arq"
    fi

done


# ======================================
# RESULTADO
# ======================================

echo
echo "======================================"
echo " READINESS RESULT"
echo "======================================"
echo

echo "Erros: $ERROS"
echo "Avisos: $AVISOS"
echo


if [ "$ERROS" -gt 0 ]; then

    echo "DECISÃO: BLOCKED"
    echo "Produção não recomendada."

    exit 1

fi


if [ "$AVISOS" -gt 0 ]; then

    echo "DECISÃO: GO WITH WARNINGS"
    echo "Produção possível."

    exit 0

fi


echo "DECISÃO: GO"
echo "Sistema pronto para produção."

exit 0
