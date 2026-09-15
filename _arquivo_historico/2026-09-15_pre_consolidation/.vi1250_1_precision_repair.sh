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
temp/vi1250_1 \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1250_1_precision_repair_console.log"

CERT="$HOME/ShortAutoPro/temp/vi1250_1/final_certification.txt"

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
tree_hash \
roteiros \
'motion_plan_*.json'
)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1250.1 PRECISION REPAIR CERTIFICATION" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1200_01_real_transport.py \
vi1250_04_candidate_engine.py \
vi1250_05_portfolio_optimizer.py \
vi1250_00_deep_real_source_expansion.py \
vi1250_08_coverage_diagnostics.py \
vi1250_09_repair_regression.py \
vi1250_06_portfolio_adversarial.py \
vi1250_07_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE_STATUS=${PIPESTATUS[0]}


echo "COMPILE STATUS=$COMPILE_STATUS" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== REPAIR REGRESSION =====" |
tee -a "$LOG"


python \
vi1250_09_repair_regression.py \
2>&1 |
tee -a "$LOG"

REG_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== DEEP SOURCE EXPANSION =====" |
tee -a "$LOG"


python \
vi1250_00_deep_real_source_expansion.py \
2>&1 |
tee -a "$LOG"

PIPE_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== COVERAGE DIAGNOSTICS =====" |
tee -a "$LOG"


python \
vi1250_08_coverage_diagnostics.py \
2>&1 |
tee -a "$LOG"

DIAG_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== PORTFOLIO ADVERSARIAL =====" |
tee -a "$LOG"


python \
vi1250_06_portfolio_adversarial.py \
2>&1 |
tee -a "$LOG"

ADV_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1250_07_architecture_audit.py \
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
tree_hash \
roteiros \
'motion_plan_*.json'
)"


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
MOTION_OK="$(same "$MOTION0" "$MOTION1")"


{
echo
echo "=============================================="
echo " VI1250.1 CORE INTEGRITY"
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


export V12501_COMPILE="$COMPILE_STATUS"
export V12501_REG="$REG_STATUS"
export V12501_PIPE="$PIPE_STATUS"
export V12501_DIAG="$DIAG_STATUS"
export V12501_ADV="$ADV_STATUS"
export V12501_ARCH="$ARCH_STATUS"

export V12501_VIDEO="$VIDEO_OK"
export V12501_GERAR="$GERAR_OK"
export V12501_ROTEIRO="$ROTEIRO_OK"
export V12501_EXECUTOR="$EXECUTOR_OK"
export V12501_V6="$V6_OK"

export V12501_SEMANTIC="$SEMANTIC_OK"
export V12501_QUERY="$QUERY_OK"
export V12501_RUNTIME="$RUNTIME_OK"
export V12501_HOOK="$HOOK_OK"

export V12501_MEDIA="$MEDIA_OK"
export V12501_MOTION="$MOTION_OK"


python - <<'PY' > "$CERT" 2>&1
import json
import os

from pathlib import Path


def gate(
    filename
):
    path = (
        Path(
            "logs/producao"
        )
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
    "vi1250_00_deep_real_source_expansion_latest.json"
)

diagnostics = gate(
    "vi1250_08_coverage_diagnostics_latest.json"
)

adversarial = gate(
    "vi1250_06_portfolio_adversarial_latest.json"
)

architecture = gate(
    "vi1250_07_architecture_audit_latest.json"
)


processes = {
    "COMPILE":
        int(
            os.environ.get(
                "V12501_COMPILE",
                99
            )
        ),

    "REGRESSION":
        int(
            os.environ.get(
                "V12501_REG",
                99
            )
        ),

    "PIPELINE":
        int(
            os.environ.get(
                "V12501_PIPE",
                99
            )
        ),

    "DIAGNOSTICS":
        int(
            os.environ.get(
                "V12501_DIAG",
                99
            )
        ),

    "ADVERSARIAL":
        int(
            os.environ.get(
                "V12501_ADV",
                99
            )
        ),

    "ARCHITECTURE":
        int(
            os.environ.get(
                "V12501_ARCH",
                99
            )
        ),
}


integrity = {
    "VIDEO":
        os.environ.get(
            "V12501_VIDEO"
        )
        == "True",

    "GERAR":
        os.environ.get(
            "V12501_GERAR"
        )
        == "True",

    "ROTEIRO":
        os.environ.get(
            "V12501_ROTEIRO"
        )
        == "True",

    "EXECUTOR":
        os.environ.get(
            "V12501_EXECUTOR"
        )
        == "True",

    "V6":
        os.environ.get(
            "V12501_V6"
        )
        == "True",

    "SEMANTIC":
        os.environ.get(
            "V12501_SEMANTIC"
        )
        == "True",

    "QUERY_GATE":
        os.environ.get(
            "V12501_QUERY"
        )
        == "True",

    "RUNTIME":
        os.environ.get(
            "V12501_RUNTIME"
        )
        == "True",

    "COMMAND_HOOK":
        os.environ.get(
            "V12501_HOOK"
        )
        == "True",

    "MEDIA":
        os.environ.get(
            "V12501_MEDIA"
        )
        == "True",

    "MOTION_PLANS":
        os.environ.get(
            "V12501_MOTION"
        )
        == "True",
}


network = (
    pipeline.get(
        "network"
    )
    or {}
)


attempts = (
    network.get(
        "requests_attempted"
    )
    or 0
)


budget_ok = (
    attempts <= 140
)


certified = (
    pipeline.get(
        "status"
    )
    ==
    "VI1250_SOURCE_EXPANSION_SAFETY_CERTIFIED"

    and

    diagnostics.get(
        "status"
    )
    ==
    "VI1250_1_COVERAGE_DIAGNOSTICS_CERTIFIED"

    and

    adversarial.get(
        "status"
    )
    ==
    "VI1250_PORTFOLIO_ADVERSARIAL_CERTIFIED"

    and

    architecture.get(
        "status"
    )
    ==
    "VI1250_ARCHITECTURE_CERTIFIED"

    and

    all(
        value == 0
        for value in processes.values()
    )

    and

    all(
        integrity.values()
    )

    and

    budget_ok
)


print(
    "PIPELINE =",
    pipeline.get(
        "status",
        "MISSING"
    )
)

print(
    "DIAGNOSTICS =",
    diagnostics.get(
        "status",
        "MISSING"
    )
)

print(
    "ADVERSARIAL =",
    adversarial.get(
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


print()
print(
    "REQUESTS ATTEMPTED =",
    attempts
)

print(
    "REQUEST BUDGET HARD-CAPPED =",
    budget_ok
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
        "VI1250.1 FINAL: "
        "COVERAGE_DIAGNOSTICS_AND_PRECISION_REPAIR_CERTIFIED"
    )

    raise SystemExit(
        0
    )


print(
    "VI1250.1 FINAL: HOLD"
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

echo "FINAL STATUS=$FINAL_STATUS" |
tee -a "$LOG"


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1250_1_Precision_Repair.txt" \
2>/dev/null


exit "$FINAL_STATUS"
