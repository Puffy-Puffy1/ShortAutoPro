#!/usr/bin/env python3

from vi6_7_retrieval_planner import (
    plan
)

from vi6_8_storyboard_director import (
    build_global_plan
)


scenes = [
    {
        "visual_mode":
            "evidence",

        "visual_query":
            "airplane mystery",

        "must_have":
            [
                "Flight 19",
                "1945"
            ]
    },

    {
        "visual_mode":
            "location",

        "visual_query":
            "old hotel",

        "must_have":
            [
                "Cecil Hotel",
                "Los Angeles"
            ]
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "busy city street"
    },

    {
        "visual_mode":
            "person",

        "visual_query":
            "sad young girl portrait"
    },

    {
        "visual_mode":
            "object",

        "visual_query":
            "medicine bottle"
    },

    {
        "visual_mode":
            "evidence",

        "visual_query":
            "newspaper archive"
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "police investigation"
    },

    {
        "visual_mode":
            "location",

        "visual_query":
            "building exterior"
    },

    {
        "visual_mode":
            "evidence",

        "visual_query":
            "case documents"
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "pharmacy shelves"
    },

    {
        "visual_mode":
            "object",

        "visual_query":
            "sealed packaging"
    },

    {
        "visual_mode":
            "cta_reuse",

        "visual_query":
            "subscribe"
    },
]


print()
print(
    "======================================"
)
print(
    " VI6.7 + VI6.8 OFFLINE TEST"
)
print(
    "======================================"
)


for i, scene in enumerate(
    scenes,
    1
):

    p = plan(scene)

    print()
    print(
        f"CENA {i:02d}"
    )

    print(
        "  ROLE:",
        p["role"]
    )

    print(
        "  STRATEGY:",
        p["strategy"]
    )

    print(
        "  PRIMARY:",
        p["primary"]
    )

    print(
        "  OVERRIDE:",
        p["override"]
    )

    print(
        "  ANCHORS:",
        p["anchors"]
    )


global_plan = (
    build_global_plan(
        scenes
    )
)


print()
print(
    "======================================"
)
print(
    " GLOBAL STORYBOARD"
)
print(
    "======================================"
)

print(
    "DOCUMENTARY TARGET:",
    global_plan[
        "documentary_target"
    ]
)

print(
    "MOTION TARGET:",
    global_plan[
        "motion_target"
    ]
)

print(
    "MAX SAME SOURCE:",
    global_plan[
        "max_same_source_streak"
    ]
)

print(
    "MAX SAME ASSET:",
    global_plan[
        "max_identical_asset"
    ]
)

print(
    "CTA:",
    global_plan[
        "cta_strategy"
    ]
)

print()
print(
    "API CALLS=0"
)
print(
    "DOWNLOADS=0"
)
print(
    "VIDEOS=0"
)
