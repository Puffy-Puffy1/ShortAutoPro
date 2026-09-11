#!/data/data/com.termux/files/usr/bin/bash

cd "$HOME/ShortAutoPro" || return 1

STAMP="$(cat temp/UNIFY_SESSION 2>/dev/null)"

echo "=============================================="
echo " SHORTAUTOPRO UNIFICATION ROLLBACK"
echo "=============================================="

if [ -z "$STAMP" ]; then
    echo "ROLLBACK=FAIL_NO_SESSION"
else

    BKP="backups/unification_$STAMP/root"

    if [ -d "$BKP" ]; then

        cp -f "$BKP"/* . 2>/dev/null

        echo "ROOT_FILES_RESTORED=YES"

    else

        echo "ROOT_BACKUP_NOT_FOUND"

    fi


    if [ -d "_legacy/ShortAuto" ] && [ ! -e "ShortAuto" ]; then

        mv \
        "_legacy/ShortAuto" \
        "ShortAuto"

        echo "LEGACY_DIRECTORY_RESTORED=YES"

    fi

    echo "ROLLBACK_COMPLETE=YES"

fi

echo "TERMUX_CONTINUA_ABERTO=SIM"
