#!/usr/bin/env python3

VERSION = "7.12"


def role(scene):

    if scene == 1:
        return "HOOK"

    if scene == 12:
        return "CTA"

    if scene in {
        2,
        3,
        4,
    }:
        return "EARLY_CONTEXT"

    if scene in {
        5,
        6,
        7,
        8,
    }:
        return "CONTEXT"

    if scene in {
        9,
        10,
        11,
    }:
        return "CLIMAX"

    return "UNKNOWN"


def self_test():

    assert role(1) == "HOOK"
    assert role(6) == "CONTEXT"
    assert role(10) == "CLIMAX"
    assert role(12) == "CTA"

    print(
        "VI7.12 NARRATIVE ROLE=PASS"
    )


if __name__ == "__main__":
    self_test()
