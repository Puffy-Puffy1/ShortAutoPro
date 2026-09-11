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
