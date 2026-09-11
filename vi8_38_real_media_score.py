#!/usr/bin/env python3

from vi8_09_candidate_scorer import (
    evaluate as candidate_score
)

VERSION = "8.38"


def evaluate(
    scene,
    candidate,
    previous=None
):

    score = candidate_score(
        scene,
        candidate,
        previous or []
    )


    technical = float(
        (
            candidate.get(
                "metadata"
            )
            or {}
        ).get(
            "technical_score",
            50
        )
        or 50
    )


    base = float(
        score.get(
            "score",
            0
        )
    )


    combined = (
        base * .80
        + technical * .20
    )


    return {
        "version":
            VERSION,

        "score":
            round(
                combined,
                2
            ),

        "base_score":
            round(
                base,
                2
            ),

        "technical_score":
            round(
                technical,
                2
            ),

        "eligible":
            score.get(
                "eligible"
            ),

        "blockers":
            score.get(
                "blockers"
            )
            or [],

        "warnings":
            score.get(
                "warnings"
            )
            or [],
    }


def self_test():

    assert VERSION == "8.38"

    print(
        "VI8.38 REAL MEDIA SCORE=PASS"
    )


if __name__ == "__main__":
    self_test()
