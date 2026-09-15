#!/usr/bin/env python3

VERSION = "8.53"


MIN_GAIN = {
    "CRITICAL": 0,
    "HIGH": 8,
    "MEDIUM": 6,
    "LOW": 4,
    "NONE": 999,
}


def threshold(need):
    return MIN_GAIN.get(
        str(
            need or "LOW"
        ).upper(),
        6
    )


def self_test():
    assert threshold(
        "HIGH"
    ) == 8

    assert threshold(
        "NONE"
    ) > 100

    print(
        "VI8.53 MINIMUM GAIN POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
