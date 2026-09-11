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
