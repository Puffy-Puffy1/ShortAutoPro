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

set -e
set -o pipefail

BASE="$HOME/ShortAutoPro"

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
# Mantém SHORT_ID fornecido explicitamente para reprodução/debug.
# Em produção normal usa segundos + PID, eliminando colisões de lote.

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
echo " SHORTAUTO PRO - STABLE 1.9"
echo "======================================"
echo
echo "ID: $SHORT_ID"
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
# HELPERS
# =====================================================

rodar_python() {
    TITULO="$1"
    ARQUIVO="$2"

    echo
    echo "--------------------------------------"
    echo "$TITULO"
    echo "--------------------------------------"
    echo

    if [ ! -f "$BASE/$ARQUIVO" ]; then
        echo "ERRO: arquivo obrigatório não encontrado: $ARQUIVO"
        exit 1
    fi

    INICIO_ETAPA="$(date +%s)"

    if python "$BASE/$ARQUIVO"; then
        FIM_ETAPA="$(date +%s)"
        TEMPO="$((FIM_ETAPA - INICIO_ETAPA))"
        echo
        echo "ETAPA OK: ${TEMPO}s"
    else
        CODIGO=$?
        echo
        echo "ERRO NA ETAPA: $TITULO"
        echo "Arquivo: $ARQUIVO"
        echo "Código: $CODIGO"
        exit "$CODIGO"
    fi
}

rodar_shell() {
    TITULO="$1"
    ARQUIVO="$2"
    shift 2

    echo
    echo "--------------------------------------"
    echo "$TITULO"
    echo "--------------------------------------"
    echo

    if [ ! -f "$BASE/$ARQUIVO" ]; then
        echo "ERRO: arquivo obrigatório não encontrado: $ARQUIVO"
        exit 1
    fi

    if bash "$BASE/$ARQUIVO" "$@"; then
        echo
        echo "$TITULO: OK"
    else
        CODIGO=$?
        echo
        echo "ERRO: $TITULO falhou. Código: $CODIGO"
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

rodar_python "1/12 - TOPIC ENGINE" "topic_engine.py"
rodar_python "2/12 - ROTEIRO + PESQUISA FACTUAL" "roteiro.py"
rodar_python "3/12 - CONFIRMANDO ASSUNTO USADO" "used_topic.py"
rodar_python "4/12 - HOOK ENGINE" "hook_engine.py"
rodar_python "4B/12 - NARRATIVE DIRECTOR 3.2" "narrative_director.py"
rodar_python "4C/12 - COLD OPEN DIRECTOR 3.3" "cold_open_director.py"
rodar_python "5/12 - SCENE DIRECTOR + RELEVÂNCIA" "scene_director.py"
rodar_python "5A0/12 - SCENE TRUTH REFINER" "scene_truth_refiner_6_7.py"
rodar_python "5A/12 - DOCUMENTARY DIRECTOR" "documentary_director.py"
rodar_python "5B/12 - VISUAL DIRECTOR" "visual_director.py"
rodar_python "5C/12 - FACTUAL VISUAL RISK GUARD" "visual_risk_guard.py"
rodar_python "5D/12 - EDITORIAL CONTINUITY GUARD" "editorial_continuity.py"
rodar_python "5D1/12 - LOSSLESS SCENE COVERAGE REPAIR" "scene_lossless_repair.py"
rodar_python "5D2/12 - POST-SCRIPT TRUTH LOCK" "post_script_truth_lock.py"
rodar_python "5E/12 - SEMANTIC INTEGRITY GATE" "semantic_integrity_gate.py"
rodar_python "6/12 - SMART MEDIA SELECTOR" "midia_runtime.py"
rodar_python "6A/12 - MEDIA MASTER GATE" "media_master_gate.py"
rodar_python "6B/12 - CINEMATIC MOTION DIRECTOR" "motion_director.py"
rodar_python "6C/12 - MONTAGE RHYTHM DIRECTOR" "rhythm_director.py"
rodar_python "6D/12 - PRODUCTION SUPERVISOR" "production_supervisor.py"
rodar_python "6E/12 - FINAL EDITORIAL GATE" "editorial_gate.py"
rodar_python "7/12 - GERANDO VOZ PIPER" "audio.py"
rodar_python "8/12 - WHISPER + LEGENDA DINÂMICA" "legenda_dinamica.py"
rodar_python "9/12 - MONTANDO CENAS SEMÂNTICAS" "video.py"

# =====================================================
# RENDER FINAL — APENAS PIPELINE V6
# =====================================================
# v6_runtime supervisiona timeout, remove saída velha e valida a saída do
# renderer real. Não existe fallback silencioso para pipeline legado.

echo
echo "--------------------------------------"
echo "10/12 - RENDER FINAL V6"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/v6_runtime.py" ]; then
    echo "ERRO: v6_runtime.py não encontrado."
    exit 1
fi

if python "$BASE/v6_runtime.py"; then
    FINAL="$BASE/videos/short_v6_${SHORT_ID}.mp4"
    VERSAO="V6 PRINCIPAL"
else
    CODIGO=$?
    echo "ERRO: render V6 falhou. Nenhum pipeline legado será usado como fallback."
    exit "$CODIGO"
fi

if [ ! -s "$FINAL" ]; then
    echo "ERRO: vídeo final não encontrado ou vazio: $FINAL"
    exit 1
fi

# =====================================================
# GATES FINAIS
# =====================================================

rodar_python "10B/12 - QUALITY GATE" "quality_check.py"
rodar_python "11A/12 - PUBLISH PACK" "publish_pack.py"
rodar_python "11B/12 - SOURCE & ATTRIBUTION LEDGER" "source_ledger.py"
rodar_python "11C/12 - PUBLISH INTEGRITY GATE" "publish_integrity_gate.py"
rodar_python "12A/12 - PRODUCTION MANIFEST" "production_manifest.py"
rodar_python "12B/12 - FINAL QUALITY GATE" "final_quality.py"

# =====================================================
# COPIAR PARA DOWNLOADS
# =====================================================
# A cópia é conveniência. Falha de armazenamento compartilhado não invalida
# um vídeo que já passou pelos gates e permanece preservado em $FINAL.

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
# Só ocorre depois de todos os gates e após a tentativa de entrega.

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

# =====================================================
# RESUMO
# =====================================================

echo
echo "======================================"
echo " SHORT PRO PRONTO!"
echo "======================================"
echo "ID: $SHORT_ID"
echo "VERSÃO: $VERSAO"
echo "QUALITY: PASS"
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
echo "STATUS: QUALITY PASS"
echo "FIM: $(date)"
