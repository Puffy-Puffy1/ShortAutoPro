#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

SHORT_ID="${SHORT_ID:-2026-09-02_2358}"
export SHORT_ID

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="temp/GENERAL_AUDIT_V2_${SHORT_ID}_${STAMP}.txt"

mkdir -p temp logs/producao

PASS=0
WARN=0
FAIL=0

ok() {
    echo "AUDIT_PASS | $*"
    PASS=$((PASS + 1))
}

warn() {
    echo "AUDIT_WARN | $*"
    WARN=$((WARN + 1))
}

bad() {
    echo "AUDIT_FAIL | $*"
    FAIL=$((FAIL + 1))
}

section() {
    echo
    echo "======================================================================"
    echo " $1"
    echo "======================================================================"
}

{
section "SHORTAUTOPRO GENERAL AUDIT V2"

echo "DATE=$(date)"
echo "PWD=$(pwd)"
echo "SHORT_ID=$SHORT_ID"
echo "PYTHON=$(python --version 2>&1)"
echo "FFMPEG=$(ffmpeg -version 2>/dev/null | head -n 1)"
echo


section "1. DISK / ENVIRONMENT"

df -h . 2>/dev/null

FREE_KB="$(
    df -Pk . 2>/dev/null |
    awk 'NR==2 {print $4}'
)"

if [ -n "$FREE_KB" ] && [ "$FREE_KB" -gt 500000 ]; then
    ok "DISK_FREE_GT_500MB"
else
    warn "LOW_OR_UNKNOWN_DISK_SPACE free_kb=${FREE_KB:-unknown}"
fi

command -v python >/dev/null 2>&1 \
&& ok "PYTHON_FOUND" \
|| bad "PYTHON_MISSING"

command -v ffmpeg >/dev/null 2>&1 \
&& ok "FFMPEG_FOUND" \
|| bad "FFMPEG_MISSING"

command -v ffprobe >/dev/null 2>&1 \
&& ok "FFPROBE_FOUND" \
|| bad "FFPROBE_MISSING"


section "2. CORE FILE PRESENCE"

CORE_FILES=(
    gerar_short.sh
    midia.py
    video.py
    v6.py
    legenda_dinamica.py
    media_provenance_capture_v1.py
    media_diversity_guard_v1.py
    visual_selection_engine_v2.py
    visual_selection_final_gate_v3.py
    visual_selection_engine_v4.py
    visual_scene_commit_lock_v1.py
    visual_must_rescue_v1.py
    fresh_render_guard_v1.py
    render_input_fingerprint_v1.py
)

for F in "${CORE_FILES[@]}"
do
    if [ -s "$F" ]; then
        echo "CORE_FILE=FOUND | $(stat -c%s "$F") | $F"
    else
        bad "CORE_FILE_MISSING_OR_EMPTY $F"
    fi
done


section "3. CORE HASHES"

for F in \
midia.py \
video.py \
v6.py \
gerar_short.sh \
visual_selection_engine_v4.py \
media_diversity_guard_v1.py \
fresh_render_guard_v1.py
do
    [ -f "$F" ] && sha256sum "$F"
done


section "4. ALL TOP-LEVEL PYTHON COMPILE"

PY_TOTAL=0
PY_BAD=0

for F in ./*.py
do
    [ -f "$F" ] || continue

    PY_TOTAL=$((PY_TOTAL + 1))

    python -m py_compile "$F" 2>/dev/null

    S=$?

    if [ "$S" -ne 0 ]; then
        echo "PY_COMPILE=FAIL | $F"
        PY_BAD=$((PY_BAD + 1))
    fi
done

echo "PYTHON_FILES_TESTED=$PY_TOTAL"
echo "PYTHON_COMPILE_FAILURES=$PY_BAD"

if [ "$PY_BAD" -eq 0 ]; then
    ok "ALL_TOP_LEVEL_PYTHON_COMPILES"
else
    bad "PYTHON_COMPILE_FAILURES=$PY_BAD"
fi


section "5. SHELL SYNTAX"

SH_TOTAL=0
SH_BAD=0

for F in ./*.sh
do
    [ -f "$F" ] || continue

    SH_TOTAL=$((SH_TOTAL + 1))

    bash -n "$F" 2>/dev/null

    S=$?

    if [ "$S" -ne 0 ]; then
        echo "SH_SYNTAX=FAIL | $F"
        SH_BAD=$((SH_BAD + 1))
    fi
done

echo "SHELL_FILES_TESTED=$SH_TOTAL"
echo "SHELL_FAILURES=$SH_BAD"

if [ "$SH_BAD" -eq 0 ]; then
    ok "ALL_SHELL_SYNTAX"
else
    bad "SHELL_SYNTAX_FAILURES=$SH_BAD"
fi


section "6. DUPLICATE TOP-LEVEL PYTHON DEFINITIONS"

python - <<'PY'
from pathlib import Path
import ast
from collections import Counter

files = [
    "midia.py",
    "video.py",
    "v6.py",
    "visual_selection_engine_v4.py",
]

total_bad = 0

for name in files:
    p = Path(name)

    if not p.is_file():
        continue

    try:
        tree = ast.parse(
            p.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except Exception as exc:
        print(
            f"DUPDEF_PARSE_FAIL={name} | "
            f"{type(exc).__name__}: {exc}"
        )
        total_bad += 1
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

    duplicates = {
        key: count
        for key, count in Counter(names).items()
        if count > 1
    }

    if duplicates:
        print(
            f"DUPLICATE_DEFINITIONS={name} | "
            f"{duplicates}"
        )
        total_bad += len(duplicates)
    else:
        print(
            f"DUPLICATE_DEFINITIONS={name} | NONE"
        )

print(
    f"DUPLICATE_DEFINITION_GROUPS={total_bad}"
)
PY


section "7. VSE4 TRUE GLOBAL AUDIT"

python - <<'PY'
from pathlib import Path
import symtable
import builtins

p = Path("visual_selection_engine_v4.py")

if not p.is_file():
    print("VSE4_GLOBAL_AUDIT=MISSING")
    raise SystemExit(0)

src = p.read_text(
    encoding="utf-8",
    errors="replace",
)

try:
    table = symtable.symtable(
        src,
        str(p),
        "exec",
    )
except Exception as exc:
    print(
        "VSE4_GLOBAL_AUDIT=PARSE_FAIL",
        repr(exc),
    )
    raise SystemExit(0)

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

            unresolved.add(name)

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
    print("VSE4_GLOBAL_AUDIT=FAIL")
else:
    print("VSE4_UNRESOLVED_GLOBALS=NONE")
    print("VSE4_GLOBAL_AUDIT=PASS")
PY


section "8. VSE4 SELF TEST"

if [ -s visual_selection_engine_v4.py ]; then

    python visual_selection_engine_v4.py \
        > "temp/general_audit_vse4_${SHORT_ID}.log" \
        2>&1

    VSE4_TEST=$?

    echo "VSE4_SELF_TEST=$VSE4_TEST"

    if [ "$VSE4_TEST" -eq 0 ]; then
        ok "VSE4_SELF_TEST"
    else
        bad "VSE4_SELF_TEST=$VSE4_TEST"

        echo
        echo "===== VSE4 FAILURE ====="

        tail -n 100 \
            "temp/general_audit_vse4_${SHORT_ID}.log"
    fi
else
    bad "VSE4_MISSING"
fi


section "9. VSE4 IMPORTANT SYMBOLS"

python - <<'PY'
from pathlib import Path
import ast
from collections import Counter

p = Path("visual_selection_engine_v4.py")

if not p.is_file():
    print("VSE4_SYMBOL_AUDIT=MISSING")
    raise SystemExit(0)

src = p.read_text(
    encoding="utf-8",
    errors="replace",
)

tree = ast.parse(src)

funcs = Counter(
    node.name
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
)

assignments = Counter()

for node in tree.body:

    if isinstance(node, ast.Assign):

        for target in node.targets:

            if isinstance(target, ast.Name):
                assignments[
                    target.id
                ] += 1

important_funcs = (
    "norm",
    "objget",
    "number",
    "provider",
    "source_group",
    "media_type",
    "candidate_key",
    "base_score",
    "must_tier",
    "flatten_candidates",
    "concept_hits",
    "geo_hits",
    "candidate_text",
    "tokens",
    "score_candidate",
    "self_test",
)

important_constants = (
    "CONCEPTS",
    "GEO_GROUPS",
    "GENERIC_LIFESTYLE",
    "MEDICINE_TERMS",
    "STOP",
    "ROOT",
)

for name in important_funcs:
    print(
        f"VSE4_FUNCTION={name} count={funcs[name]}"
    )

for name in important_constants:
    print(
        f"VSE4_CONSTANT={name} "
        f"count={assignments[name]}"
    )
PY


section "10. MIDIA VSE INTEGRATION"

python - <<'PY'
from pathlib import Path

src = Path(
    "midia.py"
).read_text(
    encoding="utf-8",
    errors="replace",
)

checks = {
    "VSE2":
        (
            "visual_selection_engine_v2"
            in src
            or "VSE2" in src
        ),

    "VSE3":
        (
            "visual_selection_final_gate_v3"
            in src
            or "VSE3" in src
        ),

    "VSE4":
        (
            "visual_selection_engine_v4"
            in src
            or "VSE4" in src
        ),

    "COMMIT_LOCK":
        (
            "visual_scene_commit_lock"
            in src
            or "SCENE_COMMIT_LOCK"
            in src
        ),

    "MUST_RESCUE":
        (
            "visual_must_rescue"
            in src
            or "MUST_RESCUE"
            in src
        ),

    "PROVENANCE":
        "media_provenance_capture"
        in src,

    "DIVERSITY":
        "media_diversity_guard"
        in src,
}

for key, value in checks.items():

    print(
        f"MIDIA_{key}="
        f"{'FOUND' if value else 'NOT_FOUND'}"
    )
PY


section "11. PROVIDER ACQUISITION MAP"

python - <<'PY'
from pathlib import Path
import ast

src = Path(
    "midia.py"
).read_text(
    encoding="utf-8",
    errors="replace",
)

tree = ast.parse(src)

wanted = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",
    "buscar_todos_candidatos",
    "baixar_candidato_5_2",
}

for node in tree.body:

    if (
        isinstance(node, ast.FunctionDef)
        and node.name in wanted
    ):
        print(
            f"FUNCTION={node.name} "
            f"lines={node.lineno}-{node.end_lineno}"
        )

target = next(
    (
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "buscar_todos_candidatos"
    ),
    None,
)

if target is None:

    print(
        "BUSCAR_TODOS_CANDIDATOS=NOT_FOUND"
    )

else:

    calls = []

    for node in ast.walk(target):

        if not isinstance(node, ast.Call):
            continue

        fn = node.func

        if isinstance(fn, ast.Name):
            name = fn.id

        elif isinstance(fn, ast.Attribute):
            name = fn.attr

        else:
            continue

        calls.append(
            (
                node.lineno,
                name,
            )
        )

    for line, name in sorted(calls):

        if any(
            term in name.lower()
            for term in (
                "pexels",
                "pixabay",
                "coverr",
                "wikimedia",
            )
        ):
            print(
                f"PROVIDER_CALL=line:{line} name:{name}"
            )
PY


section "12. PROVIDER CONFIG NAMES ONLY"

if [ -f config.env ]; then

    grep -E \
        '^[A-Za-z_][A-Za-z0-9_]*=' \
        config.env |
    cut -d= -f1 |
    grep -Ei \
        'pexels|pixabay|coverr|wiki|gemini|api' |
    sed 's/^/CONFIG_KEY_NAME=/'

else
    warn "config.env missing"
fi


section "13. CURRENT 12-SCENE STRUCTURE"

MEDIA_DIR="imagens/short_${SHORT_ID}"

SCENE_BAD=0
SCENE_TOTAL=0

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

    SCENE_TOTAL=$((SCENE_TOTAL + COUNT))

    echo "SCENE_${N}_COUNT=$COUNT"

    find "$MEDIA_DIR" \
        -maxdepth 1 \
        -type f \
        -name "scene_${N}.*" \
        -printf '  %s bytes | %f\n' \
        2>/dev/null

    if [ "$COUNT" -ne 1 ]; then
        SCENE_BAD=$((SCENE_BAD + 1))
    fi
done

echo "MEDIA_TOTAL=$SCENE_TOTAL"
echo "INVALID_SCENE_COUNT=$SCENE_BAD"

if [ "$SCENE_TOTAL" -eq 12 ] &&
   [ "$SCENE_BAD" -eq 0 ]; then
    ok "EXACTLY_12_SCENE_MEDIA"
else
    bad "SCENE_STRUCTURE total=$SCENE_TOTAL invalid=$SCENE_BAD"
fi


section "14. MEDIA TECHNICAL PROBE"

MEDIA_PROBE_BAD=0

if [ -d "$MEDIA_DIR" ]; then

    for F in "$MEDIA_DIR"/scene_*
    do
        [ -f "$F" ] || continue

        INFO="$(
            ffprobe \
            -v error \
            -show_entries \
stream=codec_name,width,height,duration \
            -show_entries \
format=duration,size \
            -of compact=p=0:nk=0 \
            "$F" \
            2>&1
        )"

        STATUS=$?

        echo "MEDIA_PROBE | $F | $INFO"

        if [ "$STATUS" -ne 0 ]; then
            MEDIA_PROBE_BAD=$((MEDIA_PROBE_BAD + 1))
        fi
    done
fi

echo "MEDIA_PROBE_FAILURES=$MEDIA_PROBE_BAD"

if [ "$MEDIA_PROBE_BAD" -eq 0 ]; then
    ok "MEDIA_TECHNICAL_PROBE"
else
    bad "MEDIA_PROBE_FAILURES=$MEDIA_PROBE_BAD"
fi


section "15. EXACT MEDIA HASH DUPLICATES"

python - <<'PY'
from pathlib import Path
from collections import defaultdict
import hashlib
import os

sid = os.environ["SHORT_ID"]

root = (
    Path("imagens")
    / f"short_{sid}"
)

groups = defaultdict(list)

for p in sorted(
    root.glob(
        "scene_*"
    )
):

    if not p.is_file():
        continue

    h = hashlib.sha256()

    with p.open("rb") as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):
            h.update(chunk)

    groups[
        h.hexdigest()
    ].append(
        p.name
    )

duplicates = {
    sha: names
    for sha, names in groups.items()
    if len(names) > 1
}

if duplicates:

    for sha, names in duplicates.items():

        print(
            "EXACT_MEDIA_DUPLICATE="
            + sha
            + " | "
            + ",".join(names)
        )

    print(
        "EXACT_MEDIA_DUPLICATES=YES"
    )

else:

    print(
        "EXACT_MEDIA_DUPLICATES=NO"
    )
PY


section "16. PIPELINE REQUIRED ASSETS"

for F in \
"audios/short_${SHORT_ID}.mp3" \
"videos/short_${SHORT_ID}.ass" \
"temp/${SHORT_ID}/video_sem_audio.mp4" \
"videos/short_v6_${SHORT_ID}.mp4"
do

    if [ -s "$F" ]; then
        echo "PIPELINE_FILE=PASS | $(stat -c%s "$F") | $F"
    elif [ -e "$F" ]; then
        echo "PIPELINE_FILE=EMPTY | $F"
    else
        echo "PIPELINE_FILE=MISSING | $F"
    fi
done


section "17. AUDIO / ASS / VIDEO DURATIONS"

for F in \
"audios/short_${SHORT_ID}.mp3" \
"temp/${SHORT_ID}/video_sem_audio.mp4" \
"videos/short_v6_${SHORT_ID}.mp4"
do

    [ -s "$F" ] || continue

    D="$(
        ffprobe \
        -v error \
        -show_entries format=duration \
        -of default=nw=1:nk=1 \
        "$F" \
        2>/dev/null
    )"

    echo "DURATION=$D | $F"
done

ASS="videos/short_${SHORT_ID}.ass"

if [ -s "$ASS" ]; then

    EVENTS="$(
        grep -c '^Dialogue:' "$ASS" 2>/dev/null
    )"

    echo "ASS_DIALOGUE_EVENTS=$EVENTS"

    if [ "$EVENTS" -gt 0 ]; then
        ok "ASS_HAS_DIALOGUE_EVENTS=$EVENTS"
    else
        bad "ASS_HAS_NO_DIALOGUE_EVENTS"
    fi
fi


section "18. SCENE MAP STATE"

find roteiros \
    -maxdepth 1 \
    -type f \
    -name "*${SHORT_ID}*.json" \
    -printf '%s | %f\n' \
    2>/dev/null |
sort


section "19. RENDER INPUT FINGERPRINT"

if [ -s render_input_fingerprint_v1.py ]; then

    python render_input_fingerprint_v1.py 2>&1

else

    warn "render_input_fingerprint_v1.py missing"
fi


section "20. FRESH RENDER GUARD SAFETY"

python - <<'PY'
from pathlib import Path

p = Path(
    "fresh_render_guard_v1.py"
)

if not p.is_file():
    print(
        "RENDER_GUARD=MISSING"
    )
    raise SystemExit(0)

src = p.read_text(
    encoding="utf-8",
    errors="replace",
)

checks = {
    "ASS_PROTECTED":
        (
            '".ass"' in src
            or "'.ass'" in src
        ),

    "SRT_PROTECTED":
        (
            '".srt"' in src
            or "'.srt'" in src
        ),

    "MP3_PROTECTED":
        (
            '".mp3"' in src
            or "'.mp3'" in src
        ),

    "VIDEO_SEM_AUDIO_TARGETED":
        "video_sem_audio.mp4"
        in src,
}

for name, ok in checks.items():

    print(
        f"RENDER_GUARD_{name}="
        f"{'PASS' if ok else 'FAIL'}"
    )
PY


section "21. PROVENANCE STATE"

if [ -d manifests/source_provenance_live ]; then

    COUNT="$(
        find manifests/source_provenance_live \
        -type f \
        -name '*.json' \
        2>/dev/null |
        wc -l
    )"

    echo "PROVENANCE_JSON_COUNT=$COUNT"

    find manifests/source_provenance_live \
        -type f \
        -name '*.json' \
        -printf '%TY-%Tm-%Td %TH:%TM:%TS | %s | %p\n' \
        2>/dev/null |
        sort -r |
        head -n 20

else
    warn "SOURCE_PROVENANCE_DIRECTORY_MISSING"
fi


section "22. CURRENT VSE/MEDIA LOG SUMMARY"

LATEST_MEDIA_LOG="$(
    find logs/producao \
    -type f \
    \( \
        -name "*${SHORT_ID}*" \
        -o \
        -name '*vse*' \
    \) \
    2>/dev/null |
    sort |
    tail -n 1
)"

echo "LATEST_MEDIA_LOG=${LATEST_MEDIA_LOG:-NONE}"

if [ -n "$LATEST_MEDIA_LOG" ] &&
   [ -f "$LATEST_MEDIA_LOG" ]; then

    echo
    echo "===== CHOSEN PROVIDERS ====="

    grep -E \
        'ESCOLHIDO:' \
        "$LATEST_MEDIA_LOG" \
        2>/dev/null |
        tail -n 30

    echo
    echo "===== MUST ====="

    grep -E \
        'MUST COVERAGE|must=' \
        "$LATEST_MEDIA_LOG" \
        2>/dev/null |
        tail -n 40

    echo
    echo "===== VSE / COMMIT ====="

    grep -E \
        'VSE[234]|SCENE_COMMIT|MUST_RESCUE' \
        "$LATEST_MEDIA_LOG" \
        2>/dev/null |
        tail -n 100
fi


section "23. HISTORICAL DOUBLE-DOWNLOAD SIGNAL"

LOGS="$(
    find logs/producao \
    -type f \
    -name "*${SHORT_ID}*" \
    2>/dev/null
)"

if [ -n "$LOGS" ]; then

    grep -Hn \
        'FAILOVER: QUALIDADE PRESERVADA' \
        $LOGS \
        2>/dev/null |
        tail -n 30

    grep -Hn \
        'SCENE_COMMIT_LOCK=' \
        $LOGS \
        2>/dev/null |
        tail -n 50
fi


section "24. MIDIA DOWNLOAD CALL STATIC MAP"

python - <<'PY'
from pathlib import Path
import ast

p = Path("midia.py")

if not p.is_file():
    print("MIDIA_AST=MISSING")
    raise SystemExit(0)

tree = ast.parse(
    p.read_text(
        encoding="utf-8",
        errors="replace",
    )
)

calls = []

for node in ast.walk(tree):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    fn = node.func

    if isinstance(fn, ast.Name):
        name = fn.id

    elif isinstance(fn, ast.Attribute):
        name = fn.attr

    else:
        continue

    if name == "baixar_candidato_5_2":

        calls.append(
            node.lineno
        )

print(
    "BAIXAR_CANDIDATO_CALL_COUNT="
    + str(len(calls))
)

print(
    "BAIXAR_CANDIDATO_CALL_LINES="
    + ",".join(
        str(x)
        for x in calls
    )
)
PY


section "25. GERAR_SHORT PIPELINE STAGES"

grep -nE \
    '^[[:space:]]*[A-Za-z_]*"?[0-9]+/[0-9]+|python .*\.py|legenda_dinamica|midia.py|video.py|v6.py' \
    gerar_short.sh \
    2>/dev/null |
    head -n 250


section "26. TOOLING"

WHISPER="$HOME/whisper.cpp/build/bin/whisper-cli"
MODEL="$HOME/whisper.cpp/models/ggml-base.bin"

[ -x "$WHISPER" ] \
&& ok "WHISPER_CLI" \
|| warn "WHISPER_CLI_MISSING"

[ -s "$MODEL" ] \
&& ok "WHISPER_MODEL" \
|| warn "WHISPER_MODEL_MISSING"

command -v piper >/dev/null 2>&1 \
&& ok "PIPER_FOUND" \
|| warn "PIPER_COMMAND_NOT_FOUND"

ffmpeg -hide_banner -filters 2>/dev/null |
grep -q ' subtitles ' \
&& ok "FFMPEG_SUBTITLES_FILTER" \
|| warn "FFMPEG_SUBTITLES_FILTER_MISSING"

ffmpeg -hide_banner -filters 2>/dev/null |
grep -q ' zoompan ' \
&& ok "FFMPEG_ZOOMPAN_FILTER" \
|| warn "FFMPEG_ZOOMPAN_FILTER_MISSING"


section "27. RECENT ERRORS"

find logs \
    -type f \
    -mmin -1440 \
    2>/dev/null |
while read -r LOG
do
    grep -HniE \
        'traceback|nameerror|typeerror|syntaxerror|assertionerror|exception|erro:|error:|fail(ed)?' \
        "$LOG" \
        2>/dev/null |
        tail -n 15
done |
tail -n 150


section "28. BROKEN SYMLINKS"

BROKEN="$(
    find . \
    -xtype l \
    -print \
    2>/dev/null
)"

if [ -z "$BROKEN" ]; then
    ok "NO_BROKEN_SYMLINKS"
else
    echo "$BROKEN"
    warn "BROKEN_SYMLINKS_PRESENT"
fi


section "29. LARGE TEMP FILES"

find temp \
    -type f \
    -size +20M \
    -printf '%s bytes | %p\n' \
    2>/dev/null |
    sort -nr |
    head -n 50


section "30. FINAL AUTOMATIC SUMMARY"

echo "AUDIT_PASSES=$PASS"
echo "AUDIT_WARNINGS=$WARN"
echo "AUDIT_FAILURES=$FAIL"

echo

if [ "$FAIL" -eq 0 ]; then

    echo "GENERAL_AUDIT_STATUS=PASS_WITH_${WARN}_WARNINGS"

else

    echo "GENERAL_AUDIT_STATUS=FAIL"
fi

echo
echo "SHORT_ID=$SHORT_ID"
echo "REPORT=$OUT"
echo "NETWORK_EXECUTED=NO"
echo "MEDIA_DOWNLOADED=NO"
echo "MIDIA_PIPELINE_EXECUTED=NO"
echo "VIDEO_RENDERED=NO"
echo "PRODUCTION_FILES_MODIFIED=NO"
echo "TERMUX_CONTINUA_ABERTO=SIM"

} 2>&1 | tee "$OUT"


echo
echo "======================================================================"
echo " RESUMO PARA ENVIAR AO CHAT"
echo "======================================================================"

grep -E \
'AUDIT_(PASS|WARN|FAIL)|GENERAL_AUDIT_STATUS=|VSE4_SELF_TEST=|VSE4_GLOBAL_AUDIT=|VSE4_UNRESOLVED_GLOBALS=|MIDIA_VSE4=|MIDIA_COMMIT_LOCK=|MIDIA_MUST_RESCUE=|MEDIA_TOTAL=|INVALID_SCENE_COUNT=|EXACT_MEDIA_DUPLICATES=|MEDIA_PROBE_FAILURES=|BAIXAR_CANDIDATO_CALL_COUNT=|PROVENANCE_JSON_COUNT=|PYTHON_COMPILE_FAILURES=|SHELL_FAILURES=' \
"$OUT"

echo
echo "RELATORIO_COMPLETO=$OUT"
echo "TERMUX_CONTINUA_ABERTO=SIM"
