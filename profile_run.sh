#!/data/data/com.termux/files/usr/bin/bash

set -e
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
PROFILE_RUNTIME="$BASE/profile_runtime.py"
GENERATOR="$BASE/gerar_short.sh"

PROFILE="${1:-${SAP_CHANNEL_PROFILE:-default}}"

if [ ! -f "$PROFILE_RUNTIME" ]; then
    echo "ERRO: profile_runtime.py não encontrado."
    exit 1
fi

PROFILE_EXPORTS="$(python "$PROFILE_RUNTIME" --profile "$PROFILE" --shell)" || exit $?
# A saída vem exclusivamente de chaves allow-listed e usa shlex.quote.
eval "$PROFILE_EXPORTS"

export SAP_PRO_EDIT="${SAP_PRO_EDIT:-1}"
export SAP_PROFESSIONAL_MIN_SCORE="${SAP_PROFESSIONAL_MIN_SCORE:-88}"
export SAP_PROFESSIONAL_ENFORCE="${SAP_PROFESSIONAL_ENFORCE:-0}"
export SAP_PRO_MEDIA_MIN_PIXELS="${SAP_PRO_MEDIA_MIN_PIXELS:-921600}"

if [ "$SAP_PRO_EDIT" = "1" ]; then
    PIPELINE_LABEL="PROFESSIONAL"
else
    PIPELINE_LABEL="STANDARD_ROLLBACK"
fi

if [ ! -f "$GENERATOR" ]; then
    echo "ERRO: gerador canônico não encontrado: $GENERATOR"
    exit 1
fi

echo "========================================"
echo " SHORTAUTOPRO - PROFILED RUN"
echo "========================================"
echo "Perfil: $SAP_CHANNEL_PROFILE"
echo "Pipeline: $PIPELINE_LABEL"
echo "Professional score alvo: $SAP_PROFESSIONAL_MIN_SCORE"
echo "Professional enforce: $SAP_PROFESSIONAL_ENFORCE"
echo "Cenas: $SHORT_QTD_CENAS"
echo "Idioma: $SHORT_LANGUAGE"
echo "Duração alvo: ${SHORT_TARGET_DURATION_SECONDS}s"
echo "Visual mínimo: $SAP_VISUAL_MIN_SCORE"
echo "Voz: $PIPER_MODEL"
if [ -n "${SHORT_TOPIC_EXACT:-}" ]; then
    echo "Assunto exato: $SHORT_TOPIC_EXACT"
elif [ -n "${SHORT_TEMA:-}" ]; then
    echo "Tema: $SHORT_TEMA"
fi
echo "========================================"
echo

exec bash "$GENERATOR"
