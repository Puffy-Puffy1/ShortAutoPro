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
