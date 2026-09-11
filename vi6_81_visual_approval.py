#!/usr/bin/env python3

VERSION = "6.81"


APPROVAL = {

    "scene": 5,

    "profile":
        "HORIZONTAL_DISCOVERY",

    "status":
        "APPROVED",

    "legacy_vs_vi6":
        "VI6_WINNER",

    "human_visual_review":
        True,

    "approved_for_runtime_canary":
        True,

    "approved_for_full_active":
        False,
}


def get():

    return {
        "version":
            VERSION,

        **APPROVAL,
    }


def self_test():

    result = get()

    assert (
        result[
            "approved_for_runtime_canary"
        ]
        is True
    )

    assert (
        result[
            "approved_for_full_active"
        ]
        is False
    )

    print(
        "VI6.81 VISUAL APPROVAL=PASS"
    )


if __name__ == "__main__":
    self_test()
