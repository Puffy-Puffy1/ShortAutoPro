#!/data/data/com.termux/files/usr/bin/bash

set -u

BASE="$HOME/ShortAutoPro"

echo
echo "======================================"
echo " SHORTAUTO PRO - HEALTH CHECK"
echo "======================================"
echo

ERROS=0

checar_arquivo() {
    ARQ="$1"

    if [ -f "$BASE/$ARQ" ]; then
        echo "OK  $ARQ"
    else
        echo "ERRO  $ARQ"
        ERROS=$((ERROS + 1))
    fi
}

checar_arquivo "config.sh"
checar_arquivo "gerar_short.sh"
checar_arquivo "roteiro.py"
checar_arquivo "scene_director.py"
checar_arquivo "documentary_director.py"
checar_arquivo "visual_director.py"
checar_arquivo "visual_risk_guard.py"
checar_arquivo "editorial_continuity.py"
checar_arquivo "wikimedia_source.py"
checar_arquivo "wikimedia_query_bridge.py"
checar_arquivo "source_router.py"
checar_arquivo "evidence_guard.py"
checar_arquivo "source_ledger.py"
checar_arquivo "motion_director.py"
checar_arquivo "rhythm_director.py"
checar_arquivo "production_supervisor.py"
checar_arquivo "editorial_gate.py"
checar_arquivo "midia.py"
checar_arquivo "audio.py"
checar_arquivo "legenda_dinamica.py"
checar_arquivo "video.py"
checar_arquivo "v6.py"
checar_arquivo "limpar_storage.sh"
checar_arquivo "quality_check.py"
checar_arquivo "hook_engine.py"
checar_arquivo "narrative_director.py"
checar_arquivo "cold_open_director.py"
checar_arquivo "topic_engine.py"
checar_arquivo "topic_memory.py"
checar_arquivo "topic_reserve.py"
checar_arquivo "topic_index.py"
checar_arquivo "wiki_client.py"
checar_arquivo "source_identity.py"
checar_arquivo "register_topic.py"
checar_arquivo "used_topic.py"
checar_arquivo "publish_pack.py"
checar_arquivo "production_manifest.py"
checar_arquivo "final_quality.py"
checar_arquivo "batch_report.py"
checar_arquivo "batch_queue.sh"
checar_arquivo "batch_recovery.sh"
checar_arquivo "control_center.sh"
checar_arquivo "preflight_check.sh"
checar_arquivo "diagnostico.sh"
checar_arquivo "release_check.sh"

echo

if command -v ffmpeg >/dev/null 2>&1; then
    echo "OK  ffmpeg"
else
    echo "ERRO  ffmpeg"
    ERROS=$((ERROS + 1))
fi

if command -v ffprobe >/dev/null 2>&1; then
    echo "OK  ffprobe"
else
    echo "ERRO  ffprobe"
    ERROS=$((ERROS + 1))
fi

if command -v python >/dev/null 2>&1; then
    echo "OK  python"
else
    echo "ERRO  python"
    ERROS=$((ERROS + 1))
fi

echo
echo "--------------------------------------"

if [ "$ERROS" -eq 0 ]; then
    echo "STATUS: SAUDÁVEL"
    exit 0
else
    echo "STATUS: $ERROS ERRO(S)"
    exit 1
fi
