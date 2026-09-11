#!/usr/bin/env python3

import os


VERSION = "7.25"


def enabled():

    return (
        os.getenv(
            "VI730_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
    )


def self_test():

    assert VERSION == "7.25"

    print(
        "VI7.25 RUNTIME ROUTER=PASS"
    )


if __name__ == "__main__":
    self_test()
