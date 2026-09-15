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

TIMELINE = json.loads(
    (
        BASE
        / "temp/vi1310/timeline.json"
    ).read_text(
        encoding="utf-8"
    )
)

OUTPUT = (
    BASE
    / "videos/canary/vi1330/"
    "VI1330_contact_sheet.jpg"
)


def main():
    inputs = []

    filters = []


    for index, scene in enumerate(
        TIMELINE[
            "timeline"
        ]
    ):

        middle = (
            float(
                scene[
                    "start"
                ]
            )
            +
            float(
                scene[
                    "duration"
                ]
            )
            /
            2.0
        )


        inputs.extend([
            "-ss",
            f"{middle:.3f}",
            "-i",
            str(
                VIDEO
            ),
        ])


        filters.append(
            (
                f"[{index}:v]"
                "scale=270:480,"
                f"drawtext=text='S{index + 1}':"
                "x=12:y=12:"
                "fontsize=32:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=black@0.65"
                f"[v{index}]"
            )
        )


    refs = "".join(
        f"[v{i}]"

        for i in range(
            12
        )
    )


    fc = (
        ";".join(
            filters
        )
        +
        ";"
        +
        refs
        +
        "xstack=inputs=12:"
        "layout="
        "0_0|270_0|540_0|810_0|"
        "0_480|270_480|540_480|810_480|"
        "0_960|270_960|540_960|810_960"
        "[out]"
    )


    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
    ]


    command.extend(
        inputs
    )


    command.extend([
        "-filter_complex",
        fc,
        "-map",
        "[out]",
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(
            OUTPUT
        ),
    ])


    result = subprocess.run(
        command,
        check=False,
    )


    if (
        result.returncode
        != 0
        or
        not OUTPUT.exists()
    ):

        raise SystemExit(
            1
        )


    print(
        "CONTACT SHEET:",
        OUTPUT
    )
    print(
        "BYTES:",
        OUTPUT.stat().st_size
    )


if __name__ == "__main__":
    main()
