#!/usr/bin/env python3

VERSION = "8.36"


def group(items):

    scenes = {
        number: []
        for number
        in range(
            1,
            13
        )
    }

    unassigned = []


    for item in items:

        scene = item.get(
            "scene_guess"
        )

        if scene in scenes:

            scenes[
                scene
            ].append(
                item
            )

        else:

            unassigned.append(
                item
            )


    return {
        "version":
            VERSION,

        "scenes":
            scenes,

        "unassigned":
            unassigned,

        "assigned_count":
            sum(
                len(v)
                for v
                in scenes.values()
            ),

        "unassigned_count":
            len(
                unassigned
            ),
    }


def self_test():

    result = group([
        {
            "scene_guess": 2
        },
        {
            "scene_guess": None
        },
    ])

    assert (
        len(
            result[
                "scenes"
            ][2]
        )
        == 1
    )

    assert (
        result[
            "unassigned_count"
        ]
        == 1
    )

    print(
        "VI8.36 SCENE MEDIA GROUPER=PASS"
    )


if __name__ == "__main__":
    self_test()
