#!/usr/bin/env python3

from vi6_7_retrieval_planner import (
    plan
)

from vi6_8_storyboard_director import (
    build_global_plan
)

import vi6_6_active_brain as brain

import vi6_8_runtime_policy


# =====================================================
# 12 CENAS SINTÉTICAS
# =====================================================

scenes = [

    {
        "visual_mode":
            "evidence",

        "visual_query":
            "aircraft mystery",

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
            "city street"
    },

    {
        "visual_mode":
            "person",

        "visual_query":
            "young woman"
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
            "investigation"
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
            "cta_reuse"
    }
]


global_plan = (
    build_global_plan(
        scenes
    )
)


scene_map = {

    x["scene"]:
    x

    for x in global_plan[
        "scenes"
    ]

}


overrides = 0


for i, scene in enumerate(
    scenes,
    1
):

    p = plan(
        scene
    )


    scene[
        "_vi68_storyboard"
    ] = scene_map[
        i
    ]


    if p.get(
        "override"
    ):

        overrides += 1


# =====================================================
# PROVAR QUE O RUNTIME PATCH ESTÁ ATIVO
# =====================================================

assert getattr(
    brain,
    "_VI68_RUNTIME_PATCHED",
    False
)


doc = {

    "fonte":
        "Wikimedia",

    "tipo":
        "foto",

    "id":
        "flight19",

    "url":
        "flight19",

    "class":
        "REAL_DOCUMENTARY",

    "risk":
        "LOW",

    "quality_tier":
        "NORMAL",

    "truth_ok":
        True,

    "semantic":
        72,

    "provenance":
        95,

    "score":
        70,

    "evidence_class":
        "CASE_DIRECT",

    "wiki_query_tier":
        "CASE",

    "title":
        "Flight 19 aircraft 1945 archive"
}


test_scene = scenes[0]


result = brain.evaluate(
    doc,
    test_scene,
    {
        "intent":
            "EVIDENCE"
    }
)


assert result is not None


assert (
    "vi68_documentary_target"
    in result[
        "reasons"
    ]
)


print()
print(
    "======================================"
)
print(
    " VI6.7 + VI6.8 INTEGRATION TEST: PASS"
)
print(
    "======================================"
)

print(
    "SCENES:",
    len(
        scenes
    )
)

print(
    "QUERY OVERRIDES:",
    overrides
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
    "RUNTIME PATCH:",
    getattr(
        brain,
        "_VI68_RUNTIME_PATCHED",
        False
    )
)

print(
    "DOCUMENTARY TEST SCORE:",
    result[
        "score"
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
print()
