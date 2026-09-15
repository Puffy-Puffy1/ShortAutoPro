#!/usr/bin/env python3

import subprocess
from pathlib import Path


from vi1330_03_motion_engine import (
    image_filter,
)

from vi1330_04_archive_video_director import (
    render_archive,
)


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


def render_image(
    scene,
    destination,
):
    duration = float(
        scene[
            "duration"
        ]
    )


    frames = max(
        1,
        int(
            round(
                duration
                *
                30
            )
        )
    )


    vf = image_filter(
        scene[
            "strategy"
        ],
        frames,
    )


    return run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-loop",
        "1",
        "-i",
        scene[
            "visual_input"
        ],
        "-vf",
        vf,
        "-frames:v",
        str(
            frames
        ),
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
        "-movflags",
        "+faststart",
        str(
            destination
        ),
    ])


def render_scene(
    scene,
    destination,
):
    if (
        scene[
            "source_mode"
        ]
        ==
        "AUTHENTIC_CASE_VIDEO"
    ):

        return render_archive(
            scene[
                "visual_input"
            ],
            destination,
            float(
                scene[
                    "duration"
                ]
            ),
            int(
                scene[
                    "scene"
                ]
            ),
        )


    return render_image(
        scene,
        destination
    )
