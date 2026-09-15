#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

SID="${SHORT_ID:-2026-09-03_1148}"

STAMP="$(date +%Y%m%d_%H%M%S)"

OUT="temp/GENERAL_VISUAL_AUDIT_V3_${SID}_${STAMP}.txt"

mkdir -p temp

exec > >(tee "$OUT") 2>&1


section() {

    echo
    echo "======================================================================"
    echo " $1"
    echo "======================================================================"

}


echo "======================================================================"
echo " SHORTAUTOPRO - GENERAL VISUAL AUDIT V3"
echo "======================================================================"
echo "DATE=$(date)"
echo "PWD=$(pwd)"
echo "SHORT_ID=$SID"
echo "REPORT=$OUT"


# ======================================================================
# 1
# ======================================================================

section "1. CORE FILE PRESENCE + HASHES"

CORE_FILES=(
    midia.py
    visual_selection_engine_v4.py
    media_diversity_guard_v1.py
    media_provenance_capture_v1.py
    visual_scene_commit_lock_v1.py
    visual_must_rescue_v1.py
    video.py
    v6.py
    gerar_short.sh
)

MISSING_CORE=0

for F in "${CORE_FILES[@]}"
do

    if [ -f "$F" ]; then

        echo
        echo "FOUND=$F"

        sha256sum "$F"

    else

        echo
        echo "MISSING=$F"

        MISSING_CORE=$((MISSING_CORE + 1))

    fi

done

echo
echo "MISSING_CORE_FILES=$MISSING_CORE"


# ======================================================================
# 2
# ======================================================================

section "2. PYTHON COMPILE + SHELL SYNTAX"

COMPILE_FAIL=0

for F in \
midia.py \
visual_selection_engine_v4.py \
media_diversity_guard_v1.py \
media_provenance_capture_v1.py \
visual_scene_commit_lock_v1.py \
visual_must_rescue_v1.py \
video.py \
v6.py
do

    if [ ! -f "$F" ]; then
        continue
    fi

    python -m py_compile "$F"

    S=$?

    echo "$F COMPILE=$S"

    if [ "$S" -ne 0 ]; then
        COMPILE_FAIL=$((COMPILE_FAIL + 1))
    fi

done


bash -n gerar_short.sh 2>/dev/null

SHELL_STATUS=$?

echo
echo "GERAR_SHORT_SYNTAX=$SHELL_STATUS"
echo "PYTHON_COMPILE_FAILURES=$COMPILE_FAIL"


# ======================================================================
# 3
# ======================================================================

section "3. VSE4 STRUCTURE / DUPLICATE DEFINITIONS"

python - <<'PY'
from pathlib import Path
import ast
from collections import Counter

p = Path("visual_selection_engine_v4.py")

if not p.exists():
    print("VSE4_STRUCTURE=FAIL_FILE_MISSING")
    raise SystemExit(0)

src = p.read_text(
    encoding="utf-8",
    errors="replace",
)

try:
    tree = ast.parse(src)

except Exception as exc:

    print(
        "VSE4_AST_PARSE=FAIL",
        type(exc).__name__,
        exc,
    )

    raise SystemExit(0)


names = []

for node in tree.body:

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
        ),
    ):
        names.append(
            node.name
        )


counts = Counter(names)


important = (
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


duplicates = []

missing = []


for name in important:

    count = counts.get(
        name,
        0,
    )

    print(
        f"DEF_{name}={count}"
    )

    if count == 0:
        missing.append(name)

    if count > 1:
        duplicates.append(name)


print(
    "IMPORTANT_MISSING="
    +
    (
        ",".join(missing)
        if missing
        else
        "NONE"
    )
)

print(
    "IMPORTANT_DUPLICATES="
    +
    (
        ",".join(duplicates)
        if duplicates
        else
        "NONE"
    )
)

if not missing and not duplicates:
    print("VSE4_STRUCTURE=PASS")
else:
    print("VSE4_STRUCTURE=REVIEW")
PY


# ======================================================================
# 4
# ======================================================================

section "4. VSE4 TRUE UNRESOLVED GLOBALS"

python - <<'PY'
from pathlib import Path
import symtable
import builtins

p = Path("visual_selection_engine_v4.py")

if not p.exists():
    print("GLOBAL_AUDIT=SKIPPED")
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
        "GLOBAL_AUDIT=FAIL_PARSE",
        type(exc).__name__,
        exc,
    )

    raise SystemExit(0)


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
        +
        ",".join(
            sorted(unresolved)
        )
    )

    print(
        "GLOBAL_AUDIT=FAIL"
    )

else:

    print(
        "TRUE_UNRESOLVED_GLOBALS=NONE"
    )

    print(
        "GLOBAL_AUDIT=PASS"
    )
PY


# ======================================================================
# 5
# ======================================================================

section "5. VSE4 SELF TEST"

if [ -f visual_selection_engine_v4.py ]; then

    python \
    visual_selection_engine_v4.py \
    > "temp/general_vse4_selftest_${SID}.log" \
    2>&1

    VSE4_TEST=$?

    cat \
    "temp/general_vse4_selftest_${SID}.log"

    echo
    echo "VSE4_SELF_TEST_STATUS=$VSE4_TEST"

else

    echo "VSE4_SELF_TEST_STATUS=SKIPPED"

fi


# ======================================================================
# 6
# ======================================================================

section "6. DIRECT SEMANTIC / GEO SAFETY TEST"

python - <<'PY'
import runpy
import traceback

try:

    ns = runpy.run_path(
        "visual_selection_engine_v4.py",
        run_name="general_visual_audit",
    )

except Exception:

    print(
        "VSE4_RUNTIME_LOAD=FAIL"
    )

    traceback.print_exc()

    raise SystemExit(0)


required = (
    "score_candidate",
    "geo_hits",
    "concept_hits",
    "candidate_text",
)


missing = [
    name
    for name in required
    if name not in ns
]


if missing:

    print(
        "DIRECT_SEMANTIC_TEST=SKIPPED_MISSING="
        +
        ",".join(missing)
    )

    raise SystemExit(0)


score_candidate = ns[
    "score_candidate"
]

geo_hits = ns[
    "geo_hits"
]

concept_hits = ns[
    "concept_hits"
]


state = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


tests = []


# ------------------------------------------------------
# GEO CONTRADICTION
# ------------------------------------------------------

scene = (
    "Investigação em apartamento "
    "na cidade de São Paulo Brasil"
)

wrong = {
    "provider":
        "Pixabay",

    "tipo":
        "foto",

    "title":
        "Empire State Building Manhattan New York",

    "must":
        "2/2",

    "score":
        250,

    "width":
        1920,

    "height":
        1080,
}


correct = {
    "provider":
        "Wikimedia",

    "tipo":
        "foto",

    "title":
        "Apartment building Sao Paulo Brazil",

    "must":
        "1/2",

    "score":
        120,

    "width":
        1920,

    "height":
        1080,
}


try:

    wrong_result = score_candidate(
        wrong,
        scene,
        state,
    )

    correct_result = score_candidate(
        correct,
        scene,
        state,
    )


    print(
        "GEO_SCENE=",
        sorted(
            geo_hits(scene)
        ),
    )

    print(
        "GEO_WRONG=",
        sorted(
            geo_hits(
                wrong["title"]
            )
        ),
    )

    print(
        "GEO_CORRECT=",
        sorted(
            geo_hits(
                correct["title"]
            )
        ),
    )


    print(
        "WRONG_HARD_MISMATCH=",
        wrong_result.get(
            "hard_mismatch"
        ),
    )

    print(
        "CORRECT_HARD_MISMATCH=",
        correct_result.get(
            "hard_mismatch"
        ),
    )

    print(
        "WRONG_EFFECTIVE=",
        wrong_result.get(
            "effective"
        ),
    )

    print(
        "CORRECT_EFFECTIVE=",
        correct_result.get(
            "effective"
        ),
    )


    geo_pass = (
        wrong_result.get(
            "hard_mismatch"
        )
        is True
        and
        correct_result.get(
            "hard_mismatch"
        )
        is False
    )


    print(
        "GEO_HARD_MISMATCH_TEST="
        +
        (
            "PASS"
            if geo_pass
            else
            "FAIL"
        )
    )

    tests.append(
        geo_pass
    )


except Exception:

    print(
        "GEO_HARD_MISMATCH_TEST=EXCEPTION"
    )

    traceback.print_exc()

    tests.append(
        False
    )


# ------------------------------------------------------
# FORENSIC / MEDICINE FALSE ASSOCIATION
# ------------------------------------------------------

scene2 = (
    "A perícia analisou os vestígios "
    "e o laudo encontrou novas evidências"
)

medicine = {
    "provider":
        "Pixabay",

    "tipo":
        "foto",

    "title":
        "Pills medication tablets pharmacy",

    "must":
        "2/2",

    "score":
        240,

    "width":
        1920,

    "height":
        1080,
}


forensic = {
    "provider":
        "Pexels",

    "tipo":
        "foto",

    "title":
        "Forensic laboratory evidence investigation",

    "must":
        "2/2",

    "score":
        160,

    "width":
        1920,

    "height":
        1080,
}


try:

    med = score_candidate(
        medicine,
        scene2,
        state,
    )

    good = score_candidate(
        forensic,
        scene2,
        state,
    )


    print()
    print(
        "FORENSIC_SCENE_CONCEPTS=",
        sorted(
            concept_hits(scene2)
        ),
    )

    print(
        "MEDICINE_CONCEPTS=",
        sorted(
            concept_hits(
                medicine["title"]
            )
        ),
    )

    print(
        "FORENSIC_CONCEPTS=",
        sorted(
            concept_hits(
                forensic["title"]
            )
        ),
    )

    print(
        "MEDICINE_EFFECTIVE=",
        med.get(
            "effective"
        ),
    )

    print(
        "FORENSIC_EFFECTIVE=",
        good.get(
            "effective"
        ),
    )

    med_pass = (
        good.get(
            "effective",
            -999999,
        )
        >
        med.get(
            "effective",
            999999,
        )
    )


    print(
        "FORENSIC_FALSE_ASSOCIATION_TEST="
        +
        (
            "PASS"
            if med_pass
            else
            "FAIL"
        )
    )

    tests.append(
        med_pass
    )


except Exception:

    print(
        "FORENSIC_FALSE_ASSOCIATION_TEST=EXCEPTION"
    )

    traceback.print_exc()

    tests.append(
        False
    )


print()

if tests and all(tests):

    print(
        "DIRECT_SEMANTIC_TEST=PASS"
    )

else:

    print(
        "DIRECT_SEMANTIC_TEST=FAIL"
    )
PY


# ======================================================================
# 7
# ======================================================================

section "7. MIDIA.PY VSE4 INTEGRATION"

echo "===== VSE4 REFERENCES ====="

grep -nEi \
'VSE4|visual_selection_engine_v4|score_candidate|hard_mismatch|geo_|semantic|must.*rescue' \
midia.py \
2>/dev/null |
head -n 800


echo
echo "===== DIVERSITY REFERENCES ====="

grep -nEi \
'media_diversity|provider.*penal|source_group|diversity|repeat' \
midia.py \
2>/dev/null |
head -n 400


echo
echo "===== PROVENANCE REFERENCES ====="

grep -nEi \
'provenance|source_provenance|media_provenance' \
midia.py \
2>/dev/null |
head -n 400


echo
echo "===== COMMIT REFERENCES ====="

grep -nEi \
'commit|scene.*lock|winner|locked|SCENE_COMMIT' \
midia.py \
media_diversity_guard_v1.py \
2>/dev/null |
head -n 500


# ======================================================================
# 8
# ======================================================================

section "8. PROVIDER ACQUISITION MAP"

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


wanted = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",
    "buscar_todos_candidatos",
)


functions = {}


for node in tree.body:

    if (
        isinstance(
            node,
            ast.FunctionDef,
        )
        and node.name in wanted
    ):

        functions[
            node.name
        ] = node


for name in wanted:

    node = functions.get(
        name
    )

    if node is None:

        print(
            f"PROVIDER_FUNCTION={name} MISSING"
        )

        continue

    print(
        f"PROVIDER_FUNCTION={name} "
        f"lines={node.lineno}-{node.end_lineno}"
    )


target = functions.get(
    "buscar_todos_candidatos"
)


if target:

    print()
    print(
        "===== CALLS INSIDE buscar_todos_candidatos ====="
    )

    for node in ast.walk(
        target
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        try:

            name = ast.unparse(
                node.func
            )

        except Exception:

            name = "?"

        print(
            f"CALL line={node.lineno} name={name}"
        )
PY


# ======================================================================
# 9
# ======================================================================

section "9. PROVIDER CONFIG AVAILABILITY"

python - <<'PY'
from pathlib import Path
import re

src = Path(
    "midia.py"
).read_text(
    encoding="utf-8",
    errors="replace",
)

names = sorted(
    set(
        re.findall(
            r'\b[A-Z][A-Z0-9_]*(?:API|KEY|TOKEN)[A-Z0-9_]*\b',
            src,
        )
    )
)


for name in names:

    print(
        f"CONFIG_SYMBOL={name}"
    )


print(
    "CONFIG_VALUES_EXPOSED=NO"
)
PY


# ======================================================================
# 10
# ======================================================================

section "10. POST-DOWNLOAD / FAILOVER CONTROL FLOW"

python - <<'PY'
import ast
from pathlib import Path

src = Path(
    "midia.py"
).read_text(
    encoding="utf-8",
    errors="replace",
)

lines = src.splitlines()

tree = ast.parse(src)


hits = []


for node in ast.walk(tree):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    try:

        name = ast.unparse(
            node.func
        )

    except Exception:

        name = ""


    if any(
        term in name.casefold()
        for term in (
            "baixar_candidato",
            "download",
        )
    ):

        hits.append(
            (
                node.lineno,
                name,
            )
        )


for lineno, name in hits:

    print()
    print(
        "=" * 66
    )

    print(
        f"DOWNLOAD_CALL line={lineno} name={name}"
    )

    print(
        "=" * 66
    )

    start = max(
        1,
        lineno - 18,
    )

    end = min(
        len(lines),
        lineno + 40,
    )

    for n in range(
        start,
        end + 1,
    ):

        print(
            f"{n:05d}: {lines[n-1]}"
        )
PY


# ======================================================================
# 11
# ======================================================================

section "11. CURRENT SHORT MEDIA STRUCTURE"

DIR="imagens/short_${SID}"

MEDIA_TOTAL=0
BAD_SCENES=0
COLLISIONS=0


if [ ! -d "$DIR" ]; then

    echo "MEDIA_DIR=NOT_FOUND"
    echo "MEDIA_STRUCTURE=FAIL"

else

    echo "MEDIA_DIR=$DIR"


    for N in $(seq -w 1 12)
    do

        COUNT="$(
            find "$DIR" \
            -maxdepth 1 \
            -type f \
            -name "scene_${N}.*" \
            2>/dev/null |
            wc -l
        )"


        MEDIA_TOTAL=$((MEDIA_TOTAL + COUNT))


        echo
        echo "SCENE_${N}_COUNT=$COUNT"


        find "$DIR" \
        -maxdepth 1 \
        -type f \
        -name "scene_${N}.*" \
        -printf '  %s bytes | %f\n' \
        2>/dev/null


        if [ "$COUNT" -ne 1 ]; then

            BAD_SCENES=$((BAD_SCENES + 1))

        fi


        if [ "$COUNT" -gt 1 ]; then

            COLLISIONS=$((COLLISIONS + 1))

        fi

    done


    echo
    echo "MEDIA_TOTAL=$MEDIA_TOTAL"
    echo "BAD_SCENE_COUNTS=$BAD_SCENES"
    echo "SCENE_COLLISIONS=$COLLISIONS"


    if \
    [ "$MEDIA_TOTAL" -eq 12 ] &&
    [ "$BAD_SCENES" -eq 0 ]
    then

        echo "MEDIA_STRUCTURE=PASS"

    else

        echo "MEDIA_STRUCTURE=FAIL"

    fi

fi


# ======================================================================
# 12
# ======================================================================

section "12. MEDIA SHA DUPLICATION"

if [ -d "$DIR" ]; then

    python - "$DIR" <<'PY'
from pathlib import Path
from collections import defaultdict
import hashlib
import sys

root = Path(
    sys.argv[1]
)

groups = defaultdict(
    list
)


for path in sorted(
    root.glob(
        "scene_*.*"
    )
):

    if not path.is_file():
        continue


    h = hashlib.sha256()

    try:

        with path.open(
            "rb"
        ) as f:

            for chunk in iter(
                lambda:
                    f.read(
                        1024 * 1024
                    ),
                b"",
            ):

                h.update(
                    chunk
                )

    except Exception as exc:

        print(
            "HASH_ERROR=",
            path,
            type(exc).__name__,
            exc,
        )

        continue


    groups[
        h.hexdigest()
    ].append(
        path.name
    )


duplicates = {
    digest:
        files
    for digest, files in groups.items()
    if len(files) > 1
}


if not duplicates:

    print(
        "EXACT_MEDIA_DUPLICATES=0"
    )

    print(
        "MEDIA_SHA_DIVERSITY=PASS"
    )

else:

    print(
        "EXACT_MEDIA_DUPLICATES=",
        len(duplicates),
    )

    for digest, files in duplicates.items():

        print(
            "DUPLICATE_SHA=",
            digest,
            "FILES=",
            ",".join(files),
        )

    print(
        "MEDIA_SHA_DIVERSITY=FAIL"
    )
PY

fi


# ======================================================================
# 13
# ======================================================================

section "13. MEDIA TECHNICAL VALIDITY"

if [ -d "$DIR" ]; then

    TECH_FAIL=0


    for F in "$DIR"/scene_*.*
    do

        [ -f "$F" ] || continue


        SIZE="$(
            stat -c%s "$F" \
            2>/dev/null
        )"


        echo
        echo "FILE=$F"
        echo "BYTES=$SIZE"


        ffprobe \
        -v error \
        -show_entries \
stream=codec_name,codec_type,width,height,r_frame_rate,duration \
        -show_entries \
format=duration,size \
        -of default=noprint_wrappers=1 \
        "$F" \
        2>&1 |
        head -n 30


        PROBE=${PIPESTATUS[0]}


        if [ "$PROBE" -ne 0 ]; then

            echo "TECH_VALID=FAIL"

            TECH_FAIL=$((TECH_FAIL + 1))

        else

            echo "TECH_VALID=PASS"

        fi

    done


    echo
    echo "TECHNICAL_MEDIA_FAILURES=$TECH_FAIL"

fi


# ======================================================================
# 14
# ======================================================================

section "14. SCENE MAP DISCOVERY"

find roteiros \
-maxdepth 1 \
-type f \
-name "*${SID}*.json" \
-printf '%TY-%Tm-%Td %TH:%TM:%TS | %s | %p\n' \
2>/dev/null |
sort


# ======================================================================
# 15
# ======================================================================

section "15. SCENE MAP STRUCTURAL AUDIT"

python - "$SID" <<'PY'
from pathlib import Path
import json
import sys

sid = sys.argv[1]

root = Path(
    "roteiros"
)


preferred = [
    root / f"scene_map_{sid}.json",
    root / f"visual_director_{sid}.json",
]


candidates = [
    p
    for p in preferred
    if p.exists()
]


if not candidates:

    candidates = sorted(
        root.glob(
            f"*{sid}*.json"
        )
    )


target = None
data = None


for path in candidates:

    try:

        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        continue


    def find_scenes(obj):

        if isinstance(
            obj,
            list,
        ):

            if len(obj) >= 8:

                dict_count = sum(
                    isinstance(
                        x,
                        dict,
                    )
                    for x in obj
                )

                if dict_count >= 8:
                    return obj

            for item in obj:

                result = find_scenes(
                    item
                )

                if result:
                    return result


        elif isinstance(
            obj,
            dict,
        ):

            for key in (
                "scenes",
                "cenas",
                "scene_map",
                "items",
            ):

                if key in obj:

                    result = find_scenes(
                        obj[key]
                    )

                    if result:
                        return result


            for item in obj.values():

                result = find_scenes(
                    item
                )

                if result:
                    return result


        return None


    scenes = find_scenes(
        value
    )


    if scenes:

        target = path
        data = scenes
        break


if target is None:

    print(
        "SCENE_MAP_AUDIT=NO_SCENE_STRUCTURE_FOUND"
    )

    raise SystemExit(0)


print(
    "SCENE_MAP_SOURCE=",
    target,
)

print(
    "SCENE_MAP_COUNT=",
    len(data),
)


weak_queries = 0
missing_must = 0


for index, scene in enumerate(
    data[:12],
    start=1,
):

    if not isinstance(
        scene,
        dict,
    ):

        print(
            f"SCENE_{index:02d}=NON_DICT"
        )

        continue


    query = (
        scene.get(
            "visual_query"
        )
        or
        scene.get(
            "query"
        )
        or
        scene.get(
            "busca"
        )
        or
        ""
    )


    must = (
        scene.get(
            "must_have"
        )
        or
        scene.get(
            "must"
        )
        or
        []
    )


    location = (
        scene.get(
            "location"
        )
        or
        scene.get(
            "local"
        )
        or
        ""
    )


    print()
    print(
        f"SCENE_{index:02d}_QUERY={query}"
    )

    print(
        f"SCENE_{index:02d}_MUST={must}"
    )

    print(
        f"SCENE_{index:02d}_LOCATION={location}"
    )


    if len(
        str(query).split()
    ) < 2:

        weak_queries += 1


    if not must:

        missing_must += 1


print()
print(
    "WEAK_VISUAL_QUERIES=",
    weak_queries,
)

print(
    "SCENES_WITHOUT_MUST=",
    missing_must,
)


if len(data) >= 12:

    print(
        "SCENE_MAP_STRUCTURE=PASS"
    )

else:

    print(
        "SCENE_MAP_STRUCTURE=FAIL"
    )
PY


# ======================================================================
# 16
# ======================================================================

section "16. CURRENT SHORT LOG DISCOVERY"

find logs/producao \
-type f \
-name "*${SID}*" \
-printf '%TY-%Tm-%Td %TH:%TM:%TS | %s | %p\n' \
2>/dev/null |
sort


# ======================================================================
# 17
# ======================================================================

section "17. CURRENT SHORT ERROR FORENSICS"

CURRENT_ERROR_FILES=0


while IFS= read -r LOG
do

    [ -f "$LOG" ] || continue


    MATCH="$(
        grep -Ei \
'Traceback|NameError|TypeError|KeyError|AttributeError|AssertionError|SyntaxError|ModuleNotFoundError|ERRO:|ERROR:|=FAIL|STATUS=FAIL|media_count=[^1][^2]|scene_[0-9]+_count=[2-9]' \
        "$LOG" \
        2>/dev/null |
        tail -n 120
    )"


    if [ -n "$MATCH" ]; then

        CURRENT_ERROR_FILES=$((CURRENT_ERROR_FILES + 1))

        echo
        echo "LOG_WITH_ERROR=$LOG"

        echo "$MATCH"

    fi

done < <(
    find logs/producao \
    -type f \
    -name "*${SID}*" \
    2>/dev/null
)


echo
echo "CURRENT_SHORT_LOGS_WITH_ERRORS=$CURRENT_ERROR_FILES"


# ======================================================================
# 18
# ======================================================================

section "18. VSE4 CURRENT SHORT TELEMETRY"

grep -RhiE \
'VSE4|MUST COVERAGE|ESCOLHIDO|PROVIDER|SOURCE_GROUP|RESCUE|GEO|MISMATCH|HARD_MISMATCH|DIVERSITY|COMMIT_LOCK|FAILOVER' \
logs/producao/*"${SID}"* \
2>/dev/null |
tail -n 1200


# ======================================================================
# 19
# ======================================================================

section "19. PROVIDER DISTRIBUTION FROM LOGS"

python - "$SID" <<'PY'
from pathlib import Path
from collections import Counter
import re
import sys

sid = sys.argv[1]

logs = list(
    Path(
        "logs/producao"
    ).glob(
        f"*{sid}*"
    )
)


text = "\n".join(

    p.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    for p in logs

    if p.is_file()
)


providers = Counter()


patterns = [

    r"ESCOLHIDO:\s*([^/\n]+)",

    r"winner=([^/\s]+)",

    r"PROVIDER=([A-Za-z0-9_.-]+)",

]


for pattern in patterns:

    for match in re.findall(
        pattern,
        text,
        flags=re.I,
    ):

        name = str(
            match
        ).strip().casefold()

        if name:
            providers[
                name
            ] += 1


print(
    "PROVIDER_SIGNAL_COUNTS="
    +
    repr(
        dict(
            providers
        )
    )
)


known = {
    "pixabay",
    "pexels",
    "coverr",
    "wikimedia",
}


active = [
    p
    for p in known
    if any(
        p in key
        for key in providers
    )
]


print(
    "KNOWN_ACTIVE_PROVIDERS="
    +
    (
        ",".join(
            sorted(active)
        )
        if active
        else
        "NONE_DETECTED"
    )
)


if len(active) >= 2:

    print(
        "PROVIDER_DIVERSITY_SIGNAL=PASS"
    )

elif len(active) == 1:

    print(
        "PROVIDER_DIVERSITY_SIGNAL=WEAK_SINGLE_PROVIDER"
    )

else:

    print(
        "PROVIDER_DIVERSITY_SIGNAL=UNKNOWN"
    )
PY


# ======================================================================
# 20
# ======================================================================

section "20. PROVENANCE STATUS"

echo "===== PROVENANCE DIRECTORIES ====="

find manifests \
-maxdepth 2 \
-type d \
-name '*provenance*' \
-print \
2>/dev/null


echo
echo "===== SHORT-ID PROVENANCE REFERENCES ====="

grep -Rli \
"$SID" \
manifests \
2>/dev/null |
head -n 100


echo
echo "===== RECENT PROVENANCE JSON ====="

find manifests \
-type f \
-name '*.json' \
-mmin -1440 \
-printf '%TY-%Tm-%Td %TH:%TM:%TS | %s | %p\n' \
2>/dev/null |
sort -r |
head -n 100


# ======================================================================
# 21
# ======================================================================

section "21. STALE / CROSS-SHORT MEDIA CHECK"

python - "$SID" <<'PY'
from pathlib import Path
import hashlib
import sys

sid = sys.argv[1]

current = Path(
    f"imagens/short_{sid}"
)


if not current.exists():

    print(
        "CROSS_SHORT_AUDIT=SKIPPED"
    )

    raise SystemExit(0)


def digest(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(
                chunk
            )

    return h.hexdigest()


current_hashes = {}


for path in current.glob(
    "scene_*.*"
):

    if path.is_file():

        try:

            current_hashes[
                digest(path)
            ] = path.name

        except Exception:
            pass


matches = []


for other in Path(
    "imagens"
).glob(
    "short_*"
):

    if not other.is_dir():
        continue

    if other == current:
        continue


    for path in other.glob(
        "scene_*.*"
    ):

        if not path.is_file():
            continue

        try:

            h = digest(
                path
            )

        except Exception:
            continue


        if h in current_hashes:

            matches.append(
                (
                    current_hashes[h],
                    str(path),
                    h,
                )
            )


print(
    "CROSS_SHORT_EXACT_REUSE_COUNT=",
    len(matches),
)


for current_name, old_path, digest_value in matches[:50]:

    print(
        "CROSS_SHORT_REUSE="
        f"{current_name} <- {old_path} "
        f"sha={digest_value}"
    )


if not matches:

    print(
        "CROSS_SHORT_EXACT_REUSE=PASS"
    )

else:

    print(
        "CROSS_SHORT_EXACT_REUSE=REVIEW"
    )
PY


# ======================================================================
# 22
# ======================================================================

section "22. RENDER / FINAL OUTPUT STATUS"

FINAL="videos/short_v6_${SID}.mp4"
BASE="temp/${SID}/video_sem_audio.mp4"
ASS="videos/short_${SID}.ass"
AUDIO="audios/short_${SID}.mp3"


for F in \
"$BASE" \
"$AUDIO" \
"$ASS" \
"$FINAL"
do

    if [ -s "$F" ]; then

        echo
        echo "EXISTS=$F"
        echo "BYTES=$(stat -c%s "$F")"
        echo "MTIME=$(stat -c%y "$F")"

        sha256sum "$F"

    else

        echo
        echo "MISSING=$F"

    fi

done


# ======================================================================
# 23
# ======================================================================

section "23. BACKUP / PATCH MARKER FORENSICS"

grep -nE \
'SHORTAUTOPRO VSE4|VSE4\.|V4\.1|V4\.2|V4\.3|FOUNDATION|HARD.MISMATCH|SEMANTIC|GEO' \
visual_selection_engine_v4.py \
2>/dev/null |
head -n 500


echo
echo "===== MIDIA PATCH MARKERS ====="

grep -nE \
'SHORTAUTOPRO|VSE4|VSE3|PROVENANCE|DIVERSITY|COMMIT|RESCUE' \
midia.py \
2>/dev/null |
head -n 800


# ======================================================================
# 24
# ======================================================================

section "24. SUSPICIOUS EXCEPTION SWALLOWING"

echo "===== midia.py ====="

grep -nE \
'except Exception:[[:space:]]*$|except:[[:space:]]*$|pass[[:space:]]*$' \
midia.py \
2>/dev/null |
head -n 300


echo
echo "===== VSE4 ====="

grep -nE \
'except Exception:[[:space:]]*$|except:[[:space:]]*$|pass[[:space:]]*$' \
visual_selection_engine_v4.py \
2>/dev/null |
head -n 300


# ======================================================================
# 25
# ======================================================================

section "25. FINAL CORE RECHECK"

python -m py_compile \
visual_selection_engine_v4.py \
midia.py \
video.py \
v6.py

FINAL_PYTHON=$?


bash -n gerar_short.sh

FINAL_SHELL=$?


echo "FINAL_PYTHON_COMPILE=$FINAL_PYTHON"
echo "FINAL_SHELL_SYNTAX=$FINAL_SHELL"


# ======================================================================
# 26 SUMMARY
# ======================================================================

section "26. GENERAL AUDIT SUMMARY"

echo "SHORT_ID=$SID"
echo "MISSING_CORE_FILES=$MISSING_CORE"
echo "PYTHON_COMPILE_FAILURES=$COMPILE_FAIL"
echo "GERAR_SHORT_SYNTAX=$SHELL_STATUS"

if [ -d "$DIR" ]; then

    echo "MEDIA_TOTAL=$MEDIA_TOTAL"
    echo "BAD_SCENE_COUNTS=$BAD_SCENES"
    echo "SCENE_COLLISIONS=$COLLISIONS"

else

    echo "MEDIA_TOTAL=UNKNOWN"
    echo "BAD_SCENE_COUNTS=UNKNOWN"
    echo "SCENE_COLLISIONS=UNKNOWN"

fi

echo "CURRENT_SHORT_LOGS_WITH_ERRORS=$CURRENT_ERROR_FILES"
echo "FINAL_PYTHON_COMPILE=$FINAL_PYTHON"
echo "FINAL_SHELL_SYNTAX=$FINAL_SHELL"

echo
echo "AUDIT_COMPLETE=YES"
echo "CORE_FILES_MODIFIED=NO"
echo "MIDIA_PY_EXECUTED=NO"
echo "NETWORK_EXECUTED=NO"
echo "MEDIA_DOWNLOADED=NO"
echo "VIDEO_RENDERED=NO"
echo "TERMUX_CONTINUA_ABERTO=SIM"

echo
echo "FULL_REPORT=$OUT"
echo "======================================================================"
