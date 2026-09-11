#!/usr/bin/env python3

VERSION = "8.11"

IDEAL = {
    "FACE":
        ["medium", "close_up"],

    "DOCUMENT":
        ["close_up", "medium"],

    "EVIDENCE":
        ["close_up", "medium"],

    "LOCATION":
        ["wide", "medium"],

    "OBJECT":
        ["close_up", "medium"],

    "GENERAL":
        ["medium", "wide"],

    "ABSTRACT":
        ["medium", "wide"],
}

def generate(category):
    return IDEAL.get(
        str(category or "GENERAL").upper(),
        IDEAL["GENERAL"]
    )

def self_test():
    assert (
        generate("FACE")[0]
        == "medium"
    )

    print(
        "VI8.11 IDEAL SHOT GENERATOR=PASS"
    )

if __name__ == "__main__":
    self_test()
