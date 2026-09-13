#!/data/data/com.termux/files/usr/bin/bash

set -u

BASE="$HOME/ShortAutoPro"
ERROS=0
AVISOS=0

ok() { echo "OK     $1"; }
aviso() { echo "AVISO  $1"; AVISOS=$((AVISOS + 1)); }
erro() { echo "ERRO   $1"; ERROS=$((ERROS + 1)); }

echo
echo "======================================"
echo " SHORTAUTO PRO - PREFLIGHT CHECK 2.2"
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
if [ -n "${PEXELS_API_KEY:-}" ]; then ok "PEXELS_API_KEY"; else aviso "PEXELS_API_KEY ausente"; fi
if [ -n "${PIXABAY_API_KEY:-}" ]; then ok "PIXABAY_API_KEY"; else aviso "PIXABAY_API_KEY ausente"; fi
if [ -n "${COVERR_API_KEY:-}" ]; then ok "COVERR_API_KEY"; else aviso "COVERR_API_KEY ausente"; fi

for cmd in python ffmpeg ffprobe piper bash; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ok "$cmd"
    else
        erro "$cmd não encontrado"
    fi
done

ARQUIVOS=(
    gerar_short.sh
    topic_engine.py topic_memory.py topic_reserve.py topic_index.py wiki_client.py source_identity.py
    roteiro.py used_topic.py hook_engine.py narrative_director.py cold_open_director.py
    scene_director.py scene_truth_refiner_6_7.py documentary_director.py visual_director.py
    visual_risk_guard.py editorial_continuity.py scene_lossless_repair.py post_script_truth_lock.py
    semantic_integrity_gate.py wikimedia_source.py wikimedia_query_bridge.py source_router.py evidence_guard.py
    midia.py media_master_gate.py motion_director.py rhythm_director.py production_supervisor.py editorial_gate.py
    audio.py legenda_dinamica.py video.py v6.py v5.py quality_check.py publish_pack.py source_ledger.py
    publish_integrity_gate.py production_manifest.py final_quality.py register_topic.py
    health_check.sh limpar_storage.sh batch_queue.sh batch_recovery.sh control_center.sh
)

for arq in "${ARQUIVOS[@]}"; do
    if [ -f "$BASE/$arq" ]; then ok "$arq"; else erro "$arq ausente"; fi
done

PASTAS=(roteiros audios imagens videos temp logs manifests backups queue credits)
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
PY
    then
        ok "historico_assuntos.json"
    else
        erro "historico_assuntos.json inválido"
    fi
else
    aviso "histórico ainda não existe"
fi

SHELL_FILES=(gerar_short.sh health_check.sh limpar_storage.sh batch_queue.sh batch_recovery.sh control_center.sh preflight_check.sh diagnostico.sh release_check.sh)
for arq in "${SHELL_FILES[@]}"; do
    if [ -f "$BASE/$arq" ]; then
        if bash -n "$BASE/$arq" >/dev/null 2>&1; then ok "sintaxe $arq"; else erro "erro de sintaxe em $arq"; fi
    fi
done

PY_FILES=(
    topic_engine.py topic_memory.py topic_reserve.py topic_index.py wiki_client.py source_identity.py
    roteiro.py used_topic.py hook_engine.py narrative_director.py cold_open_director.py
    scene_director.py scene_truth_refiner_6_7.py documentary_director.py visual_director.py
    visual_risk_guard.py editorial_continuity.py scene_lossless_repair.py post_script_truth_lock.py
    semantic_integrity_gate.py wikimedia_source.py wikimedia_query_bridge.py source_router.py evidence_guard.py
    midia.py media_master_gate.py motion_director.py rhythm_director.py production_supervisor.py editorial_gate.py
    audio.py legenda_dinamica.py video.py v6.py v5.py quality_check.py publish_pack.py source_ledger.py
    publish_integrity_gate.py production_manifest.py final_quality.py register_topic.py
)

for arq in "${PY_FILES[@]}"; do
    if [ -f "$BASE/$arq" ]; then
        if python -m py_compile "$BASE/$arq" >/dev/null 2>&1; then ok "Python $arq"; else erro "erro Python em $arq"; fi
    fi
done

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
fi

echo "STATUS: NÃO PRONTO"
exit 1
