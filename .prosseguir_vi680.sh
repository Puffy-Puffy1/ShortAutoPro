#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "======================================================"
echo " VI6.70 -> VI6.80 SAFE CONTINUATION"
echo "======================================================"

echo
echo "===== COMPILE ====="

python -m py_compile \
    vi6_61_motion_filter_compiler.py \
    vi6_65_canary_candidate_selector.py \
    vi6_66_canary_filter_preview.py \
    vi6_70_master_canary_gate.py \
    || exit 10

echo "COMPILE=PASS"


echo
echo "===== VI6.70 CURRENT STATE ====="

python vi6_70_master_canary_gate.py --real \
    || exit 11


echo
echo "===== HARD AUTHORIZATION CHECK ====="

python - <<'PY'
import json
from pathlib import Path

base = Path.home() / "ShortAutoPro"

path = (
    base
    / "logs"
    / "producao"
    / "vi6_70_master_canary_gate_latest.json"
)

if not path.exists():
    raise SystemExit(
        "VI6.70 REPORT MISSING"
    )

gate = json.loads(
    path.read_text(
        encoding="utf-8"
    )
)["gate"]

candidate = (
    gate.get("candidate")
    or {}
)

preview = (
    gate.get("filter_preview")
    or {}
)

vf = (
    preview.get(
        "proposed_vi6_vf"
    )
    or ""
)

blockers = []

if gate.get("status") not in {
    "CANARY_PREVIEW_READY",
    "CANARY_PREVIEW_READY_WITH_WARNINGS",
}:
    blockers.append(
        "vi670_not_ready"
    )

if gate.get("blockers"):
    blockers.append(
        "vi670_has_blockers"
    )

if not isinstance(
    candidate.get("scene"),
    int
):
    blockers.append(
        "scene_invalid"
    )

if candidate.get(
    "role"
) != "CONTEXT":
    blockers.append(
        "candidate_not_context"
    )

if preview.get(
    "status"
) != "PREVIEW_READY":
    blockers.append(
        "preview_not_ready"
    )

if not preview.get(
    "different_from_legacy"
):
    blockers.append(
        "filter_not_different"
    )

for required in (
    "scale=",
    "crop=",
    "zoompan=",
    "setsar=1",
    "format=yuv420p",
):

    if required not in vf:
        blockers.append(
            "missing_" + required
        )

print(
    "STATUS:",
    gate.get("status")
)

print(
    "SCENE:",
    candidate.get("scene")
)

print(
    "ROLE:",
    candidate.get("role")
)

print(
    "MOTION:",
    candidate.get(
        "recommended_motion_profile"
    )
)

print(
    "PREVIEW:",
    preview.get("status")
)

print(
    "ZOOMPAN:",
    "zoompan=" in vf
)

print(
    "DIFFERENT:",
    preview.get(
        "different_from_legacy"
    )
)

print(
    "BLOCKERS:",
    blockers
)

if blockers:
    raise SystemExit(1)

print()
print(
    "VI6.70 HARD AUTHORIZATION=PASS"
)
PY

if [ "$?" -ne 0 ]; then

    echo
    echo "======================================================"
    echo " STOPPED SAFELY"
    echo "======================================================"
    echo
    echo "VI6.71-6.80 NÃO será executado."
    echo "Nenhum FFmpeg foi iniciado."
    echo "Me envie a saída acima."

    exit 12
fi


echo
echo "===== VIDEO.PY PRE-CANARY HASH ====="

HASH_BEFORE="$(
    sha256sum video.py |
    awk '{print $1}'
)"

echo "$HASH_BEFORE"


echo
echo "======================================================"
echo " STARTING VI6.71 -> VI6.80"
echo "======================================================"
echo

if [ ! -x ./.mega_update_vi671_vi680.sh ]; then

    echo "ERRO:"
    echo ".mega_update_vi671_vi680.sh ausente."

    exit 13
fi


./.mega_update_vi671_vi680.sh

STATUS="$?"


echo
echo "===== VIDEO.PY POST-CANARY HASH ====="

HASH_AFTER="$(
    sha256sum video.py |
    awk '{print $1}'
)"

echo "$HASH_AFTER"


if [ "$HASH_BEFORE" != "$HASH_AFTER" ]; then

    echo
    echo "CRITICAL:"
    echo "video.py mudou durante a etapa."
    echo
    echo "Não prossiga."

    exit 20
fi


echo "VIDEO.PY UNCHANGED=YES"


echo
echo "======================================================"
echo " VI6.80 FINAL STATE"
echo "======================================================"

python - <<'PY'
import json
from pathlib import Path

base = (
    Path.home()
    / "ShortAutoPro"
)

path = (
    base
    / "logs"
    / "producao"
    / "vi6_80_master_runtime_gate_latest.json"
)

if not path.exists():

    print(
        "VI6.80 REPORT=MISSING"
    )

    raise SystemExit(0)


gate = json.loads(
    path.read_text(
        encoding="utf-8"
    )
).get(
    "gate",
    {}
)


print(
    "STATUS:",
    gate.get("status")
)

print(
    "SCENE:",
    gate.get("scene")
)

print(
    "TECHNICAL CERTIFICATION:",
    gate.get(
        "technical_certification"
    )
)

print(
    "BLOCKERS:",
    gate.get("blockers")
)

print(
    "WARNINGS:",
    gate.get("warnings")
)

print(
    "LEGACY PREVIEW:",
    gate.get(
        "legacy_preview"
    )
)

print(
    "VI6 PREVIEW:",
    gate.get(
        "vi6_preview"
    )
)

print(
    "HUMAN VISUAL REVIEW REQUIRED:",
    gate.get(
        "human_visual_review_required"
    )
)

print(
    "RUNTIME CANARY AUTHORIZED:",
    gate.get(
        "runtime_canary_authorized"
    )
)

print(
    "FULL ACTIVE AUTHORIZED:",
    gate.get(
        "full_active_authorized"
    )
)

print(
    "ACTIVE RENDERER:",
    gate.get(
        "active_renderer"
    )
)
PY


echo
echo "======================================================"
echo " SAFE CONTINUATION COMPLETE"
echo "======================================================"
echo "SCRIPT STATUS=$STATUS"
echo "VIDEO.PY MODIFIED=NO"
echo "FULL ACTIVE=LOCKED"

exit "$STATUS"
