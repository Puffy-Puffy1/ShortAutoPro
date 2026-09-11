#!/usr/bin/env python3

from vi7_01_six_scene_policy import (
    zone_for_scene
)

from vi7_02_runtime_state import (
    zone_count
)


VERSION = "7.03"


def allocate(scene):

    zone = zone_for_scene(
        scene
    )

    if zone is None:

        return None


    index = zone_count(
        zone["name"]
    )


    profiles = zone[
        "profiles"
    ]


    if index >= len(profiles):

        return None


    return {
        "version":
            VERSION,

        "scene":
            scene,

        "zone":
            zone["name"],

        "profile":
            profiles[index],

        "profile_index":
            index,
    }


def self_test():

    from vi7_02_runtime_state import (
        reset,
        claim
    )

    reset()

    first = allocate(3)

    assert (
        first["profile"]
        == "HORIZONTAL_DISCOVERY"
    )

    claim(
        3,
        first["zone"]
    )

    second = allocate(4)

    assert (
        second["profile"]
        == "SLOW_PUSH"
    )

    reset()

    print(
        "VI7.03 PROFILE ALLOCATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
