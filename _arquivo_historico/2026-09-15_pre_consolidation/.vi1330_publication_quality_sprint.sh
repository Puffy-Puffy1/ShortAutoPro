#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado."
    exit 90
}


mkdir -p \
temp/vi1330/clips \
videos/canary/vi1330 \
logs/producao \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1330_console.log"

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
V6_0="$(hash_file v6.py)"
EXECUTOR0="$(hash_file vi6_95_scene_executor.py)"

MEDIA0="$(tree_hash imagens)"
SOURCE0="$(tree_hash temp/vi1270_downloads/assets)"
PREP0="$(tree_hash temp/vi1300_prepared)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1330 PUBLICATION QUALITY SPRINT" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1330_01_publication_visual_director.py \
vi1330_02_overlay_director.py \
vi1330_03_motion_engine.py \
vi1330_04_archive_video_director.py \
vi1330_05_subtitle_safety.py \
vi1330_06_scene_renderer.py \
vi1330_07_publication_render.py \
vi1330_08_technical_audit.py \
vi1330_09_visual_qa.py \
vi1330_10_contact_sheet.py \
vi1330_11_three_way_compare.py \
vi1330_12_regression.py \
vi1330_13_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== REGRESSION =====" |
tee -a "$LOG"


python \
vi1330_12_regression.py \
2>&1 |
tee -a "$LOG"

REGRESSION=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== VISUAL DIRECTOR =====" |
tee -a "$LOG"


python \
vi1330_01_publication_visual_director.py \
2>&1 |
tee -a "$LOG"

PLAN=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== SUBTITLE SAFETY =====" |
tee -a "$LOG"


python \
vi1330_05_subtitle_safety.py \
2>&1 |
tee -a "$LOG"

SUBTITLE=${PIPESTATUS[0]}


if \
[ "$PLAN" -eq 0 ] && \
[ "$SUBTITLE" -eq 0 ]
then

    echo |
    tee -a "$LOG"

    echo "===== OVERLAY DIRECTOR =====" |
    tee -a "$LOG"


    python \
    vi1330_02_overlay_director.py \
    2>&1 |
    tee -a "$LOG"

    OVERLAY=${PIPESTATUS[0]}

else

    OVERLAY=98

fi


if [ "$OVERLAY" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== PUBLICATION QUALITY RENDER =====" |
    tee -a "$LOG"


    python \
    vi1330_07_publication_render.py \
    2>&1 |
    tee -a "$LOG"

    RENDER=${PIPESTATUS[0]}

else

    RENDER=97

fi


if [ "$RENDER" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== TECHNICAL AUDIT =====" |
    tee -a "$LOG"


    python \
    vi1330_08_technical_audit.py \
    2>&1 |
    tee -a "$LOG"

    TECH=${PIPESTATUS[0]}

else

    TECH=96

fi


if [ "$RENDER" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== AUTOMATED VISUAL QA =====" |
    tee -a "$LOG"


    python \
    vi1330_09_visual_qa.py \
    2>&1 |
    tee -a "$LOG"

    VISUAL=${PIPESTATUS[0]}

else

    VISUAL=95

fi


if \
[ "$TECH" -eq 0 ] && \
[ "$VISUAL" -eq 0 ]
then

    echo |
    tee -a "$LOG"

    echo "===== CONTACT SHEET =====" |
    tee -a "$LOG"


    python \
    vi1330_10_contact_sheet.py \
    2>&1 |
    tee -a "$LOG"

    CONTACT=${PIPESTATUS[0]}

else

    CONTACT=94

fi


if [ "$CONTACT" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo "===== THREE-WAY COMPARISON =====" |
    tee -a "$LOG"


    python \
    vi1330_11_three_way_compare.py \
    2>&1 |
    tee -a "$LOG"

    COMPARE=${PIPESTATUS[0]}

else

    COMPARE=93

fi


echo |
tee -a "$LOG"

echo "===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1330_13_architecture_audit.py \
2>&1 |
tee -a "$LOG"

ARCH=${PIPESTATUS[0]}


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
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
ROTEIRO_OK="$(same "$ROTEIRO0" "$ROTEIRO1")"
V6_OK="$(same "$V6_0" "$V6_1")"
EXECUTOR_OK="$(same "$EXECUTOR0" "$EXECUTOR1")"

MEDIA_OK="$(same "$MEDIA0" "$MEDIA1")"
SOURCE_OK="$(same "$SOURCE0" "$SOURCE1")"
PREP_OK="$(same "$PREP0" "$PREP1")"


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
"$REGRESSION" \
"$PLAN" \
"$SUBTITLE" \
"$OVERLAY" \
"$RENDER" \
"$TECH" \
"$VISUAL" \
"$CONTACT" \
"$COMPARE" \
"$ARCH"
do

    if [ "$STATUS" -ne 0 ]; then

        FINAL=1

    fi

done


for VALUE in \
"$VIDEO_OK" \
"$GERAR_OK" \
"$ROTEIRO_OK" \
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

echo " VI1330 FINAL" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "COMPILE=$COMPILE" |
tee -a "$LOG"

echo "REGRESSION=$REGRESSION" |
tee -a "$LOG"

echo "VISUAL_PLAN=$PLAN" |
tee -a "$LOG"

echo "SUBTITLE_SAFETY=$SUBTITLE" |
tee -a "$LOG"

echo "OVERLAY=$OVERLAY" |
tee -a "$LOG"

echo "RENDER=$RENDER" |
tee -a "$LOG"

echo "TECHNICAL_AUDIT=$TECH" |
tee -a "$LOG"

echo "VISUAL_QA=$VISUAL" |
tee -a "$LOG"

echo "CONTACT_SHEET=$CONTACT" |
tee -a "$LOG"

echo "THREE_WAY_COMPARE=$COMPARE" |
tee -a "$LOG"

echo "ARCHITECTURE=$ARCH" |
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
    "$HOME/ShortAutoPro/videos/canary/vi1330/2026-09-01_1433_VI1330_CANARY.mp4" \
    "$HOME/storage/downloads/VI1330_CANARY.mp4" \
    2>/dev/null


    cp -f \
    "$HOME/ShortAutoPro/videos/canary/vi1330/VI1330_contact_sheet.jpg" \
    "$HOME/storage/downloads/VI1330_CONTACT_SHEET.jpg" \
    2>/dev/null


    cp -f \
    "$HOME/ShortAutoPro/videos/canary/vi1330/VI1310_VS_VI1320_VS_VI1330.jpg" \
    "$HOME/storage/downloads/VI1310_VS_VI1320_VS_VI1330.jpg" \
    2>/dev/null


    cp -f \
    "$LOG" \
    "$HOME/storage/downloads/VI1330_PUBLICATION_QUALITY_LOG.txt" \
    2>/dev/null

fi


exit "$FINAL"
