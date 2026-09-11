#!/usr/bin/env python3

VERSION = "8.22"


def evaluate(selection):
    winner = (
        selection.get("winner")
        or {}
    )

    ranking = (
        selection.get("ranking")
        or []
    )

    winner_score = float(
        winner.get(
            "score",
            0
        )
        or 0
    )

    eligible = [
        item
        for item in ranking
        if item.get(
            "eligible"
        )
    ]

    eligible.sort(
        key=lambda x:
            float(
                x.get(
                    "score",
                    0
                )
            ),
        reverse=True
    )

    second_score = (
        float(
            eligible[1].get(
                "score",
                0
            )
        )
        if len(eligible) >= 2
        else 0
    )

    margin = (
        winner_score
        - second_score
    )

    comparison = (
        selection.get("comparison")
        or {}
    )

    improvement = float(
        comparison.get(
            "delta",
            0
        )
        or 0
    )

    confidence = (
        45
        + min(
            30,
            max(
                0,
                margin * 2
            )
        )
        + min(
            25,
            max(
                0,
                improvement
            )
        )
    )

    confidence = max(
        0,
        min(
            100,
            confidence
        )
    )

    if confidence >= 80:
        level = "HIGH"

    elif confidence >= 65:
        level = "MEDIUM"

    else:
        level = "LOW"

    return {
        "version":
            VERSION,

        "scene":
            selection.get(
                "scene"
            ),

        "confidence":
            round(
                confidence,
                2
            ),

        "level":
            level,

        "winner_margin":
            round(
                margin,
                2
            ),

        "improvement":
            round(
                improvement,
                2
            ),
    }


def self_test():
    result = evaluate({
        "scene": 4,

        "winner": {
            "score": 90
        },

        "ranking": [
            {
                "score": 90,
                "eligible": True,
            },
            {
                "score": 70,
                "eligible": True,
            },
        ],

        "comparison": {
            "delta": 15
        },
    })

    assert (
        result["confidence"]
        >= 80
    )

    print(
        "VI8.22 SELECTION CONFIDENCE=PASS"
    )


if __name__ == "__main__":
    self_test()
