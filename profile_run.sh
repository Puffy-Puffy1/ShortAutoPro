#!/data/data/com.termux/files/usr/bin/bash
set -e
set -o pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
PROFILE_RUNTIME="$BASE/profile_runtime.py"
MAIN="$BASE/main.py"
PROFILE="${1:-${SAP_CHANNEL_PROFILE:-default}}"

if [ ! -f "$PROFILE_RUNTIME" ]; then
    echo "ERRO: profile_runtime.py não encontrado."
    exit 1
fi

PROFILE_EXPORTS="$(python "$PROFILE_RUNTIME" --profile "$PROFILE" --shell)" || exit $?
# Saída trusted/allow-listed do profile_runtime.
eval "$PROFILE_EXPORTS"

export SAP_PROFESSIONAL_MIN_SCORE="${SAP_PROFESSIONAL_MIN_SCORE:-88}"
export SAP_PROFESSIONAL_ENFORCE="${SAP_PROFESSIONAL_ENFORCE:-0}"
export SAP_PRO_MEDIA_MIN_PIXELS="${SAP_PRO_MEDIA_MIN_PIXELS:-921600}"
export SAP_RELEASE_ENFORCE="${SAP_RELEASE_ENFORCE:-1}"

if [ ! -f "$MAIN" ]; then
    echo "ERRO: entrada oficial não encontrada: $MAIN"
    exit 1
fi

echo "========================================"
echo " SHORTAUTOPRO - PROFILED RUN 3.0"
echo "========================================"
echo "Perfil: $SAP_CHANNEL_PROFILE"
echo "Entrada: main.py"
echo "Pipeline: PROFESSIONAL_CANONICAL"
echo "Professional score alvo: $SAP_PROFESSIONAL_MIN_SCORE"
echo "Release gate: $SAP_RELEASE_ENFORCE"
echo "Cenas: $SHORT_QTD_CENAS"
echo "Idioma: $SHORT_LANGUAGE"
echo "Duração alvo: ${SHORT_TARGET_DURATION_SECONDS}s"
echo "Voz: $PIPER_MODEL"
if [ -n "${SHORT_TOPIC_EXACT:-}" ]; then
    echo "Assunto exato: $SHORT_TOPIC_EXACT"
elif [ -n "${SHORT_TEMA:-}" ]; then
    echo "Tema: $SHORT_TEMA"
fi
echo "========================================"
echo

exec python "$MAIN" run
