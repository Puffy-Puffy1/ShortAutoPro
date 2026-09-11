#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1

LOG="logs/producao/vi1000_1_1_certification_console.log"

mkdir -p \
logs/producao \
"$HOME/storage/downloads"


VIDEO0="$(
sha256sum video.py |
awk '{print $1}'
)"

GERAR0="$(
sha256sum gerar_short.sh |
awk '{print $1}'
)"

ROTEIRO0="$(
sha256sum roteiro.py |
awk '{print $1}'
)"

EXECUTOR0="$(
sha256sum vi6_95_scene_executor.py |
awk '{print $1}'
)"


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
find roteiros \
-type f \
-name 'motion_plan_*.json' \
-printf '%p|%s|%T@\n' \
2>/dev/null |
sort |
sha256sum |
awk '{print $1}'
)"


{
echo
echo "=============================================="
echo " VI1000.1.1 FINAL CERTIFICATION"
echo "=============================================="

echo
echo "===== COMPILE ====="

python -m py_compile \
vi1000_1_semantic_core.py \
vi1000_1_query_gate.py \
vi1000_1_adversarial_suite.py \
vi1000_1_full_dry_run.py \
vi1000_1_architecture_audit.py \
vi1000_runtime.py \
vi1000_command_hook.py || exit 10

echo "COMPILE: PASS"


echo
echo "===== ADVERSARIAL TRUTH ====="

python \
vi1000_1_adversarial_suite.py || exit 11


echo
echo "===== GENERAL FULL DRY-RUN ====="

python \
vi1000_1_full_dry_run.py || exit 12


echo
echo "===== ARCHITECTURE ====="

python \
vi1000_1_architecture_audit.py || exit 13

} 2>&1 | tee "$LOG"

RUN_STATUS=${PIPESTATUS[0]}


VIDEO1="$(
sha256sum video.py |
awk '{print $1}'
)"

GERAR1="$(
sha256sum gerar_short.sh |
awk '{print $1}'
)"

ROTEIRO1="$(
sha256sum roteiro.py |
awk '{print $1}'
)"

EXECUTOR1="$(
sha256sum vi6_95_scene_executor.py |
awk '{print $1}'
)"


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
find roteiros \
-type f \
-name 'motion_plan_*.json' \
-printf '%p|%s|%T@\n' \
2>/dev/null |
sort |
sha256sum |
awk '{print $1}'
)"


VIDEO_OK=False
GERAR_OK=False
ROTEIRO_OK=False
EXECUTOR_OK=False
MEDIA_OK=False
MOTION_OK=False


[ "$VIDEO0" = "$VIDEO1" ] && VIDEO_OK=True
[ "$GERAR0" = "$GERAR1" ] && GERAR_OK=True
[ "$ROTEIRO0" = "$ROTEIRO1" ] && ROTEIRO_OK=True
[ "$EXECUTOR0" = "$EXECUTOR1" ] && EXECUTOR_OK=True
[ "$MEDIA0" = "$MEDIA1" ] && MEDIA_OK=True
[ "$MOTION0" = "$MOTION1" ] && MOTION_OK=True


{
echo
echo "=============================================="
echo " VI1000.1.1 CORE INTEGRITY"
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


echo
echo "===== MACHINE CERTIFICATION ====="

export VI1000_1_1_RUN_STATUS="$RUN_STATUS"
export VI1000_1_1_VIDEO_OK="$VIDEO_OK"
export VI1000_1_1_GERAR_OK="$GERAR_OK"
export VI1000_1_1_ROTEIRO_OK="$ROTEIRO_OK"
export VI1000_1_1_EXECUTOR_OK="$EXECUTOR_OK"
export VI1000_1_1_MEDIA_OK="$MEDIA_OK"
export VI1000_1_1_MOTION_OK="$MOTION_OK"


python - <<'PY'
import json
import os

from pathlib import Path


targets = {
    "ADVERSARIAL":
        (
            Path(
                "logs/producao/"
                "vi1000_1_adversarial_suite_latest.json"
            ),
            "VI1000_1_ADVERSARIAL_CERTIFIED"
        ),

    "DRY_RUN":
        (
            Path(
                "logs/producao/"
                "vi1000_1_full_dry_run_latest.json"
            ),
            "VI1000_1_FULL_DRY_RUN_CERTIFIED"
        ),

    "ARCHITECTURE":
        (
            Path(
                "logs/producao/"
                "vi1000_1_architecture_audit_latest.json"
            ),
            "VI1000_1_ARCHITECTURE_CERTIFIED"
        ),
}


statuses = {}

certified = True


for name, (
    path,
    expected
) in targets.items():

    if not path.exists():

        status = "MISSING"

    else:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        ).get(
            "gate",
            {}
        )

        status = data.get(
            "status",
            "UNKNOWN"
        )


    statuses[
        name
    ] = status


    print(
        name,
        "=",
        status
    )


    if status != expected:
        certified = False


integrity = {
    "VIDEO":
        os.environ[
            "VI1000_1_1_VIDEO_OK"
        ] == "True",

    "GERAR":
        os.environ[
            "VI1000_1_1_GERAR_OK"
        ] == "True",

    "ROTEIRO":
        os.environ[
            "VI1000_1_1_ROTEIRO_OK"
        ] == "True",

    "EXECUTOR":
        os.environ[
            "VI1000_1_1_EXECUTOR_OK"
        ] == "True",

    "MEDIA":
        os.environ[
            "VI1000_1_1_MEDIA_OK"
        ] == "True",

    "MOTION_PLANS":
        os.environ[
            "VI1000_1_1_MOTION_OK"
        ] == "True",
}


if not all(
    integrity.values()
):
    certified = False


run_status = int(
    os.environ[
        "VI1000_1_1_RUN_STATUS"
    ]
)


if run_status != 0:
    certified = False


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
        "VI1000.1.1 RESULT: "
        "READY_FOR_GENERAL_PIPELINE_TEST"
    )

    raise SystemExit(
        0
    )


print(
    "VI1000.1.1 RESULT: HOLD"
)

raise SystemExit(
    1
)
PY

CERT_STATUS=$?


echo
echo "CERTIFICATION EXIT STATUS=$CERT_STATUS"

# Preserve the machine-certification status as the
# exit status of the left side of the pipeline.
exit "$CERT_STATUS"

} 2>&1 | tee -a "$LOG"

# IMPORTANT:
# Capture PIPESTATUS immediately. Any command executed
# before this line would overwrite PIPESTATUS.
CERT_STATUS=${PIPESTATUS[0]}


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1000_1_1_Certification.txt" \
2>/dev/null || true


if [ "$CERT_STATUS" -ne 0 ]; then
    exit "$CERT_STATUS"
fi

exit 0
