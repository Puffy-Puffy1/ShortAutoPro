#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1


# FULL_POWER_CONFIG_BOOTSTRAP_V1
#
# Load the same provider/runtime configuration used by
# the normal ShortAutoPro production path.
set +u

if [ -f "$HOME/ShortAutoPro/config.sh" ]; then
    . "$HOME/ShortAutoPro/config.sh"
    echo "CONFIG_SH=LOADED"
else
    echo "CONFIG_SH=MISSING"
fi

if [ -f "$HOME/ShortAutoPro/config.env" ]; then
    set -a
    . "$HOME/ShortAutoPro/config.env"
    set +a
    echo "CONFIG_ENV=LOADED"
fi

set -u


# ============================================================
# SHORTAUTOPRO — FULL POWER RESUME
# ============================================================

export SHORT_ID="2026-09-12_2259"

# Visual Intelligence
export SAP_VSE_V4=1
export SAP_SCENE_COMMIT_LOCK=1
export SAP_VSE_V3=1
export SAP_VSE_V2=1

# Final-video enhancement stack
export SHORT_RETENTION_ENGINE=1
export SHORT_USAR_MUSICA=1
export SHORT_USAR_SFX=1
export SHORT_USAR_POP=1

# Gerar somente. Não publicar automaticamente.
export SAP_NO_PUBLISH=1

LOG_DIR="logs/producao"
LOG="$LOG_DIR/full_power_resume_${SHORT_ID}.log"

mkdir -p "$LOG_DIR" videos imagens temp

exec > >(tee -a "$LOG") 2>&1

echo
echo "============================================================"
echo " SHORTAUTOPRO — FULL POWER RESUME"
echo "============================================================"
echo "SHORT_ID=$SHORT_ID"
echo "DATE=$(date)"
echo
echo "SAP_VSE_V4=$SAP_VSE_V4"
echo "SAP_SCENE_COMMIT_LOCK=$SAP_SCENE_COMMIT_LOCK"
echo "SHORT_RETENTION_ENGINE=$SHORT_RETENTION_ENGINE"
echo "SHORT_USAR_MUSICA=$SHORT_USAR_MUSICA"
echo "SHORT_USAR_SFX=$SHORT_USAR_SFX"
echo "SHORT_USAR_POP=$SHORT_USAR_POP"
echo "SAP_NO_PUBLISH=$SAP_NO_PUBLISH"
echo

fail() {
    echo
    echo "============================================================"
    echo " FULL POWER RESUME: BLOCK"
    echo "============================================================"
    echo "FAILED_STAGE=$1"
    echo "SHORT_ID=$SHORT_ID"
    echo "LOG=$LOG"
    exit 1
}

run_stage() {
    NAME="$1"
    shift

    echo
    echo "------------------------------------------------------------"
    echo "$NAME"
    echo "------------------------------------------------------------"
    echo

    START=$(date +%s)

    "$@"
    RC=$?

    END=$(date +%s)
    ELAPSED=$((END - START))

    echo
    echo "EXIT_CODE=$RC"
    echo "TIME=${ELAPSED}s"

    if [ "$RC" -ne 0 ]; then
        fail "$NAME"
    fi

    echo "STAGE_RESULT=PASS"
}

# ============================================================
# 0. EXISTING RUN INTEGRITY
# ============================================================

echo
echo "============================================================"
echo " 0. EXISTING RUN INTEGRITY"
echo "============================================================"

REQUIRED_FILES="
roteiros/topic_${SHORT_ID}.txt
roteiros/used_topic_${SHORT_ID}.txt
roteiros/short_${SHORT_ID}.txt
roteiros/fonte_${SHORT_ID}.txt
roteiros/keywords_${SHORT_ID}.txt
roteiros/scene_map_${SHORT_ID}.json
roteiros/post_script_truth_${SHORT_ID}.json
roteiros/semantic_integrity_${SHORT_ID}.json
"

MISSING=0

for F in $REQUIRED_FILES
do
    if [ -f "$F" ]; then
        echo "FOUND=$F"
    else
        echo "MISSING=$F"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -ne 0 ]; then
    fail "EXISTING RUN INTEGRITY"
fi

echo "EXISTING_RUN=PASS"

# ============================================================
# 1. CORE COMPILE — FULL POWER
# ============================================================

echo
echo "============================================================"
echo " 1. CORE COMPILE"
echo "============================================================"

COMPILE_FILES="
visual_selection_engine_v4.py
media_provenance_capture_v1.py
media_diversity_guard_v1.py
midia.py
media_master_gate.py
motion_director.py
rhythm_director.py
production_supervisor.py
editorial_gate.py
audio.py
legenda_dinamica.py
video.py
v6.py
"

for F in $COMPILE_FILES
do
    if [ ! -f "$F" ]; then
        fail "MISSING CORE FILE $F"
    fi

    python -m py_compile "$F" || fail "COMPILE $F"

    echo "$F=COMPILE_PASS"
done

echo "CORE_COMPILE=PASS"

# ============================================================
# 2. VSE RUNTIME CERTIFICATION
# ============================================================

run_stage \
"2. VSE4 RUNTIME CERTIFICATION" \
python visual_selection_engine_v4.py

# ============================================================
# 3. REVERIFY TRUTH / SEMANTICS
# ============================================================

run_stage \
"3A. POST-SCRIPT TRUTH LOCK RECHECK" \
python post_script_truth_lock.py "$SHORT_ID"

run_stage \
"3B. SEMANTIC INTEGRITY RECHECK" \
python semantic_integrity_gate.py "$SHORT_ID"

# ============================================================
# 4. CLEAN FAILED MEDIA ATTEMPT SAFELY
#
# Never delete it. Preserve it if it exists.
# ============================================================

MEDIA_DIR="imagens/short_${SHORT_ID}"

if [ -d "$MEDIA_DIR" ]; then

    COUNT=$(find "$MEDIA_DIR" -type f 2>/dev/null | wc -l)

    echo
    echo "EXISTING_MEDIA_FILES=$COUNT"

    if [ "$COUNT" -gt 0 ]; then

        STAMP=$(date +%Y%m%d_%H%M%S)

        PRESERVE_DIR="temp/pre_resume_media_${SHORT_ID}_${STAMP}"

        mv \
        "$MEDIA_DIR" \
        "$PRESERVE_DIR" \
        || fail "PRESERVE PREVIOUS MEDIA"

        echo "PREVIOUS_MEDIA_PRESERVED=$PRESERVE_DIR"
    fi
fi

mkdir -p "$MEDIA_DIR"

# ============================================================
# 5. FULL VISUAL / MEDIA PIPELINE
# ============================================================

run_stage \
"6/12 - SMART MEDIA SELECTOR — FULL POWER" \
python midia.py

run_stage \
"6A/12 - MEDIA MASTER GATE 5.1" \
python media_master_gate.py

run_stage \
"6B/12 - CINEMATIC MOTION DIRECTOR 3.8" \
python motion_director.py

run_stage \
"6C/12 - MONTAGE RHYTHM DIRECTOR 4.3" \
python rhythm_director.py

run_stage \
"6D/12 - PRODUCTION SUPERVISOR 5.0" \
python production_supervisor.py

run_stage \
"6E/12 - FINAL EDITORIAL GATE 5.0" \
python editorial_gate.py

# ============================================================
# 6. AUDIO / CAPTIONS
# ============================================================

run_stage \
"7/12 - PIPER VOICE" \
python audio.py

run_stage \
"8/12 - WHISPER + DYNAMIC CAPTIONS" \
python legenda_dinamica.py

# ============================================================
# 7. SEMANTIC VIDEO ASSEMBLY
# ============================================================

run_stage \
"9/12 - SEMANTIC SCENE ASSEMBLY" \
python video.py

# ============================================================
# 8. FINAL RENDER
# ============================================================

echo
echo "------------------------------------------------------------"
echo "10/12 - FINAL RENDER — V6"
echo "------------------------------------------------------------"
echo

FINAL=""

python v6.py
V6_RC=$?

if [ "$V6_RC" -eq 0 ]; then

    FINAL="videos/short_v6_${SHORT_ID}.mp4"

    echo "RENDER_ENGINE=V6"

else

    echo
    echo "V6_FAILED=$V6_RC"
    echo "TRYING_V5_FALLBACK=YES"

    if [ ! -f v5.py ]; then
        fail "V6 FAILED AND V5 MISSING"
    fi

    python v5.py
    V5_RC=$?

    if [ "$V5_RC" -ne 0 ]; then
        fail "V6 AND V5 RENDER"
    fi

    FINAL="videos/short_v5_${SHORT_ID}.mp4"

    echo "RENDER_ENGINE=V5_FALLBACK"
fi

if [ ! -s "$FINAL" ]; then
    fail "FINAL VIDEO NOT CREATED"
fi

echo "FINAL_VIDEO=$FINAL"

# ============================================================
# 9. QUALITY GATE
# ============================================================

if [ -f quality_check.py ]; then

    run_stage \
    "11/12 - QUALITY GATE" \
    python quality_check.py

else

    echo
    echo "QUALITY_CHECK_MISSING=YES"
    fail "QUALITY CHECK"
fi

# ============================================================
# 10. FINAL MEDIA TECHNICAL AUDIT
# ============================================================

echo
echo "------------------------------------------------------------"
echo "12/12 - FINAL TECHNICAL AUDIT"
echo "------------------------------------------------------------"
echo

ffprobe \
-v error \
-show_entries \
format=duration,size,bit_rate \
-show_entries \
stream=index,codec_name,width,height,r_frame_rate \
-of default=noprint_wrappers=1 \
"$FINAL"

FFPROBE_RC=$?

if [ "$FFPROBE_RC" -ne 0 ]; then
    fail "FFPROBE FINAL VIDEO"
fi

# ============================================================
# 11. COPY TO DOWNLOADS
# ============================================================

DOWNLOADS="$HOME/storage/downloads"

if [ -d "$DOWNLOADS" ]; then

    DEST="$DOWNLOADS/ShortAutoPro_FULL_POWER_${SHORT_ID}.mp4"

    cp -f \
    "$FINAL" \
    "$DEST" \
    || fail "COPY FINAL VIDEO"

    echo
    echo "DOWNLOAD_COPY=$DEST"
fi

# ============================================================
# SUCCESS
# ============================================================

echo
echo "============================================================"
echo " FULL POWER SHORT COMPLETED"
echo "============================================================"
echo "SHORT_ID=$SHORT_ID"
echo "FINAL_VIDEO=$FINAL"
echo "LOG=$LOG"
echo
echo "VSE4=ON"
echo "SCENE_COMMIT_LOCK=ON"
echo "RETENTION_ENGINE=ON"
echo "MUSIC=ON"
echo "SFX=ON"
echo "POP=ON"
echo "SEMANTIC_GATE=PASS"
echo "FULL_MEDIA_STACK=PASS"
echo "FINAL_RENDER=PASS"
echo "QUALITY_GATE=PASS"
echo
echo "FULL_POWER_RESULT=SUCCESS"
echo "============================================================"

exit 0
