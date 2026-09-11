#!/usr/bin/env python3

VERSION = "8.68"


def build(
    scene,
    category,
    ideal_shot,
    priority,
    queries
):
    return {
        "version": VERSION,

        "scene":
            scene,

        "category":
            category,

        "ideal_shot":
            ideal_shot,

        "priority":
            priority,

        "queries":
            list(
                queries or []
            ),

        "max_results_per_query":
            5,

        "allow_network":
            False,

        "allow_download":
            False,

        "allow_replace":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "mode":
            "SEARCH_SHADOW",
    }


def self_test():
    result = build(
        6,
        "FACE",
        "medium",
        90,
        ["portrait"]
    )

    assert (
        result["allow_network"]
        is False
    )

    print(
        "VI8.68 SEARCH CONTRACT=PASS"
    )


if __name__ == "__main__":
    self_test()
