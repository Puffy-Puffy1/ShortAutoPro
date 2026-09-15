#!/data/data/com.termux/files/usr/bin/bash

cd "$HOME/ShortAutoPro" || return 1

export SAP_VSE42=1
export SAP_VSE42_RESCUE=1
export SAP_VSE_V4=1
export SAP_SCENE_COMMIT_LOCK=1

echo "=============================================="
echo " SHORTAUTOPRO VISUAL V4.2"
echo "=============================================="

if \
[ ! -f temp/VSE42_ENGINE_OK ] ||
[ ! -f temp/VSE42_RUNTIME_OK ] ||
[ ! -f temp/VSE42_MIDIA_OK ] ||
[ ! -f temp/VSE42_REGRESSION_OK ]
then

    echo "PRODUCTION_START=BLOCKED"
    echo "REASON=V42_NOT_CERTIFIED"

else

    echo "PRODUCTION_START=AUTHORIZED"

    bash ./gerar_short.sh

fi

echo
echo "TERMUX_CONTINUA_ABERTO=SIM"
