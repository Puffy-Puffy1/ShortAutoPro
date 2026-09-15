#!/usr/bin/env python3

VERSION = "6.67"


def build(scene):

    return {
        "version": VERSION,
        "scene": scene,

        "scope":
            "SINGLE_SCENE_ONLY",

        "failure_action":
            "RENDER_SAME_SCENE_WITH_LEGACY_FILTER",

        "global_pipeline_abort":
            False,

        "other_scenes_affected":
            False,

        "active_global_renderer":
            False,

        "rollback_required_on": [
            "ffmpeg_nonzero",
            "output_missing",
            "duration_invalid",
            "resolution_invalid",
            "filter_validation_failure",
            "unexpected_exception",
        ],

        "executed":
            False,
    }


def self_test():

    result = build(4)

    assert (
        result["failure_action"]
        == "RENDER_SAME_SCENE_WITH_LEGACY_FILTER"
    )

    assert (
        result["other_scenes_affected"]
        is False
    )

    print("VI6.67 ROLLBACK CONTRACT=PASS")


if __name__ == "__main__":
    self_test()
