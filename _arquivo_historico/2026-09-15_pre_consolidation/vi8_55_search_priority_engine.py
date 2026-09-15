#!/usr/bin/env python3

VERSION = "8.55"


NEED_WEIGHT = {
    "CRITICAL": 50,
    "HIGH": 35,
    "MEDIUM": 20,
    "LOW": 8,
    "NONE": 0,
}


def evaluate(
    scene,
    category,
    need,
    gap
):
    score = (
        NEED_WEIGHT.get(
            need,
            0
        )
        + max(
            0,
            float(
                gap or 0
            )
        )
    )

    reasons = []

    if category == "FACE":
        score += 10
        reasons.append(
            "face_quality_priority"
        )

    if category in {
        "DOCUMENT",
        "EVIDENCE",
    }:
        score += 8
        reasons.append(
            "documentary_priority"
        )

    if scene in {
        1,
        9,
        10,
        11,
    }:
        score += 8
        reasons.append(
            "high_narrative_impact"
        )

    return {
        "version": VERSION,
        "scene": scene,
        "priority_score":
            round(
                score,
                2
            ),
        "reasons": reasons,
    }


def self_test():
    result = evaluate(
        10,
        "FACE",
        "HIGH",
        12
    )

    assert (
        result[
            "priority_score"
        ] > 50
    )

    print(
        "VI8.55 SEARCH PRIORITY ENGINE=PASS"
    )


if __name__ == "__main__":
    self_test()
