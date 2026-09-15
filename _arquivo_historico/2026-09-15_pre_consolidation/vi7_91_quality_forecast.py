#!/usr/bin/env python3

VERSION = "7.91"

def forecast(result):
    visual = (
        result.get(
            "visual_quality_gate"
        )
        or {}
    )

    diversity = (
        result.get("diversity")
        or {}
    )

    transitions = (
        result.get("transitions")
        or {}
    )

    documentary = (
        result.get("documentary")
        or {}
    )

    visual_score = float(
        visual.get(
            "average_quality",
            0
        )
    )

    diversity_score = float(
        diversity.get(
            "score",
            0
        )
    )

    transition_score = float(
        transitions.get(
            "average",
            0
        )
    )

    documentary_score = (
        float(
            documentary.get(
                "documentary_ratio",
                0
            )
        )
        * 100
    )

    score = (
        visual_score * .40
        + diversity_score * .25
        + transition_score * .25
        + documentary_score * .10
    )

    if score >= 85:
        level = "EXCELLENT"

    elif score >= 75:
        level = "STRONG"

    elif score >= 65:
        level = "PROMISING"

    else:
        level = "NEEDS_WORK"

    return {
        "version": VERSION,
        "forecast_score":
            round(score, 2),
        "level": level,
        "components": {
            "visual":
                round(
                    visual_score,
                    2
                ),
            "diversity":
                round(
                    diversity_score,
                    2
                ),
            "transitions":
                round(
                    transition_score,
                    2
                ),
            "documentary":
                round(
                    documentary_score,
                    2
                ),
        },
    }

def self_test():
    result = forecast({
        "visual_quality_gate": {
            "average_quality": 90
        },
        "diversity": {
            "score": 90
        },
        "transitions": {
            "average": 90
        },
        "documentary": {
            "documentary_ratio": .8
        },
    })

    assert result[
        "forecast_score"
    ] > 80

    print(
        "VI7.91 QUALITY FORECAST=PASS"
    )

if __name__ == "__main__":
    self_test()
