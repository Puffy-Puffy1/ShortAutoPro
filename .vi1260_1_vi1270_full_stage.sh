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
temp/vi1260_1 \
temp/vi1270_downloads/assets \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1260_1_vi1270_console.log"

CERT="$HOME/ShortAutoPro/temp/vi1260_1/final_certification.txt"

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

echo " VI1260.1 + VI1270 FULL CONTROLLED STAGE" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1260_1_01_strict_semantic_audit.py \
vi1260_1_02_repair_search.py \
vi1260_1_00_predownload_audit.py \
vi1260_1_03_regression.py \
vi1270_01_controlled_downloader.py \
vi1260_1_04_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE_STATUS=${PIPESTATUS[0]}


echo "COMPILE STATUS=$COMPILE_STATUS" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== STRICT REGRESSION =====" |
tee -a "$LOG"


python \
vi1260_1_03_regression.py \
2>&1 |
tee -a "$LOG"

REG_STATUS=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== PRE-DOWNLOAD SEMANTIC AUDIT =====" |
tee -a "$LOG"


python \
vi1260_1_00_predownload_audit.py \
2>&1 |
tee -a "$LOG"

AUDIT_STATUS=${PIPESTATUS[0]}


READY="$(
python - <<'PY'
import json
from pathlib import Path

p = Path(
    "logs/producao/"
    "vi1260_1_00_predownload_audit_latest.json"
)

try:
    gate = json.loads(
        p.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )

    print(
        "YES"
        if gate.get(
            "ready_for_controlled_download"
        )
        is True
        else "NO"
    )

except Exception:
    print(
        "NO"
    )
PY
)"


echo |
tee -a "$LOG"

echo "PREDOWNLOAD READY=$READY" |
tee -a "$LOG"


DOWNLOAD_STATUS=0


if [ "$READY" = "YES" ]; then

    echo |
    tee -a "$LOG"

    echo "===== VI1270 CONTROLLED DOWNLOAD =====" |
    tee -a "$LOG"


    python \
    vi1270_01_controlled_downloader.py \
    2>&1 |
    tee -a "$LOG"

    DOWNLOAD_STATUS=${PIPESTATUS[0]}

else

    echo |
    tee -a "$LOG"

    echo "===== VI1270 CONTROLLED DOWNLOAD =====" |
    tee -a "$LOG"

    echo \
    "DOWNLOAD SKIPPED: PRE-DOWNLOAD GATE NOT READY" |
    tee -a "$LOG"

fi


echo |
tee -a "$LOG"

echo "===== ARCHITECTURE =====" |
tee -a "$LOG"


python \
vi1260_1_04_architecture_audit.py \
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
echo " CORE INTEGRITY"
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

echo "PRODUCTION_MEDIA=$([ "$MEDIA_OK" = True ] && echo PASS || echo FAIL)"
} |
tee -a "$LOG"


export V12601_COMPILE="$COMPILE_STATUS"
export V12601_REG="$REG_STATUS"
export V12601_AUDIT="$AUDIT_STATUS"
export V1270_DOWNLOAD="$DOWNLOAD_STATUS"
export V12601_ARCH="$ARCH_STATUS"
export V12601_READY="$READY"

export V12601_VIDEO="$VIDEO_OK"
export V12601_GERAR="$GERAR_OK"
export V12601_ROTEIRO="$ROTEIRO_OK"
export V12601_EXECUTOR="$EXECUTOR_OK"
export V12601_V6="$V6_OK"
export V12601_SEMANTIC="$SEMANTIC_OK"
export V12601_QUERY="$QUERY_OK"
export V12601_RUNTIME="$RUNTIME_OK"
export V12601_HOOK="$HOOK_OK"
export V12601_MEDIA="$MEDIA_OK"


python - <<'PY' > "$CERT" 2>&1
import json
import os

from pathlib import Path


def gate(
    filename,
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


audit = gate(
    "vi1260_1_00_predownload_audit_latest.json"
)

download = gate(
    "vi1270_01_controlled_downloader_latest.json"
)

architecture = gate(
    "vi1260_1_04_architecture_audit_latest.json"
)


processes = {
    "COMPILE":
        int(
            os.environ.get(
                "V12601_COMPILE",
                99
            )
        ),

    "REGRESSION":
        int(
            os.environ.get(
                "V12601_REG",
                99
            )
        ),

    "PREDOWNLOAD_AUDIT":
        int(
            os.environ.get(
                "V12601_AUDIT",
                99
            )
        ),

    "DOWNLOAD":
        int(
            os.environ.get(
                "V1270_DOWNLOAD",
                99
            )
        ),

    "ARCHITECTURE":
        int(
            os.environ.get(
                "V12601_ARCH",
                99
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
            "V12601_VIDEO",

        "GERAR":
            "V12601_GERAR",

        "ROTEIRO":
            "V12601_ROTEIRO",

        "EXECUTOR":
            "V12601_EXECUTOR",

        "V6":
            "V12601_V6",

        "SEMANTIC":
            "V12601_SEMANTIC",

        "QUERY_GATE":
            "V12601_QUERY",

        "RUNTIME":
            "V12601_RUNTIME",

        "COMMAND_HOOK":
            "V12601_HOOK",

        "PRODUCTION_MEDIA":
            "V12601_MEDIA",
    }.items()
}


ready = (
    os.environ.get(
        "V12601_READY"
    )
    == "YES"
)


base_certified = (
    audit.get(
        "status"
    )
    ==
    "VI1260_1_PREDOWNLOAD_SEMANTICS_CERTIFIED"

    and

    architecture.get(
        "status"
    )
    ==
    "VI1260_1_VI1270_ARCHITECTURE_CERTIFIED"

    and

    processes[
        "COMPILE"
    ]
    == 0

    and

    processes[
        "REGRESSION"
    ]
    == 0

    and

    processes[
        "PREDOWNLOAD_AUDIT"
    ]
    == 0

    and

    processes[
        "ARCHITECTURE"
    ]
    == 0

    and

    all(
        integrity.values()
    )
)


if ready:

    stage_certified = (
        base_certified

        and

        processes[
            "DOWNLOAD"
        ]
        == 0

        and

        download.get(
            "status"
        )
        ==
        "VI1270_CONTROLLED_DOWNLOAD_CERTIFIED"
    )

else:

    stage_certified = (
        base_certified

        and

        processes[
            "DOWNLOAD"
        ]
        == 0
    )


print(
    "PREDOWNLOAD =",
    audit.get(
        "status",
        "MISSING"
    )
)

print(
    "PREDOWNLOAD RESULT =",
    audit.get(
        "result",
        "MISSING"
    )
)

print(
    "READY FOR DOWNLOAD =",
    ready
)

print(
    "DOWNLOAD STATUS =",
    (
        download.get(
            "status"
        )
        if ready
        else "SKIPPED_BY_GATE"
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
    audit.get(
        "selected_count"
    )
)

print(
    "SAFE HOLD SCENES =",
    audit.get(
        "hold_count"
    )
)

print(
    "HOLD LIST =",
    audit.get(
        "hold_scenes"
    )
)

print(
    "UNIQUE SOURCES =",
    audit.get(
        "unique_sources"
    )
)

print(
    "DIVERSITY PASS =",
    (
        audit.get(
            "diversity"
        )
        or {}
    ).get(
        "passed"
    )
)


if ready:

    print()
    print(
        "DOWNLOADED SCENE MAP =",
        download.get(
            "mapped_scenes"
        )
    )

    print(
        "UNIQUE DOWNLOADED ASSETS =",
        download.get(
            "unique_assets"
        )
    )

    print(
        "TOTAL DOWNLOADED BYTES =",
        download.get(
            "total_bytes"
        )
    )

    print(
        "DOWNLOAD FAILURES =",
        download.get(
            "failures"
        )
    )


print()
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


if stage_certified:

    if ready:

        print(
            "VI1270 FINAL: "
            "CONTROLLED_REAL_MEDIA_DOWNLOAD_CERTIFIED"
        )

    else:

        print(
            "VI1260.1 FINAL: "
            "PREDOWNLOAD_SAFE_MORE_SOURCES_REQUIRED"
        )


    raise SystemExit(
        0
    )


print(
    "VI1260.1/VI1270 FINAL: HOLD"
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
"$HOME/storage/downloads/VI1260_1_VI1270_Controlled_Stage.txt" \
2>/dev/null


exit "$FINAL_STATUS"
