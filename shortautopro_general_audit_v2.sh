#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || return 1 2>/dev/null

STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="temp/GENERAL_AUDIT_V2_${STAMP}.txt"

mkdir -p temp

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    echo "PASS | $*"
}

warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    echo "WARN | $*"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "FAIL | $*"
}


{
echo "======================================================================"
echo " SHORTAUTOPRO - GENERAL SYSTEM AUDIT V2"
echo "======================================================================"
echo "DATE=$(date)"
echo "PWD=$(pwd)"
echo


echo "======================================================================"
echo " 1. CORE FILES"
echo "======================================================================"

CORE_FILES="
midia.py
video.py
v6.py
gerar_short.sh
legenda_dinamica.py
visual_selection_engine_v4.py
media_diversity_guard_v1.py
media_provenance_capture_v1.py
visual_scene_commit_lock_v1.py
fresh_render_guard_v1.py
render_input_fingerprint_v1.py
"

for F in $CORE_FILES
do
    if [ -s "$F" ]; then
        echo "FOUND | $F | $(stat -c%s "$F") bytes"
    else
        fail "CORE_FILE_MISSING_OR_EMPTY=$F"
    fi
done

echo


echo "======================================================================"
echo " 2. CORE HASHES"
echo "======================================================================"

for F in \
midia.py \
video.py \
v6.py \
gerar_short.sh \
visual_selection_engine_v4.py
do
    if [ -f "$F" ]; then
        sha256sum "$F"
    fi
done

echo


echo "======================================================================"
echo " 3. ALL ROOT PYTHON COMPILE"
echo "======================================================================"

PY_TOTAL=0
PY_FAIL=0

while IFS= read -r F
do
    PY_TOTAL=$((PY_TOTAL + 1))

    python -m py_compile "$F" >/dev/null 2>&1

    if [ "$?" -ne 0 ]; then
        echo "PY_COMPILE_FAIL=$F"
        PY_FAIL=$((PY_FAIL + 1))
    fi

done < <(
    find . \
    -maxdepth 1 \
    -type f \
    -name '*.py' \
    -printf '%p\n' \
    | sort
)

echo "PY_FILES_CHECKED=$PY_TOTAL"
echo "PY_COMPILE_FAILURES=$PY_FAIL"

if [ "$PY_FAIL" -eq 0 ]; then
    pass "ALL_ROOT_PYTHON_COMPILE"
else
    fail "PYTHON_COMPILE_FAILURES=$PY_FAIL"
fi

echo


echo "======================================================================"
echo " 4. ROOT SHELL SYNTAX"
echo "======================================================================"

SH_TOTAL=0
SH_FAIL=0

while IFS= read -r F
do
    SH_TOTAL=$((SH_TOTAL + 1))

    bash -n "$F" >/dev/null 2>&1

    if [ "$?" -ne 0 ]; then
        echo "SHELL_SYNTAX_FAIL=$F"
        SH_FAIL=$((SH_FAIL + 1))
    fi

done < <(
    find . \
    -maxdepth 1 \
    -type f \
    -name '*.sh' \
    -printf '%p\n' \
    | sort
)

echo "SHELL_FILES_CHECKED=$SH_TOTAL"
echo "SHELL_FAILURES=$SH_FAIL"

if [ "$SH_FAIL" -eq 0 ]; then
    pass "ALL_ROOT_SHELL_SYNTAX"
else
    fail "SHELL_SYNTAX_FAILURES=$SH_FAIL"
fi

echo


echo "======================================================================"
echo " 5. REQUIRED BINARIES"
echo "======================================================================"

for BIN in \
python \
ffmpeg \
ffprobe
do

    if command -v "$BIN" >/dev/null 2>&1; then
        pass "BINARY_$BIN"
        command -v "$BIN"
    else
        fail "BINARY_MISSING_$BIN"
    fi

done

WHISPER="$HOME/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL="$HOME/whisper.cpp/models/ggml-base.bin"

if [ -x "$WHISPER" ]; then
    pass "WHISPER_BINARY"
else
    fail "WHISPER_BINARY_MISSING"
fi

if [ -s "$WHISPER_MODEL" ]; then
    pass "WHISPER_MODEL"
    ls -lh "$WHISPER_MODEL"
else
    fail "WHISPER_MODEL_MISSING"
fi

echo


echo "======================================================================"
echo " 6. VSE4 MODULE LOAD"
echo "======================================================================"

python - <<'PY'
import runpy
import sys
import traceback

try:
    ns = runpy.run_path(
        "visual_selection_engine_v4.py",
        run_name="general_audit_load",
    )

    required = (
        "candidate_text",
        "tokens",
        "concept_hits",
        "geo_hits",
        "score_candidate",
    )

    missing = [
        name
        for name in required
        if not callable(ns.get(name))
    ]

    if missing:
        print(
            "VSE4_MODULE_LOAD=FAIL "
            + ",".join(missing)
        )
        raise SystemExit(1)

    print("VSE4_MODULE_LOAD=PASS")

except Exception:
    print("VSE4_MODULE_LOAD=FAIL")
    traceback.print_exc()
    raise
PY

VSE_LOAD=$?

if [ "$VSE_LOAD" -eq 0 ]; then
    pass "VSE4_MODULE_LOAD"
else
    fail "VSE4_MODULE_LOAD"
fi

echo


echo "======================================================================"
echo " 7. VSE4 GLOBAL SYMBOL AUDIT"
echo "======================================================================"

python - <<'PY'
from pathlib import Path
import symtable
import builtins

src = Path(
    "visual_selection_engine_v4.py"
).read_text(
    encoding="utf-8"
)

table = symtable.symtable(
    src,
    "visual_selection_engine_v4.py",
    "exec",
)

defined = set()

for symbol in table.get_symbols():

    if (
        symbol.is_assigned()
        or symbol.is_imported()
        or symbol.is_namespace()
    ):
        defined.add(
            symbol.get_name()
        )

builtins_set = set(
    dir(builtins)
)

unresolved = set()


def walk(scope):

    for child in scope.get_children():

        for symbol in child.get_symbols():

            name = symbol.get_name()

            if not symbol.is_referenced():
                continue

            if not symbol.is_global():
                continue

            if name in defined:
                continue

            if name in builtins_set:
                continue

            unresolved.add(
                name
            )

        walk(child)


walk(table)

if unresolved:
    print(
        "TRUE_UNRESOLVED_GLOBALS="
        + ",".join(
            sorted(unresolved)
        )
    )
    raise SystemExit(1)

print("TRUE_UNRESOLVED_GLOBALS=NONE")
print("GLOBAL_SYMBOL_AUDIT=PASS")
PY

VSE_GLOBAL=$?

if [ "$VSE_GLOBAL" -eq 0 ]; then
    pass "VSE4_GLOBAL_SYMBOL_AUDIT"
else
    fail "VSE4_GLOBAL_SYMBOL_AUDIT"
fi

echo


echo "======================================================================"
echo " 8. VSE4 GEO + SEMANTIC SAFETY"
echo "======================================================================"

python - <<'PY'
import runpy
import traceback

try:
    ns = runpy.run_path(
        "visual_selection_engine_v4.py",
        run_name="general_audit_semantics",
    )

    geo_hits = ns["geo_hits"]
    concept_hits = ns["concept_hits"]

    sp = set(
        geo_hits(
            "Investigação em apartamento "
            "na cidade de São Paulo Brasil"
        )
    )

    ny = set(
        geo_hits(
            "Empire State Building "
            "Manhattan New York USA"
        )
    )

    forensic = set(
        concept_hits(
            "laudo pericial forensic evidence"
        )
    )

    police = set(
        concept_hits(
            "police investigation detective"
        )
    )

    print(
        "SAO_PAULO_GEO=",
        sorted(sp),
    )

    print(
        "NEW_YORK_GEO=",
        sorted(ny),
    )

    print(
        "FORENSIC_CONCEPTS=",
        sorted(forensic),
    )

    print(
        "POLICE_CONCEPTS=",
        sorted(police),
    )

    checks = [
        bool(sp),
        bool(ny),
        sp != ny,
        bool(forensic),
        bool(police),
    ]

    if not all(checks):
        print("VSE4_SEMANTIC_FOUNDATION=FAIL")
        raise SystemExit(1)

    print("VSE4_SEMANTIC_FOUNDATION=PASS")

except Exception:
    traceback.print_exc()
    raise
PY

SEMANTIC=$?

if [ "$SEMANTIC" -eq 0 ]; then
    pass "VSE4_SEMANTIC_FOUNDATION"
else
    fail "VSE4_SEMANTIC_FOUNDATION"
fi

echo


echo "======================================================================"
echo " 9. VSE4 HARD MISMATCH REGRESSION"
echo "======================================================================"

python - <<'PY'
import runpy
import traceback

try:

    ns = runpy.run_path(
        "visual_selection_engine_v4.py",
        run_name="general_audit_vse4",
    )

    score = ns[
        "score_candidate"
    ]

    state = {
        "providers": [],
        "groups": [],
        "types": [],
        "keys": [],
    }


    cases = [

        (
            "SP_VS_NEW_YORK",

            "Investigação em apartamento "
            "em São Paulo Brasil",

            {
                "provider":
                    "Pixabay",

                "tipo":
                    "foto",

                "title":
                    "Empire State Building "
                    "Manhattan New York",

                "must":
                    "2/2",

                "score":
                    250,

                "width":
                    1920,

                "height":
                    1080,
            },

            True,
        ),


        (
            "SP_CORRECT",

            "Investigação em apartamento "
            "em São Paulo Brasil",

            {
                "provider":
                    "Wikimedia",

                "tipo":
                    "foto",

                "title":
                    "Apartment building "
                    "Sao Paulo Brazil",

                "must":
                    "1/2",

                "score":
                    110,

                "width":
                    1920,

                "height":
                    1080,
            },

            False,
        ),
    ]


    failed = []


    for (
        name,
        scene,
        candidate,
        expected,
    ) in cases:

        result = score(
            candidate,
            scene,
            state,
        )

        hard = bool(
            result.get(
                "hard_mismatch",
                False,
            )
        )

        print(
            f"{name}_HARD_MISMATCH="
            f"{hard}"
        )

        print(
            f"{name}_EFFECTIVE="
            f"{result.get('effective')}"
        )

        print(
            f"{name}_RESULT="
            f"{result}"
        )

        if hard != expected:
            failed.append(name)


    if failed:

        print(
            "VSE4_HARD_MISMATCH_REGRESSION=FAIL "
            + ",".join(failed)
        )

        raise SystemExit(1)


    print(
        "VSE4_HARD_MISMATCH_REGRESSION=PASS"
    )

except Exception:

    traceback.print_exc()
    raise
PY

VSE_HARD=$?

if [ "$VSE_HARD" -eq 0 ]; then
    pass "VSE4_HARD_MISMATCH_REGRESSION"
else
    fail "VSE4_HARD_MISMATCH_REGRESSION"
fi

echo


echo "======================================================================"
echo " 10. VSE4 SELF TEST"
echo "======================================================================"

python visual_selection_engine_v4.py \
> "temp/general_audit_vse4_selftest.log" \
2>&1

VSE_SELF=$?

cat "temp/general_audit_vse4_selftest.log"

if [ "$VSE_SELF" -eq 0 ]; then
    pass "VSE4_SELF_TEST"
else
    fail "VSE4_SELF_TEST"
fi

echo


echo "======================================================================"
echo " 11. VSE4 <-> MIDIA INTEGRATION"
echo "======================================================================"

if grep -qi \
'visual_selection_engine_v4' \
midia.py
then
    pass "MIDIA_REFERENCES_VSE4"
else
    warn "MIDIA_REFERENCES_VSE4=NO"
fi

grep -nEi \
'VSE4|visual_selection_engine_v4|score_candidate|hard_mismatch' \
midia.py \
2>/dev/null \
| head -n 100

echo


echo "======================================================================"
echo " 12. COMMIT LOCK INTEGRATION"
echo "======================================================================"

if grep -Rqi \
'SCENE_COMMIT_LOCK' \
--include='*.py' \
. \
2>/dev/null
then
    pass "SCENE_COMMIT_LOCK_CODE_FOUND"
else
    warn "SCENE_COMMIT_LOCK_CODE_NOT_FOUND"
fi

grep -Rni \
'SCENE_COMMIT_LOCK' \
--include='*.py' \
. \
2>/dev/null \
| head -n 50

echo


echo "======================================================================"
echo " 13. PROVIDER ACQUISITION STRUCTURE"
echo "======================================================================"

python - <<'PY'
from pathlib import Path
import ast

src = Path(
    "midia.py"
).read_text(
    encoding="utf-8"
)

tree = ast.parse(src)

required_defs = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
}

defs = {
    node.name
    for node in tree.body
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    )
}

missing = sorted(
    required_defs - defs
)

print(
    "PROVIDER_FUNCTIONS_MISSING="
    + (
        ",".join(missing)
        if missing
        else
        "NONE"
    )
)

if missing:
    raise SystemExit(1)


target = next(
    node
    for node in tree.body
    if (
        isinstance(
            node,
            ast.FunctionDef,
        )
        and
        node.name == "buscar_todos_candidatos"
    )
)

calls = set()

for node in ast.walk(target):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    if isinstance(
        node.func,
        ast.Name,
    ):
        calls.add(
            node.func.id
        )


expected_calls = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}

missing_calls = sorted(
    expected_calls - calls
)

print(
    "PROVIDER_CALLS_MISSING="
    + (
        ",".join(missing_calls)
        if missing_calls
        else
        "NONE"
    )
)

if missing_calls:
    raise SystemExit(1)

print(
    "PROVIDER_ACQUISITION_STRUCTURE=PASS"
)
PY

PROVIDER_TEST=$?

if [ "$PROVIDER_TEST" -eq 0 ]; then
    pass "PROVIDER_ACQUISITION_STRUCTURE"
else
    fail "PROVIDER_ACQUISITION_STRUCTURE"
fi

echo


echo "======================================================================"
echo " 14. DETECT CURRENT/LATEST SHORT"
echo "======================================================================"

LATEST_SHORT_FILE="$(
    find roteiros \
    -maxdepth 1 \
    -type f \
    -name 'short_*.txt' \
    ! -name '*pre_*' \
    -printf '%T@ %p\n' \
    2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | cut -d' ' -f2-
)"

CURRENT_ID=""

if [ -n "$LATEST_SHORT_FILE" ]; then

    BASE_NAME="$(
        basename "$LATEST_SHORT_FILE"
    )"

    CURRENT_ID="$(
        printf '%s' "$BASE_NAME" \
        | sed \
        -e 's/^short_//' \
        -e 's/\.txt$//'
    )"

    echo "CURRENT_SHORT_FILE=$LATEST_SHORT_FILE"
    echo "CURRENT_SHORT_ID=$CURRENT_ID"

    pass "CURRENT_SHORT_ID_RESOLVED"

else

    warn "CURRENT_SHORT_ID_NOT_RESOLVED"

fi

echo


echo "======================================================================"
echo " 15. CURRENT SHORT MEDIA STRUCTURE"
echo "======================================================================"

if [ -n "$CURRENT_ID" ]; then

    MEDIA_DIR="imagens/short_${CURRENT_ID}"

    if [ -d "$MEDIA_DIR" ]; then

        TOTAL_MEDIA=0
        BAD_SCENES=0

        for N in $(seq -w 1 12)
        do

            COUNT="$(
                find "$MEDIA_DIR" \
                -maxdepth 1 \
                -type f \
                -name "scene_${N}.*" \
                2>/dev/null \
                | wc -l
            )"

            echo "SCENE_${N}_COUNT=$COUNT"

            find "$MEDIA_DIR" \
            -maxdepth 1 \
            -type f \
            -name "scene_${N}.*" \
            -printf '  %s bytes | %f\n' \
            2>/dev/null

            TOTAL_MEDIA=$(
                (
                    TOTAL_MEDIA
                    +
                    COUNT
                )
            )

            if [ "$COUNT" -ne 1 ]; then
                BAD_SCENES=$(
                    (
                        BAD_SCENES
                        +
                        1
                    )
                )
            fi

        done

        echo "MEDIA_TOTAL=$TOTAL_MEDIA"
        echo "MEDIA_BAD_SCENES=$BAD_SCENES"

        if \
        [ "$TOTAL_MEDIA" -eq 12 ] &&
        [ "$BAD_SCENES" -eq 0 ]
        then
            pass "CURRENT_MEDIA_STRUCTURE"
        else
            fail "CURRENT_MEDIA_STRUCTURE"
        fi

    else

        warn "MEDIA_DIR_MISSING=$MEDIA_DIR"

    fi

else

    warn "CURRENT_MEDIA_STRUCTURE_SKIPPED"

fi

echo


echo "======================================================================"
echo " 16. CURRENT MEDIA TECHNICAL VALIDITY"
echo "======================================================================"

if \
[ -n "$CURRENT_ID" ] &&
[ -d "imagens/short_${CURRENT_ID}" ]
then

    MEDIA_VALID=0
    MEDIA_INVALID=0

    for F in \
    imagens/short_${CURRENT_ID}/scene_*
    do

        [ -f "$F" ] || continue

        SIZE="$(stat -c%s "$F" 2>/dev/null)"

        if [ -z "$SIZE" ] || [ "$SIZE" -lt 1024 ]; then

            echo "MEDIA_INVALID_TOO_SMALL=$F"
            MEDIA_INVALID=$((MEDIA_INVALID + 1))
            continue

        fi


        case "${F##*.}" in

            mp4|MP4)

                ffprobe \
                -v error \
                -show_entries stream=codec_type \
                -of csv=p=0 \
                "$F" \
                >/dev/null \
                2>&1

                if [ "$?" -eq 0 ]; then
                    MEDIA_VALID=$((MEDIA_VALID + 1))
                else
                    echo "MEDIA_INVALID_FFPROBE=$F"
                    MEDIA_INVALID=$((MEDIA_INVALID + 1))
                fi
                ;;


            jpg|jpeg|JPG|JPEG|png|PNG|webp|WEBP)

                python - "$F" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
b = p.read_bytes()[:16]

valid = (
    b.startswith(b"\xff\xd8\xff")
    or b.startswith(b"\x89PNG\r\n\x1a\n")
    or (
        len(b) >= 12
        and b[:4] == b"RIFF"
        and b[8:12] == b"WEBP"
    )
)

raise SystemExit(
    0 if valid else 1
)
PY

                if [ "$?" -eq 0 ]; then
                    MEDIA_VALID=$((MEDIA_VALID + 1))
                else
                    echo "MEDIA_INVALID_SIGNATURE=$F"
                    MEDIA_INVALID=$((MEDIA_INVALID + 1))
                fi
                ;;


            *)

                echo "MEDIA_UNKNOWN_EXTENSION=$F"
                MEDIA_INVALID=$((MEDIA_INVALID + 1))
                ;;

        esac

    done

    echo "MEDIA_VALID_COUNT=$MEDIA_VALID"
    echo "MEDIA_INVALID_COUNT=$MEDIA_INVALID"

    if [ "$MEDIA_INVALID" -eq 0 ]; then
        pass "CURRENT_MEDIA_TECHNICAL_VALIDITY"
    else
        fail "CURRENT_MEDIA_INVALID=$MEDIA_INVALID"
    fi

else

    warn "MEDIA_TECHNICAL_VALIDITY_SKIPPED"

fi

echo


echo "======================================================================"
echo " 17. CURRENT AUDIO / ASS / RENDER INPUTS"
echo "======================================================================"

if [ -n "$CURRENT_ID" ]; then

    AUDIO="audios/short_${CURRENT_ID}.mp3"
    ASS="videos/short_${CURRENT_ID}.ass"
    VIDEO_BASE="temp/${CURRENT_ID}/video_sem_audio.mp4"
    FINAL="videos/short_v6_${CURRENT_ID}.mp4"

    for ITEM in \
    "$AUDIO" \
    "$ASS"
    do

        if [ -s "$ITEM" ]; then
            echo "INPUT_FOUND | $(stat -c%s "$ITEM") | $ITEM"
        else
            warn "INPUT_MISSING=$ITEM"
        fi

    done

    if [ -s "$VIDEO_BASE" ]; then
        echo "VIDEO_BASE_FOUND=$(stat -c%s "$VIDEO_BASE")"
    else
        echo "VIDEO_BASE_NOT_PRESENT=$VIDEO_BASE"
    fi

    if [ -s "$FINAL" ]; then

        echo "FINAL_FOUND=$(stat -c%s "$FINAL")"

        ffprobe \
        -v error \
        -show_entries format=duration,size,bit_rate \
        -show_entries stream=codec_name,codec_type,width,height,r_frame_rate \
        -of default=noprint_wrappers=1 \
        "$FINAL"

    else

        echo "FINAL_NOT_PRESENT=$FINAL"

    fi

fi

echo


echo "======================================================================"
echo " 18. ACTIVE JSON VALIDITY"
echo "======================================================================"

JSON_FAIL=0
JSON_TOTAL=0

for D in \
roteiros \
manifests \
credits
do

    [ -d "$D" ] || continue

    while IFS= read -r -d '' F
    do

        JSON_TOTAL=$((JSON_TOTAL + 1))

        python -m json.tool \
        "$F" \
        >/dev/null \
        2>&1

        if [ "$?" -ne 0 ]; then
            echo "JSON_INVALID=$F"
            JSON_FAIL=$((JSON_FAIL + 1))
        fi

    done < <(
        find "$D" \
        -type f \
        -name '*.json' \
        -print0 \
        2>/dev/null
    )

done

echo "JSON_FILES_CHECKED=$JSON_TOTAL"
echo "JSON_INVALID_COUNT=$JSON_FAIL"

if [ "$JSON_FAIL" -eq 0 ]; then
    pass "JSON_VALIDITY"
else
    fail "JSON_INVALID_COUNT=$JSON_FAIL"
fi

echo


echo "======================================================================"
echo " 19. ZERO-BYTE ACTIVE FILES"
echo "======================================================================"

ZERO_COUNT=0

while IFS= read -r F
do

    [ -n "$F" ] || continue

    echo "ZERO_BYTE=$F"
    ZERO_COUNT=$((ZERO_COUNT + 1))

done < <(
    find \
    roteiros \
    imagens \
    audios \
    videos \
    manifests \
    credits \
    -maxdepth 3 \
    -type f \
    -size 0 \
    2>/dev/null \
    | head -n 200
)

echo "ZERO_BYTE_COUNT=$ZERO_COUNT"

if [ "$ZERO_COUNT" -eq 0 ]; then
    pass "NO_ZERO_BYTE_ACTIVE_FILES"
else
    warn "ZERO_BYTE_FILES_FOUND=$ZERO_COUNT"
fi

echo


echo "======================================================================"
echo " 20. DUPLICATE MEDIA SHA IN CURRENT SHORT"
echo "======================================================================"

if \
[ -n "$CURRENT_ID" ] &&
[ -d "imagens/short_${CURRENT_ID}" ]
then

    python - <<PY
from pathlib import Path
import hashlib
from collections import defaultdict

root = Path(
    "imagens/short_${CURRENT_ID}"
)

groups = defaultdict(list)

for path in sorted(root.glob("scene_*.*")):

    if not path.is_file():
        continue

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    groups[h.hexdigest()].append(
        path.name
    )


dupes = [
    (sha, names)
    for sha, names in groups.items()
    if len(names) > 1
]


if dupes:

    for sha, names in dupes:
        print(
            "DUPLICATE_SHA="
            f"{sha} "
            + ",".join(names)
        )

    print(
        "DUPLICATE_MEDIA_COUNT=",
        len(dupes),
    )

else:

    print(
        "DUPLICATE_MEDIA_COUNT=0"
    )
PY

fi

echo


echo "======================================================================"
echo " 21. GENERIC / STALE RENDER ARTIFACTS"
echo "======================================================================"

GENERIC_COUNT=0

while IFS= read -r F
do

    [ -n "$F" ] || continue

    echo "GENERIC_RENDER_ARTIFACT=$F"
    GENERIC_COUNT=$((GENERIC_COUNT + 1))

done < <(
    find temp \
    -maxdepth 4 \
    -type f \
    \( \
        -name 'final.mp4' \
        -o \
        -name 'video.mp4' \
        -o \
        -name 'output.mp4' \
        -o \
        -name 'render.mp4' \
        -o \
        -name 'video_base.mp4' \
    \) \
    2>/dev/null
)

echo "GENERIC_RENDER_ARTIFACT_COUNT=$GENERIC_COUNT"

if [ "$GENERIC_COUNT" -gt 0 ]; then
    warn "GENERIC_RENDER_ARTIFACTS_FOUND"
else
    pass "NO_GENERIC_RENDER_ARTIFACTS"
fi

echo


echo "======================================================================"
echo " 22. FRESH RENDER GUARD SAFETY"
echo "======================================================================"

if [ -f fresh_render_guard_v1.py ]; then

    TEST_ID="AUDIT_GUARD_$$"

    mkdir -p \
    "temp/$TEST_ID" \
    videos

    printf 'ASS_SAFE\n' \
    > "videos/short_${TEST_ID}.ass"

    printf 'AUDIO_SAFE\n' \
    > "temp/${TEST_ID}/test.mp3"

    printf 'TEMP_VIDEO\n' \
    > "temp/${TEST_ID}/video_sem_audio.mp4"

    printf 'FINAL_VIDEO\n' \
    > "videos/short_v6_${TEST_ID}.mp4"

    SHORT_ID="$TEST_ID" \
    python fresh_render_guard_v1.py \
    >/dev/null \
    2>&1

    GUARD_OK=1

    if [ ! -f "videos/short_${TEST_ID}.ass" ]; then
        echo "GUARD_REMOVED_ASS=YES"
        GUARD_OK=0
    fi

    if [ ! -f "temp/${TEST_ID}/test.mp3" ]; then
        echo "GUARD_REMOVED_AUDIO=YES"
        GUARD_OK=0
    fi

    if [ -f "temp/${TEST_ID}/video_sem_audio.mp4" ]; then
        echo "GUARD_FAILED_TO_REMOVE_TEMP_VIDEO=YES"
        GUARD_OK=0
    fi

    if [ -f "videos/short_v6_${TEST_ID}.mp4" ]; then
        echo "GUARD_FAILED_TO_REMOVE_FINAL=YES"
        GUARD_OK=0
    fi

    rm -rf "temp/$TEST_ID"
    rm -f \
    "videos/short_${TEST_ID}.ass" \
    "videos/short_v6_${TEST_ID}.mp4"

    if [ "$GUARD_OK" -eq 1 ]; then
        pass "FRESH_RENDER_GUARD_SAFETY"
    else
        fail "FRESH_RENDER_GUARD_SAFETY"
    fi

else

    warn "FRESH_RENDER_GUARD_NOT_FOUND"

fi

echo


echo "======================================================================"
echo " 23. RECENT PRODUCTION ERRORS"
echo "======================================================================"

if [ -d logs/producao ]; then

    grep -RniE \
    'Traceback|NameError|TypeError|AssertionError|SyntaxError|ERROR|ERRO:|FAIL' \
    logs/producao \
    2>/dev/null \
    | tail -n 150 \
    || true

else

    warn "PRODUCTION_LOG_DIRECTORY_MISSING"

fi

echo


echo "======================================================================"
echo " 24. RECENT VSE / COMMIT TELEMETRY"
echo "======================================================================"

if [ -d logs/producao ]; then

    grep -RhiE \
    'VSE4|VSE3|SCENE_COMMIT_LOCK|MUST COVERAGE|ESCOLHIDO:' \
    logs/producao \
    2>/dev/null \
    | tail -n 200 \
    || true

fi

echo


echo "======================================================================"
echo " 25. MIDIA PROVIDER CONFIG PRESENCE"
echo "======================================================================"

grep -nEi \
'PEXELS|PIXABAY|COVERR|WIKIMEDIA|API_KEY|TOKEN' \
midia.py \
2>/dev/null \
| sed -E \
's/(API_KEY|TOKEN|KEY)[[:space:]]*=[[:space:]]*[^[:space:]]+/\1=<REDACTED>/Ig' \
| head -n 150

echo


echo "======================================================================"
echo " 26. PROJECT DISK USAGE"
echo "======================================================================"

du -sh . 2>/dev/null

for D in \
imagens \
audios \
videos \
temp \
logs \
backups
do

    [ -d "$D" ] && du -sh "$D" 2>/dev/null

done

echo


echo "======================================================================"
echo " 27. FINAL CORE RE-COMPILE"
echo "======================================================================"

python -m py_compile \
midia.py \
video.py \
v6.py \
legenda_dinamica.py \
visual_selection_engine_v4.py \
2>/dev/null

FINAL_COMPILE=$?

bash -n \
gerar_short.sh \
2>/dev/null

FINAL_SHELL=$?

echo "FINAL_CORE_COMPILE=$FINAL_COMPILE"
echo "FINAL_SHELL_SYNTAX=$FINAL_SHELL"

if [ "$FINAL_COMPILE" -eq 0 ]; then
    pass "FINAL_CORE_COMPILE"
else
    fail "FINAL_CORE_COMPILE"
fi

if [ "$FINAL_SHELL" -eq 0 ]; then
    pass "FINAL_SHELL_SYNTAX"
else
    fail "FINAL_SHELL_SYNTAX"
fi

echo


echo "======================================================================"
echo " GENERAL AUDIT SUMMARY"
echo "======================================================================"

echo "PASS_COUNT=$PASS_COUNT"
echo "WARN_COUNT=$WARN_COUNT"
echo "FAIL_COUNT=$FAIL_COUNT"

if [ "$FAIL_COUNT" -eq 0 ]; then

    if [ "$WARN_COUNT" -eq 0 ]; then
        echo "GENERAL_AUDIT_STATUS=PASS"
    else
        echo "GENERAL_AUDIT_STATUS=PASS_WITH_WARNINGS"
    fi

else

    echo "GENERAL_AUDIT_STATUS=FAIL"

fi

echo
echo "NETWORK_EXECUTED=NO"
echo "MEDIA_DOWNLOADED=NO"
echo "VIDEO_RENDERED=NO"
echo "PIPELINE_EXECUTED=NO"
echo "TERMUX_CONTINUA_ABERTO=SIM"
echo "======================================================================"

} 2>&1 | tee "$REPORT"

echo
echo "======================================================================"
echo " AUDIT SAVED"
echo "======================================================================"
echo "REPORT=$REPORT"
echo
echo "Para mostrar apenas problemas:"
echo
echo "grep -E '^(FAIL|WARN)|GENERAL_AUDIT_STATUS=|FAIL_COUNT=|WARN_COUNT=' \"$REPORT\""
echo
echo "TERMUX_CONTINUA_ABERTO=SIM"
