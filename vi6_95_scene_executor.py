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
