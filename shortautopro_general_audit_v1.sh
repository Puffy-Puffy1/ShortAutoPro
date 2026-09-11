#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

ROOT="$HOME/ShortAutoPro"

cd "$ROOT" || {
    echo "ERRO: ShortAutoPro não encontrado."
    return 1 2>/dev/null || true
}

STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p \
temp \
logs/producao

REPORT="temp/SHORTAUTOPRO_GENERAL_AUDIT_${STAMP}.txt"

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


section() {

    echo
    echo "======================================================================"
    echo " $*"
    echo "======================================================================"
}


exec > >(tee "$REPORT") 2>&1


echo "======================================================================"
echo " SHORTAUTOPRO GENERAL AUDIT V1"
echo "======================================================================"
echo "DATE=$(date)"
echo "ROOT=$ROOT"
echo "REPORT=$REPORT"
echo "MODE=READ_ONLY_AUDIT"
echo


# ======================================================================
# 1. ENVIRONMENT
# ======================================================================

section "1. ENVIRONMENT"

echo "PWD=$(pwd)"
echo "HOME=$HOME"

for CMD in \
python \
bash \
ffmpeg \
ffprobe \
sha256sum \
find \
grep \
sed \
awk
do

    if command -v "$CMD" >/dev/null 2>&1; then

        pass "COMMAND_$CMD"

        command -v "$CMD"

    else

        fail "COMMAND_MISSING_$CMD"

    fi

done


echo
python --version 2>&1
ffmpeg -version 2>/dev/null | head -n 1
ffprobe -version 2>/dev/null | head -n 1


# ======================================================================
# 2. STORAGE
# ======================================================================

section "2. STORAGE"

df -h "$HOME" 2>/dev/null

if [ -d "$HOME/storage/shared" ]; then

    pass "TERMUX_STORAGE_READY"

    df -h "$HOME/storage/shared" 2>/dev/null

else

    warn "TERMUX_STORAGE_SHARED_NOT_FOUND"

fi


# ======================================================================
# 3. CORE FILES
# ======================================================================

section "3. CORE FILES"

CORE_FILES="
gerar_short.sh
midia.py
video.py
v6.py
legenda_dinamica.py
shortautopro_full_power_run.sh
media_provenance_capture_v1.py
media_diversity_guard_v1.py
visual_selection_engine_v4.py
"

for F in $CORE_FILES
do

    if [ -s "$F" ]; then

        pass "CORE_FILE=$F"

        sha256sum "$F"

    else

        fail "CORE_FILE_MISSING_OR_EMPTY=$F"

    fi

done


# ======================================================================
# 4. ALL ROOT PYTHON SYNTAX
# ======================================================================

section "4. PYTHON SYNTAX - ALL ROOT MODULES"

python - <<'PY'
from pathlib import Path

files = sorted(
    Path(".").glob("*.py")
)

failed = []

print(
    f"PYTHON_FILES={len(files)}"
)

for path in files:

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="strict",
        )

        compile(
            source,
            str(path),
            "exec",
        )

        print(
            f"PY_COMPILE=PASS | {path}"
        )

    except Exception as exc:

        failed.append(
            str(path)
        )

        print(
            f"PY_COMPILE=FAIL | "
            f"{path} | "
            f"{type(exc).__name__}: {exc}"
        )


print(
    "PYTHON_FAILED_COUNT="
    + str(
        len(failed)
    )
)

if failed:

    print(
        "PYTHON_FAILED_FILES="
        +
        ",".join(failed)
    )
PY

PY_FAILED="$(
python - <<'PY'
from pathlib import Path

bad = 0

for p in Path(".").glob("*.py"):

    try:
        compile(
            p.read_text(
                encoding="utf-8"
            ),
            str(p),
            "exec",
        )

    except Exception:
        bad += 1

print(bad)
PY
)"

if [ "$PY_FAILED" -eq 0 ]; then
    pass "ALL_ROOT_PYTHON_COMPILE"
else
    fail "ROOT_PYTHON_COMPILE_FAILURES=$PY_FAILED"
fi


# ======================================================================
# 5. SHELL SYNTAX
# ======================================================================

section "5. SHELL SYNTAX"

SHELL_BAD=0

for F in *.sh
do

    [ -f "$F" ] || continue

    bash -n "$F" 2>/dev/null

    STATUS=$?

    if [ "$STATUS" -eq 0 ]; then

        echo "SHELL_SYNTAX=PASS | $F"

    else

        echo "SHELL_SYNTAX=FAIL | $F"

        SHELL_BAD=$((SHELL_BAD + 1))

    fi

done

if [ "$SHELL_BAD" -eq 0 ]; then
    pass "ALL_ROOT_SHELL_SYNTAX"
else
    fail "SHELL_SYNTAX_FAILURES=$SHELL_BAD"
fi


# ======================================================================
# 6. DUPLICATE PYTHON DEFINITIONS
# ======================================================================

section "6. DUPLICATE TOP-LEVEL PYTHON DEFINITIONS"

python - <<'PY'
from pathlib import Path
import ast
from collections import Counter

total = 0

for path in sorted(
    Path(".").glob("*.py")
):

    try:
        tree = ast.parse(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        continue


    names = [
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        )
    ]


    dup = {
        name: count
        for name, count in Counter(
            names
        ).items()
        if count > 1
    }


    if dup:

        total += len(dup)

        print(
            f"DUPLICATE_DEFINITION | "
            f"{path} | {dup}"
        )


print(
    f"DUPLICATE_DEFINITION_COUNT={total}"
)
PY


# ======================================================================
# 7. VSE4 STATIC GLOBAL AUDIT
# ======================================================================

section "7. VSE4 STATIC GLOBAL AUDIT"

if [ -s visual_selection_engine_v4.py ]; then

python - <<'PY'
from pathlib import Path
import symtable
import builtins

path = Path(
    "visual_selection_engine_v4.py"
)

src = path.read_text(
    encoding="utf-8"
)

table = symtable.symtable(
    src,
    str(path),
    "exec",
)

defined = set()

for symbol in table.get_symbols():

    if (
        symbol.is_assigned()
        or
        symbol.is_imported()
        or
        symbol.is_namespace()
    ):

        defined.add(
            symbol.get_name()
        )


builtin_names = set(
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

            if name in builtin_names:
                continue

            unresolved.add(
                name
            )

        walk(child)


walk(table)


if unresolved:

    print(
        "VSE4_UNRESOLVED_GLOBALS="
        +
        ",".join(
            sorted(unresolved)
        )
    )

else:

    print(
        "VSE4_UNRESOLVED_GLOBALS=NONE"
    )
PY

fi


# ======================================================================
# 8. VSE4 RUNTIME SELF TEST
# ======================================================================

section "8. VSE4 RUNTIME SELF TEST"

if [ -s visual_selection_engine_v4.py ]; then

    export SAP_NO_NETWORK=1
    export SAP_NO_RENDER=1

    VSE_LOG="temp/general_audit_vse4_${STAMP}.log"

    if command -v timeout >/dev/null 2>&1; then

        timeout 60 \
        python visual_selection_engine_v4.py \
        >"$VSE_LOG" 2>&1

    else

        python visual_selection_engine_v4.py \
        >"$VSE_LOG" 2>&1

    fi

    VSE_STATUS=$?

    cat "$VSE_LOG"

    echo
    echo "VSE4_SELF_TEST_STATUS=$VSE_STATUS"

    if [ "$VSE_STATUS" -eq 0 ]; then

        pass "VSE4_RUNTIME_SELF_TEST"

    else

        fail "VSE4_RUNTIME_SELF_TEST"

    fi

else

    warn "VSE4_NOT_INSTALLED"

fi


# ======================================================================
# 9. PROVIDER ACQUISITION STATIC TEST
# ======================================================================

section "9. PROVIDER ACQUISITION"

python - <<'PY'
from pathlib import Path
import ast

path = Path(
    "midia.py"
)

if not path.exists():

    print(
        "PROVIDER_AUDIT=FAIL_NO_MIDIA"
    )

    raise SystemExit


tree = ast.parse(
    path.read_text(
        encoding="utf-8"
    )
)


required = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
}


defined = {
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


for name in sorted(required):

    print(
        f"PROVIDER_FUNCTION_{name}="
        f"{'PASS' if name in defined else 'FAIL'}"
    )


target = None

for node in tree.body:

    if (
        isinstance(
            node,
            ast.FunctionDef,
        )
        and
        node.name == "buscar_todos_candidatos"
    ):

        target = node
        break


expected_calls = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}


calls = set()

if target:

    for node in ast.walk(target):

        if isinstance(
            node,
            ast.Call,
        ):

            if isinstance(
                node.func,
                ast.Name,
            ):

                calls.add(
                    node.func.id
                )


for name in sorted(expected_calls):

    print(
        f"PROVIDER_CALL_{name}="
        f"{'PASS' if name in calls else 'FAIL'}"
    )


missing = (
    required - defined
)

call_missing = (
    expected_calls - calls
)


if not missing and not call_missing:

    print(
        "PROVIDER_ACQUISITION_STATIC=PASS"
    )

else:

    print(
        "PROVIDER_ACQUISITION_STATIC=FAIL"
    )

    print(
        "MISSING_FUNCTIONS="
        +
        ",".join(
            sorted(missing)
        )
    )

    print(
        "MISSING_CALLS="
        +
        ",".join(
            sorted(call_missing)
        )
    )
PY


# ======================================================================
# 10. API CONFIG - NAMES ONLY
# ======================================================================

section "10. PROVIDER CONFIG PRESENCE"

python - <<'PY'
from pathlib import Path
import re

patterns = {
    "PEXELS":
        re.compile(
            r"\bPEXELS[A-Z0-9_]*\b"
        ),

    "PIXABAY":
        re.compile(
            r"\bPIXABAY[A-Z0-9_]*\b"
        ),

    "COVERR":
        re.compile(
            r"\bCOVERR[A-Z0-9_]*\b"
        ),
}


for provider, pattern in patterns.items():

    names = set()

    for path in Path(".").glob("*.py"):

        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        for name in pattern.findall(
            text
        ):

            names.add(name)


    print(
        provider
        + "_CONFIG_NAMES="
        + (
            ",".join(
                sorted(names)
            )
            if names
            else
            "NONE"
        )
    )


print(
    "SECRET_VALUES_PRINTED=NO"
)
PY


# ======================================================================
# 11. CURRENT SHORT DETECTION
# ======================================================================

section "11. CURRENT SHORT DETECTION"

SID="${SHORT_ID:-}"

if [ -z "$SID" ]; then

    LATEST_MEDIA_DIR="$(
        ls -1dt \
        imagens/short_* \
        2>/dev/null |
        head -n 1
    )"

    if [ -n "$LATEST_MEDIA_DIR" ]; then

        SID="$(
            basename "$LATEST_MEDIA_DIR" |
            sed 's/^short_//'
        )"

    fi

fi


echo "DETECTED_SHORT_ID=$SID"


if [ -n "$SID" ]; then

    pass "SHORT_ID_DETECTED=$SID"

else

    warn "SHORT_ID_NOT_DETECTED"

fi


# ======================================================================
# 12. MEDIA SCENE STRUCTURE
# ======================================================================

section "12. MEDIA SCENE STRUCTURE"

if [ -n "$SID" ]; then

    MEDIA_DIR="imagens/short_$SID"

    echo "MEDIA_DIR=$MEDIA_DIR"

    MEDIA_TOTAL=0
    INVALID_SCENES=0

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

        MEDIA_TOTAL=$(
            (
                MEDIA_TOTAL
                +
                COUNT
            )
        )

        echo "SCENE_${N}_COUNT=$COUNT"

        find "$MEDIA_DIR" \
        -maxdepth 1 \
        -type f \
        -name "scene_${N}.*" \
        -print \
        2>/dev/null

        if [ "$COUNT" -ne 1 ]; then

            INVALID_SCENES=$(
                (
                    INVALID_SCENES
                    +
                    1
                )
            )

        fi

    done


    echo "MEDIA_TOTAL=$MEDIA_TOTAL"
    echo "INVALID_SCENES=$INVALID_SCENES"


    if \
    [ "$MEDIA_TOTAL" -eq 12 ] &&
    [ "$INVALID_SCENES" -eq 0 ]
    then

        pass "MEDIA_STRUCTURE_12_OF_12"

    else

        fail \
        "MEDIA_STRUCTURE total=$MEDIA_TOTAL invalid=$INVALID_SCENES"

    fi

else

    warn "MEDIA_STRUCTURE_SKIPPED_NO_SHORT_ID"

fi


# ======================================================================
# 13. MEDIA HASH / DUPLICATE TEST
# ======================================================================

section "13. MEDIA DUPLICATE HASH TEST"

if [ -n "$SID" ] && [ -d "imagens/short_$SID" ]; then

python - "$SID" <<'PY'
from pathlib import Path
import hashlib
import sys
from collections import defaultdict

sid = sys.argv[1]

root = (
    Path("imagens")
    /
    f"short_{sid}"
)


def sha(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(chunk)

    return h.hexdigest()


groups = defaultdict(list)

files = sorted(
    root.glob("scene_*.*")
)


for path in files:

    digest = sha(path)

    groups[
        digest
    ].append(
        path.name
    )

    print(
        f"MEDIA_HASH={digest} | "
        f"{path.name} | "
        f"{path.stat().st_size}"
    )


duplicates = {
    digest: names
    for digest, names in groups.items()
    if len(names) > 1
}


if duplicates:

    print(
        "DUPLICATE_MEDIA_SHA=YES"
    )

    for digest, names in duplicates.items():

        print(
            f"DUPLICATE_SHA={digest} "
            f"FILES={','.join(names)}"
        )

else:

    print(
        "DUPLICATE_MEDIA_SHA=NO"
    )
PY

fi


# ======================================================================
# 14. MEDIA TECHNICAL VALIDITY
# ======================================================================

section "14. MEDIA TECHNICAL VALIDITY"

if [ -n "$SID" ] && [ -d "imagens/short_$SID" ]; then

    BAD_MEDIA=0

    for F in imagens/short_"$SID"/scene_*.*
    do

        [ -f "$F" ] || continue

        SIZE="$(
            stat -c%s "$F" \
            2>/dev/null
        )"

        echo
        echo "MEDIA=$F"
        echo "BYTES=$SIZE"

        if [ -z "$SIZE" ] || [ "$SIZE" -lt 4096 ]; then

            echo "MEDIA_SIZE=FAIL"

            BAD_MEDIA=$(
                (
                    BAD_MEDIA
                    +
                    1
                )
            )

            continue

        else

            echo "MEDIA_SIZE=PASS"

        fi


        case "$F" in

            *.mp4|*.mov|*.webm|*.mkv)

                ffprobe \
                -v error \
                -show_entries \
                stream=codec_name,width,height,duration \
                -of \
                default=noprint_wrappers=1 \
                "$F"

                STATUS=$?

                if [ "$STATUS" -eq 0 ]; then

                    echo "MEDIA_PROBE=PASS"

                else

                    echo "MEDIA_PROBE=FAIL"

                    BAD_MEDIA=$(
                        (
                            BAD_MEDIA
                            +
                            1
                        )
                    )

                fi
            ;;

            *.jpg|*.jpeg|*.png|*.webp)

                python - "$F" <<'PY'
from pathlib import Path
import sys

p = Path(
    sys.argv[1]
)

data = p.read_bytes()[:16]

ok = (
    data.startswith(b"\xff\xd8\xff")
    or
    data.startswith(b"\x89PNG\r\n\x1a\n")
    or
    (
        data.startswith(b"RIFF")
        and
        b"WEBP" in data
    )
)

print(
    "IMAGE_SIGNATURE="
    +
    (
        "PASS"
        if ok
        else
        "FAIL"
    )
)
PY
            ;;

        esac

    done


    echo
    echo "BAD_MEDIA_COUNT=$BAD_MEDIA"

    if [ "$BAD_MEDIA" -eq 0 ]; then

        pass "MEDIA_TECHNICAL_VALIDITY"

    else

        fail "BAD_MEDIA_COUNT=$BAD_MEDIA"

    fi

fi


# ======================================================================
# 15. RENDER INPUTS / OUTPUTS
# ======================================================================

section "15. RENDER PIPELINE STATE"

if [ -n "$SID" ]; then

    AUDIO="audios/short_${SID}.mp3"

    ASS="videos/short_${SID}.ass"

    VIDEO_BASE="temp/${SID}/video_sem_audio.mp4"

    FINAL="videos/short_v6_${SID}.mp4"


    for ITEM in \
    "$AUDIO" \
    "$ASS" \
    "$VIDEO_BASE" \
    "$FINAL"
    do

        if [ -s "$ITEM" ]; then

            echo \
            "FILE=PASS | $(stat -c%s "$ITEM") | $ITEM"

        else

            echo \
            "FILE=MISSING | $ITEM"

        fi

    done


    if [ -s "$FINAL" ]; then

        echo
        echo "FINAL_SHA256="

        sha256sum "$FINAL"


        echo
        echo "FINAL_FFPROBE="

        ffprobe \
        -v error \
        -show_entries \
        stream=codec_name,codec_type,width,height,r_frame_rate \
        -show_entries \
        format=duration,size,bit_rate \
        -of \
        default=noprint_wrappers=1 \
        "$FINAL"

    fi

fi


# ======================================================================
# 16. STALE RENDER TEST
# ======================================================================

section "16. STALE RENDER / CACHE TEST"

if [ -n "$SID" ]; then

    FINAL="videos/short_v6_${SID}.mp4"

    MEDIA_DIR="imagens/short_${SID}"


    if [ -s "$FINAL" ] && [ -d "$MEDIA_DIR" ]; then

        FINAL_TIME="$(
            stat -c%Y "$FINAL"
        )"


        NEWEST_MEDIA_TIME="$(
            find "$MEDIA_DIR" \
            -maxdepth 1 \
            -type f \
            -name 'scene_*.*' \
            -printf '%T@\n' \
            2>/dev/null |
            sort -n |
            tail -n 1 |
            cut -d. -f1
        )"


        echo "FINAL_MTIME=$FINAL_TIME"
        echo "NEWEST_MEDIA_MTIME=$NEWEST_MEDIA_TIME"


        if \
        [ -n "$NEWEST_MEDIA_TIME" ] &&
        [ "$FINAL_TIME" -ge "$NEWEST_MEDIA_TIME" ]
        then

            pass "FINAL_NOT_OLDER_THAN_MEDIA"

        else

            warn "FINAL_MAY_BE_STALE"

        fi

    else

        warn "STALE_TEST_SKIPPED"

    fi

fi


# ======================================================================
# 17. PROVENANCE
# ======================================================================

section "17. PROVENANCE"

if [ -n "$SID" ]; then

    echo "===== PROVENANCE REFERENCES ====="

    find manifests \
    -maxdepth 3 \
    -type f \
    -name "*${SID}*" \
    -printf '%s | %p\n' \
    2>/dev/null |
    head -n 100


    echo
    echo "===== CREDITS REFERENCES ====="

    find credits \
    -maxdepth 3 \
    -type f \
    -name "*${SID}*" \
    -printf '%s | %p\n' \
    2>/dev/null |
    head -n 100

fi


# ======================================================================
# 18. GALLERY EXPORT MODULE
# ======================================================================

section "18. GALLERY EXPORT MODULE"

RUNNER="shortautopro_full_power_run.sh"

if [ -s "$RUNNER" ]; then

    bash -n "$RUNNER"

    RUNNER_STATUS=$?

    echo "RUNNER_SYNTAX=$RUNNER_STATUS"


    if grep -q \
    'SHORTAUTOPRO GALLERY EXPORT V1' \
    "$RUNNER"
    then

        pass "GALLERY_MODULE_PRESENT"

    else

        fail "GALLERY_MODULE_MISSING"

    fi


    if grep -q \
    'GALLERY_EXPORT=PASS' \
    "$RUNNER"
    then

        pass "GALLERY_SUCCESS_GATE_PRESENT"

    else

        fail "GALLERY_SUCCESS_GATE_MISSING"

    fi


    if grep -q \
    'SOURCE_HASH' \
    "$RUNNER" &&
       grep -q \
    'DEST_HASH' \
    "$RUNNER"
    then

        pass "GALLERY_HASH_INTEGRITY_PRESENT"

    else

        fail "GALLERY_HASH_INTEGRITY_MISSING"

    fi


    if grep -q \
    'termux-media-scan' \
    "$RUNNER"
    then

        pass "GALLERY_MEDIA_SCAN_PRESENT"

    else

        warn "GALLERY_MEDIA_SCAN_NOT_FOUND"

    fi


    GALLERY_LINE="$(
        grep -n \
        'SHORTAUTOPRO GALLERY EXPORT V1$' \
        "$RUNNER" |
        head -n 1 |
        cut -d: -f1
    )"


    if [ -n "$GALLERY_LINE" ]; then

        EARLY_EXITS="$(
            sed -n \
            "1,$((GALLERY_LINE - 1))p" \
            "$RUNNER" |
            grep -Ec \
            '^[[:space:]]*exit([[:space:]]|$)' \
            2>/dev/null
        )"

        echo \
        "RUNNER_TOP_LEVEL_EXIT_BEFORE_GALLERY=$EARLY_EXITS"

        if [ "$EARLY_EXITS" -gt 0 ]; then

            warn \
            "RUNNER_HAS_EXIT_BEFORE_GALLERY_REVIEW_CONTROL_FLOW"

        fi

    fi

else

    fail "FULL_POWER_RUNNER_MISSING"

fi


# ======================================================================
# 19. WHISPER / SUBTITLE ENGINE
# ======================================================================

section "19. WHISPER / SUBTITLE ENGINE"

WHISPER="$HOME/whisper.cpp/build/bin/whisper-cli"

MODEL="$HOME/whisper.cpp/models/ggml-base.bin"


if [ -x "$WHISPER" ]; then
    pass "WHISPER_CLI"
else
    fail "WHISPER_CLI_MISSING"
fi


if [ -s "$MODEL" ]; then
    pass "WHISPER_MODEL"
    ls -lh "$MODEL"
else
    fail "WHISPER_MODEL_MISSING"
fi


if [ -s legenda_dinamica.py ]; then
    pass "LEGENDA_DINAMICA"
else
    fail "LEGENDA_DINAMICA_MISSING"
fi


# ======================================================================
# 20. RECENT ERROR LOG SCAN
# ======================================================================

section "20. RECENT ERROR / TRACEBACK SCAN"

RECENT_LIST="temp/general_audit_recent_logs_${STAMP}.txt"

find logs/producao \
-type f \
-printf '%T@ %p\n' \
2>/dev/null |
sort -nr |
head -n 30 |
cut -d' ' -f2- \
>"$RECENT_LIST"


ERROR_HITS=0


while IFS= read -r LOG
do

    [ -f "$LOG" ] || continue


    COUNT="$(
        grep -Eic \
        'Traceback|AssertionError|NameError|TypeError|SyntaxError|FileNotFoundError|No such file|ERRO:|ERROR:|FAIL' \
        "$LOG" \
        2>/dev/null
    )"


    if [ "$COUNT" -gt 0 ]; then

        ERROR_HITS=$(
            (
                ERROR_HITS
                +
                COUNT
            )
        )

        echo
        echo "LOG_WITH_ERRORS=$LOG"
        echo "ERROR_MATCHES=$COUNT"

        grep -Ein \
        'Traceback|AssertionError|NameError|TypeError|SyntaxError|FileNotFoundError|No such file|ERRO:|ERROR:|FAIL' \
        "$LOG" \
        2>/dev/null |
        tail -n 15

    fi

done < "$RECENT_LIST"


echo
echo "RECENT_LOG_ERROR_MATCHES=$ERROR_HITS"

if [ "$ERROR_HITS" -eq 0 ]; then

    pass "RECENT_LOG_SCAN_CLEAN"

else

    warn \
    "RECENT_LOGS_CONTAIN_ERRORS count=$ERROR_HITS"

fi


# ======================================================================
# 21. SUSPICIOUS ZERO-BYTE FILES
# ======================================================================

section "21. ZERO-BYTE PROJECT FILES"

ZERO_COUNT="$(
    find . \
    -maxdepth 2 \
    -type f \
    -size 0 \
    ! -path './backups/*' \
    ! -path './temp/*' \
    2>/dev/null |
    wc -l
)"


find . \
-maxdepth 2 \
-type f \
-size 0 \
! -path './backups/*' \
! -path './temp/*' \
-print \
2>/dev/null


echo "ZERO_BYTE_FILE_COUNT=$ZERO_COUNT"


if [ "$ZERO_COUNT" -eq 0 ]; then

    pass "NO_ZERO_BYTE_PROJECT_FILES"

else

    warn "ZERO_BYTE_PROJECT_FILES=$ZERO_COUNT"

fi


# ======================================================================
# 22. CORE HASH SNAPSHOT
# ======================================================================

section "22. CORE HASH SNAPSHOT"

HASH_FILE="temp/general_audit_core_hashes_${STAMP}.sha256"

for F in \
midia.py \
video.py \
v6.py \
gerar_short.sh \
legenda_dinamica.py \
visual_selection_engine_v4.py \
shortautopro_full_power_run.sh
do

    if [ -f "$F" ]; then
        sha256sum "$F"
    fi

done |
tee "$HASH_FILE"


echo "HASH_SNAPSHOT=$HASH_FILE"


# ======================================================================
# 23. GENERAL SUMMARY
# ======================================================================

section "23. GENERAL SUMMARY"

echo "SHORT_ID=$SID"

echo
echo "PASS_COUNT=$PASS_COUNT"
echo "WARN_COUNT=$WARN_COUNT"
echo "FAIL_COUNT=$FAIL_COUNT"


if [ "$FAIL_COUNT" -eq 0 ]; then

    if [ "$WARN_COUNT" -eq 0 ]; then

        echo
        echo "GENERAL_STATUS=PASS"

    else

        echo
        echo "GENERAL_STATUS=PASS_WITH_WARNINGS"

    fi

else

    echo
    echo "GENERAL_STATUS=FAIL"

fi


echo
echo "AUDIT_REPORT=$REPORT"

echo
echo "NETWORK_EXECUTED=NO"
echo "MEDIA_DOWNLOADED=NO"
echo "MIDIA_PIPELINE_EXECUTED=NO"
echo "VIDEO_RENDERED=NO"
echo "CORE_FILES_MODIFIED=NO"

echo
echo "GENERAL_AUDIT_COMPLETE=YES"
echo "TERMUX_CONTINUA_ABERTO=SIM"

