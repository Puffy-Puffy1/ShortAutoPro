#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

AUDIT = (
    BASE
    / "logs/producao/"
    "vi1310_04_render_audit_latest.json"
)

TIMELINE = (
    BASE
    / "temp/vi1310/"
    "timeline.json"
)

OUTPUT = (
    BASE
    / "videos/canary/vi1310/"
    "VI1310_contact_sheet.jpg"
)


def read_json(
    path
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main():
    audit = read_json(
        AUDIT
    ).get(
        "gate",
        {}
    )


    if (
        audit.get(
            "status"
        )
        !=
        "VI1310_FIRST_CONTROLLED_RENDER_CANARY_CERTIFIED"
    ):

        raise SystemExit(
            "CONTACT SHEET BLOCKED"
        )


    video = audit[
        "output"
    ]


    timeline = read_json(
        TIMELINE
    )[
        "timeline"
    ]


    filters = []

    inputs = []


    for index, scene in enumerate(
        timeline
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
            video,
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


    filter_complex = (
        ";".join(
            filters
        )
        +
        ";"
        +
        refs
        +
        "xstack="
        "inputs=12:"
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
        filter_complex,
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
        "CONTACT SHEET BYTES:",
        OUTPUT.stat().st_size
    )


if __name__ == "__main__":
    main()
