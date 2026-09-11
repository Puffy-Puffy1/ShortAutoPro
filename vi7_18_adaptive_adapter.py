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
