#!/usr/bin/env python3

VERSION = "7.11"

MAX_VI7_SCENES = 9

MIN_HEALTHY_CANARIES = 4

MAX_CONSECUTIVE_VI7 = 2


def policy():

    return {
        "version":
            VERSION,

        "max_vi7_scenes":
            MAX_VI7_SCENES,

        "min_healthy_canaries":
            MIN_HEALTHY_CANARIES,

        "max_consecutive_vi7":
            MAX_CONSECUTIVE_VI7,

        "hook_scene":
            1,

        "cta_scene":
            12,

        "native_video_vi7":
            False,

        "source_recovery_active":
            False,

        "full_active":
            False,
    }


def self_test():

    p = policy()

    assert p["max_vi7_scenes"] == 9
    assert p["hook_scene"] == 1
    assert p["cta_scene"] == 12
    assert p["full_active"] is False

    print(
        "VI7.11 ADAPTIVE POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
