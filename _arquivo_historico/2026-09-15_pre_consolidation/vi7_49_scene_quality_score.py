#!/usr/bin/env python3

VERSION = "7.49"

def score(
    scene,
    category,
    shot_match
):
    value = 50.0

    query = str(
        scene.get("query") or ""
    ).strip()

    must = (
        scene.get("must_have")
        or []
    )

    avoid = (
        scene.get("avoid")
        or []
    )

    visual_mode = str(
        scene.get("visual_mode")
        or ""
    ).strip()

    if query:
        value += 15

    if len(query.split()) >= 4:
        value += 10

    if must:
        value += 10

    if avoid:
        value += 5

    if shot_match:
        value += 10

    if visual_mode:
        value += 5

    if category in {
        "DOCUMENT",
        "EVIDENCE",
        "LOCATION",
        "FACE",
    }:
        value += 5

    return min(
        100.0,
        value
    )

def self_test():
    scene = {
        "query":
            "old handwritten letter paper",
        "must_have":
            ["paper"],
        "avoid":
            ["phone"],
        "visual_mode":
            "document",
    }

    result = score(
        scene,
        "DOCUMENT",
        True
    )

    assert result >= 90

    print(
        "VI7.49 SCENE QUALITY SCORE=PASS"
    )

if __name__ == "__main__":
    self_test()
