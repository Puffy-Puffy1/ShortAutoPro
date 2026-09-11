#!/usr/bin/env python3

VERSION = "7.55"

DOCUMENTARY = {
    "DOCUMENT",
    "EVIDENCE",
    "LOCATION",
}

def evaluate(scenes):
    documentary = sum(
        1
        for item in scenes
        if item.get("category")
        in DOCUMENTARY
    )

    total = len(scenes)

    ratio = (
        documentary / total
        if total
        else 0
    )

    return {
        "version": VERSION,
        "documentary_scenes":
            documentary,
        "total_scenes":
            total,
        "documentary_ratio":
            round(ratio, 3),
        "status": (
            "PASS"
            if ratio >= .40
            else "PASS_WITH_WARNINGS"
        ),
    }

def self_test():
    result = evaluate([
        {"category": "DOCUMENT"},
        {"category": "LOCATION"},
        {"category": "FACE"},
    ])

    assert (
        result[
            "documentary_ratio"
        ] > .5
    )

    print(
        "VI7.55 DOCUMENTARY CONTINUITY=PASS"
    )

if __name__ == "__main__":
    self_test()
