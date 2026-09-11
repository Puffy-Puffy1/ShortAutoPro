#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"

ERROS=0

ok() {
    echo "OK   $1"
}

erro() {
    echo "ERRO $1"
    ERROS=$((ERROS + 1))
}

echo
echo "======================================"
echo " SHORTAUTO PRO - RELEASE CHECK 2.3.9"
echo "======================================"
echo

# ======================================
# BASH
# ======================================

BASH_FILES=(
    gerar_short.sh
    health_check.sh
    preflight_check.sh
    limpar_storage.sh
    batch_queue.sh
    batch_recovery.sh
    control_center.sh
    diagnostico.sh
)

for arq in "${BASH_FILES[@]}"; do

    if [ ! -f "$BASE/$arq" ]; then
        erro "$arq ausente"
        continue
    fi

    if bash -n "$BASE/$arq" >/dev/null 2>&1; then
        ok "Bash $arq"
    else
        erro "Sintaxe $arq"
    fi

done

# ======================================
# PYTHON
# ======================================

PY_FILES=(
    wiki_client.py
    source_identity.py
    topic_memory.py
    topic_reserve.py
    topic_index.py
    topic_engine.py
    roteiro.py
    used_topic.py
    hook_engine.py
    narrative_director.py
    cold_open_director.py
    scene_director.py
    documentary_director.py
    visual_director.py
    visual_risk_guard.py
    editorial_continuity.py
    wikimedia_source.py
    wikimedia_query_bridge.py
    source_router.py
    evidence_guard.py
    source_ledger.py
    motion_director.py
    rhythm_director.py
    production_supervisor.py
    editorial_gate.py
    midia.py
    audio.py
    legenda_dinamica.py
    video.py
    v6.py
    quality_check.py
    publish_pack.py
    production_manifest.py
    final_quality.py
    register_topic.py
    batch_report.py
)

for arq in "${PY_FILES[@]}"; do

    if [ ! -f "$BASE/$arq" ]; then
        erro "$arq ausente"
        continue
    fi

    if python -m py_compile \
        "$BASE/$arq" \
        >/dev/null 2>&1
    then
        ok "Python $arq"
    else
        erro "Python $arq"
    fi

done

# ======================================
# IMPORTS IMPORTANTES
# ======================================

cd "$BASE" || exit 1

if python - <<'PY' >/dev/null 2>&1
import topic_memory
import topic_reserve
import wiki_client
PY
then
    ok "Imports internos"
else
    erro "Imports internos"
fi

# ======================================
# BROADCAST AUDIO FILTERS
# ======================================

FFMPEG_FILTERS="$(
    ffmpeg -hide_banner -filters 2>/dev/null || true
)"


if grep -F "sidechaincompress" \
    <<< "$FFMPEG_FILTERS" \
    >/dev/null 2>&1
then

    ok "FFmpeg sidechaincompress"

else

    erro "FFmpeg sidechaincompress ausente"

fi


if grep -F "loudnorm" \
    <<< "$FFMPEG_FILTERS" \
    >/dev/null 2>&1
then

    ok "FFmpeg loudnorm"

else

    erro "FFmpeg loudnorm ausente"

fi


# ======================================
# CONFIG
# ======================================

if [ -f "$BASE/config.sh" ]; then

    # shellcheck disable=SC1090
    source "$BASE/config.sh"

    ok "config.sh"

else

    erro "config.sh ausente"

fi

if [ -n "${GEMINI_API_KEY:-}" ]; then
    ok "Gemini key carregada"
else
    erro "Gemini key ausente"
fi

# ======================================
# ESTRUTURA
# ======================================

PASTAS=(
    roteiros
    imagens
    audios
    videos
    temp
    logs
    manifests
    backups
)

for pasta in "${PASTAS[@]}"; do

    if [ -d "$BASE/$pasta" ]; then
        ok "pasta $pasta"
    else
        erro "pasta $pasta ausente"
    fi

done

# ======================================
# STORAGE
# ======================================

LIVRE_KB="$(
    df -Pk "$HOME" 2>/dev/null \
    | awk 'NR==2 {print $4}'
)"

if [[ "${LIVRE_KB:-}" =~ ^[0-9]+$ ]]; then

    LIVRE_MB=$((LIVRE_KB / 1024))

    if [ "$LIVRE_MB" -ge 1500 ]; then
        ok "Storage ${LIVRE_MB} MB livres"
    else
        erro "Storage baixo: ${LIVRE_MB} MB"
    fi

else

    erro "Não consegui medir storage"

fi

# ======================================
# RESULTADO
# ======================================

echo
echo "======================================"
echo " RELEASE RESULT"
echo "======================================"
echo
echo "Erros: $ERROS"
echo

if [ "$ERROS" -eq 0 ]; then

    echo "STATUS: RELEASE READY"
    exit 0

else

    echo "STATUS: BLOQUEADO"
    exit 1

fi
