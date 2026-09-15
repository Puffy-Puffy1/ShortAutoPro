#!/data/data/com.termux/files/usr/bin/bash

cd "$HOME/ShortAutoPro" || return 2

BACKUP="backups/VSE42_PRODUCTION_20260906_013448"

echo "=============================================="
echo " VSE42 ROLLBACK"
echo "=============================================="
echo "BACKUP=$BACKUP"

if [ -f "$BACKUP/midia.py" ]; then

    cp -f     "$BACKUP/midia.py"     midia.py

    echo "MIDIA_ROLLBACK=PASS"

else

    echo "MIDIA_ROLLBACK=FAIL"

fi

if [ -f "$BACKUP/gerar_short.sh" ]; then

    cp -f     "$BACKUP/gerar_short.sh"     gerar_short.sh

fi

python -m py_compile midia.py

echo "ROLLBACK_COMPILE=$?"

bash -n gerar_short.sh

echo "ROLLBACK_SHELL=$?"

echo "TERMUX_CONTINUA_ABERTO=SIM"
