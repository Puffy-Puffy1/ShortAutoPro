#!/usr/bin/env python3

import subprocess


def run(
    command
):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    return {
        "returncode":
            result.returncode,

        "stdout":
            result.stdout,

        "stderr":
            result.stderr,
    }


def probe_duration(
    source
):
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nw=1:nk=1",
        str(
            source
        ),
    ])


    if result[
        "returncode"
    ] != 0:

        return 0.0


    try:

        return float(
            result[
                "stdout"
            ].strip()
        )

    except Exception:

        return 0.0


def archive_filter():
    return (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "boxblur=28:14,"
        "eq=brightness=-0.08"
        "[bg];"

        "[0:v]"
        "scale=1020:1740:"
        "force_original_aspect_ratio=decrease"
        "[fg];"

        "[bg][fg]"
        "overlay="
        "(W-w)/2:"
        "(H-h)/2,"
        "vignette=PI/8,"
        "fps=30,"
        "format=yuv420p"
    )


def render_archive(
    source,
    destination,
    duration,
    scene_number,
):
    source_duration = probe_duration(
        source
    )


    if source_duration <= 0:

        return {
            "returncode":
                1,

            "stdout":
                "",

            "stderr":
                "archive_probe_failed",
        }


    if int(
        scene_number
    ) == 1:

        offset = 0.0


    else:

        offset = min(
            max(
                source_duration
                *
                0.52,
                3.0
            ),
            max(
                0.0,
                source_duration
                -
                duration
                -
                0.2
            ),
        )


    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-stream_loop",
        "-1",
        "-ss",
        f"{offset:.3f}",
        "-i",
        str(
            source
        ),
        "-t",
        f"{duration:.3f}",
        "-filter_complex",
        archive_filter(),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        str(
            destination
        ),
    ]


    return run(
        command
    )
