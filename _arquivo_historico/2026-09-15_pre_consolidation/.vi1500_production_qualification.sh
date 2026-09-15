#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado."
    exit 90
}


mkdir -p \
temp/vi1500 \
temp/vi1500/runs \
logs/producao \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1500_production_qualification.log"

: > "$LOG"


hash_file() {
    sha256sum "$1" 2>/dev/null |
    awk '{print $1}'
}


VIDEO0="$(hash_file video.py)"
GERAR0="$(hash_file gerar_short.sh)"
ROTEIRO0="$(hash_file roteiro.py)"
V60="$(hash_file v6.py)"
EXEC0="$(hash_file vi6_95_scene_executor.py)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1500 PRODUCTION QUALIFICATION SUITE" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1500_*.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


echo "COMPILE=$COMPILE" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== REGRESSION =====" |
tee -a "$LOG"


python \
vi1500_23_regression.py \
2>&1 |
tee -a "$LOG"

REGRESSION=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1500_22_architecture_audit.py \
2>&1 |
tee -a "$LOG"

ARCHITECTURE=${PIPESTATUS[0]}


TOPICS=99


if \
[ "$COMPILE" -eq 0 ] && \
[ "$REGRESSION" -eq 0 ] && \
[ "$ARCHITECTURE" -eq 0 ]
then

    echo |
    tee -a "$LOG"

    echo "===== THREE-TOPIC BLIND QUALIFICATION =====" |
    tee -a "$LOG"


    python \
    vi1500_24_topic_runner.py \
    --all \
    2>&1 |
    tee -a "$LOG"

    TOPICS=${PIPESTATUS[0]}

fi


echo |
tee -a "$LOG"

echo "===== CROSS-TOPIC AUDIT =====" |
tee -a "$LOG"


python \
vi1500_20_cross_topic_audit.py \
2>&1 |
tee -a "$LOG"

CROSS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== GENERALIZATION REPORT =====" |
tee -a "$LOG"


python \
vi1500_21_generalization_report.py \
2>&1 |
tee -a "$LOG"

GENERALIZATION=${PIPESTATUS[0]}


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
V61="$(hash_file v6.py)"
EXEC1="$(hash_file vi6_95_scene_executor.py)"


same() {
    [ "$1" = "$2" ] &&
    echo PASS ||
    echo FAIL
}


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " VI1500 CORE INTEGRITY" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


VIDEO_OK="$(same "$VIDEO0" "$VIDEO1")"
GERAR_OK="$(same "$GERAR0" "$GERAR1")"
ROTEIRO_OK="$(same "$ROTEIRO0" "$ROTEIRO1")"
V6_OK="$(same "$V60" "$V61")"
EXEC_OK="$(same "$EXEC0" "$EXEC1")"


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


python - <<'PY' \
2>&1 |
tee -a "$LOG"

import json

from pathlib import Path


base = Path(
    "temp/vi1500"
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
    "cross_topic_audit.json"
)

general = read(
    "generalization_report.json"
)


print()

print(
    "=============================================="
)

print(
    " VI1500 FINAL QUALIFICATION"
)

print(
    "=============================================="
)


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
    general.get(
        "average_score"
    )
)


print(
    "INTERPRETATION =",
    general.get(
        "interpretation"
    )
)


print(
    "FALSE RELEASES =",
    general.get(
        "false_releases"
    )
)


print(
    "BENCHMARK CONTAMINATION =",
    general.get(
        "benchmark_contamination"
    )
)


print(
    "CORE DRIFT =",
    general.get(
        "core_drift"
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
    "CORE_MUTATION_ALLOWED = FALSE"
)
PY


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1500_Production_Qualification.txt" \
2>/dev/null


TECHNICAL=0


[ "$COMPILE" -ne 0 ] &&
TECHNICAL=1


[ "$REGRESSION" -ne 0 ] &&
TECHNICAL=1


[ "$ARCHITECTURE" -ne 0 ] &&
TECHNICAL=1


[ "$TOPICS" -ne 0 ] &&
TECHNICAL=1


[ "$CROSS" -ne 0 ] &&
TECHNICAL=1


[ "$GENERALIZATION" -ne 0 ] &&
TECHNICAL=1


[ "$VIDEO_OK" != "PASS" ] &&
TECHNICAL=1


[ "$GERAR_OK" != "PASS" ] &&
TECHNICAL=1


[ "$ROTEIRO_OK" != "PASS" ] &&
TECHNICAL=1


[ "$V6_OK" != "PASS" ] &&
TECHNICAL=1


[ "$EXEC_OK" != "PASS" ] &&
TECHNICAL=1


echo |
tee -a "$LOG"


if [ "$TECHNICAL" -eq 0 ]; then

    echo \
    "VI1500 SUITE: TECHNICALLY CERTIFIED" |
    tee -a "$LOG"

    echo \
    "FINAL STATUS=0" |
    tee -a "$LOG"

    exit 0

else

    echo \
    "VI1500 SUITE: TECHNICAL HOLD" |
    tee -a "$LOG"

    echo \
    "FINAL STATUS=1" |
    tee -a "$LOG"

    exit 1

fi
