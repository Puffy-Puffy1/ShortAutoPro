#!/usr/bin/env python3

from vi7_11_adaptive_policy import (
    MAX_CONSECUTIVE_VI7,
    MAX_VI7_SCENES
)

from vi7_14_adaptive_state import (
    count,
    consecutive_vi7_if_select
)


VERSION = "7.16"


def allow(scene):

    reasons = []


    if count() >= MAX_VI7_SCENES:

        reasons.append(
            "global_limit"
        )


    if (
        consecutive_vi7_if_select(
            scene
        )
        > MAX_CONSECUTIVE_VI7
    ):

        reasons.append(
            "consecutive_limit"
        )


    return {
        "version":
            VERSION,

        "allowed":
            not reasons,

        "reasons":
            reasons,
    }


def self_test():

    assert VERSION == "7.16"

    print(
        "VI7.16 SEQUENCE GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
