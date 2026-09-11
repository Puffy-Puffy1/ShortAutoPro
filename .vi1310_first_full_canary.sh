#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado."
    exit 90
}


mkdir -p \
temp/vi1310/clips \
videos/canary/vi1310 \
logs/producao \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1310_console.log"

: > "$LOG"


hash_file() {
    sha256sum "$1" 2>/dev/null |
    awk '{print $1}'
}


tree_hash() {
    find "$1" \
    -type f \
    -printf '%p|%s|%T@\n' \
    2>/dev/null |
    sort |
    sha256sum |
    awk '{print $1}'
}


VIDEO0="$(hash_file video.py)"
GERAR0="$(hash_file gerar_short.sh)"
ROTEIRO0="$(hash_file roteiro.py)"
EXECUTOR0="$(hash_file vi6_95_scene_executor.py)"
V6_0="$(hash_file v6.py)"

MEDIA0="$(tree_hash imagens)"
DOWNLOAD0="$(tree_hash temp/vi1270_downloads/assets)"
PREPARED0="$(tree_hash temp/vi1300_prepared)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1310 FIRST FULL CONTROLLED RENDER CANARY" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1310_01_media_discovery.py \
vi1310_02_timeline_planner.py \
vi1310_03_controlled_render.py \
vi1310_04_render_audit.py \
vi1310_05_contact_sheet.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== DISCOVERY =====" |
tee -a "$LOG"


python \
vi1310_01_media_discovery.py \
2>&1 |
tee -a "$LOG"

DISCOVERY=${PIPESTATUS[0]}


if [ "$DISCOVERY" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== TIMELINE =====" |
    tee -a "$LOG"


    python \
    vi1310_02_timeline_planner.py \
    2>&1 |
    tee -a "$LOG"

    TIMELINE=${PIPESTATUS[0]}

else

    TIMELINE=98

fi


if [ "$TIMELINE" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== CONTROLLED RENDER =====" |
    tee -a "$LOG"


    python \
    vi1310_03_controlled_render.py \
    2>&1 |
    tee -a "$LOG"

    RENDER=${PIPESTATUS[0]}

else

    RENDER=97

fi


if [ "$RENDER" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== FINAL VIDEO AUDIT =====" |
    tee -a "$LOG"


    python \
    vi1310_04_render_audit.py \
    2>&1 |
    tee -a "$LOG"

    AUDIT=${PIPESTATUS[0]}

else

    AUDIT=96

fi


if [ "$AUDIT" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== CONTACT SHEET =====" |
    tee -a "$LOG"


    python \
    vi1310_05_contact_sheet.py \
    2>&1 |
    tee -a "$LOG"

    CONTACT=${PIPESTATUS[0]}

else

    CONTACT=95

fi


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
EXECUTOR1="$(hash_file vi6_95_scene_executor.py)"
V6_1="$(hash_file v6.py)"

MEDIA1="$(tree_hash imagens)"
DOWNLOAD1="$(tree_hash temp/vi1270_downloads/assets)"
PREPARED1="$(tree_hash temp/vi1300_prepared)"


same() {
    [ "$1" = "$2" ] &&
    echo PASS ||
    echo FAIL
}


VIDEO_OK="$(same "$VIDEO0" "$VIDEO1")"
GERAR_OK="$(same "$GERAR0" "$GERAR1")"
ROTEIRO_OK="$(same "$ROTEIRO0" "$ROTEIRO1")"
EXECUTOR_OK="$(same "$EXECUTOR0" "$EXECUTOR1")"
V6_OK="$(same "$V6_0" "$V6_1")"

MEDIA_OK="$(same "$MEDIA0" "$MEDIA1")"
DOWNLOAD_OK="$(same "$DOWNLOAD0" "$DOWNLOAD1")"
PREPARED_OK="$(same "$PREPARED0" "$PREPARED1")"


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " CORE + SOURCE INTEGRITY" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "VIDEO=$VIDEO_OK" |
tee -a "$LOG"

echo "GERAR=$GERAR_OK" |
tee -a "$LOG"

echo "ROTEIRO=$ROTEIRO_OK" |
tee -a "$LOG"

echo "EXECUTOR=$EXECUTOR_OK" |
tee -a "$LOG"

echo "V6=$V6_OK" |
tee -a "$LOG"

echo "PRODUCTION_MEDIA=$MEDIA_OK" |
tee -a "$LOG"

echo "CONTROLLED_DOWNLOADS=$DOWNLOAD_OK" |
tee -a "$LOG"

echo "PREPARED_ASSETS=$PREPARED_OK" |
tee -a "$LOG"


FINAL=0


for STATUS in \
"$COMPILE" \
"$DISCOVERY" \
"$TIMELINE" \
"$RENDER" \
"$AUDIT" \
"$CONTACT"
do

    if [ "$STATUS" -ne 0 ]; then
        FINAL=1
    fi

done


for VALUE in \
"$VIDEO_OK" \
"$GERAR_OK" \
"$ROTEIRO_OK" \
"$EXECUTOR_OK" \
"$V6_OK" \
"$MEDIA_OK" \
"$DOWNLOAD_OK" \
"$PREPARED_OK"
do

    if [ "$VALUE" != "PASS" ]; then
        FINAL=1
    fi

done


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " VI1310 FINAL" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "COMPILE=$COMPILE" |
tee -a "$LOG"

echo "DISCOVERY=$DISCOVERY" |
tee -a "$LOG"

echo "TIMELINE=$TIMELINE" |
tee -a "$LOG"

echo "RENDER=$RENDER" |
tee -a "$LOG"

echo "AUDIT=$AUDIT" |
tee -a "$LOG"

echo "CONTACT_SHEET=$CONTACT" |
tee -a "$LOG"

echo "NETWORK_EXECUTED=FALSE" |
tee -a "$LOG"

echo "DOWNLOAD_EXECUTED=FALSE" |
tee -a "$LOG"

echo "PRODUCTION_MUTATED=FALSE" |
tee -a "$LOG"

echo "PUBLICATION_EXECUTED=FALSE" |
tee -a "$LOG"

echo "FINAL_STATUS=$FINAL" |
tee -a "$LOG"


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1310_First_Full_Canary.txt" \
2>/dev/null


VIDEO_PATH="$HOME/ShortAutoPro/videos/canary/vi1310/2026-09-01_1433_VI1310_CANARY.mp4"

CONTACT_PATH="$HOME/ShortAutoPro/videos/canary/vi1310/VI1310_contact_sheet.jpg"


if [ "$FINAL" -eq 0 ]; then

    cp -f \
    "$VIDEO_PATH" \
    "$HOME/storage/downloads/VI1310_CANARY.mp4" \
    2>/dev/null


    cp -f \
    "$CONTACT_PATH" \
    "$HOME/storage/downloads/VI1310_CONTACT_SHEET.jpg" \
    2>/dev/null

fi


exit "$FINAL"
