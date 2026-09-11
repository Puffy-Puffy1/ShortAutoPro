#!/usr/bin/env python3

import math


VERSION = "6.61.1"


PROFILES = {

    "HOOK_PUSH": {
        "zoom_total": 0.060,
        "direction": "CENTER",
    },

    "DOCUMENTARY_DRIFT": {
        "zoom_total": 0.035,
        "direction": "CENTER",
    },

    "SLOW_PUSH": {
        "zoom_total": 0.045,
        "direction": "CENTER",
    },

    "HORIZONTAL_DISCOVERY": {
        "zoom_total": 0.035,
        "direction": "LEFT_TO_RIGHT",
    },

    "REVERSE_DRIFT": {
        "zoom_total": 0.035,
        "direction": "RIGHT_TO_LEFT",
    },

    "DETAIL_PUSH": {
        "zoom_total": 0.055,
        "direction": "CENTER",
    },

    "MICRO_MOTION": {
        "zoom_total": 0.020,
        "direction": "CENTER",
    },

    "CLIMAX_PUSH": {
        "zoom_total": 0.055,
        "direction": "CENTER",
    },

    "CLIMAX_PAN": {
        "zoom_total": 0.045,
        "direction": "LEFT_TO_RIGHT",
    },

    "CLIMAX_LOCK": {
        "zoom_total": 0.025,
        "direction": "CENTER",
    },

    "CTA_SETTLE": {
        "zoom_total": 0.020,
        "direction": "CENTER",
    },
}


def compile_filter(
    profile,
    duration_seconds,
    fps=30.0
):

    blockers = []
    warnings = []


    try:
        duration = float(
            duration_seconds
        )
    except Exception:
        duration = None


    try:
        fps = float(fps)
    except Exception:
        fps = None


    if (
        duration is None
        or duration <= 0
    ):
        blockers.append(
            "duration_invalid"
        )


    if (
        fps is None
        or fps <= 0
    ):
        blockers.append(
            "fps_invalid"
        )


    spec = PROFILES.get(
        profile
    )


    if spec is None:
        blockers.append(
            "unknown_motion_profile"
        )


    if blockers:

        return {
            "version": VERSION,
            "status": "HOLD",
            "profile": profile,
            "vf": None,
            "frames": None,
            "fps": fps,
            "blockers": blockers,
            "warnings": warnings,
        }


    frames = max(
        1,
        int(
            math.ceil(
                duration * fps
            )
        )
    )


    zoom_total = float(
        spec["zoom_total"]
    )


    zoom_step = (
        zoom_total
        / max(
            frames - 1,
            1
        )
    )


    zoom_end = (
        1.0
        + zoom_total
    )


    zoom_expr = (
        "if(eq(on,1),"
        "1.000000,"
        f"min(zoom+{zoom_step:.8f},"
        f"{zoom_end:.6f}))"
    )


    direction = spec[
        "direction"
    ]


    if direction == "LEFT_TO_RIGHT":

        x_expr = (
            "(iw-iw/zoom)"
            "*on/"
            f"{max(frames - 1, 1)}"
        )

        y_expr = (
            "(ih-ih/zoom)/2"
        )


    elif direction == "RIGHT_TO_LEFT":

        x_expr = (
            "(iw-iw/zoom)"
            "*(1-on/"
            f"{max(frames - 1, 1)})"
        )

        y_expr = (
            "(ih-ih/zoom)/2"
        )


    else:

        x_expr = (
            "(iw-iw/zoom)/2"
        )

        y_expr = (
            "(ih-ih/zoom)/2"
        )


    vf = (
        "scale="
        "1200:2133:"
        "force_original_aspect_ratio="
        "increase,"
        "crop=1200:2133,"
        "zoompan="
        f"z='{zoom_expr}':"
        f"x='{x_expr}':"
        f"y='{y_expr}':"
        f"d={frames}:"
        "s=1080x1920:"
        f"fps={fps:g},"
        "setsar=1,"
        "format=yuv420p"
    )


    return {
        "version": VERSION,

        "status": "COMPILED",

        "profile": profile,

        "direction": direction,

        "duration_seconds":
            duration,

        "fps":
            fps,

        "frames":
            frames,

        "zoom_total":
            zoom_total,

        "zoom_step":
            round(
                zoom_step,
                8
            ),

        "vf":
            vf,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "filter_applied":
            False,
    }


def self_test():

    for profile in PROFILES:

        result = compile_filter(
            profile,
            3.4,
            30
        )

        assert (
            result["status"]
            == "COMPILED"
        )

        assert (
            "zoompan="
            in result["vf"]
        )

        assert (
            "format=yuv420p"
            in result["vf"]
        )

        assert (
            result[
                "filter_applied"
            ]
            is False
        )


    assert (
        compile_filter(
            "SLOW_PUSH",
            3.4,
            30
        )["frames"]
        == 102
    )


    print(
        "VI6.61.1 MOTION FILTER COMPILER=PASS"
    )


if __name__ == "__main__":
    self_test()
