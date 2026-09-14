#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"

echo
echo "======================================"
echo " SHORTAUTO PRO - HEALTH CHECK 2.5"
echo "======================================"
echo

ERROS=0

checar_arquivo() {
    local arq="$1"
    if [ -f "$BASE/$arq" ]; then
        echo "OK  $arq"
    else
        echo "ERRO  $arq"
        ERROS=$((ERROS + 1))
    fi
}

ARQUIVOS=(
    config.sh gerar_short.sh
    topic_engine.py topic_memory.py topic_reserve.py topic_index.py wiki_client.py source_identity.py
    roteiro.py used_topic.py hook_engine.py narrative_director.py cold_open_director.py
    scene_director.py scene_truth_refiner_6_7.py documentary_director.py visual_director.py
    visual_risk_guard.py editorial_continuity.py scene_lossless_repair.py post_script_truth_lock.py
    semantic_integrity_gate.py wikimedia_source.py wikimedia_query_bridge.py source_router.py evidence_guard.py
    midia.py midia_runtime.py visual_pipeline_bridge_v42.py visual_selection_engine_v4.py visual_intelligence_6.py
    vi6_8_runtime_policy.py vi6_9_runtime_policy.py media_master_gate.py motion_director.py rhythm_director.py
    production_supervisor.py editorial_gate.py audio.py legenda_dinamica.py subtitle_alignment.py video.py v6.py v6_runtime.py quality_check.py
    publish_pack.py source_ledger.py publish_integrity_gate.py production_manifest.py final_quality.py register_topic.py
    limpar_storage.sh batch_report.py batch_queue.sh batch_recovery.sh control_center.sh
    preflight_check.sh diagnostico.sh release_check.sh
)

for arq in "${ARQUIVOS[@]}"; do
    checar_arquivo "$arq"
done

echo

for cmd in python ffmpeg ffprobe piper bash; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "OK  $cmd"
    else
        echo "ERRO  $cmd"
        ERROS=$((ERROS + 1))
    fi
done

VOICE_DIR="$BASE/piper/voice"
if [ -d "$VOICE_DIR" ] && find "$VOICE_DIR" -maxdepth 1 -type f -name 'pt_BR-faber-medium*.onnx' -print -quit 2>/dev/null | grep -q .; then
    echo "OK  voz Piper pt_BR-faber-medium"
else
    echo "ERRO  modelo Piper pt_BR-faber-medium ausente"
    ERROS=$((ERROS + 1))
fi

WHISPER_CLI="${WHISPER_CLI:-$HOME/whisper.cpp/build/bin/whisper-cli}"
WHISPER_MODEL="${WHISPER_MODEL:-$HOME/whisper.cpp/models/ggml-base.bin}"

if [ -x "$WHISPER_CLI" ]; then
    echo "OK  Whisper CLI"
else
    echo "ERRO  Whisper CLI ausente: $WHISPER_CLI"
    ERROS=$((ERROS + 1))
fi

if [ -f "$WHISPER_MODEL" ]; then
    echo "OK  Whisper model"
else
    echo "ERRO  Whisper model ausente: $WHISPER_MODEL"
    ERROS=$((ERROS + 1))
fi

# Catch local runtime dependencies without starting production work.
if (
    cd "$BASE" &&
    python - <<'PY' >/dev/null 2>&1
import importlib

for name in (
    "midia_runtime",
    "subtitle_alignment",
    "topic_memory",
    "topic_reserve",
    "source_identity",
    "wiki_client",
    "v6_runtime",
):
    importlib.import_module(name)
PY
); then
    echo "OK  imports runtime críticos"
else
    echo "ERRO  imports runtime críticos"
    ERROS=$((ERROS + 1))
fi

echo
echo "--------------------------------------"

if [ "$ERROS" -eq 0 ]; then
    echo "STATUS: SAUDÁVEL"
    exit 0
fi

echo "STATUS: $ERROS ERRO(S)"
exit 1
