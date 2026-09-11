#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado."
    exit 90
}


LOG="$HOME/ShortAutoPro/logs/producao/vi1320_console.log"

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
V6_0="$(hash_file v6.py)"
EXECUTOR0="$(hash_file vi6_95_scene_executor.py)"

MEDIA0="$(tree_hash imagens)"
SOURCE0="$(tree_hash temp/vi1270_downloads/assets)"
PREP0="$(tree_hash temp/vi1300_prepared)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1320 VISUAL DIRECTOR 2.0 CANARY" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"
echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1320_01_visual_plan.py \
vi1320_02_overlays.py \
vi1320_03_render.py \
vi1320_04_audit_compare.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


if [ "$COMPILE" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== VISUAL PLAN =====" |
    tee -a "$LOG"

    python \
    vi1320_01_visual_plan.py \
    2>&1 |
    tee -a "$LOG"

    PLAN=${PIPESTATUS[0]}

else

    PLAN=99

fi


if [ "$PLAN" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== OVERLAYS =====" |
    tee -a "$LOG"

    python \
    vi1320_02_overlays.py \
    2>&1 |
    tee -a "$LOG"

    OVERLAYS=${PIPESTATUS[0]}

else

    OVERLAYS=98

fi


if [ "$OVERLAYS" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== VISUAL DIRECTOR RENDER =====" |
    tee -a "$LOG"

    python \
    vi1320_03_render.py \
    2>&1 |
    tee -a "$LOG"

    RENDER=${PIPESTATUS[0]}

else

    RENDER=97

fi


if [ "$RENDER" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== VISUAL AUDIT + COMPARISON =====" |
    tee -a "$LOG"

    python \
    vi1320_04_audit_compare.py \
    2>&1 |
    tee -a "$LOG"

    AUDIT=${PIPESTATUS[0]}

else

    AUDIT=96

fi


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
V6_1="$(hash_file v6.py)"
EXECUTOR1="$(hash_file vi6_95_scene_executor.py)"

MEDIA1="$(tree_hash imagens)"
SOURCE1="$(tree_hash temp/vi1270_downloads/assets)"
PREP1="$(tree_hash temp/vi1300_prepared)"


same() {
    [ "$1" = "$2" ] &&
    echo PASS ||
    echo FAIL
}


VIDEO_OK="$(same "$VIDEO0" "$VIDEO1")"
GERAR_OK="$(same "$GERAR0" "$GERAR1")"
V6_OK="$(same "$V6_0" "$V6_1")"
EXECUTOR_OK="$(same "$EXECUTOR0" "$EXECUTOR1")"

MEDIA_OK="$(same "$MEDIA0" "$MEDIA1")"
SOURCE_OK="$(same "$SOURCE0" "$SOURCE1")"
PREP_OK="$(same "$PREP0" "$PREP1")"


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " INTEGRITY" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "VIDEO=$VIDEO_OK" |
tee -a "$LOG"

echo "GERAR=$GERAR_OK" |
tee -a "$LOG"

echo "V6=$V6_OK" |
tee -a "$LOG"

echo "EXECUTOR=$EXECUTOR_OK" |
tee -a "$LOG"

echo "PRODUCTION_MEDIA=$MEDIA_OK" |
tee -a "$LOG"

echo "SOURCE_ASSETS=$SOURCE_OK" |
tee -a "$LOG"

echo "PREPARED_ASSETS=$PREP_OK" |
tee -a "$LOG"


FINAL=0


for STATUS in \
"$COMPILE" \
"$PLAN" \
"$OVERLAYS" \
"$RENDER" \
"$AUDIT"
do

    if [ "$STATUS" -ne 0 ]; then
        FINAL=1
    fi

done


for VALUE in \
"$VIDEO_OK" \
"$GERAR_OK" \
"$V6_OK" \
"$EXECUTOR_OK" \
"$MEDIA_OK" \
"$SOURCE_OK" \
"$PREP_OK"
do

    if [ "$VALUE" != "PASS" ]; then
        FINAL=1
    fi

done


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " VI1320 FINAL" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "COMPILE=$COMPILE" |
tee -a "$LOG"

echo "VISUAL_PLAN=$PLAN" |
tee -a "$LOG"

echo "OVERLAYS=$OVERLAYS" |
tee -a "$LOG"

echo "RENDER=$RENDER" |
tee -a "$LOG"

echo "AUDIT_COMPARE=$AUDIT" |
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


if [ "$FINAL" -eq 0 ]; then

    cp -f \
    "$HOME/ShortAutoPro/videos/canary/vi1320/2026-09-01_1433_VI1320_CANARY.mp4" \
    "$HOME/storage/downloads/VI1320_CANARY.mp4" \
    2>/dev/null


    cp -f \
    "$HOME/ShortAutoPro/videos/canary/vi1320/VI1320_contact_sheet.jpg" \
    "$HOME/storage/downloads/VI1320_CONTACT_SHEET.jpg" \
    2>/dev/null


    cp -f \
    "$HOME/ShortAutoPro/videos/canary/vi1320/VI1310_vs_VI1320.jpg" \
    "$HOME/storage/downloads/VI1310_VS_VI1320.jpg" \
    2>/dev/null

fi


exit "$FINAL"
