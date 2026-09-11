#!/usr/bin/env python3

VERSION = "7.01"

MAX_CANARIES = 6

MAX_PER_ZONE = 2


ZONES = (

    {
        "name":
            "EARLY_CONTEXT",

        "scenes":
            (2, 3, 4),

        "profiles":
            (
                "HORIZONTAL_DISCOVERY",
                "SLOW_PUSH",
            ),
    },

    {
        "name":
            "MID_CONTEXT",

        "scenes":
            (5, 6, 7, 8),

        "profiles":
            (
                "DETAIL_PUSH",
                "REVERSE_DRIFT",
            ),
    },

    {
        "name":
            "CLIMAX",

        "scenes":
            (9, 10, 11),

        "profiles":
            (
                "CLIMAX_PUSH",
                "CLIMAX_PAN",
            ),
    },
)


def zone_for_scene(scene):

    for zone in ZONES:

        if scene in zone["scenes"]:

            return zone

    return None


def policy():

    return {
        "version":
            VERSION,

        "max_canaries":
            MAX_CANARIES,

        "max_per_zone":
            MAX_PER_ZONE,

        "hook_scene":
            1,

        "cta_scene":
            12,

        "video_canary_allowed":
            False,

        "full_active":
            False,
    }


def self_test():

    assert MAX_CANARIES == 6
    assert MAX_PER_ZONE == 2

    assert (
        zone_for_scene(3)["name"]
        == "EARLY_CONTEXT"
    )

    assert (
        zone_for_scene(7)["name"]
        == "MID_CONTEXT"
    )

    assert (
        zone_for_scene(10)["name"]
        == "CLIMAX"
    )

    assert zone_for_scene(1) is None
    assert zone_for_scene(12) is None

    print(
        "VI7.01 SIX-SCENE POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
