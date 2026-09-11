#!/usr/bin/env python3

VERSION = "7.13"


CATALOG = {

    "HORIZONTAL_DISCOVERY": {
        "energy": 2,
        "direction": "RIGHT",
    },

    "SLOW_PUSH": {
        "energy": 1,
        "direction": "CENTER",
    },

    "DETAIL_PUSH": {
        "energy": 2,
        "direction": "CENTER",
    },

    "REVERSE_DRIFT": {
        "energy": 2,
        "direction": "LEFT",
    },

    "CLIMAX_PUSH": {
        "energy": 3,
        "direction": "CENTER",
    },

    "CLIMAX_PAN": {
        "energy": 3,
        "direction": "RIGHT",
    },
}


ROLE_POOLS = {

    "EARLY_CONTEXT": (
        "HORIZONTAL_DISCOVERY",
        "SLOW_PUSH",
        "DETAIL_PUSH",
    ),

    "CONTEXT": (
        "DETAIL_PUSH",
        "REVERSE_DRIFT",
        "SLOW_PUSH",
        "HORIZONTAL_DISCOVERY",
    ),

    "CLIMAX": (
        "CLIMAX_PUSH",
        "CLIMAX_PAN",
        "DETAIL_PUSH",
        "REVERSE_DRIFT",
    ),
}


def info(profile):

    return CATALOG.get(
        profile,
        {}
    )


def pool(role):

    return ROLE_POOLS.get(
        role,
        ()
    )


def self_test():

    assert (
        info(
            "CLIMAX_PUSH"
        )["energy"]
        == 3
    )

    assert pool(
        "CONTEXT"
    )

    print(
        "VI7.13 MOTION CATALOG=PASS"
    )


if __name__ == "__main__":
    self_test()
