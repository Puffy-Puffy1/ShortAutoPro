#!/usr/bin/env python3

VERSION = "8.42"


def by_number(scenes):
    result = {}

    for index, scene in enumerate(
        scenes,
        start=1
    ):
        number = int(
            scene.get(
                "scene",
                index
            )
        )

        result[number] = scene

    return result


def self_test():
    result = by_number([
        {
            "scene": 3,
            "query": "house"
        }
    ])

    assert 3 in result

    print(
        "VI8.42 SCENE LOOKUP=PASS"
    )


if __name__ == "__main__":
    self_test()
