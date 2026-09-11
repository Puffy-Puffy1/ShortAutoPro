#!/usr/bin/env python3

from vi6_91_three_scene_policy import (
    ZONES
)


VERSION = "6.92"


def zone_for_scene(scene):

    for zone in ZONES:

        if scene in zone["scenes"]:

            return {
                "zone":
                    zone["name"],

                "profile":
                    zone["profile"],
            }


    return None


def self_test():

    assert (
        zone_for_scene(5)["profile"]
        == "HORIZONTAL_DISCOVERY"
    )

    assert (
        zone_for_scene(10)["profile"]
        == "CLIMAX_PAN"
    )

    assert zone_for_scene(1) is None
    assert zone_for_scene(12) is None

    print(
        "VI6.92 PROFILE ALLOCATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
