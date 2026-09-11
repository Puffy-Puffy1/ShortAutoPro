#!/usr/bin/env python3

VERSION = "6.83"


CANARY_SCENE = 5


def validate(
    scene
):

    return {

        "version":
            VERSION,

        "scene":
            scene,

        "locked_scene":
            CANARY_SCENE,

        "allowed":
            (
                scene
                == CANARY_SCENE
            ),

        "other_scenes_allowed":
            False,
    }


def self_test():

    assert (
        validate(
            5
        )["allowed"]
        is True
    )

    assert (
        validate(
            4
        )["allowed"]
        is False
    )

    print(
        "VI6.83 SCENE LOCK=PASS"
    )


if __name__ == "__main__":
    self_test()
