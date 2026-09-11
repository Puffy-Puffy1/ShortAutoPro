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

ID="$(date +%F_%H%M)"
export SHORT_ID="$ID"

LOG_DIR="$BASE/logs/producao"
mkdir -p "$LOG_DIR"

LOG="$LOG_DIR/short_${SHORT_ID}.log"

exec > >(tee -a "$LOG") 2>&1

echo
echo "======================================"
echo " SHORTAUTO PRO - STABLE 1.7"
echo "======================================"
echo
echo "ID: $SHORT_ID"
echo "INÍCIO: $(date)"
echo "LOG: $LOG"
echo

cd "$BASE"

# ======================================
# CONFIG
# ======================================

if [ -f "$BASE/config.sh" ]; then
    source "$BASE/config.sh"
else
    echo "ERRO: config.sh não encontrado."
    exit 1
fi

# ======================================
# HEALTH CHECK
# ======================================

echo
echo "--------------------------------------"
echo "HEALTH CHECK"
echo "--------------------------------------"
echo

if [ -x "$BASE/health_check.sh" ]; then

    if "$BASE/health_check.sh"; then
        echo
        echo "Health Check: OK"
    else
        echo
        echo "ERRO: Health Check falhou."
        exit 1
    fi

else

    echo "ERRO: health_check.sh não encontrado."
    exit 1

fi

# ======================================
# FUNÇÃO DAS ETAPAS
# ======================================

rodar() {

    TITULO="$1"
    ARQUIVO="$2"

    echo
    echo "--------------------------------------"
    echo "$TITULO"
    echo "--------------------------------------"
    echo

    INICIO_ETAPA=$(date +%s)

    if python "$BASE/$ARQUIVO"; then

        FIM_ETAPA=$(date +%s)
        TEMPO=$((FIM_ETAPA - INICIO_ETAPA))

        echo
        echo "ETAPA OK: ${TEMPO}s"

    else

        CODIGO=$?

        echo
        echo "ERRO NA ETAPA:"
        echo "$TITULO"
        echo
        echo "Arquivo:"
        echo "$ARQUIVO"
        echo
        echo "Código: $CODIGO"

        exit "$CODIGO"

    fi
}

# ======================================
# PIPELINE STABLE 1.4
# ======================================

rodar \
"1/12 - TOPIC ENGINE" \
"topic_engine.py"

rodar \
"2/12 - ROTEIRO + PESQUISA FACTUAL" \
"roteiro.py"

rodar \
"3/12 - CONFIRMANDO ASSUNTO USADO" \
"used_topic.py"

rodar \
"4/12 - HOOK ENGINE" \
"hook_engine.py"

rodar \
"4B/12 - NARRATIVE DIRECTOR 3.2" \
"narrative_director.py"

rodar \
"4C/12 - COLD OPEN DIRECTOR 3.3" \
"cold_open_director.py"

rodar \
"5/12 - SCENE DIRECTOR + RELEVÂNCIA" \
"scene_director.py"

rodar \
"5A0/12 - SCENE TRUTH REFINER 6.7" \
"scene_truth_refiner_6_7.py"

rodar \
"5A/12 - DOCUMENTARY DIRECTOR 3.1" \
"documentary_director.py"

rodar \
"5B/12 - VISUAL DIRECTOR PASS 3.0" \
"visual_director.py"

rodar \
"5C/12 - FACTUAL VISUAL RISK GUARD" \
"visual_risk_guard.py"

rodar \
"5D/12 - EDITORIAL CONTINUITY GUARD 4.4" \
"editorial_continuity.py"


rodar \
"5D1/12 - LOSSLESS SCENE COVERAGE REPAIR 6.2" \
"scene_lossless_repair.py"

echo
echo "--------------------------------------"
echo "5D2/12 - POST-SCRIPT TRUTH LOCK 6.2"
echo "--------------------------------------"
echo

python "$BASE/post_script_truth_lock.py"

CODIGO=$?

if [ "$CODIGO" -ne 0 ]; then

    echo
    echo "======================================"
    echo " POST-SCRIPT TRUTH LOCK: BLOCK"
    echo "======================================"
    echo
    echo "Topic/fonte/roteiro/cenas não passaram"
    echo "pela validação de identidade."
    echo "Nenhuma mídia será produzida."
    echo "Código: $CODIGO"

    exit "$CODIGO"
fi

echo
echo "POST-SCRIPT TRUTH LOCK: OK"
echo

rodar \
"5E/12 - SEMANTIC INTEGRITY GATE 5.1" \
"semantic_integrity_gate.py"

rodar \
"6/12 - SMART MEDIA SELECTOR" \
"midia.py"


rodar \
"6A/12 - MEDIA MASTER GATE 5.1" \
"media_master_gate.py"

rodar \
"6B/12 - CINEMATIC MOTION DIRECTOR 3.8" \
"motion_director.py"

rodar \
"6C/12 - MONTAGE RHYTHM DIRECTOR 4.3" \
"rhythm_director.py"

rodar \
"6D/12 - PRODUCTION SUPERVISOR 5.0" \
"production_supervisor.py"

rodar \
"6E/12 - FINAL EDITORIAL GATE 5.0" \
"editorial_gate.py"

rodar \
"7/12 - GERANDO VOZ PIPER" \
"audio.py"

rodar \
"8/12 - WHISPER + LEGENDA DINÂMICA" \
"legenda_dinamica.py"

rodar \
"9/12 - MONTANDO CENAS SEMÂNTICAS" \
"video.py"

# ======================================
# 9/9 - RENDER FINAL
# ======================================

echo
echo "--------------------------------------"
echo "10/12 - RENDER FINAL"
echo "--------------------------------------"
echo

VERSAO=""
FINAL=""

if python "$BASE/v6.py"; then

    FINAL="$BASE/videos/short_v6_${SHORT_ID}.mp4"
    VERSAO="V6 STABLE 1.4"

else

    echo
    echo "AVISO: render V6 falhou."
    echo "Tentando V5 como fallback..."
    echo

    if [ ! -f "$BASE/v5.py" ]; then
        echo "ERRO: v5.py não encontrado."
        exit 1
    fi

    if python "$BASE/v5.py"; then

        FINAL="$BASE/videos/short_v5_${SHORT_ID}.mp4"
        VERSAO="V5 FALLBACK"

    else

        echo
        echo "ERRO: V6 e V5 falharam."
        exit 1

    fi

fi

# ======================================
# VERIFICAR ARQUIVO FINAL
# ======================================

if [ ! -f "$FINAL" ]; then

    echo
    echo "ERRO: vídeo final não encontrado."
    echo "$FINAL"

    exit 1

fi

# ======================================
# QUALITY GATE
# ======================================

echo
echo "--------------------------------------"
echo "QUALITY GATE"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/quality_check.py" ]; then
    echo "ERRO: quality_check.py não encontrado."
    exit 1
fi

if python "$BASE/quality_check.py"; then

    echo
    echo "Quality Gate: PASS"

else

    CODIGO=$?

    echo
    echo "======================================"
    echo " QUALITY GATE: FAIL"
    echo "======================================"
    echo
    echo "O vídeo não será copiado para Downloads."
    echo "O assunto também NÃO será registrado no histórico."
    echo
    echo "Código: $CODIGO"

    exit "$CODIGO"

fi

# ======================================
# 11A/12 - PUBLISH PACK
# ======================================

echo
echo "--------------------------------------"
echo "11A/12 - PUBLISH PACK"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/publish_pack.py" ]; then
    echo "ERRO: publish_pack.py não encontrado."
    exit 1
fi

if python "$BASE/publish_pack.py"; then

    echo
    echo "Publish Pack: OK"

else

    CODIGO=$?

    echo
    echo "======================================"
    echo " PUBLISH PACK: FAIL"
    echo "======================================"
    echo
    echo "Metadados de publicação não foram validados."
    echo "O assunto NÃO será registrado."
    echo "Código: $CODIGO"

    exit "$CODIGO"

fi


# ======================================
# 11B/12 - SOURCE LEDGER
# ======================================

echo
echo "--------------------------------------"
echo "11B/12 - SOURCE & ATTRIBUTION LEDGER"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/source_ledger.py" ]; then
    echo "ERRO: source_ledger.py não encontrado."
    exit 1
fi

if python "$BASE/source_ledger.py"; then

    echo
    echo "Source Ledger: OK"

else

    CODIGO=$?

    echo
    echo "======================================"
    echo " SOURCE LEDGER: FAIL"
    echo "======================================"
    echo
    echo "A rastreabilidade/atribuição da mídia falhou."
    echo "O assunto NÃO será registrado."
    echo "Código: $CODIGO"

    exit "$CODIGO"

fi


# ======================================
# 11C/12 - PUBLISH INTEGRITY
# ======================================

echo
echo "--------------------------------------"
echo "11C/12 - PUBLISH INTEGRITY GATE 5.1"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/publish_integrity_gate.py" ]; then
    echo "ERRO: publish_integrity_gate.py não encontrado."
    exit 1
fi

if python "$BASE/publish_integrity_gate.py"; then

    echo
    echo "Publish Integrity: PASS"

else

    CODIGO=$?

    echo
    echo "======================================"
    echo " PUBLISH INTEGRITY: BLOCK"
    echo "======================================"
    echo
    echo "Título/descrição não passaram pela validação."
    echo "O assunto NÃO será registrado."
    echo "Código: $CODIGO"

    exit "$CODIGO"

fi


# ======================================
# 12A/12 - PRODUCTION MANIFEST
# ======================================

echo
echo "--------------------------------------"
echo "12A/12 - PRODUCTION MANIFEST"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/production_manifest.py" ]; then
    echo "ERRO: production_manifest.py não encontrado."
    exit 1
fi

if python "$BASE/production_manifest.py"; then

    echo
    echo "Production Manifest: OK"

else

    CODIGO=$?

    echo
    echo "======================================"
    echo " PRODUCTION MANIFEST: FAIL"
    echo "======================================"
    echo
    echo "O pacote da produção ficou incompleto."
    echo "O assunto NÃO será registrado."
    echo "Código: $CODIGO"

    exit "$CODIGO"

fi


# ======================================
# 12B/12 - FINAL QUALITY
# ======================================

echo
echo "--------------------------------------"
echo "12B/12 - FINAL QUALITY GATE"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/final_quality.py" ]; then
    echo "ERRO: final_quality.py não encontrado."
    exit 1
fi

if python "$BASE/final_quality.py"; then

    echo
    echo "Final Quality: PASS"

else

    CODIGO=$?

    echo
    echo "======================================"
    echo " FINAL QUALITY: BLOCK"
    echo "======================================"
    echo
    echo "A produção não recebeu aprovação final."
    echo "O assunto NÃO será registrado."
    echo "Código: $CODIGO"

    exit "$CODIGO"

fi


# ======================================
# REGISTRAR ASSUNTO
# SOMENTE APÓS TODOS OS GATES
# ======================================

echo
echo "--------------------------------------"
echo "REGISTRANDO ASSUNTO"
echo "--------------------------------------"
echo

if [ ! -f "$BASE/register_topic.py" ]; then

    echo "ERRO: register_topic.py não encontrado."
    echo "O histórico não será atualizado."
    exit 1

fi


if python "$BASE/register_topic.py"; then

    echo
    echo "Registro de assunto: OK"

else

    CODIGO=$?

    echo
    echo "======================================"
    echo " REGISTRO DE ASSUNTO: FAIL"
    echo "======================================"
    echo
    echo "O vídeo permanece preservado,"
    echo "mas a produção não será marcada"
    echo "como totalmente finalizada."
    echo "Código: $CODIGO"

    exit "$CODIGO"

fi


# ======================================
# INFORMAÇÕES DO VÍDEO
# ======================================

DURACAO="$(
    ffprobe \
    -v error \
    -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 \
    "$FINAL" 2>/dev/null || true
)"

WIDTH="$(
    ffprobe \
    -v error \
    -select_streams v:0 \
    -show_entries stream=width \
    -of default=noprint_wrappers=1:nokey=1 \
    "$FINAL" 2>/dev/null || true
)"

HEIGHT="$(
    ffprobe \
    -v error \
    -select_streams v:0 \
    -show_entries stream=height \
    -of default=noprint_wrappers=1:nokey=1 \
    "$FINAL" 2>/dev/null || true
)"

FPS="$(
    ffprobe \
    -v error \
    -select_streams v:0 \
    -show_entries stream=avg_frame_rate \
    -of default=noprint_wrappers=1:nokey=1 \
    "$FINAL" 2>/dev/null || true
)"

TAMANHO="$(
    du -h "$FINAL" 2>/dev/null \
    | cut -f1
)"

# ======================================
# COPIAR PARA DOWNLOADS
# ======================================

echo
echo "--------------------------------------"
echo "COPIANDO PARA DOWNLOADS"
echo "--------------------------------------"
echo

DOWNLOADS="$HOME/storage/shared/Download"

if [ -d "$DOWNLOADS" ]; then

    DESTINO="$DOWNLOADS/ShortAutoPro_${SHORT_ID}.mp4"

    cp "$FINAL" "$DESTINO"

    if [ ! -f "$DESTINO" ]; then
        echo "ERRO: falha ao copiar para Downloads."
        exit 1
    fi

    echo "Cópia concluída."
    echo "$DESTINO"

else

    DESTINO="$FINAL"

    echo "AVISO: Downloads não encontrada."
    echo "Vídeo mantido em:"
    echo "$FINAL"

fi

# ======================================
# ARQUIVOS DA PRODUÇÃO
# ======================================

USED_TOPIC="$BASE/roteiros/used_topic_${SHORT_ID}.txt"
TOPIC="$BASE/roteiros/topic_${SHORT_ID}.txt"
ROTEIRO="$BASE/roteiros/short_${SHORT_ID}.txt"
HOOK="$BASE/roteiros/hook_${SHORT_ID}.txt"
FONTE="$BASE/roteiros/fonte_${SHORT_ID}.txt"
MAPA="$BASE/roteiros/scene_map_${SHORT_ID}.json"
KEYWORDS="$BASE/roteiros/keywords_${SHORT_ID}.txt"

# ======================================
# RESUMO
# ======================================

echo
echo "======================================"
echo " SHORT PRO PRONTO!"
echo "======================================"
echo
echo "ID: $SHORT_ID"
echo "VERSÃO: $VERSAO"
echo "QUALITY: PASS"
echo "DURAÇÃO: ${DURACAO:-?}s"
echo "RESOLUÇÃO: ${WIDTH:-?}x${HEIGHT:-?}"
echo "FPS: ${FPS:-?}"
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
    echo
    echo "HOOK:"
    cat "$HOOK"
    echo
fi

echo
echo "VÍDEO:"
echo "$DESTINO"
echo
echo "ROTEIRO:"
echo "$ROTEIRO"
echo
echo "BUSCAS VISUAIS:"
echo "$KEYWORDS"
echo
echo "FONTE FACTUAL:"
echo "$FONTE"
echo
echo "MAPA SEMÂNTICO:"
echo "$MAPA"
echo
echo "LOG:"
echo "$LOG"
echo

# ======================================
# STORAGE GUARD
# ======================================

echo
echo "--------------------------------------"
echo "STORAGE GUARD"
echo "--------------------------------------"
echo

if [ -x "$BASE/limpar_storage.sh" ]; then

    if "$BASE/limpar_storage.sh" --execute; then
        echo
        echo "Storage Guard: OK"
    else
        echo
        echo "AVISO: Storage Guard apresentou erro."
    fi

else

    echo "AVISO: limpar_storage.sh não encontrado."

fi

# ======================================
# ARMAZENAMENTO
# ======================================

echo
echo "--------------------------------------"
echo "ARMAZENAMENTO"
echo "--------------------------------------"
echo

df -h "$HOME" | tail -1

# ======================================
# FINAL
# ======================================

echo
echo "======================================"
echo " PRODUÇÃO FINALIZADA"
echo "======================================"
echo
echo "ID: $SHORT_ID"
echo "STATUS: QUALITY PASS"
echo "FIM: $(date)"
echo
