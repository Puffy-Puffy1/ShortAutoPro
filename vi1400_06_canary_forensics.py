#!/usr/bin/env python3

import hashlib
import json
import subprocess

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

VIDEO = (
    BASE
    / "temp/vi1400/canary/"
    "VI1400_visual_canary.mp4"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1400_06_canary_forensics_latest.json"
)


def sha256_file(
    path,
):
    sha = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha.update(
                chunk
            )

    return sha.hexdigest()


def main():
    if not VIDEO.exists():

        raise SystemExit(
            "CANARY_MISSING"
        )

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(VIDEO),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        raise SystemExit(
            result.stderr
        )

    probe = json.loads(
        result.stdout
    )

    video_streams = [
        stream

        for stream in (
            probe.get(
                "streams"
            )
            or []
        )

        if (
            stream.get(
                "codec_type"
            )
            ==
            "video"
        )
    ]

    audio_streams = [
        stream

        for stream in (
            probe.get(
                "streams"
            )
            or []
        )

        if (
            stream.get(
                "codec_type"
            )
            ==
            "audio"
        )
    ]

    stream = (
        video_streams[0]
        if video_streams
        else {}
    )

    try:
        duration = float(
            (
                probe.get(
                    "format"
                )
                or {}
            ).get(
                "duration"
            )
        )

    except Exception:
        duration = 0.0

    checks = {
        "video_stream_present":
            len(
                video_streams
            )
            == 1,

        "width_1080":
            stream.get(
                "width"
            )
            == 1080,

        "height_1920":
            stream.get(
                "height"
            )
            == 1920,

        "codec_h264":
            stream.get(
                "codec_name"
            )
            ==
            "h264",

        "fps_30":
            stream.get(
                "r_frame_rate"
            )
            in {
                "30/1",
                "60/2",
            },

        "duration_valid":
            23.0
            <= duration
            <= 25.5,

        "audio_absent":
            len(
                audio_streams
            )
            == 0,

        "file_nontrivial":
            VIDEO.stat().st_size
            > 100000,
    }

    failed = [
        key

        for key, value
        in checks.items()

        if value is not True
    ]

    certified = (
        not failed
    )

    status = (
        "VI1400_VISUAL_CANARY_FORENSICS_CERTIFIED"
        if certified
        else
        "VI1400_VISUAL_CANARY_FORENSICS_HOLD"
    )

    report = {
        "version":
            "1400.00",

        "status":
            status,

        "path":
            str(
                VIDEO.resolve()
            ),

        "bytes":
            VIDEO.stat().st_size,

        "sha256":
            sha256_file(
                VIDEO
            ),

        "duration":
            duration,

        "width":
            stream.get(
                "width"
            ),

        "height":
            stream.get(
                "height"
            ),

        "fps":
            stream.get(
                "r_frame_rate"
            ),

        "codec":
            stream.get(
                "codec_name"
            ),

        "audio_streams":
            len(
                audio_streams
            ),

        "checks":
            checks,

        "failed":
            failed,
    }

    OUT.write_text(
        json.dumps(
            {
                "gate":
                    report
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
        " VI1400 CANARY FORENSICS"
    )
    print(
        "=============================================="
    )

    print(
        "RESOLUTION:",
        stream.get(
            "width"
        ),
        "x",
        stream.get(
            "height"
        )
    )

    print(
        "FPS:",
        stream.get(
            "r_frame_rate"
        )
    )

    print(
        "DURATION:",
        duration
    )

    print(
        "CODEC:",
        stream.get(
            "codec_name"
        )
    )

    print(
        "AUDIO STREAMS:",
        len(
            audio_streams
        )
    )

    print(
        "SHA256:",
        report[
            "sha256"
        ]
    )

    print(
        "FAILED:",
        failed
    )

    print(
        "STATUS:",
        status
    )

    if not certified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
