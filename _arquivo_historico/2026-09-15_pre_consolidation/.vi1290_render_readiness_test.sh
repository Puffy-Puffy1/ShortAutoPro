#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado."
    exit 90
}


mkdir -p \
temp/vi1290 \
logs/producao \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1290_console.log"

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
DL0="$(tree_hash temp/vi1270_downloads/assets)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1290 ASSET PREPARATION + RENDER READINESS" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1290_01_asset_planner.py \
vi1290_02_regression.py \
vi1290_03_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== REGRESSION =====" |
tee -a "$LOG"


python \
vi1290_02_regression.py \
2>&1 |
tee -a "$LOG"

REGRESSION=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== REAL RENDER READINESS PLAN =====" |
tee -a "$LOG"


python \
vi1290_01_asset_planner.py \
2>&1 |
tee -a "$LOG"

PLANNER=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1290_03_architecture_audit.py \
2>&1 |
tee -a "$LOG"

ARCH=${PIPESTATUS[0]}


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
EXECUTOR1="$(hash_file vi6_95_scene_executor.py)"
V6_1="$(hash_file v6.py)"

MEDIA1="$(tree_hash imagens)"
DL1="$(tree_hash temp/vi1270_downloads/assets)"


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
DOWNLOADS_OK="$(same "$DL0" "$DL1")"


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " CORE + ASSET INTEGRITY" |
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

echo "CONTROLLED_DOWNLOAD_ASSETS=$DOWNLOADS_OK" |
tee -a "$LOG"


FINAL=0


if \
[ "$COMPILE" -ne 0 ] || \
[ "$REGRESSION" -ne 0 ] || \
[ "$PLANNER" -ne 0 ] || \
[ "$ARCH" -ne 0 ]
then

    FINAL=1

fi


for VALUE in \
"$VIDEO_OK" \
"$GERAR_OK" \
"$ROTEIRO_OK" \
"$EXECUTOR_OK" \
"$V6_OK" \
"$MEDIA_OK" \
"$DOWNLOADS_OK"
do

    if [ "$VALUE" != "PASS" ]; then

        FINAL=1

    fi

done


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " VI1290 FINAL" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "COMPILE=$COMPILE" |
tee -a "$LOG"

echo "REGRESSION=$REGRESSION" |
tee -a "$LOG"

echo "PLANNER=$PLANNER" |
tee -a "$LOG"

echo "ARCHITECTURE=$ARCH" |
tee -a "$LOG"

echo "NETWORK_EXECUTED=FALSE" |
tee -a "$LOG"

echo "DOWNLOAD_EXECUTED=FALSE" |
tee -a "$LOG"

echo "FFPROBE_EXECUTED=FALSE" |
tee -a "$LOG"

echo "FFMPEG_EXECUTED=FALSE" |
tee -a "$LOG"

echo "VIDEO_GENERATED=FALSE" |
tee -a "$LOG"

echo "RENDERER_ACTIVATED=FALSE" |
tee -a "$LOG"

echo "PRODUCTION_MUTATED=FALSE" |
tee -a "$LOG"

echo "FINAL_STATUS=$FINAL" |
tee -a "$LOG"


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1290_Render_Readiness.txt" \
2>/dev/null


exit "$FINAL"
