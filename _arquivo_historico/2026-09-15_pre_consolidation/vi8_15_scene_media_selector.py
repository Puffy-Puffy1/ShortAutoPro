#!/usr/bin/env python3

from vi8_09_candidate_scorer import (
    evaluate as score_candidate
)

from vi8_12_virtual_candidate_factory import (
    build as virtual_candidates
)

from vi8_13_current_media_model import (
    from_scene as current_candidate
)

from vi8_14_current_vs_ideal import (
    compare
)

VERSION = "8.15"

def select(
    scene,
    category,
    previous_winners=None
):
    previous_winners = (
        previous_winners
        or []
    )

    current = current_candidate(
        scene,
        category
    )

    current_result = (
        score_candidate(
            scene,
            current,
            previous_winners
        )
    )

    candidates = [
        current
    ]

    candidates.extend(
        virtual_candidates(
            scene,
            category
        )
    )

    ranked = []

    for candidate in candidates:
        result = score_candidate(
            scene,
            candidate,
            previous_winners
        )

        ranked.append({
            "candidate":
                candidate,

            "score":
                result["score"],

            "eligible":
                result["eligible"],

            "blockers":
                result["blockers"],

            "warnings":
                result["warnings"],

            "components":
                result["components"],
        })

    eligible = [
        item
        for item in ranked
        if item["eligible"]
    ]

    eligible.sort(
        key=lambda item:
            item["score"],
        reverse=True
    )

    if not eligible:
        winner = ranked[0]
    else:
        winner = eligible[0]

    comparison = compare(
        current_result["score"],
        winner["score"]
    )

    return {
        "version":
            VERSION,

        "scene":
            scene.get("scene"),

        "category":
            category,

        "current":
            {
                "candidate":
                    current,

                "score":
                    current_result[
                        "score"
                    ],

                "components":
                    current_result[
                        "components"
                    ],
            },

        "winner":
            winner,

        "candidate_count":
            len(ranked),

        "ranking":
            ranked,

        "comparison":
            comparison,
    }

def self_test():
    result = select(
        {
            "scene": 6,
            "query":
                "young girl portrait",
            "shot_type":
                "wide",
            "segment":
                "girl portrait",
        },
        "FACE"
    )

    assert (
        result[
            "candidate_count"
        ] >= 3
    )

    print(
        "VI8.15 SCENE MEDIA SELECTOR=PASS"
    )

if __name__ == "__main__":
    self_test()
