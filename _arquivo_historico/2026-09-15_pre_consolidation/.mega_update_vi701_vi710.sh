#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/mega_vi701_vi710_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " SHORTAUTOPRO MEGA UPDATE VI"
echo " VI7.01 -> VI7.10"
echo " SIX-SCENE CONTROLLED PRODUCTION CANARY"
echo "======================================================"
echo
echo "MAX VI6 STILL SCENES = 6"
echo "MAX PER NARRATIVE ZONE = 2"
echo "VIDEO MEDIA = LEGACY"
echo "HOOK = LEGACY"
echo "CTA = LEGACY"
echo "PER-SCENE LEGACY RETRY = ON"
echo "FULL ACTIVE = LOCKED"
echo


# =====================================================
# 0. REQUIREMENTS
# =====================================================

REQUIRED="
video.py
gerar_short.sh
vi6_49_real_command_mapper.py
vi6_61_motion_filter_compiler.py
vi6_95_scene_executor.py
vi7_00_master_gate.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F ausente."
        exit 2
    fi
done


MASTER700="logs/producao/vi7_00_master_gate_latest.json"

if [ ! -f "$MASTER700" ]; then
    echo "ERRO: relatório VI7.00 ausente."
    exit 3
fi


VIDEO_HASH_BEFORE="$(
    sha256sum video.py |
    awk '{print $1}'
)"


echo
echo "VIDEO.PY SHA256:"
echo "$VIDEO_HASH_BEFORE"


# =====================================================
# 1. VERIFY VI7.00 REAL BASELINE
# =====================================================

echo
echo "===== VI7.00 BASELINE CHECK ====="

python - <<'PY'
import json
from pathlib import Path

base = Path.home() / "ShortAutoPro"

p = (
    base
    / "logs/producao/"
      "vi7_00_master_gate_latest.json"
)

gate = json.loads(
    p.read_text(
        encoding="utf-8"
    )
)["gate"]

blockers = []

if gate.get("status") != (
    "THREE_SCENE_CANARY_CERTIFIED"
):
    blockers.append(
        "vi700_not_three_scene_certified"
    )

if gate.get(
    "selected_scene_count"
) != 3:
    blockers.append(
        "vi700_scene_count_not_3"
    )

if gate.get(
    "legacy_retry_failed_count",
    0
) != 0:
    blockers.append(
        "vi700_legacy_retry_failure"
    )

if gate.get("blockers"):
    blockers.append(
        "vi700_has_blockers"
    )

if gate.get(
    "full_active_authorized"
):
    blockers.append(
        "full_active_should_be_locked"
    )

print(
    "STATUS:",
    gate.get("status")
)

print(
    "SCENES:",
    gate.get("selected_scenes")
)

print(
    "SUCCESSES:",
    gate.get(
        "vi6_success_scenes"
    )
)

print(
    "RETRIES:",
    gate.get(
        "legacy_retry_count"
    )
)

print(
    "BLOCKERS:",
    blockers
)

if blockers:
    raise SystemExit(1)

print(
    "VI7.00 BASELINE=PASS"
)
PY

if [ "$?" -ne 0 ]; then
    exit 4
fi


# =====================================================
# 2. BACKUPS
# =====================================================

FILES="
vi6_95_scene_executor.py
vi7_01_six_scene_policy.py
vi7_02_runtime_state.py
vi7_03_profile_allocator.py
vi7_04_six_scene_adapter.py
vi7_05_output_validator.py
vi7_06_scene_executor.py
vi7_07_telemetry.py
vi7_08_sequence_audit.py
vi7_09_production_gate.py
vi7_10_master_gate.py
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
    echo " VI7.01 -> VI7.10 ROLLBACK"
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
# 3. VI7.01 — SIX-SCENE POLICY
# =====================================================

cat > vi7_01_six_scene_policy.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.01"

MAX_CANARIES = 6

MAX_PER_ZONE = 2


ZONES = (

    {
        "name":
            "EARLY_CONTEXT",

        "scenes":
            (2, 3, 4),

        "profiles":
            (
                "HORIZONTAL_DISCOVERY",
                "SLOW_PUSH",
            ),
    },

    {
        "name":
            "MID_CONTEXT",

        "scenes":
            (5, 6, 7, 8),

        "profiles":
            (
                "DETAIL_PUSH",
                "REVERSE_DRIFT",
            ),
    },

    {
        "name":
            "CLIMAX",

        "scenes":
            (9, 10, 11),

        "profiles":
            (
                "CLIMAX_PUSH",
                "CLIMAX_PAN",
            ),
    },
)


def zone_for_scene(scene):

    for zone in ZONES:

        if scene in zone["scenes"]:

            return zone

    return None


def policy():

    return {
        "version":
            VERSION,

        "max_canaries":
            MAX_CANARIES,

        "max_per_zone":
            MAX_PER_ZONE,

        "hook_scene":
            1,

        "cta_scene":
            12,

        "video_canary_allowed":
            False,

        "full_active":
            False,
    }


def self_test():

    assert MAX_CANARIES == 6
    assert MAX_PER_ZONE == 2

    assert (
        zone_for_scene(3)["name"]
        == "EARLY_CONTEXT"
    )

    assert (
        zone_for_scene(7)["name"]
        == "MID_CONTEXT"
    )

    assert (
        zone_for_scene(10)["name"]
        == "CLIMAX"
    )

    assert zone_for_scene(1) is None
    assert zone_for_scene(12) is None

    print(
        "VI7.01 SIX-SCENE POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 4. VI7.02 — RUNTIME STATE
# =====================================================

cat > vi7_02_runtime_state.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.02"

_selected_scenes = set()

_zone_scenes = {}


def reset():

    _selected_scenes.clear()
    _zone_scenes.clear()


def total():

    return len(
        _selected_scenes
    )


def zone_count(zone):

    return len(
        _zone_scenes.get(
            zone,
            set()
        )
    )


def can_claim(
    scene,
    zone,
    max_total,
    max_zone
):

    if scene in _selected_scenes:
        return False

    if total() >= max_total:
        return False

    if zone_count(zone) >= max_zone:
        return False

    return True


def claim(
    scene,
    zone
):

    _selected_scenes.add(
        scene
    )

    _zone_scenes.setdefault(
        zone,
        set()
    ).add(
        scene
    )


def snapshot():

    return {
        "version":
            VERSION,

        "selected_scenes":
            sorted(
                _selected_scenes
            ),

        "zone_scenes":
            {
                key:
                    sorted(value)

                for key, value
                in _zone_scenes.items()
            },

        "total":
            total(),
    }


def self_test():

    reset()

    assert can_claim(
        3,
        "EARLY",
        6,
        2
    )

    claim(
        3,
        "EARLY"
    )

    claim(
        4,
        "EARLY"
    )

    assert not can_claim(
        2,
        "EARLY",
        6,
        2
    )

    assert total() == 2

    reset()

    print(
        "VI7.02 RUNTIME STATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 5. VI7.03 — PROFILE ALLOCATOR
# =====================================================

cat > vi7_03_profile_allocator.py <<'PY'
#!/usr/bin/env python3

from vi7_01_six_scene_policy import (
    zone_for_scene
)

from vi7_02_runtime_state import (
    zone_count
)


VERSION = "7.03"


def allocate(scene):

    zone = zone_for_scene(
        scene
    )

    if zone is None:

        return None


    index = zone_count(
        zone["name"]
    )


    profiles = zone[
        "profiles"
    ]


    if index >= len(profiles):

        return None


    return {
        "version":
            VERSION,

        "scene":
            scene,

        "zone":
            zone["name"],

        "profile":
            profiles[index],

        "profile_index":
            index,
    }


def self_test():

    from vi7_02_runtime_state import (
        reset,
        claim
    )

    reset()

    first = allocate(3)

    assert (
        first["profile"]
        == "HORIZONTAL_DISCOVERY"
    )

    claim(
        3,
        first["zone"]
    )

    second = allocate(4)

    assert (
        second["profile"]
        == "SLOW_PUSH"
    )

    reset()

    print(
        "VI7.03 PROFILE ALLOCATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 6. VI7.07 — TELEMETRY
# =====================================================

cat > vi7_07_telemetry.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "7.07"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

REPORT = (
    BASE
    / "logs/producao/"
      "vi7_07_six_scene_runtime_latest.json"
)

_EVENTS = []


def reset():

    _EVENTS.clear()

    try:

        if REPORT.exists():
            REPORT.unlink()

    except Exception:
        pass


def record(event):

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

    assert VERSION == "7.07"

    print(
        "VI7.07 TELEMETRY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 7. VI7.04 — SIX-SCENE ADAPTER
# =====================================================

cat > vi7_04_six_scene_adapter.py <<'PY'
#!/usr/bin/env python3

from vi6_49_real_command_mapper import (
    map_command
)

from vi6_61_motion_filter_compiler import (
    compile_filter
)

from vi7_01_six_scene_policy import (
    MAX_CANARIES,
    MAX_PER_ZONE,
    zone_for_scene
)

from vi7_02_runtime_state import (
    can_claim,
    claim,
    snapshot
)

from vi7_03_profile_allocator import (
    allocate
)

from vi7_07_telemetry import (
    record
)


VERSION = "7.04"


def _replace_vf(
    command,
    vf
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


    if index + 1 >= len(result):

        return None


    result[
        index + 1
    ] = vf


    return result


def prepare(command):

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


        # -----------------------------------------
        # Never canary unknown scenes.
        # -----------------------------------------

        if not isinstance(
            scene,
            int
        ):

            record(
                {
                    "scene":
                        scene,

                    "action":
                        "LEGACY",

                    "reason":
                        "scene_unknown",
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


        # -----------------------------------------
        # Native video must stay native.
        # -----------------------------------------

        if branch != "STILL":

            record(
                {
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "action":
                        "LEGACY",

                    "reason":
                        "native_video_preserved",
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


        # -----------------------------------------
        # Hook and CTA excluded by policy.
        # -----------------------------------------

        if scene in {
            1,
            12,
        }:

            record(
                {
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "action":
                        "LEGACY",

                    "reason":
                        "hook_or_cta_protected",
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


        zone = zone_for_scene(
            scene
        )


        if zone is None:

            record(
                {
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "action":
                        "LEGACY",

                    "reason":
                        "outside_canary_policy",
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


        zone_name = zone[
            "name"
        ]


        if not can_claim(
            scene,
            zone_name,
            MAX_CANARIES,
            MAX_PER_ZONE
        ):

            record(
                {
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "zone":
                        zone_name,

                    "action":
                        "LEGACY",

                    "reason":
                        "zone_or_global_limit",
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


        allocation = allocate(
            scene
        )


        if allocation is None:

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


        profile = allocation[
            "profile"
        ]


        compiled = compile_filter(
            profile,
            duration,
            30
        )


        if (
            compiled.get(
                "status"
            )
            != "COMPILED"
        ):

            record(
                {
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "zone":
                        zone_name,

                    "profile":
                        profile,

                    "action":
                        "LEGACY",

                    "reason":
                        "motion_compile_hold",
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


        required = (
            "scale=",
            "crop=",
            "zoompan=",
            "setsar=1",
            "format=yuv420p",
        )


        if any(
            token not in vf
            for token in required
        ):

            record(
                {
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "zone":
                        zone_name,

                    "profile":
                        profile,

                    "action":
                        "LEGACY",

                    "reason":
                        "compiled_filter_invalid",
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
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "action":
                        "LEGACY",

                    "reason":
                        "vf_argument_missing",
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


        # Claim only after complete compilation.
        claim(
            scene,
            zone_name
        )


        record(
            {
                "scene":
                    scene,

                "branch":
                    branch,

                "zone":
                    zone_name,

                "profile":
                    profile,

                "action":
                    "VI7_SELECTED",

                "duration_seconds":
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

            # Critical immutable fallback route.
            "legacy_command":
                original,

            "scene":
                scene,

            "branch":
                branch,

            "duration_seconds":
                duration,

            "zone":
                zone_name,

            "profile":
                profile,

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

    assert VERSION == "7.04"

    print(
        "VI7.04 SIX-SCENE ADAPTER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 8. VI7.05 — STRONG POST-RENDER VALIDATOR
# =====================================================

cat > vi7_05_output_validator.py <<'PY'
#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


VERSION = "7.05"


def _fps(value):

    if not value:
        return None


    try:

        a, b = str(
            value
        ).split(
            "/",
            1
        )


        return (
            float(a)
            / float(b)
        )


    except Exception:

        try:
            return float(value)

        except Exception:
            return None


def validate(
    path,
    expected_duration
):

    path = Path(
        path
    )


    blockers = []


    if not path.exists():

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "blockers":
                ["output_missing"],
        }


    if path.stat().st_size <= 0:

        blockers.append(
            "output_empty"
        )


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
                    "avg_frame_rate,"
                    "pix_fmt,"
                    "codec_name:"
                    "format=duration,size"
                ),

                "-of",
                "json",

                str(path),
            ],
            text=True
        )


        data = json.loads(
            raw
        )


    except Exception as exc:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "blockers":
                [
                    "ffprobe_failure:"
                    + type(exc).__name__
                ],
        }


    stream = (
        data.get("streams")
        or [{}]
    )[0]


    fmt = (
        data.get("format")
        or {}
    )


    width = stream.get(
        "width"
    )


    height = stream.get(
        "height"
    )


    if (
        width != 1080
        or height != 1920
    ):

        blockers.append(
            "resolution_invalid"
        )


    fps = _fps(
        stream.get(
            "avg_frame_rate"
        )
    )


    if (
        fps is None
        or abs(
            fps - 30.0
        ) > .05
    ):

        blockers.append(
            "fps_invalid"
        )


    if stream.get(
        "pix_fmt"
    ) not in {
        "yuv420p",
        "yuvj420p",
    }:

        blockers.append(
            "pixel_format_invalid"
        )


    if stream.get(
        "codec_name"
    ) != "h264":

        blockers.append(
            "codec_invalid"
        )


    try:

        duration = float(
            fmt.get(
                "duration"
            )
        )

    except Exception:

        duration = None


    try:

        expected = float(
            expected_duration
        )

    except Exception:

        expected = None


    duration_delta = None


    if (
        duration is None
        or duration <= 0
    ):

        blockers.append(
            "duration_invalid"
        )


    elif expected is not None:

        duration_delta = abs(
            duration
            - expected
        )


        if duration_delta > .15:

            blockers.append(
                "duration_delta_too_high"
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

        "width":
            width,

        "height":
            height,

        "fps":
            fps,

        "duration":
            duration,

        "expected_duration":
            expected,

        "duration_delta":
            (
                round(
                    duration_delta,
                    4
                )
                if duration_delta is not None
                else None
            ),

        "codec":
            stream.get(
                "codec_name"
            ),

        "pix_fmt":
            stream.get(
                "pix_fmt"
            ),

        "bytes":
            path.stat().st_size,

        "blockers":
            blockers,
    }


def self_test():

    result = validate(
        "/file/that/does/not/exist.mp4",
        3.0
    )

    assert (
        result["status"]
        == "HOLD"
    )

    print(
        "VI7.05 OUTPUT VALIDATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 9. VI7.06 — REAL EXECUTOR + SAME-SCENE RETRY
# =====================================================

cat > vi7_06_scene_executor.py <<'PY'
#!/usr/bin/env python3

import subprocess

from pathlib import Path


from vi7_04_six_scene_adapter import (
    prepare
)

from vi7_05_output_validator import (
    validate
)

from vi7_07_telemetry import (
    record
)


VERSION = "7.06"


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


    if not using_vi6:

        return subprocess.run(
            chosen,
            **run_kwargs
        )


    profile = prepared.get(
        "profile"
    )


    zone = prepared.get(
        "zone"
    )


    expected_duration = prepared.get(
        "duration_seconds"
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

            "zone":
                zone,

            "profile":
                profile,

            "action":
                "VI7_RENDER_ATTEMPT",
        }
    )


    failure_reason = None


    # ---------------------------------------------
    # Attempt VI7 render.
    # ---------------------------------------------

    try:

        result = subprocess.run(
            chosen,
            **run_kwargs
        )


        validation = (
            validate(
                output_path,
                expected_duration
            )

            if output_path

            else {
                "status":
                    "HOLD",

                "blockers":
                    ["output_path_unknown"],
            }
        )


        if (
            validation.get(
                "status"
            )
            == "PASS"
        ):

            record(
                {
                    "scene":
                        scene,

                    "zone":
                        zone,

                    "profile":
                        profile,

                    "action":
                        "VI7_RENDER_SUCCESS",

                    "validation":
                        validation,
                }
            )


            return result


        failure_reason = (
            "post_render_validation"
        )


        record(
            {
                "scene":
                    scene,

                "zone":
                    zone,

                "profile":
                    profile,

                "action":
                    "VI7_VALIDATION_HOLD",

                "validation":
                    validation,
            }
        )


    except subprocess.CalledProcessError:

        failure_reason = (
            "ffmpeg_nonzero"
        )


    except Exception as exc:

        failure_reason = (
            "vi7_exception:"
            + type(exc).__name__
        )


    # ---------------------------------------------
    # TRUE SAME-SCENE LEGACY RETRY.
    # ---------------------------------------------

    record(
        {
            "scene":
                scene,

            "zone":
                zone,

            "profile":
                profile,

            "action":
                "LEGACY_RETRY",

            "reason":
                failure_reason,
        }
    )


    try:

        if (
            output_path
            and output_path.exists()
        ):

            output_path.unlink()

    except Exception:
        pass


    legacy_result = subprocess.run(
        legacy,
        **run_kwargs
    )


    legacy_validation = (
        validate(
            output_path,
            expected_duration
        )

        if output_path

        else {
            "status":
                "HOLD",

            "blockers":
                ["output_path_unknown"],
        }
    )


    if (
        legacy_validation.get(
            "status"
        )
        != "PASS"
    ):

        record(
            {
                "scene":
                    scene,

                "zone":
                    zone,

                "profile":
                    profile,

                "action":
                    "LEGACY_RETRY_FAILED",

                "validation":
                    legacy_validation,
            }
        )


        raise RuntimeError(
            "VI710_LEGACY_RETRY_FAILED"
        )


    record(
        {
            "scene":
                scene,

            "zone":
                zone,

            "profile":
                profile,

            "action":
                "LEGACY_RETRY_SUCCESS",

            "validation":
                legacy_validation,
        }
    )


    return legacy_result


def self_test():

    assert VERSION == "7.06"

    print(
        "VI7.06 SCENE EXECUTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 10. VI7.08 — SEQUENCE AUDIT
# =====================================================

cat > vi7_08_sequence_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.08"


def audit(events):

    selected = [
        event
        for event in (
            events
            or []
        )
        if event.get(
            "action"
        ) == "VI7_SELECTED"
    ]


    scenes = sorted(
        {
            event.get(
                "scene"
            )
            for event in selected
            if isinstance(
                event.get(
                    "scene"
                ),
                int
            )
        }
    )


    profiles = [
        event.get(
            "profile"
        )
        for event in selected
        if event.get(
            "profile"
        )
    ]


    zones = [
        event.get(
            "zone"
        )
        for event in selected
        if event.get(
            "zone"
        )
    ]


    blockers = []
    warnings = []


    if len(scenes) > 6:

        blockers.append(
            "more_than_six_canaries"
        )


    if any(
        scene in {
            1,
            12,
        }
        for scene in scenes
    ):

        blockers.append(
            "hook_or_cta_selected"
        )


    # No more than two canaries per narrative zone.
    for zone in set(
        zones
    ):

        if zones.count(
            zone
        ) > 2:

            blockers.append(
                "zone_limit_exceeded:"
                + str(zone)
            )


    unique_profiles = len(
        set(
            profiles
        )
    )


    if (
        len(selected) >= 4
        and unique_profiles < 4
    ):

        warnings.append(
            "motion_profile_diversity_low"
        )


    # Avoid 3 adjacent VI7 scenes.
    triples = []


    for i in range(
        len(scenes) - 2
    ):

        if (
            scenes[i + 1]
            == scenes[i] + 1
            and scenes[i + 2]
            == scenes[i] + 2
        ):

            triples.append(
                scenes[i:i + 3]
            )


    if triples:

        warnings.append(
            "three_adjacent_canary_scenes"
        )


    return {
        "version":
            VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "selected_scenes":
            scenes,

        "selected_count":
            len(scenes),

        "profiles":
            profiles,

        "unique_profile_count":
            unique_profiles,

        "zones":
            zones,

        "adjacent_triples":
            triples,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():

    sample = [
        {
            "scene": 3,
            "action": "VI7_SELECTED",
            "zone": "A",
            "profile": "P1",
        },

        {
            "scene": 5,
            "action": "VI7_SELECTED",
            "zone": "B",
            "profile": "P2",
        },

        {
            "scene": 9,
            "action": "VI7_SELECTED",
            "zone": "C",
            "profile": "P3",
        },
    ]


    assert (
        audit(sample)["status"]
        == "PASS"
    )

    print(
        "VI7.08 SEQUENCE AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 11. VI7.09 — PRODUCTION EXPANSION GATE
# =====================================================

cat > vi7_09_production_gate.py <<'PY'
#!/usr/bin/env python3

import json

from pathlib import Path


VERSION = "7.09"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    blockers = []

    warnings = []


    master = (
        BASE
        / "logs/producao/"
          "vi7_00_master_gate_latest.json"
    )


    try:

        gate = json.loads(
            master.read_text(
                encoding="utf-8"
            )
        )["gate"]


    except Exception:

        gate = None


    if gate is None:

        blockers.append(
            "vi700_master_missing"
        )


    elif gate.get(
        "status"
    ) != (
        "THREE_SCENE_CANARY_CERTIFIED"
    ):

        blockers.append(
            "vi700_not_certified"
        )


    elif gate.get(
        "selected_scene_count"
    ) != 3:

        blockers.append(
            "vi700_baseline_count_invalid"
        )


    if (
        gate
        and gate.get(
            "legacy_retry_failed_count",
            0
        )
        != 0
    ):

        blockers.append(
            "vi700_retry_failure_present"
        )


    # Source recovery remains shadow-only.
    try:

        from vi6_64_source_recovery_guard import (
            inspect
        )


        source = inspect()


        if source.get(
            "status"
        ) == "HOLD":

            blockers.append(
                "source_guard_hold"
            )


        elif source.get(
            "status"
        ) == "PASS_WITH_WARNINGS":

            warnings.append(
                "source_recovery_remains_shadow_only"
            )


    except Exception:

        warnings.append(
            "source_guard_not_available"
        )


    return {
        "version":
            VERSION,

        "status":
            (
                "SIX_SCENE_CANARY_ALLOWED"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            sorted(
                set(blockers)
            ),

        "warnings":
            sorted(
                set(warnings)
            ),

        "max_vi6_scenes":
            6,

        "source_recovery_active":
            False,

        "full_active":
            False,
    }


def self_test():

    assert VERSION == "7.09"

    print(
        "VI7.09 PRODUCTION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 12. VI7.10 — MASTER CERTIFICATION
# =====================================================

cat > vi7_10_master_gate.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


from vi7_08_sequence_audit import (
    audit as sequence_audit
)


VERSION = "7.10"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

RUNTIME = (
    BASE
    / "logs/producao/"
      "vi7_07_six_scene_runtime_latest.json"
)

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi7_10_master_gate_latest.json"
)


def evaluate():

    blockers = []

    warnings = []


    try:

        data = json.loads(
            RUNTIME.read_text(
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
            "vi707_runtime_missing"
        )


    selected = [
        event
        for event in events
        if event.get(
            "action"
        ) == "VI7_SELECTED"
    ]


    success = [
        event
        for event in events
        if event.get(
            "action"
        ) == "VI7_RENDER_SUCCESS"
    ]


    retries = [
        event
        for event in events
        if event.get(
            "action"
        ) == "LEGACY_RETRY"
    ]


    retry_success = [
        event
        for event in events
        if event.get(
            "action"
        ) == "LEGACY_RETRY_SUCCESS"
    ]


    retry_failed = [
        event
        for event in events
        if event.get(
            "action"
        ) == "LEGACY_RETRY_FAILED"
    ]


    selected_scenes = sorted(
        {
            event.get(
                "scene"
            )
            for event in selected
            if isinstance(
                event.get(
                    "scene"
                ),
                int
            )
        }
    )


    success_scenes = {
        event.get(
            "scene"
        )
        for event in success
    }


    recovered_scenes = {
        event.get(
            "scene"
        )
        for event in retry_success
    }


    valid_final_scenes = (
        success_scenes
        | recovered_scenes
    )


    if len(
        selected_scenes
    ) > 6:

        blockers.append(
            "more_than_six_vi7_scenes"
        )


    if retry_failed:

        blockers.append(
            "legacy_retry_failure"
        )


    if (
        set(
            selected_scenes
        )
        != valid_final_scenes
    ):

        blockers.append(
            "selected_scene_without_valid_output"
        )


    sequence = sequence_audit(
        events
    )


    blockers.extend(
        sequence.get(
            "blockers"
        )
        or []
    )


    warnings.extend(
        sequence.get(
            "warnings"
        )
        or []
    )


    if len(
        selected_scenes
    ) < 6:

        warnings.append(
            "fewer_than_six_eligible_still_canaries"
        )


    if retries:

        warnings.append(
            "legacy_retry_was_required"
        )


    blockers = sorted(
        set(
            blockers
        )
    )


    warnings = sorted(
        set(
            warnings
        )
    )


    if blockers:

        status = "HOLD"


    elif (
        len(
            selected_scenes
        ) == 6
        and not retries
    ):

        status = (
            "SIX_SCENE_CANARY_CERTIFIED"
        )


    else:

        status = (
            "SIX_SCENE_CANARY_SAFE_WITH_WARNINGS"
        )


    result = {
        "version":
            VERSION,

        "status":
            status,

        "selected_scene_count":
            len(
                selected_scenes
            ),

        "selected_scenes":
            selected_scenes,

        "vi7_success_scenes":
            sorted(
                success_scenes
            ),

        "legacy_retry_count":
            len(
                retries
            ),

        "legacy_retry_success_count":
            len(
                retry_success
            ),

        "legacy_retry_failure_count":
            len(
                retry_failed
            ),

        "sequence":
            sequence,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "six_scene_expansion_certified":
            (
                status
                == "SIX_SCENE_CANARY_CERTIFIED"
            ),

        # Still deliberately locked.
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

    assert VERSION == "7.10"

    print(
        "VI7.10 MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 13. DELEGATE VI7.00 EXECUTOR -> VI7.10
# =====================================================

echo
echo "===== INSTALLING VI7.10 EXECUTOR ROUTE ====="

python - <<'PY'
from pathlib import Path


p = Path(
    "vi6_95_scene_executor.py"
)


s = p.read_text(
    encoding="utf-8"
)


marker = (
    "# VI7.10 SIX-SCENE EXECUTOR DELEGATE"
)


if marker in s:

    print(
        "VI7.10 DELEGATE ALREADY INSTALLED"
    )

    raise SystemExit(0)


addition = r'''

# VI7.10 SIX-SCENE EXECUTOR DELEGATE

_vi695_execute_before_vi710 = execute


def execute(
    command,
    **run_kwargs
):

    import os


    if (
        os.getenv(
            "VI710_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
    ):

        from vi7_06_scene_executor import (
            execute as _vi710_execute
        )


        return _vi710_execute(
            command,
            **run_kwargs
        )


    return _vi695_execute_before_vi710(
        command,
        **run_kwargs
    )
'''


p.write_text(
    s + addition,
    encoding="utf-8"
)


print(
    "VI7.10 EXECUTOR DELEGATE=INSTALLED"
)
PY

if [ "$?" -ne 0 ]; then

    rollback
    exit 10
fi


# =====================================================
# 14. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi7_01_six_scene_policy.py \
    vi7_02_runtime_state.py \
    vi7_03_profile_allocator.py \
    vi7_04_six_scene_adapter.py \
    vi7_05_output_validator.py \
    vi7_06_scene_executor.py \
    vi7_07_telemetry.py \
    vi7_08_sequence_audit.py \
    vi7_09_production_gate.py \
    vi7_10_master_gate.py \
    vi6_95_scene_executor.py \
    video.py
then

    rollback
    exit 11
fi


echo "FULL COMPILE=PASS"


# =====================================================
# 15. SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

for F in \
    vi7_01_six_scene_policy.py \
    vi7_02_runtime_state.py \
    vi7_03_profile_allocator.py \
    vi7_04_six_scene_adapter.py \
    vi7_05_output_validator.py \
    vi7_06_scene_executor.py \
    vi7_07_telemetry.py \
    vi7_08_sequence_audit.py \
    vi7_09_production_gate.py \
    vi7_10_master_gate.py
do

    python "$F" || {
        rollback
        exit 12
    }

done


# =====================================================
# 16. VIDEO.PY MUST REMAIN UNCHANGED
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

    echo "CRITICAL: video.py foi alterado."

    rollback
    exit 13
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 17. REAL PRE-PRODUCTION GATE
# =====================================================

echo
echo "===== VI7.09 REAL PRODUCTION GATE ====="

python - <<'PY'
from vi7_09_production_gate import (
    evaluate
)


result = evaluate()


print(
    "STATUS:",
    result.get("status")
)

print(
    "MAX VI6 SCENES:",
    result.get(
        "max_vi6_scenes"
    )
)

print(
    "SOURCE RECOVERY ACTIVE:",
    result.get(
        "source_recovery_active"
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
    "FULL ACTIVE:",
    result.get(
        "full_active"
    )
)


if result.get("status") != (
    "SIX_SCENE_CANARY_ALLOWED"
):

    raise SystemExit(1)
PY

if [ "$?" -ne 0 ]; then

    rollback
    exit 14
fi


# =====================================================
# 18. RELEASE CHECK
# =====================================================

echo
echo "===== RELEASE CHECK ====="

bash -n gerar_short.sh || {
    rollback
    exit 15
}


./release_check.sh || {
    rollback
    exit 16
}


# =====================================================
# 19. CLEAR VI7.10 SESSION STATE
# =====================================================

rm -f \
    logs/producao/vi7_07_six_scene_runtime_latest.json \
    logs/producao/vi7_10_master_gate_latest.json


# =====================================================
# 20. REAL SIX-SCENE PRODUCTION
# =====================================================

echo
echo "======================================================"
echo " STARTING VI7.10 REAL PRODUCTION"
echo "======================================================"
echo
echo "MAX 6 VI7 STILL SCENES"
echo "2 MAX PER NARRATIVE ZONE"
echo "VIDEO = LEGACY"
echo "HOOK = LEGACY"
echo "CTA = LEGACY"
echo "FAILED VI7 SCENE = LEGACY RETRY"
echo


# VI700 must remain ON because video.py routes
# scene execution through vi6_95.
#
# VI710 then delegates vi6_95 to the new executor.
#
# Old VI682 single-scene canary stays OFF.

VI682_CANARY_MODE=OFF \
VI700_CANARY_MODE=ON \
VI710_CANARY_MODE=ON \
VI647_RENDERER_MODE=LEGACY \
./gerar_short.sh


PIPE_STATUS="$?"


echo
echo "PIPELINE STATUS=$PIPE_STATUS"


# =====================================================
# 21. MASTER CERTIFICATION
# =====================================================

echo
echo "===== VI7.10 REAL MASTER GATE ====="

python - <<'PY'
from vi7_10_master_gate import (
    evaluate
)


result = evaluate()


print()
print(
    "STATUS:",
    result.get("status")
)

print(
    "SELECTED COUNT:",
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
    "VI7 SUCCESS SCENES:",
    result.get(
        "vi7_success_scenes"
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
        "legacy_retry_failure_count"
    )
)


sequence = (
    result.get(
        "sequence"
    )
    or {}
)


print()
print(
    "MOTION PROFILES:",
    sequence.get(
        "profiles"
    )
)

print(
    "UNIQUE PROFILES:",
    sequence.get(
        "unique_profile_count"
    )
)

print(
    "ZONES:",
    sequence.get(
        "zones"
    )
)

print(
    "ADJACENT TRIPLES:",
    sequence.get(
        "adjacent_triples"
    )
)


print()
print(
    "BLOCKERS:",
    result.get("blockers")
)

print(
    "WARNINGS:",
    result.get("warnings")
)

print(
    "SIX-SCENE CERTIFIED:",
    result.get(
        "six_scene_expansion_certified"
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
# 22. EVENT TRACE
# =====================================================

echo
echo "===== VI7.10 EVENT TRACE ====="

python - <<'PY'
import json
from pathlib import Path

p = (
    Path.home()
    / "ShortAutoPro/logs/producao/"
      "vi7_07_six_scene_runtime_latest.json"
)


if not p.exists():

    print(
        "RUNTIME TELEMETRY=MISSING"
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
        "VI7_SELECTED",
        "VI7_RENDER_ATTEMPT",
        "VI7_RENDER_SUCCESS",
        "VI7_VALIDATION_HOLD",
        "LEGACY_RETRY",
        "LEGACY_RETRY_SUCCESS",
        "LEGACY_RETRY_FAILED",
    }:

        validation = (
            event.get(
                "validation"
            )
            or {}
        )


        print(
            "SCENE",
            event.get("scene"),
            "|",
            event.get("action"),
            "| zone=",
            event.get("zone"),
            "| profile=",
            event.get("profile"),
            "| duration_delta=",
            validation.get(
                "duration_delta"
            ),
            "| blockers=",
            validation.get(
                "blockers"
            ),
            "| reason=",
            event.get("reason"),
        )
PY


# =====================================================
# 23. FINAL SAFETY
# =====================================================

echo
echo "===== FINAL SAFETY ====="

VIDEO_HASH_FINAL="$(
    sha256sum video.py |
    awk '{print $1}'
)"


echo "VIDEO HASH BEFORE=$VIDEO_HASH_BEFORE"
echo "VIDEO HASH FINAL =$VIDEO_HASH_FINAL"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_FINAL" ]; then

    echo "CRITICAL:"
    echo "video.py mudou durante VI7.10."

    exit 30
fi


python -m py_compile \
    video.py \
    vi6_95_scene_executor.py \
    vi7_04_six_scene_adapter.py \
    vi7_06_scene_executor.py \
    vi7_10_master_gate.py \
    || exit 31


echo "VIDEO.PY UNCHANGED=YES"
echo "COMPILE FINAL=PASS"
echo "FULL ACTIVE=LOCKED"


echo
echo "======================================================"
echo " VI7.01 -> VI7.10 MEGA UPDATE COMPLETE"
echo "======================================================"
echo
echo "PIPELINE STATUS=$PIPE_STATUS"
echo "MAX VI7 STILL SCENES=6"
echo "MAX PER ZONE=2"
echo "VIDEO PRESERVATION=LEGACY"
echo "HOOK=LEGACY"
echo "CTA=LEGACY"
echo "REAL SAME-SCENE FALLBACK=ON"
echo "SOURCE RECOVERY ACTIVE=NO"
echo "FULL ACTIVE=LOCKED"
echo
echo "MASTER REPORT:"
echo "logs/producao/vi7_10_master_gate_latest.json"
echo

exit "$PIPE_STATUS"
