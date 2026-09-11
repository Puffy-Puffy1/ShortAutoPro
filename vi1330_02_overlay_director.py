#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

POLICY = json.loads(
    (
        BASE
        / "config/vi1330_publication_quality_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

PLAN = json.loads(
    (
        BASE
        / "temp/vi1330/publication_visual_plan.json"
    ).read_text(
        encoding="utf-8"
    )
)

OUT = (
    BASE
    / "temp/vi1330/publication_overlays.ass"
)


def t(seconds):
    seconds = max(
        0.0,
        float(
            seconds
        )
    )

    hour = int(
        seconds // 3600
    )

    minute = int(
        (
            seconds % 3600
        ) // 60
    )

    second = (
        seconds % 60
    )

    return (
        f"{hour}:"
        f"{minute:02d}:"
        f"{second:05.2f}"
    )


def esc(text):
    return (
        str(
            text
        )
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
    safe = POLICY[
        "safe_zone"
    ]

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
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
            "Style: Label,Arial,27,"
            "&H00FFFFFF,&H00FFFFFF,"
            "&H00000000,&H88000000,"
            "-1,0,0,0,"
            "100,100,0,0,"
            "3,1,0,"
            f"8,{safe['left']},{safe['right']},{safe['top']},1"
        ),
        (
            "Style: Hook1,Arial,61,"
            "&H00FFFFFF,&H00FFFFFF,"
            "&H00000000,&HA0000000,"
            "-1,0,0,0,"
            "100,100,1,0,"
            "3,2,0,"
            "8,70,70,205,1"
        ),
        (
            "Style: Hook2,Arial,71,"
            "&H0000EFFF,&H0000EFFF,"
            "&H00000000,&HA0000000,"
            "-1,0,0,0,"
            "100,100,1,0,"
            "3,2,0,"
            "8,70,70,285,1"
        ),
        (
            "Style: HookSub,Arial,27,"
            "&H00FFFFFF,&H00FFFFFF,"
            "&H00000000,&H88000000,"
            "0,0,0,0,"
            "100,100,0,0,"
            "3,1,0,"
            "8,80,80,370,1"
        ),
        "",
        "[Events]",
        (
            "Format: Layer,Start,End,Style,"
            "Name,MarginL,MarginR,MarginV,"
            "Effect,Text"
        )
    ]


    for item in PLAN[
        "plans"
    ]:

        lines.append(
            (
                "Dialogue: 0,"
                + t(
                    item[
                        "start"
                    ]
                )
                + ","
                + t(
                    item[
                        "end"
                    ]
                )
                + ",Label,,0,0,0,,"
                + esc(
                    item[
                        "overlay_label"
                    ]
                )
            )
        )


    hook = POLICY[
        "hook"
    ]


    if hook[
        "enabled"
    ]:

        start = t(
            hook[
                "start"
            ]
        )

        end = t(
            hook[
                "end"
            ]
        )


        lines.extend([
            (
                "Dialogue: 2,"
                + start
                + ","
                + end
                + ",Hook1,,0,0,0,,"
                + esc(
                    hook[
                        "text_line_1"
                    ]
                )
            ),

            (
                "Dialogue: 2,"
                + start
                + ","
                + end
                + ",Hook2,,0,0,0,,"
                + esc(
                    hook[
                        "text_line_2"
                    ]
                )
            ),

            (
                "Dialogue: 2,"
                + start
                + ","
                + end
                + ",HookSub,,0,0,0,,"
                + esc(
                    hook[
                        "subtext"
                    ]
                )
            ),
        ])


    OUT.write_text(
        "\n".join(
            lines
        )
        + "\n",
        encoding="utf-8"
    )


    print(
        "VI1330 OVERLAY ASS:",
        OUT
    )


if __name__ == "__main__":
    main()
