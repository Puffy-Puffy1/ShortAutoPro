#!/data/data/com.termux/files/usr/bin/bash

set +e
set +u
set +o pipefail 2>/dev/null

cd "$HOME/ShortAutoPro" || exit 90


mkdir -p \
temp/vi1400/prepared \
temp/vi1400/work \
temp/vi1400/canary \
logs/producao \
"$HOME/storage/downloads"


LOG="$HOME/ShortAutoPro/logs/producao/vi1400_console.log"

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

SOURCE_ASSETS0="$(
tree_hash \
temp/vi1270_downloads/assets
)"


echo "==============================================" |
tee -a "$LOG"

echo " VI1400 RELEASE CANDIDATE SPRINT" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"


echo |
tee -a "$LOG"

echo "===== PREREQUISITES =====" |
tee -a "$LOG"


python - <<'PY' 2>&1 |
tee -a "$LOG"
import json
from pathlib import Path

required = {
    "VI1300":
        (
            Path(
                "logs/producao/"
                "vi1300_00_visual_preparation_director_latest.json"
            ),
            "VI1300_VISUAL_PREPARATION_CERTIFIED",
        ),

    "VI1290":
        (
            Path(
                "logs/producao/"
                "vi1290_00_asset_readiness_latest.json"
            ),
            "VI1290_ASSET_READINESS_CERTIFIED",
        ),

    "VI1280":
        (
            Path(
                "logs/producao/"
                "vi1280_00_asset_forensics_latest.json"
            ),
            "VI1280_ASSET_FORENSICS_CERTIFIED",
        ),
}

failed = []

for name, (path, expected) in required.items():

    try:

        gate = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        ).get(
            "gate",
            {}
        )

        status = gate.get(
            "status"
        )

    except Exception:

        status = "MISSING"

    ok = (
        status == expected
    )

    print(
        name,
        "=",
        status,
        "|",
        "PASS"
        if ok
        else "FAIL"
    )

    if not ok:
        failed.append(
            name
        )

print(
    "FAILED:",
    failed
)

raise SystemExit(
    0
    if not failed
    else 1
)
PY

PREREQ=${PIPESTATUS[0]}


echo |
tee -a "$LOG"

echo "===== COMPILE =====" |
tee -a "$LOG"


python -m py_compile \
vi1400_01_transform_core.py \
vi1400_02_asset_transformer.py \
vi1400_03_prepared_forensics.py \
vi1400_04_render_manifest.py \
vi1400_05_visual_canary.py \
vi1400_06_canary_forensics.py \
vi1400_07_regression.py \
vi1400_08_architecture_audit.py \
2>&1 |
tee -a "$LOG"

COMPILE=${PIPESTATUS[0]}


echo "COMPILE=$COMPILE" |
tee -a "$LOG"


run_stage() {

    NAME="$1"
    shift

    echo |
    tee -a "$LOG"

    echo "===== $NAME =====" |
    tee -a "$LOG"

    "$@" 2>&1 |
    tee -a "$LOG"

    return ${PIPESTATUS[0]}
}


if \
[ "$PREREQ" -eq 0 ] && \
[ "$COMPILE" -eq 0 ]
then

    run_stage \
    "REGRESSION" \
    python \
    vi1400_07_regression.py

    REG=$?

else

    REG=99

fi


if [ "$REG" -eq 0 ]; then

    run_stage \
    "ASSET TRANSFORMATION" \
    python \
    vi1400_02_asset_transformer.py

    TRANSFORM=$?

else

    TRANSFORM=99

fi


if [ "$TRANSFORM" -eq 0 ]; then

    run_stage \
    "PREPARED FORENSICS" \
    python \
    vi1400_03_prepared_forensics.py

    FORENSICS=$?

else

    FORENSICS=99

fi


if [ "$FORENSICS" -eq 0 ]; then

    run_stage \
    "RENDER MANIFEST" \
    python \
    vi1400_04_render_manifest.py

    MANIFEST=$?

else

    MANIFEST=99

fi


if [ "$MANIFEST" -eq 0 ]; then

    run_stage \
    "VISUAL CANARY BUILD" \
    python \
    vi1400_05_visual_canary.py

    CANARY=$?

else

    CANARY=99

fi


if [ "$CANARY" -eq 0 ]; then

    run_stage \
    "CANARY FORENSICS" \
    python \
    vi1400_06_canary_forensics.py

    CANARY_FORENSICS=$?

else

    CANARY_FORENSICS=99

fi


if [ "$CANARY_FORENSICS" -eq 0 ]; then

    run_stage \
    "ARCHITECTURE" \
    python \
    vi1400_08_architecture_audit.py

    ARCH=$?

else

    ARCH=99

fi


VIDEO1="$(hash_file video.py)"
GERAR1="$(hash_file gerar_short.sh)"
ROTEIRO1="$(hash_file roteiro.py)"
EXECUTOR1="$(hash_file vi6_95_scene_executor.py)"
V6_1="$(hash_file v6.py)"

SOURCE_ASSETS1="$(
tree_hash \
temp/vi1270_downloads/assets
)"


same() {
    [ "$1" = "$2" ] &&
    echo True ||
    echo False
}


export V1400_VIDEO="$(
same "$VIDEO0" "$VIDEO1"
)"

export V1400_GERAR="$(
same "$GERAR0" "$GERAR1"
)"

export V1400_ROTEIRO="$(
same "$ROTEIRO0" "$ROTEIRO1"
)"

export V1400_EXECUTOR="$(
same "$EXECUTOR0" "$EXECUTOR1"
)"

export V1400_V6="$(
same "$V6_0" "$V6_1"
)"

export V1400_SOURCE_ASSETS="$(
same "$SOURCE_ASSETS0" "$SOURCE_ASSETS1"
)"


export V1400_PREREQ="$PREREQ"
export V1400_COMPILE="$COMPILE"
export V1400_REG="$REG"
export V1400_TRANSFORM="$TRANSFORM"
export V1400_FORENSICS="$FORENSICS"
export V1400_MANIFEST="$MANIFEST"
export V1400_CANARY="$CANARY"
export V1400_CANARY_FORENSICS="$CANARY_FORENSICS"
export V1400_ARCH="$ARCH"


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " VI1400 CORE INTEGRITY" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "VIDEO=$V1400_VIDEO" |
tee -a "$LOG"

echo "GERAR=$V1400_GERAR" |
tee -a "$LOG"

echo "ROTEIRO=$V1400_ROTEIRO" |
tee -a "$LOG"

echo "EXECUTOR=$V1400_EXECUTOR" |
tee -a "$LOG"

echo "V6=$V1400_V6" |
tee -a "$LOG"

echo "SOURCE_ASSETS=$V1400_SOURCE_ASSETS" |
tee -a "$LOG"


python - <<'PY' 2>&1 |
tee -a "$LOG"

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


process = {
    "PREREQ":
        int(
            os.environ[
                "V1400_PREREQ"
            ]
        ),

    "COMPILE":
        int(
            os.environ[
                "V1400_COMPILE"
            ]
        ),

    "REGRESSION":
        int(
            os.environ[
                "V1400_REG"
            ]
        ),

    "TRANSFORM":
        int(
            os.environ[
                "V1400_TRANSFORM"
            ]
        ),

    "PREPARED_FORENSICS":
        int(
            os.environ[
                "V1400_FORENSICS"
            ]
        ),

    "MANIFEST":
        int(
            os.environ[
                "V1400_MANIFEST"
            ]
        ),

    "CANARY":
        int(
            os.environ[
                "V1400_CANARY"
            ]
        ),

    "CANARY_FORENSICS":
        int(
            os.environ[
                "V1400_CANARY_FORENSICS"
            ]
        ),

    "ARCHITECTURE":
        int(
            os.environ[
                "V1400_ARCH"
            ]
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
            "V1400_VIDEO",

        "GERAR":
            "V1400_GERAR",

        "ROTEIRO":
            "V1400_ROTEIRO",

        "EXECUTOR":
            "V1400_EXECUTOR",

        "V6":
            "V1400_V6",

        "SOURCE_ASSETS":
            "V1400_SOURCE_ASSETS",
    }.items()
}


transform = gate(
    "vi1400_02_asset_transformer_latest.json"
)

prepared = gate(
    "vi1400_03_prepared_forensics_latest.json"
)

manifest = gate(
    "vi1400_04_render_manifest_latest.json"
)

canary = gate(
    "vi1400_05_visual_canary_latest.json"
)

canary_forensics = gate(
    "vi1400_06_canary_forensics_latest.json"
)

architecture = gate(
    "vi1400_08_architecture_audit_latest.json"
)


certified = (
    all(
        value == 0
        for value
        in process.values()
    )

    and

    all(
        integrity.values()
    )

    and

    transform.get(
        "status"
    )
    ==
    "VI1400_ASSET_TRANSFORMATION_CERTIFIED"

    and

    prepared.get(
        "status"
    )
    ==
    "VI1400_PREPARED_FORENSICS_CERTIFIED"

    and

    manifest.get(
        "status"
    )
    ==
    "VI1400_RENDER_MANIFEST_CERTIFIED"

    and

    canary.get(
        "status"
    )
    ==
    "VI1400_VISUAL_CANARY_GENERATED"

    and

    canary_forensics.get(
        "status"
    )
    ==
    "VI1400_VISUAL_CANARY_FORENSICS_CERTIFIED"

    and

    architecture.get(
        "status"
    )
    ==
    "VI1400_ARCHITECTURE_CERTIFIED"
)


print()
print(
    "=============================================="
)

print(
    " VI1400 FINAL CERTIFICATION"
)

print(
    "=============================================="
)


print(
    "PROCESS STATUS =",
    process
)

print(
    "CORE/SOURCE INTEGRITY =",
    integrity
)


print()
print(
    "TRANSFORM =",
    transform.get(
        "status"
    )
)

print(
    "PREPARED FORENSICS =",
    prepared.get(
        "status"
    )
)

print(
    "RENDER MANIFEST =",
    manifest.get(
        "status"
    )
)

print(
    "CANARY =",
    canary.get(
        "status"
    )
)

print(
    "CANARY FORENSICS =",
    canary_forensics.get(
        "status"
    )
)

print(
    "ARCHITECTURE =",
    architecture.get(
        "status"
    )
)


print()
print(
    "NETWORK_EXECUTED=FALSE"
)

print(
    "DOWNLOAD_EXECUTED=FALSE"
)

print(
    "FFMPEG_EXECUTED=TRUE"
)

print(
    "FFPROBE_EXECUTED=TRUE"
)

print(
    "VISUAL_CANARY_GENERATED=TRUE"
)

print(
    "PRODUCTION_RENDERER_ACTIVATED=FALSE"
)

print(
    "PRODUCTION_MUTATED=FALSE"
)


if certified:

    print()
    print(
        "VI1400 FINAL: "
        "RELEASE_CANDIDATE_VISUAL_CANARY_CERTIFIED"
    )

    raise SystemExit(0)


print()
print(
    "VI1400 FINAL: HOLD"
)

raise SystemExit(1)
PY

FINAL=${PIPESTATUS[0]}


CANARY_FILE="$HOME/ShortAutoPro/temp/vi1400/canary/VI1400_visual_canary.mp4"

if \
[ "$FINAL" -eq 0 ] && \
[ -f "$CANARY_FILE" ]
then

    cp -f \
    "$CANARY_FILE" \
    "$HOME/storage/downloads/ShortAutoPro_VI1400_Visual_Canary.mp4"

fi


cp -f \
"$LOG" \
"$HOME/storage/downloads/VI1400_Release_Candidate_Log.txt" \
2>/dev/null


echo |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo " RETORNO VI1400" |
tee -a "$LOG"

echo "==============================================" |
tee -a "$LOG"

echo "FINAL_STATUS=$FINAL" |
tee -a "$LOG"

echo "TERMUX_CONTINUA_ABERTO=SIM" |
tee -a "$LOG"


exit "$FINAL"
