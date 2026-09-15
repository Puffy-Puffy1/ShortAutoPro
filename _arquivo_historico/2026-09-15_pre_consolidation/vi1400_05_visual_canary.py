#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

MANIFEST = (
    BASE
    / "temp/vi1400/"
    "render_manifest.json"
)

CANARY_DIR = (
    BASE
    / "temp/vi1400/canary"
)

CONCAT = (
    CANARY_DIR
    / "scenes.concat.txt"
)

ASS = (
    CANARY_DIR
    / "labels.ass"
)

OUTPUT = (
    CANARY_DIR
    / "VI1400_visual_canary.mp4"
)

REPORT = (
    BASE
    / "logs/producao/"
    "vi1400_05_visual_canary_latest.json"
)


def run(
    command,
):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr[-5000:]
        )


def ass_time(
    seconds,
):
    cs = int(
        round(
            seconds * 100
        )
    )

    hours = (
        cs // 360000
    )

    cs %= 360000

    minutes = (
        cs // 6000
    )

    cs %= 6000

    secs = (
        cs // 100
    )

    hundredths = (
        cs % 100
    )

    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{secs:02d}."
        f"{hundredths:02d}"
    )


def escape_ass(
    text,
):
    return (
        str(text)
        .replace(
            "\\",
            ""
        )
        .replace(
            "{",
            "("
        )
        .replace(
            "}",
            ")"
        )
        .replace(
            "\n",
            " "
        )
    )


def main():
    data = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    if (
        data.get(
            "status"
        )
        !=
        "VI1400_RENDER_MANIFEST_CERTIFIED"
    ):

        raise SystemExit(
            "RENDER_MANIFEST_NOT_CERTIFIED"
        )

    scenes = (
        data.get(
            "scenes"
        )
        or {}
    )

    CANARY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    concat_lines = []

    current = 0.0

    dialogue = []

    for number in range(
        1,
        13
    ):
        scene = scenes[
            str(number)
        ]

        path = Path(
            scene[
                "prepared_path"
            ]
        ).resolve()

        duration = float(
            scene[
                "canary_duration"
            ]
        )

        concat_lines.append(
            "file '"
            + str(path)
            .replace(
                "'",
                "'\\''"
            )
            + "'"
        )

        concat_lines.append(
            "duration "
            + str(duration)
        )

        label = scene.get(
            "overlay_label"
        )

        if label:

            start = ass_time(
                current
            )

            end = ass_time(
                current
                +
                duration
            )

            dialogue.append(
                "Dialogue: 0,"
                + start
                + ","
                + end
                + ",Default,,0,0,0,,"
                + escape_ass(
                    label
                )
            )

        current += duration

    last_path = Path(
        scenes[
            "12"
        ][
            "prepared_path"
        ]
    ).resolve()

    concat_lines.append(
        "file '"
        + str(last_path)
        .replace(
            "'",
            "'\\''"
        )
        + "'"
    )

    CONCAT.write_text(
        "\n".join(
            concat_lines
        )
        + "\n",
        encoding="utf-8"
    )

    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,3,1,0,2,70,70,115,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

    ASS.write_text(
        ass_header
        +
        "\n".join(
            dialogue
        )
        +
        "\n",
        encoding="utf-8"
    )

    OUTPUT.unlink(
        missing_ok=True
    )

    subtitle_filter = (
        "subtitles='"
        + str(
            ASS.resolve()
        )
        + "'"
    )

    run([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(CONCAT),
        "-vf",
        (
            "fps=30,"
            + subtitle_filter
            + ",format=yuv420p"
        ),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(OUTPUT),
    ])

    if (
        not OUTPUT.exists()
        or
        OUTPUT.stat().st_size
        < 10000
    ):

        raise SystemExit(
            "CANARY_OUTPUT_INVALID"
        )

    report = {
        "version":
            "1400.00",

        "status":
            "VI1400_VISUAL_CANARY_GENERATED",

        "path":
            str(
                OUTPUT.resolve()
            ),

        "bytes":
            OUTPUT.stat().st_size,

        "expected_duration":
            current,

        "scene_count":
            12,

        "audio":
            False,

        "renderer_production":
            False,

        "production_mutation":
            False,
    }

    REPORT.write_text(
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
        " VI1400 VISUAL CANARY"
    )
    print(
        "=============================================="
    )

    print(
        "OUTPUT:",
        OUTPUT
    )

    print(
        "BYTES:",
        OUTPUT.stat().st_size
    )

    print(
        "EXPECTED DURATION:",
        current
    )

    print(
        "STATUS:",
        report["status"]
    )


if __name__ == "__main__":
    main()
