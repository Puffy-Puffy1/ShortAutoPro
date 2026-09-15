#!/usr/bin/env python3

import os


from vi6_49_real_command_mapper import (
    map_command
)

from vi6_50_shadow_filter_comparator import (
    shadow_compare
)

from vi6_51_canary_gate import (
    evaluate
)

from vi6_47_renderer_switch import (
    adapt_scene_command
)


command = [

    "ffmpeg",
    "-y",

    "-loop",
    "1",

    "-i",
    "image.jpg",

    "-vf",
    (
        "scale=1200:2133:"
        "force_original_aspect_ratio=increase,"
        "crop=1200:2133,"
        "zoompan=z='1.02':x='0':y='0':"
        "d=120:s=1080x1920:fps=30,"
        "setsar=1,"
        "format=yuv420p"
    ),

    "-frames:v",
    "120",

    "-c:v",
    "libx264",

    "cena_07.mp4",
]


mapped = map_command(
    command
)


assert (
    mapped[
        "status"
    ]
    == "MAPPED"
)


assert (
    mapped[
        "scene"
    ]
    == 7
)


registry = {

    "status":
        "READY",

    "path":
        "SELFTEST",

    "age_seconds":
        0,

    "contracts":
        [
            {
                "scene":
                    7,

                "fingerprint":
                    "contract7",

                "contract":
                    {
                        "scene":
                            7,

                        "media_type":
                            "STILL",

                        "role":
                            "CONTEXT",

                        "renderer_applied":
                            False,

                        "ken_burns":
                            {
                                "enabled":
                                    True,

                                "zoom_start":
                                    1.0,

                                "zoom_end":
                                    1.04,

                                "start_x":
                                    .47,

                                "start_y":
                                    .50,

                                "end_x":
                                    .53,

                                "end_y":
                                    .50,
                            },
                    },
            }
        ],
}


comparison = shadow_compare(
    command,
    mapped,
    registry=registry
)


assert (
    comparison[
        "status"
    ]
    in {
        "EXACT_MATCH",
        "SAFE_DIFFERENCE",
    }
)


assert (
    comparison[
        "legacy_filter_replaced"
    ]
    is False
)


# =====================================
# LEGACY identity test
# =====================================

old = os.environ.get(
    "VI647_RENDERER_MODE"
)


try:

    os.environ[
        "VI647_RENDERER_MODE"
    ] = "LEGACY"


    snapshot = list(
        command
    )


    result = adapt_scene_command(
        command
    )


    assert result is command

    assert command == snapshot


finally:

    if old is None:

        os.environ.pop(
            "VI647_RENDERER_MODE",
            None
        )

    else:

        os.environ[
            "VI647_RENDERER_MODE"
        ] = old


# =====================================
# CANARY GATE synthetic test
# =====================================

shadow = {

    "unique_scenes":
        12,

    "holds":
        0,

    "command_mutations":
        0,

    "filter_replacements":
        0,

    "events":
        [
            {
                "scene":
                    n,

                "status":
                    "SAFE_DIFFERENCE",
            }

            for n in range(
                1,
                13
            )
        ],
}


gate = evaluate(
    shadow,

    {
        "status":
            "CERTIFIED",

        "temporary_video_deleted":
            True,
    },

    {
        "next_stage_allowed":
            True
    }
)


assert (
    gate[
        "status"
    ]
    == "READY_FOR_CANARY_PATCH"
)


assert (
    gate[
        "active_canary_authorized"
    ]
    is False
)


print()
print(
    "======================================"
)
print(
    " VI6.49-6.51 INTEGRATION: PASS"
)
print(
    "======================================"
)
print(
    "REAL COMMAND PARSING=PASS"
)
print(
    "SHADOW FILTER COMPARISON=PASS"
)
print(
    "LEGACY COMMAND IDENTITY=PASS"
)
print(
    "CANARY GATE LOGIC=PASS"
)
print(
    "ACTIVE CANARY=LOCKED"
)
print(
    "FFMPEG EXECUTED=0"
)
print(
    "VIDEO GENERATED=0"
)
