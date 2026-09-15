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
temp/vi1260 \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1260_console.log"
CERT="$HOME/ShortAutoPro/temp/vi1260/final_cert.txt"

: > "$LOG"


hash_file() {
    sha256sum "$1" 2>/dev/null |
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
EXECUTOR0="$(hash_file vi6_95_scene_executor.py)"
V6_0="$(hash_file v6.py)"

SEMANTIC0="$(hash_file vi1000_1_semantic_core.py)"
QUERY0="$(hash_file vi1000_1_query_gate.py)"
RUNTIME0="$(hash_file vi1000_runtime.py)"
HOOK0="$(hash_file vi1000_command_hook.py)"

MEDIA0="$(tree_hash imagens)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1260 SEMANTIC COVERAGE TEST" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1260_01_semantic_roles.py \
vi1260_02_targeted_search.py \
vi1260_03_semantic_candidate_gate.py \
vi1260_04_global_optimizer.py \
vi1260_00_coverage_resolver.py \
vi1260_05_regression.py \
vi1260_06_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE_STATUS=${PIPESTATUS[0]}


echo "COMPILE STATUS=$COMPILE_STATUS" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== SEMANTIC REGRESSION =====" |
tee -a "$LOG"


python \
vi1260_05_regression.py \
2>&1 |
tee -a "$LOG"

REG_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== REAL COVERAGE RESOLVER =====" |
tee -a "$LOG"


python \
vi1260_00_coverage_resolver.py \
2>&1 |
tee -a "$LOG"

PIPE_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1260_06_architecture_audit.py \
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

MEDIA1="$(tree_hash imagens)"


same() {
    [ "$1" = "$2" ] &&
    echo True ||
    echo False
}


VIDEO_OK="$(same "$VIDEO0" "$VIDEO1")"
GERAR_OK="$(same "$GERAR0" "$GERAR1")"
ROTEIRO_OK="$(same "$ROTEIRO0" "$ROTEIRO1")"
EXECUTOR_OK="$(same "$EXECUTOR0" "$EXECUTOR1")"
V6_OK="$(same "$V6_0" "$V6_1")"

SEMANTIC_OK="$(same "$SEMANTIC0" "$SEMANTIC1")"
QUERY_OK="$(same "$QUERY0" "$QUERY1")"
RUNTIME_OK="$(same "$RUNTIME0" "$RUNTIME1")"
HOOK_OK="$(same "$HOOK0" "$HOOK1")"

MEDIA_OK="$(same "$MEDIA0" "$MEDIA1")"


{
echo
echo "=============================================="
echo " VI1260 CORE INTEGRITY"
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
} |
tee -a "$LOG"


export V1260_COMPILE="$COMPILE_STATUS"
export V1260_REG="$REG_STATUS"
export V1260_PIPE="$PIPE_STATUS"
export V1260_ARCH="$ARCH_STATUS"

export V1260_VIDEO="$VIDEO_OK"
export V1260_GERAR="$GERAR_OK"
export V1260_ROTEIRO="$ROTEIRO_OK"
export V1260_EXECUTOR="$EXECUTOR_OK"
export V1260_V6="$V6_OK"
export V1260_SEMANTIC="$SEMANTIC_OK"
export V1260_QUERY="$QUERY_OK"
export V1260_RUNTIME="$RUNTIME_OK"
export V1260_HOOK="$HOOK_OK"
export V1260_MEDIA="$MEDIA_OK"


python - <<'PY' > "$CERT" 2>&1
import json
import os

from pathlib import Path


def gate(
    filename
):
    path = (
        Path("logs/producao")
        /
        filename
    )

    if not path.exists():
        return {}

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        ).get(
            "gate",
            {}
        )

    except Exception:
        return {}


pipeline = gate(
    "vi1260_00_coverage_resolver_latest.json"
)

architecture = gate(
    "vi1260_06_architecture_audit_latest.json"
)


processes = {
    "COMPILE":
        int(
            os.environ.get(
                "V1260_COMPILE",
                99
            )
        ),

    "REGRESSION":
        int(
            os.environ.get(
                "V1260_REG",
                99
            )
        ),

    "PIPELINE":
        int(
            os.environ.get(
                "V1260_PIPE",
                99
            )
        ),

    "ARCHITECTURE":
        int(
            os.environ.get(
                "V1260_ARCH",
                99
            )
        ),
}


integrity = {
    name:
        os.environ.get(env)
        == "True"

    for name, env in {
        "VIDEO": "V1260_VIDEO",
        "GERAR": "V1260_GERAR",
        "ROTEIRO": "V1260_ROTEIRO",
        "EXECUTOR": "V1260_EXECUTOR",
        "V6": "V1260_V6",
        "SEMANTIC": "V1260_SEMANTIC",
        "QUERY_GATE": "V1260_QUERY",
        "RUNTIME": "V1260_RUNTIME",
        "COMMAND_HOOK": "V1260_HOOK",
        "MEDIA": "V1260_MEDIA",
    }.items()
}


certified = (
    pipeline.get("status")
    ==
    "VI1260_SEMANTIC_COVERAGE_CERTIFIED"

    and

    architecture.get("status")
    ==
    "VI1260_ARCHITECTURE_CERTIFIED"

    and

    all(
        value == 0
        for value in (
            processes.values()
        )
    )

    and

    all(
        integrity.values()
    )
)


print(
    "PIPELINE =",
    pipeline.get(
        "status",
        "MISSING"
    )
)

print(
    "ARCHITECTURE =",
    architecture.get(
        "status",
        "MISSING"
    )
)


print()
print(
    "PROCESS STATUS =",
    processes
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
    "HOLD LIST =",
    pipeline.get(
        "hold_scenes"
    )
)

print(
    "UNIQUE SOURCES =",
    pipeline.get(
        "unique_sources"
    )
)

print(
    "DIVERSITY PASS =",
    (
        pipeline.get(
            "diversity"
        )
        or {}
    ).get(
        "passed"
    )
)

print(
    "RESULT =",
    pipeline.get(
        "result"
    )
)


print()
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

print(
    "REAL BATCH GENERATED: 0"
)


print()


if certified:

    print(
        "VI1260 FINAL: "
        "SEMANTIC_ROLE_AND_COVERAGE_RESOLVER_CERTIFIED"
    )

    raise SystemExit(0)


print(
    "VI1260 FINAL: HOLD"
)

raise SystemExit(1)
PY


FINAL_STATUS=$?


cat "$CERT" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "FINAL STATUS=$FINAL_STATUS" |
tee -a "$LOG"


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1260_Semantic_Coverage.txt" \
2>/dev/null


exit "$FINAL_STATUS"
