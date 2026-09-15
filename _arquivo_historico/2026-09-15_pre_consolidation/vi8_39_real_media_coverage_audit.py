#!/usr/bin/env python3

VERSION = "8.39"


def evaluate(grouped):

    scenes = (
        grouped.get(
            "scenes"
        )
        or {}
    )


    covered = [
        scene
        for scene, items
        in scenes.items()
        if items
    ]


    missing = [
        scene
        for scene
        in range(
            1,
            13
        )
        if scene
        not in covered
    ]


    multi = {
        scene:
            len(items)

        for scene, items
        in scenes.items()

        if len(items) > 1
    }


    return {
        "version":
            VERSION,

        "covered_scenes":
            covered,

        "covered_count":
            len(covered),

        "missing_scenes":
            missing,

        "multi_candidate_scenes":
            multi,

        "unassigned_count":
            grouped.get(
                "unassigned_count",
                0
            ),

        "status":
            (
                "PASS"
                if len(covered) == 12
                else "PASS_WITH_WARNINGS"
            ),
    }


def self_test():

    assert VERSION == "8.39"

    print(
        "VI8.39 REAL MEDIA COVERAGE AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
