#!/usr/bin/env python3

import re

from vi1400_01_common import (
    TMP,
    ffprobe,
    load_json,
    run,
    save_json,
)


def run_temporal():
    video = load_json(
        TMP
        / "artifacts.json"
    )[
        "final_video"
    ]


    info = ffprobe(
        video
    )


    streams = info.get(
        "streams",
        []
    )


    video_stream = next(
        (
            stream

            for stream in streams

            if stream.get(
                "codec_type"
            )
            ==
            "video"
        ),
        {},
    )


    audio_stream = next(
        (
            stream

            for stream in streams

            if stream.get(
                "codec_type"
            )
            ==
            "audio"
        ),
        {},
    )


    rc, stdout, stderr = run([
        "ffmpeg",
        "-hide_banner",
        "-nostats",

        "-i",
        video,

        "-vf",
        (
            "blackdetect="
            "d=0.45:"
            "pix_th=0.10,"
            "freezedetect="
            "n=-50dB:"
            "d=1.5"
        ),

        "-an",

        "-f",
        "null",
        "-",
    ],
        timeout=120,
    )


    black_segments = len(
        re.findall(
            r"black_start:",
            stderr
        )
    )


    freeze_segments = len(
        re.findall(
            r"freeze_start:",
            stderr
        )
    )


    blockers = []

    warnings = []


    if (
        int(
            video_stream.get(
                "width"
            )
            or 0
        )
        != 1080

        or

        int(
            video_stream.get(
                "height"
            )
            or 0
        )
        != 1920
    ):

        blockers.append(
            "resolution_not_1080x1920"
        )


    if not audio_stream:

        blockers.append(
            "audio_stream_missing"
        )


    if black_segments > 1:

        warnings.append(
            "multiple_black_segments_detected"
        )


    if freeze_segments > 4:

        warnings.append(
            "many_freeze_segments_detected"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "black_segments":
            black_segments,

        "freeze_segments":
            freeze_segments,

        "video_stream":
            video_stream,

        "audio_stream":
            audio_stream,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


    save_json(
        TMP
        / "temporal_qa.json",
        report
    )


    return report


if __name__ == "__main__":

    report = (
        run_temporal()
    )


    print(
        "VI1400 TEMPORAL QA=",
        report[
            "status"
        ]
    )

    print(
        "BLACK=",
        report[
            "black_segments"
        ],
        "FREEZE=",
        report[
            "freeze_segments"
        ]
    )

    print(
        "WARNINGS=",
        report[
            "warnings"
        ]
    )

    print(
        "BLOCKERS=",
        report[
            "blockers"
        ]
    )
