#!/usr/bin/env python3

import os


VERSION = "6.99"


def enabled():

    return (
        os.getenv(
            "VI700_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
    )


def self_test():

    assert VERSION == "6.99"

    print(
        "VI6.99 RUNTIME ROUTER=PASS"
    )


if __name__ == "__main__":
    self_test()
