#!/data/data/com.termux/files/usr/bin/bash

set -u

cd "$HOME/ShortAutoPro" || exit 1


echo
echo "======================================================"
echo " VI6.60 MASTER SHADOW CERTIFICATION"
echo "======================================================"
echo
echo "REAL VIDEO WILL BE GENERATED"
echo "RENDER PATH = LEGACY"
echo "VI6 = OBSERVATION ONLY"
echo


rm -f \
    logs/producao/vi6_60_shadow_session_latest.json \
    logs/producao/vi6_60_master_gate_latest.json


if [ ! -x ./.executar_shadow_vi651.sh ]; then

    echo "ERRO: .executar_shadow_vi651.sh não encontrado."

    exit 2
fi


./.executar_shadow_vi651.sh

PIPE_STATUS="$?"


echo
echo "======================================================"
echo " VI6.60 MASTER GATE"
echo "======================================================"

python \
    vi6_60_master_gate.py \
    --real


echo
echo "======================================================"
echo " VI6.60 REAL SESSION SUMMARY"
echo "======================================================"

python - <<'PY'
import json
from pathlib import Path


base = (
    Path.home()
    / "ShortAutoPro"
    / "logs"
    / "producao"
)


session_path = (
    base
    / "vi6_60_shadow_session_latest.json"
)


gate_path = (
    base
    / "vi6_60_master_gate_latest.json"
)


if session_path.exists():

    session = json.loads(
        session_path.read_text(
            encoding="utf-8"
        )
    ).get(
        "session",
        {}
    )


    print(
        "UNIQUE SCENES:",
        session.get(
            "unique_scenes"
        )
    )


    print(
        "IDENTITY HOLDS:",
        session.get(
            "identity_holds"
        )
    )


    print(
        "NATIVE VIDEO HOLDS:",
        session.get(
            "native_video_holds"
        )
    )


    print(
        "DIVERSITY:",
        (
            session.get(
                "diversity"
            )
            or {}
        ).get(
            "status"
        )
    )


    print(
        "RHYTHM:",
        (
            session.get(
                "rhythm"
            )
            or {}
        ).get(
            "status"
        )
    )


    perf = (
        session.get(
            "performance"
        )
        or {}
    )


    print(
        "PERFORMANCE COMPLEXITY:",
        perf.get(
            "estimated_complexity"
        )
    )


    print()
    print(
        "===== SCENE INTELLIGENCE ====="
    )


    for event in (
        session.get(
            "events"
        )
        or []
    ):

        mega = (
            event.get(
                "mega"
            )
            or {}
        )


        contract = (
            mega.get(
                "contract"
            )
            or {}
        )


        motion = (
            mega.get(
                "motion"
            )
            or {}
        )


        recovery = (
            mega.get(
                "self_healing"
            )
            or {}
        )


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

            "| role=",
            contract.get(
                "role"
            ),

            "| motion=",
            motion.get(
                "profile"
            ),

            "| recover=",
            recovery.get(
                "recommended_action"
            ),

            "| interval=",
            mega.get(
                "inter_event_wall_seconds"
            ),
        )


if gate_path.exists():

    gate = json.loads(
        gate_path.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )


    print()
    print(
        "===== MASTER RESULT ====="
    )


    print(
        "MASTER STATUS:",
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
        "CANARY BUILD ALLOWED:",
        gate.get(
            "canary_build_allowed"
        )
    )


    print(
        "ACTIVE CANARY AUTHORIZED:",
        gate.get(
            "active_canary_authorized"
        )
    )


    print(
        "ACTIVE RENDERER:",
        gate.get(
            "active_renderer"
        )
    )


print()
print(
    "LEGACY FILTER REPLACEMENTS=0"
)

print(
    "ACTIVE=LOCKED"
)
PY


exit "$PIPE_STATUS"
