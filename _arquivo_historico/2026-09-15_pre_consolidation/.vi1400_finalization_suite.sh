#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado"
    exit 90
}


mkdir -p \
temp/vi1400 \
logs/producao \
videos/canary/vi1400 \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1400_finalization_console.log"

: > "$LOG"


hash_file() {
    sha256sum "$1" \
    2>/dev/null |
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

V60="$(hash_file v6.py)"

EXEC0="$(hash_file vi6_95_scene_executor.py)"

MEDIA0="$(tree_hash imagens)"


run_stage() {
    NAME="$1"
    shift

    echo |
    tee -a "$LOG"

    echo "===== $NAME =====" |
    tee -a "$LOG"

    "$@" \
    2>&1 |
    tee -a "$LOG"

    return ${PIPESTATUS[0]}
}


echo "==============================================" |
tee -a "$LOG"

echo " VI1400 FINALIZATION SUITE" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


python -m py_compile \
vi1400_*.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


echo "COMPILE=$COMPILE" |
tee -a "$LOG"


run_stage \
"REGRESSION" \
python \
vi1400_14_regression.py

REG=$?


run_stage \
"DRY RUN + HUMAN-LIKE QA" \
python \
vi1400_17_dry_run.py

DRY=$?


run_stage \
"ARCHITECTURE" \
python \
vi1400_15_architecture_audit.py

ARCH=$?


run_stage \
"RELEASE GATE" \
python \
vi1400_18_release_gate.py

GATE=$?


READY="$(
python - <<'PY'
import json
from pathlib import Path

path = Path(
    "temp/vi1400/"
    "release_gate.json"
)

try:

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


    print(
        "YES"
        if data.get(
            "ready"
        )
        is True
        else "NO"
    )

except Exception:

    print(
        "NO"
    )
PY
)"


echo \
"READY_FOR_FINAL_CANARY=$READY" |
tee -a "$LOG"


POST=0

FINAL_AUDIT=0


if \
[ "$READY" = "YES" ] && \
[ "$COMPILE" -eq 0 ] && \
[ "$REG" -eq 0 ] && \
[ "$DRY" -eq 0 ] && \
[ "$ARCH" -eq 0 ]
then

    run_stage \
    "FINAL AUDIO POSTMASTER" \
    python \
    vi1400_19_postmaster.py

    POST=$?


    run_stage \
    "FINAL MASTER AUDIT" \
    python \
    vi1400_20_final_audit.py

    FINAL_AUDIT=$?

else

    echo |
    tee -a "$LOG"

    echo \
    "POSTMASTER SKIPPED BY QUALITY GATE" |
    tee -a "$LOG"

fi


VIDEO1="$(hash_file video.py)"

GERAR1="$(hash_file gerar_short.sh)"

ROTEIRO1="$(hash_file roteiro.py)"

V61="$(hash_file v6.py)"

EXEC1="$(hash_file vi6_95_scene_executor.py)"

MEDIA1="$(tree_hash imagens)"


same() {
    [ "$1" = "$2" ] &&
    echo PASS ||
    echo FAIL
}


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " CORE INTEGRITY" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo \
"VIDEO=$(same "$VIDEO0" "$VIDEO1")" |
tee -a "$LOG"

echo \
"GERAR=$(same "$GERAR0" "$GERAR1")" |
tee -a "$LOG"

echo \
"ROTEIRO=$(same "$ROTEIRO0" "$ROTEIRO1")" |
tee -a "$LOG"

echo \
"V6=$(same "$V60" "$V61")" |
tee -a "$LOG"

echo \
"EXECUTOR=$(same "$EXEC0" "$EXEC1")" |
tee -a "$LOG"

echo \
"PRODUCTION_MEDIA=$(same "$MEDIA0" "$MEDIA1")" |
tee -a "$LOG"


python - <<'PY' \
2>&1 |
tee -a "$LOG"

import json

from pathlib import Path


def read(
    name,
):
    path = (
        Path(
            "temp/vi1400"
        )
        /
        name
    )


    try:

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return {}


score = read(
    "score.json"
)

gate = read(
    "release_gate.json"
)

final = read(
    "final_audit.json"
)

rescue = read(
    "rescue_plan.json"
)


print()

print(
    "=============================================="
)

print(
    " VI1400 FINAL REPORT"
)

print(
    "=============================================="
)


print(
    "HUMAN_LIKE_SCORE =",
    score.get(
        "score"
    )
)


print(
    "QUALITY_WARNINGS =",
    score.get(
        "warnings"
    )
)


print(
    "QUALITY_BLOCKERS =",
    score.get(
        "blockers"
    )
)


print(
    "RELEASE_GATE =",
    gate.get(
        "status"
    )
)


print(
    "READY =",
    gate.get(
        "ready"
    )
)


print(
    "FINAL_AUDIT =",
    final.get(
        "status",
        "NOT_RUN"
    )
)


print(
    "RESCUE_DIRECTIVES =",
    len(
        (
            rescue.get(
                "directives"
            )
            or []
        )
    )
)


print(
    "NETWORK_EXECUTED = FALSE"
)

print(
    "DOWNLOAD_EXECUTED = FALSE"
)

print(
    "PRODUCTION_MUTATED = FALSE"
)

print(
    "PUBLICATION_EXECUTED = FALSE"
)
PY


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1400_Finalization_Report.txt" \
2>/dev/null


HARD=0


[ "$COMPILE" -ne 0 ] &&
HARD=1


[ "$REG" -ne 0 ] &&
HARD=1


[ "$DRY" -ne 0 ] &&
HARD=1


[ "$ARCH" -ne 0 ] &&
HARD=1


[ "$VIDEO0" != "$VIDEO1" ] &&
HARD=1


[ "$GERAR0" != "$GERAR1" ] &&
HARD=1


[ "$ROTEIRO0" != "$ROTEIRO1" ] &&
HARD=1


[ "$V60" != "$V61" ] &&
HARD=1


[ "$EXEC0" != "$EXEC1" ] &&
HARD=1


[ "$MEDIA0" != "$MEDIA1" ] &&
HARD=1


if [ "$READY" = "YES" ]; then

    [ "$POST" -ne 0 ] &&
    HARD=1


    [ "$FINAL_AUDIT" -ne 0 ] &&
    HARD=1

fi


echo |
tee -a "$LOG"


if [ "$HARD" -eq 0 ]; then

    if [ "$READY" = "YES" ]; then

        echo \
        "VI1400 FINAL: FINAL_RELEASE_CANDIDATE_CERTIFIED" |
        tee -a "$LOG"

    else

        echo \
        "VI1400 FINAL: SAFE_HOLD_EDITORIAL_REPAIR_REQUIRED" |
        tee -a "$LOG"

    fi


    echo \
    "FINAL STATUS=0" |
    tee -a "$LOG"


    exit 0

else

    echo \
    "VI1400 FINAL: TECHNICAL_HOLD" |
    tee -a "$LOG"


    echo \
    "FINAL STATUS=1" |
    tee -a "$LOG"


    exit 1

fi
