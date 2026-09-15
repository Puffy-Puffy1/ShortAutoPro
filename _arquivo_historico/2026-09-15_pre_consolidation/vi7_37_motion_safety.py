#!/usr/bin/env python3

VERSION = "7.37"

SAFE = {
    "FACE": (
        "FACE_SAFE_PUSH",
        "SLOW_PUSH",
        "MICRO_HOLD",
    ),
    "DOCUMENT": (
        "DOCUMENT_SCAN",
        "SLOW_PUSH",
        "DETAIL_PUSH",
    ),
    "EVIDENCE": (
        "DETAIL_PUSH",
        "MICRO_DISCOVERY",
        "SLOW_PUSH",
    ),
    "LOCATION": (
        "HORIZONTAL_DISCOVERY",
        "ARCHITECTURE_DRIFT",
        "SLOW_PUSH",
    ),
    "OBJECT": (
        "DETAIL_PUSH",
        "MICRO_DISCOVERY",
        "SLOW_PUSH",
    ),
    "ABSTRACT": (
        "SLOW_PUSH",
        "REVERSE_DRIFT",
        "MICRO_HOLD",
    ),
    "GENERAL": (
        "SLOW_PUSH",
        "DETAIL_PUSH",
        "HORIZONTAL_DISCOVERY",
    ),
}

def profiles(category):
    return SAFE.get(
        category,
        SAFE["GENERAL"]
    )

def self_test():
    assert (
        "FACE_SAFE_PUSH"
        in profiles("FACE")
    )

    assert (
        "HORIZONTAL_DISCOVERY"
        not in profiles("FACE")
    )

    print("VI7.37 MOTION SAFETY=PASS")

if __name__ == "__main__":
    self_test()
