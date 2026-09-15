#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || {
    echo "ShortAutoPro não encontrado."
    exit 90
}


mkdir -p \
logs/producao \
temp/vi1100_general \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1100_1_general_pipeline_console.log"

CERT_TMP="$HOME/ShortAutoPro/temp/vi1100_general/final_certification.txt"


: > "$LOG"


hash_file() {
    sha256sum "$1" 2>/dev/null |
    awk '{print $1}'
}


tree_hash() {
    local ROOT="$1"
    local PATTERN="$2"

    find "$ROOT" \
    -type f \
    -name "$PATTERN" \
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

MEDIA0="$(
find imagens \
-type f \
-printf '%p|%s|%T@\n' \
2>/dev/null |
sort |
sha256sum |
awk '{print $1}'
)"

MOTION0="$(
tree_hash \
roteiros \
'motion_plan_*.json'
)"


echo \
"==============================================" |
tee -a "$LOG"

echo \
" VI1100.1 GENERAL PIPELINE CERTIFICATION" |
tee -a "$LOG"

echo \
"==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo \
"===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1000_1_semantic_core.py \
vi1000_1_query_gate.py \
vi1000_runtime.py \
vi1000_command_hook.py \
vi1000_1_adversarial_suite.py \
vi1100_00_general_pipeline_test.py \
vi1100_01_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE_STATUS=${PIPESTATUS[0]}


echo \
"COMPILE STATUS=$COMPILE_STATUS" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo \
"===== ADVERSARIAL TRUTH =====" |
tee -a "$LOG"


python \
vi1000_1_adversarial_suite.py \
2>&1 |
tee -a "$LOG"

ADV_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo \
"===== GENERAL PIPELINE =====" |
tee -a "$LOG"


python \
vi1100_00_general_pipeline_test.py \
2>&1 |
tee -a "$LOG"

PIPELINE_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo \
"===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1100_01_architecture_audit.py \
2>&1 |
tee -a "$LOG"

ARCH_STATUS=${PIPESTATUS[0]}


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
EXECUTOR1="$(hash_file vi6_95_scene_executor.py)"
V6_1="$(hash_file v6.py)"

MEDIA1="$(
find imagens \
-type f \
-printf '%p|%s|%T@\n' \
2>/dev/null |
sort |
sha256sum |
awk '{print $1}'
)"

MOTION1="$(
tree_hash \
roteiros \
'motion_plan_*.json'
)"


VIDEO_OK=False
GERAR_OK=False
ROTEIRO_OK=False
EXECUTOR_OK=False
V6_OK=False
MEDIA_OK=False
MOTION_OK=False


[ "$VIDEO0" = "$VIDEO1" ] && VIDEO_OK=True
[ "$GERAR0" = "$GERAR1" ] && GERAR_OK=True
[ "$ROTEIRO0" = "$ROTEIRO1" ] && ROTEIRO_OK=True
[ "$EXECUTOR0" = "$EXECUTOR1" ] && EXECUTOR_OK=True
[ "$V6_0" = "$V6_1" ] && V6_OK=True
[ "$MEDIA0" = "$MEDIA1" ] && MEDIA_OK=True
[ "$MOTION0" = "$MOTION1" ] && MOTION_OK=True


{
echo
echo "=============================================="
echo " VI1100.1 CORE INTEGRITY"
echo "=============================================="

echo \
"VIDEO=$(
[ "$VIDEO_OK" = True ] &&
echo PASS ||
echo FAIL
)"

echo \
"GERAR=$(
[ "$GERAR_OK" = True ] &&
echo PASS ||
echo FAIL
)"

echo \
"ROTEIRO=$(
[ "$ROTEIRO_OK" = True ] &&
echo PASS ||
echo FAIL
)"

echo \
"EXECUTOR=$(
[ "$EXECUTOR_OK" = True ] &&
echo PASS ||
echo FAIL
)"

echo \
"V6=$(
[ "$V6_OK" = True ] &&
echo PASS ||
echo FAIL
)"

echo \
"MEDIA=$(
[ "$MEDIA_OK" = True ] &&
echo PASS ||
echo FAIL
)"

echo \
"MOTION_PLANS=$(
[ "$MOTION_OK" = True ] &&
echo PASS ||
echo FAIL
)"
} |
tee -a "$LOG"


export VI1100_1_COMPILE_STATUS="$COMPILE_STATUS"
export VI1100_1_ADV_STATUS="$ADV_STATUS"
export VI1100_1_PIPELINE_STATUS="$PIPELINE_STATUS"
export VI1100_1_ARCH_STATUS="$ARCH_STATUS"

export VI1100_1_VIDEO_OK="$VIDEO_OK"
export VI1100_1_GERAR_OK="$GERAR_OK"
export VI1100_1_ROTEIRO_OK="$ROTEIRO_OK"
export VI1100_1_EXECUTOR_OK="$EXECUTOR_OK"
export VI1100_1_V6_OK="$V6_OK"
export VI1100_1_MEDIA_OK="$MEDIA_OK"
export VI1100_1_MOTION_OK="$MOTION_OK"


echo |
tee -a "$LOG"

echo \
"===== FINAL MACHINE CERTIFICATION =====" |
tee -a "$LOG"


python - <<'PY' > "$CERT_TMP" 2>&1
import json
import os

from pathlib import Path


targets = {
    "ADVERSARIAL": (
        Path(
            "logs/producao/"
            "vi1000_1_adversarial_suite_latest.json"
        ),
        "VI1000_1_ADVERSARIAL_CERTIFIED"
    ),

    "PIPELINE": (
        Path(
            "logs/producao/"
            "vi1100_00_general_pipeline_test_latest.json"
        ),
        "VI1100_GENERAL_PIPELINE_CERTIFIED"
    ),

    "ARCHITECTURE": (
        Path(
            "logs/producao/"
            "vi1100_01_architecture_audit_latest.json"
        ),
        "VI1100_ARCHITECTURE_CERTIFIED"
    ),
}


statuses = {}

certified = True


for name, (
    path,
    expected
) in targets.items():

    if not path.exists():
        current = "MISSING"

    else:
        try:
            current = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            ).get(
                "gate",
                {}
            ).get(
                "status",
                "UNKNOWN"
            )

        except Exception:
            current = (
                "INVALID_JSON"
            )


    statuses[
        name
    ] = current


    print(
        name,
        "=",
        current
    )


    if current != expected:
        certified = False


processes = {
    "COMPILE":
        int(
            os.environ.get(
                "VI1100_1_COMPILE_STATUS",
                "99"
            )
        ),

    "ADVERSARIAL":
        int(
            os.environ.get(
                "VI1100_1_ADV_STATUS",
                "99"
            )
        ),

    "PIPELINE":
        int(
            os.environ.get(
                "VI1100_1_PIPELINE_STATUS",
                "99"
            )
        ),

    "ARCHITECTURE":
        int(
            os.environ.get(
                "VI1100_1_ARCH_STATUS",
                "99"
            )
        ),
}


integrity = {
    "VIDEO":
        os.environ.get(
            "VI1100_1_VIDEO_OK"
        )
        == "True",

    "GERAR":
        os.environ.get(
            "VI1100_1_GERAR_OK"
        )
        == "True",

    "ROTEIRO":
        os.environ.get(
            "VI1100_1_ROTEIRO_OK"
        )
        == "True",

    "EXECUTOR":
        os.environ.get(
            "VI1100_1_EXECUTOR_OK"
        )
        == "True",

    "V6":
        os.environ.get(
            "VI1100_1_V6_OK"
        )
        == "True",

    "MEDIA":
        os.environ.get(
            "VI1100_1_MEDIA_OK"
        )
        == "True",

    "MOTION_PLANS":
        os.environ.get(
            "VI1100_1_MOTION_OK"
        )
        == "True",
}


if not all(
    value == 0
    for value in (
        processes.values()
    )
):
    certified = False


if not all(
    integrity.values()
):
    certified = False


print()
print(
    "PROCESS STATUS:",
    processes
)

print(
    "CORE INTEGRITY:",
    integrity
)


print()
print(
    "NETWORK EXECUTED: False"
)

print(
    "DOWNLOADS EXECUTED: False"
)

print(
    "FFMPEG EXECUTED: False"
)

print(
    "VIDEO GENERATED: False"
)

print(
    "RENDERER ACTIVATED: False"
)

print(
    "REAL BATCH GENERATED: 0"
)

print()


if certified:
    print(
        "VI1100.1 RESULT: "
        "READY_FOR_CONTROLLED_REAL_PIPELINE_TEST"
    )

    raise SystemExit(
        0
    )


print(
    "VI1100.1 RESULT: HOLD"
)

raise SystemExit(
    1
)
PY


FINAL_STATUS=$?


cat "$CERT_TMP" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo \
"FINAL STATUS=$FINAL_STATUS" |
tee -a "$LOG"


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1100_1_General_Pipeline_Test.txt" \
2>/dev/null


exit "$FINAL_STATUS"
