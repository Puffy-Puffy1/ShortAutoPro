#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


VERSION = "6.75"


def probe(path):

    path = Path(
        path
    )


    if not path.exists():

        return {
            "status": "MISSING",
            "path": str(path),
        }


    command = [
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
            "r_frame_rate,"
            "pix_fmt,"
            "codec_name,"
            "nb_frames:"
            "format=duration,size"
        ),

        "-of",
        "json",

        str(path),
    ]


    try:

        raw = subprocess.check_output(
            command,
            text=True
        )


        data = json.loads(
            raw
        )


    except Exception as exc:

        return {
            "status": "HOLD",
            "path": str(path),
            "error":
                type(exc).__name__,
        }


    stream = (
        data.get("streams")
        or [{}]
    )[0]


    fmt = (
        data.get("format")
        or {}
    )


    return {
        "status": "PASS",

        "path": str(path),

        "width":
            stream.get("width"),

        "height":
            stream.get("height"),

        "fps":
            (
                stream.get(
                    "avg_frame_rate"
                )
                or stream.get(
                    "r_frame_rate"
                )
            ),

        "pix_fmt":
            stream.get("pix_fmt"),

        "codec":
            stream.get("codec_name"),

        "nb_frames":
            stream.get("nb_frames"),

        "duration":
            fmt.get("duration"),

        "size":
            fmt.get("size"),
    }


def self_test():

    assert probe(
        "/definitely/not/here.mp4"
    )["status"] == "MISSING"


    print(
        "VI6.75 TWIN PROBE=PASS"
    )


if __name__ == "__main__":
    self_test()
