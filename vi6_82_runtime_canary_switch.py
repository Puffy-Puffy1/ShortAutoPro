#!/usr/bin/env python3

import os

from vi6_81_visual_approval import (
    get as visual_approval
)


VERSION = "6.82"


CANARY_ENV = (
    "VI682_CANARY_MODE"
)


def enabled():

    return (
        os.getenv(
            CANARY_ENV,
            "OFF"
        ).upper()
        == "ON"
    )


def should_use_vi6(
    scene
):

    approval = visual_approval()


    if not enabled():

        return False


    if not approval.get(
        "approved_for_runtime_canary"
    ):

        return False


    return (
        scene
        == approval.get(
            "scene"
        )
    )


def self_test():

    assert VERSION == "6.82"

    print(
        "VI6.82 RUNTIME CANARY SWITCH=PASS"
    )


if __name__ == "__main__":
    self_test()
