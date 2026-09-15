#!/usr/bin/env python3

VERSION = "8.21"


def priority(
    selection,
    cinematic_plan=None
):
    comparison = (
        selection.get("comparison")
        or {}
    )

    delta = float(
        comparison.get(
            "delta",
            0
        )
        or 0
    )

    category = str(
        selection.get(
            "category"
        )
        or "GENERAL"
    ).upper()

    scene = int(
        selection.get(
            "scene"
        )
        or 0
    )

    score = delta

    reasons = []

    if delta >= 15:
        score += 20
        reasons.append(
            "large_media_gain"
        )

    elif delta >= 7:
        score += 10
        reasons.append(
            "meaningful_media_gain"
        )

    if category == "FACE":
        score += 10
        reasons.append(
            "subject_preservation_priority"
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

    if cinematic_plan:
        if not cinematic_plan.get(
            "shot_match",
            True
        ):
            score += 15
            reasons.append(
                "shot_mismatch"
            )

        if cinematic_plan.get(
            "status"
        ) == "HOLD":
            score += 25
            reasons.append(
                "cinematic_hold"
            )

    return {
        "version":
            VERSION,

        "scene":
            scene,

        "priority_score":
            round(
                score,
                2
            ),

        "reasons":
            reasons,
    }


def self_test():
    result = priority({
        "scene": 6,
        "category": "FACE",
        "comparison": {
            "delta": 18
        },
    })

    assert (
        result["priority_score"]
        > 18
    )

    print(
        "VI8.21 IMPROVEMENT PRIORITY=PASS"
    )


if __name__ == "__main__":
    self_test()
