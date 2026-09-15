#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

VIDEO = (
    BASE
    / "videos/canary/vi1330/"
    "2026-09-01_1433_VI1330_CANARY.mp4"
)

DISCOVERY = json.loads(
    (
        BASE
        / "temp/vi1310/discovery.json"
    ).read_text(
        encoding="utf-8"
    )
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1330_08_technical_audit_latest.json"
)


def main():
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(
                VIDEO
            ),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


    if result.returncode != 0:

        raise SystemExit(
            "VI1330 FFPROBE FAILED"
        )


    data = json.loads(
        result.stdout
    )


    streams = data.get(
        "streams"
    ) or []


    video = next(
        (
            stream

            for stream in streams

            if stream.get(
                "codec_type"
            )
            ==
            "video"
        ),
        None,
    )


    audio = next(
        (
            stream

            for stream in streams

            if stream.get(
                "codec_type"
            )
            ==
            "audio"
        ),
        None,
    )


    duration = float(
        (
            data.get(
                "format"
            )
            or {}
        ).get(
            "duration"
        )
        or 0
    )


    source_duration = float(
        DISCOVERY[
            "audio_duration"
        ]
    )


    width = int(
        (
            video
            or {}
        ).get(
            "width"
        )
        or 0
    )


    height = int(
        (
            video
            or {}
        ).get(
            "height"
        )
        or 0
    )


    checks = {
        "video_exists":
            VIDEO.exists(),

        "width_1080":
            width == 1080,

        "height_1920":
            height == 1920,

        "video_stream":
            video is not None,

        "audio_stream":
            audio is not None,

        "duration_matches_audio":
            abs(
                duration
                -
                source_duration
            )
            <= 0.65,

        "h264_video":
            (
                video
                or {}
            ).get(
                "codec_name"
            )
            ==
            "h264",

        "aac_audio":
            (
                audio
                or {}
            ).get(
                "codec_name"
            )
            ==
            "aac",

        "file_size_good":
            VIDEO.stat().st_size
            >
            3000000,
    }


    failed = [
        key

        for key, value in checks.items()

        if value is not True
    ]


    status = (
        "VI1330_TECHNICAL_RENDER_CERTIFIED"

        if not failed

        else
        "VI1330_TECHNICAL_RENDER_HOLD"
    )


    output = {
        "status":
            status,

        "width":
            width,

        "height":
            height,

        "duration":
            duration,

        "audio_duration":
            source_duration,

        "video_codec":
            (
                video
                or {}
            ).get(
                "codec_name"
            ),

        "audio_codec":
            (
                audio
                or {}
            ).get(
                "codec_name"
            ),

        "bytes":
            VIDEO.stat().st_size,

        "checks":
            checks,

        "failed":
            failed,
    }


    OUT.write_text(
        json.dumps(
            {
                "gate":
                    output
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print()
    print(
        "=============================================="
    )
    print(
        " VI1330 TECHNICAL AUDIT"
    )
    print(
        "=============================================="
    )

    print(
        "SIZE:",
        width,
        "x",
        height
    )
    print(
        "DURATION:",
        duration
    )
    print(
        "AUDIO:",
        source_duration
    )
    print(
        "FAILED:",
        failed
    )
    print(
        "STATUS:",
        status
    )


    if failed:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
