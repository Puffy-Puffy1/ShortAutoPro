#!/data/data/com.termux/files/usr/bin/bash

# SHORTAUTOPRO VISUAL ENGINE V5 FLAGS
export SAP_VQE5="${SAP_VQE5:-1}"
export SAP_VQE5_RESCUE="${SAP_VQE5_RESCUE:-1}"
export SAP_VQE5_QUERY_EXTRA="${SAP_VQE5_QUERY_EXTRA:-2}"
export SAP_VQE5_COMMIT="${SAP_VQE5_COMMIT:-1}"

# Motores experimentais antigos ficam desligados.
export SAP_VSE_V2=0
export SAP_VSE_V3=0
export SAP_VSE_V4=0
export SAP_VSE_V42=0
export SAP_VSE4=0
export SAP_VSE42=0
export SAP_VSE4_RUNTIME=0
export SAP_SCENE_COMMIT_LOCK=0

# Pipeline único: Professional por padrão, rollback explícito por SAP_PRO_EDIT=0.
export SAP_PRO_EDIT="${SAP_PRO_EDIT:-1}"
export SAP_PROFESSIONAL_MIN_SCORE="${SAP_PROFESSIONAL_MIN_SCORE:-88}"
export SAP_PROFESSIONAL_ENFORCE="${SAP_PROFESSIONAL_ENFORCE:-0}"
export SAP_PRO_MEDIA_MIN_PIXELS="${SAP_PRO_MEDIA_MIN_PIXELS:-921600}"

if [ "$SAP_PRO_EDIT" = "1" ]; then
    PIPELINE_LABEL="PROFESSIONAL"
else
    PIPELINE_LABEL="STANDARD_ROLLBACK"
fi

set -e
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
EVOLUTION="$BASE/shortautopro_evolution.py"

# =====================================================
# EXECUTION LOCK
# =====================================================
# Cron, lote e execução manual não podem produzir o mesmo Short
# ao mesmo tempo. flock é preferido; mkdir é fallback atômico.

LOCK_ROOT="$BASE/.locks"
mkdir -p "$LOCK_ROOT"
LOCK_FILE="$LOCK_ROOT/gerar_short.lock"
LOCK_DIR="$LOCK_ROOT/gerar_short.lockdir"
LOCK_FALLBACK=0

liberar_lock_fallback() {
    if [ "$LOCK_FALLBACK" -eq 1 ]; then
        rm -f "$LOCK_DIR/pid" 2>/dev/null || true
        rmdir "$LOCK_DIR" 2>/dev/null || true
    fi
}

if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
        echo "ERRO: já existe uma geração do ShortAutoPro em andamento."
        exit 75
    fi
else
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
        PID_ANTIGO=""
        if [ -f "$LOCK_DIR/pid" ]; then
            PID_ANTIGO="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
        fi

        if [ -n "$PID_ANTIGO" ] && kill -0 "$PID_ANTIGO" 2>/dev/null; then
            echo "ERRO: já existe uma geração do ShortAutoPro em andamento."
            exit 75
        fi

        rm -rf "$LOCK_DIR" 2>/dev/null || true
        if ! mkdir "$LOCK_DIR" 2>/dev/null; then
            echo "ERRO: não foi possível adquirir trava de produção."
            exit 75
        fi
    fi

    printf '%s\n' "$$" > "$LOCK_DIR/pid"
    LOCK_FALLBACK=1
    trap liberar_lock_fallback EXIT INT TERM
fi

# =====================================================
# ID ÚNICO
# =====================================================

if [ -n "${SHORT_ID:-}" ]; then
    ID="$SHORT_ID"
else
    ID="$(date +%F_%H%M%S)_$$"
fi

export SHORT_ID="$ID"

LOG_DIR="$BASE/logs/producao"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/short_${SHORT_ID}.log"
exec > >(tee -a "$LOG") 2>&1

echo
echo "======================================"
echo " SHORTAUTO PRO - UNIFIED V6 + EVOLUTION"
echo "======================================"
echo
echo "ID: $SHORT_ID"
echo "PIPELINE: $PIPELINE_LABEL"
echo "INÍCIO: $(date)"
echo "LOG: $LOG"
echo

cd "$BASE"

# =====================================================
# CONFIG
# =====================================================

if [ -f "$BASE/config.sh" ]; then
    # shellcheck disable=SC1091
    source "$BASE/config.sh"
else
    echo "ERRO: config.sh não encontrado."
    exit 1
fi

# =====================================================
# EVOLUTION TELEMETRY
# =====================================================
# Falhas nesta camada nunca escondem uma falha real do pipeline. A camada
# registra checkpoint/tempo/qualidade, mas o pipeline principal segue sendo
# autoridade para produção.

evolution_checkpoint() {
    local stage="$1"
    local status="$2"
    local title="${3:-}"
    if [ -f "$EVOLUTION" ]; then
        python "$EVOLUTION" checkpoint --stage "$stage" --status "$status" --title "$title" >/dev/null 2>&1 \
            || echo "AVISO: checkpoint Evolution falhou: $stage/$status"
    fi
}

evolution_finish() {
    local status="${1:-SUCCESS}"
    if [ -f "$EVOLUTION" ]; then
        python "$EVOLUTION" finish --status "$status" >/dev/null 2>&1 \
            || echo "AVISO: fechamento Evolution falhou."
    fi
}

evolution_checkpoint "pipeline" "start" "ShortAutoPro production"

# =====================================================
# HELPERS
# =====================================================

rodar_python() {
    local TITULO="$1"
    local ARQUIVO="$2"
    shift 2

    echo
    echo "--------------------------------------"
    echo "$TITULO"
    echo "--------------------------------------"
    echo

    if [ ! -f "$BASE/$ARQUIVO" ]; then
        echo "ERRO: arquivo obrigatório não encontrado: $ARQUIVO"
        evolution_checkpoint "$ARQUIVO" "fail" "$TITULO"
        exit 1
    fi

    local INICIO_ETAPA
    INICIO_ETAPA="$(date +%s)"
    evolution_checkpoint "$ARQUIVO" "start" "$TITULO"

    if python "$BASE/$ARQUIVO" "$@"; then
        local FIM_ETAPA TEMPO
        FIM_ETAPA="$(date +%s)"
        TEMPO="$((FIM_ETAPA - INICIO_ETAPA))"
        evolution_checkpoint "$ARQUIVO" "pass" "$TITULO"
        echo
        echo "ETAPA OK: ${TEMPO}s"
    else
        local CODIGO=$?
        evolution_checkpoint "$ARQUIVO" "fail" "$TITULO"
        echo
        echo "ERRO NA ETAPA: $TITULO"
        echo "Arquivo: $ARQUIVO"
        echo "Código: $CODIGO"
        evolution_finish "FAILED"
        exit "$CODIGO"
    fi
}

rodar_shell() {
    local TITULO="$1"
    local ARQUIVO="$2"
    shift 2

    echo
    echo "--------------------------------------"
    echo "$TITULO"
    echo "--------------------------------------"
    echo

    if [ ! -f "$BASE/$ARQUIVO" ]; then
        echo "ERRO: arquivo obrigatório não encontrado: $ARQUIVO"
        evolution_checkpoint "$ARQUIVO" "fail" "$TITULO"
        exit 1
    fi

    evolution_checkpoint "$ARQUIVO" "start" "$TITULO"
    if bash "$BASE/$ARQUIVO" "$@"; then
        evolution_checkpoint "$ARQUIVO" "pass" "$TITULO"
        echo
        echo "$TITULO: OK"
    else
        local CODIGO=$?
        evolution_checkpoint "$ARQUIVO" "fail" "$TITULO"
        echo
        echo "ERRO: $TITULO falhou. Código: $CODIGO"
        evolution_finish "FAILED"
        exit "$CODIGO"
    fi
}

# =====================================================
# PREFLIGHT + HEALTH
# =====================================================

rodar_shell "PREFLIGHT CHECK" "preflight_check.sh"
rodar_shell "HEALTH CHECK" "health_check.sh"

# =====================================================
# PIPELINE PRINCIPAL
# =====================================================

rodar_python "1/12 - TOPIC ENGINE" "topic_engine_runtime.py"
rodar_python "2/12 - ROTEIRO + PESQUISA FACTUAL" "roteiro.py"
rodar_python "3/12 - CONFIRMANDO ASSUNTO USADO" "used_topic.py"
rodar_python "4/12 - HOOK ENGINE" "hook_runtime.py"
rodar_python "4B/12 - NARRATIVE DIRECTOR 3.2" "narrative_director.py"
rodar_python "4C/12 - COLD OPEN DIRECTOR 3.3" "cold_open_director.py"
rodar_python "5/12 - SCENE DIRECTOR + RELEVÂNCIA" "scene_director.py"
rodar_python "5A0/12 - SCENE TRUTH REFINER" "scene_truth_refiner_6_7.py"
rodar_python "5A/12 - DOCUMENTARY DIRECTOR" "documentary_director.py"
rodar_python "5B/12 - VISUAL DIRECTOR" "visual_director.py"
rodar_python "5B1/12 - HUMANIZED SHOT GRAMMAR" "visual_shot_bridge.py"
rodar_python "5C/12 - FACTUAL VISUAL RISK GUARD" "visual_risk_guard.py"
rodar_python "5D/12 - EDITORIAL CONTINUITY GUARD" "editorial_continuity.py"
rodar_python "5D1/12 - LOSSLESS SCENE COVERAGE REPAIR" "scene_lossless_repair.py"
rodar_python "5D2/12 - POST-SCRIPT TRUTH LOCK" "post_script_truth_lock.py"
rodar_python "5E/12 - SEMANTIC INTEGRITY GATE" "semantic_integrity_gate.py"
rodar_python "6/12 - SMART MEDIA SELECTOR" "midia.py"
rodar_python "6A/12 - MEDIA MASTER GATE" "media_master_gate.py"
rodar_python "6B/12 - CINEMATIC MOTION DIRECTOR" "motion_director.py"
rodar_python "6C/12 - MONTAGE RHYTHM DIRECTOR" "rhythm_director.py"

if [ "$SAP_PRO_EDIT" = "1" ]; then
    rodar_python "6C1/12 - PROFESSIONAL EDIT DIRECTOR" "professional_edit_director.py"
    rodar_python "6C2/12 - PROFESSIONAL EDIT AUTO-REPAIR" "professional_edit_repair.py"
fi

rodar_python "6D/12 - PRODUCTION SUPERVISOR" "production_supervisor.py"
rodar_python "6D1/12 - EVOLUTION VISUAL AUDIT" "shortautopro_evolution.py" visual-audit
rodar_python "6E/12 - FINAL EDITORIAL GATE" "editorial_gate.py"
rodar_python "7/12 - GERANDO VOZ PIPER" "audio.py"
rodar_python "8/12 - WHISPER + LEGENDA DINÂMICA" "legenda_dinamica.py"

if [ "$SAP_PRO_EDIT" = "1" ]; then
    rodar_python "8A/12 - PROFESSIONAL CAPTION DIRECTOR" "professional_caption_director.py"
fi

rodar_python "8B/12 - EVOLUTION CAPTION AUDIT" "shortautopro_evolution.py" caption-audit

if [ "$SAP_PRO_EDIT" = "1" ]; then
    rodar_python "9/12 - PROFESSIONAL SCENE ASSEMBLER" "video_professional.py"
else
    rodar_python "9/12 - MONTANDO CENAS SEMÂNTICAS" "video.py"
fi

# =====================================================
# RENDER FINAL — RUNTIME ÚNICO, IMPLEMENTAÇÃO POR MODO
# =====================================================

if [ "$SAP_PRO_EDIT" = "1" ]; then
    RENDER_LABEL="10/12 - RENDER FINAL V6 PROFESSIONAL"
    VERSAO="V6 PROFESSIONAL UNIFIED + EVOLUTION 1.2"
else
    RENDER_LABEL="10/12 - RENDER FINAL V6 STANDARD"
    VERSAO="V6 STANDARD ROLLBACK + EVOLUTION 1.2"
fi

echo
echo "--------------------------------------"
echo "$RENDER_LABEL"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/v6_runtime.py" ]; then
    echo "ERRO: v6_runtime.py não encontrado."
    evolution_checkpoint "v6_runtime.py" "fail" "$RENDER_LABEL"
    evolution_finish "FAILED"
    exit 1
fi

evolution_checkpoint "v6_runtime.py" "start" "$RENDER_LABEL"
if python "$BASE/v6_runtime.py"; then
    FINAL="$BASE/videos/short_v6_${SHORT_ID}.mp4"
    evolution_checkpoint "v6_runtime.py" "pass" "$RENDER_LABEL"
else
    CODIGO=$?
    evolution_checkpoint "v6_runtime.py" "fail" "$RENDER_LABEL"
    evolution_finish "FAILED"
    echo "ERRO: render V6 falhou. Nenhum pipeline legado será usado como fallback."
    exit "$CODIGO"
fi

if [ ! -s "$FINAL" ]; then
    evolution_checkpoint "final_video" "fail" "FINAL VIDEO EXISTS"
    evolution_finish "FAILED"
    echo "ERRO: vídeo final não encontrado ou vazio: $FINAL"
    exit 1
fi

evolution_checkpoint "final_video" "start" "FINAL VIDEO EXISTS"
evolution_checkpoint "final_video" "pass" "FINAL VIDEO EXISTS"

# =====================================================
# GATES FINAIS
# =====================================================

rodar_python "10A/12 - EVOLUTION E2E VIDEO CHECK" "shortautopro_evolution.py" e2e
rodar_python "10B/12 - QUALITY GATE" "quality_check.py"
rodar_python "11A/12 - PUBLISH PACK" "publish_pack.py"
rodar_python "11B/12 - SOURCE & ATTRIBUTION LEDGER" "source_ledger.py"
rodar_python "11C/12 - PUBLISH INTEGRITY GATE" "publish_integrity_gate.py"
rodar_python "12A/12 - PRODUCTION MANIFEST" "production_manifest.py"
rodar_python "12B/12 - FINAL QUALITY GATE" "final_quality.py"

# O score Evolution continua observacional por padrão até calibração suficiente.
if [ "${SAP_EVOLUTION_ENFORCE:-0}" = "1" ]; then
    rodar_python "12C/12 - EVOLUTION QUALITY SCORE (ENFORCED)" "shortautopro_evolution.py" quality-score --enforce
else
    rodar_python "12C/12 - EVOLUTION QUALITY SCORE" "shortautopro_evolution.py" quality-score
fi

if [ "$SAP_PRO_EDIT" = "1" ]; then
    rodar_python "12D/12 - PROFESSIONAL QUALITY GATE" "professional_quality_gate.py"
fi

# =====================================================
# COPIAR PARA DOWNLOADS
# =====================================================

echo
echo "--------------------------------------"
echo "COPIANDO PARA DOWNLOADS"
echo "--------------------------------------"
echo

DOWNLOADS="$HOME/storage/shared/Download"
DESTINO="$FINAL"

if [ -d "$DOWNLOADS" ]; then
    CANDIDATO="$DOWNLOADS/ShortAutoPro_${SHORT_ID}.mp4"
    if cp "$FINAL" "$CANDIDATO" && [ -s "$CANDIDATO" ]; then
        DESTINO="$CANDIDATO"
        echo "Cópia concluída: $DESTINO"
    else
        echo "AVISO: falha ao copiar para Downloads."
        echo "Vídeo preservado em: $FINAL"
    fi
else
    echo "AVISO: Downloads não encontrada."
    echo "Vídeo preservado em: $FINAL"
fi

# =====================================================
# REGISTRAR ASSUNTO
# =====================================================

rodar_python "REGISTRANDO ASSUNTO" "register_topic.py"

# =====================================================
# INFORMAÇÕES DO VÍDEO
# =====================================================

DURACAO="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null || true)"
WIDTH="$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null || true)"
HEIGHT="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null || true)"
FPS_FINAL="$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of default=noprint_wrappers=1:nokey=1 "$FINAL" 2>/dev/null || true)"
TAMANHO="$(du -h "$FINAL" 2>/dev/null | cut -f1 || true)"

USED_TOPIC="$BASE/roteiros/used_topic_${SHORT_ID}.txt"
TOPIC="$BASE/roteiros/topic_${SHORT_ID}.txt"
ROTEIRO="$BASE/roteiros/short_${SHORT_ID}.txt"
HOOK="$BASE/roteiros/hook_${SHORT_ID}.txt"
FONTE="$BASE/roteiros/fonte_${SHORT_ID}.txt"
MAPA="$BASE/roteiros/scene_map_${SHORT_ID}.json"
KEYWORDS="$BASE/roteiros/keywords_${SHORT_ID}.txt"
EVOLUTION_REPORT="$BASE/manifests/${SHORT_ID}_evolution.json"
PROFESSIONAL_REPORT="$BASE/manifests/${SHORT_ID}_professional.json"

# =====================================================
# RESUMO
# =====================================================

echo
echo "======================================"
echo " SHORT PRO PRONTO!"
echo "======================================"
echo "ID: $SHORT_ID"
echo "VERSÃO: $VERSAO"
echo "PIPELINE: $PIPELINE_LABEL"
QUALITY_REPORT="$BASE/manifests/${SHORT_ID}_quality.json"
QUALITY_STATUS="$(python - "$QUALITY_REPORT" "$EVOLUTION_REPORT" "$PROFESSIONAL_REPORT" "${SAP_EVOLUTION_ENFORCE:-0}" "${SAP_PRO_EDIT:-1}" <<'PYQUALITY'
import json
import sys
from pathlib import Path

quality_path = Path(sys.argv[1])
evolution_path = Path(sys.argv[2])
professional_path = Path(sys.argv[3])
evolution_enforced = sys.argv[4] == "1"
professional_mode = sys.argv[5] == "1"


def load(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


quality = load(quality_path)
evolution = load(evolution_path)
professional = load(professional_path)

if not quality.get("approved", False):
    print("BLOCK")
    raise SystemExit(0)

status = str(evolution.get("status", "UNKNOWN") or "UNKNOWN").upper()
score = evolution.get("total_score")
threshold = evolution.get("threshold")

if status == "PASS":
    base = f"PASS (EVOLUTION {score}/{threshold})" if score is not None and threshold is not None else "PASS"
elif evolution_enforced:
    base = f"BLOCK (EVOLUTION {status})"
else:
    base = f"REVIEW (EVOLUTION {status}, OBSERVATION)"

if professional_mode and professional:
    pro_status = str(professional.get("status", "UNKNOWN") or "UNKNOWN").upper()
    pro_score = professional.get("score")
    pro_threshold = professional.get("threshold")
    base += f" | PROFESSIONAL {pro_status} {pro_score}/{pro_threshold}"

print(base)
PYQUALITY
)"
echo "QUALITY: ${QUALITY_STATUS:-UNKNOWN}"
echo "DURAÇÃO: ${DURACAO:-?}s"
echo "RESOLUÇÃO: ${WIDTH:-?}x${HEIGHT:-?}"
echo "FPS: ${FPS_FINAL:-?}"
echo "TAMANHO: ${TAMANHO:-?}"
echo

echo "ASSUNTO:"
if [ -f "$USED_TOPIC" ]; then
    cat "$USED_TOPIC"
elif [ -f "$TOPIC" ]; then
    cat "$TOPIC"
else
    echo "desconhecido"
fi

echo
if [ -f "$HOOK" ]; then
    echo "HOOK:"
    cat "$HOOK"
    echo
fi

echo "VÍDEO: $DESTINO"
echo "ROTEIRO: $ROTEIRO"
echo "BUSCAS VISUAIS: $KEYWORDS"
echo "FONTE FACTUAL: $FONTE"
echo "MAPA SEMÂNTICO: $MAPA"
echo "EVOLUTION REPORT: $EVOLUTION_REPORT"
if [ "$SAP_PRO_EDIT" = "1" ]; then
    echo "PROFESSIONAL REPORT: $PROFESSIONAL_REPORT"
fi
echo "LOG: $LOG"
echo

# =====================================================
# STORAGE GUARD
# =====================================================

if [ -f "$BASE/limpar_storage.sh" ]; then
    echo "--------------------------------------"
    echo "STORAGE GUARD"
    echo "--------------------------------------"
    if bash "$BASE/limpar_storage.sh" --execute; then
        echo "Storage Guard: OK"
    else
        echo "AVISO: Storage Guard apresentou erro."
    fi
fi

evolution_checkpoint "pipeline" "pass" "ShortAutoPro production"
evolution_finish "SUCCESS"

echo
echo "--------------------------------------"
echo "ARMAZENAMENTO"
echo "--------------------------------------"
df -h "$HOME" | tail -1 || true

echo
echo "======================================"
echo " PRODUÇÃO FINALIZADA"
echo "======================================"
echo "ID: $SHORT_ID"
echo "STATUS: ${QUALITY_STATUS:-UNKNOWN}"
echo "FIM: $(date)"
