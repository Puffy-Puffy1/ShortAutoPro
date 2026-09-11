#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/vi1320_visual_director_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

PLAN = json.loads(
    (
        BASE
        / "temp/vi1320/visual_plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

OUT = (
    BASE
    / "temp/vi1320/visual_overlays.ass"
)


def timestamp(seconds):
    seconds = max(
        0,
        float(seconds)
    )

    h = int(
        seconds // 3600
    )

    m = int(
        (
            seconds % 3600
        ) // 60
    )

    s = seconds % 60

    return (
        f"{h}:"
        f"{m:02d}:"
        f"{s:05.2f}"
    )


def escape(value):
    return (
        str(value)
        .replace(
            "\\",
            "\\\\"
        )
        .replace(
            "{",
            "\\{"
        )
        .replace(
            "}",
            "\\}"
        )
        .replace(
            "\n",
            " "
        )
    )


def main():
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        (
            "Format: Name,Fontname,Fontsize,"
            "PrimaryColour,SecondaryColour,"
            "OutlineColour,BackColour,"
            "Bold,Italic,Underline,StrikeOut,"
            "ScaleX,ScaleY,Spacing,Angle,"
            "BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,"
            "Encoding"
        ),
        (
            "Style: Label,Arial,29,"
            "&H00FFFFFF,&H00FFFFFF,"
            "&H00000000,&H88000000,"
            "-1,0,0,0,"
            "100,100,0,0,"
            "3,1,0,"
            "8,70,70,72,1"
        ),
        (
            "Style: Hook,Arial,54,"
            "&H00FFFFFF,&H00FFFFFF,"
            "&H00000000,&H99000000,"
            "-1,0,0,0,"
            "100,100,0,0,"
            "3,2,0,"
            "8,80,80,155,1"
        ),
        "",
        "[Events]",
        (
            "Format: Layer,Start,End,Style,"
            "Name,MarginL,MarginR,MarginV,"
            "Effect,Text"
        ),
    ]

    for item in PLAN["plans"]:
        label = item.get(
            "overlay_label"
        )

        if not label:
            continue

        lines.append(
            (
                "Dialogue: 0,"
                + timestamp(
                    item["start"]
                )
                + ","
                + timestamp(
                    item["end"]
                )
                + ",Label,,0,0,0,,"
                + escape(
                    label
                )
            )
        )

    if POLICY[
        "hook"
    ][
        "enabled"
    ]:

        lines.append(
            (
                "Dialogue: 1,0:00:00.00,"
                + timestamp(
                    POLICY[
                        "hook"
                    ][
                        "duration"
                    ]
                )
                + ",Hook,,0,0,0,,"
                + escape(
                    POLICY[
                        "hook"
                    ][
                        "text"
                    ]
                )
            )
        )

    OUT.write_text(
        "\n".join(
            lines
        )
        + "\n",
        encoding="utf-8"
    )

    print(
        "VI1320 OVERLAYS:",
        OUT
    )


if __name__ == "__main__":
    main()
