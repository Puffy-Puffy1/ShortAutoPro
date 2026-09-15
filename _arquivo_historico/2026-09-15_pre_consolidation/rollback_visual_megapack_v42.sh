#!/data/data/com.termux/files/usr/bin/bash

cd "$HOME/ShortAutoPro" || return 1

BKP="$(cat temp/MEGAPACK_BACKUP_PATH 2>/dev/null)"

echo "=============================================="
echo " V42 ROLLBACK"
echo "=============================================="
echo "BACKUP=$BKP"

if [ -z "$BKP" ] || [ ! -d "$BKP" ]; then

    echo "ROLLBACK=FAIL_NO_BACKUP"

else

    for F in \
    midia.py \
    video.py \
    v6.py \
    gerar_short.sh \
    visual_selection_engine_v4.py \
    media_diversity_guard_v1.py \
    fresh_render_guard_v1.py \
    render_input_fingerprint_v1.py
    do

        if [ -f "$BKP/$F" ]; then
            cp -f "$BKP/$F" "$F"
            echo "RESTORED=$F"
        fi

    done

    echo "ROLLBACK=PASS"

fi

echo "TERMUX_CONTINUA_ABERTO=SIM"
