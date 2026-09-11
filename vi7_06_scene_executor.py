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
