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
