#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || return 1

REPORT="temp/VSE421_GENERAL_AUDIT.txt"

mkdir -p temp

{
echo "============================================================"
echo " SHORTAUTOPRO VSE4.2.1 GENERAL AUDIT"
echo "============================================================"
echo "DATE=$(date)"
echo


echo "============================================================"
echo " 1. CERTIFICATES"
echo "============================================================"

for F in \
temp/VSE421_SEMANTIC_CERTIFIED \
temp/VSE421_MIDIA_CERTIFIED
do

    if [ -f "$F" ]; then
        echo "$(basename "$F")=PASS"
    else
        echo "$(basename "$F")=FAIL"
    fi

done


echo
echo "============================================================"
echo " 2. ROOT PYTHON COMPILE"
echo "============================================================"

PY_BAD=0
PY_COUNT=0

for F in ./*.py
do

    [ -f "$F" ] || continue

    PY_COUNT=$((PY_COUNT + 1))

    python -m py_compile "$F" \
    >/dev/null 2>&1

    STATUS=$?

    if [ "$STATUS" -ne 0 ]; then

        echo "PYTHON_FAIL=$F"
        PY_BAD=$((PY_BAD + 1))

    fi

done

echo "PYTHON_FILES=$PY_COUNT"
echo "PYTHON_FAILURES=$PY_BAD"


echo
echo "============================================================"
echo " 3. ROOT SHELL SYNTAX"
echo "============================================================"

SH_BAD=0
SH_COUNT=0

for F in ./*.sh
do

    [ -f "$F" ] || continue

    SH_COUNT=$((SH_COUNT + 1))

    bash -n "$F" \
    >/dev/null 2>&1

    STATUS=$?

    if [ "$STATUS" -ne 0 ]; then

        echo "SHELL_FAIL=$F"
        SH_BAD=$((SH_BAD + 1))

    fi

done

echo "SHELL_FILES=$SH_COUNT"
echo "SHELL_FAILURES=$SH_BAD"


echo
echo "============================================================"
echo " 4. VSE4 SELF TEST"
echo "============================================================"

python \
visual_selection_engine_v4.py \
>/tmp_vse421_audit.log 2>&1

VSE=$?

cat /tmp_vse421_audit.log 2>/dev/null

rm -f /tmp_vse421_audit.log

echo "VSE4_SELF_TEST_STATUS=$VSE"


echo
echo "============================================================"
echo " 5. PROVIDER ACQUISITION"
echo "============================================================"

python - <<'PY'
from pathlib import Path
import ast

src = Path(
    "midia.py"
).read_text(
    encoding="utf-8"
)

tree = ast.parse(src)


required = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}


defined = {
    n.name
    for n in tree.body
    if isinstance(
        n,
        ast.FunctionDef,
    )
}


buscar = next(
    (
        n
        for n in tree.body
        if isinstance(
            n,
            ast.FunctionDef,
        )
        and
        n.name
        ==
        "buscar_todos_candidatos"
    ),
    None,
)


calls = set()


if buscar:

    for n in ast.walk(
        buscar
    ):

        if isinstance(
            n,
            ast.Call,
        ):

            if isinstance(
                n.func,
                ast.Name,
            ):

                calls.add(
                    n.func.id
                )


for name in sorted(
    required
):

    print(
        f"PROVIDER_DEF_{name}="
        f"{'PASS' if name in defined else 'FAIL'}"
    )

    print(
        f"PROVIDER_CALL_{name}="
        f"{'PASS' if name in calls else 'FAIL'}"
    )


missing_defs = (
    required
    -
    defined
)

missing_calls = (
    required
    -
    calls
)


if (
    not missing_defs
    and
    not missing_calls
):

    print(
        "PROVIDER_ACQUISITION_STRUCTURE=PASS"
    )

else:

    print(
        "PROVIDER_ACQUISITION_STRUCTURE=FAIL"
    )

    raise SystemExit(1)
PY

PROVIDERS=$?


echo
echo "============================================================"
echo " 6. SUCCESS PATHS"
echo "============================================================"

python - <<'PY'
from pathlib import Path
import ast

src = Path(
    "midia.py"
).read_text(
    encoding="utf-8"
)

tree = ast.parse(src)

parents = {}


for parent in ast.walk(tree):

    for child in ast.iter_child_nodes(
        parent
    ):

        parents[
            child
        ] = parent


def loop_parent(node):

    p = parents.get(
        node
    )

    while p:

        if isinstance(
            p,
            (
                ast.For,
                ast.While,
            ),
        ):

            return p

        p = parents.get(
            p
        )

    return None


def success(body):

    for stmt in body:

        for n in ast.walk(
            stmt
        ):

            if not isinstance(
                n,
                ast.Assign,
            ):
                continue

            if not (
                isinstance(
                    n.value,
                    ast.Constant,
                )
                and
                n.value.value is True
            ):
                continue

            for target in n.targets:

                if (
                    isinstance(
                        target,
                        ast.Name,
                    )
                    and
                    target.id
                    ==
                    "sucesso"
                ):

                    return True

    return False


lines = src.splitlines()

bad = []
total = 0


for node in ast.walk(tree):

    if not (
        isinstance(
            node,
            ast.If,
        )
        and
        loop_parent(node)
        and
        success(node.body)
    ):

        continue


    total += 1


    text = "\n".join(
        lines[
            node.body[0].lineno - 1:
            node.body[-1].end_lineno
        ]
    )


    cleanup = (
        "_vse42_cleanup_scene_sibling"
        in text
    )

    commit = (
        "_vse42_commit_candidate"
        in text
        or
        "_vse42_commit_safe"
        in text
    )

    break_ok = isinstance(
        node.body[-1],
        ast.Break,
    )


    print(
        f"SUCCESS_LINE={node.lineno} "
        f"CLEANUP={cleanup} "
        f"COMMIT={commit} "
        f"BREAK={break_ok}"
    )


    if not (
        cleanup
        and
        commit
        and
        break_ok
    ):

        bad.append(
            node.lineno
        )


print(
    "SUCCESS_PATH_TOTAL=",
    total
)


if bad:

    print(
        "SUCCESS_PATH_BAD="
        +
        ",".join(
            map(
                str,
                bad
            )
        )
    )

    raise SystemExit(1)


print(
    "SUCCESS_PATH_BAD=NONE"
)

print(
    "SUCCESS_PATH_AUDIT=PASS"
)
PY

SUCCESS=$?


echo
echo "============================================================"
echo " 7. OPTIONAL CURRENT MEDIA"
echo "============================================================"

SID="${SHORT_ID:-}"

if [ -z "$SID" ]; then

    LAST_DIR="$(
        find imagens \
        -maxdepth 1 \
        -type d \
        -name 'short_*' \
        2>/dev/null |
        sort |
        tail -n 1
    )"

    if [ -n "$LAST_DIR" ]; then
        SID="${LAST_DIR##*/short_}"
    fi

fi


if [ -n "$SID" ] &&
   [ -d "imagens/short_$SID" ]
then

    echo "MEDIA_SHORT_ID=$SID"

    MEDIA_TOTAL=0
    MEDIA_BAD=0

    for N in $(seq -w 1 12)
    do

        COUNT="$(
            find \
            "imagens/short_$SID" \
            -maxdepth 1 \
            -type f \
            -name "scene_${N}.*" \
            2>/dev/null |
            wc -l
        )"

        echo "SCENE_${N}_COUNT=$COUNT"

        MEDIA_TOTAL=$(
            (
                MEDIA_TOTAL
                +
                COUNT
            )
        )

        if [ "$COUNT" -ne 1 ]; then
            MEDIA_BAD=$((MEDIA_BAD + 1))
        fi

    done

    echo "MEDIA_TOTAL=$MEDIA_TOTAL"
    echo "MEDIA_BAD_SCENES=$MEDIA_BAD"

else

    echo "MEDIA_CHECK=SKIPPED"

fi


echo
echo "============================================================"
echo " FINAL"
echo "============================================================"

echo "PYTHON_FAILURES=$PY_BAD"
echo "SHELL_FAILURES=$SH_BAD"
echo "VSE4_SELF_TEST_STATUS=$VSE"
echo "PROVIDER_STATUS=$PROVIDERS"
echo "SUCCESS_PATH_STATUS=$SUCCESS"


if \
[ "$PY_BAD" -eq 0 ] &&
[ "$SH_BAD" -eq 0 ] &&
[ "$VSE" -eq 0 ] &&
[ "$PROVIDERS" -eq 0 ] &&
[ "$SUCCESS" -eq 0 ] &&
[ -f temp/VSE421_SEMANTIC_CERTIFIED ] &&
[ -f temp/VSE421_MIDIA_CERTIFIED ]
then

    echo
    echo "VSE421_FULL_CERTIFIED=PASS"

else

    echo
    echo "VSE421_FULL_CERTIFIED=FAIL"

fi


echo
echo "NETWORK_EXECUTED=NO"
echo "MEDIA_DOWNLOADED=NO"
echo "VIDEO_RENDERED=NO"
echo "TERMUX_CONTINUA_ABERTO=SIM"

} 2>&1 | tee "$REPORT"

echo
echo "REPORT=$REPORT"
