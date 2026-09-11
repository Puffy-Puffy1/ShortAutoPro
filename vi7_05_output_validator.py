#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


VERSION = "7.05"


def _fps(value):

    if not value:
        return None


    try:

        a, b = str(
            value
        ).split(
            "/",
            1
        )


        return (
            float(a)
            / float(b)
        )


    except Exception:

        try:
            return float(value)

        except Exception:
            return None


def validate(
    path,
    expected_duration
):

    path = Path(
        path
    )


    blockers = []


    if not path.exists():

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "blockers":
                ["output_missing"],
        }


    if path.stat().st_size <= 0:

        blockers.append(
            "output_empty"
        )


    try:

        raw = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",

                "-select_streams",
                "v:0",

                "-show_entries",
                (
                    "stream="
                    "width,height,"
                    "avg_frame_rate,"
                    "pix_fmt,"
                    "codec_name:"
                    "format=duration,size"
                ),

                "-of",
                "json",

                str(path),
            ],
            text=True
        )


        data = json.loads(
            raw
        )


    except Exception as exc:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "blockers":
                [
                    "ffprobe_failure:"
                    + type(exc).__name__
                ],
        }


    stream = (
        data.get("streams")
        or [{}]
    )[0]


    fmt = (
        data.get("format")
        or {}
    )


    width = stream.get(
        "width"
    )


    height = stream.get(
        "height"
    )


    if (
        width != 1080
        or height != 1920
    ):

        blockers.append(
            "resolution_invalid"
        )


    fps = _fps(
        stream.get(
            "avg_frame_rate"
        )
    )


    if (
        fps is None
        or abs(
            fps - 30.0
        ) > .05
    ):

        blockers.append(
            "fps_invalid"
        )


    if stream.get(
        "pix_fmt"
    ) not in {
        "yuv420p",
        "yuvj420p",
    }:

        blockers.append(
            "pixel_format_invalid"
        )


    if stream.get(
        "codec_name"
    ) != "h264":

        blockers.append(
            "codec_invalid"
        )


    try:

        duration = float(
            fmt.get(
                "duration"
            )
        )

    except Exception:

        duration = None


    try:

        expected = float(
            expected_duration
        )

    except Exception:

        expected = None


    duration_delta = None


    if (
        duration is None
        or duration <= 0
    ):

        blockers.append(
            "duration_invalid"
        )


    elif expected is not None:

        duration_delta = abs(
            duration
            - expected
        )


        if duration_delta > .15:

            blockers.append(
                "duration_delta_too_high"
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

        "width":
            width,

        "height":
            height,

        "fps":
            fps,

        "duration":
            duration,

        "expected_duration":
            expected,

        "duration_delta":
            (
                round(
                    duration_delta,
                    4
                )
                if duration_delta is not None
                else None
            ),

        "codec":
            stream.get(
                "codec_name"
            ),

        "pix_fmt":
            stream.get(
                "pix_fmt"
            ),

        "bytes":
            path.stat().st_size,

        "blockers":
            blockers,
    }


def self_test():

    result = validate(
        "/file/that/does/not/exist.mp4",
        3.0
    )

    assert (
        result["status"]
        == "HOLD"
    )

    print(
        "VI7.05 OUTPUT VALIDATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
