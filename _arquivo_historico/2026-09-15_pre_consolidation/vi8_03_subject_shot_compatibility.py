#!/usr/bin/env python3

VERSION = "8.03"

IDEAL = {
    "FACE": {
        "medium": 100,
        "close_up": 100,
        "wide": 45,
    },

    "DOCUMENT": {
        "close_up": 100,
        "medium": 90,
        "wide": 40,
    },

    "EVIDENCE": {
        "close_up": 100,
        "medium": 90,
        "wide": 55,
    },

    "LOCATION": {
        "wide": 100,
        "medium": 90,
        "close_up": 55,
    },

    "OBJECT": {
        "close_up": 100,
        "medium": 90,
        "wide": 50,
    },

    "GENERAL": {
        "medium": 90,
        "wide": 80,
        "close_up": 80,
    },
}

def score(category, shot):
    category = str(
        category or "GENERAL"
    ).upper()

    shot = str(
        shot or "medium"
    ).lower()

    return IDEAL.get(
        category,
        IDEAL["GENERAL"]
    ).get(
        shot,
        65
    )

def self_test():
    assert score(
        "FACE",
        "wide"
    ) < score(
        "FACE",
        "medium"
    )

    assert score(
        "LOCATION",
        "wide"
    ) == 100

    print(
        "VI8.03 SUBJECT SHOT COMPATIBILITY=PASS"
    )

if __name__ == "__main__":
    self_test()
