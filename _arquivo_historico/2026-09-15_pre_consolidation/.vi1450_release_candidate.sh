#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado."
    exit 90
}


mkdir -p \
temp/vi1400/prepared \
temp/vi1400/work \
temp/vi1400/canary \
temp/vi1450 \
logs/producao \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1450_console.log"

RUNLOG="$HOME/ShortAutoPro/temp/vi1450/current_stage.log"

: > "$LOG"


run_logged() {

    NAME="$1"
    shift

    echo |
    tee -a "$LOG"

    echo "===== $NAME =====" |
    tee -a "$LOG"

    : > "$RUNLOG"

    "$@" >"$RUNLOG" 2>&1

    RC=$?

    cat "$RUNLOG" |
    tee -a "$LOG"

    echo "$NAME STATUS=$RC" |
    tee -a "$LOG"

    return "$RC"
}


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


same_bool() {

    if [ "$1" = "$2" ]; then
        echo True
    else
        echo False
    fi
}


VIDEO0="$(hash_file video.py)"
GERAR0="$(hash_file gerar_short.sh)"
ROTEIRO0="$(hash_file roteiro.py)"
EXECUTOR0="$(hash_file vi6_95_scene_executor.py)"
V6_0="$(hash_file v6.py)"

SOURCE0="$(
tree_hash \
temp/vi1270_downloads/assets
)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1450 PRE-FINAL RELEASE CANDIDATE" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


run_logged \
"PREREQUISITE" \
python \
vi1450_01_prerequisite_gate.py

PREREQ=$?


echo |
tee -a "$LOG"

echo "===== COMPILE ALL =====" |
tee -a "$LOG"


python -m py_compile \
vi1400_01_transform_core.py \
vi1400_02_asset_transformer.py \
vi1400_03_prepared_forensics.py \
vi1400_04_render_manifest.py \
vi1400_05_visual_canary.py \
vi1400_06_canary_forensics.py \
vi1400_07_regression.py \
vi1400_08_architecture_audit.py \
vi1450_01_prerequisite_gate.py \
vi1450_02_contact_sheet.py \
vi1450_03_credits_manifest.py \
vi1450_04_portfolio_audit.py \
vi1450_05_architecture_audit.py \
vi1450_06_final_certification.py \
>"$RUNLOG" 2>&1

COMPILE=$?

cat "$RUNLOG" |
tee -a "$LOG"

echo "COMPILE STATUS=$COMPILE" |
tee -a "$LOG"


REG=99
TRANSFORM=99
FORENSICS=99
MANIFEST=99
CANARY=99
CANARY_FORENSICS=99
ARCH1400=99
CONTACT=99
CREDITS=99
PORTFOLIO=99
ARCH1450=99


if \
[ "$PREREQ" -eq 0 ] && \
[ "$COMPILE" -eq 0 ]
then

    run_logged \
    "REGRESSION" \
    python \
    vi1400_07_regression.py

    REG=$?

fi


if [ "$REG" -eq 0 ]; then

    run_logged \
    "ASSET TRANSFORMATION" \
    python \
    vi1400_02_asset_transformer.py

    TRANSFORM=$?

fi


if [ "$TRANSFORM" -eq 0 ]; then

    run_logged \
    "PREPARED FORENSICS" \
    python \
    vi1400_03_prepared_forensics.py

    FORENSICS=$?

fi


if [ "$FORENSICS" -eq 0 ]; then

    run_logged \
    "RENDER MANIFEST" \
    python \
    vi1400_04_render_manifest.py

    MANIFEST=$?

fi


if [ "$MANIFEST" -eq 0 ]; then

    run_logged \
    "VISUAL CANARY BUILD" \
    python \
    vi1400_05_visual_canary.py

    CANARY=$?

fi


if [ "$CANARY" -eq 0 ]; then

    run_logged \
    "CANARY FORENSICS" \
    python \
    vi1400_06_canary_forensics.py

    CANARY_FORENSICS=$?

fi


if [ "$CANARY_FORENSICS" -eq 0 ]; then

    run_logged \
    "VI1400 ARCHITECTURE" \
    python \
    vi1400_08_architecture_audit.py

    ARCH1400=$?

fi


if [ "$ARCH1400" -eq 0 ]; then

    run_logged \
    "CONTACT SHEET" \
    python \
    vi1450_02_contact_sheet.py

    CONTACT=$?

fi


if [ "$CONTACT" -eq 0 ]; then

    run_logged \
    "CREDITS MANIFEST" \
    python \
    vi1450_03_credits_manifest.py

    CREDITS=$?

fi


if [ "$CREDITS" -eq 0 ]; then

    run_logged \
    "PORTFOLIO AUDIT" \
    python \
    vi1450_04_portfolio_audit.py

    PORTFOLIO=$?

fi


if [ "$PORTFOLIO" -eq 0 ]; then

    run_logged \
    "VI1450 ARCHITECTURE" \
    python \
    vi1450_05_architecture_audit.py

    ARCH1450=$?

fi


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
EXECUTOR1="$(hash_file vi6_95_scene_executor.py)"
V6_1="$(hash_file v6.py)"

SOURCE1="$(
tree_hash \
temp/vi1270_downloads/assets
)"


VIDEO_OK="$(
same_bool \
"$VIDEO0" \
"$VIDEO1"
)"

GERAR_OK="$(
same_bool \
"$GERAR0" \
"$GERAR1"
)"

ROTEIRO_OK="$(
same_bool \
"$ROTEIRO0" \
"$ROTEIRO1"
)"

EXECUTOR_OK="$(
same_bool \
"$EXECUTOR0" \
"$EXECUTOR1"
)"

V6_OK="$(
same_bool \
"$V6_0" \
"$V6_1"
)"

SOURCE_OK="$(
same_bool \
"$SOURCE0" \
"$SOURCE1"
)"


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " VI1450 CORE + SOURCE INTEGRITY" |
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

echo "SOURCE_ASSETS=$SOURCE_OK" |
tee -a "$LOG"


export V1450_PREREQ="$PREREQ"
export V1450_COMPILE="$COMPILE"
export V1450_REG="$REG"
export V1450_TRANSFORM="$TRANSFORM"
export V1450_FORENSICS="$FORENSICS"
export V1450_MANIFEST="$MANIFEST"
export V1450_CANARY="$CANARY"
export V1450_CANARY_FORENSICS="$CANARY_FORENSICS"
export V1450_ARCH1400="$ARCH1400"
export V1450_CONTACT="$CONTACT"
export V1450_CREDITS="$CREDITS"
export V1450_PORTFOLIO="$PORTFOLIO"
export V1450_ARCH1450="$ARCH1450"

export V1450_VIDEO_OK="$VIDEO_OK"
export V1450_GERAR_OK="$GERAR_OK"
export V1450_ROTEIRO_OK="$ROTEIRO_OK"
export V1450_EXECUTOR_OK="$EXECUTOR_OK"
export V1450_V6_OK="$V6_OK"
export V1450_SOURCE_OK="$SOURCE_OK"


run_logged \
"FINAL CERTIFICATION" \
python \
vi1450_06_final_certification.py

FINAL=$?


CANARY_FILE="$HOME/ShortAutoPro/temp/vi1400/canary/VI1400_visual_canary.mp4"

CONTACT_FILE="$HOME/ShortAutoPro/temp/vi1450/VI1450_contact_sheet.jpg"

CREDITS_FILE="$HOME/ShortAutoPro/temp/vi1450/credits.txt"


if [ "$FINAL" -eq 0 ]; then

    if [ -f "$CANARY_FILE" ]; then

        cp -f \
        "$CANARY_FILE" \
        "$HOME/storage/downloads/ShortAutoPro_VI1450_Visual_Canary.mp4"

    fi


    if [ -f "$CONTACT_FILE" ]; then

        cp -f \
        "$CONTACT_FILE" \
        "$HOME/storage/downloads/ShortAutoPro_VI1450_Contact_Sheet.jpg"

    fi


    if [ -f "$CREDITS_FILE" ]; then

        cp -f \
        "$CREDITS_FILE" \
        "$HOME/storage/downloads/ShortAutoPro_VI1450_Credits.txt"

    fi

fi


cp -f \
"$LOG" \
"$HOME/storage/downloads/ShortAutoPro_VI1450_Log.txt" \
2>/dev/null


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " VI1450 RETURN" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "PREREQ=$PREREQ" |
tee -a "$LOG"

echo "COMPILE=$COMPILE" |
tee -a "$LOG"

echo "REGRESSION=$REG" |
tee -a "$LOG"

echo "TRANSFORM=$TRANSFORM" |
tee -a "$LOG"

echo "FORENSICS=$FORENSICS" |
tee -a "$LOG"

echo "MANIFEST=$MANIFEST" |
tee -a "$LOG"

echo "CANARY=$CANARY" |
tee -a "$LOG"

echo "CANARY_FORENSICS=$CANARY_FORENSICS" |
tee -a "$LOG"

echo "ARCH1400=$ARCH1400" |
tee -a "$LOG"

echo "CONTACT=$CONTACT" |
tee -a "$LOG"

echo "CREDITS=$CREDITS" |
tee -a "$LOG"

echo "PORTFOLIO=$PORTFOLIO" |
tee -a "$LOG"

echo "ARCH1450=$ARCH1450" |
tee -a "$LOG"

echo "FINAL_STATUS=$FINAL" |
tee -a "$LOG"

echo "TERMUX_CONTINUA_ABERTO=SIM" |
tee -a "$LOG"


exit "$FINAL"
