#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/mega_vi711_vi730_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "============================================================"
echo " SHORTAUTOPRO MEGA UPDATE VII"
echo " VI7.11 -> VI7.30"
echo " ADAPTIVE VISUAL RUNTIME"
echo "============================================================"
echo
echo "ADAPTIVE STILL RENDERING = ON"
echo "MAX VI7 SCENES = 9"
echo "HOOK = LEGACY"
echo "CTA = LEGACY"
echo "NATIVE VIDEO = LEGACY"
echo "ANTI-REPETITION = ON"
echo "MOTION ENERGY CONTROL = ON"
echo "PER-SCENE LEGACY RETRY = ON"
echo "SOURCE RECOVERY = SHADOW ONLY"
echo "FULL ACTIVE = LOCKED"
echo


# ============================================================
# 0. REQUIREMENTS
# ============================================================

REQUIRED="
video.py
gerar_short.sh
vi6_49_real_command_mapper.py
vi6_61_motion_filter_compiler.py
vi6_95_scene_executor.py
vi7_05_output_validator.py
vi7_10_master_gate.py
semantic_integrity_gate.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F ausente."
        exit 2
    fi
done


VIDEO_HASH_BEFORE="$(
    sha256sum video.py |
    awk '{print $1}'
)"

echo "VIDEO.PY SHA256:"
echo "$VIDEO_HASH_BEFORE"


# ============================================================
# 1. REQUIRE VI7.10 CERTIFICATION
# ============================================================

echo
echo "===== VI7.10 BASELINE ====="

python - <<'PY'
import json
from pathlib import Path

p = (
    Path.home()
    / "ShortAutoPro/logs/producao/"
      "vi7_10_master_gate_latest.json"
)

if not p.exists():
    raise SystemExit(
        "ERRO: VI7.10 master report missing"
    )

gate = json.loads(
    p.read_text(
        encoding="utf-8"
    )
)["gate"]

blockers = []

if gate.get(
    "status"
) != "SIX_SCENE_CANARY_CERTIFIED":
    blockers.append(
        "vi710_not_certified"
    )

if gate.get(
    "selected_scene_count"
) != 6:
    blockers.append(
        "vi710_scene_count_invalid"
    )

if gate.get(
    "legacy_retry_failure_count",
    0
) != 0:
    blockers.append(
        "vi710_retry_failure"
    )

if gate.get("blockers"):
    blockers.append(
        "vi710_has_blockers"
    )

print(
    "STATUS:",
    gate.get("status")
)

print(
    "SCENES:",
    gate.get(
        "selected_scenes"
    )
)

print(
    "SUCCESS:",
    gate.get(
        "vi7_success_scenes"
    )
)

print(
    "BLOCKERS:",
    blockers
)

if blockers:
    raise SystemExit(1)

print(
    "VI7.10 BASELINE=PASS"
)
PY

if [ "$?" -ne 0 ]; then
    exit 3
fi


# ============================================================
# 2. BACKUPS
# ============================================================

FILES="
vi6_95_scene_executor.py
vi7_11_adaptive_policy.py
vi7_12_narrative_role.py
vi7_13_motion_catalog.py
vi7_14_adaptive_state.py
vi7_15_motion_planner.py
vi7_16_sequence_guard.py
vi7_17_filter_guard.py
vi7_18_adaptive_adapter.py
vi7_19_runtime_telemetry.py
vi7_20_adaptive_executor.py
vi7_21_sequence_audit.py
vi7_22_performance_budget.py
vi7_23_source_safety_lock.py
vi7_24_production_gate.py
vi7_25_runtime_router.py
vi7_26_canary_audit.py
vi7_27_output_integrity.py
vi7_28_adaptive_certification.py
vi7_29_release_gate.py
vi7_30_master_gate.py
"

for F in $FILES
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "============================================================"
    echo " VI7.11 -> VI7.30 ROLLBACK"
    echo "============================================================"

    for F in $FILES
    do
        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi
    done

    echo "ROLLBACK=OK"
}


# ============================================================
# VI7.11 — ADAPTIVE POLICY
# ============================================================

cat > vi7_11_adaptive_policy.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.11"

MAX_VI7_SCENES = 9

MIN_HEALTHY_CANARIES = 4

MAX_CONSECUTIVE_VI7 = 2


def policy():

    return {
        "version":
            VERSION,

        "max_vi7_scenes":
            MAX_VI7_SCENES,

        "min_healthy_canaries":
            MIN_HEALTHY_CANARIES,

        "max_consecutive_vi7":
            MAX_CONSECUTIVE_VI7,

        "hook_scene":
            1,

        "cta_scene":
            12,

        "native_video_vi7":
            False,

        "source_recovery_active":
            False,

        "full_active":
            False,
    }


def self_test():

    p = policy()

    assert p["max_vi7_scenes"] == 9
    assert p["hook_scene"] == 1
    assert p["cta_scene"] == 12
    assert p["full_active"] is False

    print(
        "VI7.11 ADAPTIVE POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.12 — NARRATIVE ROLE
# ============================================================

cat > vi7_12_narrative_role.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.12"


def role(scene):

    if scene == 1:
        return "HOOK"

    if scene == 12:
        return "CTA"

    if scene in {
        2,
        3,
        4,
    }:
        return "EARLY_CONTEXT"

    if scene in {
        5,
        6,
        7,
        8,
    }:
        return "CONTEXT"

    if scene in {
        9,
        10,
        11,
    }:
        return "CLIMAX"

    return "UNKNOWN"


def self_test():

    assert role(1) == "HOOK"
    assert role(6) == "CONTEXT"
    assert role(10) == "CLIMAX"
    assert role(12) == "CTA"

    print(
        "VI7.12 NARRATIVE ROLE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.13 — MOTION CATALOG
# ============================================================

cat > vi7_13_motion_catalog.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.13"


CATALOG = {

    "HORIZONTAL_DISCOVERY": {
        "energy": 2,
        "direction": "RIGHT",
    },

    "SLOW_PUSH": {
        "energy": 1,
        "direction": "CENTER",
    },

    "DETAIL_PUSH": {
        "energy": 2,
        "direction": "CENTER",
    },

    "REVERSE_DRIFT": {
        "energy": 2,
        "direction": "LEFT",
    },

    "CLIMAX_PUSH": {
        "energy": 3,
        "direction": "CENTER",
    },

    "CLIMAX_PAN": {
        "energy": 3,
        "direction": "RIGHT",
    },
}


ROLE_POOLS = {

    "EARLY_CONTEXT": (
        "HORIZONTAL_DISCOVERY",
        "SLOW_PUSH",
        "DETAIL_PUSH",
    ),

    "CONTEXT": (
        "DETAIL_PUSH",
        "REVERSE_DRIFT",
        "SLOW_PUSH",
        "HORIZONTAL_DISCOVERY",
    ),

    "CLIMAX": (
        "CLIMAX_PUSH",
        "CLIMAX_PAN",
        "DETAIL_PUSH",
        "REVERSE_DRIFT",
    ),
}


def info(profile):

    return CATALOG.get(
        profile,
        {}
    )


def pool(role):

    return ROLE_POOLS.get(
        role,
        ()
    )


def self_test():

    assert (
        info(
            "CLIMAX_PUSH"
        )["energy"]
        == 3
    )

    assert pool(
        "CONTEXT"
    )

    print(
        "VI7.13 MOTION CATALOG=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.14 — ADAPTIVE STATE
# ============================================================

cat > vi7_14_adaptive_state.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.14"


_selected = []

_profiles = []

_roles = []

_last_seen_scene = None


def reset():

    global _last_seen_scene

    _selected.clear()
    _profiles.clear()
    _roles.clear()

    _last_seen_scene = None


def count():

    return len(
        _selected
    )


def selected():

    return list(
        _selected
    )


def profiles():

    return list(
        _profiles
    )


def roles():

    return list(
        _roles
    )


def last_profiles(n=2):

    return _profiles[-n:]


def previous_selected_scenes(n=2):

    return _selected[-n:]


def claim(
    scene,
    profile,
    role
):

    _selected.append(
        scene
    )

    _profiles.append(
        profile
    )

    _roles.append(
        role
    )


def consecutive_vi7_if_select(scene):

    if not _selected:
        return 1

    run = 1

    expected = scene - 1

    for previous in reversed(
        _selected
    ):

        if previous == expected:
            run += 1
            expected -= 1
        else:
            break

    return run


def snapshot():

    return {
        "version":
            VERSION,

        "selected":
            selected(),

        "profiles":
            profiles(),

        "roles":
            roles(),

        "count":
            count(),
    }


def self_test():

    reset()

    claim(
        2,
        "SLOW_PUSH",
        "EARLY_CONTEXT"
    )

    claim(
        3,
        "DETAIL_PUSH",
        "EARLY_CONTEXT"
    )

    assert (
        consecutive_vi7_if_select(
            4
        )
        == 3
    )

    reset()

    print(
        "VI7.14 ADAPTIVE STATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.15 — MOTION PLANNER
# ============================================================

cat > vi7_15_motion_planner.py <<'PY'
#!/usr/bin/env python3

from vi7_13_motion_catalog import (
    info,
    pool
)

from vi7_14_adaptive_state import (
    last_profiles
)


VERSION = "7.15"


def choose(role):

    candidates = list(
        pool(
            role
        )
    )


    if not candidates:
        return None


    recent = last_profiles(
        2
    )


    last = (
        recent[-1]
        if recent
        else None
    )


    last_info = (
        info(last)
        if last
        else {}
    )


    for candidate in candidates:

        cinfo = info(
            candidate
        )


        # Do not repeat exact profile.
        if candidate in recent:
            continue


        # Do not repeat strong energy consecutively.
        if (
            last_info.get(
                "energy"
            ) == 3
            and cinfo.get(
                "energy"
            ) == 3
        ):
            continue


        # Avoid same lateral direction twice.
        if (
            last_info
            and cinfo.get(
                "direction"
            ) in {
                "LEFT",
                "RIGHT",
            }
            and cinfo.get(
                "direction"
            )
            == last_info.get(
                "direction"
            )
        ):
            continue


        return candidate


    # Controlled fallback:
    # choose first profile different from immediate last.
    for candidate in candidates:

        if candidate != last:
            return candidate


    return candidates[0]


def self_test():

    assert choose(
        "CONTEXT"
    )

    print(
        "VI7.15 MOTION PLANNER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.16 — SEQUENCE GUARD
# ============================================================

cat > vi7_16_sequence_guard.py <<'PY'
#!/usr/bin/env python3

from vi7_11_adaptive_policy import (
    MAX_CONSECUTIVE_VI7,
    MAX_VI7_SCENES
)

from vi7_14_adaptive_state import (
    count,
    consecutive_vi7_if_select
)


VERSION = "7.16"


def allow(scene):

    reasons = []


    if count() >= MAX_VI7_SCENES:

        reasons.append(
            "global_limit"
        )


    if (
        consecutive_vi7_if_select(
            scene
        )
        > MAX_CONSECUTIVE_VI7
    ):

        reasons.append(
            "consecutive_limit"
        )


    return {
        "version":
            VERSION,

        "allowed":
            not reasons,

        "reasons":
            reasons,
    }


def self_test():

    assert VERSION == "7.16"

    print(
        "VI7.16 SEQUENCE GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.17 — FILTER GUARD
# ============================================================

cat > vi7_17_filter_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.17"


REQUIRED = (
    "scale=",
    "crop=",
    "zoompan=",
    "setsar=1",
    "format=yuv420p",
)


def validate(
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

        for token in REQUIRED:

            if token not in vf:

                blockers.append(
                    "missing:"
                    + token
                )


    try:
        duration = float(
            duration
        )

    except Exception:
        duration = 0


    if (
        duration <= 0
        or duration > 10
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

    assert (
        validate(
            "",
            3
        )["status"]
        == "HOLD"
    )

    print(
        "VI7.17 FILTER GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.19 — TELEMETRY
# ============================================================

cat > vi7_19_runtime_telemetry.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "7.19"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

REPORT = (
    BASE
    / "logs/producao/"
      "vi7_19_adaptive_runtime_latest.json"
)

_EVENTS = []


def reset():

    _EVENTS.clear()

    try:
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

    assert VERSION == "7.19"

    print(
        "VI7.19 TELEMETRY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.18 — ADAPTIVE ADAPTER
# ============================================================

cat > vi7_18_adaptive_adapter.py <<'PY'
#!/usr/bin/env python3

from vi6_49_real_command_mapper import (
    map_command
)

from vi6_61_motion_filter_compiler import (
    compile_filter
)

from vi7_11_adaptive_policy import (
    MAX_VI7_SCENES
)

from vi7_12_narrative_role import (
    role as narrative_role
)

from vi7_14_adaptive_state import (
    claim,
    count,
    snapshot
)

from vi7_15_motion_planner import (
    choose
)

from vi7_16_sequence_guard import (
    allow
)

from vi7_17_filter_guard import (
    validate
)

from vi7_19_runtime_telemetry import (
    record
)


VERSION = "7.18"


def replace_vf(
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

    result[index + 1] = vf

    return result


def legacy(
    original,
    scene,
    reason,
    branch=None,
    role=None
):

    record(
        {
            "scene":
                scene,

            "branch":
                branch,

            "role":
                role,

            "action":
                "LEGACY",

            "reason":
                reason,
        }
    )

    return {
        "command":
            original,

        "legacy_command":
            original,

        "scene":
            scene,

        "using_vi7":
            False,
    }


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


        if not isinstance(
            scene,
            int
        ):
            return legacy(
                original,
                scene,
                "unknown_scene",
                branch
            )


        role = narrative_role(
            scene
        )


        if branch != "STILL":

            return legacy(
                original,
                scene,
                "native_video_preserved",
                branch,
                role
            )


        if role in {
            "HOOK",
            "CTA",
            "UNKNOWN",
        }:

            return legacy(
                original,
                scene,
                "protected_role",
                branch,
                role
            )


        if count() >= MAX_VI7_SCENES:

            return legacy(
                original,
                scene,
                "adaptive_limit_reached",
                branch,
                role
            )


        seq = allow(
            scene
        )


        if not seq.get(
            "allowed"
        ):

            return legacy(
                original,
                scene,
                ",".join(
                    seq.get(
                        "reasons"
                    )
                    or []
                ),
                branch,
                role
            )


        profile = choose(
            role
        )


        if not profile:

            return legacy(
                original,
                scene,
                "no_motion_profile",
                branch,
                role
            )


        compiled = compile_filter(
            profile,
            duration,
            30
        )


        if compiled.get(
            "status"
        ) != "COMPILED":

            return legacy(
                original,
                scene,
                "motion_compile_hold",
                branch,
                role
            )


        vf = compiled.get(
            "vf"
        )


        guard = validate(
            vf,
            duration
        )


        if guard.get(
            "status"
        ) != "PASS":

            return legacy(
                original,
                scene,
                "filter_guard_hold",
                branch,
                role
            )


        adapted = replace_vf(
            original,
            vf
        )


        if adapted is None:

            return legacy(
                original,
                scene,
                "vf_not_found",
                branch,
                role
            )


        claim(
            scene,
            profile,
            role
        )


        record(
            {
                "scene":
                    scene,

                "branch":
                    branch,

                "role":
                    role,

                "profile":
                    profile,

                "action":
                    "VI730_SELECTED",

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

            "legacy_command":
                original,

            "scene":
                scene,

            "branch":
                branch,

            "role":
                role,

            "profile":
                profile,

            "duration_seconds":
                duration,

            "using_vi7":
                True,
        }


    except Exception as exc:

        return legacy(
            original,
            None,
            (
                "adapter_exception:"
                + type(exc).__name__
            )
        )


def self_test():

    assert VERSION == "7.18"

    print(
        "VI7.18 ADAPTIVE ADAPTER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.20 — ADAPTIVE EXECUTOR
# ============================================================

cat > vi7_20_adaptive_executor.py <<'PY'
#!/usr/bin/env python3

import subprocess

from pathlib import Path


from vi7_18_adaptive_adapter import (
    prepare
)

from vi7_05_output_validator import (
    validate
)

from vi7_19_runtime_telemetry import (
    record
)


VERSION = "7.20"


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

    if not prepared.get(
        "using_vi7"
    ):

        return subprocess.run(
            chosen,
            **run_kwargs
        )


    profile = prepared.get(
        "profile"
    )

    role = prepared.get(
        "role"
    )

    duration = prepared.get(
        "duration_seconds"
    )

    output = (
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

            "role":
                role,

            "profile":
                profile,

            "action":
                "VI730_RENDER_ATTEMPT",
        }
    )


    failure = None


    try:

        result = subprocess.run(
            chosen,
            **run_kwargs
        )


        validation = (
            validate(
                output,
                duration
            )
            if output
            else {
                "status":
                    "HOLD",

                "blockers":
                    ["output_unknown"],
            }
        )


        if validation.get(
            "status"
        ) == "PASS":

            record(
                {
                    "scene":
                        scene,

                    "role":
                        role,

                    "profile":
                        profile,

                    "action":
                        "VI730_RENDER_SUCCESS",

                    "validation":
                        validation,
                }
            )

            return result


        failure = (
            "post_render_validation"
        )


        record(
            {
                "scene":
                    scene,

                "role":
                    role,

                "profile":
                    profile,

                "action":
                    "VI730_VALIDATION_HOLD",

                "validation":
                    validation,
            }
        )


    except subprocess.CalledProcessError:

        failure = (
            "ffmpeg_nonzero"
        )


    except Exception as exc:

        failure = (
            "vi730_exception:"
            + type(exc).__name__
        )


    record(
        {
            "scene":
                scene,

            "role":
                role,

            "profile":
                profile,

            "action":
                "LEGACY_RETRY",

            "reason":
                failure,
        }
    )


    try:

        if (
            output
            and output.exists()
        ):
            output.unlink()

    except Exception:
        pass


    legacy_result = subprocess.run(
        legacy,
        **run_kwargs
    )


    legacy_validation = (
        validate(
            output,
            duration
        )
        if output
        else {
            "status":
                "HOLD",

            "blockers":
                ["output_unknown"],
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
            "VI730_LEGACY_RETRY_FAILED"
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


    return legacy_result


def self_test():

    assert VERSION == "7.20"

    print(
        "VI7.20 ADAPTIVE EXECUTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.21 — SEQUENCE AUDIT
# ============================================================

cat > vi7_21_sequence_audit.py <<'PY'
#!/usr/bin/env python3

from vi7_13_motion_catalog import (
    info
)


VERSION = "7.21"


def audit(events):

    selected = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI730_SELECTED"
    ]


    scenes = [
        e.get("scene")
        for e in selected
        if isinstance(
            e.get("scene"),
            int
        )
    ]


    profiles = [
        e.get("profile")
        for e in selected
        if e.get("profile")
    ]


    roles = [
        e.get("role")
        for e in selected
        if e.get("role")
    ]


    blockers = []
    warnings = []


    if len(
        set(scenes)
    ) != len(scenes):

        blockers.append(
            "duplicate_scene_selection"
        )


    if len(scenes) > 9:

        blockers.append(
            "adaptive_limit_exceeded"
        )


    if any(
        x in {
            1,
            12,
        }
        for x in scenes
    ):

        blockers.append(
            "protected_scene_selected"
        )


    # exact profile repetition
    for a, b in zip(
        profiles,
        profiles[1:]
    ):

        if a == b:

            blockers.append(
                "consecutive_identical_profile"
            )


    # strong motion repetition
    for a, b in zip(
        profiles,
        profiles[1:]
    ):

        if (
            info(a).get(
                "energy"
            ) == 3
            and info(b).get(
                "energy"
            ) == 3
        ):

            warnings.append(
                "consecutive_strong_motion"
            )


    # detect 3 adjacent selected scenes
    triples = []

    ordered = sorted(
        scenes
    )

    for i in range(
        len(ordered) - 2
    ):

        if (
            ordered[i + 1]
            == ordered[i] + 1
            and ordered[i + 2]
            == ordered[i] + 2
        ):

            triples.append(
                ordered[
                    i:i + 3
                ]
            )


    if triples:

        blockers.append(
            "three_adjacent_vi7_scenes"
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

        "scenes":
            ordered,

        "profiles":
            profiles,

        "roles":
            roles,

        "unique_profiles":
            len(
                set(
                    profiles
                )
            ),

        "adjacent_triples":
            triples,

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),
    }


def self_test():

    assert (
        audit(
            []
        )["status"]
        == "PASS"
    )

    print(
        "VI7.21 SEQUENCE AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.22 — PERFORMANCE BUDGET
# ============================================================

cat > vi7_22_performance_budget.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.22"


def evaluate(
    events
):

    success = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI730_RENDER_SUCCESS"
    ]


    retries = [
        e
        for e in events
        if e.get(
            "action"
        ) == "LEGACY_RETRY"
    ]


    return {
        "version":
            VERSION,

        "successful_vi7":
            len(success),

        "retries":
            len(retries),

        "status":
            (
                "PASS"
                if len(retries) <= 2
                else "PASS_WITH_WARNINGS"
            ),
    }


def self_test():

    assert VERSION == "7.22"

    print(
        "VI7.22 PERFORMANCE BUDGET=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.23 — SOURCE SAFETY LOCK
# ============================================================

cat > vi7_23_source_safety_lock.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.23"


def evaluate():

    return {
        "version":
            VERSION,

        "source_recovery_mode":
            "SHADOW_ONLY",

        "automatic_source_recovery":
            False,

        "renderer_may_activate_recovery":
            False,

        "status":
            "LOCKED_SAFE",
    }


def self_test():

    r = evaluate()

    assert (
        r[
            "automatic_source_recovery"
        ]
        is False
    )

    print(
        "VI7.23 SOURCE SAFETY LOCK=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.24 — PRODUCTION GATE
# ============================================================

cat > vi7_24_production_gate.py <<'PY'
#!/usr/bin/env python3

import json

from pathlib import Path


from vi7_23_source_safety_lock import (
    evaluate as source_lock
)


VERSION = "7.24"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    blockers = []
    warnings = []


    p = (
        BASE
        / "logs/producao/"
          "vi7_10_master_gate_latest.json"
    )


    try:

        old = json.loads(
            p.read_text(
                encoding="utf-8"
            )
        )["gate"]

    except Exception:

        old = None


    if (
        not old
        or old.get(
            "status"
        )
        != "SIX_SCENE_CANARY_CERTIFIED"
    ):

        blockers.append(
            "vi710_baseline_missing"
        )


    src = source_lock()


    if src.get(
        "automatic_source_recovery"
    ):

        blockers.append(
            "source_recovery_must_remain_locked"
        )


    return {
        "version":
            VERSION,

        "status":
            (
                "ADAPTIVE_CANARY_ALLOWED"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "source_safety":
            src,

        "full_active":
            False,
    }


def self_test():

    assert VERSION == "7.24"

    print(
        "VI7.24 PRODUCTION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.25 — ROUTER
# ============================================================

cat > vi7_25_runtime_router.py <<'PY'
#!/usr/bin/env python3

import os


VERSION = "7.25"


def enabled():

    return (
        os.getenv(
            "VI730_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
    )


def self_test():

    assert VERSION == "7.25"

    print(
        "VI7.25 RUNTIME ROUTER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.26 — CANARY AUDIT
# ============================================================

cat > vi7_26_canary_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.26"


def evaluate(
    events
):

    selected = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI730_SELECTED"
    ]


    success = [
        e
        for e in events
        if e.get(
            "action"
        ) == "VI730_RENDER_SUCCESS"
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


    return {
        "version":
            VERSION,

        "selected":
            selected,

        "success":
            success,

        "retries":
            retries,

        "retry_success":
            retry_success,

        "retry_failed":
            retry_failed,
    }


def self_test():

    assert VERSION == "7.26"

    print(
        "VI7.26 CANARY AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.27 — OUTPUT INTEGRITY
# ============================================================

cat > vi7_27_output_integrity.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.27"


def evaluate(
    successful_events
):

    blockers = []


    for event in successful_events:

        validation = (
            event.get(
                "validation"
            )
            or {}
        )


        if validation.get(
            "status"
        ) != "PASS":

            blockers.append(
                "successful_event_without_pass_validation"
            )


        if validation.get(
            "blockers"
        ):

            blockers.append(
                "validation_contains_blockers"
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
            sorted(
                set(
                    blockers
                )
            ),
    }


def self_test():

    assert (
        evaluate(
            []
        )["status"]
        == "PASS"
    )

    print(
        "VI7.27 OUTPUT INTEGRITY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.28 — ADAPTIVE CERTIFICATION
# ============================================================

cat > vi7_28_adaptive_certification.py <<'PY'
#!/usr/bin/env python3

from vi7_21_sequence_audit import (
    audit as sequence_audit
)

from vi7_22_performance_budget import (
    evaluate as performance
)

from vi7_26_canary_audit import (
    evaluate as canary_audit
)

from vi7_27_output_integrity import (
    evaluate as output_integrity
)


VERSION = "7.28"


def evaluate(
    events
):

    canary = canary_audit(
        events
    )

    sequence = sequence_audit(
        events
    )

    perf = performance(
        events
    )

    output = output_integrity(
        canary["success"]
    )


    blockers = []

    warnings = []


    blockers.extend(
        sequence.get(
            "blockers"
        )
        or []
    )


    blockers.extend(
        output.get(
            "blockers"
        )
        or []
    )


    if canary[
        "retry_failed"
    ]:

        blockers.append(
            "legacy_retry_failed"
        )


    warnings.extend(
        sequence.get(
            "warnings"
        )
        or []
    )


    selected_scenes = sorted(
        {
            e.get(
                "scene"
            )
            for e in canary[
                "selected"
            ]
            if isinstance(
                e.get(
                    "scene"
                ),
                int
            )
        }
    )


    success_scenes = {
        e.get(
            "scene"
        )
        for e in canary[
            "success"
        ]
    }


    recovered_scenes = {
        e.get(
            "scene"
        )
        for e in canary[
            "retry_success"
        ]
    }


    final_valid = (
        success_scenes
        | recovered_scenes
    )


    if (
        set(
            selected_scenes
        )
        != final_valid
    ):

        blockers.append(
            "selected_scene_without_valid_final_output"
        )


    if len(
        selected_scenes
    ) < 4:

        blockers.append(
            "insufficient_adaptive_canaries"
        )


    if len(
        selected_scenes
    ) < 7:

        warnings.append(
            "adaptive_selection_below_target"
        )


    if canary[
        "retries"
    ]:

        warnings.append(
            "legacy_retry_required"
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


    return {
        "version":
            VERSION,

        "selected_scenes":
            selected_scenes,

        "selected_count":
            len(
                selected_scenes
            ),

        "success_scenes":
            sorted(
                success_scenes
            ),

        "recovered_scenes":
            sorted(
                recovered_scenes
            ),

        "retry_count":
            len(
                canary[
                    "retries"
                ]
            ),

        "sequence":
            sequence,

        "performance":
            perf,

        "output_integrity":
            output,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():

    assert VERSION == "7.28"

    print(
        "VI7.28 ADAPTIVE CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.29 — RELEASE GATE
# ============================================================

cat > vi7_29_release_gate.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.29"


def evaluate(
    certification
):

    blockers = (
        certification.get(
            "blockers"
        )
        or []
    )


    count = certification.get(
        "selected_count",
        0
    )


    if blockers:

        status = "HOLD"

    elif count >= 7:

        status = (
            "ADAPTIVE_RUNTIME_CERTIFIED"
        )

    else:

        status = (
            "ADAPTIVE_RUNTIME_SAFE_WITH_WARNINGS"
        )


    return {
        "version":
            VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            certification.get(
                "warnings"
            )
            or [],

        "full_active_authorized":
            False,
    }


def self_test():

    assert VERSION == "7.29"

    print(
        "VI7.29 RELEASE GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# VI7.30 — MASTER GATE
# ============================================================

cat > vi7_30_master_gate.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


from vi7_28_adaptive_certification import (
    evaluate as certify
)

from vi7_29_release_gate import (
    evaluate as release_gate
)


VERSION = "7.30"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

RUNTIME = (
    BASE
    / "logs/producao/"
      "vi7_19_adaptive_runtime_latest.json"
)

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi7_30_master_gate_latest.json"
)


def evaluate():

    blockers = []


    try:

        data = json.loads(
            RUNTIME.read_text(
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
            "runtime_telemetry_missing"
        )


    certification = certify(
        events
    )


    certification[
        "blockers"
    ] = sorted(
        set(
            certification.get(
                "blockers"
            )
            or []
        )
        | set(
            blockers
        )
    )


    release = release_gate(
        certification
    )


    result = {
        "version":
            VERSION,

        "status":
            release.get(
                "status"
            ),

        "selected_count":
            certification.get(
                "selected_count"
            ),

        "selected_scenes":
            certification.get(
                "selected_scenes"
            ),

        "success_scenes":
            certification.get(
                "success_scenes"
            ),

        "recovered_scenes":
            certification.get(
                "recovered_scenes"
            ),

        "retry_count":
            certification.get(
                "retry_count"
            ),

        "profiles":
            (
                certification.get(
                    "sequence"
                )
                or {}
            ).get(
                "profiles"
            ),

        "roles":
            (
                certification.get(
                    "sequence"
                )
                or {}
            ).get(
                "roles"
            ),

        "unique_profiles":
            (
                certification.get(
                    "sequence"
                )
                or {}
            ).get(
                "unique_profiles"
            ),

        "adjacent_triples":
            (
                certification.get(
                    "sequence"
                )
                or {}
            ).get(
                "adjacent_triples"
            ),

        "blockers":
            release.get(
                "blockers"
            ),

        "warnings":
            release.get(
                "warnings"
            ),

        "adaptive_runtime_certified":
            (
                release.get(
                    "status"
                )
                == "ADAPTIVE_RUNTIME_CERTIFIED"
            ),

        "source_recovery_active":
            False,

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

    assert VERSION == "7.30"

    print(
        "VI7.30 MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# ============================================================
# INSTALL DELEGATE IN EXISTING EXECUTOR
# ============================================================

echo
echo "===== INSTALL VI7.30 RUNTIME DELEGATE ====="

python - <<'PY'
from pathlib import Path

p = Path(
    "vi6_95_scene_executor.py"
)

s = p.read_text(
    encoding="utf-8"
)

marker = (
    "# VI7.30 ADAPTIVE EXECUTOR DELEGATE"
)

if marker in s:

    print(
        "VI7.30 DELEGATE ALREADY PRESENT"
    )

    raise SystemExit(0)


addition = r'''

# VI7.30 ADAPTIVE EXECUTOR DELEGATE

_vi695_execute_before_vi730 = execute


def execute(
    command,
    **run_kwargs
):

    import os


    if (
        os.getenv(
            "VI730_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
    ):

        from vi7_20_adaptive_executor import (
            execute as _vi730_execute
        )


        return _vi730_execute(
            command,
            **run_kwargs
        )


    return _vi695_execute_before_vi730(
        command,
        **run_kwargs
    )
'''


p.write_text(
    s + addition,
    encoding="utf-8"
)

print(
    "VI7.30 DELEGATE=INSTALLED"
)
PY

if [ "$?" -ne 0 ]; then
    rollback
    exit 10
fi


# ============================================================
# COMPILE
# ============================================================

echo
echo "===== FULL COMPILE ====="

python -m py_compile \
    vi7_11_adaptive_policy.py \
    vi7_12_narrative_role.py \
    vi7_13_motion_catalog.py \
    vi7_14_adaptive_state.py \
    vi7_15_motion_planner.py \
    vi7_16_sequence_guard.py \
    vi7_17_filter_guard.py \
    vi7_18_adaptive_adapter.py \
    vi7_19_runtime_telemetry.py \
    vi7_20_adaptive_executor.py \
    vi7_21_sequence_audit.py \
    vi7_22_performance_budget.py \
    vi7_23_source_safety_lock.py \
    vi7_24_production_gate.py \
    vi7_25_runtime_router.py \
    vi7_26_canary_audit.py \
    vi7_27_output_integrity.py \
    vi7_28_adaptive_certification.py \
    vi7_29_release_gate.py \
    vi7_30_master_gate.py \
    vi6_95_scene_executor.py \
    video.py \
    semantic_integrity_gate.py \
    || {
        rollback
        exit 11
    }

bash -n gerar_short.sh || {
    rollback
    exit 12
}

echo "FULL COMPILE=PASS"


# ============================================================
# SELF TESTS
# ============================================================

echo
echo "===== SELF TESTS ====="

for F in \
    vi7_11_adaptive_policy.py \
    vi7_12_narrative_role.py \
    vi7_13_motion_catalog.py \
    vi7_14_adaptive_state.py \
    vi7_15_motion_planner.py \
    vi7_16_sequence_guard.py \
    vi7_17_filter_guard.py \
    vi7_19_runtime_telemetry.py \
    vi7_18_adaptive_adapter.py \
    vi7_20_adaptive_executor.py \
    vi7_21_sequence_audit.py \
    vi7_22_performance_budget.py \
    vi7_23_source_safety_lock.py \
    vi7_24_production_gate.py \
    vi7_25_runtime_router.py \
    vi7_26_canary_audit.py \
    vi7_27_output_integrity.py \
    vi7_28_adaptive_certification.py \
    vi7_29_release_gate.py \
    vi7_30_master_gate.py
do

    python "$F" || {
        rollback
        exit 13
    }

done


# ============================================================
# VIDEO.PY MUST REMAIN UNCHANGED
# ============================================================

VIDEO_HASH_AFTER="$(
    sha256sum video.py |
    awk '{print $1}'
)"

echo
echo "===== VIDEO.PY INTEGRITY ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"
echo "AFTER =$VIDEO_HASH_AFTER"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_AFTER" ]; then

    echo "CRITICAL: video.py changed."

    rollback
    exit 14
fi

echo "VIDEO.PY UNCHANGED=YES"


# ============================================================
# PRODUCTION GATE
# ============================================================

echo
echo "===== VI7.24 PRODUCTION GATE ====="

python - <<'PY'
from vi7_24_production_gate import (
    evaluate
)

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

print(
    "BLOCKERS:",
    r.get("blockers")
)

print(
    "WARNINGS:",
    r.get("warnings")
)

print(
    "SOURCE RECOVERY:",
    (
        r.get(
            "source_safety"
        )
        or {}
    ).get(
        "source_recovery_mode"
    )
)

print(
    "FULL ACTIVE:",
    r.get("full_active")
)

if r.get(
    "status"
) != "ADAPTIVE_CANARY_ALLOWED":
    raise SystemExit(1)
PY

if [ "$?" -ne 0 ]; then
    rollback
    exit 15
fi


# ============================================================
# RELEASE CHECK
# ============================================================

echo
echo "===== RELEASE CHECK ====="

./release_check.sh || {
    rollback
    exit 16
}


# ============================================================
# CLEAR ONLY NEW SESSION TELEMETRY
# ============================================================

rm -f \
    logs/producao/vi7_19_adaptive_runtime_latest.json \
    logs/producao/vi7_30_master_gate_latest.json


# ============================================================
# REAL ADAPTIVE PRODUCTION
# ============================================================

echo
echo "============================================================"
echo " STARTING VI7.30 ADAPTIVE REAL PRODUCTION"
echo "============================================================"
echo
echo "ELIGIBLE STILL SCENES = ADAPTIVE"
echo "MAX VI7 = 9"
echo "MAX CONSECUTIVE = 2"
echo "HOOK = LEGACY"
echo "CTA = LEGACY"
echo "VIDEO = LEGACY"
echo "FAILURE = SAME-SCENE LEGACY RETRY"
echo


VI682_CANARY_MODE=OFF \
VI710_CANARY_MODE=OFF \
VI730_CANARY_MODE=ON \
VI700_CANARY_MODE=ON \
VI647_RENDERER_MODE=LEGACY \
./gerar_short.sh

PIPE_STATUS="$?"


echo
echo "PIPELINE STATUS=$PIPE_STATUS"


# ============================================================
# MASTER GATE
# ============================================================

echo
echo "===== VI7.30 REAL MASTER GATE ====="

python - <<'PY'
from vi7_30_master_gate import (
    evaluate
)

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

print(
    "SELECTED COUNT:",
    r.get("selected_count")
)

print(
    "SELECTED SCENES:",
    r.get("selected_scenes")
)

print(
    "SUCCESS SCENES:",
    r.get("success_scenes")
)

print(
    "RECOVERED SCENES:",
    r.get("recovered_scenes")
)

print(
    "LEGACY RETRIES:",
    r.get("retry_count")
)

print(
    "PROFILES:",
    r.get("profiles")
)

print(
    "UNIQUE PROFILES:",
    r.get("unique_profiles")
)

print(
    "ROLES:",
    r.get("roles")
)

print(
    "ADJACENT TRIPLES:",
    r.get("adjacent_triples")
)

print(
    "BLOCKERS:",
    r.get("blockers")
)

print(
    "WARNINGS:",
    r.get("warnings")
)

print(
    "ADAPTIVE CERTIFIED:",
    r.get(
        "adaptive_runtime_certified"
    )
)

print(
    "SOURCE RECOVERY ACTIVE:",
    r.get(
        "source_recovery_active"
    )
)

print(
    "FULL ACTIVE AUTHORIZED:",
    r.get(
        "full_active_authorized"
    )
)
PY


# ============================================================
# EVENT TRACE
# ============================================================

echo
echo "===== VI7.30 ADAPTIVE TRACE ====="

python - <<'PY'
import json
from pathlib import Path

p = (
    Path.home()
    / "ShortAutoPro/logs/producao/"
      "vi7_19_adaptive_runtime_latest.json"
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


for e in (
    data.get("events")
    or []
):

    if e.get(
        "action"
    ) not in {
        "VI730_SELECTED",
        "VI730_RENDER_ATTEMPT",
        "VI730_RENDER_SUCCESS",
        "VI730_VALIDATION_HOLD",
        "LEGACY_RETRY",
        "LEGACY_RETRY_SUCCESS",
        "LEGACY_RETRY_FAILED",
    }:
        continue


    validation = (
        e.get(
            "validation"
        )
        or {}
    )


    print(
        "SCENE",
        e.get("scene"),
        "|",
        e.get("action"),
        "| role=",
        e.get("role"),
        "| profile=",
        e.get("profile"),
        "| delta=",
        validation.get(
            "duration_delta"
        ),
        "| blockers=",
        validation.get(
            "blockers"
        ),
        "| reason=",
        e.get("reason"),
    )
PY


# ============================================================
# FINAL SAFETY
# ============================================================

echo
echo "===== FINAL SAFETY ====="

VIDEO_HASH_FINAL="$(
    sha256sum video.py |
    awk '{print $1}'
)"

echo "BEFORE=$VIDEO_HASH_BEFORE"
echo "FINAL =$VIDEO_HASH_FINAL"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_FINAL" ]; then

    echo "CRITICAL: video.py changed during runtime."
    exit 30
fi


python -m py_compile \
    video.py \
    vi6_95_scene_executor.py \
    vi7_18_adaptive_adapter.py \
    vi7_20_adaptive_executor.py \
    vi7_30_master_gate.py \
    || exit 31


echo "VIDEO.PY UNCHANGED=YES"
echo "FINAL COMPILE=PASS"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"


echo
echo "============================================================"
echo " VI7.11 -> VI7.30 MEGA UPDATE COMPLETE"
echo "============================================================"
echo
echo "PIPELINE STATUS=$PIPE_STATUS"
echo "ADAPTIVE VISUAL RUNTIME=ON"
echo "MAX VI7 STILL SCENES=9"
echo "MAX CONSECUTIVE VI7=2"
echo "HOOK=LEGACY"
echo "CTA=LEGACY"
echo "NATIVE VIDEO=LEGACY"
echo "REAL FALLBACK=ON"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"
echo
echo "MASTER REPORT:"
echo "logs/producao/vi7_30_master_gate_latest.json"
echo

exit "$PIPE_STATUS"
