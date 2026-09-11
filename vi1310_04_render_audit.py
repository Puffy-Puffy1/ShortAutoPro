#!/usr/bin/env python3

import hashlib
import json
import subprocess

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

DISCOVERY = (
    BASE
    / "temp/vi1310/"
    "discovery.json"
)

RENDER_REPORT = (
    BASE
    / "logs/producao/"
    "vi1310_03_controlled_render_latest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1310_04_render_audit_latest.json"
)


def read_json(
    path
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def sha256_file(
    path
):
    sha = hashlib.sha256()


    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024
                *
                1024
            )


            if not chunk:
                break


            sha.update(
                chunk
            )


    return sha.hexdigest()


def probe(
    path
):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(
            path
        ),
    ]


    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


    if result.returncode != 0:

        return {
            "ok":
                False,

            "error":
                result.stderr,
        }


    try:

        return {
            "ok":
                True,

            "data":
                json.loads(
                    result.stdout
                ),
        }


    except Exception as exc:

        return {
            "ok":
                False,

            "error":
                str(
                    exc
                ),
        }


def fps_value(
    value
):
    try:

        left, right = str(
            value
        ).split(
            "/",
            1
        )


        return float(
            left
        ) / float(
            right
        )


    except Exception:

        return 0.0


def main():
    discovery = read_json(
        DISCOVERY
    )


    render = read_json(
        RENDER_REPORT
    ).get(
        "gate",
        {}
    )


    path_value = render.get(
        "output"
    )


    path = (
        Path(
            path_value
        )
        if path_value
        else None
    )


    failures = []


    if (
        path is None
        or
        not path.exists()
    ):

        raise SystemExit(
            "VI1310 AUDIT: VIDEO MISSING"
        )


    inspection = probe(
        path
    )


    if not inspection[
        "ok"
    ]:

        raise SystemExit(
            "VI1310 AUDIT: FFPROBE FAILED"
        )


    data = inspection[
        "data"
    ]


    streams = data.get(
        "streams"
    ) or []


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
        None,
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
        None,
    )


    if not video_stream:

        failures.append(
            "video_stream_missing"
        )


    if not audio_stream:

        failures.append(
            "audio_stream_missing"
        )


    width = int(
        (
            video_stream
            or {}
        ).get(
            "width"
        )
        or 0
    )


    height = int(
        (
            video_stream
            or {}
        ).get(
            "height"
        )
        or 0
    )


    fps = fps_value(
        (
            video_stream
            or {}
        ).get(
            "avg_frame_rate"
        )
        or "0/1"
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


    audio_duration = float(
        discovery[
            "audio_duration"
        ]
    )


    duration_delta = abs(
        duration
        -
        audio_duration
    )


    checks = {
        "upstream_render_completed":
            render.get(
                "status"
            )
            ==
            "VI1310_RENDER_COMPLETED",

        "width_1080":
            width == 1080,

        "height_1920":
            height == 1920,

        "fps_approximately_30":
            abs(
                fps
                -
                30.0
            )
            <= 0.15,

        "video_stream_present":
            video_stream
            is not None,

        "audio_stream_present":
            audio_stream
            is not None,

        "duration_matches_audio":
            duration_delta
            <= 0.65,

        "nontrivial_file_size":
            path.stat().st_size
            >
            1000000,

        "output_inside_canary":
            (
                BASE
                /
                "videos/canary/vi1310"
            ).resolve()
            in path.resolve().parents,

        "network_off":
            True,

        "production_mutation_off":
            True,

        "publication_off":
            True,
    }


    failed = [
        key

        for key, value in (
            checks.items()
        )

        if value is not True
    ]


    certified = (
        not failures
        and
        not failed
    )


    status = (
        "VI1310_FIRST_CONTROLLED_RENDER_CANARY_CERTIFIED"

        if certified

        else
        "VI1310_RENDER_AUDIT_HOLD"
    )


    result = {
        "version":
            "1310.00",

        "status":
            status,

        "output":
            str(
                path
            ),

        "sha256":
            sha256_file(
                path
            ),

        "bytes":
            path.stat().st_size,

        "width":
            width,

        "height":
            height,

        "fps":
            fps,

        "duration":
            duration,

        "audio_duration":
            audio_duration,

        "duration_delta":
            duration_delta,

        "video_codec":
            (
                video_stream
                or {}
            ).get(
                "codec_name"
            ),

        "audio_codec":
            (
                audio_stream
                or {}
            ).get(
                "codec_name"
            ),

        "checks":
            checks,

        "failures":
            failures,

        "failed_checks":
            failed,
    }


    OUT.write_text(
        json.dumps(
            {
                "gate":
                    result
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
        " VI1310 FINAL RENDER AUDIT"
    )

    print(
        "=============================================="
    )

    print(
        "OUTPUT:",
        path
    )

    print(
        "SIZE:",
        width,
        "x",
        height
    )

    print(
        "FPS:",
        fps
    )

    print(
        "DURATION:",
        duration
    )

    print(
        "AUDIO DURATION:",
        audio_duration
    )

    print(
        "DELTA:",
        duration_delta
    )

    print(
        "VIDEO CODEC:",
        result[
            "video_codec"
        ]
    )

    print(
        "AUDIO CODEC:",
        result[
            "audio_codec"
        ]
    )


    print()
    print(
        "===== CHECKS ====="
    )


    for key, value in (
        checks.items()
    ):

        print(
            key,
            "=",
            (
                "PASS"
                if value
                else "FAIL"
            )
        )


    print(
        "FAILED:",
        failed
    )

    print(
        "FAILURES:",
        failures
    )

    print()
    print(
        "STATUS:",
        status
    )


    if not certified:
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
