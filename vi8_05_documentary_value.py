#!/usr/bin/env python3

VERSION = "8.05"

VALUE = {
    "DOCUMENT": 100,
    "EVIDENCE": 100,
    "LOCATION": 90,
    "FACE": 80,
    "OBJECT": 80,
    "GENERAL": 65,
    "ABSTRACT": 45,
}

def score(category):
    return VALUE.get(
        str(
            category or "GENERAL"
        ).upper(),
        65
    )

def self_test():
    assert (
        score("DOCUMENT")
        > score("ABSTRACT")
    )

    print(
        "VI8.05 DOCUMENTARY VALUE=PASS"
    )

if __name__ == "__main__":
    self_test()
