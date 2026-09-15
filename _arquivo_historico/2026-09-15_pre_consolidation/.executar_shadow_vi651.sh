#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
TESTDIR="logs/producao/shadow_vi651_${STAMP}"

mkdir -p "$TESTDIR"

echo
echo "======================================================"
echo " VI6.49-6.51 REAL 12-SCENE SHADOW RUN"
echo " RENDERER EFFECTIVE OUTPUT = LEGACY"
echo "======================================================"
echo


# =====================================================
# 0. REQUIRED
# =====================================================

REQUIRED="
video.py
gerar_short.sh
vi6_47_renderer_switch.py
vi6_48_emergency_rollback.py
vi6_49_real_command_mapper.py
vi6_50_shadow_filter_comparator.py
vi6_51_canary_gate.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then

        echo "ERRO: $F ausente."

        exit 2
    fi
done


# =====================================================
# 1. COMPILE + RELEASE
# =====================================================

echo "===== PRE-RUN COMPILE ====="

if ! python -m py_compile \
    video.py \
    vi6_47_renderer_switch.py \
    vi6_48_emergency_rollback.py \
    vi6_49_real_command_mapper.py \
    vi6_50_shadow_filter_comparator.py \
    vi6_51_canary_gate.py
then

    echo "COMPILE FALHOU."

    exit 3
fi

echo "COMPILE=PASS"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh
then

    echo "RELEASE CHECK FALHOU."

    exit 4
fi


# =====================================================
# 2. VIDEO.PY HASH
# =====================================================

VIDEO_HASH_BEFORE="$(
    sha256sum video.py \
    | awk '{print $1}'
)"


echo
echo "VIDEO.PY HASH BEFORE:"
echo "$VIDEO_HASH_BEFORE"


# =====================================================
# 3. BACKUP OLD REPORTS
# =====================================================

for F in \
    logs/producao/vi6_47_shadow_runtime_latest.json \
    logs/producao/vi6_50_shadow_compare_latest.json \
    logs/producao/vi6_51_canary_gate_latest.json
do

    if [ -f "$F" ]; then

        cp "$F" \
           "$TESTDIR/$(basename "$F").before"

    fi

done


# =====================================================
# 4. CLEAN ONLY SHADOW SESSION REPORTS
# =====================================================

rm -f \
    logs/producao/vi6_47_shadow_runtime_latest.json \
    logs/producao/vi6_50_shadow_compare_latest.json \
    logs/producao/vi6_51_canary_gate_latest.json


# =====================================================
# 5. EMERGENCY LEGACY FLAG CHECK
# =====================================================

echo
echo "===== VI6.48 EMERGENCY STATUS ====="

if [ -f temp/vi648_force_legacy.flag ]; then

    echo "ERRO:"
    echo "temp/vi648_force_legacy.flag está ativo."
    echo
    echo "O SHADOW seria forçado para LEGACY."
    echo "Não vou apagar o flag automaticamente."

    exit 5

fi


echo "FORCE LEGACY FLAG=NO"


# =====================================================
# 6. MODE PROOF
# =====================================================

echo
echo "===== MODE PROOF ====="

VI647_RENDERER_MODE=SHADOW \
python - <<'PY'
import os

from vi6_48_emergency_rollback import (
    resolve_mode
)


requested = os.getenv(
    "VI647_RENDERER_MODE",
    "LEGACY"
)


effective, reason = resolve_mode(
    requested
)


print(
    "REQUESTED:",
    requested
)

print(
    "EFFECTIVE:",
    effective
)

print(
    "REASON:",
    reason
)


if effective != "SHADOW":

    raise SystemExit(
        "SHADOW_MODE_NOT_AVAILABLE"
    )
PY


if [ "$?" -ne 0 ]; then
    exit 6
fi


# =====================================================
# 7. REAL PRODUCTION PIPELINE IN SHADOW
# =====================================================

echo
echo "======================================================"
echo " STARTING REAL SHORT"
echo "======================================================"
echo
echo "VI647_RENDERER_MODE=SHADOW"
echo "LEGACY FILTER REPLACEMENT=NO"
echo "ACTIVE=BLOCKED"
echo


START="$(date +%s)"


VI647_RENDERER_MODE=SHADOW \
./gerar_short.sh


PIPE_STATUS="$?"


END="$(date +%s)"

ELAPSED="$((END - START))"


echo
echo "======================================================"
echo " PIPELINE FINISHED"
echo "======================================================"

echo "PIPELINE STATUS=$PIPE_STATUS"

echo "ELAPSED SECONDS=$ELAPSED"


# =====================================================
# 8. VIDEO.PY MUST NOT CHANGE
# =====================================================

VIDEO_HASH_AFTER="$(
    sha256sum video.py \
    | awk '{print $1}'
)"


echo
echo "===== VIDEO.PY INTEGRITY ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"

echo "AFTER =$VIDEO_HASH_AFTER"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_AFTER" ]; then

    echo
    echo "CRITICAL:"
    echo "video.py mudou durante SHADOW."

    exit 20
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 9. VI6.50 SHADOW REPORT
# =====================================================

echo
echo "===== VI6.50 REAL SHADOW REPORT ====="

python - <<'PY'
import json
import os


path = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_50_shadow_compare_latest.json"
)


if not os.path.exists(
    path
):

    print(
        "VI6.50 REPORT=MISSING"
    )

    raise SystemExit(0)


with open(
    path,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(
        f
    )


summary = data.get(
    "summary",
    {}
)


print(
    "UNIQUE EVENTS:",
    summary.get(
        "unique_events"
    )
)

print(
    "UNIQUE SCENES:",
    summary.get(
        "unique_scenes"
    )
)

print(
    "STATUSES:",
    summary.get(
        "statuses"
    )
)

print(
    "HOLDS:",
    summary.get(
        "holds"
    )
)

print(
    "COMMAND MUTATIONS:",
    summary.get(
        "command_mutations"
    )
)

print(
    "FILTER REPLACEMENTS:",
    summary.get(
        "filter_replacements"
    )
)


print()
print(
    "===== PER-SCENE ====="
)


events = (
    summary.get(
        "events"
    )
    or []
)


events = sorted(
    events,
    key=lambda x: (
        x.get(
            "scene"
        )
        if isinstance(
            x.get(
                "scene"
            ),
            int
        )
        else 999
    )
)


for event in events:

    print(
        "SCENE",
        event.get(
            "scene"
        ),

        "|",
        event.get(
            "branch"
        ),

        "|",
        event.get(
            "status"
        ),

        "| duration=",
        event.get(
            "duration_seconds"
        ),

        "| contract=",
        event.get(
            "match_reason"
        ),

        "| blockers=",
        event.get(
            "blockers"
        ),
    )
PY


# =====================================================
# 10. VI6.51 REAL GATE
# =====================================================

echo
echo "===== VI6.51 REAL CANARY GATE ====="

python \
    vi6_51_canary_gate.py \
    --real


# =====================================================
# 11. FINAL COMBINED RESULT
# =====================================================

echo
echo "======================================================"
echo " VI6.51 FINAL SHADOW CERTIFICATION"
echo "======================================================"

python - <<'PY'
import json
import os


BASE = os.path.expanduser(
    "~/ShortAutoPro/logs/producao"
)


def load(
    filename,
    key
):

    path = os.path.join(
        BASE,
        filename
    )


    if not os.path.exists(
        path
    ):

        return {}


    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
            ).get(
                key,
                {}
            )


    except Exception:

        return {}


shadow = load(
    "vi6_50_shadow_compare_latest.json",
    "summary"
)


gate = load(
    "vi6_51_canary_gate_latest.json",
    "gate"
)


print(
    "SHADOW UNIQUE SCENES:",
    shadow.get(
        "unique_scenes"
    )
)

print(
    "SHADOW STATUSES:",
    shadow.get(
        "statuses"
    )
)

print(
    "SHADOW HOLDS:",
    shadow.get(
        "holds"
    )
)

print(
    "COMMAND MUTATIONS:",
    shadow.get(
        "command_mutations"
    )
)

print(
    "FILTER REPLACEMENTS:",
    shadow.get(
        "filter_replacements"
    )
)


print()
print(
    "VI6.51 STATUS:",
    gate.get(
        "status"
    )
)

print(
    "BLOCKERS:",
    gate.get(
        "blockers"
    )
)

print(
    "WARNINGS:",
    gate.get(
        "warnings"
    )
)

print(
    "NEXT STAGE ALLOWED:",
    gate.get(
        "next_stage_allowed"
    )
)

print(
    "ACTIVE CANARY AUTHORIZED:",
    gate.get(
        "active_canary_authorized"
    )
)


print()
print(
    "DEFAULT RENDERER=LEGACY"
)

print(
    "SHADOW MUTATION=NO"
)

print(
    "ACTIVE RENDERER=BLOCKED"
)
PY


# =====================================================
# 12. COPY REPORTS INTO SESSION FOLDER
# =====================================================

for F in \
    logs/producao/vi6_47_shadow_runtime_latest.json \
    logs/producao/vi6_50_shadow_compare_latest.json \
    logs/producao/vi6_51_canary_gate_latest.json
do

    if [ -f "$F" ]; then

        cp "$F" \
           "$TESTDIR/$(basename "$F")"

    fi

done


echo
echo "SESSION REPORTS:"
echo "$TESTDIR"


echo
echo "======================================================"
echo " SHADOW TEST COMPLETE"
echo "======================================================"
echo
echo "VIDEO.PY MODIFIED=NO"
echo "VI6 FILTER REPLACED=NO"
echo "ACTIVE RENDERER=NO"
echo
echo "Se o pipeline terminou normalmente,"
echo "o vídeo gerado é 100% pelo caminho LEGACY."
echo


exit "$PIPE_STATUS"
