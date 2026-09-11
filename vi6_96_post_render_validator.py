#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


VERSION = "6.96"


def validate(path):

    path = Path(path)


    if not path.exists():

        return {
            "version": VERSION,
            "status": "HOLD",
            "reason": "output_missing",
        }


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
                    "avg_frame_rate:"
                    "format=duration"
                ),
                "-of",
                "json",
                str(path),
            ],
            text=True
        )


        data = json.loads(raw)


        stream = (
            data.get("streams")
            or [{}]
        )[0]


        fmt = (
            data.get("format")
            or {}
        )


    except Exception as exc:

        return {
            "version": VERSION,

            "status": "HOLD",

            "reason":
                "ffprobe:"
                + type(exc).__name__,
        }


    blockers = []


    if (
        stream.get("width") != 1080
        or stream.get("height") != 1920
    ):

        blockers.append(
            "resolution_invalid"
        )


    try:
        duration = float(
            fmt.get("duration")
        )

    except Exception:
        duration = 0


    if duration <= 0:

        blockers.append(
            "duration_invalid"
        )


    return {
        "version": VERSION,

        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "width":
            stream.get("width"),

        "height":
            stream.get("height"),

        "duration":
            duration,

        "fps":
            stream.get(
                "avg_frame_rate"
            ),

        "blockers":
            blockers,
    }


def self_test():

    assert (
        validate(
            "/not/a/file.mp4"
        )["status"]
        == "HOLD"
    )

    print(
        "VI6.96 POST-RENDER VALIDATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
