#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1


echo
echo "=============================================="
echo " VI1000 LAUNCH ENGINE BUILD + TEST"
echo "=============================================="


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


echo
echo "===== COMPILE ALL ====="

python -m py_compile \
vi1000_runtime.py \
vi1000_command_hook.py \
vi1000_00_launch_production_engine.py \
vi1000_01_regression_suite.py \
vi1000_02_architecture_audit.py || exit 10

echo "COMPILE: PASS"


echo
echo "===== BUILD ENGINE ====="

python \
vi1000_00_launch_production_engine.py || exit 11


echo
echo "===== REGRESSION ====="

python \
vi1000_01_regression_suite.py || exit 12


echo
echo "===== ARCHITECTURE ====="

python \
vi1000_02_architecture_audit.py || exit 13


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


echo
echo "=============================================="
echo " VI1000 CORE INTEGRITY"
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


files = {
    "ENGINE":
        Path(
            "logs/producao/"
            "vi1000_00_launch_production_engine_latest.json"
        ),

    "REGRESSION":
        Path(
            "logs/producao/"
            "vi1000_01_regression_suite_latest.json"
        ),

    "ARCHITECTURE":
        Path(
            "logs/producao/"
            "vi1000_02_architecture_audit_latest.json"
        ),
}


status = {}


for name, path in (
    files.items()
):

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )

    status[
        name
    ] = data.get(
        "status"
    )


print(
    "ENGINE:",
    status[
        "ENGINE"
    ]
)

print(
    "REGRESSION:",
    status[
        "REGRESSION"
    ]
)

print(
    "ARCHITECTURE:",
    status[
        "ARCHITECTURE"
    ]
)


certified = (
    status[
        "ENGINE"
    ]
    ==
    "VI1000_LAUNCH_PRODUCTION_ENGINE_CERTIFIED"

    and

    status[
        "REGRESSION"
    ]
    ==
    "VI1000_REGRESSION_CERTIFIED"

    and

    status[
        "ARCHITECTURE"
    ]
    ==
    "VI1000_ARCHITECTURE_CERTIFIED"
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
    "RENDERER ACTIVATED: False"
)

print(
    "BATCH VIDEOS GENERATED: 0"
)

print()


if certified:

    print(
        "VI1000 RESULT: "
        "LAUNCH_ENGINE_CERTIFIED"
    )

else:

    print(
        "VI1000 RESULT: HOLD"
    )
PY
