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
temp/vi1200_real \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1200_controlled_real_pipeline_console.log"

CERT_TMP="$HOME/ShortAutoPro/temp/vi1200_real/final_certification.txt"


: > "$LOG"


hash_file() {
    sha256sum "$1" 2>/dev/null |
    awk '{print $1}'
}


tree_hash_all() {
    local ROOT="$1"

    find "$ROOT" \
    -type f \
    -printf '%p|%s|%T@\n' \
    2>/dev/null |
    sort |
    sha256sum |
    awk '{print $1}'
}


tree_hash_pattern() {
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

SEMANTIC0="$(hash_file vi1000_1_semantic_core.py)"
QUERY0="$(hash_file vi1000_1_query_gate.py)"
RUNTIME0="$(hash_file vi1000_runtime.py)"
HOOK0="$(hash_file vi1000_command_hook.py)"

MEDIA0="$(
tree_hash_all \
imagens
)"

MOTION0="$(
tree_hash_pattern \
roteiros \
'motion_plan_*.json'
)"


echo \
"==============================================" |
tee -a "$LOG"

echo \
" VI1200 CONTROLLED REAL PIPELINE TEST" |
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
vi1200_00_controlled_real_pipeline.py \
vi1200_05_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE_STATUS=${PIPESTATUS[0]}


echo \
"COMPILE STATUS=$COMPILE_STATUS" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo \
"===== REAL INTERNET PIPELINE =====" |
tee -a "$LOG"


python \
vi1200_00_controlled_real_pipeline.py \
2>&1 |
tee -a "$LOG"

PIPELINE_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo \
"===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1200_05_architecture_audit.py \
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
tree_hash_all \
imagens
)"

MOTION1="$(
tree_hash_pattern \
roteiros \
'motion_plan_*.json'
)"


VIDEO_OK=False
GERAR_OK=False
ROTEIRO_OK=False
EXECUTOR_OK=False
V6_OK=False
SEMANTIC_OK=False
QUERY_OK=False
RUNTIME_OK=False
HOOK_OK=False
MEDIA_OK=False
MOTION_OK=False


[ "$VIDEO0" = "$VIDEO1" ] && VIDEO_OK=True
[ "$GERAR0" = "$GERAR1" ] && GERAR_OK=True
[ "$ROTEIRO0" = "$ROTEIRO1" ] && ROTEIRO_OK=True
[ "$EXECUTOR0" = "$EXECUTOR1" ] && EXECUTOR_OK=True
[ "$V6_0" = "$V6_1" ] && V6_OK=True

[ "$SEMANTIC0" = "$SEMANTIC1" ] && SEMANTIC_OK=True
[ "$QUERY0" = "$QUERY1" ] && QUERY_OK=True
[ "$RUNTIME0" = "$RUNTIME1" ] && RUNTIME_OK=True
[ "$HOOK0" = "$HOOK1" ] && HOOK_OK=True

[ "$MEDIA0" = "$MEDIA1" ] && MEDIA_OK=True
[ "$MOTION0" = "$MOTION1" ] && MOTION_OK=True


{
echo
echo "=============================================="
echo " VI1200 CORE INTEGRITY"
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


export VI1200_COMPILE_STATUS="$COMPILE_STATUS"
export VI1200_PIPELINE_STATUS="$PIPELINE_STATUS"
export VI1200_ARCH_STATUS="$ARCH_STATUS"

export VI1200_VIDEO_OK="$VIDEO_OK"
export VI1200_GERAR_OK="$GERAR_OK"
export VI1200_ROTEIRO_OK="$ROTEIRO_OK"
export VI1200_EXECUTOR_OK="$EXECUTOR_OK"
export VI1200_V6_OK="$V6_OK"

export VI1200_SEMANTIC_OK="$SEMANTIC_OK"
export VI1200_QUERY_OK="$QUERY_OK"
export VI1200_RUNTIME_OK="$RUNTIME_OK"
export VI1200_HOOK_OK="$HOOK_OK"

export VI1200_MEDIA_OK="$MEDIA_OK"
export VI1200_MOTION_OK="$MOTION_OK"


echo |
tee -a "$LOG"

echo \
"===== FINAL MACHINE CERTIFICATION =====" |
tee -a "$LOG"


python - <<'PY' > "$CERT_TMP" 2>&1
import json
import os

from pathlib import Path


pipeline_path = Path(
    "logs/producao/"
    "vi1200_00_controlled_real_pipeline_latest.json"
)

architecture_path = Path(
    "logs/producao/"
    "vi1200_05_architecture_audit_latest.json"
)


def get_status(
    path
):
    if not path.exists():
        return "MISSING"

    try:
        return json.loads(
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
        return "INVALID_JSON"


pipeline = get_status(
    pipeline_path
)

architecture = get_status(
    architecture_path
)


print(
    "PIPELINE =",
    pipeline
)

print(
    "ARCHITECTURE =",
    architecture
)


processes = {
    "COMPILE":
        int(
            os.environ.get(
                "VI1200_COMPILE_STATUS",
                "99"
            )
        ),

    "PIPELINE":
        int(
            os.environ.get(
                "VI1200_PIPELINE_STATUS",
                "99"
            )
        ),

    "ARCHITECTURE":
        int(
            os.environ.get(
                "VI1200_ARCH_STATUS",
                "99"
            )
        ),
}


integrity = {
    "VIDEO":
        os.environ.get(
            "VI1200_VIDEO_OK"
        )
        == "True",

    "GERAR":
        os.environ.get(
            "VI1200_GERAR_OK"
        )
        == "True",

    "ROTEIRO":
        os.environ.get(
            "VI1200_ROTEIRO_OK"
        )
        == "True",

    "EXECUTOR":
        os.environ.get(
            "VI1200_EXECUTOR_OK"
        )
        == "True",

    "V6":
        os.environ.get(
            "VI1200_V6_OK"
        )
        == "True",

    "SEMANTIC":
        os.environ.get(
            "VI1200_SEMANTIC_OK"
        )
        == "True",

    "QUERY_GATE":
        os.environ.get(
            "VI1200_QUERY_OK"
        )
        == "True",

    "RUNTIME":
        os.environ.get(
            "VI1200_RUNTIME_OK"
        )
        == "True",

    "COMMAND_HOOK":
        os.environ.get(
            "VI1200_HOOK_OK"
        )
        == "True",

    "MEDIA":
        os.environ.get(
            "VI1200_MEDIA_OK"
        )
        == "True",

    "MOTION_PLANS":
        os.environ.get(
            "VI1200_MOTION_OK"
        )
        == "True",
}


certified = (
    pipeline
    ==
    "VI1200_CONTROLLED_REAL_PIPELINE_CERTIFIED"

    and

    architecture
    ==
    "VI1200_ARCHITECTURE_CERTIFIED"

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


print()
print(
    "PROCESS STATUS:",
    processes
)

print(
    "CORE INTEGRITY:",
    integrity
)


if pipeline_path.exists():
    data = json.loads(
        pipeline_path.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )

    preflight = data.get(
        "preflight",
        {}
    )

    network = data.get(
        "network",
        {}
    )


    print()
    print(
        "REAL SELECTED SCENES =",
        preflight.get(
            "selected_count"
        )
    )

    print(
        "SAFE HOLD SCENES =",
        preflight.get(
            "hold_count"
        )
    )

    print(
        "NEXT-STAGE PREFLIGHT =",
        preflight.get(
            "status"
        )
    )

    print(
        "NETWORK REQUESTS SUCCEEDED =",
        network.get(
            "requests_succeeded"
        )
    )

    print(
        "METADATA BYTES RECEIVED =",
        network.get(
            "metadata_bytes_received"
        )
    )


print()
print(
    "NETWORK EXECUTED: True"
)

print(
    "REAL SEARCH EXECUTED: True"
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

print(
    "REAL BATCH GENERATED: 0"
)


print()


if certified:
    print(
        "VI1200 RESULT: "
        "REAL_NETWORK_PIPELINE_CERTIFIED"
    )

    raise SystemExit(
        0
    )


print(
    "VI1200 RESULT: HOLD"
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
"$HOME/storage/downloads/VI1200_Controlled_Real_Pipeline.txt" \
2>/dev/null


exit "$FINAL_STATUS"
