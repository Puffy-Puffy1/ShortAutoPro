#!/usr/bin/env python3

VERSION = "7.58"

def evaluate(scenes):
    categories = [
        x.get("category")
        for x in scenes
        if x.get("category")
    ]

    shots = [
        x.get("shot")
        for x in scenes
        if x.get("shot")
    ]

    motions = [
        x.get("motion")
        for x in scenes
        if x.get("motion")
    ]

    category_diversity = len(
        set(categories)
    )

    shot_diversity = len(
        set(shots)
    )

    motion_diversity = len(
        set(motions)
    )

    score = (
        min(category_diversity, 5) * 8
        + min(shot_diversity, 3) * 10
        + min(motion_diversity, 6) * 5
    )

    return {
        "version": VERSION,
        "categories":
            category_diversity,
        "shots":
            shot_diversity,
        "motions":
            motion_diversity,
        "score":
            min(100, score),
    }

def self_test():
    result = evaluate([
        {
            "category": "DOCUMENT",
            "shot": "close_up",
            "motion": "DOCUMENT_SCAN",
        },
        {
            "category": "LOCATION",
            "shot": "wide",
            "motion": "HORIZONTAL_DISCOVERY",
        },
    ])

    assert result["score"] > 0

    print(
        "VI7.58 MEDIA DIVERSITY=PASS"
    )

if __name__ == "__main__":
    self_test()
