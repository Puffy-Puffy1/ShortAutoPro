#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"

echo
echo "======================================"
echo " SHORTAUTO PRO - HEALTH CHECK 3.0"
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
    config.sh main.py profile_run.sh resume_short_runtime.py
    topic_engine_runtime.py topic_engine.py topic_memory.py topic_reserve.py topic_index.py wiki_client.py source_identity.py
    roteiro.py used_topic.py hook_engine.py hook_runtime.py narrative_director.py cold_open_director.py
    scene_director.py scene_truth_refiner_6_7.py documentary_director.py visual_director.py
    visual_shot_bridge.py visual_shot_policy.py visual_editorial_policy.py
    visual_risk_guard.py editorial_continuity.py visual_continuity_engine.py scene_lossless_repair.py post_script_truth_lock.py
    semantic_integrity_gate.py wikimedia_source.py wikimedia_query_bridge.py source_router.py evidence_guard.py
    midia.py media_runtime_adapter_v1.py media_must_verifier.py vg4x_bridge.py visual_engine_unified.py
    visual_query_expansion_v4.py visual_query_planner_v4.py visual_pipeline_bridge_v42.py visual_selection_engine_v4.py visual_intelligence_6.py
    vi6_8_runtime_policy.py vi6_9_runtime_policy.py media_master_gate.py visual_score_engine.py
    motion_director.py rhythm_director.py professional_edit_director.py professional_edit_repair.py
    multi_asset_director.py retention_engine.py sound_design_engine.py production_supervisor.py editorial_gate.py
    speech_director.py audio.py legenda_dinamica.py subtitle_alignment.py subtitle_style_policy.py
    professional_caption_director.py caption_layout_guard.py video_professional.py v6_professional.py
    audio_finalizer.py visual_qa.py quality_check.py publish_pack.py source_ledger.py publish_integrity_gate.py
    production_manifest.py final_quality.py professional_quality_gate.py release_gate.py register_topic.py storage_manager.py
    batch_report.py batch_queue.sh batch_recovery.sh control_center.sh
    preflight_check.sh diagnostico.sh release_check.sh
)

for arq in "${ARQUIVOS[@]}"; do
    checar_arquivo "$arq"
done

for legacy in gerar_short.sh video.py v6.py v6_runtime.py limpar_storage.sh; do
    if [ -e "$BASE/$legacy" ]; then
        echo "ERRO  legado proibido presente: $legacy"
        ERROS=$((ERROS + 1))
    else
        echo "OK  legado ausente: $legacy"
    fi
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

if [ -x "$WHISPER_CLI" ]; then echo "OK  Whisper CLI"; else echo "ERRO  Whisper CLI ausente: $WHISPER_CLI"; ERROS=$((ERROS + 1)); fi
if [ -f "$WHISPER_MODEL" ]; then echo "OK  Whisper model"; else echo "ERRO  Whisper model ausente: $WHISPER_MODEL"; ERROS=$((ERROS + 1)); fi

# Import-only smoke test para dependências internas sem disparar produção.
if (
    cd "$BASE" &&
    python - <<'PY' >/dev/null 2>&1
import importlib
for name in (
    "subtitle_alignment",
    "subtitle_style_policy",
    "visual_shot_policy",
    "visual_editorial_policy",
    "visual_shot_bridge",
    "topic_memory",
    "topic_reserve",
    "source_identity",
    "wiki_client",
    "visual_selection_engine_v4",
    "media_must_verifier",
    "visual_engine_unified",
    "visual_query_expansion_v4",
    "media_runtime_adapter_v1",
    "vg4x_bridge",
    "visual_continuity_engine",
    "visual_score_engine",
    "retention_engine",
    "sound_design_engine",
):
    importlib.import_module(name)
PY
); then
    echo "OK  imports runtime críticos 3.0"
else
    echo "ERRO  imports runtime críticos 3.0"
    ERROS=$((ERROS + 1))
fi

echo
echo "--------------------------------------"

if [ "$ERROS" -eq 0 ]; then
    echo "STATUS: SAUDÁVEL 3.0"
    exit 0
fi

echo "STATUS: $ERROS ERRO(S)"
exit 1
