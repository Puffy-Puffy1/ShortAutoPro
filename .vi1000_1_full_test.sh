#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1


LOG="logs/producao/vi1000_1_full_test_console.log"

mkdir -p \
logs/producao \
temp/vi1000_1_dry_run


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
echo " VI1000.1 GENERAL INTELLIGENCE HARDENING"
echo "=============================================="


echo
echo "===== COMPILE ====="

python -m py_compile \
vi1000_1_semantic_core.py \
vi1000_1_query_gate.py \
vi1000_1_adversarial_suite.py \
vi1000_1_full_dry_run.py \
vi1000_1_architecture_audit.py || exit 10

echo "COMPILE: PASS"


echo
echo "===== ADVERSARIAL ====="

python \
vi1000_1_adversarial_suite.py || exit 11


echo
echo "===== FULL DRY-RUN ====="

python \
vi1000_1_full_dry_run.py || exit 12


echo
echo "===== ARCHITECTURE ====="

python \
vi1000_1_architecture_audit.py || exit 13

} 2>&1 | tee "$LOG"

STATUS=${PIPESTATUS[0]}


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


{
echo
echo "=============================================="
echo " VI1000.1 CORE INTEGRITY"
echo "=============================================="


echo \
"VIDEO=$(
[ "$VIDEO0" = "$VIDEO1" ] &&
echo PASS ||
echo FAIL
)"


echo \
"GERAR=$(
[ "$GERAR0" = "$GERAR1" ] &&
echo PASS ||
echo FAIL
)"


echo \
"ROTEIRO=$(
[ "$ROTEIRO0" = "$ROTEIRO1" ] &&
echo PASS ||
echo FAIL
)"


echo \
"EXECUTOR=$(
[ "$EXECUTOR0" = "$EXECUTOR1" ] &&
echo PASS ||
echo FAIL
)"


echo \
"MEDIA=$(
[ "$MEDIA0" = "$MEDIA1" ] &&
echo PASS ||
echo FAIL
)"


echo \
"MOTION_PLANS=$(
[ "$MOTION0" = "$MOTION1" ] &&
echo PASS ||
echo FAIL
)"


echo
echo "===== FINAL CERTIFICATION ====="


python - <<'PY'
import json

from pathlib import Path


targets = {
    "ADVERSARIAL":
        Path(
            "logs/producao/"
            "vi1000_1_adversarial_suite_latest.json"
        ),

    "DRY_RUN":
        Path(
            "logs/producao/"
            "vi1000_1_full_dry_run_latest.json"
        ),

    "ARCHITECTURE":
        Path(
            "logs/producao/"
            "vi1000_1_architecture_audit_latest.json"
        ),
}


statuses = {}


for name, path in (
    targets.items()
):
    if not path.exists():
        statuses[name] = "MISSING"
        continue

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )

    statuses[
        name
    ] = data.get(
        "status"
    )


for name, value in (
    statuses.items()
):
    print(
        name,
        "=",
        value
    )


certified = (
    statuses.get(
        "ADVERSARIAL"
    )
    ==
    "VI1000_1_ADVERSARIAL_CERTIFIED"

    and

    statuses.get(
        "DRY_RUN"
    )
    ==
    "VI1000_1_FULL_DRY_RUN_CERTIFIED"

    and

    statuses.get(
        "ARCHITECTURE"
    )
    ==
    "VI1000_1_ARCHITECTURE_CERTIFIED"
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
        "VI1000.1 RESULT: "
        "READY_FOR_FIRST_REAL_BATCH"
    )

else:
    print(
        "VI1000.1 RESULT: HOLD"
    )
PY


echo
echo "TEST EXIT STATUS=$STATUS"

} 2>&1 | tee -a "$LOG"


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1000_1_Full_Test.txt" \
2>/dev/null || true
