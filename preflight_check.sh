#!/data/data/com.termux/files/usr/bin/bash

set -u

BASE="$HOME/ShortAutoPro"

ERROS=0
AVISOS=0

ok() {
    echo "OK     $1"
}

aviso() {
    echo "AVISO  $1"
    AVISOS=$((AVISOS + 1))
}

erro() {
    echo "ERRO   $1"
    ERROS=$((ERROS + 1))
}

echo
echo "======================================"
echo " SHORTAUTO PRO - PREFLIGHT CHECK 2.1"
echo "======================================"
echo

# ======================================
# CONFIG
# ======================================

if [ -f "$BASE/config.sh" ]; then
    source "$BASE/config.sh"
    ok "config.sh"
else
    erro "config.sh ausente"
fi

# ======================================
# CHAVES
# ======================================

if [ -n "${GEMINI_API_KEY:-}" ]; then
    ok "GEMINI_API_KEY"
else
    erro "GEMINI_API_KEY não configurada"
fi

if [ -n "${PEXELS_API_KEY:-}" ]; then
    ok "PEXELS_API_KEY"
else
    aviso "PEXELS_API_KEY ausente"
fi

if [ -n "${PIXABAY_API_KEY:-}" ]; then
    ok "PIXABAY_API_KEY"
else
    aviso "PIXABAY_API_KEY ausente"
fi

if [ -n "${COVERR_API_KEY:-}" ]; then
    ok "COVERR_API_KEY"
else
    aviso "COVERR_API_KEY ausente"
fi

# ======================================
# COMANDOS
# ======================================

for CMD in python ffmpeg ffprobe; do

    if command -v "$CMD" >/dev/null 2>&1; then
        ok "$CMD"
    else
        erro "$CMD não encontrado"
    fi

done

# ======================================
# SCRIPTS OBRIGATÓRIOS
# ======================================

ARQUIVOS=(
    gerar_short.sh
    topic_engine.py
    topic_memory.py
    topic_reserve.py
    topic_index.py
    roteiro.py
    used_topic.py
    hook_engine.py
    scene_director.py
    midia.py
    audio.py
    legenda_dinamica.py
    video.py
    v6.py
    quality_check.py
    publish_pack.py
    production_manifest.py
    register_topic.py
    health_check.sh
    limpar_storage.sh
)

for ARQ in "${ARQUIVOS[@]}"; do

    if [ -f "$BASE/$ARQ" ]; then
        ok "$ARQ"
    else
        erro "$ARQ ausente"
    fi

done

# ======================================
# PASTAS
# ======================================

PASTAS=(
    roteiros
    audios
    imagens
    videos
    temp
    logs
    manifests
    backups
)

for PASTA in "${PASTAS[@]}"; do

    if [ -d "$BASE/$PASTA" ]; then
        ok "pasta $PASTA"
    else
        aviso "criando pasta $PASTA"
        mkdir -p "$BASE/$PASTA" || erro "falha criando $PASTA"
    fi

done

# ======================================
# PIPER / VOZ
# ======================================

if [ -d "$BASE/piper" ]; then
    ok "Piper"
else
    erro "pasta Piper ausente"
fi

# ======================================
# ESPAÇO LIVRE
# ======================================

LIVRE_KB="$(
    df -Pk "$HOME" 2>/dev/null \
    | awk 'NR==2 {print $4}'
)"

if [[ "${LIVRE_KB:-}" =~ ^[0-9]+$ ]]; then

    LIVRE_MB=$((LIVRE_KB / 1024))

    if [ "$LIVRE_MB" -ge 2000 ]; then
        ok "espaço livre: ${LIVRE_MB} MB"

    elif [ "$LIVRE_MB" -ge 800 ]; then
        aviso "espaço livre baixo: ${LIVRE_MB} MB"

    else
        erro "espaço insuficiente: ${LIVRE_MB} MB"
    fi

else
    aviso "não consegui medir espaço livre"
fi

# ======================================
# HISTÓRICO
# ======================================

if [ -f "$BASE/historico_assuntos.json" ]; then

    if python - <<'PY' >/dev/null 2>&1
import json
from pathlib import Path

p = Path.home() / "ShortAutoPro" / "historico_assuntos.json"

with open(
    p,
    encoding="utf-8"
) as f:
    d = json.load(f)

assert isinstance(d, list)
PY
    then
        ok "historico_assuntos.json"
    else
        erro "historico_assuntos.json inválido"
    fi

else
    aviso "histórico ainda não existe"
fi

# ======================================
# SINTAXE BASH
# ======================================

for ARQ in \
    gerar_short.sh \
    health_check.sh \
    limpar_storage.sh \
    batch_queue.sh \
    batch_recovery.sh \
    control_center.sh
do

    if [ -f "$BASE/$ARQ" ]; then

        if bash -n "$BASE/$ARQ" >/dev/null 2>&1; then
            ok "sintaxe $ARQ"
        else
            erro "erro de sintaxe em $ARQ"
        fi

    fi

done

# ======================================
# PYTHON COMPILE
# ======================================

PY_FILES=(
    topic_engine.py
    topic_memory.py
    topic_reserve.py
    topic_index.py
    roteiro.py
    used_topic.py
    hook_engine.py
    scene_director.py
    midia.py
    audio.py
    legenda_dinamica.py
    video.py
    v6.py
    quality_check.py
    publish_pack.py
    production_manifest.py
    register_topic.py
)

for ARQ in "${PY_FILES[@]}"; do

    if [ -f "$BASE/$ARQ" ]; then

        if python -m py_compile \
            "$BASE/$ARQ" \
            >/dev/null 2>&1
        then
            ok "Python $ARQ"
        else
            erro "erro Python em $ARQ"
        fi

    fi

done

# ======================================
# RESULTADO
# ======================================

echo
echo "======================================"
echo " PREFLIGHT RESULTADO"
echo "======================================"
echo
echo "Erros: $ERROS"
echo "Avisos: $AVISOS"
echo

if [ "$ERROS" -eq 0 ]; then

    echo "STATUS: PRONTO PARA PRODUÇÃO"

    exit 0

else

    echo "STATUS: NÃO PRONTO"

    exit 1

fi
