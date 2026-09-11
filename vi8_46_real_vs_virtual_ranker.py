#!/usr/bin/env python3

from vi8_38_real_media_score import (
    evaluate as real_score
)

from vi8_12_virtual_candidate_factory import (
    build as virtual_candidates
)

from vi8_09_candidate_scorer import (
    evaluate as virtual_score
)

VERSION = "8.46"


def rank(
    scene,
    category,
    real_candidates,
    previous_winners=None
):
    previous_winners = (
        previous_winners
        or []
    )

    ranking = []

    for candidate in (
        real_candidates
        or []
    ):
        score = real_score(
            scene,
            candidate,
            previous_winners
        )

        ranking.append({
            "kind":
                "REAL",

            "candidate":
                candidate,

            "score":
                score["score"],

            "eligible":
                score["eligible"],

            "blockers":
                score["blockers"],

            "warnings":
                score["warnings"],

            "technical_score":
                score[
                    "technical_score"
                ],
        })

    virtual = virtual_candidates(
        scene,
        category
    )

    for candidate in virtual:
        score = virtual_score(
            scene,
            candidate,
            previous_winners
        )

        ranking.append({
            "kind":
                "VIRTUAL_IDEAL",

            "candidate":
                candidate,

            "score":
                score["score"],

            "eligible":
                score["eligible"],

            "blockers":
                score["blockers"],

            "warnings":
                score["warnings"],

            "technical_score":
                None,
        })

    eligible = [
        x
        for x in ranking
        if x.get(
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

    winner = (
        eligible[0]
        if eligible
        else None
    )

    real_only = [
        x
        for x in eligible
        if x.get(
            "kind"
        ) == "REAL"
    ]

    real_only.sort(
        key=lambda x:
            float(
                x.get(
                    "score",
                    0
                )
            ),
        reverse=True
    )

    best_real = (
        real_only[0]
        if real_only
        else None
    )

    virtual_only = [
        x
        for x in eligible
        if x.get(
            "kind"
        ) == "VIRTUAL_IDEAL"
    ]

    virtual_only.sort(
        key=lambda x:
            float(
                x.get(
                    "score",
                    0
                )
            ),
        reverse=True
    )

    best_virtual = (
        virtual_only[0]
        if virtual_only
        else None
    )

    real_gap = None

    if (
        best_real
        and best_virtual
    ):
        real_gap = round(
            float(
                best_virtual[
                    "score"
                ]
            )
            -
            float(
                best_real[
                    "score"
                ]
            ),
            2
        )

    return {
        "version":
            VERSION,

        "ranking":
            ranking,

        "winner":
            winner,

        "best_real":
            best_real,

        "best_virtual":
            best_virtual,

        "virtual_advantage":
            real_gap,

        "real_candidate_count":
            len(
                real_candidates
                or []
            ),
    }


def self_test():
    assert VERSION == "8.46"

    print(
        "VI8.46 REAL VS VIRTUAL RANKER=PASS"
    )


if __name__ == "__main__":
    self_test()
