#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

BASE="$HOME/ShortAutoPro"
ERROS=0
AVISOS=0

mkdir -p "$BASE/.sap_state" 2>/dev/null || true
CODE_CACHE="$BASE/.sap_state/preflight_code_cache.txt"
CODE_HEAD=""
CODE_CACHE_HIT=0

if command -v git >/dev/null 2>&1 && [ -d "$BASE/.git" ]; then
    CODE_HEAD="$(git -C "$BASE" rev-parse HEAD 2>/dev/null || true)"
    if [ -n "$CODE_HEAD" ] && [ -z "$(git -C "$BASE" status --porcelain 2>/dev/null)" ]; then
        if [ -f "$CODE_CACHE" ] && [ "$(cat "$CODE_CACHE" 2>/dev/null)" = "$CODE_HEAD" ]; then
            CODE_CACHE_HIT=1
        fi
    fi
fi

ok() { echo "OK     $1"; }
aviso() { echo "AVISO  $1"; AVISOS=$((AVISOS + 1)); }
erro() { echo "ERRO   $1"; ERROS=$((ERROS + 1)); }

echo
echo "======================================"
echo " SHORTAUTO PRO - PREFLIGHT CHECK 3.0.2"
echo "======================================"
echo

if [ -f "$BASE/config.sh" ]; then
    # shellcheck disable=SC1091
    source "$BASE/config.sh"
    ok "config.sh"
else
    erro "config.sh ausente"
fi

if [ -n "${GEMINI_API_KEY:-}" ]; then ok "GEMINI_API_KEY"; else erro "GEMINI_API_KEY não configurada"; fi
if [ -n "${PEXELS_API_KEY:-}" ]; then ok "PEXELS_API_KEY"; else aviso "PEXELS_API_KEY ausente; provider será ignorado e os fallbacks gratuitos continuarão disponíveis"; fi
if [ -n "${PIXABAY_API_KEY:-}" ]; then ok "PIXABAY_API_KEY"; else aviso "PIXABAY_API_KEY ausente"; fi
if [ -n "${COVERR_API_KEY:-}" ]; then ok "COVERR_API_KEY"; else aviso "COVERR_API_KEY ausente"; fi

for cmd in python ffmpeg ffprobe piper bash; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ok "$cmd"
    else
        erro "$cmd não encontrado"
    fi
done

# Somente componentes do pipeline canônico 3.0.2 e utilitários operacionais ativos.
ARQUIVOS=(
    main.py profile_run.sh resume_short_runtime.py finalize_short.sh
    topic_engine_runtime.py topic_engine.py topic_memory.py topic_reserve.py topic_index.py wiki_client.py source_identity.py
    script_runtime.py roteiro.py used_topic.py hook_engine.py hook_runtime.py narrative_director.py cold_open_director.py
    scene_director.py scene_truth_refiner_6_7.py documentary_director.py visual_director.py
    visual_shot_bridge.py visual_shot_policy.py visual_editorial_policy.py
    visual_risk_guard.py editorial_continuity.py visual_continuity_engine.py scene_lossless_repair.py post_script_truth_lock.py
    semantic_integrity_gate.py wikimedia_source.py wikimedia_query_bridge.py source_router.py evidence_guard.py
    media_stage_runtime.py midia.py media_runtime_adapter_v1.py media_runtime_adapter_v2.py media_must_verifier.py vg4x_bridge.py visual_engine_unified.py
    visual_query_expansion_v4.py visual_query_planner_v4.py visual_pipeline_bridge_v42.py visual_selection_engine_v4.py visual_intelligence_6.py
    vi6_8_runtime_policy.py vi6_9_runtime_policy.py media_master_gate.py visual_score_engine.py
    motion_director.py rhythm_director.py professional_edit_director.py professional_edit_repair.py
    multi_asset_director.py retention_engine.py sound_design_engine.py production_supervisor.py editorial_gate.py
    speech_director.py audio.py legenda_dinamica.py subtitle_alignment.py subtitle_style_policy.py
    professional_caption_director.py caption_layout_guard.py video_professional.py v6_professional.py
    audio_finalizer.py visual_qa.py quality_check.py publish_pack.py source_ledger.py publish_integrity_gate.py
    production_manifest.py final_quality.py professional_quality_gate.py release_gate.py register_topic.py storage_manager.py
    health_check.sh batch_queue.sh batch_recovery.sh control_center.sh
)

for arq in "${ARQUIVOS[@]}"; do
    if [ -f "$BASE/$arq" ]; then ok "$arq"; else erro "$arq ausente"; fi
done

# Legados da arquitetura 2.x não podem reaparecer silenciosamente.
LEGADOS=(gerar_short.sh video.py v6.py v6_runtime.py limpar_storage.sh)
for arq in "${LEGADOS[@]}"; do
    if [ -e "$BASE/$arq" ]; then erro "legado proibido presente: $arq"; else ok "legado ausente: $arq"; fi
done

PASTAS=(roteiros audios imagens videos temp logs manifests backups queue credits reports .sap_state .locks)
for pasta in "${PASTAS[@]}"; do
    if [ -d "$BASE/$pasta" ]; then
        ok "pasta $pasta"
    else
        aviso "criando pasta $pasta"
        mkdir -p "$BASE/$pasta" || erro "falha criando $pasta"
    fi
done

VOICE_DIR="$BASE/piper/voice"
if [ -d "$VOICE_DIR" ] && find "$VOICE_DIR" -maxdepth 1 -type f -name 'pt_BR-faber-medium*.onnx' -print -quit 2>/dev/null | grep -q .; then
    ok "voz Piper pt_BR-faber-medium"
else
    erro "voz Piper pt_BR-faber-medium ausente"
fi

WHISPER_CLI="${WHISPER_CLI:-$HOME/whisper.cpp/build/bin/whisper-cli}"
WHISPER_MODEL="${WHISPER_MODEL:-$HOME/whisper.cpp/models/ggml-base.bin}"
if [ -x "$WHISPER_CLI" ]; then ok "Whisper CLI"; else erro "Whisper CLI ausente: $WHISPER_CLI"; fi
if [ -f "$WHISPER_MODEL" ]; then ok "Whisper model"; else erro "Whisper model ausente: $WHISPER_MODEL"; fi

LIVRE_KB="$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2 {print $4}')"
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

if [ -f "$BASE/historico_assuntos.json" ]; then
    if BASE_CHECK="$BASE" python - <<'PY' >/dev/null 2>&1
import json
import os
from pathlib import Path
p = Path(os.environ["BASE_CHECK"]) / "historico_assuntos.json"
with p.open(encoding="utf-8") as f:
    d = json.load(f)
assert isinstance(d, list)
assert all(isinstance(item, dict) for item in d)
PY
    then
        ok "historico_assuntos.json"
    else
        erro "historico_assuntos.json inválido"
    fi
else
    aviso "histórico ainda não existe"
fi

if [ "$CODE_CACHE_HIT" -eq 1 ]; then
    ok "validação de sintaxe/imports em cache para commit $CODE_HEAD"
else
    CODE_ERRORS_BEFORE="$ERROS"

    SHELL_FILES=(
        profile_run.sh finalize_short.sh health_check.sh batch_queue.sh batch_recovery.sh
        control_center.sh preflight_check.sh diagnostico.sh release_check.sh
    )
    for arq in "${SHELL_FILES[@]}"; do
        if [ -f "$BASE/$arq" ]; then
            if bash -n "$BASE/$arq" >/dev/null 2>&1; then ok "sintaxe $arq"; else erro "erro de sintaxe em $arq"; fi
        fi
    done
    
    PY_FILES=(
        main.py resume_short_runtime.py topic_engine_runtime.py topic_engine.py topic_memory.py topic_reserve.py topic_index.py wiki_client.py source_identity.py
        script_runtime.py roteiro.py used_topic.py hook_engine.py hook_runtime.py narrative_director.py cold_open_director.py
        scene_director.py scene_truth_refiner_6_7.py documentary_director.py visual_director.py visual_shot_bridge.py
        visual_shot_policy.py visual_editorial_policy.py visual_risk_guard.py editorial_continuity.py visual_continuity_engine.py
        scene_lossless_repair.py post_script_truth_lock.py semantic_integrity_gate.py wikimedia_source.py wikimedia_query_bridge.py
        source_router.py evidence_guard.py media_stage_runtime.py midia.py media_runtime_adapter_v1.py media_runtime_adapter_v2.py media_must_verifier.py vg4x_bridge.py visual_engine_unified.py
        visual_query_expansion_v4.py visual_query_planner_v4.py visual_pipeline_bridge_v42.py visual_selection_engine_v4.py visual_intelligence_6.py
        vi6_8_runtime_policy.py vi6_9_runtime_policy.py media_master_gate.py visual_score_engine.py motion_director.py rhythm_director.py
        professional_edit_director.py professional_edit_repair.py multi_asset_director.py retention_engine.py sound_design_engine.py
        production_supervisor.py editorial_gate.py speech_director.py audio.py legenda_dinamica.py subtitle_alignment.py subtitle_style_policy.py
        professional_caption_director.py caption_layout_guard.py video_professional.py v6_professional.py audio_finalizer.py visual_qa.py
        quality_check.py publish_pack.py source_ledger.py publish_integrity_gate.py production_manifest.py final_quality.py
        professional_quality_gate.py release_gate.py register_topic.py storage_manager.py
    )
    
    for arq in "${PY_FILES[@]}"; do
        if [ -f "$BASE/$arq" ]; then
            if python -m py_compile "$BASE/$arq" >/dev/null 2>&1; then ok "Python $arq"; else erro "erro Python em $arq"; fi
        fi
    done
    
    # Import-only checks: módulos sem efeitos de produção na importação.
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
    "visual_pipeline_bridge_v42",
    "visual_selection_engine_v4",
    "media_must_verifier",
    "visual_engine_unified",
    "visual_query_expansion_v4",
    "media_runtime_adapter_v1",
    "media_runtime_adapter_v2",
    "vg4x_bridge",
    "visual_intelligence_6",
    "vi6_8_runtime_policy",
    "vi6_9_runtime_policy",
    "visual_continuity_engine",
    "visual_score_engine",
    "retention_engine",
    "sound_design_engine",
):
    importlib.import_module(name)
PY
    ); then
        ok "imports runtime críticos 3.0.2"
    else
        erro "dependência/import runtime crítico 3.0.2 quebrado"
    fi
    
    

    if [ "$ERROS" -eq "$CODE_ERRORS_BEFORE" ] && [ -n "$CODE_HEAD" ] && [ -z "$(git -C "$BASE" status --porcelain 2>/dev/null)" ]; then
        printf '%s\n' "$CODE_HEAD" > "$CODE_CACHE" 2>/dev/null || true
        ok "cache de validação de código atualizado"
    fi
fi

echo
echo "======================================"
echo " PREFLIGHT RESULTADO"
echo "======================================"
echo "Erros: $ERROS"
echo "Avisos: $AVISOS"
echo

if [ "$ERROS" -eq 0 ]; then
    echo "STATUS: PRONTO PARA PRODUÇÃO 3.0.2"
    exit 0
fi

echo "STATUS: NÃO PRONTO"
exit 1
