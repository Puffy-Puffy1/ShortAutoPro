#!/usr/bin/env python3

import json
import re

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1310_controlled_render_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

DISCOVERY = (
    BASE
    / "temp/vi1310/"
    "discovery.json"
)

PREPARED = (
    BASE
    / "temp/vi1300/"
    "prepared_manifest.json"
)

OUT = (
    BASE
    / "temp/vi1310/"
    "timeline.json"
)

LABEL_ASS = (
    BASE
    / "temp/vi1310/"
    "semantic_labels.ass"
)


def read_json(
    path
):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def word_weight(
    text
):
    words = re.findall(
        r"\w+",
        str(
            text
        ),
        flags=re.UNICODE,
    )


    return max(
        3,
        len(
            words
        )
    )


def allocate(
    total,
    segments
):
    count = len(
        segments
    )


    floor = float(
        POLICY[
            "timing"
        ][
            "minimum_scene_duration"
        ]
    )


    if total <= (
        floor
        *
        count
    ):

        values = [
            total
            /
            count

            for _ in segments
        ]

    else:

        weights = [
            word_weight(
                text
            )

            for text in segments
        ]


        residual = (
            total
            -
            floor
            *
            count
        )


        weight_total = sum(
            weights
        )


        values = [
            floor
            +
            residual
            *
            (
                weight
                /
                weight_total
            )

            for weight in weights
        ]


    # Preserve exact audio duration.
    difference = (
        total
        -
        sum(
            values
        )
    )


    values[
        -1
    ] += difference


    return values


def ass_time(
    seconds
):
    seconds = max(
        0.0,
        float(
            seconds
        )
    )


    hours = int(
        seconds
        //
        3600
    )


    minutes = int(
        (
            seconds
            %
            3600
        )
        //
        60
    )


    secs = (
        seconds
        %
        60
    )


    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{secs:05.2f}"
    )


def ass_escape(
    value
):
    return (
        str(
            value
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


def write_labels_ass(
    timeline
):
    font_size = int(
        POLICY[
            "semantic_labels"
        ][
            "font_size"
        ]
    )


    margin = int(
        POLICY[
            "semantic_labels"
        ][
            "top_margin"
        ]
    )


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
            "Style: Label,Arial,"
            f"{font_size},"
            "&H00FFFFFF,&H00FFFFFF,"
            "&H00000000,&H90000000,"
            "-1,0,0,0,"
            "100,100,0,0,"
            "3,1,0,"
            f"8,80,80,{margin},"
            "1"
        ),
        "",
        "[Events]",
        (
            "Format: Layer,Start,End,Style,"
            "Name,MarginL,MarginR,MarginV,"
            "Effect,Text"
        ),
    ]


    for item in timeline:

        label = item.get(
            "overlay_label"
        )


        if not label:
            continue


        lines.append(
            (
                "Dialogue: 0,"
                + ass_time(
                    item[
                        "start"
                    ]
                )
                + ","
                + ass_time(
                    item[
                        "end"
                    ]
                )
                + ",Label,,0,0,0,,"
                + ass_escape(
                    label
                )
            )
        )


    LABEL_ASS.write_text(
        "\n".join(
            lines
        )
        + "\n",
        encoding="utf-8"
    )


def main():
    discovery = read_json(
        DISCOVERY
    )

    prepared = read_json(
        PREPARED
    )


    duration = float(
        discovery[
            "audio_duration"
        ]
    )


    segments = discovery.get(
        "segments"
    ) or [
        ""
        for _ in range(
            12
        )
    ]


    prepared_items = sorted(
        prepared.get(
            "prepared"
        )
        or [],
        key=lambda item:
            int(
                item[
                    "scene"
                ]
            ),
    )


    if len(
        prepared_items
    ) != 12:

        raise SystemExit(
            "VI1310: PREPARED SCENES != 12"
        )


    durations = allocate(
        duration,
        segments
    )


    timeline = []

    cursor = 0.0


    for index, item in enumerate(
        prepared_items
    ):

        scene_duration = float(
            durations[
                index
            ]
        )


        start = cursor

        end = (
            start
            +
            scene_duration
        )


        timeline.append({
            "scene":
                int(
                    item[
                        "scene"
                    ]
                ),

            "start":
                round(
                    start,
                    4
                ),

            "end":
                round(
                    end,
                    4
                ),

            "duration":
                round(
                    scene_duration,
                    4
                ),

            "segment":
                segments[
                    index
                ],

            "prepared_path":
                item[
                    "prepared_path"
                ],

            "prepared_sha256":
                item[
                    "prepared_sha256"
                ],

            "strategy":
                item.get(
                    "strategy"
                ),

            "semantic_mode":
                item.get(
                    "semantic_mode"
                ),

            "overlay_label":
                item.get(
                    "overlay_label"
                ),

            "presentation_constraints":
                item.get(
                    "presentation_constraints"
                )
                or [],
        })


        cursor = end


    # Eliminate accumulated floating-point drift.
    timeline[
        -1
    ][
        "end"
    ] = round(
        duration,
        4
    )


    timeline[
        -1
    ][
        "duration"
    ] = round(
        duration
        -
        timeline[
            -1
        ][
            "start"
        ],
        4
    )


    output = {
        "version":
            "1310.00",

        "sid":
            discovery[
                "sid"
            ],

        "audio":
            discovery[
                "audio"
            ],

        "subtitle":
            discovery[
                "subtitle"
            ],

        "audio_duration":
            duration,

        "scene_count":
            len(
                timeline
            ),

        "timeline":
            timeline,

        "network":
            False,

        "production_mutation":
            False,
    }


    OUT.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    write_labels_ass(
        timeline
    )


    print()
    print(
        "=============================================="
    )

    print(
        " VI1310 TIMELINE PLANNER"
    )

    print(
        "=============================================="
    )


    for item in timeline:

        print(
            "SCENE",
            item[
                "scene"
            ],
            "|",
            f"{item['start']:.2f}",
            "->",
            f"{item['end']:.2f}",
            "|",
            f"{item['duration']:.2f}s",
            "| label=",
            item[
                "overlay_label"
            ],
        )


    print()
    print(
        "TOTAL:",
        timeline[
            -1
        ][
            "end"
        ]
    )

    print(
        "LABEL ASS:",
        LABEL_ASS
    )


if __name__ == "__main__":
    main()
