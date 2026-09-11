#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/mega_vi681_vi690_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " SHORTAUTOPRO MEGA UPDATE IV"
echo " VI6.81 -> VI6.90"
echo " REAL SINGLE-SCENE PRODUCTION CANARY"
echo "======================================================"
echo
echo "CANARY SCENE = 5"
echo "OTHER SCENES = LEGACY"
echo "FULL ACTIVE = LOCKED"
echo


# =====================================================
# 0. REQUIREMENTS
# =====================================================

REQUIRED="
video.py
gerar_short.sh
vi6_47_renderer_switch.py
vi6_48_emergency_rollback.py
vi6_61_motion_filter_compiler.py
vi6_67_scene_rollback_contract.py
vi6_80_master_runtime_gate.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F ausente."
        exit 2
    fi
done


GATE80="logs/producao/vi6_80_master_runtime_gate_latest.json"

if [ ! -f "$GATE80" ]; then
    echo "ERRO: VI6.80 master gate ausente."
    exit 3
fi


VIDEO_HASH_BEFORE="$(
    sha256sum video.py |
    awk '{print $1}'
)"


# =====================================================
# 1. HARD PRECHECK VI6.80
# =====================================================

echo
echo "===== VI6.80 HARD PRECHECK ====="

python - <<'PY'
import json
from pathlib import Path

base = Path.home() / "ShortAutoPro"

gate = json.loads(
    (
        base
        / "logs/producao/"
          "vi6_80_master_runtime_gate_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["gate"]

blockers = []

if gate.get("status") not in {
    "READY_FOR_HUMAN_VISUAL_REVIEW",
    "READY_FOR_HUMAN_VISUAL_REVIEW_WITH_WARNINGS",
}:
    blockers.append(
        "vi680_not_ready"
    )

if gate.get("scene") != 5:
    blockers.append(
        "unexpected_canary_scene"
    )

if gate.get("blockers"):
    blockers.append(
        "vi680_has_blockers"
    )

if gate.get(
    "technical_certification"
) not in {
    "TECHNICALLY_CERTIFIED",
    "TECHNICALLY_CERTIFIED_WITH_WARNINGS",
}:
    blockers.append(
        "technical_certification_missing"
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
    "TECHNICAL:",
    gate.get(
        "technical_certification"
    )
)

print(
    "BLOCKERS:",
    blockers
)

if blockers:
    raise SystemExit(1)

print(
    "VI6.80 PRECHECK=PASS"
)
PY

if [ "$?" -ne 0 ]; then
    exit 4
fi


# =====================================================
# 2. BACKUPS
# =====================================================

FILES="
vi6_81_visual_approval.py
vi6_82_runtime_canary_switch.py
vi6_83_scene_lock.py
vi6_84_canary_fallback.py
vi6_85_canary_output_validator.py
vi6_86_legacy_recovery.py
vi6_87_canary_telemetry.py
vi6_88_production_canary_gate.py
vi6_89_runtime_canary_adapter.py
vi6_90_master_canary_certification.py
vi6_47_renderer_switch.py
video.py
"

for F in $FILES
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.81-6.90"
    echo "======================================"

    for F in $FILES
    do

        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi

    done

    echo "Rollback concluído."
}


# =====================================================
# 3. VI6.81 VISUAL APPROVAL
# =====================================================

cat > vi6_81_visual_approval.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.81"


APPROVAL = {

    "scene": 5,

    "profile":
        "HORIZONTAL_DISCOVERY",

    "status":
        "APPROVED",

    "legacy_vs_vi6":
        "VI6_WINNER",

    "human_visual_review":
        True,

    "approved_for_runtime_canary":
        True,

    "approved_for_full_active":
        False,
}


def get():

    return {
        "version":
            VERSION,

        **APPROVAL,
    }


def self_test():

    result = get()

    assert (
        result[
            "approved_for_runtime_canary"
        ]
        is True
    )

    assert (
        result[
            "approved_for_full_active"
        ]
        is False
    )

    print(
        "VI6.81 VISUAL APPROVAL=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 4. VI6.82 RUNTIME CANARY SWITCH
# =====================================================

cat > vi6_82_runtime_canary_switch.py <<'PY'
#!/usr/bin/env python3

import os

from vi6_81_visual_approval import (
    get as visual_approval
)


VERSION = "6.82"


CANARY_ENV = (
    "VI682_CANARY_MODE"
)


def enabled():

    return (
        os.getenv(
            CANARY_ENV,
            "OFF"
        ).upper()
        == "ON"
    )


def should_use_vi6(
    scene
):

    approval = visual_approval()


    if not enabled():

        return False


    if not approval.get(
        "approved_for_runtime_canary"
    ):

        return False


    return (
        scene
        == approval.get(
            "scene"
        )
    )


def self_test():

    assert VERSION == "6.82"

    print(
        "VI6.82 RUNTIME CANARY SWITCH=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 5. VI6.83 EXACT SCENE LOCK
# =====================================================

cat > vi6_83_scene_lock.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.83"


CANARY_SCENE = 5


def validate(
    scene
):

    return {

        "version":
            VERSION,

        "scene":
            scene,

        "locked_scene":
            CANARY_SCENE,

        "allowed":
            (
                scene
                == CANARY_SCENE
            ),

        "other_scenes_allowed":
            False,
    }


def self_test():

    assert (
        validate(
            5
        )["allowed"]
        is True
    )

    assert (
        validate(
            4
        )["allowed"]
        is False
    )

    print(
        "VI6.83 SCENE LOCK=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 6. VI6.84 FALLBACK POLICY
# =====================================================

cat > vi6_84_canary_fallback.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.84"


FAILURES = {
    "compile_failure",
    "filter_validation_failure",
    "ffmpeg_failure",
    "output_missing",
    "duration_invalid",
    "resolution_invalid",
    "unexpected_exception",
}


def decide(
    failure=None
):

    if failure is None:

        return {
            "version":
                VERSION,

            "fallback":
                False,

            "action":
                "KEEP_VI6_CANARY",
        }


    return {
        "version":
            VERSION,

        "fallback":
            True,

        "action":
            "USE_LEGACY_FOR_SAME_SCENE",

        "reason":
            failure,
    }


def self_test():

    assert (
        decide(
            "ffmpeg_failure"
        )["fallback"]
        is True
    )

    print(
        "VI6.84 CANARY FALLBACK=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 7. VI6.85 OUTPUT VALIDATOR
# =====================================================

cat > vi6_85_canary_output_validator.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.85"


def validate_plan(
    vf,
    duration
):

    blockers = []


    if not isinstance(
        vf,
        str
    ):

        blockers.append(
            "filter_missing"
        )


    else:

        required = (
            "scale=",
            "crop=",
            "zoompan=",
            "setsar=1",
            "format=yuv420p",
        )


        for token in required:

            if token not in vf:

                blockers.append(
                    "missing_" + token
                )


    try:

        duration = float(
            duration
        )

    except Exception:

        duration = None


    if (
        duration is None
        or duration <= 0
        or duration > 8
    ):

        blockers.append(
            "duration_invalid"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            blockers,
    }


def self_test():

    vf = (
        "scale=1200:2133,"
        "crop=1200:2133,"
        "zoompan=z='1.01':"
        "d=90:s=1080x1920:fps=30,"
        "setsar=1,"
        "format=yuv420p"
    )


    assert (
        validate_plan(
            vf,
            3
        )["status"]
        == "PASS"
    )


    print(
        "VI6.85 OUTPUT VALIDATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 8. VI6.86 LEGACY RECOVERY
# =====================================================

cat > vi6_86_legacy_recovery.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.86"


def recover(
    original_command,
    reason
):

    return {

        "version":
            VERSION,

        "status":
            "RECOVERED_TO_LEGACY",

        "reason":
            reason,

        "command":
            original_command,

        "same_object":
            True,

        "global_abort":
            False,
    }


def self_test():

    command = [
        "ffmpeg"
    ]


    result = recover(
        command,
        "test"
    )


    assert (
        result["command"]
        is command
    )


    print(
        "VI6.86 LEGACY RECOVERY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 9. VI6.87 TELEMETRY
# =====================================================

cat > vi6_87_canary_telemetry.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "6.87"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


REPORT = (
    BASE
    / "logs/producao/"
      "vi6_87_runtime_canary_latest.json"
)


_EVENTS = []


def record(
    event
):

    _EVENTS.append(
        dict(
            event
            or {}
        )
    )


    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    REPORT.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "version":
                    VERSION,

                "events":
                    _EVENTS,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    assert VERSION == "6.87"

    print(
        "VI6.87 CANARY TELEMETRY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 10. VI6.88 PRODUCTION CANARY GATE
# =====================================================

cat > vi6_88_production_canary_gate.py <<'PY'
#!/usr/bin/env python3

from vi6_81_visual_approval import (
    get as approval
)


VERSION = "6.88"


def evaluate():

    a = approval()

    blockers = []


    if a.get(
        "status"
    ) != "APPROVED":

        blockers.append(
            "visual_not_approved"
        )


    if not a.get(
        "approved_for_runtime_canary"
    ):

        blockers.append(
            "runtime_canary_not_approved"
        )


    if a.get(
        "approved_for_full_active"
    ):

        blockers.append(
            "full_active_must_remain_locked"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "CANARY_ALLOWED"
                if not blockers
                else "HOLD"
            ),

        "scene":
            a.get(
                "scene"
            ),

        "profile":
            a.get(
                "profile"
            ),

        "blockers":
            blockers,

        "full_active":
            False,
    }


def self_test():

    result = evaluate()

    assert (
        result["status"]
        == "CANARY_ALLOWED"
    )

    print(
        "VI6.88 PRODUCTION CANARY GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 11. VI6.89 RUNTIME COMMAND ADAPTER
# =====================================================

cat > vi6_89_runtime_canary_adapter.py <<'PY'
#!/usr/bin/env python3

import copy

from vi6_49_real_command_mapper import (
    map_command
)

from vi6_61_motion_filter_compiler import (
    compile_filter
)

from vi6_82_runtime_canary_switch import (
    should_use_vi6
)

from vi6_83_scene_lock import (
    validate as scene_lock
)

from vi6_84_canary_fallback import (
    decide as fallback_decide
)

from vi6_85_canary_output_validator import (
    validate_plan
)

from vi6_87_canary_telemetry import (
    record
)


VERSION = "6.89"


PROFILE = (
    "HORIZONTAL_DISCOVERY"
)


def _replace_vf(
    command,
    new_vf
):

    result = list(
        command
    )


    try:

        index = result.index(
            "-vf"
        )

    except ValueError:

        return None


    if (
        index + 1
        >= len(result)
    ):

        return None


    result[
        index + 1
    ] = new_vf


    return result


def adapt(
    command
):

    original = command


    try:

        mapped = map_command(
            command
        )


        scene = mapped.get(
            "scene"
        )


        branch = mapped.get(
            "branch"
        )


        duration = mapped.get(
            "duration_seconds"
        )


        if not should_use_vi6(
            scene
        ):

            record(
                {
                    "scene":
                        scene,

                    "action":
                        "LEGACY",

                    "reason":
                        "not_canary_scene",

                    "command_mutated":
                        False,
                }
            )

            return original


        lock = scene_lock(
            scene
        )


        if not lock.get(
            "allowed"
        ):

            record(
                {
                    "scene":
                        scene,

                    "action":
                        "LEGACY",

                    "reason":
                        "scene_lock_denied",

                    "command_mutated":
                        False,
                }
            )

            return original


        if branch != "STILL":

            record(
                {
                    "scene":
                        scene,

                    "action":
                        "LEGACY",

                    "reason":
                        "canary_not_still",

                    "command_mutated":
                        False,
                }
            )

            return original


        compiled = compile_filter(
            PROFILE,
            duration,
            30
        )


        if (
            compiled.get(
                "status"
            )
            != "COMPILED"
        ):

            fb = fallback_decide(
                "compile_failure"
            )


            record(
                {
                    "scene":
                        scene,

                    "action":
                        "LEGACY_FALLBACK",

                    "reason":
                        fb.get(
                            "reason"
                        ),

                    "command_mutated":
                        False,
                }
            )

            return original


        vf = compiled.get(
            "vf"
        )


        validation = validate_plan(
            vf,
            duration
        )


        if (
            validation.get(
                "status"
            )
            != "PASS"
        ):

            record(
                {
                    "scene":
                        scene,

                    "action":
                        "LEGACY_FALLBACK",

                    "reason":
                        "filter_validation_failure",

                    "blockers":
                        validation.get(
                            "blockers"
                        ),

                    "command_mutated":
                        False,
                }
            )

            return original


        adapted = _replace_vf(
            original,
            vf
        )


        if adapted is None:

            record(
                {
                    "scene":
                        scene,

                    "action":
                        "LEGACY_FALLBACK",

                    "reason":
                        "vf_argument_not_found",

                    "command_mutated":
                        False,
                }
            )

            return original


        record(
            {
                "scene":
                    scene,

                "action":
                    "VI6_CANARY",

                "profile":
                    PROFILE,

                "command_mutated":
                    True,

                "scope":
                    "ONE_SCENE_ONLY",
            }
        )


        return adapted


    except Exception as exc:

        record(
            {
                "scene":
                    None,

                "action":
                    "LEGACY_FALLBACK",

                "reason":
                    (
                        "unexpected_exception:"
                        + type(
                            exc
                        ).__name__
                    ),

                "command_mutated":
                    False,
            }
        )


        return original


def self_test():

    assert VERSION == "6.89"

    print(
        "VI6.89 RUNTIME CANARY ADAPTER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 12. VI6.90 MASTER CERTIFICATION
# =====================================================

cat > vi6_90_master_canary_certification.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "6.90"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


REPORT87 = (
    BASE
    / "logs/producao/"
      "vi6_87_runtime_canary_latest.json"
)


OUTPUT = (
    BASE
    / "logs/producao/"
      "vi6_90_master_canary_latest.json"
)


def evaluate():

    blockers = []
    warnings = []


    try:

        data = json.loads(
            REPORT87.read_text(
                encoding="utf-8"
            )
        )


        events = (
            data.get(
                "events"
            )
            or []
        )


    except Exception:

        events = []

        blockers.append(
            "runtime_canary_report_missing"
        )


    vi6_events = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI6_CANARY"
    ]


    wrong_scene = [
        e
        for e in vi6_events
        if e.get(
            "scene"
        ) != 5
    ]


    if wrong_scene:

        blockers.append(
            "vi6_used_outside_scene_5"
        )


    if len(
        vi6_events
    ) != 1:

        blockers.append(
            "requires_exactly_one_vi6_scene"
        )


    fallbacks = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_FALLBACK"
    ]


    if fallbacks:

        warnings.append(
            "canary_fallback_occurred"
        )


    status = (
        "HOLD"
        if blockers
        else (
            "CERTIFIED_WITH_WARNINGS"
            if warnings
            else "CERTIFIED"
        )
    )


    result = {

        "version":
            VERSION,

        "status":
            status,

        "vi6_scene_count":
            len(
                vi6_events
            ),

        "vi6_scenes":
            [
                e.get(
                    "scene"
                )
                for e in vi6_events
            ],

        "fallback_count":
            len(
                fallbacks
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "single_scene_canary":
            (
                not blockers
            ),

        "full_active_authorized":
            False,
    }


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


def self_test():

    assert VERSION == "6.90"

    print(
        "VI6.90 MASTER CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 13. PATCH VI6.47 SWITCH
# =====================================================

echo
echo "===== PATCHING VI6.47 CANARY ROUTE ====="

python - <<'PY'
from pathlib import Path


p = Path(
    "vi6_47_renderer_switch.py"
)


s = p.read_text(
    encoding="utf-8"
)


marker = (
    "# VI6.89 SINGLE-SCENE PRODUCTION CANARY"
)


if marker in s:

    print(
        "VI6.89 ROUTE ALREADY PRESENT"
    )


else:

    addition = r'''

# VI6.89 SINGLE-SCENE PRODUCTION CANARY
_vi647_original_adapt_scene_command_vi689 = (
    adapt_scene_command
)


def adapt_scene_command(
    command,
    context=None
):

    import os


    if (
        os.getenv(
            "VI682_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
    ):

        try:

            from vi6_89_runtime_canary_adapter import (
                adapt as _vi689_adapt
            )


            return _vi689_adapt(
                command
            )


        except Exception:

            return command


    return (
        _vi647_original_adapt_scene_command_vi689(
            command,
            context
        )
    )
'''


    p.write_text(
        s + addition,
        encoding="utf-8"
    )


    print(
        "VI6.89 ROUTE=INSTALLED"
    )
PY


# =====================================================
# 14. COMPILE
# =====================================================

echo
echo "===== COMPILE ====="

if ! python -m py_compile \
    vi6_81_visual_approval.py \
    vi6_82_runtime_canary_switch.py \
    vi6_83_scene_lock.py \
    vi6_84_canary_fallback.py \
    vi6_85_canary_output_validator.py \
    vi6_86_legacy_recovery.py \
    vi6_87_canary_telemetry.py \
    vi6_88_production_canary_gate.py \
    vi6_89_runtime_canary_adapter.py \
    vi6_90_master_canary_certification.py \
    vi6_47_renderer_switch.py \
    video.py
then

    rollback
    exit 10
fi


echo "COMPILE=PASS"


# =====================================================
# 15. SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

python vi6_81_visual_approval.py || {
    rollback
    exit 11
}

python vi6_82_runtime_canary_switch.py || {
    rollback
    exit 12
}

python vi6_83_scene_lock.py || {
    rollback
    exit 13
}

python vi6_84_canary_fallback.py || {
    rollback
    exit 14
}

python vi6_85_canary_output_validator.py || {
    rollback
    exit 15
}

python vi6_86_legacy_recovery.py || {
    rollback
    exit 16
}

python vi6_87_canary_telemetry.py || {
    rollback
    exit 17
}

python vi6_88_production_canary_gate.py || {
    rollback
    exit 18
}

python vi6_89_runtime_canary_adapter.py || {
    rollback
    exit 19
}

python vi6_90_master_canary_certification.py || {
    rollback
    exit 20
}


# =====================================================
# 16. VIDEO.PY INTEGRITY
# =====================================================

VIDEO_HASH_AFTER="$(
    sha256sum video.py |
    awk '{print $1}'
)"


echo
echo "===== VIDEO.PY INTEGRITY ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"
echo "AFTER =$VIDEO_HASH_AFTER"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_AFTER" ]; then

    echo "CRITICAL: video.py mudou."

    rollback
    exit 21
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 17. RELEASE CHECK
# =====================================================

./release_check.sh || {
    rollback
    exit 22
}


# =====================================================
# 18. REAL PRODUCTION CANARY
# =====================================================

echo
echo "======================================================"
echo " STARTING REAL SINGLE-SCENE CANARY SHORT"
echo "======================================================"
echo
echo "SCENE 5 = VI6 TRY"
echo "ALL OTHERS = LEGACY"
echo


rm -f \
    logs/producao/vi6_87_runtime_canary_latest.json \
    logs/producao/vi6_90_master_canary_latest.json


VI682_CANARY_MODE=ON \
VI647_RENDERER_MODE=LEGACY \
./gerar_short.sh

PIPE_STATUS="$?"


echo
echo "PIPELINE STATUS=$PIPE_STATUS"


# =====================================================
# 19. CANARY CERTIFICATION
# =====================================================

echo
echo "===== VI6.90 REAL CERTIFICATION ====="

python - <<'PY'
import json
from pathlib import Path

from vi6_90_master_canary_certification import (
    evaluate
)


result = evaluate()


print(
    "STATUS:",
    result.get(
        "status"
    )
)

print(
    "VI6 SCENE COUNT:",
    result.get(
        "vi6_scene_count"
    )
)

print(
    "VI6 SCENES:",
    result.get(
        "vi6_scenes"
    )
)

print(
    "FALLBACK COUNT:",
    result.get(
        "fallback_count"
    )
)

print(
    "BLOCKERS:",
    result.get(
        "blockers"
    )
)

print(
    "WARNINGS:",
    result.get(
        "warnings"
    )
)

print(
    "SINGLE-SCENE CANARY:",
    result.get(
        "single_scene_canary"
    )
)

print(
    "FULL ACTIVE AUTHORIZED:",
    result.get(
        "full_active_authorized"
    )
)
PY


# =====================================================
# 20. FINAL INTEGRITY
# =====================================================

VIDEO_HASH_FINAL="$(
    sha256sum video.py |
    awk '{print $1}'
)"


echo
echo "===== FINAL VIDEO.PY INTEGRITY ====="

echo "ORIGINAL=$VIDEO_HASH_BEFORE"
echo "FINAL   =$VIDEO_HASH_FINAL"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_FINAL" ]; then

    echo "CRITICAL:"
    echo "video.py mudou durante produção."

    exit 30
fi


echo "VIDEO.PY UNCHANGED=YES"


echo
echo "======================================================"
echo " VI6.81 -> VI6.90 COMPLETE"
echo "======================================================"
echo
echo "PIPELINE STATUS=$PIPE_STATUS"
echo "SCENE 5 CANARY ATTEMPTED=YES"
echo "FULL ACTIVE=LOCKED"
echo
echo "REPORT:"
echo "logs/producao/vi6_90_master_canary_latest.json"
echo

exit "$PIPE_STATUS"
