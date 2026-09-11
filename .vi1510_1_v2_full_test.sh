#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || exit 90

mkdir -p \
logs/producao \
temp/vi1510_1 \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1510_1_v2_full_test.log"

: > "$LOG"


hash_file() {

    if [ -f "$1" ]; then

        sha256sum "$1" |
        awk '{print $1}'

    else

        echo "MISSING"

    fi
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
EXECUTOR0="$(hash_file vi6_95_scene_executor.py)"
V6_0="$(hash_file v6.py)"

MEDIA0="$(tree_hash imagens)"

MOTION0="$(
    find roteiros \
    -type f \
    -name 'motion_plan*.json' \
    -printf '%p|%s|%T@\n' \
    2>/dev/null |
    sort |
    sha256sum |
    awk '{print $1}'
)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1510.1 V2 FULL GENERALIZATION TEST" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== COMPILE 24-34 =====" |
tee -a "$LOG"


python -m py_compile \
vi1510_1_24_partitioned_resolver.py \
vi1510_1_25_scene_usage.py \
vi1510_1_26_evidence_text.py \
vi1510_1_27_source_metadata_v2.py \
vi1510_1_28_relevance_v2.py \
vi1510_1_29_lineage_v2.py \
vi1510_1_30_evidence_gate_v2.py \
vi1510_1_31_cross_topic_v3.py \
vi1510_1_32_regression_v2.py \
vi1510_1_33_architecture_v2.py \
vi1510_1_34_v2_pipeline.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


echo "COMPILE STATUS=$COMPILE" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== V2 REGRESSION =====" |
tee -a "$LOG"


python \
vi1510_1_32_regression_v2.py \
2>&1 |
tee -a "$LOG"

REGRESSION=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== V2 PIPELINE =====" |
tee -a "$LOG"


python \
vi1510_1_34_v2_pipeline.py \
2>&1 |
tee -a "$LOG"

PIPELINE=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== V2 ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1510_1_33_architecture_v2.py \
2>&1 |
tee -a "$LOG"

ARCHITECTURE=${PIPESTATUS[0]}


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
EXECUTOR1="$(hash_file vi6_95_scene_executor.py)"
V6_1="$(hash_file v6.py)"

MEDIA1="$(tree_hash imagens)"

MOTION1="$(
    find roteiros \
    -type f \
    -name 'motion_plan*.json' \
    -printf '%p|%s|%T@\n' \
    2>/dev/null |
    sort |
    sha256sum |
    awk '{print $1}'
)"


same() {

    [ "$1" = "$2" ] &&
    echo PASS ||
    echo FAIL
}


VIDEO_OK="$(same "$VIDEO0" "$VIDEO1")"
GERAR_OK="$(same "$GERAR0" "$GERAR1")"
ROTEIRO_OK="$(same "$ROTEIRO0" "$ROTEIRO1")"
EXECUTOR_OK="$(same "$EXECUTOR0" "$EXECUTOR1")"
V6_OK="$(same "$V6_0" "$V6_1")"
MEDIA_OK="$(same "$MEDIA0" "$MEDIA1")"
MOTION_OK="$(same "$MOTION0" "$MOTION1")"


{
echo
echo "=============================================="
echo " VI1510.1 CORE INTEGRITY"
echo "=============================================="

echo "VIDEO=$VIDEO_OK"
echo "GERAR=$GERAR_OK"
echo "ROTEIRO=$ROTEIRO_OK"
echo "EXECUTOR=$EXECUTOR_OK"
echo "V6=$V6_OK"
echo "MEDIA=$MEDIA_OK"
echo "MOTION_PLANS=$MOTION_OK"

} |
tee -a "$LOG"


FINAL=0


for value in \
"$COMPILE" \
"$REGRESSION" \
"$PIPELINE" \
"$ARCHITECTURE"
do

    if [ "$value" -ne 0 ]; then

        FINAL=1

    fi

done


for value in \
"$VIDEO_OK" \
"$GERAR_OK" \
"$ROTEIRO_OK" \
"$EXECUTOR_OK" \
"$V6_OK" \
"$MEDIA_OK" \
"$MOTION_OK"
do

    if [ "$value" != "PASS" ]; then

        FINAL=1

    fi

done


echo |
tee -a "$LOG"

echo "===== MACHINE RESULT =====" |
tee -a "$LOG"


python - <<'PY' 2>&1 |
tee -a "$LOG"
import json

from pathlib import Path


path = Path(
    "logs/producao/"
    "vi1510_1_v2_pipeline_latest.json"
)


try:

    gate = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )


except Exception:

    gate = {}


print(
    "PIPELINE =",
    gate.get(
        "status",
        "MISSING"
    )
)

print(
    "RESOLVED PARTITIONS =",
    gate.get(
        "resolved_partition_count"
    )
)

print(
    "SUCCESSFUL PARTITIONS =",
    gate.get(
        "successful_partition_count"
    )
)

print(
    "CERTIFIED PARTITIONS =",
    gate.get(
        "certified_partition_count"
    )
)

print(
    "CROSS TOPIC =",
    (
        gate.get(
            "cross_topic"
        )
        or {}
    ).get(
        "status"
    )
)

print(
    "BLOCKERS =",
    gate.get(
        "blockers"
    )
)


print()
print(
    "NETWORK EXECUTED: False"
)

print(
    "FFMPEG EXECUTED: False"
)

print(
    "VIDEO GENERATED: False"
)

print(
    "PRODUCTION MUTATED: False"
)
PY


echo |
tee -a "$LOG"


if [ "$FINAL" -eq 0 ]; then

    echo \
    "VI1510.1 RESULT: V2_GENERALIZATION_CERTIFIED" |
    tee -a "$LOG"

else

    echo \
    "VI1510.1 RESULT: HOLD_FOR_TARGETED_REPAIR" |
    tee -a "$LOG"

fi


echo "FINAL STATUS=$FINAL" |
tee -a "$LOG"


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1510_1_V2_Full_Test.txt" \
2>/dev/null


exit "$FINAL"
