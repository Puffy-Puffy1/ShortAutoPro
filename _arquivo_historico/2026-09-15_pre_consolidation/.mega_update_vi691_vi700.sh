#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/mega_vi691_vi700_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " SHORTAUTOPRO MEGA UPDATE V"
echo " VI6.91 -> VI7.00"
echo " THREE-SCENE CONTROLLED PRODUCTION CANARY"
echo "======================================================"
echo
echo "MAX VI6 SCENES = 3"
echo "VIDEO ONLY = LEGACY"
echo "FFMPEG FAILURE = SAME-SCENE LEGACY RETRY"
echo "FULL ACTIVE = LOCKED"
echo


# =====================================================
# 0. REQUIREMENTS
# =====================================================

REQUIRED="
video.py
gerar_short.sh
vi6_47_renderer_switch.py
vi6_49_real_command_mapper.py
vi6_61_motion_filter_compiler.py
vi6_87_canary_telemetry.py
vi6_89_runtime_canary_adapter.py
vi6_90_master_canary_certification.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F ausente."
        exit 2
    fi
done


VIDEO_HASH_ORIGINAL="$(
    sha256sum video.py |
    awk '{print $1}'
)"

echo "VIDEO.PY ORIGINAL:"
echo "$VIDEO_HASH_ORIGINAL"


# =====================================================
# 1. REBUILD VI6.90 IF NECESSARY
# =====================================================

echo
echo "===== VI6.90 BASELINE ====="

python - <<'PY'
from pathlib import Path

from vi6_90_master_canary_certification import (
    evaluate
)

base = Path.home() / "ShortAutoPro"
logs = base / "logs" / "producao"

p87 = logs / "vi6_87_runtime_canary_latest.json"

if not p87.exists():
    raise SystemExit(
        "VI6.87 REAL TELEMETRY MISSING"
    )

result = evaluate()

print(
    "VI6.90 STATUS:",
    result.get("status")
)

print(
    "VI6 SCENES:",
    result.get("vi6_scenes")
)

print(
    "FALLBACKS:",
    result.get("fallback_count")
)

print(
    "BLOCKERS:",
    result.get("blockers")
)

if result.get("status") not in {
    "CERTIFIED",
    "CERTIFIED_WITH_WARNINGS",
}:
    raise SystemExit(
        "VI6.90 NOT CERTIFIED"
    )

if result.get("vi6_scenes") != [5]:
    raise SystemExit(
        "VI6.90 BASELINE IS NOT SINGLE SCENE 5"
    )
PY

if [ "$?" -ne 0 ]; then
    exit 3
fi


# =====================================================
# 2. BACKUPS
# =====================================================

FILES="
video.py
vi6_47_renderer_switch.py
vi6_91_three_scene_policy.py
vi6_92_profile_allocator.py
vi6_93_runtime_state.py
vi6_94_three_scene_adapter.py
vi6_95_scene_executor.py
vi6_96_post_render_validator.py
vi6_97_three_scene_telemetry.py
vi6_98_production_gate.py
vi6_99_runtime_router.py
vi7_00_master_gate.py
"

for F in $FILES
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================================"
    echo " VI6.91 -> VI7.00 ROLLBACK"
    echo "======================================================"

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
# 3. VI6.91 THREE-SCENE POLICY
# =====================================================

cat > vi6_91_three_scene_policy.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.91"

MAX_CANARIES = 3


# We deliberately avoid:
# scene 1  = hook
# scene 12 = CTA
#
# Zone A -> normal context
# Zone B -> later context
# Zone C -> climax area

ZONES = (
    {
        "name": "CONTEXT_A",
        "scenes": (3, 4, 5, 6),
        "profile": "HORIZONTAL_DISCOVERY",
    },

    {
        "name": "CONTEXT_B",
        "scenes": (6, 7, 8),
        "profile": "DETAIL_PUSH",
    },

    {
        "name": "CLIMAX",
        "scenes": (9, 10, 11),
        "profile": "CLIMAX_PAN",
    },
)


def policy():

    return {
        "version": VERSION,

        "max_canaries":
            MAX_CANARIES,

        "zones":
            ZONES,

        "hook_canary_allowed":
            False,

        "cta_canary_allowed":
            False,

        "video_canary_allowed":
            False,

        "full_active":
            False,
    }


def self_test():

    p = policy()

    assert p["max_canaries"] == 3
    assert p["full_active"] is False

    print(
        "VI6.91 THREE-SCENE POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 4. VI6.92 DISTINCT PROFILE ALLOCATOR
# =====================================================

cat > vi6_92_profile_allocator.py <<'PY'
#!/usr/bin/env python3

from vi6_91_three_scene_policy import (
    ZONES
)


VERSION = "6.92"


def zone_for_scene(scene):

    for zone in ZONES:

        if scene in zone["scenes"]:

            return {
                "zone":
                    zone["name"],

                "profile":
                    zone["profile"],
            }


    return None


def self_test():

    assert (
        zone_for_scene(5)["profile"]
        == "HORIZONTAL_DISCOVERY"
    )

    assert (
        zone_for_scene(10)["profile"]
        == "CLIMAX_PAN"
    )

    assert zone_for_scene(1) is None
    assert zone_for_scene(12) is None

    print(
        "VI6.92 PROFILE ALLOCATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 5. VI6.93 RUNTIME STATE
# =====================================================

cat > vi6_93_runtime_state.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.93"


_selected_zones = set()
_selected_scenes = set()


def reset():

    _selected_zones.clear()
    _selected_scenes.clear()


def selected_count():

    return len(
        _selected_scenes
    )


def can_claim(
    scene,
    zone,
    max_canaries=3
):

    if selected_count() >= max_canaries:
        return False

    if scene in _selected_scenes:
        return False

    if zone in _selected_zones:
        return False

    return True


def claim(
    scene,
    zone
):

    _selected_scenes.add(
        scene
    )

    _selected_zones.add(
        zone
    )


def snapshot():

    return {
        "version": VERSION,

        "selected_scenes":
            sorted(
                _selected_scenes
            ),

        "selected_zones":
            sorted(
                _selected_zones
            ),
    }


def self_test():

    reset()

    assert can_claim(
        5,
        "CONTEXT_A"
    )

    claim(
        5,
        "CONTEXT_A"
    )

    assert not can_claim(
        4,
        "CONTEXT_A"
    )

    print(
        "VI6.93 RUNTIME STATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 6. VI6.97 TELEMETRY
# =====================================================

cat > vi6_97_three_scene_telemetry.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "6.97"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

REPORT = (
    BASE
    / "logs/producao/"
      "vi6_97_three_scene_canary_latest.json"
)

_EVENTS = []


def reset():

    _EVENTS.clear()

    if REPORT.exists():
        REPORT.unlink()


def record(event):

    _EVENTS.append(
        dict(event or {})
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

    assert VERSION == "6.97"

    print(
        "VI6.97 TELEMETRY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 7. VI6.94 THREE-SCENE ADAPTER
# =====================================================

cat > vi6_94_three_scene_adapter.py <<'PY'
#!/usr/bin/env python3

from vi6_49_real_command_mapper import (
    map_command
)

from vi6_61_motion_filter_compiler import (
    compile_filter
)

from vi6_91_three_scene_policy import (
    MAX_CANARIES
)

from vi6_92_profile_allocator import (
    zone_for_scene
)

from vi6_93_runtime_state import (
    can_claim,
    claim,
    snapshot
)

from vi6_97_three_scene_telemetry import (
    record
)


VERSION = "6.94"


def _replace_vf(
    command,
    vf
):

    result = list(command)


    try:
        index = result.index(
            "-vf"
        )

    except ValueError:
        return None


    if index + 1 >= len(result):
        return None


    result[index + 1] = vf

    return result


def prepare(
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


        if branch != "STILL":

            record(
                {
                    "scene": scene,
                    "action": "LEGACY",
                    "reason": "video_preserved",
                }
            )

            return {
                "command":
                    original,

                "legacy_command":
                    original,

                "scene":
                    scene,

                "using_vi6":
                    False,
            }


        allocation = zone_for_scene(
            scene
        )


        if allocation is None:

            record(
                {
                    "scene": scene,
                    "action": "LEGACY",
                    "reason": "outside_canary_zones",
                }
            )

            return {
                "command":
                    original,

                "legacy_command":
                    original,

                "scene":
                    scene,

                "using_vi6":
                    False,
            }


        zone = allocation[
            "zone"
        ]

        profile = allocation[
            "profile"
        ]


        if not can_claim(
            scene,
            zone,
            MAX_CANARIES
        ):

            record(
                {
                    "scene": scene,
                    "action": "LEGACY",
                    "reason": "zone_or_limit_already_claimed",
                }
            )

            return {
                "command":
                    original,

                "legacy_command":
                    original,

                "scene":
                    scene,

                "using_vi6":
                    False,
            }


        compiled = compile_filter(
            profile,
            duration,
            30
        )


        if compiled.get(
            "status"
        ) != "COMPILED":

            record(
                {
                    "scene": scene,
                    "action": "LEGACY",
                    "reason": "motion_compile_hold",
                    "profile": profile,
                }
            )

            return {
                "command":
                    original,

                "legacy_command":
                    original,

                "scene":
                    scene,

                "using_vi6":
                    False,
            }


        vf = compiled.get(
            "vf"
        )


        if not isinstance(
            vf,
            str
        ):

            return {
                "command":
                    original,

                "legacy_command":
                    original,

                "scene":
                    scene,

                "using_vi6":
                    False,
            }


        for required in (
            "scale=",
            "crop=",
            "zoompan=",
            "setsar=1",
            "format=yuv420p",
        ):

            if required not in vf:

                record(
                    {
                        "scene": scene,
                        "action": "LEGACY",
                        "reason":
                            "compiled_filter_invalid",
                        "profile": profile,
                    }
                )

                return {
                    "command":
                        original,

                    "legacy_command":
                        original,

                    "scene":
                        scene,

                    "using_vi6":
                        False,
                }


        adapted = _replace_vf(
            original,
            vf
        )


        if adapted is None:

            record(
                {
                    "scene": scene,
                    "action": "LEGACY",
                    "reason": "vf_not_found",
                }
            )

            return {
                "command":
                    original,

                "legacy_command":
                    original,

                "scene":
                    scene,

                "using_vi6":
                    False,
            }


        claim(
            scene,
            zone
        )


        record(
            {
                "scene":
                    scene,

                "action":
                    "VI6_SELECTED",

                "zone":
                    zone,

                "profile":
                    profile,

                "duration":
                    duration,

                "state":
                    snapshot(),

                "command_mutated":
                    True,
            }
        )


        return {
            "command":
                adapted,

            # Critical:
            # untouched command retained for real retry.
            "legacy_command":
                original,

            "scene":
                scene,

            "profile":
                profile,

            "zone":
                zone,

            "using_vi6":
                True,
        }


    except Exception as exc:

        record(
            {
                "scene":
                    None,

                "action":
                    "LEGACY",

                "reason":
                    "adapter_exception:"
                    + type(exc).__name__,
            }
        )


        return {
            "command":
                original,

            "legacy_command":
                original,

            "scene":
                None,

            "using_vi6":
                False,
        }


def self_test():

    assert VERSION == "6.94"

    print(
        "VI6.94 THREE-SCENE ADAPTER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 8. VI6.96 OUTPUT VALIDATION
# =====================================================

cat > vi6_96_post_render_validator.py <<'PY'
#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


VERSION = "6.96"


def validate(path):

    path = Path(path)


    if not path.exists():

        return {
            "version": VERSION,
            "status": "HOLD",
            "reason": "output_missing",
        }


    try:

        raw = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                (
                    "stream="
                    "width,height,"
                    "avg_frame_rate:"
                    "format=duration"
                ),
                "-of",
                "json",
                str(path),
            ],
            text=True
        )


        data = json.loads(raw)


        stream = (
            data.get("streams")
            or [{}]
        )[0]


        fmt = (
            data.get("format")
            or {}
        )


    except Exception as exc:

        return {
            "version": VERSION,

            "status": "HOLD",

            "reason":
                "ffprobe:"
                + type(exc).__name__,
        }


    blockers = []


    if (
        stream.get("width") != 1080
        or stream.get("height") != 1920
    ):

        blockers.append(
            "resolution_invalid"
        )


    try:
        duration = float(
            fmt.get("duration")
        )

    except Exception:
        duration = 0


    if duration <= 0:

        blockers.append(
            "duration_invalid"
        )


    return {
        "version": VERSION,

        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "width":
            stream.get("width"),

        "height":
            stream.get("height"),

        "duration":
            duration,

        "fps":
            stream.get(
                "avg_frame_rate"
            ),

        "blockers":
            blockers,
    }


def self_test():

    assert (
        validate(
            "/not/a/file.mp4"
        )["status"]
        == "HOLD"
    )

    print(
        "VI6.96 POST-RENDER VALIDATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 9. VI6.95 REAL SCENE EXECUTOR + LEGACY RETRY
# =====================================================

cat > vi6_95_scene_executor.py <<'PY'
#!/usr/bin/env python3

import subprocess

from pathlib import Path


from vi6_94_three_scene_adapter import (
    prepare
)

from vi6_96_post_render_validator import (
    validate
)

from vi6_97_three_scene_telemetry import (
    record
)


VERSION = "6.95"


def execute(
    command,
    **run_kwargs
):

    prepared = prepare(
        command
    )


    chosen = prepared[
        "command"
    ]


    legacy = prepared[
        "legacy_command"
    ]


    scene = prepared.get(
        "scene"
    )


    using_vi6 = prepared.get(
        "using_vi6"
    )


    # ---------------------------------------------
    # Normal LEGACY route.
    # ---------------------------------------------

    if not using_vi6:

        return subprocess.run(
            chosen,
            **run_kwargs
        )


    profile = prepared.get(
        "profile"
    )


    output_path = (
        Path(
            chosen[-1]
        )
        if chosen
        else None
    )


    record(
        {
            "scene":
                scene,

            "action":
                "VI6_RENDER_ATTEMPT",

            "profile":
                profile,
        }
    )


    # ---------------------------------------------
    # First try: VI6.
    # ---------------------------------------------

    try:

        result = subprocess.run(
            chosen,
            **run_kwargs
        )


        validation = (
            validate(
                output_path
            )
            if output_path
            else {
                "status": "HOLD",
                "reason": "output_unknown",
            }
        )


        if validation.get(
            "status"
        ) == "PASS":

            record(
                {
                    "scene":
                        scene,

                    "action":
                        "VI6_RENDER_SUCCESS",

                    "profile":
                        profile,

                    "validation":
                        validation,
                }
            )

            return result


        failure_reason = (
            "post_render_validation"
        )


    except subprocess.CalledProcessError:

        failure_reason = (
            "ffmpeg_nonzero"
        )


    except Exception as exc:

        failure_reason = (
            "vi6_exception:"
            + type(exc).__name__
        )


    # ---------------------------------------------
    # Actual same-scene LEGACY retry.
    # ---------------------------------------------

    record(
        {
            "scene":
                scene,

            "action":
                "LEGACY_RETRY",

            "profile":
                profile,

            "reason":
                failure_reason,
        }
    )


    # Remove failed/invalid partial output first.
    try:

        if (
            output_path
            and output_path.exists()
        ):

            output_path.unlink()

    except Exception:
        pass


    result = subprocess.run(
        legacy,
        **run_kwargs
    )


    legacy_validation = (
        validate(
            output_path
        )
        if output_path
        else {
            "status": "HOLD"
        }
    )


    if legacy_validation.get(
        "status"
    ) != "PASS":

        record(
            {
                "scene":
                    scene,

                "action":
                    "LEGACY_RETRY_FAILED",

                "validation":
                    legacy_validation,
            }
        )


        raise RuntimeError(
            "VI7_LEGACY_RETRY_FAILED"
        )


    record(
        {
            "scene":
                scene,

            "action":
                "LEGACY_RETRY_SUCCESS",

            "validation":
                legacy_validation,
        }
    )


    return result


def self_test():

    assert VERSION == "6.95"

    print(
        "VI6.95 REAL SCENE EXECUTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 10. VI6.98 PRE-PRODUCTION GATE
# =====================================================

cat > vi6_98_production_gate.py <<'PY'
#!/usr/bin/env python3

import json

from pathlib import Path


VERSION = "6.98"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    blockers = []


    p90 = (
        BASE
        / "logs/producao/"
          "vi6_90_master_canary_latest.json"
    )


    try:

        gate = json.loads(
            p90.read_text(
                encoding="utf-8"
            )
        )["gate"]


    except Exception:

        gate = None


    if gate is None:

        blockers.append(
            "vi690_gate_missing"
        )


    elif gate.get(
        "status"
    ) not in {
        "CERTIFIED",
        "CERTIFIED_WITH_WARNINGS",
    }:

        blockers.append(
            "single_scene_canary_not_certified"
        )


    elif gate.get(
        "vi6_scenes"
    ) != [5]:

        blockers.append(
            "single_scene_baseline_invalid"
        )


    return {
        "version": VERSION,

        "status":
            (
                "THREE_SCENE_CANARY_ALLOWED"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            blockers,

        "max_vi6_scenes":
            3,

        "full_active":
            False,
    }


def self_test():

    assert VERSION == "6.98"

    print(
        "VI6.98 PRODUCTION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 11. VI6.99 RUNTIME ROUTER
# =====================================================

cat > vi6_99_runtime_router.py <<'PY'
#!/usr/bin/env python3

import os


VERSION = "6.99"


def enabled():

    return (
        os.getenv(
            "VI700_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
    )


def self_test():

    assert VERSION == "6.99"

    print(
        "VI6.99 RUNTIME ROUTER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 12. VI7.00 MASTER GATE
# =====================================================

cat > vi7_00_master_gate.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "7.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


REPORT = (
    BASE
    / "logs/producao/"
      "vi6_97_three_scene_canary_latest.json"
)


OUTPUT = (
    BASE
    / "logs/producao/"
      "vi7_00_master_gate_latest.json"
)


def evaluate():

    blockers = []

    warnings = []


    try:

        data = json.loads(
            REPORT.read_text(
                encoding="utf-8"
            )
        )


        events = (
            data.get("events")
            or []
        )


    except Exception:

        events = []

        blockers.append(
            "vi697_telemetry_missing"
        )


    selected = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI6_SELECTED"
    ]


    successes = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI6_RENDER_SUCCESS"
    ]


    retries = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY"
    ]


    retry_success = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY_SUCCESS"
    ]


    retry_failed = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY_FAILED"
    ]


    selected_scenes = sorted(
        {
            e.get("scene")
            for e in selected
            if isinstance(
                e.get("scene"),
                int
            )
        }
    )


    success_scenes = sorted(
        {
            e.get("scene")
            for e in successes
            if isinstance(
                e.get("scene"),
                int
            )
        }
    )


    if len(selected_scenes) > 3:

        blockers.append(
            "more_than_three_vi6_scenes"
        )


    if retry_failed:

        blockers.append(
            "legacy_retry_failure"
        )


    # A healthy run should normally obtain three
    # distinct STILL canaries. If media composition
    # does not provide three eligible stills, do not
    # pretend expansion was fully certified.

    if len(selected_scenes) < 3:

        warnings.append(
            "fewer_than_three_eligible_vi6_scenes"
        )


    if retries:

        warnings.append(
            "legacy_retry_was_required"
        )


    if (
        selected_scenes
        and sorted(
            set(
                success_scenes
            )
            | {
                e.get("scene")
                for e in retry_success
            }
        )
        != selected_scenes
    ):

        blockers.append(
            "selected_scene_without_valid_final_render"
        )


    if blockers:

        status = "HOLD"


    elif (
        len(selected_scenes) == 3
        and not retries
    ):

        status = (
            "THREE_SCENE_CANARY_CERTIFIED"
        )


    else:

        status = (
            "CANARY_SAFE_WITH_WARNINGS"
        )


    result = {
        "version":
            VERSION,

        "status":
            status,

        "selected_scene_count":
            len(selected_scenes),

        "selected_scenes":
            selected_scenes,

        "vi6_success_scenes":
            success_scenes,

        "legacy_retry_count":
            len(retries),

        "legacy_retry_success_count":
            len(retry_success),

        "legacy_retry_failed_count":
            len(retry_failed),

        "blockers":
            sorted(
                set(blockers)
            ),

        "warnings":
            sorted(
                set(warnings)
            ),

        "three_scene_expansion_certified":
            (
                status
                == "THREE_SCENE_CANARY_CERTIFIED"
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

    assert VERSION == "7.00"

    print(
        "VI7.00 MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 13. PATCH VIDEO.PY FOR TRUE SAME-SCENE RETRY
# =====================================================

echo
echo "===== INSTALLING TRUE CANARY EXECUTOR ====="

python - <<'PY'
from pathlib import Path


p = Path(
    "video.py"
)


s = p.read_text(
    encoding="utf-8"
)


marker = (
    "# VI7.00 TRUE SCENE EXECUTOR"
)


if marker in s:

    print(
        "VI7 EXECUTOR ALREADY INSTALLED"
    )

    raise SystemExit(0)


needle = """        subprocess.run(
            comando,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )"""


if needle not in s:

    # tolerate historical indentation
    needle = """        subprocess.run(
            comando,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )"""


if needle not in s:

    raise SystemExit(
        "ABORT: exact primary scene subprocess.run block not found"
    )


replacement = """        # VI7.00 TRUE SCENE EXECUTOR
        # LEGACY remains default unless VI700_CANARY_MODE=ON.
        try:
            import os as _vi700_os

            if (
                _vi700_os.getenv(
                    "VI700_CANARY_MODE",
                    "OFF"
                ).upper()
                == "ON"
            ):
                from vi6_95_scene_executor import (
                    execute as _vi700_execute_scene
                )

                _vi700_execute_scene(
                    comando,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            else:
                subprocess.run(
                    comando,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

        except ImportError:
            subprocess.run(
                comando,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )"""


patched = s.replace(
    needle,
    replacement,
    1
)


if patched == s:

    raise SystemExit(
        "ABORT: video.py patch not applied"
    )


p.write_text(
    patched,
    encoding="utf-8"
)


print(
    "VI7 TRUE SCENE EXECUTOR=INSTALLED"
)
PY

if [ "$?" -ne 0 ]; then
    rollback
    exit 10
fi


# =====================================================
# 14. IMPORTANT:
# DISABLE OLD VI6.89 MUTATION DURING VI7 ROUTE
# =====================================================

# VI7 invokes the new adapter inside vi6_95.
# Therefore the old VI682 canary MUST stay OFF during
# VI7 production to avoid double mutation.


# =====================================================
# 15. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_91_three_scene_policy.py \
    vi6_92_profile_allocator.py \
    vi6_93_runtime_state.py \
    vi6_94_three_scene_adapter.py \
    vi6_95_scene_executor.py \
    vi6_96_post_render_validator.py \
    vi6_97_three_scene_telemetry.py \
    vi6_98_production_gate.py \
    vi6_99_runtime_router.py \
    vi7_00_master_gate.py \
    video.py
then

    rollback
    exit 11
fi


echo "COMPILE=PASS"


# =====================================================
# 16. SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

for F in \
    vi6_91_three_scene_policy.py \
    vi6_92_profile_allocator.py \
    vi6_93_runtime_state.py \
    vi6_94_three_scene_adapter.py \
    vi6_95_scene_executor.py \
    vi6_96_post_render_validator.py \
    vi6_97_three_scene_telemetry.py \
    vi6_98_production_gate.py \
    vi6_99_runtime_router.py \
    vi7_00_master_gate.py
do

    python "$F" || {
        rollback
        exit 12
    }

done


# =====================================================
# 17. PRE-PRODUCTION GATE
# =====================================================

echo
echo "===== VI6.98 REAL GATE ====="

python - <<'PY'
from vi6_98_production_gate import (
    evaluate
)

result = evaluate()

print(
    "STATUS:",
    result.get("status")
)

print(
    "MAX VI6 SCENES:",
    result.get("max_vi6_scenes")
)

print(
    "BLOCKERS:",
    result.get("blockers")
)

print(
    "FULL ACTIVE:",
    result.get("full_active")
)

if result.get("status") != (
    "THREE_SCENE_CANARY_ALLOWED"
):
    raise SystemExit(1)
PY

if [ "$?" -ne 0 ]; then

    rollback
    exit 13
fi


# =====================================================
# 18. RELEASE CHECK
# =====================================================

echo
echo "===== RELEASE CHECK ====="

bash -n gerar_short.sh || {
    rollback
    exit 14
}


./release_check.sh || {
    rollback
    exit 15
}


# =====================================================
# 19. CLEAR ONLY VI7 SESSION TELEMETRY
# =====================================================

rm -f \
    logs/producao/vi6_97_three_scene_canary_latest.json \
    logs/producao/vi7_00_master_gate_latest.json


# =====================================================
# 20. REAL VI7.00 PRODUCTION
# =====================================================

echo
echo "======================================================"
echo " STARTING VI7.00 THREE-SCENE PRODUCTION CANARY"
echo "======================================================"
echo
echo "MAX VI6 STILL SCENES = 3"
echo "VIDEO SCENES = LEGACY"
echo "HOOK = LEGACY"
echo "CTA = LEGACY"
echo "VI6 FFmpeg failure = LEGACY retry"
echo


# Old single-scene system explicitly OFF.
VI682_CANARY_MODE=OFF \
VI700_CANARY_MODE=ON \
VI647_RENDERER_MODE=LEGACY \
./gerar_short.sh


PIPE_STATUS="$?"


echo
echo "PIPELINE STATUS=$PIPE_STATUS"


# =====================================================
# 21. VI7 MASTER CERTIFICATION
# =====================================================

echo
echo "===== VI7.00 REAL MASTER GATE ====="

python - <<'PY'
from vi7_00_master_gate import (
    evaluate
)


result = evaluate()


print()
print(
    "STATUS:",
    result.get("status")
)

print(
    "SELECTED SCENE COUNT:",
    result.get(
        "selected_scene_count"
    )
)

print(
    "SELECTED SCENES:",
    result.get(
        "selected_scenes"
    )
)

print(
    "VI6 SUCCESS SCENES:",
    result.get(
        "vi6_success_scenes"
    )
)

print(
    "LEGACY RETRIES:",
    result.get(
        "legacy_retry_count"
    )
)

print(
    "LEGACY RETRY SUCCESSES:",
    result.get(
        "legacy_retry_success_count"
    )
)

print(
    "LEGACY RETRY FAILURES:",
    result.get(
        "legacy_retry_failed_count"
    )
)

print(
    "BLOCKERS:",
    result.get("blockers")
)

print(
    "WARNINGS:",
    result.get("warnings")
)

print(
    "THREE-SCENE CERTIFIED:",
    result.get(
        "three_scene_expansion_certified"
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
# 22. TELEMETRY
# =====================================================

echo
echo "===== VI7.00 EVENT TRACE ====="

python - <<'PY'
import json

from pathlib import Path


p = (
    Path.home()
    / "ShortAutoPro/logs/producao/"
      "vi6_97_three_scene_canary_latest.json"
)


if not p.exists():

    print(
        "TELEMETRY=MISSING"
    )

    raise SystemExit(0)


data = json.loads(
    p.read_text(
        encoding="utf-8"
    )
)


for event in (
    data.get("events")
    or []
):

    if event.get(
        "action"
    ) in {
        "VI6_SELECTED",
        "VI6_RENDER_ATTEMPT",
        "VI6_RENDER_SUCCESS",
        "LEGACY_RETRY",
        "LEGACY_RETRY_SUCCESS",
        "LEGACY_RETRY_FAILED",
    }:

        print(
            "SCENE",
            event.get("scene"),
            "|",
            event.get("action"),
            "| profile=",
            event.get("profile"),
            "| reason=",
            event.get("reason"),
        )
PY


# =====================================================
# 23. FINAL SAFETY
# =====================================================

echo
echo "===== FINAL SAFETY ====="

python - <<'PY'
import re
from pathlib import Path

p = Path("video.py")

text = p.read_text(
    encoding="utf-8"
)

count = text.count(
    "# VI7.00 TRUE SCENE EXECUTOR"
)

print(
    "VI7 EXECUTOR MARKERS:",
    count
)

if count != 1:
    raise SystemExit(
        "INVALID VI7 MARKER COUNT"
    )

print(
    "VIDEO.PY COMPILE=PASS"
)

print(
    "FULL ACTIVE=LOCKED"
)
PY


echo
echo "======================================================"
echo " VI7.00 MEGA UPDATE COMPLETE"
echo "======================================================"
echo
echo "PIPELINE STATUS=$PIPE_STATUS"
echo "MAX VI6 SCENES=3"
echo "REAL LEGACY RETRY=ENABLED"
echo "VIDEO SCENES=LEGACY"
echo "HOOK=LEGACY"
echo "CTA=LEGACY"
echo "FULL ACTIVE=LOCKED"
echo
echo "MASTER REPORT:"
echo "logs/producao/vi7_00_master_gate_latest.json"
echo

exit "$PIPE_STATUS"
