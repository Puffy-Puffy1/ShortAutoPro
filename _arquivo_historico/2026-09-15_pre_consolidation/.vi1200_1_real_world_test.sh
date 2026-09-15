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
temp/vi1200_1_real \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1200_1_real_world_console.log"

CERT="$HOME/ShortAutoPro/temp/vi1200_1_real/final_cert.txt"


: > "$LOG"


hash_file() {
    sha256sum "$1" 2>/dev/null |
    awk '{print $1}'
}


VIDEO0="$(hash_file video.py)"
GERAR0="$(hash_file gerar_short.sh)"
ROTEIRO0="$(hash_file roteiro.py)"
EXECUTOR0="$(hash_file vi6_95_scene_executor.py)"
V6_0="$(hash_file v6.py)"

SEMANTIC0="$(hash_file vi1000_1_semantic_core.py)"
QUERY0="$(hash_file vi1000_1_query_gate.py)"
RUNTIME0="$(hash_file vi1000_runtime.py)"
HOOK0="$(hash_file vi1000_command_hook.py)"


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


echo \
"==============================================" |
tee -a "$LOG"

echo \
" VI1200.1 REAL-WORLD PRECISION TEST" |
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
vi1200_01_real_transport.py \
vi1200_02_commons_provider.py \
vi1200_03_archive_provider.py \
vi1200_04_real_candidate_adapter.py \
vi1200_06_visual_precision.py \
vi1200_07_search_expansion.py \
vi1200_10_hardened_real_pipeline.py \
vi1200_11_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo \
"===== HARDENED REAL PIPELINE =====" |
tee -a "$LOG"


python \
vi1200_10_hardened_real_pipeline.py \
2>&1 |
tee -a "$LOG"

PIPE_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo \
"===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1200_11_architecture_audit.py \
2>&1 |
tee -a "$LOG"

ARCH_STATUS=${PIPESTATUS[0]}


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
EXECUTOR1="$(hash_file vi6_95_scene_executor.py)"
V6_1="$(hash_file v6.py)"

SEMANTIC1="$(hash_file vi1000_1_semantic_core.py)"
QUERY1="$(hash_file vi1000_1_query_gate.py)"
RUNTIME1="$(hash_file vi1000_runtime.py)"
HOOK1="$(hash_file vi1000_command_hook.py)"


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


integrity() {
    [ "$1" = "$2" ] &&
    echo True ||
    echo False
}


VIDEO_OK="$(integrity "$VIDEO0" "$VIDEO1")"
GERAR_OK="$(integrity "$GERAR0" "$GERAR1")"
ROTEIRO_OK="$(integrity "$ROTEIRO0" "$ROTEIRO1")"
EXECUTOR_OK="$(integrity "$EXECUTOR0" "$EXECUTOR1")"
V6_OK="$(integrity "$V6_0" "$V6_1")"

SEMANTIC_OK="$(integrity "$SEMANTIC0" "$SEMANTIC1")"
QUERY_OK="$(integrity "$QUERY0" "$QUERY1")"
RUNTIME_OK="$(integrity "$RUNTIME0" "$RUNTIME1")"
HOOK_OK="$(integrity "$HOOK0" "$HOOK1")"

MEDIA_OK="$(integrity "$MEDIA0" "$MEDIA1")"
MOTION_OK="$(integrity "$MOTION0" "$MOTION1")"


{
echo
echo "=============================================="
echo " VI1200.1 CORE INTEGRITY"
echo "=============================================="

echo "VIDEO=$([ "$VIDEO_OK" = True ] && echo PASS || echo FAIL)"
echo "GERAR=$([ "$GERAR_OK" = True ] && echo PASS || echo FAIL)"
echo "ROTEIRO=$([ "$ROTEIRO_OK" = True ] && echo PASS || echo FAIL)"
echo "EXECUTOR=$([ "$EXECUTOR_OK" = True ] && echo PASS || echo FAIL)"
echo "V6=$([ "$V6_OK" = True ] && echo PASS || echo FAIL)"

echo "SEMANTIC=$([ "$SEMANTIC_OK" = True ] && echo PASS || echo FAIL)"
echo "QUERY_GATE=$([ "$QUERY_OK" = True ] && echo PASS || echo FAIL)"
echo "RUNTIME=$([ "$RUNTIME_OK" = True ] && echo PASS || echo FAIL)"
echo "COMMAND_HOOK=$([ "$HOOK_OK" = True ] && echo PASS || echo FAIL)"

echo "MEDIA=$([ "$MEDIA_OK" = True ] && echo PASS || echo FAIL)"
echo "MOTION_PLANS=$([ "$MOTION_OK" = True ] && echo PASS || echo FAIL)"
} |
tee -a "$LOG"


export VI12001_COMPILE="$COMPILE_STATUS"
export VI12001_PIPE="$PIPE_STATUS"
export VI12001_ARCH="$ARCH_STATUS"

export VI12001_VIDEO="$VIDEO_OK"
export VI12001_GERAR="$GERAR_OK"
export VI12001_ROTEIRO="$ROTEIRO_OK"
export VI12001_EXECUTOR="$EXECUTOR_OK"
export VI12001_V6="$V6_OK"
export VI12001_SEMANTIC="$SEMANTIC_OK"
export VI12001_QUERY="$QUERY_OK"
export VI12001_RUNTIME="$RUNTIME_OK"
export VI12001_HOOK="$HOOK_OK"
export VI12001_MEDIA="$MEDIA_OK"
export VI12001_MOTION="$MOTION_OK"


python - <<'PY' > "$CERT" 2>&1
import json
import os

from pathlib import Path


pipeline_file = Path(
    "logs/producao/"
    "vi1200_10_hardened_real_pipeline_latest.json"
)

arch_file = Path(
    "logs/producao/"
    "vi1200_11_architecture_audit_latest.json"
)


def read_gate(
    path
):
    if not path.exists():
        return {}

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )


pipeline = read_gate(
    pipeline_file
)

arch = read_gate(
    arch_file
)


pipeline_status = pipeline.get(
    "status",
    "MISSING"
)

arch_status = arch.get(
    "status",
    "MISSING"
)


process = {
    "COMPILE":
        int(
            os.environ.get(
                "VI12001_COMPILE",
                "99"
            )
        ),

    "PIPELINE":
        int(
            os.environ.get(
                "VI12001_PIPE",
                "99"
            )
        ),

    "ARCHITECTURE":
        int(
            os.environ.get(
                "VI12001_ARCH",
                "99"
            )
        ),
}


integrity = {
    name:
        os.environ.get(
            env
        )
        == "True"

    for name, env in {
        "VIDEO":
            "VI12001_VIDEO",

        "GERAR":
            "VI12001_GERAR",

        "ROTEIRO":
            "VI12001_ROTEIRO",

        "EXECUTOR":
            "VI12001_EXECUTOR",

        "V6":
            "VI12001_V6",

        "SEMANTIC":
            "VI12001_SEMANTIC",

        "QUERY_GATE":
            "VI12001_QUERY",

        "RUNTIME":
            "VI12001_RUNTIME",

        "COMMAND_HOOK":
            "VI12001_HOOK",

        "MEDIA":
            "VI12001_MEDIA",

        "MOTION_PLANS":
            "VI12001_MOTION",
    }.items()
}


certified = (
    pipeline_status
    ==
    "VI1200_1_REAL_WORLD_SAFETY_CERTIFIED"

    and

    arch_status
    ==
    "VI1200_1_ARCHITECTURE_CERTIFIED"

    and

    all(
        value == 0
        for value in (
            process.values()
        )
    )

    and

    all(
        integrity.values()
    )
)


print(
    "PIPELINE =",
    pipeline_status
)

print(
    "ARCHITECTURE =",
    arch_status
)

print(
    "PROCESS STATUS =",
    process
)

print(
    "CORE INTEGRITY =",
    integrity
)


print()

print(
    "SELECTED SCENES =",
    pipeline.get(
        "selected_count"
    )
)

print(
    "SAFE HOLD SCENES =",
    pipeline.get(
        "hold_count"
    )
)

print(
    "PREFLIGHT =",
    pipeline.get(
        "preflight_status"
    )
)


print()

print(
    "NETWORK EXECUTED: True"
)

print(
    "REMOTE MEDIA DOWNLOADED: False"
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
    "PRODUCTION MUTATED: False"
)


print()


if certified:

    print(
        "VI1200.1 FINAL: "
        "REAL_WORLD_PRECISION_CERTIFIED"
    )

    raise SystemExit(
        0
    )


print(
    "VI1200.1 FINAL: HOLD"
)

raise SystemExit(
    1
)
PY


FINAL_STATUS=$?


cat "$CERT" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo \
"FINAL STATUS=$FINAL_STATUS" |
tee -a "$LOG"


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1200_1_Real_World_Test.txt" \
2>/dev/null


exit "$FINAL_STATUS"
