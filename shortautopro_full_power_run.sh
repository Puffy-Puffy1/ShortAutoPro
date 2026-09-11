#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ROOT_NOT_FOUND"
    return 1 2>/dev/null || true
}

# ============================================================
# SHORTAUTOPRO - FULL POWER PRODUCTION RUNNER
# ============================================================

SHORT_ID="$(date +%Y-%m-%d_%H%M%S)"

export SHORT_ID

# ------------------------------------------------------------
# VISUAL INTELLIGENCE
# ------------------------------------------------------------

export SAP_VSE_V4=1
export SAP_SCENE_COMMIT_LOCK=1

# Mantemos camadas antigas disponíveis apenas se o projeto
# ainda fizer fallback internamente.
export SAP_VSE_V3="${SAP_VSE_V3:-1}"
export SAP_VSE_V2="${SAP_VSE_V2:-1}"

# ------------------------------------------------------------
# FINAL VIDEO
# ------------------------------------------------------------

export SHORT_RETENTION_ENGINE=1
export SHORT_USAR_MUSICA=1
export SHORT_USAR_SFX=1
export SHORT_USAR_POP=1

# Geração somente. Não publicar.
export SAP_NO_PUBLISH=1


LOG_DIR="logs/producao"
LOG="$LOG_DIR/full_power_${SHORT_ID}.log"

MEDIA_DIR="imagens/short_${SHORT_ID}"

FINAL="videos/short_v6_${SHORT_ID}.mp4"

mkdir -p \
"$LOG_DIR" \
temp \
videos \
imagens


echo
echo "============================================================"
echo " SHORTAUTOPRO - FULL POWER RUN"
echo "============================================================"
echo "SHORT_ID=$SHORT_ID"
echo "DATE=$(date)"
echo "PWD=$(pwd)"
echo
echo "SAP_VSE_V4=$SAP_VSE_V4"
echo "SAP_SCENE_COMMIT_LOCK=$SAP_SCENE_COMMIT_LOCK"
echo "SHORT_RETENTION_ENGINE=$SHORT_RETENTION_ENGINE"
echo "SHORT_USAR_MUSICA=$SHORT_USAR_MUSICA"
echo "SHORT_USAR_SFX=$SHORT_USAR_SFX"
echo "SHORT_USAR_POP=$SHORT_USAR_POP"
echo "SAP_NO_PUBLISH=$SAP_NO_PUBLISH"


# ============================================================
# 1. CORE COMPILE
# ============================================================

echo
echo "============================================================"
echo " 1. CORE COMPILE"
echo "============================================================"

COMPILE_FAIL=0

for F in \
visual_selection_engine_v4.py \
media_diversity_guard_v1.py \
media_provenance_capture_v1.py \
midia.py \
video.py \
v6.py
do

    if [ ! -f "$F" ]; then

        echo "MISSING=$F"
        COMPILE_FAIL=$((COMPILE_FAIL + 1))
        continue

    fi


    python -m py_compile "$F"

    RC=$?

    echo "$F COMPILE=$RC"

    if [ "$RC" -ne 0 ]; then
        COMPILE_FAIL=$((COMPILE_FAIL + 1))
    fi

done


bash -n gerar_short.sh

SHELL_RC=$?

echo "GERAR_SHORT_SYNTAX=$SHELL_RC"

if [ "$SHELL_RC" -ne 0 ]; then
    COMPILE_FAIL=$((COMPILE_FAIL + 1))
fi


# ============================================================
# 2. VSE4 RUNTIME CERTIFICATION
# ============================================================

echo
echo "============================================================"
echo " 2. VSE4 RUNTIME"
echo "============================================================"

python visual_selection_engine_v4.py

VSE4_RC=$?

echo "VSE4_SELF_TEST_STATUS=$VSE4_RC"


# ============================================================
# 3. PROVIDER ACQUISITION MAP
# ============================================================

echo
echo "============================================================"
echo " 3. PROVIDER ROUTING"
echo "============================================================"

python - <<'PY'
from pathlib import Path
import ast

src = Path("midia.py").read_text(
    encoding="utf-8",
    errors="replace",
)

tree = ast.parse(src)

providers = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",
}

defined = set()
calls = set()

for node in ast.walk(tree):

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        defined.add(node.name)

    if isinstance(node, ast.Call):

        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)

        elif isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)


for name in sorted(providers):

    print(
        f"{name}_DEFINED="
        f"{'YES' if name in defined else 'NO'}"
    )

    print(
        f"{name}_CALLED="
        f"{'YES' if name in calls else 'NO'}"
    )


print(
    "PROVIDER_ROUTE_AUDIT=COMPLETE"
)
PY


# ============================================================
# 4. PRE-LAUNCH GATE
# ============================================================

echo
echo "============================================================"
echo " 4. PRE-LAUNCH GATE"
echo "============================================================"

if [ "$COMPILE_FAIL" -eq 0 ]; then
    echo "CORE_COMPILE_GATE=PASS"
else
    echo "CORE_COMPILE_GATE=FAIL"
fi


if [ "$VSE4_RC" -eq 0 ]; then
    echo "VSE4_RUNTIME_GATE=PASS"
else
    echo "VSE4_RUNTIME_GATE=FAIL"
fi


if [ "$COMPILE_FAIL" -ne 0 ] ||
   [ "$VSE4_RC" -ne 0 ]
then

    echo
    echo "============================================================"
    echo " FULL POWER RUN ABORTED SAFELY"
    echo "============================================================"

    echo "PIPELINE_EXECUTED=NO"
    echo "SHORT_ID=$SHORT_ID"
    echo "TERMUX_CONTINUA_ABERTO=SIM"

    return 1 2>/dev/null || true
fi


# ============================================================
# 5. PIPELINE COMPLETO
# ============================================================

echo
echo "============================================================"
echo " 5. EXECUTING FULL SHORTAUTOPRO"
echo "============================================================"
echo
echo "LOG=$LOG"
echo


bash ./gerar_short.sh \
2>&1 |
tee "$LOG"

PIPELINE_RC=${PIPESTATUS[0]}


echo
echo "============================================================"
echo " 6. PIPELINE RESULT"
echo "============================================================"

echo "PIPELINE_STATUS=$PIPELINE_RC"


# ============================================================
# 7. MEDIA STRUCTURE CERTIFICATION
# ============================================================

echo
echo "============================================================"
echo " 7. MEDIA STRUCTURE"
echo "============================================================"

MEDIA_TOTAL=0
MEDIA_BAD=0


for N in $(seq -w 1 12)
do

    COUNT="$(
        find "$MEDIA_DIR" \
        -maxdepth 1 \
        -type f \
        -name "scene_${N}.*" \
        2>/dev/null |
        wc -l
    )"

    MEDIA_TOTAL=$((MEDIA_TOTAL + COUNT))

    if [ "$COUNT" -eq 1 ]; then

        FILE="$(
            find "$MEDIA_DIR" \
            -maxdepth 1 \
            -type f \
            -name "scene_${N}.*" \
            2>/dev/null |
            head -n 1
        )"

        SIZE="$(
            stat -c%s "$FILE" \
            2>/dev/null
        )"

        HASH="$(
            sha256sum "$FILE" \
            2>/dev/null |
            awk '{print $1}'
        )"

        echo \
        "SCENE_${N}=PASS | ${SIZE} bytes | ${HASH} | ${FILE}"

    else

        echo "SCENE_${N}=FAIL count=$COUNT"

        MEDIA_BAD=$((MEDIA_BAD + 1))

    fi

done


echo
echo "MEDIA_TOTAL=$MEDIA_TOTAL"
echo "MEDIA_BAD_SCENES=$MEDIA_BAD"

if [ "$MEDIA_TOTAL" -eq 12 ] &&
   [ "$MEDIA_BAD" -eq 0 ]
then
    echo "MEDIA_STRUCTURE=PASS"
else
    echo "MEDIA_STRUCTURE=FAIL"
fi


# ============================================================
# 8. MEDIA FINGERPRINT
# ============================================================

echo
echo "============================================================"
echo " 8. MEDIA FINGERPRINT"
echo "============================================================"

if [ -f render_input_fingerprint_v1.py ]; then

    python render_input_fingerprint_v1.py

else

    python - <<'PY'
import hashlib
import os
from pathlib import Path

sid = os.environ["SHORT_ID"]

root = (
    Path.home()
    / "ShortAutoPro"
    / "imagens"
    / f"short_{sid}"
)

h = hashlib.sha256()

count = 0

for n in range(1, 13):

    files = list(
        root.glob(
            f"scene_{n:02d}.*"
        )
    )

    if len(files) != 1:
        continue

    p = files[0]

    fh = hashlib.sha256(
        p.read_bytes()
    ).hexdigest()

    h.update(
        f"{p.name}:{fh}\n".encode()
    )

    count += 1


print(
    "MEDIA_COUNT=",
    count,
)

print(
    "INPUT_FINGERPRINT=",
    h.hexdigest(),
)
PY

fi


# ============================================================
# 9. VSE4 TELEMETRY
# ============================================================

echo
echo "============================================================"
echo " 9. VSE4 TELEMETRY"
echo "============================================================"

grep -Ei \
'VSE4|HARD_MISMATCH|GEO_|MUST|RESCUE|COMMIT_LOCK|ESCOLHIDO|PROVIDER|FAILOVER' \
"$LOG" \
2>/dev/null |
tail -n 500


# ============================================================
# 10. PROVIDER DISTRIBUTION
# ============================================================

echo
echo "============================================================"
echo " 10. PROVIDER DISTRIBUTION"
echo "============================================================"

for PROVIDER in \
Pexels \
Pixabay \
Coverr \
Wikimedia
do

    COUNT="$(
        grep -Ei \
        "ESCOLHIDO:.*${PROVIDER}|${PROVIDER}.*ESCOLHIDO" \
        "$LOG" \
        2>/dev/null |
        wc -l
    )"

    echo "${PROVIDER}_SELECTED=$COUNT"

done


echo
echo "===== DOWNLOAD PROVIDERS ====="

grep -Ei \
'DOWNLOAD PRIORITÁRIO:|ESCOLHIDO:' \
"$LOG" \
2>/dev/null |
tail -n 100


# ============================================================
# 11. VSE4 QUALITY COUNTERS
# ============================================================

echo
echo "============================================================"
echo " 11. VISUAL QUALITY COUNTERS"
echo "============================================================"

MUST_22="$(
    grep -E \
    'MUST COVERAGE: 2/2' \
    "$LOG" \
    2>/dev/null |
    wc -l
)"

MUST_12="$(
    grep -E \
    'MUST COVERAGE: 1/2' \
    "$LOG" \
    2>/dev/null |
    wc -l
)"

HARD_REJECT="$(
    grep -Ei \
    'hard.?mismatch.*true|HARD_MISMATCH.*YES|geo.*contradiction.*reject' \
    "$LOG" \
    2>/dev/null |
    wc -l
)"

COMMIT_COUNT="$(
    grep -E \
    'SCENE_COMMIT_LOCK=COMMITTED' \
    "$LOG" \
    2>/dev/null |
    wc -l
)"

BLOCK_COUNT="$(
    grep -E \
    'SCENE_COMMIT_LOCK=BLOCKED' \
    "$LOG" \
    2>/dev/null |
    wc -l
)"


echo "MUST_2_OF_2=$MUST_22"
echo "MUST_1_OF_2=$MUST_12"
echo "HARD_MISMATCH_REJECTIONS=$HARD_REJECT"
echo "COMMIT_LOCK_COMMITS=$COMMIT_COUNT"
echo "COMMIT_LOCK_BLOCKS=$BLOCK_COUNT"


# ============================================================
# 12. FINAL VIDEO CERTIFICATION
# ============================================================

echo
echo "============================================================"
echo " 12. FINAL VIDEO"
echo "============================================================"


if [ -s "$FINAL" ]; then

    echo "FINAL_EXISTS=YES"

    FINAL_HASH="$(
        sha256sum "$FINAL" |
        awk '{print $1}'
    )"

    VIDEO_STREAM_HASH="$(
        ffmpeg \
        -v error \
        -i "$FINAL" \
        -map 0:v:0 \
        -c copy \
        -f hash \
        -hash sha256 \
        - \
        2>/dev/null |
        sed -n 's/^SHA256=//p'
    )"

    echo "FINAL_SHA256=$FINAL_HASH"
    echo "VIDEO_STREAM_SHA256=$VIDEO_STREAM_HASH"

    ffprobe \
    -v error \
    -show_entries \
stream=codec_name,codec_type,width,height,r_frame_rate \
    -show_entries \
format=duration,size,bit_rate \
    -of default=noprint_wrappers=1 \
    "$FINAL"


    # --------------------------------------------------------
    # EXPORT EXATO
    # --------------------------------------------------------

    DEST="$HOME/storage/downloads/ShortAutoPro_FULL_POWER_${SHORT_ID}.mp4"

    rm -f "$DEST"

    cp -f \
    "$FINAL" \
    "$DEST"

    sync


    if [ -s "$DEST" ]; then

        DEST_HASH="$(
            sha256sum "$DEST" |
            awk '{print $1}'
        )"

        echo
        echo "SOURCE_HASH=$FINAL_HASH"
        echo "DEST_HASH=$DEST_HASH"


        if [ -n "$FINAL_HASH" ] &&
           [ "$FINAL_HASH" = "$DEST_HASH" ]
        then

            echo "EXPORT_INTEGRITY=PASS"
            echo "VIDEO_PRONTO=$DEST"

        else

            echo "EXPORT_INTEGRITY=FAIL"

        fi

    else

        echo "EXPORT_INTEGRITY=FAIL"

    fi

else

    echo "FINAL_EXISTS=NO"

fi


# ============================================================
# 13. FINAL PRODUCTION STATUS
# ============================================================

echo
echo "============================================================"
echo " FULL POWER PRODUCTION SUMMARY"
echo "============================================================"

echo "SHORT_ID=$SHORT_ID"
echo "PIPELINE_STATUS=$PIPELINE_RC"
echo "MEDIA_TOTAL=$MEDIA_TOTAL"
echo "MEDIA_BAD_SCENES=$MEDIA_BAD"
echo "MUST_2_OF_2=$MUST_22"
echo "MUST_1_OF_2=$MUST_12"
echo "HARD_MISMATCH_REJECTIONS=$HARD_REJECT"
echo "COMMIT_LOCK_COMMITS=$COMMIT_COUNT"
echo "COMMIT_LOCK_BLOCKS=$BLOCK_COUNT"


if [ "$PIPELINE_RC" -eq 0 ] &&
   [ "$MEDIA_TOTAL" -eq 12 ] &&
   [ "$MEDIA_BAD" -eq 0 ] &&
   [ -s "$FINAL" ]
then

    echo
    echo "FULL_POWER_STATUS=PASS"

else

    echo
    echo "FULL_POWER_STATUS=FAIL"

fi


echo
echo "LOG=$LOG"
echo "TERMUX_CONTINUA_ABERTO=SIM"
echo "============================================================"


# ============================================================
# SHORTAUTOPRO GALLERY EXPORT V1
# ============================================================

echo
echo "============================================================"
echo " GALLERY EXPORT"
echo "============================================================"

if [ -s "$FINAL" ]; then

    if [ -d "$HOME/storage/shared" ]; then

        GALLERY_DIR="$HOME/storage/movies/ShortAutoPro"

        if [ ! -d "$HOME/storage/movies" ]; then
            GALLERY_DIR="$HOME/storage/shared/Movies/ShortAutoPro"
        fi

        mkdir -p "$GALLERY_DIR"

        GALLERY_FILE="$GALLERY_DIR/ShortAutoPro_${SHORT_ID}.mp4"

        rm -f "$GALLERY_FILE"

        cp -f \
        "$FINAL" \
        "$GALLERY_FILE"

        sync

        SOURCE_HASH="$(
            sha256sum "$FINAL" |
            awk '{print $1}'
        )"

        DEST_HASH="$(
            sha256sum "$GALLERY_FILE" |
            awk '{print $1}'
        )"

        if [ -n "$SOURCE_HASH" ] &&
           [ "$SOURCE_HASH" = "$DEST_HASH" ]
        then

            echo "GALLERY_COPY=PASS"

            if command -v termux-media-scan >/dev/null 2>&1; then

                termux-media-scan \
                "$GALLERY_FILE" \
                >/dev/null 2>&1

                echo "GALLERY_SCAN=PASS"

            else

                am broadcast \
                -a android.intent.action.MEDIA_SCANNER_SCAN_FILE \
                -d "file://$GALLERY_FILE" \
                >/dev/null 2>&1

                echo "GALLERY_SCAN=FALLBACK"

            fi

            echo "GALLERY_EXPORT=PASS"
            echo "VIDEO_NA_GALERIA=$GALLERY_FILE"

        else

            echo "GALLERY_EXPORT=FAIL_HASH"

        fi

    else

        echo "GALLERY_EXPORT=FAIL_STORAGE_NOT_READY"

    fi

else

    echo "GALLERY_EXPORT=SKIPPED_NO_FINAL_VIDEO"

fi

# SHORTAUTOPRO GALLERY EXPORT V1 END

