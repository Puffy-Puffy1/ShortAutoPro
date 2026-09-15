#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado"
    exit 90
}


mkdir -p \
temp/vi1510 \
temp/vi1510/runs \
logs/producao \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1510_generalization_repair.log"

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

echo " VI1510 GENERALIZATION REPAIR SUITE" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


python -m py_compile \
vi1510_*.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


echo "COMPILE=$COMPILE" |
tee -a "$LOG"


run_stage \
"REGRESSION" \
python \
vi1510_22_regression.py

REG=$?


run_stage \
"ARCHITECTURE" \
python \
vi1510_23_architecture_audit.py

ARCH=$?


run_stage \
"BENCHMARK FINGERPRINT BANK" \
python \
vi1510_02_benchmark_bank.py

BANK=$?


run_stage \
"RESOLVE VI1500 RUNS" \
python \
vi1510_03_run_resolver.py

RESOLVE=$?


run_stage \
"REAUDIT EXISTING A/B/C" \
python \
vi1510_18_reaudit_engine.py

REAUDIT=$?


run_stage \
"CROSS-TOPIC V2" \
python \
vi1510_19_cross_topic_audit.py

CROSS=$?


run_stage \
"VI1500 VS VI1510" \
python \
vi1510_20_comparison.py

COMPARE=$?


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


VIDEO_OK="$(same "$VIDEO0" "$VIDEO1")"
GERAR_OK="$(same "$GERAR0" "$GERAR1")"
ROTEIRO_OK="$(same "$ROTEIRO0" "$ROTEIRO1")"
V6_OK="$(same "$V60" "$V61")"
EXEC_OK="$(same "$EXEC0" "$EXEC1")"
MEDIA_OK="$(same "$MEDIA0" "$MEDIA1")"


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " VI1510 CORE INTEGRITY" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "VIDEO=$VIDEO_OK" |
tee -a "$LOG"

echo "GERAR=$GERAR_OK" |
tee -a "$LOG"

echo "ROTEIRO=$ROTEIRO_OK" |
tee -a "$LOG"

echo "V6=$V6_OK" |
tee -a "$LOG"

echo "EXECUTOR=$EXEC_OK" |
tee -a "$LOG"

echo "PRODUCTION_MEDIA=$MEDIA_OK" |
tee -a "$LOG"


python - <<'PY' \
2>&1 |
tee -a "$LOG"

import json

from pathlib import Path


base = Path(
    "temp/vi1510"
)


def read(
    name
):
    path = (
        base
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


cross = read(
    "cross_topic_v2.json"
)

comparison = read(
    "vi1500_vs_vi1510.json"
)


print()

print(
    "=============================================="
)

print(
    " VI1510 FINAL REPORT"
)

print(
    "=============================================="
)


for item in cross.get(
    "results",
    []
):

    print(
        "TOPIC",
        item.get(
            "label"
        ),
        "|",
        item.get(
            "status"
        ),
        "| SCORE",
        item.get(
            "score"
        ),
        "| ASSETS",
        item.get(
            "assets"
        ),
        "| UNIQUE",
        item.get(
            "unique_assets"
        ),
        "| SOURCES",
        item.get(
            "source_records"
        ),
        "| COVERAGE",
        item.get(
            "provenance_coverage"
        )
    )


    print(
        "  BLOCKERS =",
        item.get(
            "blockers"
        )
    )


    print(
        "  CONTROL REFERENCES =",
        item.get(
            "control_plane_references"
        )
    )


print()

print(
    "STATUS =",
    cross.get(
        "status",
        "MISSING"
    )
)


print(
    "RELEASES =",
    cross.get(
        "release_count"
    )
)


print(
    "SAFE HOLDS =",
    cross.get(
        "safe_hold_count"
    )
)


print(
    "AVERAGE SCORE =",
    cross.get(
        "average_score"
    )
)


print(
    "REAL CONTENT LEAKS =",
    cross.get(
        "real_content_leaks"
    )
)


print(
    "FALSE RELEASES =",
    cross.get(
        "false_release_count"
    )
)


print()

print(
    "PUBLICATION_EXECUTED = FALSE"
)

print(
    "UPLOAD_EXECUTED = FALSE"
)

print(
    "NEW_VIDEO_GENERATED = FALSE"
)

print(
    "PRODUCTION_MUTATED = FALSE"
)
PY


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1510_Generalization_Repair.txt" \
2>/dev/null


TECH=0


[ "$COMPILE" -ne 0 ] &&
TECH=1

[ "$REG" -ne 0 ] &&
TECH=1

[ "$ARCH" -ne 0 ] &&
TECH=1

[ "$BANK" -ne 0 ] &&
TECH=1

[ "$RESOLVE" -ne 0 ] &&
TECH=1

[ "$REAUDIT" -ne 0 ] &&
TECH=1

[ "$CROSS" -ne 0 ] &&
TECH=1

[ "$COMPARE" -ne 0 ] &&
TECH=1

[ "$VIDEO_OK" != "PASS" ] &&
TECH=1

[ "$GERAR_OK" != "PASS" ] &&
TECH=1

[ "$ROTEIRO_OK" != "PASS" ] &&
TECH=1

[ "$V6_OK" != "PASS" ] &&
TECH=1

[ "$EXEC_OK" != "PASS" ] &&
TECH=1

[ "$MEDIA_OK" != "PASS" ] &&
TECH=1


if [ "$TECH" -eq 0 ]; then

    echo |
    tee -a "$LOG"

    echo \
    "VI1510 SUITE: TECHNICALLY CERTIFIED" |
    tee -a "$LOG"

    echo \
    "FINAL STATUS=0" |
    tee -a "$LOG"

    exit 0

else

    echo |
    tee -a "$LOG"

    echo \
    "VI1510 SUITE: TECHNICAL HOLD" |
    tee -a "$LOG"

    echo \
    "FINAL STATUS=1" |
    tee -a "$LOG"

    exit 1

fi
