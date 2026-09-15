#!/usr/bin/env python3

from vi7_31_visual_ontology import (
    classify
)

VERSION = "8.43"


def resolve(scene):
    return classify(
        scene
    )


def self_test():
    result = resolve({
        "query":
            "handwritten document paper"
    })

    assert result == "DOCUMENT"

    print(
        "VI8.43 REAL CATEGORY RESOLVER=PASS"
    )


if __name__ == "__main__":
    self_test()
