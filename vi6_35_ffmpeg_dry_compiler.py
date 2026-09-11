#!/usr/bin/env python3

import math


VERSION = "6.35"

FPS = 30

WIDTH = 1080
HEIGHT = 1920


def _f(v, default=0.0):

    try:
        return float(v)
    except Exception:
        return float(default)


def _safe_frames(seconds):

    seconds = max(
        .25,
        _f(
            seconds,
            4.0
        )
    )


    return max(
        1,
        int(
            round(
                seconds
                * FPS
            )
        )
    )


def _num(v):

    return (
        f"{float(v):.6f}"
        .rstrip("0")
        .rstrip(".")
    )


def compile_plan(
    contract,
    duration
):

    media = str(
        contract.get(
            "media_type",
            ""
        )
    ).upper()


    seconds = _f(
        duration.get(
            "seconds",
            4.0
        ),
        4.0
    )


    frames = _safe_frames(
        seconds
    )


    base = {

        "version":
            VERSION,

        "mode":
            "DRY_RUN",

        "executed":
            False,

        "fps":
            FPS,

        "width":
            WIDTH,

        "height":
            HEIGHT,

        "duration_seconds":
            round(
                seconds,
                3
            ),

        "frames":
            frames,

        "argv":
            None,

        "vf":
            None,
    }


    # =================================
    # NATIVE VIDEO
    # =================================

    if media == "VIDEO":

        base[
            "renderer_mode"
        ] = "NATIVE_VIDEO_PRESERVE"


        base[
            "reason"
        ] = "no_synthetic_motion"


        return base


    # =================================
    # NO MEDIA
    # =================================

    if media != "STILL":

        base[
            "renderer_mode"
        ] = "NO_RENDER_PLAN"


        base[
            "reason"
        ] = "unsupported_media_type"


        return base


    ken = (
        contract.get(
            "ken_burns"
        )
        or {}
    )


    if not ken.get(
        "enabled"
    ):

        base[
            "renderer_mode"
        ] = "STATIC_STILL"


        base[
            "vf"
        ] = (
            "scale="
            f"{WIDTH}:{HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"fps={FPS}"
        )


        base[
            "argv"
        ] = [
            "ffmpeg",
            "-loop",
            "1",
            "-i",
            "{INPUT}",
            "-vf",
            base[
                "vf"
            ],
            "-t",
            "{DURATION}",
            "-an",
            "{OUTPUT}",
        ]


        return base


    z1 = _f(
        ken.get(
            "zoom_start",
            1.0
        ),
        1.0
    )


    z2 = _f(
        ken.get(
            "zoom_end",
            1.0
        ),
        1.0
    )


    x1 = _f(
        ken.get(
            "start_x",
            .5
        ),
        .5
    )


    x2 = _f(
        ken.get(
            "end_x",
            .5
        ),
        .5
    )


    y1 = _f(
        ken.get(
            "start_y",
            .5
        ),
        .5
    )


    y2 = _f(
        ken.get(
            "end_y",
            .5
        ),
        .5
    )


    denominator = max(
        1,
        frames - 1
    )


    progress = (
        f"(on/{denominator})"
    )


    zoom_expr = (
        _num(z1)
        + "+"
        + _num(
            z2 - z1
        )
        + "*"
        + progress
    )


    x_progress = (
        _num(x1)
        + "+"
        + _num(
            x2 - x1
        )
        + "*"
        + progress
    )


    y_progress = (
        _num(y1)
        + "+"
        + _num(
            y2 - y1
        )
        + "*"
        + progress
    )


    # Coordenadas normalizadas são
    # transformadas na área disponível
    # depois do zoom.
    x_expr = (
        "(iw-iw/zoom)*("
        + x_progress
        + ")"
    )


    y_expr = (
        "(ih-ih/zoom)*("
        + y_progress
        + ")"
    )


    vf = (
        "scale="
        f"{WIDTH}:{HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        "zoompan="
        "z='"
        + zoom_expr
        + "':"
        "x='"
        + x_expr
        + "':"
        "y='"
        + y_expr
        + "':"
        f"d={frames}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS},"
        "format=yuv420p"
    )


    base[
        "renderer_mode"
    ] = "KEN_BURNS_STILL"


    base[
        "vf"
    ] = vf


    base[
        "argv"
    ] = [
        "ffmpeg",
        "-loop",
        "1",
        "-i",
        "{INPUT}",
        "-vf",
        vf,
        "-t",
        "{DURATION}",
        "-an",
        "{OUTPUT}",
    ]


    base[
        "zoom"
    ] = {
        "start":
            z1,

        "end":
            z2,
    }


    base[
        "pan"
    ] = {
        "start_x":
            x1,

        "start_y":
            y1,

        "end_x":
            x2,

        "end_y":
            y2,
    }


    return base


def validate_plan(plan):

    errors = []


    if (
        plan.get(
            "mode"
        )
        != "DRY_RUN"
    ):

        errors.append(
            "not_dry_run"
        )


    if (
        plan.get(
            "executed"
        )
        is not False
    ):

        errors.append(
            "execution_flag"
        )


    mode = (
        plan.get(
            "renderer_mode"
        )
    )


    if mode == "KEN_BURNS_STILL":

        vf = str(
            plan.get(
                "vf",
                ""
            )
        )


        for required in (
            "scale=",
            "crop=",
            "zoompan=",
            "format=yuv420p",
        ):

            if required not in vf:

                errors.append(
                    "missing_filter:"
                    + required
                )


        argv = (
            plan.get(
                "argv"
            )
            or []
        )


        if not argv:

            errors.append(
                "missing_argv"
            )


        if (
            "{INPUT}"
            not in argv
        ):

            errors.append(
                "missing_input_placeholder"
            )


        if (
            "{OUTPUT}"
            not in argv
        ):

            errors.append(
                "missing_output_placeholder"
            )


        if (
            "{DURATION}"
            not in argv
        ):

            errors.append(
                "missing_duration_placeholder"
            )


    return (
        len(errors) == 0,
        errors
    )


def self_test():

    plan = compile_plan(
        {
            "media_type":
                "STILL",

            "ken_burns":
                {
                    "enabled":
                        True,

                    "zoom_start":
                        1.0,

                    "zoom_end":
                        1.04,

                    "start_x":
                        .45,

                    "start_y":
                        .50,

                    "end_x":
                        .55,

                    "end_y":
                        .50,
                },
        },
        {
            "seconds":
                4.0
        }
    )


    assert (
        plan[
            "executed"
        ]
        is False
    )


    assert (
        plan[
            "frames"
        ]
        == 120
    )


    assert (
        "zoompan="
        in plan[
            "vf"
        ]
    )


    ok, errors = validate_plan(
        plan
    )


    assert ok is True
    assert errors == []


    video = compile_plan(
        {
            "media_type":
                "VIDEO"
        },
        {
            "seconds":
                5
        }
    )


    assert (
        video[
            "argv"
        ]
        is None
    )


    assert (
        video[
            "renderer_mode"
        ]
        == "NATIVE_VIDEO_PRESERVE"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.35 DRY COMPILER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Argument Vector Compilation"
    )
    print(
        "OK Zoompan Expression"
    )
    print(
        "OK 1080x1920"
    )
    print(
        "OK 30 FPS Frame Budget"
    )
    print(
        "OK Native Video No-Op"
    )
    print(
        "OK FFmpeg Execution = ZERO"
    )
    print()


if __name__ == "__main__":
    self_test()
